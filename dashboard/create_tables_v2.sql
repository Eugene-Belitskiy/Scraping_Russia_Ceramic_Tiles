-- Схема v2: две таблицы (products + prices) + вью для дашборда
-- Применять в Supabase после запуска migrate_to_two_tables.py

-- =============================================================
-- ТАБЛИЦА ТОВАРОВ (статичные характеристики, один раз)
-- =============================================================
CREATE TABLE IF NOT EXISTS products (
    product_id      TEXT PRIMARY KEY,       -- md5(url)[:16]
    date_added      TEXT NOT NULL,          -- "DD.MM.YYYY" — дата первого появления
    url             TEXT UNIQUE NOT NULL,
    store           TEXT,
    name            TEXT,
    color           TEXT,
    primary_color   TEXT,
    collection      TEXT,
    brand           TEXT,
    country         TEXT,
    brand_country   TEXT,
    thickness       FLOAT8,
    original_format TEXT,
    format          TEXT,
    design          TEXT,
    primary_design  TEXT,
    material        TEXT,
    surface_type    TEXT,
    surface_finish  TEXT,
    structure       TEXT,
    patterns_count  TEXT,
    package_size    FLOAT8,
    price_unit      TEXT
);

-- =============================================================
-- ТАБЛИЦА ЦЕН И ОСТАТКОВ (одна запись на товар на дату)
-- =============================================================
CREATE TABLE IF NOT EXISTS prices (
    price_id            TEXT PRIMARY KEY,   -- "{product_id}_{date}"
    product_id          TEXT NOT NULL REFERENCES products(product_id),
    store               TEXT,               -- денормализовано для запросов без JOIN
    date                TEXT NOT NULL,      -- "DD.MM.YYYY"
    time                TEXT,
    price               FLOAT8,
    price_range         TEXT,
    discount            FLOAT8,
    discount_range      TEXT,
    availability        TEXT,
    total_stock         FLOAT8,             -- null для Keramogranit_RU
    total_stock_units   INT,                -- null для Keramogranit_RU
    UNIQUE (product_id, date)               -- один снимок цены на товар в день
);

-- =============================================================
-- ВЬЮ ДЛЯ ДАШБОРДА (обратная совместимость со старой таблицей tiles)
-- Показывает актуальные (последние) цены для каждого товара
-- =============================================================
CREATE OR REPLACE VIEW tiles_v2 AS
SELECT
    p.product_id,
    p.url,
    p.store,
    p.name,
    p.color,
    p.primary_color,
    p.collection,
    p.brand,
    p.country,
    p.brand_country,
    p.thickness,
    p.original_format,
    p.format,
    p.design,
    p.primary_design,
    p.material,
    p.surface_type,
    p.surface_finish,
    p.structure,
    p.patterns_count,
    p.package_size,
    p.price_unit,
    pr.date,
    pr.time,
    pr.price,
    pr.price_range,
    pr.discount,
    pr.discount_range,
    pr.availability,
    pr.total_stock,
    pr.total_stock_units
FROM products p
JOIN prices pr ON p.product_id = pr.product_id
WHERE pr.date = (
    SELECT MAX(date) FROM prices WHERE product_id = p.product_id
);

-- =============================================================
-- ИНДЕКСЫ
-- =============================================================

-- products
CREATE INDEX IF NOT EXISTS idx_products_store          ON products(store);
CREATE INDEX IF NOT EXISTS idx_products_material       ON products(material);
CREATE INDEX IF NOT EXISTS idx_products_brand          ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_format         ON products(format);
CREATE INDEX IF NOT EXISTS idx_products_primary_design ON products(primary_design);
CREATE INDEX IF NOT EXISTS idx_products_country        ON products(country);
CREATE INDEX IF NOT EXISTS idx_products_primary_color  ON products(primary_color);

-- prices
CREATE INDEX IF NOT EXISTS idx_prices_date             ON prices(date);
CREATE INDEX IF NOT EXISTS idx_prices_product_id       ON prices(product_id);
CREATE INDEX IF NOT EXISTS idx_prices_store            ON prices(store);
CREATE INDEX IF NOT EXISTS idx_prices_price            ON prices(price);
