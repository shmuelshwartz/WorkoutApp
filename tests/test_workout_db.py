import sqlite3
from pathlib import Path

def show_workout_structure(db_path):
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Fetch all presets (workouts)
    cursor.execute("SELECT id, name FROM presets ORDER BY id")
    presets = cursor.fetchall()

    for preset_id, preset_name in presets:
        print(f"\nWorkout: {preset_name}")

        # Fetch sections in this preset
        cursor.execute("""
            SELECT id, name FROM sections
            WHERE preset_id = ?
            ORDER BY position
        """, (preset_id,))
        sections = cursor.fetchall()

        for section_id, section_name in sections:
            print(f"  Section: {section_name}")

            # Fetch exercises in this section
            cursor.execute("""
                SELECT e.name
                FROM section_exercises se
                JOIN exercises e ON se.exercise_id = e.id
                WHERE se.section_id = ?
                ORDER BY se.position
            """, (section_id,))
            exercises = cursor.fetchall()

            for exercise_name, in exercises:
                print(f"    - {exercise_name}")

    conn.close()


def test_show_workout_structure(capsys):
    db_path = Path(__file__).resolve().parent / ".." / "data" / "workout.db"
    show_workout_structure(db_path)
    captured = capsys.readouterr()
    assert "Workout:" in captured.out
