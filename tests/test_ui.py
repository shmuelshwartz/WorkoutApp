import os
import sys
from pathlib import Path
from functools import partial

import pytest

# Ensure Kivy runs in headless mode
os.environ.setdefault("KIVY_WINDOW", "mock")
os.environ.setdefault("KIVY_GRAPHICS", "mock")
os.environ.setdefault("KIVY_UNITTEST", "1")

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import core
from main import ExerciseLibraryScreen, EditExerciseScreen
from kivymd.uix.list import MDList
from kivymd.uix.recycleview import MDRecycleView


@pytest.fixture
def test_db(tmp_path):
    """Provide a temporary database and patch core helpers to use it."""
    src = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    db_path = tmp_path / "workout.db"
    db_path.write_bytes(src.read_bytes())

    # Patch core functions to use the temporary database
    def get_all(db_path_param=None, include_user_created=False):
        return core.get_all_exercises(db_path=db_path, include_user_created=include_user_created)

    patch = pytest.MonkeyPatch()
    patch.setattr(core, "get_all_exercises", get_all)
    patch.setattr(core, "Exercise", partial(core.Exercise, db_path=db_path))
    yield patch
    patch.undo()


def _get_names(rv):
    return [item.get("text") for item in rv.data]


def test_search_filtering(test_db):
    screen = ExerciseLibraryScreen()
    screen.exercise_list = MDRecycleView()
    screen.search_text = "bench"
    screen.populate()
    names = _get_names(screen.exercise_list)
    assert names and all("bench" in n.lower() for n in names)


def test_filter_options(test_db):
    # create a user-defined exercise
    ex = core.Exercise("Bench Press")
    ex.name = "Bench Deluxe"
    core.save_exercise(ex)

    screen = ExerciseLibraryScreen()
    screen.exercise_list = MDRecycleView()
    screen.filter_mode = "user"
    screen.populate()
    user_names = _get_names(screen.exercise_list)
    assert "Bench Deluxe" in user_names
    assert "Bench Press" not in user_names

    screen.filter_mode = "premade"
    screen.populate()
    pre_names = _get_names(screen.exercise_list)
    assert "Bench Deluxe" not in pre_names
    assert "Bench Press" in pre_names

    screen.filter_mode = "both"
    screen.populate()
    both_names = _get_names(screen.exercise_list)
    assert "Bench Deluxe" in both_names and "Bench Press" in both_names


def test_edit_and_save_updates_list(test_db, monkeypatch):
    screen = EditExerciseScreen()
    screen.metrics_list = MDList()
    screen.exercise_name = "Push-ups"
    screen.on_pre_enter()
    screen.update_name("Push-ups Elite")

    # bypass confirmation dialog
    monkeypatch.setattr(EditExerciseScreen, "save_exercise", lambda self: core.save_exercise(self.exercise_obj))
    screen.save_enabled = True
    screen.save_exercise()

    lib = ExerciseLibraryScreen()
    lib.exercise_list = MDRecycleView()
    lib.filter_mode = "user"
    lib.populate()
    names = _get_names(lib.exercise_list)
    assert "Push-ups Elite" in names


def test_delete_button_for_user_exercise(test_db):
    ex = core.Exercise("Bench Press")
    core.save_exercise(ex)
    screen = ExerciseLibraryScreen()
    screen.exercise_list = MDRecycleView()
    screen.filter_mode = "user"
    screen.populate()
    data = screen.exercise_list.data
    assert data
    assert data[0].get("is_user_created")


