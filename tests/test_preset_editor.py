from pathlib import Path
import sys
import pytest

# ensure project root in path
sys.path.append(str(Path(__file__).resolve().parents[1]))

from core import PresetEditor, DEFAULT_SETS_PER_EXERCISE

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workout.db"


def test_load_existing_preset():
    editor = PresetEditor("Push Day", DB_PATH)
    try:
        assert editor.preset_name == "Push Day"
        assert editor.sections
        for sec in editor.sections:
            assert "name" in sec
            assert isinstance(sec["exercises"], list)
            for ex in sec["exercises"]:
                assert "name" in ex
                assert "sets" in ex
    finally:
        editor.close()


def test_add_section_and_exercise():
    editor = PresetEditor(db_path=DB_PATH)
    try:
        idx = editor.add_section("My Section")
        assert idx == 0
        added = editor.add_exercise(idx, "Push-ups")
        assert added == {"name": "Push-ups", "sets": DEFAULT_SETS_PER_EXERCISE}
        assert editor.sections[0]["exercises"] == [added]
    finally:
        editor.close()


def test_add_exercise_validates_name():
    editor = PresetEditor(db_path=DB_PATH)
    try:
        idx = editor.add_section()
        with pytest.raises(ValueError):
            editor.add_exercise(idx, "NotReal")
    finally:
        editor.close()
