from pathlib import Path
import sqlite3


def create_sample_db(db_path: Path) -> None:
    """Populate ``db_path`` with basic sample data for tests."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    # Exercises
    cur.executemany(
        "INSERT INTO exercises (id, name, description, is_user_created) VALUES (?, ?, ?, 0)",
        [
            (1, "Bench Press", "Chest exercise"),
            (2, "Push-ups", "Bodyweight push exercise"),
            (3, "Shoulder Circles", "Warm up shoulder mobility"),
            (4, "Jumping Jacks", "Warm up cardio"),
        ],
    )

    # Metric types
    cur.executemany(
        "INSERT INTO metric_types (id, name, input_type, source_type, input_timing, is_required, scope, description, is_user_created)"
        " VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)",
        [
            (1, "Weight", "float", "manual_text", "post_set", 1, "set", "Weight used"),
            (2, "Reps", "int", "manual_text", "post_set", 1, "set", "Repetitions"),
        ],
    )

    # Exercises to metric types
    cur.executemany(
        "INSERT INTO exercise_metrics (id, exercise_id, metric_type_id, position) VALUES (?, ?, ?, ?)",
        [
            (1, 1, 1, 0),
            (2, 1, 2, 1),
            (3, 2, 2, 0),
        ],
    )

    # Preset
    cur.execute("INSERT INTO presets (id, name) VALUES (1, 'Push Day')")

    # Sections
    cur.executemany(
        "INSERT INTO sections (id, preset_id, name, position) VALUES (?, ?, ?, ?)",
        [
            (1, 1, "Warm-up", 0),
            (2, 1, "Workout", 1),
        ],
    )

    # Section exercises
    cur.executemany(
        "INSERT INTO section_exercises (id, section_id, exercise_id, position, number_of_sets, exercise_name, exercise_description)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)",
        [
            (1, 1, 3, 0, 1, "Shoulder Circles", "Warm up shoulder mobility"),
            (2, 1, 4, 1, 1, "Jumping Jacks", "Warm up cardio"),
            (3, 2, 1, 0, 3, "Bench Press", "Chest exercise"),
            (4, 2, 2, 1, 2, "Push-ups", "Bodyweight push exercise"),
        ],
    )

    # Metrics for section exercises
    cur.executemany(
        "INSERT INTO section_exercise_metrics (id, section_exercise_id, metric_type_id, input_timing, is_required, scope, default_exercise_metric_id)"
        " VALUES (?, ?, ?, ?, ?, ?, NULL)",
        [
            (1, 3, 1, "post_set", 1, "set"),
            (2, 3, 2, "post_set", 1, "set"),
            (3, 4, 2, "post_set", 1, "set"),
        ],
    )

    conn.commit()
    conn.close()
