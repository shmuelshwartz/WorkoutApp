"""Exercise database helpers.

This module was extracted from :mod:`core` and contains helpers for
querying and modifying exercises stored in the SQLite database.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING

from . import DEFAULT_DB_PATH

if TYPE_CHECKING:  # pragma: no cover - imported only for type checking
    from .exercise import Exercise


def get_all_exercises(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    include_user_created: bool = False,
) -> list:
    """Return a list of all exercise names.

    If ``include_user_created`` is ``True`` the returned list will contain
    ``(name, is_user_created)`` tuples instead of just names.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        if include_user_created:
            cursor.execute(
                "SELECT name, is_user_created FROM library_exercises WHERE deleted = 0 ORDER BY is_user_created, name"
            )
            rows = cursor.fetchall()
            exercises = [(name, bool(flag)) for name, flag in rows]
        else:
            cursor.execute(
                "SELECT name FROM library_exercises WHERE deleted = 0 ORDER BY name"
            )
            exercises = [row[0] for row in cursor.fetchall()]
        return exercises


def get_exercise_details(
    exercise_name: str,
    db_path: Path = DEFAULT_DB_PATH,
    is_user_created: bool | None = None,
) -> dict | None:
    """Return details for ``exercise_name``.

    If ``is_user_created`` is ``None`` (the default), the user-created
    copy will be preferred when both predefined and user-defined versions
    exist.  Otherwise the requested variant will be fetched.

    Returns ``None`` if the exercise does not exist.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        if is_user_created is None:
            cursor.execute(
                "SELECT name, description, is_user_created"
                " FROM library_exercises WHERE name = ? AND deleted = 0"
                " ORDER BY is_user_created DESC LIMIT 1",
                (exercise_name,),
            )
        else:
            cursor.execute(
                "SELECT name, description, is_user_created"
                " FROM library_exercises WHERE name = ? AND is_user_created = ? AND deleted = 0",
                (exercise_name, int(is_user_created)),
            )
        row = cursor.fetchone()
        if not row:
            return None
        name, description, user_flag = row
        return {
            "name": name,
            "description": description or "",
            "is_user_created": bool(user_flag),
        }


def save_exercise(exercise: "Exercise") -> None:
    """Persist ``exercise`` to the database as a user-defined copy."""

    db_path = exercise.db_path
    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND is_user_created = 1 AND deleted = 0",
            (exercise.name,),
        )
        row = cursor.fetchone()
        if row:
            ex_id = row[0]
            cursor.execute(
                "UPDATE library_exercises SET description = ? WHERE id = ?",
                (exercise.description, ex_id),
            )
            cursor.execute(
                "UPDATE library_exercise_metrics SET deleted = 1 WHERE exercise_id = ?",
                (ex_id,),
            )
        else:
            cursor.execute(
                "INSERT INTO library_exercises (name, description, is_user_created) VALUES (?, ?, 1)",
                (exercise.name, exercise.description),
            )
            ex_id = cursor.lastrowid

        for position, m in enumerate(exercise.metrics):
            cursor.execute(
                "SELECT id, type FROM library_metric_types WHERE name = ?",
                (m["name"],),
            )
            mt_row = cursor.fetchone()
            if not mt_row:
                continue
            metric_id, default_type = mt_row

            cursor.execute(
                "SELECT type, input_timing, is_required, scope FROM library_metric_types WHERE id = ?",
                (metric_id,),
            )
            default_row = cursor.fetchone()
            mtype = timing = req = scope_val = None
            if default_row:
                def_type, def_timing, def_req, def_scope = default_row
                if m.get("type") != def_type:
                    mtype = m.get("type")
                if m.get("input_timing") != def_timing:
                    timing = m.get("input_timing")
                if bool(m.get("is_required")) != bool(def_req):
                    req = int(m.get("is_required", False))
                if m.get("scope") != def_scope:
                    scope_val = m.get("scope")

            cursor.execute(
                """INSERT INTO library_exercise_metrics
                    (exercise_id, metric_type_id, position, type, input_timing, is_required, scope, enum_values_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    ex_id,
                    metric_id,
                    position,
                    mtype,
                    timing,
                    req,
                    scope_val,
                    (
                        json.dumps(m.get("values"))
                        if m.get("values") and (m.get("type") or default_type) == "enum"
                        else None
                    ),
                ),
            )

        conn.commit()

    exercise.is_user_created = True
    exercise.mark_saved()


def delete_exercise(
    name: str,
    db_path: Path = DEFAULT_DB_PATH,
    *,
    is_user_created: bool = True,
) -> bool:
    """Delete `name` from the exercises table.

    Only the variant matching `is_user_created` will be removed. The
    function returns `True` when a row was deleted.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND is_user_created = ? AND deleted = 0",
            (name, int(is_user_created)),
        )
        row = cursor.fetchone()
        if not row:
            return False

        ex_id = row[0]

        cursor.execute(
            "SELECT 1 FROM preset_section_exercises WHERE library_exercise_id = ? AND deleted = 0 LIMIT 1",
            (ex_id,),
        )
        if cursor.fetchone():
            raise ValueError("Exercise is in use and cannot be deleted")

        cursor.execute(
            "UPDATE library_exercise_metrics SET deleted = 1 WHERE exercise_id = ?",
            (ex_id,),
        )
        cursor.execute(
            "UPDATE library_exercises SET deleted = 1 WHERE id = ?",
            (ex_id,),
        )
        conn.commit()
        return True

