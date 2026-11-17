-- Consultas de análisis sobre los datos cargados.
-- Uso: docker compose exec db psql -U pipeline -d ecommerce -f /sql/analytics.sql

-- 1. Resumen por categoría (vista)
SELECT * FROM category_stats ORDER BY products DESC LIMIT 10;

-- 2. Top 3 por categoría: mejor rating y, a igual rating, el más barato (window function)
SELECT category, title, rating, price
FROM (
    SELECT c.name AS category, p.title, p.rating, p.price,
           ROW_NUMBER() OVER (PARTITION BY c.name ORDER BY p.rating DESC, p.price ASC) AS rn
    FROM products p
    JOIN categories c ON c.id = p.category_id
) ranked
WHERE rn <= 3
ORDER BY category, rn;

-- 3. Distribución de precios en 5 rangos iguales
WITH bounds AS (SELECT min(price) AS lo, max(price) AS hi FROM products)
SELECT width_bucket(p.price, b.lo, b.hi + 0.01, 5) AS bucket,
       min(p.price) AS desde, max(p.price) AS hasta, count(*) AS productos
FROM products p CROSS JOIN bounds b
GROUP BY bucket
ORDER BY bucket;

-- 4. Productos con precio por encima del promedio de su categoría
SELECT c.name AS category, p.title, p.price,
       round(avg(p.price) OVER (PARTITION BY c.name), 2) AS avg_categoria,
       round(p.price - avg(p.price) OVER (PARTITION BY c.name), 2) AS diferencia
FROM products p
JOIN categories c ON c.id = p.category_id
ORDER BY diferencia DESC
LIMIT 15;

-- 5. Cambios de precio entre corridas (LAG sobre el historial)
SELECT upc, scraped_at, price,
       LAG(price) OVER w AS precio_anterior,
       price - LAG(price) OVER w AS cambio
FROM price_history
WINDOW w AS (PARTITION BY upc ORDER BY scraped_at)
ORDER BY scraped_at DESC
LIMIT 20;

-- 6. Riesgo de quiebre de stock: categorías con más productos con menos de 5 unidades
SELECT c.name AS category,
       count(*) FILTER (WHERE p.stock < 5) AS bajo_stock,
       count(*) AS total,
       round(100.0 * count(*) FILTER (WHERE p.stock < 5) / count(*), 1) AS pct
FROM products p
JOIN categories c ON c.id = p.category_id
GROUP BY c.name
HAVING count(*) FILTER (WHERE p.stock < 5) > 0
ORDER BY pct DESC;
