"""Session-related helpers extracted from :mod:`core`.

This module provides utilities for validating and persisting a completed
workout session.  It was migrated from the monolithic ``core`` module to
keep responsibilities separated and the code base easier to maintain.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import TYPE_CHECKING

from backend.utils import _to_db_timing
from core import DEFAULT_DB_PATH

if TYPE_CHECKING:  # pragma: no cover - for type checkers only
    from backend.workout_session import WorkoutSession


def get_session_history(limit: int | None = None, db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Return past workout sessions.

    Results are ordered with the most recent session first. Each item in the
    returned list contains ``preset_name`` and ``started_at`` keys. When
    ``limit`` is provided only that many newest sessions are returned.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        query = (
            "SELECT preset_name, started_at FROM session_sessions "
            "WHERE deleted = 0 AND ended_at IS NOT NULL "
            "ORDER BY started_at DESC"
        )
        if limit is not None:
            cursor.execute(query + " LIMIT ?", (limit,))
        else:
            cursor.execute(query)
        rows = cursor.fetchall()
    return [{"preset_name": name, "started_at": ts} for name, ts in rows]


def get_session_details(started_at: float, db_path: Path = DEFAULT_DB_PATH) -> dict:
    """Return full details for the session that started at ``started_at``.

    The returned mapping contains ``preset_name``, ``started_at``,
    ``ended_at`` along with lists of ``metrics`` and ``exercises``.
    Each exercise includes its ``name`` and a list of ``sets``.  Every set
    entry exposes ``number``, ``metrics`` (name/value pairs), ``duration`` in
    seconds and ``rest`` time since the previous set.
    """

    with sqlite3.connect(str(db_path)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, preset_name, started_at, ended_at
            FROM session_sessions
            WHERE started_at = ? AND deleted = 0
            """,
            (started_at,),
        )
        row = cur.fetchone()
        if row is None:
            return {}
        session_id, preset_name, started, ended = row

        # session level metrics
        cur.execute(
            """
            SELECT metric_name, value
            FROM session_session_metrics
            WHERE session_id = ? AND deleted = 0
            ORDER BY position
            """,
            (session_id,),
        )
        metrics = [{"name": n, "value": v} for n, v in cur.fetchall()]

        # gather exercises
        cur.execute(
            """
            SELECT e.id, e.exercise_name
            FROM session_section_exercises e
            JOIN session_session_sections s ON e.section_id = s.id
            WHERE s.session_id = ? AND e.deleted = 0 AND s.deleted = 0
            ORDER BY s.position, e.position
            """,
            (session_id,),
        )
        exercises: list[dict] = []
        for ex_id, ex_name in cur.fetchall():
            cur.execute(
                """
                SELECT id, set_number, started_at, ended_at
                FROM session_exercise_sets
                WHERE section_exercise_id = ? AND deleted = 0
                ORDER BY set_number
                """,
                (ex_id,),
            )
            sets: list[dict] = []
            prev_end: float | None = None
            for set_id, num, s_start, s_end in cur.fetchall():
                duration = (s_end - s_start) if s_start is not None and s_end is not None else None
                rest = (s_start - prev_end) if prev_end and s_start else None
                prev_end = s_end if s_end is not None else prev_end
                cur.execute(
                    """
                    SELECT m.metric_name, sm.value
                    FROM session_set_metrics sm
                    JOIN session_exercise_metrics m ON sm.exercise_metric_id = m.id
                    WHERE sm.exercise_set_id = ? AND sm.deleted = 0 AND m.deleted = 0
                    ORDER BY m.position
                    """,
                    (set_id,),
                )
                set_metrics = [{"name": n, "value": v} for n, v in cur.fetchall()]
                sets.append(
                    {
                        "number": num,
                        "metrics": set_metrics,
                        "duration": duration,
                        "rest": rest,
                    }
                )
            exercises.append({"name": ex_name, "sets": sets})

    return {
        "preset_name": preset_name,
        "started_at": started,
        "ended_at": ended,
        "metrics": metrics,
        "exercises": exercises,
    }

def validate_workout_session(session: "WorkoutSession") -> list[str]:
    """Return a list of validation errors for ``session``.

    Previously every exercise had to contain results for all planned sets
    before a session could be saved, which caused partially completed
    workouts to raise errors.  Validation now only ensures an ``end_time``
    exists so that sessions can be saved even when some sets were skipped.
    """

    if session.end_time is None:
        return ["Session has not been completed"]
    return []


def save_completed_session(session: "WorkoutSession", db_path: Path | None = None) -> None:
    """Persist a finished ``session`` to the database.

    The provided ``session`` must already be validated.  When ``db_path`` is
    omitted the path associated with the session object is used.
    """

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
                        INSERT INTO session_set_metrics (exercise_set_id, exercise_metric_id, value)
                        VALUES (?, ?, ?)
                        """,
                        (set_id, metric_id, str(value)),
                    )
    session.saved = True
    session.clear_recovery_state(session.recovery_base)

