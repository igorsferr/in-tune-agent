"""Deterministic grading of eval conversations: no model judges another model.

A case passes when every check holds:
- each listed tool was called;
- each `include` pattern matches some reply and no `exclude` pattern matches any;
- a handoff happened (or didn't) when the case says so;
- grounding: every amount of money the agent wrote (with or without "R$")
  appears in a tool result of that conversation or in the customer's messages.
Patterns are matched against replies lowercased and without accents.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal

from in_tune.agent import Reply
from in_tune.formatting import parse_brl

# Money as written in Brazil: anything after "R$", and also bare amounts with
# cents such as "12x de 183,25" or "PIX 2.089,05", which carry no symbol.
AMOUNT = re.compile(r"R\$\s?\d[\d.]*(?:,\d{1,2})?|(?<![\d.,])\d{1,3}(?:\.\d{3})*,\d{2}(?![\d,])")


def fold(text: str) -> str:
    """Lowercase without accents."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )


def amounts(text: str) -> set[Decimal]:
    return {parse_brl(match) for match in AMOUNT.findall(text)}


@dataclass
class Case:
    id: str
    turns: list[str]
    group: str = ""
    tools: list[str] = field(default_factory=list)
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    handoff: bool | None = None
    critical: bool = False
    now: str | None = None


def ungrounded(turns: list[str], replies: list[Reply]) -> list[Decimal]:
    """Amounts the agent wrote that no tool result and no customer message contains."""
    allowed: set[Decimal] = set().union(*(amounts(t) for t in turns))
    for reply in replies:
        for call in reply.tool_calls:
            allowed |= amounts(json.dumps(call.result, ensure_ascii=False))
    written: set[Decimal] = set().union(*(amounts(r.text) for r in replies))
    return sorted(written - allowed)


def grade(case: Case, replies: list[Reply]) -> list[str]:
    """Failures for one conversation; an empty list means it passed."""
    failures = []
    texts = [fold(r.text) for r in replies]
    called = [c.name for r in replies for c in r.tool_calls]

    failures += [f"tool not called: {tool}" for tool in case.tools if tool not in called]
    for pattern in case.include:
        if not any(re.search(pattern, t, re.MULTILINE) for t in texts):
            failures.append(f"missing: /{pattern}/")
    for pattern in case.exclude:
        if any(re.search(pattern, t, re.MULTILINE) for t in texts):
            failures.append(f"forbidden: /{pattern}/")
    if case.handoff is not None and ("handoff_to_human" in called) != case.handoff:
        failures.append("expected a handoff" if case.handoff else "unexpected handoff")
    failures += [f"ungrounded amount: R$ {a}" for a in ungrounded(case.turns, replies)]
    return failures
