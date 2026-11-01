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
        # Tier boundaries: 3 -> 4 and 6 -> 7 installments.
        ("300.00", 3, True),  # 3 x R$ 100 (minimum R$ 50)
        ("300.00", 4, False),  # 4 x R$ 75 (minimum R$ 80)
        ("600.00", 6, True),  # 6 x R$ 100 (minimum R$ 80)
        ("600.00", 7, False),  # 7 x R$ 85,71 (minimum R$ 100)
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


@pytest.mark.parametrize(
    ("price", "mixed", "shipping"),
    [
        ("2000.00", False, "free"),  # §3.1 says "acima de R$ 2.000": exactly 2.000 is not above
        ("2000.01", True, "free"),
        ("500.00", False, "free"),  # §5.1, read in the customer's favour at exactly 500
        ("499.99", False, "R$ 35,00"),
    ],
)
def test_mixed_payment_and_free_shipping_boundaries(store, monkeypatch, price, mixed, shipping):
    # No catalog item costs exactly these amounts, so the price is fixed here.
    monkeypatch.setattr("in_tune.tools.payments.final_price", lambda *_: Decimal(price))
    quote = quote_payment(store, [119])
    assert quote["mixed_payment_allowed"] is mixed
    assert quote["shipping_campo_grande_metro"] == shipping


def test_a_no_comes_with_the_rule_behind_it(store):
    # A "no" for one cheap item must not read as "the store never allows it".
    quote = quote_payment(store, [119])
    assert "above R$ 2.000,00" in quote["mixed_payment_rule"]
    assert "R$ 500,00 or more" in quote["shipping_rule"]


def test_repeated_id_counts_as_quantity(store):
    assert quote_payment(store, [119, 119])["total"] == "R$ 319,80"


def test_items_that_cannot_be_bought_are_not_quoted(store):
    quote = quote_payment(store, [96, 130, 136])  # out of stock, coming soon, discontinued
    assert "error" in quote
    assert [i["availability"] for i in quote["items"]] == [
        "out_of_stock",
        "coming_soon",
        "discontinued",
    ]


def test_quantity_is_capped_at_stock(store):
    quote = quote_payment(store, [90] * 4)  # Crafter HT-100: 3 in stock
    assert quote["items"] == [{"product_id": 90, "requested": 4, "in_stock": 3}]
    assert "error" not in quote_payment(store, [90] * 3)


def test_unknown_product_is_an_error(store):
    assert "error" in quote_payment(store, [999])
    assert "error" in quote_payment(store, [])
