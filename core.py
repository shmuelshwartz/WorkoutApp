import sqlite3
from pathlib import Path
import time

# Number of sets each exercise defaults to when starting a workout
DEFAULT_SETS_PER_EXERCISE = 2

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


def get_all_exercises(db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db") -> list:
    """Return a list of all exercise names in the database."""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM exercises ORDER BY name")
    exercises = [row[0] for row in cursor.fetchall()]
    conn.close()
    return exercises


def get_metrics_for_exercise(
    exercise_name: str,
    db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db",
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
        SELECT mt.id, mt.name, mt.input_type, mt.source_type
        FROM exercise_metrics em
        JOIN metric_types mt ON mt.id = em.metric_type_id
        WHERE em.exercise_id = ?
        ORDER BY em.id
        """,
        (exercise_id,),
    )

    metrics = []
    for metric_id, name, input_type, source_type in cursor.fetchall():
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
                "values": values,
            }
        )

    conn.close()
    return metrics


class WorkoutSession:
    """In-memory representation of a workout session.

    The session loads the selected preset from the database when it is
    created and then works entirely with the in-memory data structure.  No
    database access occurs after initialisation, so the database can be closed
    or moved while the workout is in progress.
    """

    def __init__(self, preset_name: str,
                 db_path: Path = Path(__file__).resolve().parent / "data" / "workout.db"):
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

    def next_exercise_name(self):
        if self.current_exercise < len(self.exercises):
            return self.exercises[self.current_exercise]["name"]
        return ""

    def next_exercise_display(self):
        if self.current_exercise < len(self.exercises):
            ex = self.exercises[self.current_exercise]
            return f"{ex['name']} set {self.current_set + 1} of {ex['sets']}"
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
