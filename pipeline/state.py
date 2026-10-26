"""Watermark handling for incremental loads.

Each city remembers the last date that was loaded successfully, so the next
run only requests the days that are new since then.
"""
import sqlite3
from datetime import date, datetime, timedelta

from . import config


def get_watermark(con: sqlite3.Connection, city_id: int) -> date | None:
    row = con.execute(
        "SELECT last_loaded_date FROM pipeline_watermark WHERE city_id = ?",
        (city_id,),
    ).fetchone()
    return date.fromisoformat(row[0]) if row else None


def set_watermark(con: sqlite3.Connection, city_id: int, loaded_until: date) -> None:
    con.execute(
        """
        INSERT INTO pipeline_watermark (city_id, last_loaded_date, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT (city_id) DO UPDATE SET
            last_loaded_date = excluded.last_loaded_date,
            updated_at       = excluded.updated_at
        """,
        (city_id, loaded_until.isoformat(), datetime.now().isoformat(timespec="seconds")),
    )


def next_window(
    con: sqlite3.Connection,
    city_id: int,
    end_date: date,
    start_override: date | None = None,
) -> tuple[date, date] | None:
    """Return the (start, end) window still to load, or None if up to date."""
    if start_override:
        start = start_override
    else:
        wm = get_watermark(con, city_id)
        start = wm + timedelta(days=1) if wm else date.fromisoformat(config.DEFAULT_START_DATE)
    if start > end_date:
        return None
    return start, end_date
