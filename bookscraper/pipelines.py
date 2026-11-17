"""Pipelines: validación -> deduplicación -> carga en PostgreSQL (upsert + historial de precios)."""

from __future__ import annotations

import logging
from pathlib import Path

from scrapy.exceptions import DropItem, NotConfigured

logger = logging.getLogger(__name__)

SCHEMA_FILE = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
REQUIRED_FIELDS = ("upc", "title", "price", "url")


class ValidatePipeline:
    """Descarta items incompletos en vez de cargarlos a medias."""

    def process_item(self, item):
        missing = [f for f in REQUIRED_FIELDS if item.get(f) in (None, "")]
        if missing:
            raise DropItem(f"Faltan campos {missing} en {item.get('url')}")
        return item


class DedupPipeline:
    """Un mismo libro puede aparecer en varias páginas: se queda el primero por UPC."""

    def __init__(self):
        self.seen: set[str] = set()

    def process_item(self, item):
        if item["upc"] in self.seen:
            raise DropItem(f"Duplicado: {item['upc']}")
        self.seen.add(item["upc"])
        return item


UPSERT_CATEGORY = """
    INSERT INTO categories (name) VALUES (%s)
    ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
    RETURNING id
"""

UPSERT_PRODUCT = """
    INSERT INTO products (upc, title, category_id, price, stock, rating, description, url, image_url)
    VALUES (%(upc)s, %(title)s, %(category_id)s, %(price)s, %(stock)s, %(rating)s,
            %(description)s, %(url)s, %(image_url)s)
    ON CONFLICT (upc) DO UPDATE SET
        title = EXCLUDED.title,
        category_id = EXCLUDED.category_id,
        price = EXCLUDED.price,
        stock = EXCLUDED.stock,
        rating = EXCLUDED.rating,
        description = EXCLUDED.description,
        url = EXCLUDED.url,
        image_url = EXCLUDED.image_url,
        last_seen = now()
"""

# Solo guarda un punto de historial si el precio o el stock cambiaron desde la última lectura.
INSERT_PRICE_HISTORY = """
    INSERT INTO price_history (upc, price, stock)
    SELECT %(upc)s, %(price)s, %(stock)s
    WHERE NOT EXISTS (
        SELECT 1 FROM (
            SELECT price, stock FROM price_history
            WHERE upc = %(upc)s ORDER BY scraped_at DESC, id DESC LIMIT 1
        ) last
        WHERE last.price = %(price)s AND last.stock IS NOT DISTINCT FROM %(stock)s
    )
"""


class PostgresPipeline:
    """Carga en PostgreSQL. Se desactiva sola si no hay DATABASE_URL (modo solo-JSONL)."""

    def __init__(self, dsn: str, batch_size: int = 100):
        self.dsn = dsn
        self.batch_size = batch_size
        self.conn = None
        self.pending = 0
        self.category_ids: dict[str, int] = {}

    @classmethod
    def from_crawler(cls, crawler):
        dsn = crawler.settings.get("DATABASE_URL")
        if not dsn:
            raise NotConfigured("DATABASE_URL no definido: se exporta solo a archivo")
        return cls(dsn, crawler.settings.getint("DB_BATCH_SIZE", 100))

    def open_spider(self):
        import psycopg

        self.conn = psycopg.connect(self.dsn)
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
        self.conn.commit()

    def close_spider(self):
        if self.conn is not None:
            self.conn.commit()
            self.conn.close()
            logger.info("PostgreSQL: carga terminada")

    def _category_id(self, cur, name: str | None) -> int | None:
        if not name:
            return None
        if name not in self.category_ids:
            cur.execute(UPSERT_CATEGORY, (name,))
            self.category_ids[name] = cur.fetchone()[0]
        return self.category_ids[name]

    def process_item(self, item):
        row = dict(item)
        with self.conn.cursor() as cur:
            row["category_id"] = self._category_id(cur, row.get("category"))
            cur.execute(UPSERT_PRODUCT, row)
            cur.execute(INSERT_PRICE_HISTORY, row)
        self.pending += 1
        if self.pending >= self.batch_size:
            self.conn.commit()
            self.pending = 0
        return item
