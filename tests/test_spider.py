from decimal import Decimal
from pathlib import Path

import pytest
from scrapy.http import HtmlResponse, Request

from bookscraper.spiders.books import BooksSpider

FIXTURES = Path(__file__).parent / "fixtures"
PRODUCT_URL = "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html"
LISTING_URL = "https://books.toscrape.com/catalogue/category/books/poetry_23/index.html"


def fake_response(name: str, url: str) -> HtmlResponse:
    body = (FIXTURES / name).read_bytes()
    return HtmlResponse(url=url, body=body, encoding="utf-8", request=Request(url))


@pytest.fixture
def spider():
    return BooksSpider()


def test_parse_product_extracts_all_fields(spider):
    items = list(spider.parse_product(fake_response("product.html", PRODUCT_URL)))
    assert len(items) == 1
    item = items[0]

    assert item["upc"] == "a897fe39b1053632"
    assert item["title"] == "A Light in the Attic"
    assert item["price"] == Decimal("51.77")
    assert item["stock"] == 22
    assert item["rating"] == 3
    assert item["category"] == "Poetry"
    assert item["url"] == PRODUCT_URL
    assert item["image_url"].startswith("https://books.toscrape.com/media/")
    assert item["description"] and len(item["description"]) > 100


def test_parse_listing_follows_every_product(spider):
    requests = list(spider.parse(fake_response("listing.html", LISTING_URL)))

    assert len(requests) == 19  # la categoría Poesía tiene 19 libros en una sola página
    assert all(isinstance(r, Request) for r in requests)
    assert all(r.callback == spider.parse_product for r in requests)
    assert requests[0].url == PRODUCT_URL
