import pytest

from in_tune.quality import conflicts
from in_tune.store import Store


@pytest.fixture(scope="module")
def store():
    return Store()


def test_flags_exactly_the_products_that_contradict_themselves(store):
    flagged = {pid for pid, product in store.products.items() if conflicts(product)}
    assert flagged == {135, 136, 137, 139, 140, 142, 144}


def test_reports_each_conflicting_attribute(store):
    bass = {c["attribute"]: c for c in conflicts(store.products[137])}
    assert bass["brand"] == {"attribute": "brand", "name": "Yamaha", "description": "Ibanez"}
    assert bass["strings"] == {"attribute": "strings", "description": "5", "specs": "4"}

    synth = {c["attribute"]: c for c in conflicts(store.products[142])}
    assert synth["keys"] == {"attribute": "keys", "description": "88", "specs": "61"}


def test_model_names_identify_the_maker(store):
    # "Contrabaixo Precision" is a Fender model, sold here as an Ibanez.
    assert conflicts(store.products[136])[0]["description"] == "Fender"
    # Consistent rows in the same block are left alone.
    for pid in (138, 141, 143):
        assert conflicts(store.products[pid]) == []
