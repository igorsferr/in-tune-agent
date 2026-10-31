"""The loop, against a scripted fake client: no API key, no network."""

import json
from datetime import datetime
from types import SimpleNamespace

import pytest

from in_tune.agent import SORRY, Agent
from in_tune.policies import Policies
from in_tune.store import Store
from in_tune.toolbox import Toolbox
from in_tune.tools.store_info import TZ

NOW = datetime(2026, 10, 31, 15, 0, tzinfo=TZ)


def text(t):
    return SimpleNamespace(type="text", text=t)


def tool_use(id_, name, input_):
    return SimpleNamespace(type="tool_use", id=id_, name=name, input=input_)


def response(*content, stop_reason="end_turn"):
    usage = SimpleNamespace(input_tokens=10, output_tokens=5, cache_read_input_tokens=3)
    return SimpleNamespace(content=list(content), stop_reason=stop_reason, usage=usage)


class FakeClient:
    """Returns scripted responses and records every request."""

    def __init__(self, *responses):
        self.responses, self.requests = list(responses), []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.responses.pop(0)


@pytest.fixture(scope="module")
def parts(tmp_path_factory):
    log = tmp_path_factory.mktemp("logs") / "handoffs.jsonl"
    policies = Policies()
    return Toolbox(Store(), policies, clock=lambda: NOW, handoff_log=log), policies


def make_agent(parts, *responses, **kwargs):
    toolbox, policies = parts
    client = FakeClient(*responses)
    return Agent(toolbox, policies, client=client, **kwargs), client


def test_plain_answer_needs_one_request(parts):
    agent, client = make_agent(parts, response(text("Olá! Como posso ajudar?")))
    reply = agent.send("oi")
    assert reply.text == "Olá! Como posso ajudar?"
    assert reply.tool_calls == [] and len(client.requests) == 1
    assert [m["role"] for m in agent.messages] == ["user", "assistant"]


def test_tool_result_goes_back_with_the_matching_id(parts):
    agent, client = make_agent(
        parts,
        response(tool_use("t1", "store_status", {}), stop_reason="tool_use"),
        response(text("Hoje fechamos às 13h.")),
    )
    reply = agent.send("vocês estão abertos?")
    assert reply.text == "Hoje fechamos às 13h."
    assert [c.name for c in reply.tool_calls] == ["store_status"]
    tool_message = client.requests[1]["messages"][-1]
    assert tool_message["role"] == "user"
    result = tool_message["content"][0]
    assert result["tool_use_id"] == "t1" and result["is_error"] is False
    assert json.loads(result["content"])["open_now"] is False  # Saturday 15:00


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


def test_bad_tool_input_is_returned_as_an_error_not_raised(parts):
    agent, client = make_agent(
        parts,
        response(tool_use("t1", "check_order", {"order_id": 1}), stop_reason="tool_use"),
        response(text("Preciso do telefone ou e-mail do pedido.")),
    )
    reply = agent.send("cadê meu pedido 1?")
    assert reply.tool_calls[0].is_error
    assert client.requests[1]["messages"][-1]["content"][0]["is_error"] is True


def test_runaway_tool_loop_stops_with_an_apology(parts):
    looping = [
        response(tool_use(f"t{i}", "store_status", {}), stop_reason="tool_use") for i in range(3)
    ]
    agent, _ = make_agent(parts, *looping, max_steps=3)
    reply = agent.send("?")
    assert reply.text == SORRY and reply.stop_reason == "max_steps"
    assert agent.messages[-1] == {"role": "assistant", "content": SORRY}


def test_refusal_keeps_the_history_valid(parts):
    agent, _ = make_agent(parts, response(stop_reason="refusal"))
    reply = agent.send("...")
    assert reply.text == SORRY and reply.stop_reason == "refusal"
    assert agent.messages[-1] == {"role": "assistant", "content": SORRY}


def test_history_carries_over_between_messages(parts):
    agent, client = make_agent(parts, response(text("Oi, Ana!")), response(text("Claro.")))
    agent.send("oi, sou a Ana")
    agent.send("me ajuda?")
    assert [m["role"] for m in client.requests[1]["messages"]] == ["user", "assistant", "user"]


def test_request_shape(parts):
    agent, client = make_agent(parts, response(text("ok")), effort="low")
    agent.send("oi")
    request = client.requests[0]
    assert request["system"][0]["cache_control"] == {"type": "ephemeral"}
    assert request["output_config"] == {"effort": "low"}
    assert request["fallbacks"] == "default"  # Opus 5.5 supports server-side fallback
    assert [t["name"] for t in request["tools"]][0] == "search_products"


def test_haiku_gets_no_fallback_parameter(parts):
    agent, client = make_agent(parts, response(text("ok")), model="claude-haiku-5-5")
    agent.send("oi")
    assert "fallbacks" not in client.requests[0] and "betas" not in client.requests[0]


def test_usage_is_summed_over_steps(parts):
    agent, _ = make_agent(
        parts,
        response(tool_use("t1", "store_status", {}), stop_reason="tool_use"),
        response(text("ok")),
    )
    assert agent.send("?").usage == {
        "input_tokens": 20,
        "output_tokens": 10,
        "cache_read_input_tokens": 6,
    }
