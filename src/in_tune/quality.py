"""Detect products whose name, description and specs contradict each other.

Rules are keyed on a detected conflict per attribute, never on product ids,
so they keep working if the data changes. Conflicts are reported, not fixed:
the agent must not confirm an attribute the store's own data disagrees on.
"""

from __future__ import annotations

import re

from in_tune.store import Product

# Instrument makers only: pickup and string brands (LR Baggs, Aquila) are not
# evidence of what the instrument is.
BRANDS = (
    "Music Man", "Yamaha", "Fender", "Gibson", "Ibanez", "PRS", "Pearl", "Tama", "Roland",
    "Korg", "Nord", "Taylor", "Martin", "Takamine", "Crafter", "Giannini", "Tagima",
    "Rozini", "Shelby", "Kala", "Ohana", "Kalani",
)  # fmt: skip
# Model names that identify a maker even when the maker is not written.
MODELS = {
    "Jazz Bass": "Fender", "Precision": "Fender", "Stratocaster": "Fender",
    "Telecaster": "Fender", "StingRay": "Music Man", "Les Paul": "Gibson",
    "Stage Custom": "Yamaha", "Export": "Pearl", "Nord Stage": "Nord",
}  # fmt: skip
WOODS = ("Alder", "Ash", "Maple", "Mahogany", "Basswood", "Poplar", "Birch")


def _brands(text: str) -> set[str]:
    found = {b for b in BRANDS if re.search(rf"\b{re.escape(b)}\b", text)}
    found |= {brand for model, brand in MODELS.items() if model in text}
    return found


def _count(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text)
    return match.group(1) if match else None


def conflicts(product: Product) -> list[dict[str, str]]:
    """Attributes on which the product's own fields disagree."""
    found = []
    name_brands, description_brands = _brands(product.name), _brands(product.description)
    if name_brands and description_brands and not name_brands & description_brands:
        found.append(
            {
                "attribute": "brand",
                "name": ", ".join(sorted(name_brands)),
                "description": ", ".join(sorted(description_brands)),
            }
        )

    for attribute, pattern, spec_key in (
        ("strings", r"(\d+) cordas", "strings"),
        ("keys", r"(\d+) teclas", "keys"),
    ):
        described, spec = _count(pattern, product.description), product.specs.get(spec_key)
        if described and spec and spec.isdigit() and described != spec:
            found.append({"attribute": attribute, "description": described, "specs": spec})

    for spec_key in ("body", "shells"):
        spec = product.specs.get(spec_key)
        described = [w for w in WOODS if re.search(rf"\b{w}\b", product.description)]
        if spec and described and not any(w in spec for w in described):
            found.append({"attribute": "wood", "description": ", ".join(described), "specs": spec})

    return found
