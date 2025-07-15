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

@pytest.fixture(autouse=True, scope="session")
def populate_sample_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM presets WHERE name='Push Day'")
    if cur.fetchone()[0] == 0:
        cur.execute("INSERT INTO presets (name) VALUES ('Push Day')")
        preset_id = cur.lastrowid
        cur.execute("INSERT INTO sections (preset_id, name, position) VALUES (?, 'Warm-up', 0)", (preset_id,))
        warm_id = cur.lastrowid
        cur.execute("INSERT INTO sections (preset_id, name, position) VALUES (?, 'Workout', 1)", (preset_id,))
        work_id = cur.lastrowid

        def ensure_ex(name):
            cur.execute("SELECT id FROM exercises WHERE name=?", (name,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute("INSERT INTO exercises (name) VALUES (?)", (name,))
            return cur.lastrowid

        shoulder = ensure_ex('Shoulder Circles')
        jumping = ensure_ex('Jumping Jacks')
        bench = ensure_ex('Bench Press')
        pushups = ensure_ex('Push-ups')

        def ensure_mt(name, input_type='int', source_type='manual_text', input_timing='post_set', scope='set'):
            cur.execute("SELECT id FROM metric_types WHERE name=?", (name,))
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO metric_types (name, input_type, source_type, input_timing, scope) VALUES (?, ?, ?, ?, ?)",
                (name, input_type, source_type, input_timing, scope),
            )
            return cur.lastrowid

        reps = ensure_mt('Reps')
        weight = ensure_mt('Weight', 'float')

        def add_em(ex_id, mt_id, pos=0):
            cur.execute(
                "SELECT id FROM exercise_metrics WHERE exercise_id=? AND metric_type_id=?",
                (ex_id, mt_id),
            )
            if not cur.fetchone():
                cur.execute(
                    "INSERT INTO exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, ?)",
                    (ex_id, mt_id, pos),
                )

        for ex in (bench, pushups, jumping, shoulder):
            add_em(ex, reps)
        add_em(bench, weight, 1)

        def add_se(section_id, ex_id, pos):
            cur.execute(
                "INSERT INTO section_exercises (section_id, exercise_id, position, number_of_sets, exercise_name) VALUES (?, ?, ?, 1, (SELECT name FROM exercises WHERE id=?))",
                (section_id, ex_id, pos, ex_id),
            )
            se_id = cur.lastrowid
            cur.execute(
                "SELECT metric_type_id FROM exercise_metrics WHERE exercise_id=? ORDER BY position",
                (ex_id,),
            )
            for (mt,) in cur.fetchall():
                cur.execute(
                    "INSERT INTO section_exercise_metrics (section_exercise_id, metric_type_id, input_timing, scope) VALUES (?, ?, 'post_set', 'set')",
                    (se_id, mt),
                )

        add_se(warm_id, shoulder, 0)
        add_se(warm_id, jumping, 1)
        add_se(work_id, bench, 0)
        add_se(work_id, pushups, 1)

        conn.commit()
    conn.close()

