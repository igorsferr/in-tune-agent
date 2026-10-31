"""Load the store's CSV files into typed, read-only records.

The data is a fixed snapshot: nothing here writes back. Values are kept as
provided (no silent fixes); inconsistencies are flagged by `quality.py`.
"""

from __future__ import annotations

import csv
import json
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
FILE_PATTERN = "desafio_tecnico_ai_eng - {table}.csv"


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True)

    @field_validator("*", mode="before")
    @classmethod
    def _empty_to_none(cls, value):
        return None if value == "" else value


class Category(_Record):
    category_id: int
    name: str
    description: str


class Product(_Record):
    product_id: int
    price_brl: Decimal
    name: str
    category_id: int
    description: str
    stock_quantity: int
    status: Literal["active", "discontinued", "coming_soon"]
    specs: dict[str, str]
    created_at: date

    @field_validator("specs", mode="before")
    @classmethod
    def _parse_specs(cls, value):
        return json.loads(value) if isinstance(value, str) else value

    @property
    def sellable(self) -> bool:
        return self.status == "active" and self.stock_quantity > 0


class Customer(_Record):
    customer_id: int
    name: str
    phone: str
    email: str
    city: str


class Order(_Record):
    order_id: int
    customer_id: int
    order_date: date
    status: Literal["pending", "confirmed", "shipped", "delivered", "cancelled"]
    total_brl: Decimal
    payment_method: str
    tracking_code: str | None
    estimated_delivery: date | None
    notes: str | None


class OrderItem(_Record):
    order_id: int
    quantity: int
    product_id: int


class Promotion(_Record):
    promotion_id: int
    product_id: int
    discount_percent: int
    description: str
    is_active: bool


def _read(data_dir: Path, table: str, model: type[_Record]) -> list:
    path = data_dir / FILE_PATTERN.format(table=table)
    with path.open(encoding="utf-8", newline="") as f:
        return [model.model_validate(row) for row in csv.DictReader(f)]


class Store:
    """Read-only access to the store data, indexed by id."""

    def __init__(self, data_dir: Path = DEFAULT_DATA_DIR):
        self.categories = {c.category_id: c for c in _read(data_dir, "categories", Category)}
        self.products = {p.product_id: p for p in _read(data_dir, "products", Product)}
        self.customers = {c.customer_id: c for c in _read(data_dir, "customers", Customer)}
        self.orders = {o.order_id: o for o in _read(data_dir, "orders", Order)}
        self.order_items = _read(data_dir, "order_items", OrderItem)
        self.promotions = _read(data_dir, "promotions", Promotion)

    def items_of(self, order_id: int) -> list[OrderItem]:
        return [item for item in self.order_items if item.order_id == order_id]

    def active_promotion(self, product_id: int) -> Promotion | None:
        """The active promotion for a product, if any. Inactive ones never apply."""
        active = [p for p in self.promotions if p.product_id == product_id and p.is_active]
        return max(active, key=lambda p: p.discount_percent, default=None)
