import json
import re
from datetime import datetime

from in_tune.tools.handoff import handoff_to_human
from in_tune.tools.store_info import TZ

NOW = datetime(2026, 10, 31, 15, 20, 5, tzinfo=TZ)


def test_registers_a_handoff_with_a_protocol(tmp_path):
    log = tmp_path / "handoffs.jsonl"
    result = handoff_to_human(
        "complaint", "Instrumento chegou riscado", "(67) 99812-3456", now=NOW, log_path=log
    )
    assert result["registered"] is True
    assert re.fullmatch(r"EM-20261031-152005-[0-9A-F]{4}", result["protocol"])
    entry = json.loads(log.read_text(encoding="utf-8"))
    assert entry["reason"] == "complaint"
    assert entry["summary"] == "Instrumento chegou riscado"


def test_appends_instead_of_overwriting(tmp_path):
    log = tmp_path / "handoffs.jsonl"
    first = handoff_to_human("other", "first", now=NOW, log_path=log)
    second = handoff_to_human("other", "second", now=NOW, log_path=log)
    assert len(log.read_text(encoding="utf-8").splitlines()) == 2
    assert first["protocol"] != second["protocol"]  # same second, distinct protocols


def test_rejects_unknown_reasons(tmp_path):
    result = handoff_to_human("urgent!!", "x", log_path=tmp_path / "h.jsonl")
    assert result["registered"] is False
    assert not (tmp_path / "h.jsonl").exists()
