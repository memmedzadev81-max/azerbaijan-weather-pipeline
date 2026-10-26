"""Orchestrates one end-to-end pipeline run.

  extract_step:  API -> bronze JSON files (one per city)
  process_step:  bronze -> silver -> gold -> quality checks
                 -> commit + move watermark   (or rollback on any error)

The two steps are separate functions so an orchestrator such as Airflow can
run them as separate tasks (see dags/weather_pipeline_dag.py). Everything that
writes to the warehouse happens inside ONE transaction in process_step, so a
failed run never leaves half-loaded data behind.
"""
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config, db, state
from .export import export_gold_csv
from .extract import extract
from .load_gold import load_gold
from .quality import run_checks
from .transform import transform

log = logging.getLogger("pipeline")


def default_end_date() -> date:
    return date.today() - timedelta(days=config.ARCHIVE_LAG_DAYS)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def extract_step(
    sample: bool = False,
    start: date | None = None,
    end: date | None = None,
    db_path: Path | None = None,
    bronze_dir: Path | None = None,
) -> list[dict]:
    """Extract new data for every city. Returns one item per bronze file."""
    end = end or default_end_date()
    con = db.connect(db_path)
    db.init_schema(con)
    try:
        items = []
        for city in config.CITIES:
            window = state.next_window(con, city["city_id"], end, start)
            if window is None:
                log.info("%-9s already up to date", city["city_name"])
                continue
            w_start, w_end = window
            path = extract(city, w_start, w_end, sample=sample, bronze_dir=bronze_dir)
            log.info("%-9s extracted %s .. %s -> %s", city["city_name"], w_start, w_end, path.name)
            items.append({"path": str(path), "city_id": city["city_id"],
                          "loaded_until": w_end.isoformat()})
        if not items:
            log.info("Nothing new to load.")
        return items
    finally:
        con.close()


def process_step(items: list[dict], mode: str = "api", db_path: Path | None = None) -> dict:
    """Bronze -> silver -> gold -> quality gate -> commit, all-or-nothing."""
    con = db.connect(db_path)
    db.init_schema(con)
    run_id = con.execute(
        "INSERT INTO pipeline_runs (started_at, status, mode) VALUES (?, 'running', ?)",
        (_now(), mode),
    ).lastrowid
    con.commit()

    try:
        # ---------- BRONZE -> SILVER ----------
        raw_rows, silver_rows, affected = transform(con, [Path(i["path"]) for i in items])
        log.info("silver: %d raw rows -> %d clean rows", raw_rows, silver_rows)

        # ---------- SILVER -> GOLD ----------
        gold_rows = load_gold(con, affected)
        log.info("gold:   %d daily fact rows (re)built", gold_rows)

        # ---------- QUALITY GATE ----------
        results = run_checks(con)
        log.info("quality: %d checks passed", len(results))

        # ---------- COMMIT ----------
        for item in items:
            state.set_watermark(con, item["city_id"], date.fromisoformat(item["loaded_until"]))
        con.execute(
            """UPDATE pipeline_runs SET finished_at = ?, status = 'success',
               rows_bronze = ?, rows_silver = ?, rows_gold = ? WHERE run_id = ?""",
            (_now(), raw_rows, silver_rows, gold_rows, run_id),
        )
        con.commit()

        # ---------- PUBLISH ----------
        csv_dir = Path(db_path).parent / "gold_csv" if db_path else None
        export_gold_csv(con, csv_dir)
        log.info("gold tables exported to CSV for Power BI")

        return {"run_id": run_id, "status": "success", "rows_bronze": raw_rows,
                "rows_silver": silver_rows, "rows_gold": gold_rows}

    except Exception as exc:
        con.rollback()
        con.execute(
            "UPDATE pipeline_runs SET finished_at = ?, status = 'failed', message = ? WHERE run_id = ?",
            (_now(), str(exc)[:1000], run_id),
        )
        con.commit()
        log.error("Run %s failed and was rolled back: %s", run_id, exc)
        raise
    finally:
        con.close()


def run(
    sample: bool = False,
    start: date | None = None,
    end: date | None = None,
    db_path: Path | None = None,
    bronze_dir: Path | None = None,
) -> dict:
    items = extract_step(sample, start, end, db_path, bronze_dir)
    return process_step(items, "sample" if sample else "api", db_path)
