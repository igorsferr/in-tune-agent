"""Hand a conversation over to the human team.

The case has no ticketing system, so a handoff is appended to a local
JSON-lines log that the team would read. The protocol number lets the
customer refer to it later.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from in_tune.tools.store_info import TZ

DEFAULT_LOG = Path(__file__).resolve().parents[3] / "logs" / "handoffs.jsonl"
REASONS = ("complaint", "order_problem", "data_conflict", "data_request", "policy_doubt", "other")


def handoff_to_human(
    reason: str,
    summary: str,
    contact: str | None = None,
    now: datetime | None = None,
    log_path: Path = DEFAULT_LOG,
) -> dict:
    if reason not in REASONS:
        return {"registered": False, "error": f"reason must be one of {list(REASONS)}"}
    now = (now or datetime.now(TZ)).astimezone(TZ)
    protocol = f"EM-{now:%Y%m%d-%H%M%S}"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as log:
        entry = {
            "protocol": protocol,
            "at": now.isoformat(),
            "reason": reason,
            "summary": summary,
            "contact": contact,
        }
        log.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return {"registered": True, "protocol": protocol}
