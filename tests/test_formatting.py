from decimal import Decimal

import pytest

from in_tune.formatting import brl, parse_brl, phone_digits


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("799.9"), "R$ 799,90"),
        (Decimal("11499"), "R$ 11.499,00"),
        (Decimal("323.1"), "R$ 323,10"),
        (Decimal("0.5"), "R$ 0,50"),
        ("1967.18", "R$ 1.967,18"),
    ],
)
def test_brl_formats_brazilian_currency(value, expected):
    assert brl(value) == expected


def test_parse_brl_round_trips():
    assert parse_brl(brl(Decimal("1749"))) == Decimal("1749.00")
    assert parse_brl("R$ 1.299,90") == Decimal("1299.90")


@pytest.mark.parametrize(
    ("text", "expected"),
    [("R$ 799.90", "799.90"), ("R$ 1.299", "1299.00"), ("R$ 35", "35.00")],
)
def test_parse_brl_accepts_other_common_writings(text, expected):
    assert parse_brl(text) == Decimal(expected)


@pytest.mark.parametrize(
    "phone", ["(67) 99812-3456", "67 99812 3456", "+55 (67) 99812-3456", "67998123456"]
)
def test_phone_digits_normalises_common_formats(phone):
    assert phone_digits(phone) == "67998123456"
