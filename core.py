import sqlite3
from pathlib import Path
import time
import re

# Number of sets each exercise defaults to when starting a workout
DEFAULT_SETS_PER_EXERCISE = 2

# Default rest duration between sets in seconds
DEFAULT_REST_DURATION = 20

# Will hold preset data loaded from the database. Each item is a dict with
#   {'name': <preset name>,
#    'exercises': [{'name': <exercise name>, 'sets': <number_of_sets>}, ...]}
WORKOUT_PRESETS = []

def load_workout_presets(db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db"):
    """Load workout presets from the SQLite database into WORKOUT_PRESETS."""
    global WORKOUT_PRESETS

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM presets ORDER BY id")
    presets = []
    for preset_id, preset_name in cursor.fetchall():
        cursor.execute(
            """
            SELECT e.name, se.number_of_sets
            FROM sections s
            JOIN section_exercises se ON se.section_id = s.id
            JOIN exercises e ON se.exercise_id = e.id
            WHERE s.preset_id = ?
            ORDER BY s.position, se.position
            """,
            (preset_id,),
        )
        exercises = [
            {"name": row[0], "sets": row[1]} for row in cursor.fetchall()
        ]
        presets.append({"name": preset_name, "exercises": exercises})
    conn.close()
    WORKOUT_PRESETS = presets
    return presets


def get_all_exercises(
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
    *,
    include_user_created: bool = False,
) -> list:
    """Return a list of all exercise names.

    If ``include_user_created`` is ``True`` the returned list will contain
    ``(name, is_user_created)`` tuples instead of just names.
    """

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    if include_user_created:
        cursor.execute("SELECT name, is_user_created FROM exercises ORDER BY name")
        rows = cursor.fetchall()
        exercises = [(name, bool(flag)) for name, flag in rows]
    else:
        cursor.execute("SELECT name FROM exercises ORDER BY name")
        exercises = [row[0] for row in cursor.fetchall()]
    conn.close()
    return exercises


def get_exercise_details(
    exercise_name: str,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> dict | None:
    """Return name and description for ``exercise_name``.

    Returns ``None`` if the exercise does not exist.
    """

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT name, description FROM exercises WHERE name = ?",
        (exercise_name,),
    )
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    name, description = row
    return {"name": name, "description": description or ""}


def get_metrics_for_exercise(
    exercise_name: str,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
    preset_name: str | None = None,
) -> list:
    """Return metric definitions for ``exercise_name``.

    Each item in the returned list is a dictionary with ``name``, ``input_type``,
    ``source_type`` and ``values`` keys. ``values`` will contain any allowed
    values for ``manual_enum`` metrics.
    """

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return []
    exercise_id = row[0]

    cursor.execute(
        """
        SELECT mt.id, mt.name, mt.input_type, mt.source_type,
               mt.input_timing, mt.is_required, mt.scope, mt.description
        FROM exercise_metrics em
        JOIN metric_types mt ON mt.id = em.metric_type_id
        WHERE em.exercise_id = ?
        ORDER BY em.id
        """,
        (exercise_id,),
    )

    metrics = []
    for (
        metric_id,
        name,
        input_type,
        source_type,
        input_timing,
        is_required,
        scope,
        description,
    ) in cursor.fetchall():
        values = []
        if source_type == "manual_enum":
            cursor.execute(
                """
                SELECT value
                FROM user_defined_enum_values
                WHERE metric_type_id = ? AND exercise_id = ?
                ORDER BY position
                """,
                (metric_id, exercise_id),
            )
            values = [v[0] for v in cursor.fetchall()]
        metrics.append(
            {
                "name": name,
                "input_type": input_type,
                "source_type": source_type,
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
            SELECT mt.name, sem.input_timing, sem.is_required, sem.scope
            FROM section_exercise_metrics sem
            JOIN section_exercises se ON sem.section_exercise_id = se.id
            JOIN sections s ON se.section_id = s.id
            JOIN presets p ON s.preset_id = p.id
            JOIN exercises e ON se.exercise_id = e.id
            JOIN metric_types mt ON sem.metric_type_id = mt.id
            WHERE p.name = ? AND e.id = ?
            """,
            (preset_name, exercise_id),
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

    conn.close()
    return metrics


def get_all_metric_types(
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> list:
    """Return all metric type definitions from the database."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT name, input_type, source_type, input_timing,
               is_required, scope, description
        FROM metric_types
        ORDER BY id
        """
    )
    metric_types = [
        {
            "name": name,
            "input_type": input_type,
            "source_type": source_type,
            "input_timing": input_timing,
            "is_required": bool(is_required),
            "scope": scope,
            "description": description,
        }
        for (
            name,
            input_type,
            source_type,
            input_timing,
            is_required,
            scope,
            description,
        ) in cursor.fetchall()
    ]
    conn.close()
    return metric_types


def get_metric_type_schema(
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> list:
    """Return column definitions for the ``metric_types`` table.

    Each item is a dictionary with ``name`` and optional ``options`` keys. The
    ``options`` list will contain allowed values if the column has a CHECK
    constraint enumerating them.
    """

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='metric_types'"
    )
    row = cursor.fetchone()
    conn.close()
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
        if name in {"id", "is_user_created"}:
            continue
        fields.append({"name": name})

    for field in fields:
        chk = re.search(
            rf'{field["name"]}[^,]*CHECK\(.*?{field["name"]}.*?IN \(([^)]*)\)\)',
            create_sql,
            re.DOTALL,
        )
        if chk:
            opts = [opt.strip().strip("'\"") for opt in chk.group(1).split(',')]
            field["options"] = opts
    return fields


def add_metric_type(
    name: str,
    input_type: str,
    source_type: str,
    input_timing: str,
    scope: str,
    description: str = "",
    is_required: bool = False,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> int:
    """Insert a new metric type and return its ID."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO metric_types
            (name, input_type, source_type, input_timing,
             is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
        """,
        (
            name,
            input_type,
            source_type,
            input_timing,
            int(is_required),
            scope,
            description,
        ),
    )
    metric_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return metric_id


def add_metric_to_exercise(
    exercise_name: str,
    metric_type_name: str,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> None:
    """Associate an existing metric type with an exercise."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Exercise '{exercise_name}' not found")
    exercise_id = row[0]

    cursor.execute("SELECT id FROM metric_types WHERE name = ?", (metric_type_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Metric type '{metric_type_name}' not found")
    metric_id = row[0]

    cursor.execute(
        "SELECT 1 FROM exercise_metrics WHERE exercise_id = ? AND metric_type_id = ?",
        (exercise_id, metric_id),
    )
    if cursor.fetchone() is None:
        cursor.execute(
            "INSERT INTO exercise_metrics (exercise_id, metric_type_id) VALUES (?, ?)",
            (exercise_id, metric_id),
        )
        conn.commit()
    conn.close()


def remove_metric_from_exercise(
    exercise_name: str,
    metric_type_name: str,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> None:
    """Remove a metric association from an exercise."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Exercise '{exercise_name}' not found")
    exercise_id = row[0]

    cursor.execute("SELECT id FROM metric_types WHERE name = ?", (metric_type_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Metric type '{metric_type_name}' not found")
    metric_id = row[0]

    cursor.execute(
        "DELETE FROM exercise_metrics WHERE exercise_id = ? AND metric_type_id = ?",
        (exercise_id, metric_id),
    )
    conn.commit()
    conn.close()


def update_metric_type(
    metric_type_name: str,
    *,
    input_type: str | None = None,
    source_type: str | None = None,
    input_timing: str | None = None,
    scope: str | None = None,
    description: str | None = None,
    is_required: bool | None = None,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> None:
    """Update fields of a metric type identified by ``metric_type_name``."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM metric_types WHERE name = ?", (metric_type_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Metric type '{metric_type_name}' not found")
    updates = []
    params: list = []
    if input_type is not None:
        updates.append("input_type = ?")
        params.append(input_type)
    if source_type is not None:
        updates.append("source_type = ?")
        params.append(source_type)
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
    if updates:
        params.append(metric_type_name)
        cursor.execute(f"UPDATE metric_types SET {', '.join(updates)} WHERE name = ?", params)
        conn.commit()
    conn.close()


def set_section_exercise_metric_override(
    preset_name: str,
    section_index: int,
    exercise_name: str,
    metric_type_name: str,
    *,
    input_timing: str,
    is_required: bool = False,
    scope: str = "set",
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
) -> None:
    """Apply an override for ``metric_type_name`` for a specific exercise in a preset."""

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM presets WHERE name = ?", (preset_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Preset '{preset_name}' not found")
    preset_id = row[0]

    cursor.execute(
        "SELECT id FROM sections WHERE preset_id = ? ORDER BY position", (preset_id,)
    )
    sections = cursor.fetchall()
    if section_index < 0 or section_index >= len(sections):
        conn.close()
        raise IndexError("Section index out of range")
    section_id = sections[section_index][0]

    cursor.execute("SELECT id FROM exercises WHERE name = ?", (exercise_name,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Exercise '{exercise_name}' not found")
    exercise_id = row[0]

    cursor.execute(
        "SELECT id FROM metric_types WHERE name = ?", (metric_type_name,)
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Metric '{metric_type_name}' not found")
    metric_type_id = row[0]

    cursor.execute(
        """SELECT id FROM section_exercises WHERE section_id = ? AND exercise_id = ? ORDER BY position LIMIT 1""",
        (section_id, exercise_id),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Exercise not part of section")
    se_id = row[0]

    cursor.execute(
        "SELECT id FROM section_exercise_metrics WHERE section_exercise_id = ? AND metric_type_id = ?",
        (se_id, metric_type_id),
    )
    row = cursor.fetchone()
    if row:
        cursor.execute(
            "UPDATE section_exercise_metrics SET input_timing = ?, is_required = ?, scope = ? WHERE id = ?",
            (input_timing, int(is_required), scope, row[0]),
        )
    else:
        cursor.execute(
            "INSERT INTO section_exercise_metrics (section_exercise_id, metric_type_id, input_timing, is_required, scope) VALUES (?, ?, ?, ?, ?)",
            (se_id, metric_type_id, input_timing, int(is_required), scope),
        )
    conn.commit()
    conn.close()


class WorkoutSession:
    """In-memory representation of a workout session.

    The session loads the selected preset from the database when it is
    created and then works entirely with the in-memory data structure.  No
    database access occurs after initialisation, so the database can be closed
    or moved while the workout is in progress.
    """

    def __init__(
        self,
        preset_name: str,
        db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
        rest_duration: int = DEFAULT_REST_DURATION,
    ):
        """Load ``preset_name`` from ``db_path`` and prepare the session."""

        self.preset_name = preset_name
        presets = load_workout_presets(db_path)
        preset = next((p for p in presets if p["name"] == preset_name), None)
        if not preset:
            raise ValueError(f"Preset '{preset_name}' not found")

        self.exercises = [
            {"name": ex["name"], "sets": ex.get("sets", DEFAULT_SETS_PER_EXERCISE), "results": []}
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
            for idx, metrics in enumerate(ex['results'], 1):
                metrics_text = ", ".join(f"{k}: {v}" for k, v in metrics.items())
                lines.append(f"  Set {idx}: {metrics_text}")
        return "\n".join(lines)


class Exercise:
    """Placeholder class for editing exercises.

    Editing or creating an exercise will be performed using an instance
    of this class. The database will only be queried when retrieving an
    existing exercise and when saving it after editing.
    """

    def __init__(self, name: str = "", description: str = "") -> None:
        self.name = name
        self.description = description

    def to_dict(self) -> dict:
        """Return the exercise data in dictionary form."""

        return {"name": self.name, "description": self.description}



class PresetEditor:
    """Helper for creating or editing workout presets in memory."""

    def __init__(
        self,
        preset_name: str | None = None,
        db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
    ):
        """Create the editor and optionally load an existing preset."""

        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))

        self.preset_name: str = preset_name or ""
        self.sections: list[dict] = []

        if preset_name:
            self.load(preset_name)

    def load(self, preset_name: str) -> None:
        """Load ``preset_name`` from the database into memory."""

        cursor = self.conn.cursor()
        cursor.execute("SELECT id FROM presets WHERE name = ?", (preset_name,))
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Preset '{preset_name}' not found")

        preset_id = row[0]
        cursor.execute(
            "SELECT id, name FROM sections WHERE preset_id = ? ORDER BY position",
            (preset_id,),
        )

        self.preset_name = preset_name
        self.sections.clear()

        for section_id, name in cursor.fetchall():
            cursor.execute(
                """
                SELECT e.name, se.number_of_sets
                FROM section_exercises se
                JOIN exercises e ON se.exercise_id = e.id
                WHERE se.section_id = ?
                ORDER BY se.position
                """,
                (section_id,),
            )
            exercises = [
                {"name": ex_name, "sets": sets} for ex_name, sets in cursor.fetchall()
            ]
            self.sections.append({"name": name, "exercises": exercises})

    def add_section(self, name: str = "Section") -> int:
        """Add a new section and return its index."""

        self.sections.append({"name": name, "exercises": []})
        return len(self.sections) - 1

    def remove_section(self, index: int) -> None:
        """Remove the section at ``index`` if it exists."""

        if 0 <= index < len(self.sections):
            self.sections.pop(index)

    def add_exercise(
        self,
        section_index: int,
        exercise_name: str,
        sets: int = DEFAULT_SETS_PER_EXERCISE,
    ) -> dict:
        """Add an exercise to the specified section."""

        if section_index < 0 or section_index >= len(self.sections):
            raise IndexError("Section index out of range")

        cursor = self.conn.cursor()
        cursor.execute("SELECT 1 FROM exercises WHERE name = ?", (exercise_name,))
        if cursor.fetchone() is None:
            raise ValueError(f"Exercise '{exercise_name}' does not exist")

        ex = {"name": exercise_name, "sets": sets}
        self.sections[section_index]["exercises"].append(ex)
        return ex

    def to_dict(self) -> dict:
        """Return the preset data as a dictionary."""

        return {"name": self.preset_name, "sections": self.sections}

    def close(self) -> None:
        self.conn.close()
