from decimal import Decimal

import pytest

from bookscraper.normalize import clean_text, parse_price, parse_rating, parse_stock


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("£51.77", Decimal("51.77")), ("$ 1,5", Decimal("1.5")), ("10", Decimal("10")), ("", None), (None, None), ("N/A", None)],
)
def test_parse_price(raw, expected):
    assert parse_price(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("\n  In stock (22 available)\n", 22), ("In stock (1 available)", 1), ("Out of stock", 0), ("", 0), (None, 0)],
)
def test_parse_stock(raw, expected):
    assert parse_stock(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("star-rating Three", 3), ("star-rating Five", 5), ("star-rating", None), (None, None)],
)
def test_parse_rating(raw, expected):
    assert parse_rating(raw) == expected


def test_clean_text_collapses_whitespace():
    assert clean_text("  A   Light\n in the\tAttic ") == "A Light in the Attic"
    assert clean_text("   ") is None
    assert clean_text(None) is None
