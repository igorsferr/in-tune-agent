import pytest

from in_tune.store import Store
from in_tune.tools.catalog import get_product, search_products


@pytest.fixture(scope="module")
def store():
    return Store()


def test_brief_sample_acoustic_guitars_up_to_1000(store):
    # "Quais opções de violões disponíveis custando até R$1000?"
    found = search_products(store, category="Violões", max_price=1000, limit=50)
    ids = {r["product_id"] for r in found["results"]}
    assert found["total_matches"] == 12
    assert 96 not in ids  # active but out of stock
    assert 113 not in ids  # discontinued
    prices = [r.get("promotion", {}).get("final_price", r["price"]) for r in found["results"]]
    assert prices[0] == "R$ 429,90"  # cheapest first


def test_brief_sample_takamine_price_ignores_inactive_promotion(store):
    # "Quanto custa o Takamine GD20?" has an inactive 12% "Oferta Especial".
    takamine = get_product(store, name="Takamine GD20")
    assert takamine["found"]
    assert takamine["price"] == "R$ 2.199,00"
    assert "promotion" not in takamine
    assert takamine["pix_price"] == "R$ 2.089,05"


def test_active_promotion_shows_original_discount_and_final_price(store):
    ohana = get_product(store, product_id=121)
    assert ohana["price"] == "R$ 549,00"
    assert ohana["promotion"] == {
        "campaign": "Desconto Exclusivo",
        "discount": "20%",
        "final_price": "R$ 439,20",
    }
    assert "pix_price" not in ohana  # PIX does not stack on promotions


def test_price_filter_uses_promotional_price(store):
    # Crafter HT-100 lists at R$ 2.399 but costs R$ 1.967,18 with 18% off.
    found = search_products(store, query="Crafter HT-100", max_price=2000)
    assert [r["product_id"] for r in found["results"]] == [90]


@pytest.mark.parametrize(
    ("product_id", "availability"),
    [(96, "out_of_stock"), (113, "discontinued"), (130, "coming_soon"), (136, "discontinued")],
)
def test_unavailable_products_come_with_available_alternatives(store, product_id, availability):
    product = get_product(store, product_id=product_id)
    assert product["availability"] == availability
    assert product["alternatives"]
    assert all(alt["availability"] == "available" for alt in product["alternatives"])


def test_conflicting_attributes_are_reported_not_resolved(store):
    bass = get_product(store, product_id=137)
    assert {"attribute": "strings", "description": "5", "specs": "4"} in bass["data_warnings"]


def test_empty_category_returns_nothing(store):
    assert search_products(store, category="Cordas Orquestrais")["total_matches"] == 0


def test_search_ignores_accents_and_case(store):
    assert search_products(store, query="VIOLAO 7 cordas")["total_matches"] == 4


def test_unknown_and_ambiguous_names(store):
    assert get_product(store, name="Steinway")["found"] is False
    assert len(get_product(store, name="Martin D-28")["ambiguous"]) == 2
