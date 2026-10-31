"""Product search and product details (PLAN §4: status, promotions, PIX, conflicts)."""

from __future__ import annotations

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
    haystack = _fold(
        " ".join(
            [product.name, product.description, store.categories[product.category_id].name]
            + list(product.specs.values())
        )
    )
    return all(token in haystack for token in _fold(query).split())


def _names_match(product: Product, query: str) -> bool:
    """Every query word is a whole word of the product name ("D-28" is not "D-28E")."""
    words = _fold(product.name).split()
    return all(token in words for token in _fold(query).split())


def _category_id(store: Store, category: str) -> int | None:
    folded = _fold(category)
    return next((cid for cid, c in store.categories.items() if _fold(c.name) == folded), None)


def search_products(
    store: Store,
    query: str | None = None,
    category: str | None = None,
    min_price: float | None = None,
    max_price: float | None = None,
    available_only: bool = True,
    limit: int = 20,
) -> dict:
    """Products matching every given filter, cheapest first.

    Price filters apply to the price the customer pays (promotion included).
    An unknown category is an error listing the valid ones, never "no results".
    """
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
    if product_id is not None:
        candidates = [store.products[product_id]] if product_id in store.products else []
    else:
        candidates = [p for p in store.products.values() if name and _matches(p, store, name)]
        # Prefer products whose name holds every word asked for.
        exact = [p for p in candidates if _names_match(p, name)]
        candidates = exact or candidates
    if not candidates:
        return {"found": False}
    if len(candidates) > 1:
        return {
            "found": False,
            "ambiguous": True,
            "message": "Several products match; ask the customer which one.",
            "candidates": [card(store, p) for p in candidates[:5]],
        }

    product = candidates[0]
    result = {"found": True, **card(store, product)}
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
