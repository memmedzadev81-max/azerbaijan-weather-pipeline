"""Warehouse connection and schema setup (SQLite)."""
import sqlite3
from pathlib import Path

from . import config


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or config.WAREHOUSE_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute("PRAGMA foreign_keys = ON")
    return con


def init_schema(con: sqlite3.Connection) -> None:
    """Create all tables if they do not exist yet (idempotent)."""
    for name in ("schema.sql",):
        con.executescript((config.SQL_DIR / name).read_text(encoding="utf-8"))
    con.commit()
