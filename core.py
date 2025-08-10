from __future__ import annotations

import sqlite3
from pathlib import Path
import time
import re
import copy
import json
from typing import TYPE_CHECKING

# Number of sets each exercise defaults to when starting a workout
DEFAULT_SETS_PER_EXERCISE = 3

# Default rest duration between sets in seconds
DEFAULT_REST_DURATION = 120

# Default path to the bundled SQLite database
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "workout.db"

if TYPE_CHECKING:
    from backend.exercise import Exercise

# Will hold preset data loaded from the database. Each item is a dict with
#   {'name': <preset name>,
#    'exercises': [{'name': <exercise name>, 'sets': <number_of_sets>}, ...]}
WORKOUT_PRESETS = []

# Map legacy session-level input_timing values to the canonical
# values expected by the ``preset_preset_metrics`` table.
_TIMING_TO_DB = {
    "pre_session": "pre_workout",
    "post_session": "post_workout",
}
_TIMING_FROM_DB = {v: k for k, v in _TIMING_TO_DB.items()}


def _to_db_timing(value: str | None) -> str | None:
    """Return canonical timing value for database writes."""

    if value is None:
        return None
    return _TIMING_TO_DB.get(value, value)


def _from_db_timing(value: str | None) -> str | None:
    """Return UI-friendly timing value from the database."""

    if value is None:
        return None
    return _TIMING_FROM_DB.get(value, value)


def load_workout_presets(db_path: Path = DEFAULT_DB_PATH):
    """Load workout presets from the SQLite database into WORKOUT_PRESETS."""
    global WORKOUT_PRESETS

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name FROM preset_presets WHERE deleted = 0 ORDER BY id"
        )
        presets = []
        for preset_id, preset_name in cursor.fetchall():
            cursor.execute(
                """
            SELECT se.exercise_name, se.number_of_sets, se.rest_time
            FROM preset_preset_sections s
            JOIN preset_section_exercises se ON se.section_id = s.id
            WHERE s.preset_id = ? AND s.deleted = 0 AND se.deleted = 0
            ORDER BY s.position, se.position
            """,
                (preset_id,),
            )
            exercises = [
                {"name": row[0], "sets": row[1], "rest": row[2]}
                for row in cursor.fetchall()
            ]
            presets.append({"name": preset_name, "exercises": exercises})

    WORKOUT_PRESETS = presets
    return presets


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


def get_metrics_for_exercise(
    exercise_name: str,
    db_path: Path = DEFAULT_DB_PATH,
    preset_name: str | None = None,
    is_user_created: bool | None = None,
) -> list:
    """Return metric definitions for ``exercise_name``.

    Each item in the returned list is a dictionary with ``name`` and ``type``
    keys. ``values`` will contain any allowed values for ``enum`` metrics.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        if is_user_created is None:
            cursor.execute(
                "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                (exercise_name,),
            )
        else:
            cursor.execute(
                "SELECT id FROM library_exercises WHERE name = ? AND is_user_created = ? AND deleted = 0",
                (exercise_name, int(is_user_created)),
            )
        row = cursor.fetchone()
        if not row:
            return []
        exercise_id = row[0]

        cursor.execute(
            """
        SELECT mt.id,
               mt.name,
               COALESCE(em.type, mt.type),
               COALESCE(em.input_timing, mt.input_timing),
               COALESCE(em.is_required, mt.is_required),
               COALESCE(em.scope, mt.scope),
               COALESCE(em.enum_values_json, mt.enum_values_json),
               mt.description
        FROM library_exercise_metrics em
        JOIN library_metric_types mt ON mt.id = em.metric_type_id
        WHERE em.exercise_id = ? AND em.deleted = 0 AND mt.deleted = 0
        ORDER BY em.id
        """,
            (exercise_id,),
        )

        metrics = []
        for (
            metric_type_id,
            name,
            mtype,
            input_timing,
            is_required,
            scope,
            enum_json,
            description,
        ) in cursor.fetchall():
            values = []
            if mtype == "enum" and enum_json:
                try:
                    values = json.loads(enum_json)
                except Exception:
                    values = []
            metrics.append(
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": input_timing,
                    "is_required": bool(is_required),
                    "scope": scope,
                    "description": description,
                    "values": values,
                    "library_metric_type_id": metric_type_id,
                    "preset_exercise_metric_id": None,
                }
            )

        # Apply overrides for a specific preset if requested
        if preset_name:
            cursor.execute(
                """
            SELECT sem.id,
                   sem.metric_name,
                   COALESCE(sem.type, mt.type),
                   COALESCE(sem.input_timing, mt.input_timing),
                   COALESCE(sem.is_required, mt.is_required),
                   COALESCE(sem.scope, mt.scope),
                   COALESCE(sem.enum_values_json, mt.enum_values_json),
                   COALESCE(sem.metric_description, mt.description),
                   COALESCE(sem.library_metric_type_id, mt.id)
            FROM preset_exercise_metrics sem
            JOIN preset_section_exercises se ON sem.section_exercise_id = se.id
            JOIN preset_preset_sections s ON se.section_id = s.id
            JOIN preset_presets p ON s.preset_id = p.id
            LEFT JOIN library_metric_types mt ON sem.library_metric_type_id = mt.id
            WHERE p.name = ? AND se.exercise_name = ?
              AND sem.deleted = 0 AND se.deleted = 0 AND s.deleted = 0 AND p.deleted = 0
            ORDER BY sem.position
            """,
                (preset_name, exercise_name),
            )
            overrides: dict[str, dict] = {}
            for (
                sem_id,
                name,
                mtype,
                input_timing,
                is_required,
                scope,
                enum_json,
                description,
                lib_type_id,
            ) in cursor.fetchall():
                values = []
                if mtype == "enum" and enum_json:
                    try:
                        values = json.loads(enum_json)
                    except Exception:
                        values = []
                overrides[name] = {
                    "preset_exercise_metric_id": sem_id,
                    "type": mtype,
                    "input_timing": input_timing,
                    "is_required": bool(is_required),
                    "scope": scope,
                    "values": values,
                    "description": description,
                    "library_metric_type_id": lib_type_id,
                }
            names = {m["name"] for m in metrics}
            for m in metrics:
                o = overrides.get(m["name"])
                if o:
                    for k, v in o.items():
                        if k == "library_metric_type_id" and v is None:
                            continue
                        m[k] = v
            for name, data in overrides.items():
                if name not in names:
                    metrics.append({"name": name, **data})

        return metrics


def get_metrics_for_preset(
    preset_name: str, db_path: Path = DEFAULT_DB_PATH
) -> list:
    """Return preset-level metric definitions for ``preset_name``."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
            (preset_name,),
        )
        row = cursor.fetchone()
        if not row:
            return []
        preset_id = row[0]
        cursor.execute(
            """
            SELECT pm.id,
                   COALESCE(pm.library_metric_type_id, mt.id),
                   pm.metric_name,
                   COALESCE(pm.metric_description, mt.description),
                   COALESCE(pm.type, mt.type),
                   COALESCE(pm.input_timing, mt.input_timing),
                   COALESCE(pm.is_required, mt.is_required),
                   COALESCE(pm.scope, mt.scope),
                   COALESCE(pm.enum_values_json, mt.enum_values_json)
              FROM preset_preset_metrics pm
              LEFT JOIN library_metric_types mt ON pm.library_metric_type_id = mt.id
             WHERE pm.preset_id = ? AND pm.deleted = 0
             ORDER BY pm.position
            """,
            (preset_id,),
        )
        metrics = []
        for (
            pm_id,
            lib_type_id,
            name,
            description,
            mtype,
            timing,
            is_required,
            scope,
            enum_json,
        ) in cursor.fetchall():
            values = []
            if mtype == "enum" and enum_json:
                try:
                    values = json.loads(enum_json)
                except Exception:
                    values = []
            metrics.append(
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": _from_db_timing(timing),
                    "is_required": bool(is_required),
                    "scope": scope,
                    "values": values,
                    "description": description,
                    "library_metric_type_id": lib_type_id,
                    "preset_metric_id": pm_id,
                }
            )
    return metrics


def get_all_metric_types(
    db_path: Path = DEFAULT_DB_PATH,
    *,
    include_user_created: bool = False,
) -> list:
    """Return all metric type definitions from the database.

    If ``include_user_created`` is ``True`` the returned dictionaries include an
    ``is_user_created`` flag.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        if include_user_created:
            cursor.execute(
                """
                SELECT name, type, input_timing,
                       is_required, scope, description, is_user_created,
                       enum_values_json
                FROM library_metric_types
                WHERE deleted = 0
                ORDER BY id
                """
            )
            metric_types = [
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": input_timing,
                    "is_required": bool(is_required),
                    "scope": scope,
                    "description": description,
                    "is_user_created": bool(flag),
                    "enum_values_json": enum_json,
                }
                for (
                    name,
                    mtype,
                    input_timing,
                    is_required,
                    scope,
                    description,
                    flag,
                    enum_json,
                ) in cursor.fetchall()
            ]
        else:
            cursor.execute(
                """
                SELECT name, type, input_timing,
                       is_required, scope, description, enum_values_json
                FROM library_metric_types
                WHERE deleted = 0
                ORDER BY id
                """
            )
            metric_types = [
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": input_timing,
                    "is_required": bool(is_required),
                    "scope": scope,
                    "description": description,
                    "enum_values_json": enum_json,
                }
                for (
                    name,
                    mtype,
                    input_timing,
                    is_required,
                    scope,
                    description,
                    enum_json,
                ) in cursor.fetchall()
            ]
        return metric_types


def get_metric_type_schema(
    db_path: Path = DEFAULT_DB_PATH,
) -> list:
    """Return column definitions for the ``library_metric_types`` table.

    Each item is a dictionary with ``name`` and optional ``options`` keys. The
    ``options`` list will contain allowed values if the column has a CHECK
    constraint enumerating them.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='library_metric_types'"
        )
        row = cursor.fetchone()
        if not row:
            return []

        create_sql = row[0]
        fields = []
        for line in create_sql.splitlines():
            line = line.strip().lstrip(",").rstrip(",").strip()
            if (
                not line
                or line.startswith("CREATE TABLE")
                or line.startswith("PRIMARY KEY")
                or line.startswith("'")
            ):
                continue
            m = re.match(r'"?(\w+)"?', line)
            if not m:
                continue
            name = m.group(1)
            if name in {"id", "is_user_created", "deleted"}:
                continue
            fields.append({"name": name})

        for field in fields:
            chk = re.search(
                rf'{field["name"]}[^,]*CHECK\(.*?{field["name"]}.*?IN \(([^)]*)\)\)',
                create_sql,
                re.DOTALL,
            )
            if chk:
                opts = [opt.strip().strip("'\"") for opt in chk.group(1).split(",")]
                field["options"] = opts
        return fields


def is_metric_type_user_created(
    metric_type_name: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """Return ``True`` if ``metric_type_name`` is marked as user created."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT is_user_created FROM library_metric_types WHERE name = ?",
            (metric_type_name,),
        )
        row = cursor.fetchone()
        return bool(row[0]) if row else False


def add_metric_type(
    name: str,
    mtype: str,
    input_timing: str,
    scope: str,
    description: str = "",
    is_required: bool = False,
    enum_values: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> int:
    """Insert a new metric type and return its ID."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO library_metric_types
                (name, type, input_timing,
                 is_required, scope, description, is_user_created,
                 enum_values_json)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            """,
            (
                name,
                mtype,
                input_timing,
                int(is_required),
                scope,
                description,
                json.dumps(enum_values) if enum_values is not None else None,
            ),
        )
        metric_id = cursor.lastrowid
        conn.commit()
        return metric_id


def add_metric_to_exercise(
    exercise_name: str,
    metric_type_name: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Associate an existing metric type with an exercise."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0",
            (exercise_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Exercise '{exercise_name}' not found")
        exercise_id = row[0]

        cursor.execute(
            "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0",
            (metric_type_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric type '{metric_type_name}' not found")
        metric_id = row[0]

        cursor.execute(
            "SELECT 1 FROM library_exercise_metrics WHERE exercise_id = ? AND metric_type_id = ? AND deleted = 0",
            (exercise_id, metric_id),
        )
        if cursor.fetchone() is None:
            cursor.execute(
                "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id) VALUES (?, ?)",
                (exercise_id, metric_id),
            )
            conn.commit()


def remove_metric_from_exercise(
    exercise_name: str,
    metric_type_name: str,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Remove a metric association from an exercise."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0",
            (exercise_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Exercise '{exercise_name}' not found")
        exercise_id = row[0]

        cursor.execute(
            "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0",
            (metric_type_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric type '{metric_type_name}' not found")
        metric_id = row[0]

        cursor.execute(
            "UPDATE library_exercise_metrics SET deleted = 1 WHERE exercise_id = ? AND metric_type_id = ?",
            (exercise_id, metric_id),
        )
        conn.commit()


def update_metric_type(
    metric_type_name: str,
    *,
    mtype: str | None = None,
    input_timing: str | None = None,
    scope: str | None = None,
    description: str | None = None,
    is_required: bool | None = None,
    enum_values: list[str] | None = None,
    is_user_created: bool | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Update fields of a metric type identified by ``metric_type_name``."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        if is_user_created is None:
            cursor.execute(
                "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                (metric_type_name,),
            )
        else:
            cursor.execute(
                "SELECT id FROM library_metric_types WHERE name = ? AND is_user_created = ? AND deleted = 0",
                (metric_type_name, int(is_user_created)),
            )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric type '{metric_type_name}' not found")
        metric_id = row[0]
        updates = []
        params: list = []
        if mtype is not None:
            updates.append("type = ?")
            params.append(mtype)
        if input_timing is not None:
            updates.append("input_timing = ?")
            params.append(input_timing)
        if is_required is not None:
            updates.append("is_required = ?")
            params.append(int(is_required))
        if scope is not None:
            updates.append("scope = ?")
            params.append(scope)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if enum_values is not None:
            updates.append("enum_values_json = ?")
            params.append(json.dumps(enum_values))
        if updates:
            params.append(metric_id)
            cursor.execute(
                f"UPDATE library_metric_types SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()


def set_section_exercise_metric_override(
    preset_name: str,
    section_index: int,
    exercise_name: str,
    metric_type_name: str,
    *,
    input_timing: str,
    is_required: bool = False,
    scope: str = "set",
    enum_values: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Apply an override for ``metric_type_name`` for a specific exercise in a preset."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        cursor.execute(
            "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
            (preset_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Preset '{preset_name}' not found")
        preset_id = row[0]

        cursor.execute(
            "SELECT id FROM preset_preset_sections WHERE preset_id = ? AND deleted = 0 ORDER BY position",
            (preset_id,),
        )
        sections = cursor.fetchall()
        if section_index < 0 or section_index >= len(sections):
            raise IndexError("Section index out of range")
        section_id = sections[section_index][0]

        cursor.execute(
            "SELECT id, type, description FROM library_metric_types WHERE name = ? AND deleted = 0",
            (metric_type_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric '{metric_type_name}' not found")
        metric_type_id, def_type, metric_desc = row

        cursor.execute(
            """SELECT id FROM preset_section_exercises WHERE section_id = ? AND exercise_name = ? AND deleted = 0 ORDER BY position LIMIT 1""",
            (section_id, exercise_name),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Exercise not part of section")
        se_id = row[0]

        cursor.execute(
            "SELECT id FROM preset_exercise_metrics WHERE section_exercise_id = ? AND metric_name = ? AND deleted = 0",
            (se_id, metric_type_name),
        )
        row = cursor.fetchone()
        if row:
            updates = ["input_timing = ?", "is_required = ?", "scope = ?"]
            params = [input_timing, int(is_required), scope]
            if enum_values is not None:
                updates.append("enum_values_json = ?")
                params.append(json.dumps(enum_values))
            params.append(row[0])
            cursor.execute(
                f"UPDATE preset_exercise_metrics SET {', '.join(updates)} WHERE id = ?",
                params,
            )
        else:
            cursor.execute(
                """
                INSERT INTO preset_exercise_metrics
                    (section_exercise_id, metric_name, metric_description, type, input_timing,
                     is_required, scope, enum_values_json, library_metric_type_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    se_id,
                    metric_type_name,
                    metric_desc,
                    def_type,
                    input_timing,
                    int(is_required),
                    scope,
                    json.dumps(enum_values) if enum_values is not None else None,
                    metric_type_id,
                ),
            )
        conn.commit()


def set_exercise_metric_override(
    exercise_name: str,
    metric_type_name: str,
    *,
    is_user_created: bool | None = None,
    mtype: str | None = None,
    input_timing: str | None = None,
    is_required: bool | None = None,
    scope: str | None = None,
    enum_values: list[str] | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Apply an override for ``metric_type_name`` for a specific exercise.

    ``is_user_created`` selects between predefined and user-created copies of
    the exercise.  If ``None`` (the default), the user-created variant will be
    chosen when it exists.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()

        if is_user_created is None:
            cursor.execute(
                "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                (exercise_name,),
            )
        else:
            cursor.execute(
                "SELECT id FROM library_exercises WHERE name = ? AND is_user_created = ? AND deleted = 0",
                (exercise_name, int(is_user_created)),
            )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Exercise '{exercise_name}' not found")
        exercise_id = row[0]

        cursor.execute(
            "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0",
            (metric_type_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric '{metric_type_name}' not found")
        metric_type_id = row[0]

        cursor.execute(
            "SELECT id FROM library_exercise_metrics WHERE exercise_id = ? AND metric_type_id = ? AND deleted = 0",
            (exercise_id, metric_type_id),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError("Exercise is not associated with the metric")
        em_id = row[0]

        updates = []
        params: list = []
        if mtype is not None:
            updates.append("type = ?")
            params.append(mtype)
        if input_timing is not None:
            updates.append("input_timing = ?")
            params.append(input_timing)
        if is_required is not None:
            updates.append("is_required = ?")
            params.append(int(is_required))
        if scope is not None:
            updates.append("scope = ?")
            params.append(scope)
        if enum_values is not None:
            updates.append("enum_values_json = ?")
            params.append(json.dumps(enum_values))

        if not updates:
            cursor.execute(
                """
                UPDATE library_exercise_metrics
                   SET type = NULL,
                       input_timing = NULL,
                       is_required = NULL,
                       scope = NULL,
                       enum_values_json = NULL
                 WHERE id = ?
                """,
                (em_id,),
            )
        else:
            params.append(em_id)
            cursor.execute(
                f"UPDATE library_exercise_metrics SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()



def validate_workout_session(session: "WorkoutSession") -> list[str]:
    """Return a list of validation errors for ``session``."""

    errors: list[str] = []
    if session.end_time is None:
        errors.append("Session has not been completed")
    for ex in session.exercises:
        expected = ex.get("sets", 0)
        actual = len(ex.get("results", []))
        if actual != expected:
            errors.append(
                f"Exercise '{ex.get('name')}' has {actual} recorded sets but expected {expected}"
            )
    return errors


def save_completed_session(
    session: "WorkoutSession", db_path: Path | None = None
) -> None:
    """Persist a finished ``session`` to the database."""

    path = Path(db_path or session.db_path)
    errors = validate_workout_session(session)
    if errors:
        raise ValueError("; ".join(errors))

    with sqlite3.connect(str(path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO session_sessions (preset_id, preset_name, started_at, ended_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                session.preset_id,
                session.preset_name,
                session.start_time,
                session.end_time or time.time(),
            ),
        )
        session_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO session_session_sections (session_id, name, position)
            VALUES (?, ?, 1)
            """,
            (session_id, session.preset_name),
        )
        section_id = cursor.lastrowid

        if session.session_metrics:
            metric_map = {m["name"]: m for m in session.session_metric_defs}
            for pos, (name, value) in enumerate(
                session.session_metrics.items(), 1
            ):
                mdef = metric_map.get(name, {})
                cursor.execute(
                    """
                    INSERT INTO session_session_metrics
                        (session_id, library_metric_type_id, preset_preset_metric_id, metric_name,
                         metric_description, type, input_timing, scope, is_required,
                         enum_values_json, value, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        mdef.get("library_metric_type_id"),
                        mdef.get("preset_metric_id"),
                        name,
                        mdef.get("description"),
                        mdef.get("type", "str"),
                        _to_db_timing(mdef.get("input_timing")),
                        mdef.get("scope", "session"),
                        int(mdef.get("is_required", False)),
                        json.dumps(mdef.get("values"))
                        if mdef.get("type") == "enum"
                        else None,
                        str(value),
                        pos,
                    ),
                )

        for ex_pos, ex in enumerate(session.exercises, 1):
            cursor.execute(
                """
                INSERT INTO session_section_exercises
                    (section_id, library_exercise_id, preset_section_exercise_id,
                     exercise_name, exercise_description, number_of_sets, rest_time, position)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    section_id,
                    ex.get("library_exercise_id"),
                    ex.get("preset_section_exercise_id"),
                    ex.get("name"),
                    ex.get("exercise_description"),
                    ex.get("sets", 0),
                    ex.get("rest", session.rest_duration),
                    ex_pos,
                ),
            )
            session_ex_id = cursor.lastrowid
            metric_defs = ex.get("metric_defs", [])
            metric_ids: dict[str, int] = {}
            for m_pos, m in enumerate(metric_defs, 1):
                cursor.execute(
                    """
                    INSERT INTO session_exercise_metrics
                        (session_exercise_id, library_metric_type_id, preset_exercise_metric_id,
                         metric_name, metric_description, type, input_timing, scope,
                         is_required, enum_values_json, position)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_ex_id,
                        m.get("library_metric_type_id"),
                        m.get("preset_exercise_metric_id"),
                        m["name"],
                        m.get("description"),
                        m.get("type", "str"),
                        _to_db_timing(m.get("input_timing")),
                        m.get("scope", "set"),
                        int(m.get("is_required", False)),
                        json.dumps(m.get("values"))
                        if m.get("type") == "enum"
                        else None,
                        m_pos,
                    ),
                )
                metric_ids[m["name"]] = cursor.lastrowid

            for set_idx, result in enumerate(ex.get("results", []), 1):
                cursor.execute(
                    """
                    INSERT INTO session_exercise_sets (section_exercise_id, set_number, started_at, ended_at, notes)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        session_ex_id,
                        set_idx,
                        result.get("started_at"),
                        result.get("ended_at"),
                        result.get("notes"),
                    ),
                )
                set_id = cursor.lastrowid
                metrics = result.get("metrics", {})
                for name, value in metrics.items():
                    metric_id = metric_ids.get(name)
                    if metric_id is None:
                        cursor.execute(
                            """
                            INSERT INTO session_exercise_metrics
                                (session_exercise_id, metric_name, type, input_timing, scope, position)
                            VALUES (?, ?, ?, ?, ?, ?)
                            """,
                            (
                                session_ex_id,
                                name,
                                "str",
                                _to_db_timing("post_set"),
                                "set",
                                len(metric_ids) + 1,
                            ),
                        )
                        metric_id = cursor.lastrowid
                        metric_ids[name] = metric_id
                    cursor.execute(
                        """
                        INSERT INTO session_set_metrics
                            (exercise_set_id, exercise_metric_id, value)
                        VALUES (?, ?, ?)
                        """,
                        (set_id, metric_id, str(value)),
                    )

    session.saved = True



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


def delete_metric_type(
    name: str,
    db_path: Path = DEFAULT_DB_PATH,
    *,
    is_user_created: bool = True,
) -> bool:
    """Delete ``name`` from the metric types table.

    Only the variant matching ``is_user_created`` will be removed. The
    function returns ``True`` when a row was deleted.  A ``ValueError`` is
    raised if the metric type is still referenced by any exercise or preset.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM library_metric_types WHERE name = ? AND is_user_created = ? AND deleted = 0",
            (name, int(is_user_created)),
        )
        row = cursor.fetchone()
        if not row:
            return False

        mt_id = row[0]

        # Check if this metric type is referenced by any exercises or presets
        cursor.execute(
            "SELECT 1 FROM library_exercise_metrics WHERE metric_type_id = ? AND deleted = 0 LIMIT 1",
            (mt_id,),
        )
        if cursor.fetchone():
            raise ValueError("Metric type is in use and cannot be deleted")

        cursor.execute(
            "SELECT 1 FROM preset_preset_metrics WHERE library_metric_type_id = ? AND deleted = 0 LIMIT 1",
            (mt_id,),
        )
        if cursor.fetchone():
            raise ValueError("Metric type is in use and cannot be deleted")

        cursor.execute(
            "SELECT 1 FROM preset_exercise_metrics WHERE library_metric_type_id = ? AND deleted = 0 LIMIT 1",
            (mt_id,),
        )
        if cursor.fetchone():
            raise ValueError("Metric type is in use and cannot be deleted")

        cursor.execute(
            "SELECT 1 FROM preset_preset_metrics WHERE library_metric_type_id = ? AND deleted = 0 LIMIT 1",
            (mt_id,),
        )
        if cursor.fetchone():
            raise ValueError("Metric type is in use and cannot be deleted")

        cursor.execute(
            "UPDATE library_metric_types SET deleted = 1 WHERE id = ?",
            (mt_id,),
        )
        conn.commit()
        return True


def uses_default_metric(
    exercise_name: str,
    metric_type_name: str,
    *,
    is_user_created: bool | None = None,
    db_path: Path = DEFAULT_DB_PATH,
) -> bool:
    """Return ``True`` if ``exercise_name`` uses ``metric_type_name`` defaults."""

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        if is_user_created is None:
            cursor.execute(
                "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                (exercise_name,),
            )
        else:
            cursor.execute(
                "SELECT id FROM library_exercises WHERE name = ? AND is_user_created = ? AND deleted = 0",
                (exercise_name, int(is_user_created)),
            )
        row = cursor.fetchone()
        if not row:
            return False
        ex_id = row[0]
        cursor.execute(
            """
            SELECT em.type, em.input_timing, em.is_required, em.scope, em.enum_values_json
              FROM library_exercise_metrics em
              JOIN library_metric_types mt ON em.metric_type_id = mt.id
             WHERE em.exercise_id = ? AND mt.name = ? AND em.deleted = 0 AND mt.deleted = 0
            """,
            (ex_id, metric_type_name),
        )
        row = cursor.fetchone()
        if not row:
            return False
        return all(val is None for val in row)


def find_presets_using_exercise(
    exercise_name: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[str]:
    """Return a list of preset names referencing ``exercise_name``."""

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
            (exercise_name,),
        )
        row = cur.fetchone()
        if not row:
            return []
        lib_id = row[0]
        cur.execute(
            """
            SELECT DISTINCT p.name
              FROM preset_section_exercises se
              JOIN preset_preset_sections s ON se.section_id = s.id
              JOIN preset_presets p ON s.preset_id = p.id
             WHERE se.library_exercise_id = ? AND se.deleted = 0 AND s.deleted = 0 AND p.deleted = 0
            """,
            (lib_id,),
        )
        return [r[0] for r in cur.fetchall()]


def apply_exercise_changes_to_presets(
    exercise: "Exercise",
    presets: list[str],
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> None:
    """Update ``presets`` to use the details from ``exercise``."""

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND is_user_created = ? AND deleted = 0",
            (exercise.name, int(exercise.is_user_created)),
        )
        row = cur.fetchone()
        if not row:
            return
        lib_id = row[0]

        cur.execute(
            "SELECT mt.id, mt.name, mt.description, mt.type, mt.input_timing, mt.is_required, mt.scope, mt.enum_values_json, em.position"
            " FROM library_exercise_metrics em JOIN library_metric_types mt ON em.metric_type_id = mt.id"
            " WHERE em.exercise_id = ? AND em.deleted = 0 AND mt.deleted = 0 ORDER BY em.position",
            (lib_id,),
        )
        metric_rows = cur.fetchall()

        for preset in presets:
            cur.execute(
                "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
                (preset,),
            )
            prow = cur.fetchone()
            if not prow:
                continue
            pid = prow[0]
            cur.execute(
                "SELECT id FROM preset_preset_sections WHERE preset_id = ? AND deleted = 0",
                (pid,),
            )
            section_ids = [r[0] for r in cur.fetchall()]
            for sid in section_ids:
                cur.execute(
                    "SELECT id FROM preset_section_exercises WHERE section_id = ? AND library_exercise_id = ? AND deleted = 0",
                    (sid, lib_id),
                )
                ex_ids = [r[0] for r in cur.fetchall()]
                for se_id in ex_ids:
                    cur.execute(
                        "UPDATE preset_section_exercises SET exercise_name = ?, exercise_description = ? WHERE id = ?",
                        (exercise.name, exercise.description, se_id),
                    )
                    cur.execute(
                        "UPDATE preset_exercise_metrics SET deleted = 1 WHERE section_exercise_id = ?",
                        (se_id,),
                    )
                    for (
                        mt_id,
                        mt_name,
                        mt_desc,
                        mtype,
                        timing,
                        req,
                        scope,
                        enum_json,
                        pos,
                    ) in metric_rows:
                        cur.execute(
                            """
                            INSERT INTO preset_exercise_metrics
                                (section_exercise_id, metric_name, metric_description, type, input_timing,
                                 is_required, scope, enum_values_json, position, library_metric_type_id)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                se_id,
                                mt_name,
                                mt_desc,
                                mtype,
                                timing,
                                req,
                                scope,
                                enum_json,
                                pos,
                                mt_id,
                            ),
                        )
        conn.commit()


def find_exercises_using_metric_type(
    metric_name: str,
    *,
    db_path: Path = DEFAULT_DB_PATH,
) -> list[str]:
    """Return exercise names that include ``metric_name``."""

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0",
            (metric_name,),
        )
        row = cur.fetchone()
        if not row:
            return []
        mt_id = row[0]
        cur.execute(
            """
            SELECT e.name
              FROM library_exercise_metrics em
              JOIN library_exercises e ON em.exercise_id = e.id
             WHERE em.metric_type_id = ? AND em.deleted = 0 AND e.deleted = 0
            """,
            (mt_id,),
        )
        return [r[0] for r in cur.fetchall()]


