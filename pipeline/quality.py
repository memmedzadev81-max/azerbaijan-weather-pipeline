"""Data quality checks.

Every check is a SQL query that returns the number of *bad* rows. If any check
finds bad rows the run fails, the transaction is rolled back and nothing
half-finished reaches the gold layer.
"""
import sqlite3

from . import config


class DataQualityError(Exception):
    pass


def _range_checks() -> dict[str, str]:
    checks = {}
    for col, (low, high) in config.VALID_RANGES.items():
        checks[f"silver: {col} within [{low}, {high}]"] = (
            f"SELECT COUNT(*) FROM silver_weather_hourly "
            f"WHERE {col} IS NOT NULL AND ({col} < {low} OR {col} > {high})"
        )
    return checks


CHECKS = {
    "silver: no NULL keys": """
        SELECT COUNT(*) FROM silver_weather_hourly
        WHERE city_id IS NULL OR observed_at IS NULL OR observed_date IS NULL
    """,
    "silver: observed_date matches observed_at": """
        SELECT COUNT(*) FROM silver_weather_hourly
        WHERE substr(observed_at, 1, 10) <> observed_date
    """,
    "silver: every city exists in config": None,  # filled in at runtime
    "gold: hours_recorded between 1 and 25": """
        SELECT COUNT(*) FROM fact_weather_daily
        WHERE hours_recorded < 1 OR hours_recorded > 25   -- 25 allows a DST day
    """,
    "gold: min <= avg <= max temperature": """
        SELECT COUNT(*) FROM fact_weather_daily
        WHERE min_temperature_c > avg_temperature_c + 0.01
           OR avg_temperature_c > max_temperature_c + 0.01
    """,
    "gold: every fact row has a date dimension": """
        SELECT COUNT(*) FROM fact_weather_daily f
        LEFT JOIN dim_date d ON d.date_key = f.date_key
        WHERE d.date_key IS NULL
    """,
    "gold: every fact row has a city dimension": """
        SELECT COUNT(*) FROM fact_weather_daily f
        LEFT JOIN dim_city c ON c.city_id = f.city_id
        WHERE c.city_id IS NULL
    """,
}


def run_checks(con: sqlite3.Connection) -> list[tuple[str, int]]:
    city_ids = ",".join(str(c["city_id"]) for c in config.CITIES)
    checks = dict(CHECKS)
    checks["silver: every city exists in config"] = (
        f"SELECT COUNT(*) FROM silver_weather_hourly WHERE city_id NOT IN ({city_ids})"
    )
    checks.update(_range_checks())

    results = [(name, con.execute(sql).fetchone()[0]) for name, sql in checks.items()]
    failed = [(n, c) for n, c in results if c > 0]
    if failed:
        details = "; ".join(f"{n} -> {c} bad rows" for n, c in failed)
        raise DataQualityError(details)
    return results
