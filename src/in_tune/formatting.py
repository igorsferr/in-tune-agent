"""Money and phone formats shared by the tools and the grounding check."""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_cents(value: Decimal | float | str) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def brl(value: Decimal | float | str) -> str:
    """Format as Brazilian currency: Decimal("1299") -> "R$ 1.299,00"."""
    integer, cents = f"{to_cents(value):,.2f}".split(".")
    return f"R$ {integer.replace(',', '.')},{cents}"


def parse_brl(text: str) -> Decimal:
    """Inverse of `brl`: "R$ 1.299,00" -> Decimal("1299.00").

    Also accepts a dot as the decimal mark when there is no comma ("R$ 799.90").
    """
    number = text.replace("R$", "").strip()
    if "," in number:
        number = number.replace(".", "").replace(",", ".")
    elif not re.search(r"\.\d{2}$", number):
        number = number.replace(".", "")  # "1.299" is a thousands separator
    return to_cents(number)


def phone_digits(phone: str) -> str:
    """Keep only digits and drop a leading country code: "+55 (67) 99812-3456" -> "67998123456"."""
    digits = re.sub(r"\D", "", phone)
    return digits[2:] if digits.startswith("55") and len(digits) > 11 else digits
