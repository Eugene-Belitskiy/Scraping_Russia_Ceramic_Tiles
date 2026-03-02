-- Таблица с данными о керамической плитке
CREATE TABLE IF NOT EXISTS tiles (
    id              BIGSERIAL PRIMARY KEY,
    name            TEXT,
    price           FLOAT8,
    price_range     TEXT,
    discount        FLOAT8,
    discount_range  TEXT,
    price_unit      TEXT,
    url             TEXT,
    store           TEXT,
    availability    TEXT,
    date            TEXT,
    time            TEXT,
    color           TEXT,
    collection      TEXT,
    brand           TEXT,
    country         TEXT,
    brand_country   TEXT,
    thickness       FLOAT8,
    original_format TEXT,
    format          TEXT,
    design          TEXT,
    material        TEXT,
    surface_type    TEXT,
    surface_finish  TEXT,
    structure       TEXT,
    patterns_count  TEXT,
    total_stock     FLOAT8,
    package_size    FLOAT8,
    total_stock_units INT,
    primary_design  TEXT,
    primary_color   TEXT
);

-- Индексы для быстрой фильтрации в дашборде
CREATE INDEX IF NOT EXISTS idx_tiles_store       ON tiles(store);
CREATE INDEX IF NOT EXISTS idx_tiles_material    ON tiles(material);
CREATE INDEX IF NOT EXISTS idx_tiles_brand       ON tiles(brand);
CREATE INDEX IF NOT EXISTS idx_tiles_price       ON tiles(price);
CREATE INDEX IF NOT EXISTS idx_tiles_format      ON tiles(format);
CREATE INDEX IF NOT EXISTS idx_tiles_primary_design ON tiles(primary_design);
