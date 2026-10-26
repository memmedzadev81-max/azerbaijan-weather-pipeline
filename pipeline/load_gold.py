"""SILVER -> GOLD

Builds a star schema that a BI tool such as Power BI can read directly:
  dim_city, dim_date  (dimensions)
  fact_weather_daily  (one row per city per day)

The fact table is rebuilt incrementally: only dates touched by the current run
are deleted and re-aggregated, so re-running the pipeline never creates
duplicates and never reprocesses the full history.
"""
import sqlite3

from . import config


def _sql(name: str) -> str:
    return (config.SQL_DIR / name).read_text(encoding="utf-8")


def load_dim_city(con: sqlite3.Connection) -> None:
    con.executemany(
        """
        INSERT INTO dim_city (city_id, city_name, latitude, longitude)
        VALUES (:city_id, :city_name, :latitude, :longitude)
        ON CONFLICT (city_id) DO UPDATE SET
            city_name = excluded.city_name,
            latitude  = excluded.latitude,
            longitude = excluded.longitude
        """,
        config.CITIES,
    )


def load_gold(con: sqlite3.Connection, affected_dates: set[str]) -> int:
    load_dim_city(con)
    # execute() (not executescript) so we stay inside the run's transaction
    con.execute(_sql("gold_dim_date.sql"))
    if not affected_dates:
        return 0

    con.execute("DROP TABLE IF EXISTS _affected_dates")
    con.execute("CREATE TEMP TABLE _affected_dates (observed_date TEXT PRIMARY KEY)")
    con.executemany("INSERT INTO _affected_dates VALUES (?)", [(d,) for d in sorted(affected_dates)])

    con.execute(
        """
        DELETE FROM fact_weather_daily
        WHERE date_key IN (
            SELECT CAST(strftime('%Y%m%d', observed_date) AS INTEGER) FROM _affected_dates
        )
        """
    )
    cur = con.execute(_sql("gold_fact_weather_daily.sql"))
    inserted = cur.rowcount
    con.execute("DROP TABLE _affected_dates")
    return inserted
