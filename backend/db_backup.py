"""Automatic backup and restoration helpers for the workout database.

The application keeps a single up-to-date copy of ``workout.db`` in
``data/backup``.  This module exposes utilities to create that backup after
database mutations and to restore from it if corruption is detected when the
database is opened.  Copies are performed using a temporary file followed by an
atomic rename to avoid partial writes.
"""
from __future__ import annotations

from pathlib import Path
import os
import sqlite3
import shutil

# Path to the active database and location for the single backup copy.
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workout.db"
BACKUP_PATH = Path(__file__).resolve().parents[1] / "data" / "backup" / "workout.db"


def _atomic_copy(src: Path, dest: Path) -> None:
    """Copy ``src`` to ``dest`` using a temporary file then rename."""

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp")
    shutil.copy2(src, tmp)
    os.replace(tmp, dest)


def create_backup(conn: sqlite3.Connection | None = None) -> None:
    """Write a fresh backup of the main database.

    Parameters
    ----------
    conn:
        Optional open connection to the source database. If omitted a new
        connection to :data:`DB_PATH` is created.
    """

    tmp_backup = BACKUP_PATH.with_suffix(".tmp")
    if conn is None:
        with sqlite3.connect(str(DB_PATH)) as src, sqlite3.connect(str(tmp_backup)) as dst:
            src.backup(dst)
    else:
        with sqlite3.connect(str(tmp_backup)) as dst:
            conn.backup(dst)
    try:
        os.replace(tmp_backup, BACKUP_PATH)
    except PermissionError:
        # On Windows the destination may be locked if opened by another process.
        with open(tmp_backup, "rb") as src, open(BACKUP_PATH, "wb") as dst:
            shutil.copyfileobj(src, dst)
        os.remove(tmp_backup)


def restore_if_corrupt() -> None:
    """Replace a corrupt main database with the latest backup if available."""

    try:
        with sqlite3.connect(str(DB_PATH)) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA integrity_check")
            result = cur.fetchone()
            if not result or result[0] != "ok":
                raise sqlite3.DatabaseError("integrity check failed")
    except Exception:
        if BACKUP_PATH.exists():
            if DB_PATH.exists():
                DB_PATH.unlink()
            _atomic_copy(BACKUP_PATH, DB_PATH)


# Ensure the main database is valid before any other module uses it.
restore_if_corrupt()
