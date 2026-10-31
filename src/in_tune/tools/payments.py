"""Payment options for a purchase, under the manual's rules (§3, §3.1, §5.1, §6.2)."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from in_tune.formatting import brl, to_cents
from in_tune.store import Store
from in_tune.tools.catalog import PIX_DISCOUNT, availability, final_price

# §3.1 wins over the §3 summary table (DATA_AUDIT #18): minimum installment by count.
MIN_INSTALLMENT = [(3, Decimal("50")), (6, Decimal("80")), (12, Decimal("100"))]
MIXED_PAYMENT_ABOVE = Decimal("2000")
# §5.1 says "acima de R$ 500"; exactly R$ 500 is read in the customer's favour.
FREE_METRO_SHIPPING_FROM = Decimal("500")
METRO_SHIPPING_FEE = Decimal("35")


def _installment_allowed(total: Decimal, count: int) -> bool:
    if count == 1:
        return True
    minimum = next(m for limit, m in MIN_INSTALLMENT if count <= limit)
    return total / count >= minimum


def quote_payment(store: Store, product_ids: list[int]) -> dict:
    """Totals per payment method for the given products (repeat an id for quantity)."""
    unknown = [pid for pid in product_ids if pid not in store.products]
    if unknown or not product_ids:
        return {"error": f"unknown product ids: {unknown}" if unknown else "no products given"}
    # Only what can actually be bought gets a quote, and never more than in stock.
    problems = []
    for pid, quantity in Counter(product_ids).items():
        product = store.products[pid]
        if not product.sellable:
            problems.append({"product_id": pid, "availability": availability(product)})
        elif quantity > product.stock_quantity:
            problems.append(
                {"product_id": pid, "requested": quantity, "in_stock": product.stock_quantity}
            )
    if problems:
        return {"error": "some items cannot be bought as requested", "items": problems}

    products = [store.products[pid] for pid in product_ids]
    total = sum((final_price(store, p) for p in products), Decimal(0))
    # §6.2: PIX gives 5% off list price, but never on top of a promotion.
    pix_total = sum(
        (
            final_price(store, p)
            if store.active_promotion(p.product_id)
            else to_cents(p.price_brl * (1 - PIX_DISCOUNT))
            for p in products
        ),
        Decimal(0),
    )
    result = {
        "items": [p.name for p in products],
        "total": brl(total),
        "pix": brl(pix_total),
        "debit_card": brl(total),
        "boleto": brl(total) + " (clears in up to 3 business days)",
        "credit_card": [
            {"installments": n, "each": brl(total / n)}
            for n in range(1, 13)
            if _installment_allowed(total, n)
        ],
        "mixed_payment_allowed": total > MIXED_PAYMENT_ABOVE,
        "shipping_campo_grande_metro": "free"
        if total >= FREE_METRO_SHIPPING_FROM
        else brl(METRO_SHIPPING_FEE),
        "shipping_elsewhere": (
            "cost depends on the CEP and cannot be quoted here; delivery times in policy §5.2"
        ),
    }
    if any(store.active_promotion(p.product_id) for p in products):
        result["note"] = "PIX discount not applied to promotional items"
    return result
