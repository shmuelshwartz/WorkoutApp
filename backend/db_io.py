"""Import and export helpers for the workout database."""
from __future__ import annotations

from pathlib import Path
import json
import os
import shutil
import sqlite3
import time
import logging
from typing import Any, Dict, List, Tuple

# Path to the application's SQLite database.
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workout.db"
# Directory where database backups are stored.
BACKUP_DIR = Path(__file__).resolve().parents[1] / "backups"

# Minimal set of tables expected to exist in any valid workout database.
REQUIRED_TABLES = [
    "library_exercises",
    "library_metric_types",
    "preset_presets",
]


def get_downloads_dir() -> Path:
    """Return the public ``Download`` directory.

    Requests :class:`android.permissions.Permission.MANAGE_EXTERNAL_STORAGE` at
    runtime and returns the path to the shared ``Download`` folder. If the
    permission is denied or the Android APIs are unavailable a
    :class:`PermissionError` is raised. Callers must handle this error and
    inform the user that "All files access" is required. No fallback to
    private directories is provided.
    """

    try:  # pragma: no cover - imports require Android
        from android.permissions import (
            request_permissions,
            check_permission,
            Permission,
        )
        from android.storage import primary_external_storage_path
    except Exception as exc:
        logging.exception("Android APIs unavailable: %s", exc)
        raise PermissionError("All files access not granted") from exc

    request_permissions([Permission.MANAGE_EXTERNAL_STORAGE])
    if check_permission(Permission.MANAGE_EXTERNAL_STORAGE):
        downloads = Path(primary_external_storage_path()) / "Download"
        downloads.mkdir(parents=True, exist_ok=True)
        return downloads.resolve()

    raise PermissionError("All files access not granted")


def sqlite_to_json(db_path: Path) -> Dict[str, List[Dict[str, Any]]]:
    """Return a JSON-serialisable representation of ``db_path``.

    The function introspects the database to discover all user tables and
    converts each row to a dictionary mapping column names to values. This
    implementation is schema-agnostic so it can operate on future database
    layouts without modification.
    """
    result: Dict[str, List[Dict[str, Any]]] = {}
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""SELECT name FROM sqlite_master \
                       WHERE type='table' AND name NOT LIKE 'sqlite_%'""")
        tables = [r[0] for r in cur.fetchall()]
        for table in tables:
            cur.execute(f"SELECT * FROM {table}")
            rows = [dict(row) for row in cur.fetchall()]
            result[table] = rows
    return result


def export_database(db_path: Path = DB_PATH, dest_dir: Path | None = None) -> Path:
    """Export ``db_path`` to ``dest_dir`` as a ``.db`` file.

    On success the absolute path to the exported file is returned. Specific
    file-system errors are logged with full stack traces and re-raised so the
    caller can present a meaningful error to the user. If the required storage
    permission is missing a :class:`PermissionError` is propagated to the
    caller.
    """

    dest_dir = dest_dir or get_downloads_dir()
    filename = f"workout_{int(time.time())}.db"
    dest = (dest_dir / filename).resolve()
    try:
        shutil.copy2(db_path, dest)
    except FileNotFoundError:
        logging.exception("Database file not found: %s", db_path)
        raise
    except PermissionError:
        logging.exception("Permission denied writing export to %s", dest)
        raise
    except OSError:
        logging.exception("OS error exporting database to %s", dest)
        raise
    logging.info("Exported database to %s", dest)
    return dest


def export_database_json(
    db_path: Path = DB_PATH, dest_dir: Path | None = None
) -> Path:
    """Export ``db_path`` to ``dest_dir`` as a JSON file.

    Returns the absolute path to the exported JSON document. File-system
    problems are logged and re-raised to allow the caller to inform the user of
    the specific failure. A :class:`PermissionError` is raised if access to the
    public Downloads folder is not granted.
    """

    dest_dir = dest_dir or get_downloads_dir()
    data = sqlite_to_json(db_path)
    filename = f"workout_{int(time.time())}.json"
    dest = (dest_dir / filename).resolve()
    try:
        with dest.open("w", encoding="utf-8") as fh:
            json.dump(data, fh)
    except FileNotFoundError:
        logging.exception("Destination not found for JSON export: %s", dest)
        raise
    except PermissionError:
        logging.exception("Permission denied writing JSON export to %s", dest)
        raise
    except OSError:
        logging.exception("OS error exporting JSON database to %s", dest)
        raise
    logging.info("Exported database JSON to %s", dest)
    return dest


def validate_database(db_path: Path) -> Tuple[bool, List[str]]:
    """Run validation checks on ``db_path``.

    Currently the function ensures all tables listed in
    :data:`REQUIRED_TABLES` exist. The returned tuple contains a boolean
    indicating success and a list of error messages. The design intentionally
    makes it easy to add further validation rules in the future.
    """
    errors: List[str] = []
    try:
        with sqlite3.connect(str(db_path)) as conn:
            cur = conn.cursor()
            for table in REQUIRED_TABLES:
                cur.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
                    (table,),
                )
                if not cur.fetchone():
                    errors.append(f"missing table: {table}")
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(str(exc))
    return (len(errors) == 0, errors)


def import_database(
    src_path: Path, db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR
) -> None:
    """Validate and replace the current database with ``src_path``.

    A backup of the existing database is created in ``backup_dir`` before the
    replacement occurs. Validation and file-system errors are logged and
    re-raised so callers receive the underlying failure reason.
    """

    valid, errors = validate_database(src_path)
    if not valid:
        message = "; ".join(errors)
        logging.error("Import failed validation: %s", message)
        raise ValueError(message)

    try:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = backup_dir / f"workout_{int(time.time())}.db.bak"
        shutil.copy2(db_path, backup_path)
        shutil.copy2(src_path, db_path)
    except FileNotFoundError:
        logging.exception("Import failed, file not found")
        raise
    except PermissionError:
        logging.exception("Import failed, permission denied")
        raise
    except OSError:
        logging.exception("Import failed due to OS error")
        raise
    logging.info("Replaced database with %s (backup: %s)", src_path, backup_path)
