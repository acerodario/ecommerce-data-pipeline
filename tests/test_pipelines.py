import os
from decimal import Decimal

import pytest
from scrapy.exceptions import DropItem

from bookscraper.items import BookItem
from bookscraper.pipelines import DedupPipeline, PostgresPipeline, ValidatePipeline


def make_item(**overrides):
    data = dict(
        upc="test-0001",
        title="Libro de prueba",
        price=Decimal("10.00"),
        stock=5,
        rating=4,
        category="Pruebas",
        description="Descripción",
        image_url="https://books.toscrape.com/media/x.jpg",
        url="https://books.toscrape.com/catalogue/x/index.html",
    )
    data.update(overrides)
    return BookItem(**data)


def test_validate_drops_item_without_price():
    with pytest.raises(DropItem):
        ValidatePipeline().process_item(make_item(price=None))


def test_validate_keeps_complete_item():
    item = make_item()
    assert ValidatePipeline().process_item(item) is item


def test_dedup_drops_repeated_upc():
    pipe = DedupPipeline()
    pipe.process_item(make_item())
    with pytest.raises(DropItem):
        pipe.process_item(make_item(title="Otro título, mismo UPC"))


# --- Integración con PostgreSQL real (corre en CI con un servicio postgres) ---

DATABASE_URL = os.getenv("DATABASE_URL")


@pytest.mark.skipif(not DATABASE_URL, reason="requiere DATABASE_URL")
def test_postgres_upsert_and_price_history():
    import psycopg

    pipe = PostgresPipeline(DATABASE_URL)
    pipe.open_spider()
    with pipe.conn.cursor() as cur:
        cur.execute("DELETE FROM products WHERE upc LIKE 'test-%'")
    pipe.conn.commit()

    pipe.process_item(make_item())
    pipe.process_item(make_item())                          # mismo precio: no agrega historial
    pipe.process_item(make_item(price=Decimal("8.50")))     # baja de precio: sí agrega
    pipe.close_spider()

    with psycopg.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("SELECT price FROM products WHERE upc = 'test-0001'")
        assert cur.fetchone()[0] == Decimal("8.50")
        cur.execute("SELECT price FROM price_history WHERE upc = 'test-0001' ORDER BY id")
        assert [r[0] for r in cur.fetchall()] == [Decimal("10.00"), Decimal("8.50")]
        cur.execute("DELETE FROM products WHERE upc LIKE 'test-%'")
