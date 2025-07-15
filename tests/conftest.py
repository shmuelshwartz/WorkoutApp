import sqlite3
from pathlib import Path
import pytest

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workout.db"

@pytest.fixture(autouse=True)
def ensure_push_day():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id FROM exercises WHERE name=?", ("Shoulder Circles",))
    row = cur.fetchone()
    if row is None:
        cur.execute(
            "INSERT INTO exercises (name, description, is_user_created) VALUES (?, '', 0)",
            ("Shoulder Circles",),
        )
        shoulder_id = cur.lastrowid
    else:
        shoulder_id = row[0]
    cur.execute("SELECT id FROM presets WHERE name=?", ("Push Day",))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO presets (name) VALUES (?)", ("Push Day",))
        preset_id = cur.lastrowid
        cur.execute(
            "INSERT INTO sections (preset_id, name, position) VALUES (?, ?, 1)",
            (preset_id, "Warmup"),
        )
        section_id = cur.lastrowid
        cur.execute(
            "INSERT INTO section_exercises (section_id, exercise_id, position, number_of_sets) VALUES (?, ?, 1, 1)",
            (section_id, shoulder_id),
        )
        conn.commit()
    conn.close()
    yield
