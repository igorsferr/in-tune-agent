"""The tools as the model sees them, and the one place their input is checked.

Each tool has a pydantic input model: its JSON schema is what the model
receives, and the same model validates (and coerces) what comes back, so
"1" becomes 1 and a bad call returns an error the model can read and fix.
No tool call can crash the conversation.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from in_tune.policies import Policies
from in_tune.store import Store
from in_tune.tools.catalog import get_product, search_products
from in_tune.tools.handoff import DEFAULT_LOG, REASONS, handoff_to_human
from in_tune.tools.orders import check_order
from in_tune.tools.payments import quote_payment
from in_tune.tools.store_info import store_status


class _Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SearchProducts(_Input):
    query: str | None = Field(None, description="Words to match: brand, model, type, feature.")
    category: str | None = Field(None, description="Exact category name, from the list.")
    min_price: float | None = Field(None, description="Minimum price paid, in reais.")
    max_price: float | None = Field(None, description="Maximum price paid, in reais.")
    available_only: bool = Field(True, description="False to include items that can't be bought.")


class GetProduct(_Input):
    product_id: int | None = Field(None, description="Product id, when known.")
    name: str | None = Field(None, description="Product name or model, when the id is unknown.")


class CheckOrder(_Input):
    order_id: int = Field(description="Order number given by the customer.")
    contact: str = Field(description="Phone or e-mail given by the customer.")


class QuotePayment(_Input):
    product_ids: list[int] = Field(
        min_length=1, description="Products to buy; repeat an id to buy more than one."
    )


class GetPolicy(_Input):
    section: str = Field(description="Section number from the manual index, e.g. '4.1' or '4'.")


class StoreStatus(_Input):
    pass


class HandoffToHuman(_Input):
    reason: Literal[REASONS]  # type: ignore[valid-type]
    summary: str = Field(description="What the customer needs, in one or two sentences.")
    contact: str | None = Field(None, description="Customer phone or e-mail, if given.")


DESCRIPTIONS = {
    "search_products": (
        "Search the catalog. Use for any question about what the store sells, prices or "
        "availability. Returns sellable products only, cheapest first, unless available_only "
        "is false. 'price' is the list price; when 'promotion' is present its 'final_price' "
        "is what the customer pays; 'pix_price' appears only when there is no promotion."
    ),
    "get_product": (
        "Full details of one product: price, promotion, availability, description and specs. "
        "Unavailable products come with available alternatives. 'data_warnings' lists "
        "attributes the store's own data contradicts: never confirm those."
    ),
    "check_order": (
        "Status of an order. Requires the order number and the phone or e-mail of the customer "
        "who placed it. 'needs_human' means the order must be handed to the team."
    ),
    "quote_payment": (
        "Totals for each payment method, the allowed credit-card installments, whether mixed "
        "payment is allowed, and Campo Grande metro shipping, for the given products."
    ),
    "get_policy": (
        "Text of a section of the store's policy manual: hours, contact, payment, returns, "
        "exchanges, shipping, promotions, warranty, privacy. Asking for '4' returns 4.1-4.4."
    ),
    "store_status": (
        "Current date and time in Campo Grande, whether the store is open now, and when it "
        "opens next. Holidays included."
    ),
    "handoff_to_human": (
        "Register a handoff to the human team and get a protocol number. Use for complaints, "
        "orders flagged needs_human, data the store contradicts, data-deletion requests, and "
        "anything the manual says to escalate."
    ),
}

INPUTS = {
    "search_products": SearchProducts,
    "get_product": GetProduct,
    "check_order": CheckOrder,
    "quote_payment": QuotePayment,
    "get_policy": GetPolicy,
    "store_status": StoreStatus,
    "handoff_to_human": HandoffToHuman,
}


class Toolbox:
    def __init__(
        self,
        store: Store,
        policies: Policies,
        clock: Callable[[], datetime],
        handoff_log: Path = DEFAULT_LOG,
    ):
        self.store, self.policies, self.clock, self.handoff_log = (
            store,
            policies,
            clock,
            handoff_log,
        )

    def definitions(self) -> list[dict]:
        """Tool definitions for the Messages API, in a fixed order (cache-friendly)."""
        tools = []
        for name, model in INPUTS.items():
            schema = model.model_json_schema()
            if name == "search_products":
                categories = [c.name for c in self.store.categories.values()]
                options = schema["properties"]["category"]["anyOf"]
                next(o for o in options if o.get("type") == "string")["enum"] = categories
            tools.append({"name": name, "description": DESCRIPTIONS[name], "input_schema": schema})
        return tools

    def run(self, name: str, raw_input: dict) -> tuple[dict, bool]:
        """Run a tool call. Returns (result, is_error); never raises."""
        if name not in INPUTS:
            return {"error": f"unknown tool {name!r}"}, True
        try:
            args = INPUTS[name].model_validate(raw_input)
        except ValidationError as e:
            problems = [f"{'.'.join(map(str, err['loc']))}: {err['msg']}" for err in e.errors()]
            return {"error": "invalid arguments", "problems": problems}, True
        try:
            result = self._call(name, args)
        except Exception as e:  # a tool bug must not end the conversation
            return {"error": f"{type(e).__name__}: {e}"}, True
        return result, "error" in result

    def _call(self, name: str, args: _Input) -> dict:
        s = self.store
        match name:
            case "search_products":
                return search_products(s, **args.model_dump())
            case "get_product":
                return get_product(s, args.product_id, args.name)
            case "check_order":
                return check_order(s, args.order_id, args.contact, self.clock().date())
            case "quote_payment":
                return quote_payment(s, args.product_ids)
            case "get_policy":
                return self.policies.get(args.section)
            case "store_status":
                return store_status(self.clock())
            case "handoff_to_human":
                return handoff_to_human(
                    args.reason, args.summary, args.contact, self.clock(), self.handoff_log
                )
        raise AssertionError(name)
