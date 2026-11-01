"""The loop, against a scripted fake client: no API key, no network.

Every test ends with `assert_valid_history`: whatever happened, the next
customer message must be sendable.
"""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from in_tune.agent import FALLBACK_BETA, SORRY, Agent
from in_tune.policies import Policies
from in_tune.store import Store
from in_tune.toolbox import Toolbox
from in_tune.tools.store_info import TZ

NOW = datetime(2026, 10, 31, 15, 0, tzinfo=TZ)


def text(t):
    return SimpleNamespace(type="text", text=t)


def tool_use(id_, name, input_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def response(*content, stop_reason="end_turn", model=None):
    usage = SimpleNamespace(
        input_tokens=10, output_tokens=5, cache_read_input_tokens=3, cache_creation_input_tokens=1
    )
    fake = SimpleNamespace(content=list(content), stop_reason=stop_reason, usage=usage)
    if model:  # the real API always sets it; leaving it out tests the "unknown" case
        fake.model = model
    return fake


class FakeClient:
    """Returns scripted responses (or raises scripted exceptions) and records requests."""

    def __init__(self, *script):
        self.script, self.requests = list(script), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        step = self.script.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


def _has_text(content) -> bool:
    if isinstance(content, str):
        return bool(content.strip())
    return any(getattr(b, "type", None) == "text" and b.text.strip() for b in content)


def assert_valid_history(messages):
    """What the API needs before the next message: starts with the user, no empty
    content, every tool_use answered by exactly its tool_results, ends in text."""
    assert messages[0]["role"] == "user"
    pending: set[str] = set()
    for message in messages:
        content = message["content"]
        assert content not in ("", [], None)
        if message["role"] == "assistant" and not isinstance(content, str):
            assert not pending, "assistant spoke before tool results came back"
            pending = {b.id for b in content if getattr(b, "type", None) == "tool_use"}
        elif message["role"] == "user" and not isinstance(content, str):
            assert {r["tool_use_id"] for r in content} == pending
            pending = set()
        else:
            assert not pending, f"tool calls without results: {pending}"
    assert not pending
    assert messages[-1]["role"] == "assistant" and _has_text(messages[-1]["content"])


@pytest.fixture(scope="module")
def parts(tmp_path_factory):
    log = tmp_path_factory.mktemp("logs") / "handoffs.jsonl"
    policies = Policies()
    return Toolbox(Store(), policies, clock=lambda: NOW, handoff_log=log), policies


def make_agent(parts, *script, **kwargs):
    toolbox, policies = parts
    client = FakeClient(*script)
    return Agent(toolbox, policies, client=client, **kwargs), client


# --- happy paths ---------------------------------------------------------------


def test_plain_answer_needs_one_request(parts):
    agent, client = make_agent(parts, response(text("Olá! Como posso ajudar?")))
    reply = agent.send("oi")
    assert reply.text == "Olá! Como posso ajudar?"
    assert reply.tool_calls == [] and len(client.requests) == 1
    assert_valid_history(agent.messages)


def test_tool_result_goes_back_with_the_matching_id(parts):
    agent, client = make_agent(
        parts,
        response(tool_use("t1", "store_status", {}), stop_reason="tool_use"),
        response(text("Hoje fechamos às 13h.")),
    )
    reply = agent.send("vocês estão abertos?")
    assert reply.text == "Hoje fechamos às 13h."
    assert [c.name for c in reply.tool_calls] == ["store_status"]
    result = client.requests[1]["messages"][-1]["content"][0]
    assert result["tool_use_id"] == "t1" and result["is_error"] is False
    assert json.loads(result["content"])["open_now"] is False  # Saturday 15:00
    assert_valid_history(agent.messages)


def test_parallel_calls_return_together_in_order(parts):
    agent, client = make_agent(
        parts,
        response(
            tool_use("a", "get_product", {"product_id": 95}),
            tool_use("b", "get_policy", {"section": "3.1"}),
            stop_reason="tool_use",
        ),
        response(text("ok")),
    )
    agent.send("quanto custa o Takamine e como parcelo?")
    results = client.requests[1]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["a", "b"]
    assert_valid_history(agent.messages)


def test_bad_tool_input_is_returned_as_an_error_not_raised(parts):
    agent, client = make_agent(
        parts,
        response(tool_use("t1", "check_order", {"order_id": 1}), stop_reason="tool_use"),
        response(text("Preciso do telefone ou e-mail do pedido.")),
    )
    reply = agent.send("cadê meu pedido 1?")
    assert reply.tool_calls[0].is_error
    assert client.requests[1]["messages"][-1]["content"][0]["is_error"] is True
    assert_valid_history(agent.messages)


def test_history_carries_over_between_messages(parts):
    agent, client = make_agent(parts, response(text("Oi, Ana!")), response(text("Claro.")))
    agent.send("oi, sou a Ana")
    agent.send("me ajuda?")
    assert [m["role"] for m in client.requests[1]["messages"]] == ["user", "assistant", "user"]
    assert_valid_history(agent.messages)


# --- every other exit keeps the history valid -----------------------------------


def test_runaway_tool_loop_stops_with_an_apology(parts):
    looping = [
        response(tool_use(f"t{i}", "store_status", {}), stop_reason="tool_use") for i in range(3)
    ]
    agent, _ = make_agent(parts, *looping, max_steps=3)
    reply = agent.send("?")
    assert reply.text == SORRY and reply.stop_reason == "max_steps"
    assert_valid_history(agent.messages)


@pytest.mark.parametrize("after_a_tool_step", [False, True])
def test_refusal_keeps_the_history_valid(parts, after_a_tool_step):
    script = [response(tool_use("t1", "store_status", {}), stop_reason="tool_use")] * (
        after_a_tool_step
    )
    agent, _ = make_agent(parts, *script, response(stop_reason="refusal"))
    reply = agent.send("...")
    assert reply.text == SORRY and reply.stop_reason == "refusal"
    assert_valid_history(agent.messages)


def test_truncated_tool_call_is_answered_as_not_run(parts):
    agent, _ = make_agent(
        parts, response(tool_use("t1", "get_product", {"product_id": 9}), stop_reason="max_tokens")
    )
    reply = agent.send("?")
    assert reply.text == SORRY and reply.tool_calls == []  # the cut-off call never ran
    assert_valid_history(agent.messages)


def test_empty_response_is_not_recorded_as_an_empty_turn(parts):
    agent, _ = make_agent(parts, response())
    assert agent.send("?").text == SORRY
    assert_valid_history(agent.messages)


def test_api_error_mid_loop_leaves_a_usable_session(parts):
    agent, _ = make_agent(
        parts,
        response(tool_use("t1", "store_status", {}), stop_reason="tool_use"),
        RuntimeError("529 overloaded"),
        response(text("Agora sim!")),
    )
    with pytest.raises(RuntimeError):
        agent.send("vocês estão abertos?")
    assert_valid_history(agent.messages)
    assert agent.send("e agora?").text == "Agora sim!"
    assert_valid_history(agent.messages)


def test_api_error_on_the_first_request_forgets_the_message(parts):
    agent, _ = make_agent(parts, RuntimeError("connection reset"))
    with pytest.raises(RuntimeError):
        agent.send("oi")
    assert agent.messages == []


def test_ctrl_c_while_tools_run_is_recovered(parts, monkeypatch):
    toolbox, _ = parts
    agent, _ = make_agent(
        parts, response(tool_use("t1", "store_status", {}), stop_reason="tool_use")
    )

    def interrupted(*_):
        raise KeyboardInterrupt

    monkeypatch.setattr(agent.toolbox, "run", interrupted)
    with pytest.raises(KeyboardInterrupt):
        agent.send("?")
    assert_valid_history(agent.messages)


# --- request shape and accounting ----------------------------------------------


def test_request_shape(parts):
    agent, client = make_agent(parts, response(text("ok")), effort="low")
    agent.send("oi")
    request = client.requests[0]
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request["cache_control"] == {"type": "ephemeral"}  # caches the growing history
    assert request["output_config"] == {"effort": "low"}
    assert request["betas"] == [FALLBACK_BETA] and request["fallbacks"] == "default"
    assert [t["name"] for t in request["tools"]][0] == "search_products"


@pytest.mark.parametrize(
    ("model", "has_fallback"),
    [("claude-opus-5-5", True), ("claude-sonnet-5-5", True), ("claude-haiku-5-5", False)],
)
def test_fallback_only_where_supported(parts, model, has_fallback):
    agent, client = make_agent(parts, response(text("ok")), model=model)
    agent.send("oi")
    assert ("fallbacks" in client.requests[0]) is has_fallback
    assert ("betas" in client.requests[0]) is has_fallback


def test_reply_records_each_model_the_api_reported(parts):
    agent, _ = make_agent(
        parts,
        response(
            tool_use("t1", "store_status", {}), stop_reason="tool_use", model="claude-sonnet-5-5"
        ),
        response(text("ok"), model="claude-opus-5-5"),  # e.g. a fallback served this step
    )
    assert agent.send("?").models == ["claude-sonnet-5-5", "claude-opus-5-5"]


def test_reply_has_no_model_when_the_api_reports_none(parts):
    agent, _ = make_agent(parts, response(text("ok")))
    assert agent.send("oi").models == []


def test_usage_is_summed_over_steps_including_cache_writes(parts):
    agent, _ = make_agent(
        parts,
        response(tool_use("t1", "store_status", {}), stop_reason="tool_use"),
        response(text("ok")),
    )
    assert agent.send("?").usage == {
        "input_tokens": 20,
        "output_tokens": 10,
        "cache_read_input_tokens": 6,
        "cache_creation_input_tokens": 2,
    }
