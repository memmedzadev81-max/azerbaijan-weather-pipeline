"""Exports the gold layer to CSV so it can be opened directly in Power BI or Excel."""
import csv
import sqlite3
from pathlib import Path

from . import config

GOLD_TABLES = ["dim_city", "dim_date", "fact_weather_daily"]


def export_gold_csv(con: sqlite3.Connection, out_dir: Path | None = None) -> list[Path]:
    out = Path(out_dir or config.DATA_DIR / "gold_csv")
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for table in GOLD_TABLES:
        cur = con.execute(f"SELECT * FROM {table} ORDER BY 1, 2")
        path = out / f"{table}.csv"
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([c[0] for c in cur.description])
            writer.writerows(cur)
        paths.append(path)
    return paths
