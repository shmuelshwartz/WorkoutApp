"""Reset the workout database to an empty schema for branch testing.

This one-time migration follows the project's migration guidelines to back up
and rebuild the database before swapping it into place. The resulting
`workout.db` file matches the schema from ``workout_schema.sql`` but contains no
rows so the application can be exercised without any persisted data (including
metrics such as "tempo").
"""

from __future__ import annotations

from pathlib import Path
import shutil
import sqlite3
import sys
import time
from typing import Iterable


def log(message: str) -> None:
    """Print a formatted migration log entry."""

    print(f"[migration] {message}")


def drop_existing_objects(conn: sqlite3.Connection) -> None:
    """Remove all non-system tables, indexes, views, and triggers."""

    drop_plan: Iterable[tuple[str, str]] = (
        ("view", "DROP VIEW"),
        ("trigger", "DROP TRIGGER"),
        ("index", "DROP INDEX"),
        ("table", "DROP TABLE"),
    )
    for object_type, drop_cmd in drop_plan:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type=? AND name NOT LIKE 'sqlite_%'",
            (object_type,),
        ).fetchall()
        for (name,) in rows:
            log(f"Dropping {object_type}: {name}")
            conn.execute(f"{drop_cmd} {name}")
    log("Clearing autoincrement state")
    try:
        conn.execute("DELETE FROM sqlite_sequence")
    except sqlite3.OperationalError:
        log("sqlite_sequence not present; nothing to clear")


def verify_tables_empty(conn: sqlite3.Connection) -> None:
    """Ensure every user table currently holds zero rows."""

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    for (table_name,) in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM \"{table_name}\"").fetchone()[0]
        if count:
            raise RuntimeError(
                f"Table '{table_name}' contains {count} rows after reset; expected empty"
            )
        log(f"Verified table '{table_name}' is empty")


def apply_schema(conn: sqlite3.Connection, schema_path: Path) -> None:
    """Create the fresh schema defined in ``schema_path``."""

    schema_sql = schema_path.read_text(encoding="utf-8")
    sanitized_sql = schema_sql.replace("IF NOT EXISTS", "")
    log(f"Applying schema from {schema_path}")
    conn.executescript(sanitized_sql)


def main() -> None:
    """Execute the reset migration."""

    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "data"
    backup_dir = base_dir / "backups"
    backup_dir.mkdir(exist_ok=True)

    old_db = data_dir / "workout.db"
    new_db = data_dir / "workout_new.db"
    schema_path = data_dir / "workout_schema.sql"

    if not old_db.exists():
        raise FileNotFoundError(f"Cannot locate database at {old_db}")
    if not schema_path.exists():
        raise FileNotFoundError(f"Cannot locate schema file at {schema_path}")

    backup_file = backup_dir / f"workout_{int(time.time())}.db.bak"
    log(f"Backing up existing database to {backup_file}")
    shutil.copy2(old_db, backup_file)

    if new_db.exists():
        log(f"Removing leftover working database at {new_db}")
        new_db.unlink()

    log(f"Creating working copy at {new_db}")
    shutil.copy2(old_db, new_db)

    conn = sqlite3.connect(new_db)
    try:
        conn.execute("PRAGMA foreign_keys = OFF;")
        drop_existing_objects(conn)
        apply_schema(conn, schema_path)
        verify_tables_empty(conn)
        conn.execute("PRAGMA foreign_keys = ON;")
        fk_errors = conn.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign key violations detected: {fk_errors}")
        conn.commit()
    except Exception as exc:  # pragma: no cover - defensive guardrail
        conn.rollback()
        log(f"Migration failed: {exc}")
        log(
            "Restore the backup by copying "
            f"{backup_file.name} back to {old_db.name} if needed."
        )
        raise
    finally:
        conn.close()

    log(f"Replacing {old_db} with freshly initialized database")
    old_db.unlink()
    shutil.move(str(new_db), str(old_db))

    verify_conn = sqlite3.connect(f"file:{old_db}?mode=ro", uri=True)
    try:
        verify_tables_empty(verify_conn)
    finally:
        verify_conn.close()

    log("Database reset completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        sys.exit(1)
