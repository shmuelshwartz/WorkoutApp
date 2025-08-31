"""Verify that the shipped workout.db uses the same schema as workout_schema.sql."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def _get_tables(conn: sqlite3.Connection) -> list[str]:
    """Return application table names, ignoring SQLite's internal tables."""
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return sorted(name for (name,) in cur.fetchall())


def _get_table_details(conn: sqlite3.Connection, table: str) -> tuple[list[tuple], list[tuple]]:
    """Return column info and foreign key details for *table*."""
    cols = conn.execute(f"PRAGMA table_info('{table}')").fetchall()
    fks = conn.execute(f"PRAGMA foreign_key_list('{table}')").fetchall()
    return cols, fks


def test_workout_schema_matches_db() -> None:
    """Ensure workout_schema.sql matches the bundled workout.db schema."""
    project_root = Path(__file__).resolve().parents[1]
    schema_sql = (project_root / "data" / "workout_schema.sql").read_text()
    db_path = project_root / "data" / "workout.db"

    # Build a reference database from the schema SQL.
    schema_conn = sqlite3.connect(":memory:")
    schema_conn.executescript(schema_sql)

    # Open the real database in read-only mode.
    real_conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    schema_tables = _get_tables(schema_conn)
    real_tables = _get_tables(real_conn)
    assert schema_tables == real_tables

    for table in schema_tables:
        expected_cols, expected_fks = _get_table_details(schema_conn, table)
        real_cols, real_fks = _get_table_details(real_conn, table)
        assert real_cols == expected_cols
        assert real_fks == expected_fks

    schema_conn.close()
    real_conn.close()
