import sqlite3
from pathlib import Path
import time
import re
import copy
import json

# Number of sets each exercise defaults to when starting a workout
DEFAULT_SETS_PER_EXERCISE = 3

# Default rest duration between sets in seconds
DEFAULT_REST_DURATION = 120

# Default path to the bundled SQLite database
DEFAULT_DB_PATH = Path(__file__).resolve().parent / "data" / "workout.db"

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
        metric_id,
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
            }
            )

        # Apply overrides for a specific preset if requested
        if preset_name:
            cursor.execute(
            """
            SELECT sem.metric_name, sem.input_timing, sem.is_required, sem.scope
            FROM preset_exercise_metrics sem
            JOIN preset_section_exercises se ON sem.section_exercise_id = se.id
            JOIN preset_preset_sections s ON se.section_id = s.id
            JOIN preset_presets p ON s.preset_id = p.id
            WHERE p.name = ? AND se.exercise_name = ?
              AND sem.deleted = 0 AND se.deleted = 0 AND s.deleted = 0 AND p.deleted = 0
            """,
                (preset_name, exercise_name),
            )
            overrides = {
                name: {
                    "input_timing": input_timing,
                    "is_required": bool(is_required),
                    "scope": scope,
                }
                for name, input_timing, is_required, scope in cursor.fetchall()
            }
            for m in metrics:
                if m["name"] in overrides:
                    m.update(overrides[m["name"]])

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
            "SELECT id, type FROM library_metric_types WHERE name = ? AND deleted = 0",
            (metric_type_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric '{metric_type_name}' not found")
        metric_type_id, def_type = row

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
                    (section_exercise_id, metric_name, type, input_timing, is_required, scope, enum_values_json, library_metric_type_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    se_id,
                    metric_type_name,
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


class WorkoutSession:
    """In-memory representation of a workout session.

    The session loads the selected preset from the database when it is
    created.  While the workout is running it manages state in memory and
    never writes to the database.  It may read additional information from
    the database if needed but will not modify any tables until the workout
    is finished, at which point the completed session is saved.
    """

    def __init__(
        self,
        preset_name: str,
        db_path: Path = DEFAULT_DB_PATH,
        rest_duration: int = DEFAULT_REST_DURATION,
    ):
        """Load ``preset_name`` from ``db_path`` and prepare the session."""

        self.preset_name = preset_name
        presets = load_workout_presets(db_path)
        preset = next((p for p in presets if p["name"] == preset_name), None)
        if not preset:
            raise ValueError(f"Preset '{preset_name}' not found")

        self.exercises = [
            {
                "name": ex["name"],
                "sets": ex.get("sets", DEFAULT_SETS_PER_EXERCISE),
                "results": [],
            }
            for ex in preset["exercises"]
        ]

        self.current_exercise = 0
        self.current_set = 0
        self.start_time = time.time()
        self.end_time = None

        self.rest_duration = rest_duration
        self.last_set_time = self.start_time
        self.rest_target_time = self.last_set_time + self.rest_duration

    def mark_set_completed(self) -> None:
        """Record the completion time for the current set."""
        self.last_set_time = time.time()
        self.rest_target_time = self.last_set_time + self.rest_duration

    def next_exercise_name(self):
        if self.current_exercise < len(self.exercises):
            return self.exercises[self.current_exercise]["name"]
        return ""

    def next_exercise_display(self):
        if self.current_exercise < len(self.exercises):
            ex = self.exercises[self.current_exercise]
            return f"{ex['name']} set {self.current_set + 1} of {ex['sets']}"
        return ""

    def upcoming_exercise_name(self):
        """Return the exercise name for the next set to be performed."""
        if self.current_exercise >= len(self.exercises):
            return ""
        ex_idx = self.current_exercise
        set_idx = self.current_set + 1
        if set_idx >= self.exercises[ex_idx]["sets"]:
            ex_idx += 1
            set_idx = 0
        if ex_idx < len(self.exercises):
            return self.exercises[ex_idx]["name"]
        return ""

    def upcoming_exercise_display(self):
        """Return display string for the next set to be performed."""
        if self.current_exercise >= len(self.exercises):
            return ""
        ex_idx = self.current_exercise
        set_idx = self.current_set + 1
        if set_idx >= self.exercises[ex_idx]["sets"]:
            ex_idx += 1
            set_idx = 0
        if ex_idx < len(self.exercises):
            ex = self.exercises[ex_idx]
            return f"{ex['name']} set {set_idx + 1} of {ex['sets']}"
        return ""

    def record_metrics(self, metrics):
        if self.current_exercise >= len(self.exercises):
            if self.end_time is None:
                self.end_time = time.time()
            return True

        ex = self.exercises[self.current_exercise]
        ex["results"].append(metrics)
        self.current_set += 1

        if self.current_set >= ex["sets"]:
            self.current_set = 0
            self.current_exercise += 1

        if self.current_exercise >= len(self.exercises):
            self.end_time = time.time()
            return True

        return False

    def adjust_rest_timer(self, seconds: int) -> None:
        """Adjust the target time for the current rest period."""
        now = time.time()
        if self.rest_target_time <= now:
            self.rest_target_time = now
        self.rest_target_time += seconds
        if self.rest_target_time <= now:
            self.rest_target_time = now

    def rest_remaining(self) -> float:
        """Return seconds remaining in the current rest period."""
        return max(0.0, self.rest_target_time - time.time())

    def summary(self) -> str:
        """Return a formatted text summary of the session."""

        end_time = self.end_time or time.time()
        lines = [f"Workout: {self.preset_name}"]
        start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time))
        end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
        dur = int(end_time - self.start_time)
        m, s = divmod(dur, 60)
        lines.append(f"Start: {start}")
        lines.append(f"End:   {end}")
        lines.append(f"Duration: {m}m {s}s")
        for ex in self.exercises:
            lines.append(f"\n{ex['name']}")
            for idx, metrics in enumerate(ex["results"], 1):
                metrics_text = ", ".join(f"{k}: {v}" for k, v in metrics.items())
                lines.append(f"  Set {idx}: {metrics_text}")
        return "\n".join(lines)


class Exercise:
    """Editable exercise loaded from the database.

    This is a lightweight helper used by the ``EditExerciseScreen``.  It
    mirrors the details stored in the database and keeps all modifications
    in memory.  The database is updated only when the caller explicitly
    chooses to persist the changes.
    """

    def __init__(
        self,
        name: str = "",
        *,
        db_path: Path = DEFAULT_DB_PATH,
        is_user_created: bool | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.name: str = name
        self.description: str = ""
        self.metrics: list[dict] = []
        self.is_user_created: bool = True
        self._original: dict | None = None

        if name:
            self.load(name, is_user_created=is_user_created)
        else:
            self._original = self.to_dict()

    def load(self, name: str, *, is_user_created: bool | None = None) -> None:
        """Load ``name`` from ``db_path`` into this object."""

        details = get_exercise_details(name, self.db_path, is_user_created)
        if details:
            self.name = details.get("name", name)
            self.description = details.get("description", "")
            self.is_user_created = details.get("is_user_created", True)
        else:
            self.is_user_created = (
                bool(is_user_created) if is_user_created is not None else True
            )
        self.metrics = get_metrics_for_exercise(
            name,
            db_path=self.db_path,
            is_user_created=(
                details.get("is_user_created") if details else is_user_created
            ),
        )
        self._original = self.to_dict()

    # ------------------------------------------------------------------
    # Modification helpers.  These operate only on the in-memory object
    # until the exercise is explicitly saved back to the database.
    # ------------------------------------------------------------------
    def add_metric(self, metric: dict) -> None:
        """Append ``metric`` to the metrics list."""

        self.metrics.append(metric)

    def remove_metric(self, metric_name: str) -> None:
        """Remove metric with ``metric_name`` if present."""

        self.metrics = [m for m in self.metrics if m.get("name") != metric_name]

    def update_metric(self, metric_name: str, **updates) -> None:
        """Update metric named ``metric_name`` with ``updates``."""

        for metric in self.metrics:
            if metric.get("name") == metric_name:
                metric.update(updates)
                break

    def to_dict(self) -> dict:
        """Return a ``dict`` representation of the exercise."""

        return {
            "name": self.name,
            "description": self.description,
            "metrics": [m.copy() for m in self.metrics],
        }

    def is_modified(self) -> bool:
        """Return ``True`` if the exercise differs from its original state."""

        return self._original != self.to_dict()

    def mark_saved(self) -> None:
        """Reset the original state to the current data."""

        self._original = self.to_dict()

    def had_metric(self, metric_name: str) -> bool:
        """Return ``True`` if ``metric_name`` existed when loaded."""

        if not self._original:
            return False
        for m in self._original.get("metrics", []):
            if m.get("name") == metric_name:
                return True
        return False


def save_exercise(exercise: Exercise) -> None:
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
                        json.dumps(m.get("values")) if m.get("values") and (m.get("type") or default_type) == "enum" else None
    
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
            "UPDATE library_metric_types SET deleted = 1 WHERE id = ?",
            (mt_id,),
        )
        conn.commit()
        return True

class PresetEditor:
    """Helper for creating or editing workout presets in memory."""

    def __init__(
        self,
        preset_name: str | None = None,
        db_path: Path = DEFAULT_DB_PATH,
    ):
        """Create the editor and optionally load an existing preset."""

        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))

        self.preset_name: str = preset_name or ""
        self.sections: list[dict] = []
        self.preset_metrics: list[dict] = []
        self._preset_id: int | None = None
        self._original: dict | None = None

        if preset_name:
            self.load(preset_name)
        else:
            self._load_required_metrics()
            self._original = self.to_dict()

    def _load_required_metrics(self) -> None:
        """Load required preset metric types into ``preset_metrics``."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT name, description, type,
                   input_timing, is_required, scope, enum_values_json

              FROM library_metric_types
             WHERE deleted = 0 AND is_required = 1
               AND scope IN ('preset', 'session')
            ORDER BY id
            """
        )
        for (
            name,
            desc,
            mtype,
            timing,
            req,
            scope,
            enum_json,
        ) in cursor.fetchall():
            values = []
            if mtype == "enum" and enum_json:
                try:
                    values = json.loads(enum_json)
                except Exception:
                    values = []
            self.preset_metrics.append(
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": timing,
                    "is_required": bool(req),
                    "scope": scope,
                    "description": desc,
                    "values": values,
                    "value": None,
                }
            )

    def load(self, preset_name: str) -> None:
        """Load ``preset_name`` from the database into memory."""

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
            (preset_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Preset '{preset_name}' not found")

        preset_id = row[0]
        cursor.execute(
            "SELECT id, name FROM preset_preset_sections WHERE preset_id = ? AND deleted = 0 ORDER BY position",
            (preset_id,),
        )

        self.preset_name = preset_name
        self.sections.clear()
        self.preset_metrics.clear()

        for section_id, name in cursor.fetchall():
            cursor.execute(
                """
                SELECT id, exercise_name, number_of_sets, rest_time, library_exercise_id
                  FROM preset_section_exercises
                 WHERE section_id = ? AND deleted = 0
                 ORDER BY position
                """,
                (section_id,),
            )
            exercises = []
            for ex_id, ex_name, sets, rest, lib_id in cursor.fetchall():
                exercises.append(
                    {
                        "id": ex_id,
                        "name": ex_name,
                        "sets": sets,
                        "rest": rest,
                        "library_id": lib_id,
                    }
                )
            self.sections.append({"name": name, "exercises": exercises})

        cursor.execute(
            """
            SELECT mt.name, pm.value, pm.type,
                   pm.input_timing, pm.is_required, pm.scope,
                   pm.enum_values_json, mt.description
              FROM preset_preset_metrics pm
              JOIN library_metric_types mt ON mt.id = pm.library_metric_type_id
             WHERE pm.preset_id = ? AND pm.deleted = 0 AND mt.deleted = 0
             ORDER BY pm.position
            """,
            (preset_id,),
        )
        for (
            name,
            value,
            mtype,
            timing,
            req,
            scope,
            enum_json,
            desc,
        ) in cursor.fetchall():
            if mtype == "int":
                try:
                    value = int(value)
                except Exception:
                    value = 0
            elif mtype in ("float", "slider"):
                try:
                    value = float(value)
                except Exception:
                    value = 0.0
            values = []
            if mtype == "enum" and enum_json:
                try:
                    values = json.loads(enum_json)
                except Exception:
                    values = []
            self.preset_metrics.append(
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": _from_db_timing(timing),
                    "is_required": bool(req),
                    "scope": scope,
                    "description": desc,
                    "values": values,
                    "value": value,
                }
            )

        self._preset_id = preset_id
        self._original = self.to_dict()

    def add_section(self, name: str = "Section") -> int:
        """Add a new section and return its index."""

        self.sections.append({"name": name, "exercises": []})
        return len(self.sections) - 1

    def remove_section(self, index: int) -> None:
        """Remove the section at ``index`` if it exists."""

        if 0 <= index < len(self.sections):
            self.sections.pop(index)

    def rename_section(self, index: int, name: str) -> None:
        """Rename the section at ``index`` to ``name``."""

        if index < 0 or index >= len(self.sections):
            raise IndexError("Section index out of range")
        self.sections[index]["name"] = name

    def add_exercise(
        self,
        section_index: int,
        exercise_name: str,
        sets: int = DEFAULT_SETS_PER_EXERCISE,
        rest: int = DEFAULT_REST_DURATION,
    ) -> dict:
        """Add an exercise to the specified section."""

        if section_index < 0 or section_index >= len(self.sections):
            raise IndexError("Section index out of range")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
            (exercise_name,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Exercise '{exercise_name}' does not exist")

        ex = {
            "id": None,
            "name": exercise_name,
            "sets": sets,
            "rest": rest,
            "library_id": row[0],
        }
        self.sections[section_index]["exercises"].append(ex)
        return ex

    def update_exercise(
        self,
        section_index: int,
        exercise_index: int,
        *,
        sets: int | None = None,
        rest: int | None = None,
    ) -> None:
        """Update sets or rest time for an exercise in the preset."""

        if (
            section_index < 0
            or section_index >= len(self.sections)
            or exercise_index < 0
            or exercise_index >= len(self.sections[section_index]["exercises"])
        ):
            raise IndexError("Exercise index out of range")

        exercise = self.sections[section_index]["exercises"][exercise_index]
        if sets is not None:
            exercise["sets"] = sets
        if rest is not None:
            exercise["rest"] = rest

    def remove_exercise(self, section_index: int, exercise_index: int) -> None:
        """Remove an exercise from ``section_index`` at ``exercise_index``."""

        if (
            section_index < 0
            or section_index >= len(self.sections)
            or exercise_index < 0
            or exercise_index >= len(self.sections[section_index]["exercises"])
        ):
            raise IndexError("Exercise index out of range")

        self.sections[section_index]["exercises"].pop(exercise_index)

    def move_exercise(self, section_index: int, old_index: int, new_index: int) -> None:
        """Move an exercise within a section to ``new_index``."""

        if (
            section_index < 0
            or section_index >= len(self.sections)
            or old_index < 0
            or old_index >= len(self.sections[section_index]["exercises"])
            or new_index < 0
            or new_index >= len(self.sections[section_index]["exercises"])
        ):
            raise IndexError("Exercise index out of range")

        exercises = self.sections[section_index]["exercises"]
        ex = exercises.pop(old_index)
        exercises.insert(new_index, ex)

    # ------------------------------------------------------------------
    # Preset metric helpers
    # ------------------------------------------------------------------
    def add_metric(self, metric_name: str, *, value=None) -> None:
        """Add a metric defined in ``library_metric_types`` by name."""

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT description, type, input_timing,
                   scope, is_required, enum_values_json
              FROM library_metric_types
             WHERE name = ? AND deleted = 0
            """,
            (metric_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric '{metric_name}' not found")
        (
            desc,
            mtype,
            timing,
            scope,
            req,
            enum_json,
        ) = row
        values = []
        if mtype == "enum" and enum_json:
            try:
                values = json.loads(enum_json)
            except Exception:
                values = []
        self.preset_metrics.append(
            {
                "name": metric_name,
                "type": mtype,
                "input_timing": timing,
                "is_required": bool(req),
                "scope": scope,
                "description": desc,
                "values": values,
                "value": value,
            }
        )

    def remove_metric(self, metric_name: str) -> None:
        """Remove metric with ``metric_name`` if present."""

        self.preset_metrics = [m for m in self.preset_metrics if m.get("name") != metric_name]

    def update_metric(self, metric_name: str, **updates) -> None:
        """Update metric named ``metric_name`` with ``updates``."""

        for metric in self.preset_metrics:
            if metric.get("name") == metric_name:
                metric.update(updates)
                break

    def to_dict(self) -> dict:
        """Return the preset data as a dictionary."""

        result = {
            "name": self.preset_name,
            "sections": [],
            "preset_metrics": copy.deepcopy(self.preset_metrics),
        }
        for sec in self.sections:
            ex_list = []
            for ex in sec.get("exercises", []):
                ex_copy = {k: v for k, v in ex.items() if k not in {"id", "library_id"}}
                ex_list.append(copy.deepcopy(ex_copy))
            result["sections"].append({"name": sec.get("name"), "exercises": ex_list})
        return result

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Modification tracking helpers
    # ------------------------------------------------------------------
    def is_modified(self) -> bool:
        """Return ``True`` if the preset differs from the original state."""

        return self._original != self.to_dict()

    def mark_saved(self) -> None:
        """Record the current state as the saved state."""

        self._preset_id = self._preset_id  # keep mypy happy
        self._original = self.to_dict()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def save(self) -> None:
        """Write the current preset to the database."""

        if not self.preset_name.strip():
            raise ValueError("Preset name cannot be empty")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
            (self.preset_name,),
        )
        row = cursor.fetchone()
        if row and (self._preset_id is None or row[0] != self._preset_id):
            raise ValueError("A preset with that name already exists")

        if row:
            preset_id = row[0]
            self._preset_id = preset_id
            cursor.execute(
                "SELECT id FROM preset_preset_sections WHERE preset_id = ? AND deleted = 0 ORDER BY position",
                (preset_id,),
            )
            sec_ids = [r[0] for r in cursor.fetchall()]
            cursor.execute(
                "UPDATE preset_presets SET name = ? WHERE id = ?",
                (self.preset_name, preset_id),
            )
        else:
            cursor.execute(
                "INSERT INTO preset_presets (name) VALUES (?)",
                (self.preset_name,),
            )
            preset_id = cursor.lastrowid
            self._preset_id = preset_id
            sec_ids = []

        for sec_pos, sec in enumerate(self.sections):
            if sec_pos < len(sec_ids):
                section_id = sec_ids[sec_pos]
                cursor.execute(
                    "UPDATE preset_preset_sections SET name = ?, position = ?, deleted = 0 WHERE id = ?",
                    (sec.get("name", f"Section {sec_pos + 1}"), sec_pos, section_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO preset_preset_sections (preset_id, name, position) VALUES (?, ?, ?)",
                    (preset_id, sec.get("name", f"Section {sec_pos + 1}"), sec_pos),
                )
                section_id = cursor.lastrowid

            cursor.execute(
                "SELECT id, exercise_name, number_of_sets, rest_time, position, library_exercise_id FROM preset_section_exercises WHERE section_id = ? AND deleted = 0",
                (section_id,),
            )
            existing = {
                row_id: {
                    "name": n,
                    "sets": s,
                    "rest": r,
                    "pos": p,
                    "library_id": lib,
                }
                for row_id, n, s, r, p, lib in cursor.fetchall()
            }
            unused = set(existing.keys())

            for ex_pos, ex in enumerate(sec.get("exercises", [])):
                cursor.execute(
                    "SELECT id, description FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                    (ex["name"],),
                )
                lr = cursor.fetchone()
                if lr is None:
                    raise ValueError(f"Exercise '{ex['name']}' does not exist")
                lib_id, desc = lr[0], lr[1] or ""

                ex_id = ex.get("id")
                sets_val = ex.get("sets", DEFAULT_SETS_PER_EXERCISE)
                rest_val = ex.get("rest", DEFAULT_REST_DURATION)

                if ex_id is not None and ex_id in existing:
                    row = existing[ex_id]
                    unused.discard(ex_id)
                    if (
                        row["name"] == ex["name"]
                        and row["sets"] == sets_val
                        and row["rest"] == rest_val
                        and row["library_id"] == lib_id
                    ):
                        if row["pos"] != ex_pos:
                            cursor.execute(
                                "UPDATE preset_section_exercises SET position = ? WHERE id = ?",
                                (ex_pos, ex_id),
                            )
                    else:
                        cursor.execute(
                            "UPDATE preset_section_exercises SET exercise_name = ?, exercise_description = ?, number_of_sets = ?, rest_time = ?, position = ?, library_exercise_id = ?, deleted = 0 WHERE id = ?",
                            (
                                ex["name"],
                                desc,
                                sets_val,
                                rest_val,
                                ex_pos,
                                lib_id,
                                ex_id,
                            ),
                        )

                        if row["library_id"] != lib_id:
                            cursor.execute(
                                "UPDATE preset_exercise_metrics SET deleted = 1 WHERE section_exercise_id = ?",
                                (ex_id,),
                            )
                            cursor.execute(
                            """
                            SELECT mt.name,
                                   COALESCE(em.type, mt.type),
                                   COALESCE(em.input_timing, mt.input_timing),
                                   COALESCE(em.is_required, mt.is_required),
                                   COALESCE(em.scope, mt.scope),
                                   COALESCE(em.enum_values_json, mt.enum_values_json),
                                  em.position,
                                  mt.id
                              FROM library_exercise_metrics em
                              JOIN library_metric_types mt ON em.metric_type_id = mt.id
                             WHERE em.exercise_id = ?
                             ORDER BY em.position
                            """,
                            (lib_id,),
                        )
                        for (
                            mt_name,
                            m_input,

                            m_timing,
                            m_req,
                            m_scope,
                            m_enum_json,
                            mpos,
                            mt_id,
                        ) in cursor.fetchall():
                            cursor.execute(
                                """INSERT INTO preset_exercise_metrics (section_exercise_id, metric_name, type, input_timing, is_required, scope, enum_values_json, position, library_metric_type_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (
                                    ex_id,
                                    mt_name,
                                    m_input,

                                    m_timing,
                                    m_req,
                                    m_scope,
                                    m_enum_json,
                                    mpos,
                                    mt_id,
                                ),
                            )
                else:
                    cursor.execute(
                        """INSERT INTO preset_section_exercises (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id, rest_time) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            section_id,
                            ex["name"],
                            desc,
                            ex_pos,
                            sets_val,
                            lib_id,
                            rest_val,
                        ),
                    )
                    ex_id = cursor.lastrowid
                    ex["id"] = ex_id

                    cursor.execute(
                        """
                        SELECT mt.name,
                               COALESCE(em.type, mt.type),
                               COALESCE(em.input_timing, mt.input_timing),
                               COALESCE(em.is_required, mt.is_required),
                               COALESCE(em.scope, mt.scope),
                               COALESCE(em.enum_values_json, mt.enum_values_json),
                               em.position,
                               mt.id
                          FROM library_exercise_metrics em
                          JOIN library_metric_types mt ON em.metric_type_id = mt.id
                         WHERE em.exercise_id = ?
                         ORDER BY em.position
                        """,
                        (lib_id,),
                    )
                    for (
                        mt_name,
                        m_input,

                        m_timing,
                        m_req,
                        m_scope,
                        m_enum_json,
                        mpos,
                        mt_id,
                    ) in cursor.fetchall():
                        cursor.execute(
                            """INSERT INTO preset_exercise_metrics (section_exercise_id, metric_name, type, input_timing, is_required, scope, enum_values_json, position, library_metric_type_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                ex_id,
                                mt_name,
                                m_input,

                                m_timing,
                                m_req,
                                m_scope,
                                m_enum_json,
                                mpos,
                                mt_id,
                            ),
                        )

            for old_id in unused:
                cursor.execute(
                    "UPDATE preset_exercise_metrics SET deleted = 1 WHERE section_exercise_id = ?",
                    (old_id,),
                )
                cursor.execute(
                    "UPDATE preset_section_exercises SET deleted = 1 WHERE id = ?",
                    (old_id,),
                )

        for sid in sec_ids[len(self.sections):]:
            cursor.execute(
                "SELECT id FROM preset_section_exercises WHERE section_id = ? AND deleted = 0",
                (sid,),
            )
            ex_ids = [r[0] for r in cursor.fetchall()]
            for eid in ex_ids:
                cursor.execute(
                    "UPDATE preset_exercise_metrics SET deleted = 1 WHERE section_exercise_id = ?",
                    (eid,),
                )
                cursor.execute(
                    "UPDATE preset_section_exercises SET deleted = 1 WHERE id = ?",
                    (eid,),
                )
            cursor.execute(
                "UPDATE preset_preset_sections SET deleted = 1 WHERE id = ?",
                (sid,),
            )

        cursor.execute(
            "SELECT id, library_metric_type_id FROM preset_preset_metrics"
            " WHERE preset_id = ? AND deleted = 0",
            (preset_id,),
        )
        existing = {lm_id: row_id for row_id, lm_id in cursor.fetchall()}

        for pos, metric in enumerate(self.preset_metrics):
            cursor.execute(
                "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0",
                (metric.get("name"),),
            )
            row = cursor.fetchone()
            if not row:
                continue
            mt_id = row[0]
            enum_json = (
                json.dumps(metric.get("values"))
                if metric.get("type") == "enum" and metric.get("values")
                else None
            )

            if mt_id in existing:
                cursor.execute(
                    """
                    UPDATE preset_preset_metrics
                       SET type = ?,
                           input_timing = ?,
                           scope = ?,
                           is_required = ?,
                           enum_values_json = ?,
                           position = ?,
                           value = ?,
                           deleted = 0
                     WHERE id = ?
                    """,
                    (
                        metric.get("type"),
                        _to_db_timing(metric.get("input_timing")),
                        metric.get("scope"),
                        int(metric.get("is_required", False)),
                        enum_json,
                        pos,
                        str(metric.get("value")) if metric.get("value") is not None else None,
                        existing.pop(mt_id),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO preset_preset_metrics
                        (
                            preset_id,
                            library_metric_type_id,
                            type,
                            input_timing,
                            scope,
                            is_required,
                            enum_values_json,
                            position,
                            value
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        preset_id,
                        mt_id,
                        metric.get("type"),
                        _to_db_timing(metric.get("input_timing")),
                        metric.get("scope"),
                        int(metric.get("is_required", False)),
                        enum_json,
                        pos,
                        str(metric.get("value")) if metric.get("value") is not None else None,
                    ),
                )

        for remaining_id in existing.values():
            cursor.execute(
                "UPDATE preset_preset_metrics SET deleted = 1 WHERE id = ?",
                (remaining_id,),
            )

        self.conn.commit()
        self.mark_saved()
