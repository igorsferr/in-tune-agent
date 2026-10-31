from decimal import Decimal

import pytest

from in_tune.store import Store
from in_tune.tools.payments import _installment_allowed, quote_payment


@pytest.fixture(scope="module")
def store():
    return Store()


@pytest.mark.parametrize(
    ("total", "count", "allowed"),
    [
        ("159.90", 3, True),  # R$ 53,30 >= R$ 50
        ("140.00", 3, False),  # R$ 46,67 < R$ 50
        ("480.00", 6, True),  # R$ 80,00 >= R$ 80
        ("349.90", 6, False),  # R$ 58,32 < R$ 80 (order 9 broke this rule)
        ("1200.00", 12, True),  # R$ 100,00 >= R$ 100
        ("459.90", 12, False),  # R$ 38,33 < R$ 100 (order 18 broke this rule)
        ("10.00", 1, True),  # paying in full is always allowed
    ],
)
def test_installment_minimums_follow_section_3_1(total, count, allowed):
    assert _installment_allowed(Decimal(total), count) is allowed


def test_regular_item_gets_pix_discount_and_all_installments(store):
    quote = quote_payment(store, [95])  # Takamine GD20, R$ 2.199
    assert quote["total"] == "R$ 2.199,00"
    assert quote["pix"] == "R$ 2.089,05"
    assert [o["installments"] for o in quote["credit_card"]] == list(range(1, 13))
    assert quote["credit_card"][-1]["each"] == "R$ 183,25"
    assert quote["mixed_payment_allowed"] is True
    assert quote["shipping_campo_grande_metro"] == "free"


def test_promotional_item_gets_no_extra_pix_discount(store):
    quote = quote_payment(store, [121])  # Ohana CK-20, R$ 549 with 20% off
    assert quote["total"] == "R$ 439,20"
    assert quote["pix"] == "R$ 439,20"
    assert quote["note"] == "PIX discount not applied to promotional items"


def test_cheap_item_has_few_installments_and_pays_metro_shipping(store):
    quote = quote_payment(store, [119])  # Shelby ukulele, R$ 159,90
    assert [o["installments"] for o in quote["credit_card"]] == [1, 2, 3]
    assert quote["shipping_campo_grande_metro"] == "R$ 35,00"
    assert quote["mixed_payment_allowed"] is False


def test_repeated_id_counts_as_quantity(store):
    assert quote_payment(store, [119, 119])["total"] == "R$ 319,80"


def test_unknown_product_is_an_error(store):
    assert "error" in quote_payment(store, [999])
    assert "error" in quote_payment(store, [])
