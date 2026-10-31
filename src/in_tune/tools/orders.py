"""Order lookup, shown only to the order's owner (PLAN §4, DATA_AUDIT #10-12)."""

from __future__ import annotations

from datetime import date

from in_tune.formatting import brl, phone_digits
from in_tune.store import Store

# An order not dispatched after this many days is treated as stalled.
STALLED_AFTER_DAYS = 7
NOT_FOUND = {
    "found": False,
    "message": (
        "No order matches this number and contact. Ask the customer to check both, "
        "or to use the phone number registered on the order."
    ),
}


def _owns(store: Store, customer_id: int, contact: str | None) -> bool:
    contact = (contact or "").strip()
    if "@" in contact:
        # An e-mail identifies a customer only if no one else uses it
        # (bruno.martins@jmail.com belongs to two people, DATA_AUDIT #10).
        holders = [
            c.customer_id
            for c in store.customers.values()
            if c.email.casefold() == contact.casefold()
        ]
        return holders == [customer_id]
    digits = phone_digits(contact)
    return bool(digits) and digits == phone_digits(store.customers[customer_id].phone)


def _attention(order, today: date) -> str | None:
    """Why a human should look at this order, if they should."""
    if order.status == "shipped" and order.estimated_delivery and order.estimated_delivery < today:
        return f"overdue: estimated delivery was {order.estimated_delivery.isoformat()}"
    if order.status in ("pending", "confirmed"):
        waiting = (today - order.order_date).days
        if waiting > STALLED_AFTER_DAYS:
            return f"stalled: {order.status} for {waiting} days without dispatch"
    return None


def check_order(store: Store, order_id: int, contact: str | None, today: date) -> dict:
    """Status of an order, after checking the phone or e-mail belongs to its customer.

    A wrong number and a wrong contact get the same answer, so the tool never
    reveals whether an order exists to someone who does not own it.
    """
    order = store.orders.get(order_id)
    if order is None or not _owns(store, order.customer_id, contact):
        return dict(NOT_FOUND)

    result = {
        "found": True,
        "order_id": order.order_id,
        "customer_first_name": store.customers[order.customer_id].name.split()[0],
        "status": order.status,
        "order_date": order.order_date.isoformat(),
        # The stored total is authoritative: items carry no unit price (DATA_AUDIT #6).
        "total": brl(order.total_brl),
        "payment_method": order.payment_method,
        "items": [
            {"name": store.products[item.product_id].name, "quantity": item.quantity}
            for item in store.items_of(order.order_id)
        ],
        "tracking_code": order.tracking_code,
        "estimated_delivery": order.estimated_delivery.isoformat()
        if order.estimated_delivery
        else None,
    }
    if order.notes:
        result["notes"] = order.notes
    if reason := _attention(order, today):
        result["needs_human"] = reason
    return result
