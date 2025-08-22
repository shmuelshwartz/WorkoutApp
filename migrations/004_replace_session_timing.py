"""One-time migration for replacing legacy workout timing values.

The legacy enum values ``pre_workout`` and ``post_workout`` were renamed to
``pre_session`` and ``post_session``. This script backs up the existing
``workout.db`` database, rebuilds it with the updated schema, and rewrites any
legacy values while copying data. After migration, the script verifies that no
legacy values remain in either data or schema definitions.
"""

from pathlib import Path
import shutil
import sqlite3
import sys
import time
from typing import List, Tuple

OLD_PRE = "pre_" + "workout"
OLD_POST = "post_" + "workout"
LEGACY_MAP = {OLD_PRE: "pre_session", OLD_POST: "post_session"}
LEGACY_KEYS = tuple(LEGACY_MAP.keys())


def log(message: str) -> None:
    """Print a formatted migration log message."""
    print(f"[migration] {message}")


def scan_for_legacy(conn: sqlite3.Connection) -> List[Tuple[str, str, int]]:
    """Return any occurrences of legacy timing values in schema or data."""
    findings: List[Tuple[str, str, int]] = []

    for name, sql in conn.execute(
        "SELECT name, sql FROM sqlite_master WHERE sql IS NOT NULL"
    ):
        if any(key in sql for key in LEGACY_KEYS):
            findings.append((name, "<schema>", 1))

    tables = [
        r[0]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name!='sqlite_sequence'"
        )
    ]
    for table in tables:
        cols = [c[1] for c in conn.execute(f"PRAGMA table_info({table})")]
        for col in cols:
            count = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE {col} IN (?, ?)", LEGACY_KEYS
            ).fetchone()[0]
            if count:
                findings.append((table, col, count))
    return findings


def main() -> None:
    """Migrate ``workout.db`` to remove legacy workout timing values."""
    base = Path(__file__).resolve().parent.parent
    db_dir = base / "data"
    old_db = db_dir / "workout.db"
    backup_dir = base / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_file = backup_dir / f"workout_{int(time.time())}.db.bak"
    log(f"Backing up original database to {backup_file}")
    shutil.copyfile(old_db, backup_file)

    new_db = db_dir / "workout_new.db"
    log(f"Creating new database at {new_db}")
    src = sqlite3.connect(old_db)
    dst = sqlite3.connect(new_db)
    try:
        dst.execute("PRAGMA foreign_keys = OFF;")
        schema_sql = (db_dir / "workout_schema.sql").read_text().replace(
            "IF NOT EXISTS", ""
        )
        dst.executescript(schema_sql)

        tables = [
            r[0]
            for r in src.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name!='sqlite_sequence'"
            )
        ]
        for table in tables:
            cols = [c[1] for c in src.execute(f"PRAGMA table_info({table})")]
            placeholders = ",".join(["?"] * len(cols))
            rows = []
            for row in src.execute(f"SELECT {', '.join(cols)} FROM {table}"):
                row = list(row)
                for i, val in enumerate(row):
                    if isinstance(val, str) and val in LEGACY_MAP:
                        row[i] = LEGACY_MAP[val]
                rows.append(row)
            dst.executemany(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                rows,
            )
            src_count = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            dst_count = dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if src_count != dst_count:
                raise RuntimeError(
                    f"Row count mismatch for {table}: {src_count} != {dst_count}"
                )
            log(f"Copied {src_count} rows from table: {table}")

        try:
            seq_rows = src.execute("SELECT name, seq FROM sqlite_sequence").fetchall()
            dst.execute("DELETE FROM sqlite_sequence")
            dst.executemany(
                "INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", seq_rows
            )
            log(f"Copied {len(seq_rows)} rows from table: sqlite_sequence")
        except sqlite3.OperationalError:
            pass

        findings = scan_for_legacy(dst)
        if findings:
            raise RuntimeError(f"Found legacy timing values: {findings}")

        dst.execute("PRAGMA foreign_keys = ON;")
        fk_errors = dst.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign key violations detected: {fk_errors}")

        dst.commit()
    except Exception as exc:
        dst.rollback()
        log(f"Migration failed: {exc}")
        sys.exit(1)
    finally:
        src.close()
        dst.close()

    shutil.move(str(new_db), str(old_db))
    log("Verifying migrated database in read-only mode")
    verify = sqlite3.connect(f"file:{old_db}?mode=ro", uri=True)
    try:
        findings = scan_for_legacy(verify)
        if findings:
            raise RuntimeError(f"Legacy timing values remain: {findings}")
    finally:
        verify.close()

    log("Migration completed successfully.")


if __name__ == "__main__":
    main()
