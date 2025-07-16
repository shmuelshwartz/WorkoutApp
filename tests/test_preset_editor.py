import shutil
import sqlite3
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import PresetEditor, DEFAULT_SETS_PER_EXERCISE


@pytest.fixture
def db_copy(tmp_path):
    """Return a temporary copy of the sample workout database."""
    src = Path(__file__).resolve().parent.parent / "data" / "workout.db"
    dst = tmp_path / "workout.db"
    shutil.copy(src, dst)
    # migrate table names to the latest schema
    conn = sqlite3.connect(dst)
    cur = conn.cursor()
    migrations = [
        "ALTER TABLE exercises RENAME TO library_exercises",
        "ALTER TABLE exercise_metrics RENAME TO library_exercise_metrics",
        "ALTER TABLE exercise_enum_values RENAME TO library_exercise_enum_values",
        "ALTER TABLE metric_types RENAME TO library_metric_types",
        "ALTER TABLE presets RENAME TO preset_presets",
        "ALTER TABLE sections RENAME TO preset_sections",
        "ALTER TABLE section_exercises RENAME TO preset_section_exercises",
        "ALTER TABLE section_exercise_metrics RENAME TO preset_section_exercise_metrics",
    ]
    for stmt in migrations:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError:
            pass
    cur.executescript(
        """
        DROP VIEW IF EXISTS view_exercise_metrics;
        CREATE VIEW library_view_exercise_metrics AS
            SELECT em.id AS exercise_metric_id,
                   em.exercise_id,
                   e.name AS exercise_name,
                   em.metric_type_id,
                   mt.name AS metric_type_name
            FROM library_exercise_metrics em
            JOIN library_exercises e ON em.exercise_id = e.id
            JOIN library_metric_types mt ON em.metric_type_id = mt.id;
        DROP INDEX IF EXISTS idx_exercises_name_user_created;
        CREATE UNIQUE INDEX idx_library_exercises_name_user_created ON library_exercises (name, is_user_created);
        """
    )
    conn.commit()
    conn.close()
    return dst


@pytest.fixture
def db_with_preset(db_copy):
    """Create a preset with one section and one exercise for loading tests."""
    conn = sqlite3.connect(db_copy)
    cur = conn.cursor()
    cur.execute("INSERT INTO preset_presets (name) VALUES (?)", ("Test Preset",))
    preset_id = cur.lastrowid
    cur.execute(
        "INSERT INTO preset_sections (preset_id, name, position) VALUES (?, ?, 0)",
        (preset_id, "Warmup"),
    )
    section_id = cur.lastrowid
    # Use an existing exercise from the sample DB
    cur.execute("SELECT id FROM library_exercises WHERE name = 'Push-ups'")
    ex_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO preset_section_exercises (section_id, exercise_id, position, number_of_sets)"
        " VALUES (?, ?, 0, 3)",
        (section_id, ex_id),
    )
    conn.commit()
    conn.close()
    return db_copy


def test_add_and_remove_section(db_copy):
    editor = PresetEditor(db_path=db_copy)
    idx1 = editor.add_section("Warmup")
    idx2 = editor.add_section("Main")
    assert idx1 == 0
    assert idx2 == 1
    assert [s["name"] for s in editor.sections] == ["Warmup", "Main"]
    editor.remove_section(0)
    assert len(editor.sections) == 1
    assert editor.sections[0]["name"] == "Main"
    editor.close()


def test_add_exercise_success(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.add_section("Warmup")
    ex = editor.add_exercise(0, "Push-ups", sets=4)
    assert ex == {"name": "Push-ups", "sets": 4}
    assert editor.sections[0]["exercises"] == [ex]
    editor.close()


def test_add_exercise_invalid_index(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.add_section("Warmup")
    with pytest.raises(IndexError):
        editor.add_exercise(2, "Push-ups")
    editor.close()


def test_add_exercise_unknown_exercise(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.add_section("Warmup")
    with pytest.raises(ValueError):
        editor.add_exercise(0, "DoesNotExist")
    editor.close()


def test_to_dict_after_modifications(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.preset_name = "My Preset"
    editor.add_section("Warmup")
    editor.add_exercise(0, "Push-ups")
    expected = {
        "name": "My Preset",
        "sections": [
            {
                "name": "Warmup",
                "exercises": [
                    {"name": "Push-ups", "sets": DEFAULT_SETS_PER_EXERCISE}
                ],
            }
        ],
    }
    assert editor.to_dict() == expected
    editor.close()


def test_load_existing_preset(db_with_preset):
    editor = PresetEditor("Test Preset", db_path=db_with_preset)
    assert editor.preset_name == "Test Preset"
    assert len(editor.sections) == 1
    sec = editor.sections[0]
    assert sec["name"] == "Warmup"
    assert sec["exercises"] == [{"name": "Push-ups", "sets": 3}]
    editor.close()


def test_close_closes_connection(db_copy):
    editor = PresetEditor(db_path=db_copy)
    editor.close()
    with pytest.raises(sqlite3.ProgrammingError):
        editor.conn.execute("SELECT 1")


