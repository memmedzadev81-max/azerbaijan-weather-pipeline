"""BRONZE -> SILVER

Reads raw JSON files, flattens them into a table, applies cleaning rules and
upserts the result into silver_weather_hourly.

Cleaning rules
  1. Rename API fields to clear, unit-suffixed column names.
  2. Convert types (timestamps, floats).
  3. Values outside physically plausible ranges are set to NULL.
  4. Rows where every measurement is NULL are dropped.
  5. Duplicates (same city + hour) are removed, keeping the latest file.
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

from . import config

COLUMN_MAP = {
    "temperature_2m": "temperature_c",
    "relative_humidity_2m": "relative_humidity_pct",
    "precipitation": "precipitation_mm",
    "wind_speed_10m": "wind_speed_kmh",
}
MEASURES = list(COLUMN_MAP.values())


def bronze_to_frame(path: Path) -> pd.DataFrame:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    meta, hourly = record["_metadata"], record["payload"]["hourly"]
    df = pd.DataFrame(hourly).rename(columns=COLUMN_MAP)
    df["city_id"] = meta["city_id"]
    df["source_file"] = Path(path).name
    df["_extracted_at"] = meta["extracted_at"]
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    ts = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M", errors="coerce")
    df = df[ts.notna()].copy()
    ts = ts[ts.notna()]
    df["observed_at"] = ts.dt.strftime("%Y-%m-%d %H:%M")
    df["observed_date"] = ts.dt.strftime("%Y-%m-%d")

    for col in MEASURES:
        if col not in df.columns:
            df[col] = None
        df[col] = pd.to_numeric(df[col], errors="coerce")
        low, high = config.VALID_RANGES[col]
        df.loc[(df[col] < low) | (df[col] > high), col] = None

    df = df.dropna(subset=MEASURES, how="all")
    df = (df.sort_values("_extracted_at")
            .drop_duplicates(subset=["city_id", "observed_at"], keep="last"))
    df["loaded_at"] = datetime.now().isoformat(timespec="seconds")
    cols = ["city_id", "observed_at", "observed_date", *MEASURES, "source_file", "loaded_at"]
    return df[cols].reset_index(drop=True)


def upsert_silver(con: sqlite3.Connection, df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    rows = df.astype(object).where(df.notna(), None).itertuples(index=False, name=None)
    con.executemany(
        """
        INSERT INTO silver_weather_hourly
            (city_id, observed_at, observed_date, temperature_c, relative_humidity_pct,
             precipitation_mm, wind_speed_kmh, source_file, loaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (city_id, observed_at) DO UPDATE SET
            observed_date         = excluded.observed_date,
            temperature_c         = excluded.temperature_c,
            relative_humidity_pct = excluded.relative_humidity_pct,
            precipitation_mm      = excluded.precipitation_mm,
            wind_speed_kmh        = excluded.wind_speed_kmh,
            source_file           = excluded.source_file,
            loaded_at             = excluded.loaded_at
        """,
        list(rows),
    )
    return len(df)


def transform(con: sqlite3.Connection, bronze_files: list[Path]) -> tuple[int, int, set[str]]:
    """Returns (raw rows read, rows written to silver, affected dates)."""
    if not bronze_files:
        return 0, 0, set()
    raw = pd.concat([bronze_to_frame(p) for p in bronze_files], ignore_index=True)
    cleaned = clean(raw)
    written = upsert_silver(con, cleaned)
    return len(raw), written, set(cleaned["observed_date"])
