import sqlite3
from pathlib import Path
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import core


def create_empty_db(path: Path) -> None:
    """Create a new database at *path* using the bundled schema."""
    schema = Path("data/workout.sql").read_text()
    conn = sqlite3.connect(path)
    conn.executescript(schema)
    conn.commit()
    conn.close()


def populate_sample_data(db_path: Path) -> None:
    """Insert sample exercises, metric types and a preset."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Exercises
    cur.executemany(
        "INSERT INTO exercises (name, description, is_user_created) VALUES (?, ?, ?)",
        [
            ("Bench Press", "Chest", 0),
            ("Push Up", "Standard push up", 0),
            ("Push Up", "My push up", 1),
        ],
    )
    # Metric types
    cur.executemany(
        "INSERT INTO metric_types (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created) VALUES (?, ?, ?, ?, ?, ?, ?, 1)",
        [
            ("Reps", "int", "manual_text", "post_set", 1, "set", "Number of reps"),
            ("Weight", "float", "manual_text", "post_set", 0, "set", "Weight used"),
        ],
    )
    # Preset with one section and two exercises
    cur.execute("INSERT INTO presets (name) VALUES ('Push Day')")
    preset_id = cur.lastrowid
    cur.execute(
        "INSERT INTO sections (preset_id, name, position) VALUES (?, ?, 0)",
        (preset_id, "Main"),
    )
    section_id = cur.lastrowid
    cur.execute(
        "SELECT id FROM exercises WHERE name = 'Bench Press' AND is_user_created = 0",
    )
    bench_id = cur.fetchone()[0]
    cur.execute(
        "SELECT id FROM exercises WHERE name = 'Push Up' AND is_user_created = 0",
    )
    push_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO section_exercises (section_id, exercise_id, position, number_of_sets) VALUES (?, ?, 0, 3)",
        (section_id, bench_id),
    )
    cur.execute(
        "INSERT INTO section_exercises (section_id, exercise_id, position, number_of_sets) VALUES (?, ?, 1, 2)",
        (section_id, push_id),
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    db_file = tmp_path / "workout.db"
    create_empty_db(db_file)
    return db_file


@pytest.fixture()
def sample_db(tmp_db: Path) -> Path:
    populate_sample_data(tmp_db)
    return tmp_db


def test_get_metric_type_schema(tmp_db: Path):
    fields = core.get_metric_type_schema(db_path=tmp_db)
    names = {f["name"] for f in fields}
    assert names == {"name", "input_type", "source_type", "input_timing", "is_required", "scope", "description"}
    input_type_opts = next(f["options"] for f in fields if f["name"] == "input_type")
    assert set(input_type_opts) == {"int", "float", "str", "bool"}


def test_get_all_exercises_and_details(sample_db: Path):
    all_ex = core.get_all_exercises(db_path=sample_db, include_user_created=True)
    assert all_ex == [
        ("Bench Press", False),
        ("Push Up", False),
        ("Push Up", True),
    ]
    details = core.get_exercise_details("Push Up", db_path=sample_db)
    assert details["is_user_created"] is True
    details_specific = core.get_exercise_details("Push Up", db_path=sample_db, is_user_created=False)
    assert details_specific["is_user_created"] is False
    assert core.get_exercise_details("Nope", db_path=sample_db) is None


def test_load_workout_presets(sample_db: Path):
    presets = core.load_workout_presets(db_path=sample_db)
    assert presets == [
        {
            "name": "Push Day",
            "exercises": [
                {"name": "Bench Press", "sets": 3},
                {"name": "Push Up", "sets": 2},
            ],
        }
    ]


def test_add_and_remove_metric_from_exercise(sample_db: Path):
    core.add_metric_to_exercise("Bench Press", "Reps", db_path=sample_db)
    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    cur.execute("""SELECT COUNT(*) FROM exercise_metrics em JOIN exercises e ON em.exercise_id = e.id JOIN metric_types mt ON em.metric_type_id = mt.id WHERE e.name='Bench Press' AND mt.name='Reps'""")
    count = cur.fetchone()[0]
    assert count == 1
    core.remove_metric_from_exercise("Bench Press", "Reps", db_path=sample_db)
    cur.execute("""SELECT COUNT(*) FROM exercise_metrics em JOIN exercises e ON em.exercise_id = e.id JOIN metric_types mt ON em.metric_type_id = mt.id WHERE e.name='Bench Press' AND mt.name='Reps'""")
    count = cur.fetchone()[0]
    conn.close()
    assert count == 0
