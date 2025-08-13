from __future__ import annotations


import sqlite3
from pathlib import Path

from backend.exercise import Exercise

# Default path to the bundled SQLite database (relative to repo root)
DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workout.db"

# Will hold preset data loaded from the database. Each item is a dict with
#   {'name': <preset name>,
#    'exercises': [{'name': <exercise name>, 'sets': <number_of_sets>}, ...]}
WORKOUT_PRESETS: list[dict] = []


def load_workout_presets(db_path: Path = DEFAULT_DB_PATH) -> list[dict]:
    """Load workout presets from the SQLite database into WORKOUT_PRESETS."""
    global WORKOUT_PRESETS

    with sqlite3.connect(str(db_path)) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name FROM preset_presets WHERE deleted = 0 ORDER BY id"
        )
        presets: list[dict] = []
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
    exercise: Exercise,
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
