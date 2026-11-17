-- Esquema idempotente: se puede ejecutar en cada corrida.

CREATE TABLE IF NOT EXISTS categories (
    id   SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    upc         TEXT PRIMARY KEY,
    title       TEXT          NOT NULL,
    category_id INT           REFERENCES categories (id),
    price       NUMERIC(10,2) NOT NULL CHECK (price >= 0),
    stock       INT           NOT NULL DEFAULT 0 CHECK (stock >= 0),
    rating      SMALLINT      CHECK (rating BETWEEN 1 AND 5),
    description TEXT,
    url         TEXT          NOT NULL,
    image_url   TEXT,
    first_seen  TIMESTAMPTZ   NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS price_history (
    id         BIGSERIAL PRIMARY KEY,
    upc        TEXT          NOT NULL REFERENCES products (upc) ON DELETE CASCADE,
    price      NUMERIC(10,2) NOT NULL,
    stock      INT,
    scraped_at TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_category   ON products (category_id);
CREATE INDEX IF NOT EXISTS idx_products_price      ON products (price);
CREATE INDEX IF NOT EXISTS idx_price_history_upc   ON price_history (upc, scraped_at DESC);

CREATE OR REPLACE VIEW category_stats AS
SELECT c.name                     AS category,
       count(*)                   AS products,
       round(avg(p.price), 2)     AS avg_price,
       min(p.price)               AS min_price,
       max(p.price)               AS max_price,
       round(avg(p.rating), 2)    AS avg_rating,
       sum(p.stock)               AS total_stock
FROM products p
JOIN categories c ON c.id = p.category_id
GROUP BY c.name;
