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


def test_a_long_list_says_it_was_cut(store):
    found = search_products(store, category="Violões")
    assert found["total_matches"] == 33 and len(found["results"]) == 20
    assert "narrow the search" in found["note"]
    assert "note" not in search_products(store, category="Violões", max_price=1000)


def test_empty_category_returns_nothing(store):
    assert search_products(store, category="Cordas Orquestrais")["total_matches"] == 0


def test_unknown_category_is_an_error_not_an_empty_shelf(store):
    for category in ("Violão", "guitarra", "Guitars"):
        found = search_products(store, category=category)
        assert "error" in found
        assert "Violões" in found["available_categories"]


def test_category_ignores_accents_and_case(store):
    # 35 acoustic guitars, minus 96 (out of stock) and 113 (discontinued).
    assert search_products(store, category="VIOLOES")["total_matches"] == 33


def test_search_ignores_accents_and_case(store):
    accented = search_products(store, query="Giannini Violão")
    plain = search_products(store, query="giannini VIOLAO")
    assert accented == plain
    assert {r["product_id"] for r in plain["results"]} == {84, 88, 101, 110}


def test_a_full_model_name_finds_that_product_only(store):
    # "D-28" must not also match the "D-28E".
    assert get_product(store, name="Martin D-28")["product_id"] == 93
    assert get_product(store, name="Martin D-28E")["product_id"] == 108


def test_unknown_and_ambiguous_names(store):
    assert get_product(store, name="Steinway")["found"] is False
    ambiguous = get_product(store, name="Martin")
    assert ambiguous["ambiguous"] is True
    assert {c["product_id"] for c in ambiguous["candidates"]} == {93, 108}


def test_no_pix_price_for_products_that_cannot_be_bought(store):
    assert "pix_price" not in get_product(store, product_id=113)  # discontinued
    assert "pix_price" not in get_product(store, product_id=96)  # out of stock


def test_alternatives_prefer_the_same_kind_of_instrument(store):
    # 96 is a steel-string acoustic without electronics.
    alternatives = get_product(store, product_id=96)["alternatives"]
    for alt in alternatives:
        specs = get_product(store, product_id=alt["product_id"])["specs"]
        assert specs["strings"] == "steel" and specs["electronics"] == "no"


@pytest.mark.parametrize("name", ["takamini gd20", "Takamine GD-20", "takamine gd 20"])
def test_misspelled_or_hyphenated_model_names_still_find_the_product(store, name):
    product = get_product(store, name=name)
    assert product["found"] and product["product_id"] == 95


def test_a_spelling_correction_is_reported(store):
    assert "takamine" in get_product(store, name="takamini gd20")["note"]
    found = search_products(store, query="ukelele")
    assert found["total_matches"] == 14 and "ukulele" in found["note"]


def test_correct_spelling_is_left_alone(store):
    assert "note" not in get_product(store, name="Takamine GD20")
    assert "note" not in search_products(store, query="ukulele")


def test_nonsense_is_still_not_found(store):
    assert get_product(store, name="xyzzy 3000")["found"] is False
    assert search_products(store, query="xyzzy")["total_matches"] == 0
