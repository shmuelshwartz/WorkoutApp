import importlib.util
import os
import pytest

os.environ["KIVY_WINDOW"] = "mock"
# Skip tests entirely if Kivy (and KivyMD) are not installed
kivy_available = (
    importlib.util.find_spec("kivy") is not None and
    importlib.util.find_spec("kivymd") is not None
)

if kivy_available:
    # Prevent opening real windows during tests
    os.environ.setdefault("KIVY_WINDOW", "mock")
    os.environ.setdefault("KIVY_UNITTEST", "1")

    from kivy.app import App
    from kivy.properties import ObjectProperty
    import core

    from main import (
        RestScreen,
        MetricInputScreen,
        WorkoutActiveScreen,
        AddMetricPopup,
        EditExerciseScreen,
        ExerciseSelectionPanel,
        PresetsScreen,
    )
    import time

    class _DummyApp:
        """Minimal stand-in for :class:`~kivymd.app.MDApp` used in tests."""

        theme_cls = object()

        def property(self, name, default=None):  # pragma: no cover - simple shim
            return ObjectProperty(None)


    @pytest.fixture(autouse=True)
    def _provide_app(monkeypatch):
        """Ensure widgets see a running App instance."""

        monkeypatch.setattr(App, "get_running_app", lambda: _DummyApp())
        yield


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_switch_tab_updates_current_tab():
    screen = MetricInputScreen()
    screen.update_header = lambda: None
    screen.switch_tab("next")
    assert screen.current_tab == "next"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_rest_screen_toggle_ready_changes_state():
    screen = RestScreen()
    screen.is_ready = False
    screen.timer_color = (1, 0, 0, 1)
    screen.toggle_ready()
    assert screen.is_ready is True
    assert screen.timer_color == (0, 1, 0, 1)


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_update_elapsed_formats_time(monkeypatch):
    screen = WorkoutActiveScreen()
    screen.start_time = 100.0
    monkeypatch.setattr(time, "time", lambda: 175.0)
    screen._update_elapsed(0)
    assert screen.elapsed == pytest.approx(75.0, abs=1e-3)
    assert screen.formatted_time == "01:15"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_enum_values_accepts_spaces():
    class DummyScreen:
        exercise_obj = type("obj", (), {"metrics": []})()

    popup = AddMetricPopup(DummyScreen(), mode="new")
    popup.input_widgets["input_type"].text = "str"
    filtered = popup.enum_values_field.input_filter("A B,C", False)
    assert filtered == "A B,C"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_enum_values_strip_spaces_after_comma():
    class DummyScreen:
        exercise_obj = type("obj", (), {"metrics": []})()

    popup = AddMetricPopup(DummyScreen(), mode="new")
    popup.input_widgets["input_type"].text = "str"
    filtered = popup.enum_values_field.input_filter("A, B ,  C", False)
    assert filtered == "A,B,C"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_add_metric_popup_filters_scope(monkeypatch):
    class DummyScreen:
        exercise_obj = type("obj", (), {"metrics": []})()

    metrics = [
        {"name": "Session", "scope": "session"},
        {"name": "Section", "scope": "section"},
        {"name": "Exercise", "scope": "exercise"},
        {"name": "Set", "scope": "set"},
    ]

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: metrics)

    popup = AddMetricPopup(DummyScreen(), mode="select")
    list_view = popup.content_cls.children[0]
    names = {child.text for child in list_view.children}

    assert "Session" not in names
    assert "Section" not in names
    assert {"Exercise", "Set"}.issubset(names)


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_exercise_default_tab():
    screen = EditExerciseScreen()
    screen.previous_screen = "exercise_library"
    screen.on_pre_enter()
    assert screen.current_tab == "metrics"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_exercise_preset_tab():
    screen = EditExerciseScreen()
    screen.previous_screen = "edit_preset"
    screen.on_pre_enter()
    assert screen.current_tab == "config"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_exercise_selection_panel_filters(monkeypatch):
    panel = ExerciseSelectionPanel()
    panel.exercise_list = type("L", (), {"children": [], "clear_widgets": lambda self: self.children.clear(), "add_widget": lambda self, w: self.children.append(w)})()

    monkeypatch.setattr(
        core,
        "get_all_exercises",
        lambda *a, **k: [("Push Ups", False), ("Custom", True)],
    )

    panel.populate_exercises()
    assert len(panel.exercise_list.children) == 2

    panel.apply_filter("user")
    assert len(panel.exercise_list.children) == 1
    assert panel.exercise_list.children[0].text == "Custom"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_preset_select_button_updates(monkeypatch):
    """Selecting a preset updates the select button text."""
    from kivy.lang import Builder
    from pathlib import Path
    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    monkeypatch.setattr(
        core,
        "WORKOUT_PRESETS",
        [{"name": "Sample", "exercises": []}],
    )

    screen = PresetsScreen()
    dummy = type("Obj", (), {"md_bg_color": (0, 0, 0, 0)})()
    screen.select_preset("Sample", dummy)

    assert screen.ids.select_btn.text == "Sample"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")

def test_save_exercise_duplicate_name(monkeypatch, tmp_path):
    """Saving with a duplicate user-defined name shows an error."""
    import sqlite3
    from pathlib import Path

    schema = Path(__file__).resolve().parents[1] / "data" / "workout.sql"
    db_path = tmp_path / "workout.db"
    conn = sqlite3.connect(db_path)
    with open(schema, "r", encoding="utf-8") as fh:
        conn.executescript(fh.read())
    conn.close()

    ex = core.Exercise(db_path=db_path)
    ex.name = "Custom"
    core.save_exercise(ex)

    screen = EditExerciseScreen()
    screen.exercise_obj = core.Exercise(db_path=db_path)
    screen.exercise_obj.name = "Custom"
    screen.name_field = type("F", (), {"error": False})()

    import sys

    opened = {"value": False}

    class DummyDialog:
        def __init__(self, *a, **k):
            pass

        def open(self_inner):
            opened["value"] = True

    monkeypatch.setattr(sys.modules["main"], "MDDialog", DummyDialog)

    screen.save_exercise()

    assert opened["value"]
    assert screen.name_field.error

@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_metric_duplicate_name(monkeypatch):
    class DummyExercise:
        def __init__(self):
            self.metrics = [{"name": "Reps"}, {"name": "Weight"}]
            self.updated = False
            self.is_user_created = False

        def update_metric(self, *a, **k):
            self.updated = True

    class DummyScreen:
        exercise_obj = DummyExercise()

    metric = DummyScreen.exercise_obj.metrics[0]
    popup = EditMetricPopup(DummyScreen(), metric)
    popup.input_widgets["name"].text = "Weight"
    monkeypatch.setattr(core, "is_metric_type_user_created", lambda *a, **k: False)
    popup.save_metric()

    assert not DummyScreen.exercise_obj.updated
    assert popup.input_widgets["name"].error


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_metric_type_popup_selects_correct_metric():
    class DummyScreen:
        all_metrics = [
            {"name": "Reps", "is_user_created": False, "description": "orig"},
            {"name": "Reps", "is_user_created": True, "description": "copy"},
        ]

    popup = EditMetricTypePopup(DummyScreen(), "Reps", True)
    assert popup.metric["description"] == "copy"

@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_preset_select_button_color(monkeypatch):
    """Selecting a preset updates the select button color."""
    from kivy.lang import Builder
    from pathlib import Path
    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    monkeypatch.setattr(
        core,
        "WORKOUT_PRESETS",
        [{"name": "Sample", "exercises": []}],
    )

    screen = PresetsScreen()
    dummy = type("Obj", (), {"md_bg_color": (0, 0, 0, 0)})()
    screen.select_preset("Sample", dummy)

    assert dummy.md_bg_color == screen._selected_color

