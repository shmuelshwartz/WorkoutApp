"""Database helpers for metric definitions and associations."""

from __future__ import annotations

import json
import re
import sqlite3
from pathlib import Path

from . import DEFAULT_DB_PATH
from .utils import _to_db_timing, _from_db_timing


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
    """Return column definitions for the ``library_metric_types`` table."""

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
    """Apply an override for ``metric_type_name`` for a specific exercise."""

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


def delete_metric_type(
    name: str,
    db_path: Path = DEFAULT_DB_PATH,
    *,
    is_user_created: bool = True,
) -> bool:
    """Delete ``name`` from the metric types table."""

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


