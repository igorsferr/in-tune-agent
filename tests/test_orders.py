from datetime import date

import pytest

from in_tune.store import Store
from in_tune.tools.orders import NOT_FOUND, check_order

TODAY = date(2026, 10, 31)


@pytest.fixture(scope="module")
def store():
    return Store()


def test_owner_sees_the_order_by_phone_in_any_format(store):
    # Order 1 belongs to customer 3, phone (67) 98432-1098.
    for contact in ("(67) 98432-1098", "67984321098", "+55 67 98432 1098"):
        order = check_order(store, 1, contact, TODAY)
        assert order["found"] and order["status"] == "delivered"
    assert order["customer_first_name"] == "Pedro"
    assert order["total"] == "R$ 11.499,00"


def test_owner_sees_the_order_by_email_case_insensitively(store):
    assert check_order(store, 1, "Pedro.Oliveira@JMAIL.com", TODAY)["found"]


def test_wrong_contact_and_unknown_order_look_the_same(store):
    assert check_order(store, 1, "(67) 99999-0000", TODAY) == NOT_FOUND
    assert check_order(store, 999, "(67) 98432-1098", TODAY) == NOT_FOUND
    assert check_order(store, 1, "", TODAY) == NOT_FOUND


def test_shared_email_only_opens_its_own_customers_orders(store):
    # bruno.martins@jmail.com belongs to customers 11 and 43; order 10 is customer 11's.
    assert check_order(store, 10, "bruno.martins@jmail.com", TODAY)["found"]


def test_stored_total_is_reported_even_when_items_disagree(store):
    # Order 3: two items at R$ 1.749 would be R$ 3.498; the record says R$ 3.450.
    assert check_order(store, 3, "(67) 99678-9012", TODAY)["total"] == "R$ 3.450,00"


def test_overdue_shipment_needs_a_human(store):
    order = check_order(store, 8, "(67) 99654-7821", TODAY)
    assert order["status"] == "shipped"
    assert order["tracking_code"] == "BRJL5544332BR"
    assert order["needs_human"].startswith("overdue")


def test_old_pending_order_is_stalled_but_a_fresh_one_is_not(store):
    assert check_order(store, 13, "(67) 99456-7890", TODAY)["needs_human"].startswith("stalled")
    assert "needs_human" not in check_order(store, 13, "(67) 99456-7890", date(2026, 3, 15))


def test_cancelled_order_explains_why(store):
    order = check_order(store, 18, "(67) 98098-7654", TODAY)
    assert order["status"] == "cancelled"
    assert order["notes"] == "Item fora de estoque no momento do pedido"
    assert "needs_human" not in order
