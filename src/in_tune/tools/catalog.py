"""Product search and product details (PLAN §4: status, promotions, PIX, conflicts)."""

from __future__ import annotations

import difflib
import unicodedata
from decimal import Decimal

from in_tune.formatting import brl, to_cents
from in_tune.quality import conflicts
from in_tune.store import Product, Store

PIX_DISCOUNT = Decimal("0.05")


def _fold(text: str) -> str:
    """Lowercase without accents, so 'violão' matches 'Violao'."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", text.casefold()) if not unicodedata.combining(c)
    )


def _key(text: str) -> str:
    """Matching form: folded, hyphens dropped, so "GD-20" matches "GD20"."""
    return _fold(text).replace("-", "")


def _haystack(store: Store, product: Product) -> str:
    return _key(
        " ".join(
            [product.name, product.description, store.categories[product.category_id].name]
            + list(product.specs.values())
        )
    )


def _correct_spelling(store: Store, query: str) -> str:
    """Replace words found nowhere in the catalog by the closest catalog word
    ("takamini" -> "takamine", "ukelele" -> "ukulele"). Used only when the query
    as typed matches nothing.

    Words with a digit are model codes, and a code one character away is a
    different product ("314ce" is not the "214ce"), so they are never changed.
    """
    text = " ".join(_haystack(store, p) for p in store.products.values())
    vocabulary = sorted(set(text.split()))
    words = []
    for word in _key(query).split():
        if word in text or any(c.isdigit() for c in word):
            words.append(word)
            continue
        close = difflib.get_close_matches(word, vocabulary, n=1, cutoff=0.85)
        words.append(close[0] if close else word)
    return " ".join(words)


def _similar_names(store: Store, name: str) -> list[str]:
    """Product names that start like the query, for a "did you mean" question."""
    query = _key(name)
    scored = [
        (difflib.SequenceMatcher(None, query, _key(p.name)[: len(query) + 2]).ratio(), p.name)
        for p in store.products.values()
    ]
    return [n for score, n in sorted(scored, reverse=True)[:3] if score >= 0.75]


def availability(product: Product) -> str:
    if product.status == "discontinued":
        return "discontinued"
    if product.status == "coming_soon":
        return "coming_soon"
    return "available" if product.stock_quantity > 0 else "out_of_stock"


def final_price(store: Store, product: Product) -> Decimal:
    """Price the customer pays: the active promotion applied, if there is one."""
    promo = store.active_promotion(product.product_id)
    if promo is None:
        return product.price_brl
    return to_cents(product.price_brl * (100 - promo.discount_percent) / 100)


def card(store: Store, product: Product) -> dict:
    promo = store.active_promotion(product.product_id)
    result = {
        "product_id": product.product_id,
        "name": product.name,
        "category": store.categories[product.category_id].name,
        "availability": availability(product),
        "price": brl(product.price_brl),
    }
    if promo:
        # Policy §6.2: show the original price, the % off and the final price;
        # the PIX discount does not stack on a promotional price.
        result["promotion"] = {
            "campaign": promo.description,
            "discount": f"{promo.discount_percent}%",
            "final_price": brl(final_price(store, product)),
        }
    elif product.sellable:
        result["pix_price"] = brl(product.price_brl * (1 - PIX_DISCOUNT))
    if found := conflicts(product):
        result["data_warnings"] = found
    return result


def _matches(product: Product, store: Store, query: str) -> bool:
    haystack = _haystack(store, product)
    return all(token in haystack for token in _key(query).split())


def _names_match(product: Product, query: str) -> bool:
    """Every query word is a whole word of the product name ("D-28" is not "D-28E")."""
    words = _key(product.name).split()
    return all(token in words for token in _key(query).split())


def _by_name(store: Store, name: str | None) -> list[Product]:
    candidates = [p for p in store.products.values() if name and _matches(p, store, name)]
    # Prefer products whose name holds every word asked for.
    exact = [p for p in candidates if _names_match(p, name)]
    return exact or candidates


def _category_id(store: Store, category: str) -> int | None:
    folded = _fold(category)
    return next((cid for cid, c in store.categories.items() if _fold(c.name) == folded), None)


def search_products(store: Store, query: str | None = None, **filters) -> dict:
    """Products matching every given filter, cheapest first.

    Price filters apply to the price the customer pays (promotion included).
    An unknown category is an error listing the valid ones, never "no results".
    A misspelled query that matches nothing is retried with corrected spelling,
    and the result says so.
    """
    found = _search(store, query, **filters)
    if query and found.get("total_matches") == 0:
        corrected = _correct_spelling(store, query)
        if corrected != _key(query):
            found = _search(store, corrected, **filters)
            found["note"] = f"nothing matched {query!r}; showing results for {corrected!r}"
    return found


def _search(
    store: Store,
    query: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    available_only: bool = True,
    limit: int = 20,
) -> dict:
    category_id = _category_id(store, category) if category else None
    if category and category_id is None:
        return {
            "error": f"unknown category {category!r}",
            "available_categories": [c.name for c in store.categories.values()],
        }
    results = []
    for product in store.products.values():
        price = final_price(store, product)
        if available_only and not product.sellable:
            continue
        if category_id is not None and product.category_id != category_id:
            continue
        if min_price is not None and price < Decimal(str(min_price)):
            continue
        if max_price is not None and price > Decimal(str(max_price)):
            continue
        if query and not _matches(product, store, query):
            continue
        results.append((price, product))
    results.sort(key=lambda pair: (pair[0], pair[1].product_id))
    found = {
        "total_matches": len(results),
        "results": [card(store, product) for _, product in results[:limit]],
    }
    if len(results) > limit:
        found["note"] = f"showing the {limit} cheapest; narrow the search to see others"
    return found


def get_product(store: Store, product_id: int | None = None, name: str | None = None) -> dict:
    """One product with full details, by id or by name. Unavailable products
    come with up to 3 available alternatives from the same category (§7.3)."""
    note = None
    if product_id is not None:
        candidates = [store.products[product_id]] if product_id in store.products else []
    else:
        candidates = _by_name(store, name)
        if not candidates and name:
            corrected = _correct_spelling(store, name)
            if corrected != _key(name):
                candidates = _by_name(store, corrected)
                note = f"nothing matched {name!r}; showing results for {corrected!r}"
    if not candidates:
        result = {"found": False}
        if name and (similar := _similar_names(store, name)):
            # Names only: a near miss may be another product, so ask before quoting.
            result["did_you_mean"] = similar
        return result
    if len(candidates) > 1:
        result = {
            "found": False,
            "ambiguous": True,
            "message": "Several products match; ask the customer which one.",
            "candidates": [card(store, p) for p in candidates[:5]],
        }
        if note:
            result["note"] = note
        return result

    product = candidates[0]
    result = {"found": True, **card(store, product)}
    if note:
        result["note"] = note
    result["description"] = product.description
    result["specs"] = product.specs
    if not product.sellable:
        same_category = [
            p
            for p in store.products.values()
            if p.category_id == product.category_id and p.sellable
        ]
        # Most similar first (§7.3 "alternativas semelhantes"): same string type
        # and electronics, then the closest price.
        same_category.sort(
            key=lambda p: (
                p.specs.get("strings") != product.specs.get("strings"),
                p.specs.get("electronics") != product.specs.get("electronics"),
                abs(final_price(store, p) - product.price_brl),
            )
        )
        result["alternatives"] = [card(store, p) for p in same_category[:3]]
    return result
