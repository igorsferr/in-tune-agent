import json
import re
from decimal import Decimal
from pathlib import Path

import pytest

from in_tune.agent import Reply, ToolCall
from in_tune.grading import Case, amounts, fold, grade, ungrounded

CASES = Path(__file__).resolve().parents[1] / "evals" / "cases.json"


def reply(text, *calls):
    return Reply(text, list(calls), "end_turn")


def call(name, result):
    return ToolCall(name, {}, result, False)


PRODUCT = call("get_product", {"price": "R$ 2.199,00", "pix_price": "R$ 2.089,05"})


def test_passes_when_every_check_holds():
    case = Case("c", ["quanto custa?"], tools=["get_product"], include=["2\\.199,00"])
    assert grade(case, [reply("Custa R$ 2.199,00, ou R$ 2.089,05 no PIX.", PRODUCT)]) == []


def test_patterns_ignore_case_and_accents():
    case = Case("c", ["?"], include=["nao temos violino"])
    assert grade(case, [reply("Não temos VIOLINO, infelizmente.")]) == []


def test_each_failure_is_named():
    case = Case(
        "c",
        ["?"],
        tools=["check_order"],
        include=["protocolo"],
        exclude=["vao te ligar"],
        handoff=True,
    )
    failures = grade(case, [reply("Pronto! Eles vão te ligar.")])
    assert failures == [
        "tool not called: check_order",
        "missing: /protocolo/",
        "forbidden: /vao te ligar/",
        "expected a handoff",
    ]


def test_an_amount_no_tool_returned_is_ungrounded():
    invented = reply("Com o desconto especial fica R$ 1.099,50.", PRODUCT)
    assert ungrounded(["quanto custa?"], [invented]) == [Decimal("1099.50")]


@pytest.mark.parametrize(
    "text",
    ["12x de 183,25", "no PIX fica 2.089,05", "R$183,25", "parcelas de R$ 1.099,50"],
)
def test_amounts_without_the_currency_symbol_are_checked_too(text):
    grounded = call("quote_payment", {"each": "R$ 183,25", "pix": "R$ 2.089,05"})
    found = ungrounded(["?"], [reply(text, grounded)])
    assert found == ([] if "1.099,50" not in text else [Decimal("1099.50")])


def test_numbers_that_are_not_money_are_ignored():
    text = "Entrega em 1 a 3 dias, escala de 650mm, 12x sem juros, 5% no PIX, até 28/02/2026."
    assert amounts(text) == set()


def test_amounts_from_the_customer_and_any_earlier_turn_are_grounded():
    first = reply("Custa R$ 2.199,00.", PRODUCT)
    second = reply("Até R$1000 não tenho esse modelo; ele custa R$ 2.199,00.")
    assert ungrounded(["quanto custa?", "tem até R$1000?"], [first, second]) == []


def test_amounts_inside_policy_text_are_grounded():
    policy = call("get_policy", {"sections": [{"text": "Frete grátis acima de R$ 500,00."}]})
    assert ungrounded(["frete?"], [reply("Acima de R$ 500,00 o frete é grátis.", policy)]) == []


def test_eval_file_is_well_formed():
    data = json.loads(CASES.read_text(encoding="utf-8"))
    cases = [Case(**c) for c in data["cases"]]
    assert len({c.id for c in cases}) == len(cases)
    for case in cases:
        for pattern in case.include + case.exclude:
            re.compile(pattern)
            # Replies are folded before matching, so patterns must hold no accents
            # and no capital letters (regex escapes such as \W excepted).
            letters = re.sub(r"\\[A-Za-z]", "", pattern)
            assert letters == fold(letters), f"{case.id}: pattern must be folded: {pattern}"


@pytest.mark.parametrize("text", ["Pode sim! Vou te ligar amanhã.", "ok"])
def test_exclude_anchors_work_per_line(text):
    case = Case("c", ["?"], exclude=["^ok\\W*$"])
    assert bool(grade(case, [reply(text)])) == (text == "ok")
