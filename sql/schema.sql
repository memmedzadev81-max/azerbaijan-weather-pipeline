-- ============================================================
-- Pipeline metadata
-- ============================================================
CREATE TABLE IF NOT EXISTS pipeline_watermark (
    city_id          INTEGER PRIMARY KEY,
    last_loaded_date TEXT NOT NULL,          -- YYYY-MM-DD
    updated_at       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at      TEXT NOT NULL,
    finished_at     TEXT,
    status          TEXT NOT NULL,           -- running / success / failed
    mode            TEXT NOT NULL,           -- api / sample
    rows_bronze     INTEGER DEFAULT 0,
    rows_silver     INTEGER DEFAULT 0,
    rows_gold       INTEGER DEFAULT 0,
    message         TEXT
);

-- ============================================================
-- SILVER: cleaned, typed, de-duplicated hourly observations
-- ============================================================
CREATE TABLE IF NOT EXISTS silver_weather_hourly (
    city_id               INTEGER NOT NULL,
    observed_at           TEXT    NOT NULL,  -- local time, YYYY-MM-DD HH:MM
    observed_date         TEXT    NOT NULL,  -- YYYY-MM-DD
    temperature_c         REAL,
    relative_humidity_pct REAL,
    precipitation_mm      REAL,
    wind_speed_kmh        REAL,
    source_file           TEXT    NOT NULL,  -- lineage back to the bronze file
    loaded_at             TEXT    NOT NULL,
    PRIMARY KEY (city_id, observed_at)
);

-- ============================================================
-- GOLD: star schema for reporting (e.g. Power BI)
-- ============================================================
CREATE TABLE IF NOT EXISTS dim_city (
    city_id    INTEGER PRIMARY KEY,
    city_name  TEXT NOT NULL,
    latitude   REAL NOT NULL,
    longitude  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key     INTEGER PRIMARY KEY,         -- YYYYMMDD
    full_date    TEXT    NOT NULL,
    year         INTEGER NOT NULL,
    quarter      INTEGER NOT NULL,
    month        INTEGER NOT NULL,
    month_name   TEXT    NOT NULL,
    day          INTEGER NOT NULL,
    day_of_week  INTEGER NOT NULL,            -- 1 = Monday ... 7 = Sunday
    day_name     TEXT    NOT NULL,
    is_weekend   INTEGER NOT NULL,
    season       TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_weather_daily (
    date_key             INTEGER NOT NULL REFERENCES dim_date (date_key),
    city_id              INTEGER NOT NULL REFERENCES dim_city (city_id),
    avg_temperature_c    REAL,
    min_temperature_c    REAL,
    max_temperature_c    REAL,
    total_precipitation_mm REAL,
    avg_humidity_pct     REAL,
    max_wind_speed_kmh   REAL,
    rainy_hours          INTEGER,
    hours_recorded       INTEGER NOT NULL,
    PRIMARY KEY (date_key, city_id)
);
