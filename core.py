import sqlite3
from pathlib import Path

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


class WorkoutSession:
    """Simple in-memory representation of a workout session."""

    def __init__(self, exercises):
        """Initialize with a list of ``{'name', 'sets'}`` dictionaries."""
        self.exercises = [
            {"name": ex["name"], "sets": ex["sets"], "results": []}
            for ex in exercises
        ]
        self.current_exercise = 0
        self.current_set = 0

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
            return True
        ex = self.exercises[self.current_exercise]
        ex["results"].append(metrics)
        self.current_set += 1
        if self.current_set >= ex["sets"]:
            self.current_set = 0
            self.current_exercise += 1
        return self.current_exercise >= len(self.exercises)
