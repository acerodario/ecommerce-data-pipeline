"""API REST de solo lectura sobre los datos cargados por el scraper."""

from __future__ import annotations

import os
from contextlib import contextmanager
from decimal import Decimal

import psycopg
from fastapi import FastAPI, HTTPException, Query
from psycopg.rows import dict_row
from pydantic import BaseModel

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://pipeline:pipeline@localhost:5432/ecommerce")

app = FastAPI(
    title="E-commerce Data API",
    description="Consulta de productos, categorías e historial de precios extraídos con Scrapy.",
    version="1.0.0",
)


class Product(BaseModel):
    upc: str
    title: str
    category: str | None
    price: Decimal
    stock: int
    rating: int | None
    url: str
    image_url: str | None


class PricePoint(BaseModel):
    price: Decimal
    stock: int | None
    scraped_at: str


class ProductDetail(Product):
    description: str | None
    price_history: list[PricePoint]


class CategoryStats(BaseModel):
    category: str
    products: int
    avg_price: Decimal
    min_price: Decimal
    max_price: Decimal
    avg_rating: Decimal | None
    total_stock: int


@contextmanager
def cursor():
    with psycopg.connect(DATABASE_URL, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            yield cur


PRODUCT_SELECT = """
    SELECT p.upc, p.title, c.name AS category, p.price, p.stock, p.rating,
           p.url, p.image_url, p.description
    FROM products p
    LEFT JOIN categories c ON c.id = p.category_id
"""


@app.get("/health")
def health():
    with cursor() as cur:
        cur.execute("SELECT count(*) AS products FROM products")
        return {"status": "ok", **cur.fetchone()}


@app.get("/products", response_model=list[Product])
def list_products(
    q: str | None = Query(None, description="Texto a buscar en el título"),
    category: str | None = None,
    min_rating: int | None = Query(None, ge=1, le=5),
    max_price: Decimal | None = Query(None, ge=0),
    in_stock: bool = False,
    order_by: str = Query("title", pattern="^(title|price|-price|rating|-rating)$"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    where, params = [], {}
    if q:
        where.append("p.title ILIKE %(q)s")
        params["q"] = f"%{q}%"
    if category:
        where.append("c.name ILIKE %(category)s")
        params["category"] = category
    if min_rating is not None:
        where.append("p.rating >= %(min_rating)s")
        params["min_rating"] = min_rating
    if max_price is not None:
        where.append("p.price <= %(max_price)s")
        params["max_price"] = max_price
    if in_stock:
        where.append("p.stock > 0")

    # order_by ya viene validado por el patrón: no hay inyección posible
    column = order_by.lstrip("-")
    direction = "DESC" if order_by.startswith("-") else "ASC"
    sql = PRODUCT_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += f" ORDER BY p.{column} {direction}, p.upc LIMIT %(limit)s OFFSET %(offset)s"
    params.update(limit=limit, offset=offset)

    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@app.get("/products/{upc}", response_model=ProductDetail)
def get_product(upc: str):
    with cursor() as cur:
        cur.execute(PRODUCT_SELECT + " WHERE p.upc = %s", (upc,))
        product = cur.fetchone()
        if product is None:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
        cur.execute(
            "SELECT price, stock, scraped_at::text FROM price_history "
            "WHERE upc = %s ORDER BY scraped_at",
            (upc,),
        )
        product["price_history"] = cur.fetchall()
        return product


@app.get("/categories", response_model=list[CategoryStats])
def categories():
    with cursor() as cur:
        cur.execute("SELECT * FROM category_stats ORDER BY products DESC")
        return cur.fetchall()
