"""The agent loop: send the conversation, run the tools the model asks for, repeat.

Written by hand (Anthropic SDK, no framework) so every step is visible:
one request, the tool calls it asked for, their results, the next request,
until the model answers in text.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import anthropic

from in_tune.policies import Policies
from in_tune.prompts import build_system_prompt
from in_tune.toolbox import Toolbox

# Chosen by the evals under the PLAN §8 rule (evals/results/20261031-1650-summary.md).
DEFAULT_MODEL = "claude-sonnet-5-5"
# Models that support server-side refusal fallback (`fallbacks: "default"`).
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_STEPS = 8  # model requests per customer message
USAGE_KEYS = (
    "input_tokens",
    "output_tokens",
    "cache_read_input_tokens",
    "cache_creation_input_tokens",
)
SORRY = (
    "Desculpe, não consegui concluir sua resposta agora. Pode tentar de novo em instantes? "
    "Se preferir, fale com a equipe pelo WhatsApp (67) 3321-4500."
)


@dataclass
class ToolCall:
    name: str
    input: dict
    result: dict
    is_error: bool


@dataclass
class Reply:
    text: str
    tool_calls: list[ToolCall]
    stop_reason: str
    usage: dict[str, int] = field(default_factory=dict)
    # Models the API reported for this turn's responses (more than one if a
    # fallback served a step); empty when the responses didn't say.
    models: list[str] = field(default_factory=list)


class Agent:
    """One customer conversation. History lives in memory for the session only."""

    def __init__(
        self,
        toolbox: Toolbox,
        policies: Policies,
        model: str = DEFAULT_MODEL,
        effort: str = "medium",
        client: anthropic.Anthropic | None = None,
        max_steps: int = MAX_STEPS,
    ):
        self.toolbox, self.model, self.effort, self.max_steps = toolbox, model, effort, max_steps
        self.client = client or anthropic.Anthropic()
        # Tools render before the system prompt, so one breakpoint here caches both.
        self.system = [
            {
                "type": "text",
                "text": build_system_prompt(policies),
                "cache_control": {"type": "ephemeral"},
            }
        ]
        self.tools = toolbox.definitions()
        self.messages: list[dict] = []

    def _request(self):
        kwargs = {
            "model": self.model,
            "max_tokens": 16000,
            "system": self.system,
            "tools": self.tools,
            "messages": self.messages,
            "output_config": {"effort": self.effort},
            # Also cache the conversation so far: within one customer message,
            # every tool step resends the whole history.
            "cache_control": {"type": "ephemeral"},
        }
        if self.model in FALLBACK_MODELS:
            kwargs |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return self.client.beta.messages.create(**kwargs)

    def send(self, text: str) -> Reply:
        """Answer one customer message.

        Every exit (an answer, a refusal, the step limit, a truncated reply, an
        API error, Ctrl+C) leaves the history ending in an assistant message with
        text and no tool call without its result, so the next message is valid.
        """
        self.messages.append({"role": "user", "content": text})
        calls: list[ToolCall] = []
        usage: dict[str, int] = {}
        models: list[str] = []
        try:
            for _ in range(self.max_steps):
                response = self._request()
                for key in USAGE_KEYS:
                    usage[key] = usage.get(key, 0) + (getattr(response.usage, key, 0) or 0)
                served = getattr(response, "model", None)
                if served and served not in models:
                    models.append(served)

                if response.stop_reason == "refusal" or not response.content:
                    # A refused turn's content (and any tool call in it) is discarded.
                    return self._close(calls, response.stop_reason or "empty", usage, models)

                self.messages.append({"role": "assistant", "content": response.content})
                tool_uses = [b for b in response.content if b.type == "tool_use"]
                if response.stop_reason == "tool_use" and tool_uses:
                    self.messages.append({"role": "user", "content": self._run(tool_uses, calls)})
                    continue
                if tool_uses:  # stopped mid-call (e.g. max_tokens): those calls never ran
                    self.messages.append({"role": "user", "content": _not_run(tool_uses)})
                    return self._close(calls, response.stop_reason, usage, models)

                reply = "\n".join(b.text for b in response.content if b.type == "text").strip()
                if not reply:
                    return self._close(calls, response.stop_reason, usage, models)
                return Reply(reply, calls, response.stop_reason, usage, models)
            return self._close(calls, "max_steps", usage, models)
        except BaseException:
            self._recover()
            raise

    def _run(self, tool_uses, calls: list[ToolCall]) -> list[dict]:
        """Run every tool call of one step; all results go back in one message."""
        results = []
        for block in tool_uses:
            result, is_error = self.toolbox.run(block.name, block.input)
            calls.append(ToolCall(block.name, block.input, result, is_error))
            content = json.dumps(result, ensure_ascii=False, default=str)
            results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": content,
                    "is_error": is_error,
                }
            )
        return results

    def _close(
        self, calls: list[ToolCall], reason: str, usage: dict[str, int], models: list[str]
    ) -> Reply:
        """End the turn with the fixed apology, recorded in the history too."""
        self.messages.append({"role": "assistant", "content": SORRY})
        return Reply(SORRY, calls, reason, usage, models)

    def _recover(self) -> None:
        """After an exception mid-turn, put the history back in a valid state."""
        last = self.messages[-1]
        if last["role"] == "user" and isinstance(last["content"], str):
            self.messages.pop()  # nothing was answered: forget the message
            return
        if last["role"] == "assistant":
            pending = [b for b in last["content"] if getattr(b, "type", None) == "tool_use"]
            if pending:  # interrupted while running tools
                self.messages.append({"role": "user", "content": _not_run(pending)})
        self.messages.append({"role": "assistant", "content": SORRY})


def _not_run(tool_uses) -> list[dict]:
    return [
        {
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": '{"error": "cut off before it ran; not executed"}',
            "is_error": True,
        }
        for block in tool_uses
    ]
