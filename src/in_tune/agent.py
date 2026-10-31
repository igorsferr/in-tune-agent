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

DEFAULT_MODEL = "claude-opus-5-5"
# Models that support server-side refusal fallback (`fallbacks: "default"`).
FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5"}
FALLBACK_BETA = "server-side-fallback-2026-07-01"
MAX_STEPS = 8  # model requests per customer message
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
        }
        if self.model in FALLBACK_MODELS:
            kwargs |= {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return self.client.beta.messages.create(**kwargs)

    def send(self, text: str) -> Reply:
        self.messages.append({"role": "user", "content": text})
        calls: list[ToolCall] = []
        usage: dict[str, int] = {}
        for _ in range(self.max_steps):
            response = self._request()
            for key in ("input_tokens", "output_tokens", "cache_read_input_tokens"):
                usage[key] = usage.get(key, 0) + (getattr(response.usage, key, 0) or 0)

            if response.stop_reason == "refusal":
                # Keep the history valid for the next message: no empty assistant turn.
                self.messages.append({"role": "assistant", "content": SORRY})
                return Reply(SORRY, calls, "refusal", usage)

            self.messages.append({"role": "assistant", "content": response.content})
            tool_uses = [b for b in response.content if b.type == "tool_use"]
            if response.stop_reason != "tool_use" or not tool_uses:
                reply = "\n".join(b.text for b in response.content if b.type == "text").strip()
                return Reply(reply or SORRY, calls, response.stop_reason, usage)

            results = []
            for block in tool_uses:
                result, is_error = self.toolbox.run(block.name, block.input)
                calls.append(ToolCall(block.name, block.input, result, is_error))
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                        "is_error": is_error,
                    }
                )
            # All results of one step go back together, in one user message.
            self.messages.append({"role": "user", "content": results})

        # Too many steps: close the turn with text so the history stays valid.
        self.messages.append({"role": "assistant", "content": SORRY})
        return Reply(SORRY, calls, "max_steps", usage)
