from datetime import date
from decimal import Decimal

import pytest

from in_tune.store import Store


@pytest.fixture(scope="module")
def store():
    return Store()


def test_loads_every_table(store):
    assert len(store.categories) == 9
    assert len(store.products) == 65
    assert len(store.customers) == 50
    assert len(store.orders) == 20
    assert len(store.order_items) == 22
    assert len(store.promotions) == 25


def test_product_fields_are_typed(store):
    martin = store.products[93]
    assert martin.price_brl == Decimal("11499")
    assert martin.specs["top"] == "Sitka Spruce Sólido"
    assert martin.created_at == date(2023, 1, 20)


def test_empty_cells_become_none(store):
    pending = store.orders[13]
    assert pending.tracking_code is None
    assert pending.estimated_delivery is None
    assert pending.notes is None


def test_sellable_requires_active_status_and_stock(store):
    assert store.products[81].sellable  # active, stock 12
    assert not store.products[96].sellable  # active, stock 0
    assert not store.products[136].sellable  # discontinued, stock 13
    assert not store.products[130].sellable  # coming_soon, stock 2


def test_only_active_promotions_apply(store):
    with_active = {pid for pid in store.products if store.active_promotion(pid)}
    assert with_active == {90, 94, 121, 127}
    assert store.active_promotion(93) is None  # two inactive promotions only


def test_items_of_an_order(store):
    assert [i.product_id for i in store.items_of(15)] == [82, 106]
