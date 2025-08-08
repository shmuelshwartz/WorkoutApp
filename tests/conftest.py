import sqlite3
from pathlib import Path
import sys
import pytest
import importlib.util
import types

sys.path.append(str(Path(__file__).resolve().parents[1]))

# Provide a lightweight RestScreen when Kivy isn't available so tests can run
if importlib.util.find_spec("kivy") is None or importlib.util.find_spec("kivymd") is None:
    stub = types.ModuleType("ui.screens.rest_screen")

    class RestScreen:
        def confirm_finish(self):
            dialog = stub.MDDialog()
            dialog.open()

    class DummyDialog:
        def __init__(self, *a, **k):
            pass

        def open(self, *a, **k):
            pass

        def dismiss(self, *a, **k):
            pass

    stub.RestScreen = RestScreen
    stub.MDDialog = DummyDialog
    stub.MDRaisedButton = lambda *a, **k: None
    sys.modules["ui.screens.rest_screen"] = stub
    import builtins
    builtins.RestScreen = RestScreen



@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    """Create a temporary database populated with a minimal 'Push Day' preset."""
    db_path = tmp_path / "workout.db"
    sql_path = Path(__file__).resolve().parent.parent / "data" / "workout_schema.sql"

    conn = sqlite3.connect(db_path)
    with open(sql_path, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())

    # metric types
    conn.execute(
        """
        INSERT INTO library_metric_types
            (name, type, input_timing, is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, '', 0)
        """,
        ("Reps", "int", "post_set", 1, "set"),
    )
    conn.execute(
        """
        INSERT INTO library_metric_types
            (name, type, input_timing, is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, '', 0)
        """,
        ("Weight", "float", "pre_set", 0, "set"),
    )
    conn.execute(
        """
        INSERT INTO library_metric_types
            (name, type, input_timing, is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, '', 0)
        """,
        ("Machine", "enum", "pre_session", 0, "exercise"),
    )

    reps_id = conn.execute("SELECT id FROM library_metric_types WHERE name='Reps'").fetchone()[0]
    weight_id = conn.execute("SELECT id FROM library_metric_types WHERE name='Weight'").fetchone()[0]
    machine_id = conn.execute("SELECT id FROM library_metric_types WHERE name='Machine'").fetchone()[0]

    # exercises
    conn.execute(
        "INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Push-up', 'Push-up exercise', 0)"
    )
    conn.execute(
        "INSERT INTO library_exercises (name, description, is_user_created) VALUES ('Bench Press', 'Bench Press exercise', 0)"
    )

    pushup_id = conn.execute("SELECT id FROM library_exercises WHERE name='Push-up'").fetchone()[0]
    bench_id = conn.execute("SELECT id FROM library_exercises WHERE name='Bench Press'").fetchone()[0]


    # associate metrics with exercises
    conn.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, 0)",
        (pushup_id, reps_id),
    )

    conn.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, 0)",
        (bench_id, reps_id),
    )
    conn.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, 1)",
        (bench_id, weight_id),
    )
    conn.execute(
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position, enum_values_json) VALUES (?, ?, 2, ?)",
        (bench_id, machine_id, '["A","B"]'),
    )

    # preset
    conn.execute("INSERT INTO preset_presets (name) VALUES ('Push Day')")
    preset_id = conn.execute("SELECT id FROM preset_presets WHERE name='Push Day'").fetchone()[0]
    conn.execute(
        "INSERT INTO preset_preset_sections (preset_id, name, position) VALUES (?, 'Main', 0)",
        (preset_id,),
    )
    section_id = conn.execute(
        "SELECT id FROM preset_preset_sections WHERE preset_id=?", (preset_id,)
    ).fetchone()[0]

    # section exercises
    conn.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id)
        VALUES (?, 'Push-up', '', 0, 2, ?)
        """,
        (section_id, pushup_id),
    )
    push_se_id = conn.execute(
        "SELECT id FROM preset_section_exercises WHERE library_exercise_id=? AND section_id=?",
        (pushup_id, section_id),
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id)
        VALUES (?, 'Bench Press', '', 1, 2, ?)
        """,
        (section_id, bench_id),
    )
    bench_se_id = conn.execute(
        "SELECT id FROM preset_section_exercises WHERE library_exercise_id=? AND section_id=?",
        (bench_id, section_id),
    ).fetchone()[0]

    # section exercise metrics (override reps timing for bench)
    conn.execute(
        """
        INSERT INTO preset_exercise_metrics
            (section_exercise_id, metric_name, type, input_timing, is_required, scope, library_metric_type_id)
        VALUES (?, 'Reps', 'int', 'post_set', 1, 'set', ?)
        """,
        (push_se_id, reps_id),
    )
    conn.execute(
        """
        INSERT INTO preset_exercise_metrics
            (section_exercise_id, metric_name, type, input_timing, is_required, scope, library_metric_type_id)
        VALUES (?, 'Reps', 'int', 'pre_set', 1, 'set', ?)
        """,
        (bench_se_id, reps_id),
    )
    conn.execute(
        """
        INSERT INTO preset_exercise_metrics
            (section_exercise_id, metric_name, type, input_timing, is_required, scope, library_metric_type_id)
        VALUES (?, 'Weight', 'float', 'pre_set', 0, 'set', ?)
        """,
        (bench_se_id, weight_id),
    )
    conn.execute(
        """
        INSERT INTO preset_exercise_metrics
            (section_exercise_id, metric_name, type, input_timing, is_required, scope, enum_values_json, library_metric_type_id)
        VALUES (?, 'Machine', 'enum', 'pre_session', 0, 'exercise', ?, ?)
        """,
        (bench_se_id, '["A","B"]', machine_id),
    )

    conn.commit()
    conn.close()
    return db_path
