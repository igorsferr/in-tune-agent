from datetime import datetime

import pytest

from in_tune.policies import Policies
from in_tune.store import Store
from in_tune.toolbox import INPUTS, Toolbox
from in_tune.tools.store_info import TZ

NOW = datetime(2026, 10, 31, 15, 0, tzinfo=TZ)


@pytest.fixture(scope="module")
def toolbox(tmp_path_factory):
    log = tmp_path_factory.mktemp("logs") / "handoffs.jsonl"
    return Toolbox(Store(), Policies(), clock=lambda: NOW, handoff_log=log)


def test_every_tool_has_a_definition_in_a_fixed_order(toolbox):
    definitions = toolbox.definitions()
    assert [d["name"] for d in definitions] == list(INPUTS)
    assert all(d["description"] and d["input_schema"]["type"] == "object" for d in definitions)
    assert definitions == toolbox.definitions()  # identical every time, so it caches


def test_category_choices_come_from_the_data(toolbox):
    search = toolbox.definitions()[0]["input_schema"]
    assert "Violões" in search["properties"]["category"]["anyOf"][0]["enum"]


def test_string_ids_are_coerced(toolbox):
    result, is_error = toolbox.run("check_order", {"order_id": "1", "contact": "(67) 98432-1098"})
    assert not is_error and result["found"]
    result, is_error = toolbox.run("get_product", {"product_id": "95"})
    assert not is_error and result["name"] == "Takamine GD20 Dreadnought Natural"


@pytest.mark.parametrize(
    ("name", "raw"),
    [
        ("check_order", {"order_id": 1}),  # missing contact
        ("search_products", {"max_price": "abc"}),
        ("quote_payment", {"product_ids": []}),
        ("handoff_to_human", {"reason": "urgent", "summary": "x"}),
        ("get_policy", {"section": "4", "extra": True}),
        ("no_such_tool", {}),
    ],
)
def test_bad_calls_become_error_results(toolbox, name, raw):
    result, is_error = toolbox.run(name, raw)
    assert is_error and "error" in result


def test_tool_level_errors_are_flagged(toolbox):
    result, is_error = toolbox.run("search_products", {"category": "Guitars"})
    assert is_error and "available_categories" in result


def test_a_crashing_tool_does_not_raise(toolbox, monkeypatch):
    monkeypatch.setattr(toolbox, "_call", lambda *_: 1 / 0)
    result, is_error = toolbox.run("store_status", {})
    assert is_error and result["error"].startswith("ZeroDivisionError")


def test_clock_drives_time_dependent_tools(toolbox):
    status, _ = toolbox.run("store_status", {})
    assert status["now"] == "sábado, 31/10/2026, 15:00"


def test_store_status_takes_a_date_as_text(toolbox):
    status, is_error = toolbox.run("store_status", {"day": "2026-11-02"})
    assert not is_error
    assert status["day"]["hours"] == "closed (Finados)"
