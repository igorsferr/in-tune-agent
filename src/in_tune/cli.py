"""Chat with the store's agent in the terminal: `uv run in-tune`."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

import anthropic
from dotenv import load_dotenv

from in_tune.agent import DEFAULT_MODEL, Agent
from in_tune.policies import Policies
from in_tune.store import Store
from in_tune.toolbox import Toolbox
from in_tune.tools.store_info import TZ

NO_KEY = (
    "Nenhuma credencial da Anthropic encontrada. Defina ANTHROPIC_API_KEY no ambiente "
    "ou num arquivo .env (veja .env.example)."
)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Atendimento virtual da Empório da Música.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"default: {DEFAULT_MODEL}")
    parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"])
    parser.add_argument(
        "--now",
        type=datetime.fromisoformat,
        help="fixed Campo Grande time, e.g. 2026-11-03T10:00 (default: the real clock)",
    )
    parser.add_argument("--show-tools", action="store_true", help="print each tool call")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    sys.stdout.reconfigure(encoding="utf-8")
    args = _parse_args(argv)
    now = None
    if args.now:  # read as Campo Grande time; an explicit offset is converted to it
        now = args.now.replace(tzinfo=TZ) if args.now.tzinfo is None else args.now.astimezone(TZ)
    clock = (lambda: now) if now else (lambda: datetime.now(TZ))

    policies = Policies()
    agent = Agent(Toolbox(Store(), policies, clock), policies, args.model, args.effort)
    print(f"Empório da Música · atendimento virtual ({args.model}). Digite 'sair' para encerrar.")

    while True:
        try:
            text = input("\nvocê > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not text:
            continue
        if text.casefold() in {"sair", "exit", "quit"}:
            return 0
        print("Empório está digitando…", end="\r", flush=True)
        try:
            reply = agent.send(text)
        except KeyboardInterrupt:
            print()
            return 0
        except TypeError as e:
            # The SDK raises TypeError("Could not resolve authentication method...")
            # when no credential is configured at all; tests pin that message.
            if "authentication" not in str(e):
                raise
            print(NO_KEY)
            return 1
        except anthropic.AuthenticationError:
            print(NO_KEY)
            return 1
        except anthropic.APIError as e:
            # The agent has already put its history back in a valid state.
            print(f"[erro ao falar com o modelo: {e}] Tente de novo.")
            continue
        if args.show_tools:
            for call in reply.tool_calls:
                mark = " (erro)" if call.is_error else ""
                print(f"  · {call.name}({json.dumps(call.input, ensure_ascii=False)}){mark}")
        print(f"\nEmpório > {reply.text}")


if __name__ == "__main__":
    sys.exit(main())
