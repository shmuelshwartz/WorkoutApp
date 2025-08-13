"""Session-related helpers.

This module contains utilities for validating and saving completed workout
sessions.  The functionality was originally implemented in ``core.py`` and has
been migrated here for better separation of concerns.
"""

from __future__ import annotations

from pathlib import Path
import sqlite3
import time
import json

from core import _to_db_timing


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


def save_completed_session(session: "WorkoutSession", db_path: Path | None = None) -> None:
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

