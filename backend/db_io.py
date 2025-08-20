"""Import and export helpers for the workout database."""
from __future__ import annotations

from pathlib import Path
import json
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
    """Return a user-accessible Downloads directory.

    On Android we resolve the path to the primary external storage so that
    exported files appear in the device's shared ``Download`` folder. Storage
    permissions are requested at runtime. When the Android APIs are not
    available (e.g. during desktop testing), ``~/Downloads`` is used instead.

    The directory is created if it does not already exist and a
    :class:`~pathlib.Path` to it is returned.
    """
    try:
        # These modules only exist on Android; importing them at runtime keeps
        # desktop development lightweight.
        from android.permissions import Permission, request_permissions  # type: ignore
        from android.storage import primary_external_storage_path  # type: ignore
    except Exception:
        downloads = Path.home() / "Downloads"
    else:
        request_permissions(
            [Permission.READ_EXTERNAL_STORAGE, Permission.WRITE_EXTERNAL_STORAGE]
        )
        downloads = Path(primary_external_storage_path()) / "Download"
    downloads.mkdir(parents=True, exist_ok=True)
    return downloads


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

    The destination file is named ``workout_<EPOCH>.db`` and stored in the
    user's Downloads directory by default. A :class:`pathlib.Path` pointing to
    the exported file is returned.
    """
    dest_dir = dest_dir or get_downloads_dir()
    filename = f"workout_{int(time.time())}.db"
    dest = dest_dir / filename
    shutil.copy2(db_path, dest)
    logging.info("Exported database to %s", dest)
    return dest


def export_database_json(db_path: Path = DB_PATH, dest_dir: Path | None = None) -> Path:
    """Export ``db_path`` to ``dest_dir`` as a JSON file.

    The JSON document captures the entire contents of the database without
    relying on any hard-coded schema information. The destination file is named
    ``workout_<EPOCH>.json``. A :class:`pathlib.Path` to the exported file is
    returned.
    """
    dest_dir = dest_dir or get_downloads_dir()
    data = sqlite_to_json(db_path)
    filename = f"workout_{int(time.time())}.json"
    dest = dest_dir / filename
    with dest.open("w", encoding="utf-8") as fh:
        json.dump(data, fh)
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


def import_database(src_path: Path, db_path: Path = DB_PATH, backup_dir: Path = BACKUP_DIR) -> bool:
    """Validate and replace the current database with ``src_path``.

    A backup of the existing database is created in ``backup_dir`` before the
    replacement occurs. If validation fails the operation is aborted and the
    current database is left untouched. ``True`` is returned on success.
    """
    valid, errors = validate_database(src_path)
    if not valid:
        logging.error("Import failed validation: %s", "; ".join(errors))
        return False

    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_path = backup_dir / f"workout_{int(time.time())}.db.bak"
    shutil.copy2(db_path, backup_path)
    shutil.copy2(src_path, db_path)
    logging.info("Replaced database with %s (backup: %s)", src_path, backup_path)
    return True
