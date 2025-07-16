import sqlite3
from pathlib import Path
import sys
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))


@pytest.fixture
def sample_db(tmp_path: Path) -> Path:
    """Create a temporary database populated with a minimal 'Push Day' preset."""
    db_path = tmp_path / "workout.db"
    sql_path = Path(__file__).resolve().parent.parent / "data" / "workout.sql"

    conn = sqlite3.connect(db_path)
    with open(sql_path, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())

    # metric types
    conn.execute(
        """
        INSERT INTO library_metric_types
            (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, ?, '', 0)
        """,
        ("Reps", "int", "manual_text", "post_set", 1, "set"),
    )
    conn.execute(
        """
        INSERT INTO library_metric_types
            (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, ?, '', 0)
        """,
        ("Weight", "float", "manual_text", "pre_set", 0, "set"),
    )
    conn.execute(
        """
        INSERT INTO library_metric_types
            (name, input_type, source_type, input_timing, is_required, scope, description, is_user_created)
        VALUES (?, ?, ?, ?, ?, ?, '', 0)
        """,
        ("Machine", "str", "manual_enum", "pre_workout", 0, "exercise"),
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

    # enum values for Machine metric (linked to Bench Press)
    conn.execute(
        "INSERT INTO library_exercise_enum_values (metric_type_id, exercise_id, value, position) VALUES (?, ?, 'A', 0)",
        (machine_id, bench_id),
    )
    conn.execute(
        "INSERT INTO library_exercise_enum_values (metric_type_id, exercise_id, value, position) VALUES (?, ?, 'B', 1)",
        (machine_id, bench_id),
    )

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
        "INSERT INTO library_exercise_metrics (exercise_id, metric_type_id, position) VALUES (?, ?, 2)",
        (bench_id, machine_id),
    )

    # preset
    conn.execute("INSERT INTO preset_presets (name) VALUES ('Push Day')")
    preset_id = conn.execute("SELECT id FROM preset_presets WHERE name='Push Day'").fetchone()[0]
    conn.execute(
        "INSERT INTO preset_sections (preset_id, name, position) VALUES (?, 'Main', 0)",
        (preset_id,),
    )
    section_id = conn.execute(
        "SELECT id FROM preset_sections WHERE preset_id=?", (preset_id,)
    ).fetchone()[0]

    # section exercises
    conn.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_id, position, number_of_sets, exercise_name, exercise_description)
        VALUES (?, ?, 0, 2, 'Push-up', '')
        """,
        (section_id, pushup_id),
    )
    push_se_id = conn.execute(
        "SELECT id FROM preset_section_exercises WHERE exercise_id=? AND section_id=?",
        (pushup_id, section_id),
    ).fetchone()[0]

    conn.execute(
        """
        INSERT INTO preset_section_exercises
            (section_id, exercise_id, position, number_of_sets, exercise_name, exercise_description)
        VALUES (?, ?, 1, 2, 'Bench Press', '')
        """,
        (section_id, bench_id),
    )
    bench_se_id = conn.execute(
        "SELECT id FROM preset_section_exercises WHERE exercise_id=? AND section_id=?",
        (bench_id, section_id),
    ).fetchone()[0]

    # section exercise metrics (override reps timing for bench)
    conn.execute(
        "INSERT INTO preset_section_exercise_metrics (section_exercise_id, metric_type_id, input_timing, is_required, scope) VALUES (?, ?, 'post_set', 1, 'set')",
        (push_se_id, reps_id),
    )
    conn.execute(
        "INSERT INTO preset_section_exercise_metrics (section_exercise_id, metric_type_id, input_timing, is_required, scope) VALUES (?, ?, 'pre_set', 1, 'set')",
        (bench_se_id, reps_id),
    )
    conn.execute(
        "INSERT INTO preset_section_exercise_metrics (section_exercise_id, metric_type_id, input_timing, is_required, scope) VALUES (?, ?, 'pre_set', 0, 'set')",
        (bench_se_id, weight_id),
    )
    conn.execute(
        "INSERT INTO preset_section_exercise_metrics (section_exercise_id, metric_type_id, input_timing, is_required, scope) VALUES (?, ?, 'pre_workout', 0, 'exercise')",
        (bench_se_id, machine_id),
    )

    conn.commit()
    conn.close()
    return db_path
