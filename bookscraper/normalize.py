"""Funciones puras de limpieza: convierten el texto crudo del HTML en tipos útiles."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

RATINGS = {"One": 1, "Two": 2, "Three": 3, "Four": 4, "Five": 5}
_STOCK_RE = re.compile(r"\((\d+)\s+available\)", re.IGNORECASE)
_PRICE_RE = re.compile(r"\d+(?:[.,]\d+)?")


def clean_text(value: str | None) -> str | None:
    """Colapsa espacios y saltos de línea; devuelve None si queda vacío."""
    if value is None:
        return None
    text = " ".join(value.split())
    return text or None


def parse_price(value: str | None) -> Decimal | None:
    """'£51.77' -> Decimal('51.77'). Ignora el símbolo de moneda."""
    if not value:
        return None
    match = _PRICE_RE.search(value)
    if not match:
        return None
    try:
        return Decimal(match.group().replace(",", "."))
    except InvalidOperation:
        return None


def parse_stock(value: str | None) -> int:
    """'In stock (22 available)' -> 22. Sin número o 'Out of stock' -> 0."""
    if not value:
        return 0
    match = _STOCK_RE.search(value)
    return int(match.group(1)) if match else 0


def parse_rating(css_class: str | None) -> int | None:
    """'star-rating Three' -> 3."""
    if not css_class:
        return None
    for word in css_class.split():
        if word in RATINGS:
            return RATINGS[word]
    return None
