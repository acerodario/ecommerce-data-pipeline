# E-commerce Data Pipeline

![CI](https://github.com/acerodario/ecommerce-data-pipeline/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![Scrapy](https://img.shields.io/badge/Scrapy-2.15-60A839?logo=scrapy&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)

Pipeline ETL completo de extremo a extremo: **extrae** un catálogo de e-commerce con Scrapy, **transforma**
y valida los datos, los **carga** en PostgreSQL con historial de precios y los expone con una **API REST** en FastAPI.
Todo se levanta con Docker Compose.

Fuente: [books.toscrape.com](https://books.toscrape.com), sitio público creado para practicar scraping
(1.000 productos, 51 categorías, 50 páginas de listado).

```
 books.toscrape.com
        │  Scrapy (listado → detalle, paginación, robots.txt, autothrottle)
        ▼
 ValidatePipeline ─► DedupPipeline ─► PostgresPipeline ──► data/books.jsonl
   campos obligatorios   por UPC        upsert + historial
                                              │
                                              ▼
                                   PostgreSQL 16 (products, categories,
                                   price_history, vista category_stats)
                                              │
                                              ▼
                                   FastAPI  /products  /categories
```

## Resultado de una corrida

| | |
|---|---|
| Productos extraídos | 1.000 en ~34 s |
| Errores | 0 |
| Segunda corrida | 0 duplicados: el historial solo crece si cambia el precio o el stock |
| Tests | 22 (parsing con HTML real, normalización, pipelines e integración con PostgreSQL) |

Cómo se midió: `docker compose --profile scrape run --rm scraper` en un PC con Windows 11 y Docker Desktop,
8 peticiones concurrentes por dominio con autothrottle activo. El tiempo es `elapsed_time_seconds` de las
estadísticas de Scrapy al final de la corrida (17-nov-2026); varía según la red y la carga del sitio.

## Cómo correrlo

```bash
docker compose up -d db api                    # PostgreSQL + API en http://localhost:8000
docker compose --profile scrape run --rm scraper   # extrae el catálogo y lo carga
```

- Documentación interactiva de la API: http://localhost:8000/docs
- Consultas de análisis: `docker compose exec db psql -U pipeline -d ecommerce -f /sql/analytics.sql`

Sin Docker (solo exporta a JSONL):

```bash
pip install -r requirements.txt
scrapy crawl books -O data/books.jsonl
```

## API

| Endpoint | Descripción |
|---|---|
| `GET /health` | Estado y número de productos |
| `GET /products` | Filtros `q`, `category`, `min_rating`, `max_price`, `in_stock`, orden (`price`, `-price`, `rating`…) y paginación |
| `GET /products/{upc}` | Detalle con historial de precios |
| `GET /categories` | Estadísticas por categoría (precio medio, mín/máx, rating, stock) |

```bash
curl "localhost:8000/products?category=poetry&min_rating=4&order_by=-price&limit=2"
```

## SQL

[`db/schema.sql`](db/schema.sql) — esquema idempotente con claves foráneas, `CHECK`, índices y una vista.
[`sql/analytics.sql`](sql/analytics.sql) — consultas de análisis:

- Top 3 por categoría con `ROW_NUMBER() OVER (PARTITION BY …)`
- Distribución de precios con `width_bucket`
- Desviación de cada producto contra el promedio de su categoría (`AVG() OVER`)
- Cambios de precio entre corridas con `LAG()`
- Riesgo de quiebre de stock con `COUNT(*) FILTER (WHERE …)`

## Decisiones técnicas

- **Upsert** (`INSERT … ON CONFLICT DO UPDATE`): volver a correr el scraper actualiza en vez de duplicar.
- **Historial de precios condicional**: se inserta un punto solo si el precio o el stock cambiaron (`WHERE NOT EXISTS`).
- **Commits por lotes** de 100 items para no abrir una transacción por fila.
- **Normalización en funciones puras** (`bookscraper/normalize.py`), fáciles de testear aparte del spider.
- **Tests offline** con páginas HTML reales guardadas en `tests/fixtures`: no dependen de la red.
- **Scraping responsable**: respeta `robots.txt`, autothrottle y user-agent identificable.
- `pyOpenSSL` fijado en 26.0.0: las versiones 26.1+ rompen el contexto TLS de Twisted con Scrapy 2.15.

## Estructura

```
bookscraper/   spider, items, normalización y pipelines
api/           FastAPI
db/            esquema PostgreSQL
sql/           consultas de análisis
tests/         pytest + fixtures HTML
```

---
Autor: [Darío Acero](https://github.com/acerodario) · [LinkedIn](https://www.linkedin.com/in/dario-acero)
