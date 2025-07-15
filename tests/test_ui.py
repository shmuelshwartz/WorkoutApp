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
from kivymd.uix.list import MDList, OneLineRightIconListItem


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


def _get_names(list_widget):
    return [w.text for w in list_widget.children if isinstance(w, OneLineRightIconListItem)]


def test_search_filtering(test_db):
    screen = ExerciseLibraryScreen()
    screen.exercise_list = MDList()
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
    screen.exercise_list = MDList()
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
    lib.exercise_list = MDList()
    lib.filter_mode = "user"
    lib.populate()
    names = _get_names(lib.exercise_list)
    assert "Push-ups Elite" in names


def test_delete_button_for_user_exercise(test_db):
    ex = core.Exercise("Bench Press")
    core.save_exercise(ex)
    screen = ExerciseLibraryScreen()
    screen.exercise_list = MDList()
    screen.filter_mode = "user"
    screen.populate()
    items = [w for w in screen.exercise_list.children if isinstance(w, OneLineRightIconListItem)]
    assert items
    icons = [c for c in items[0].children if hasattr(c, "icon")]
    assert any(getattr(i, "icon", "") == "delete" for i in icons)


def test_update_search_debounces_populate(test_db):
    screen = ExerciseLibraryScreen()
    screen.exercise_list = MDList()
    # call update_search twice quickly; second should cancel first
    screen.update_search("ben")
    first_event = screen._search_event
    screen.update_search("bench")
    second_event = screen._search_event
    assert first_event != second_event
    # run scheduled event
    from kivy.clock import Clock
    Clock.tick()  # process scheduling
    Clock.tick()  # ensure callback executed
    names = _get_names(screen.exercise_list)
    assert names and all("bench" in n.lower() for n in names)



