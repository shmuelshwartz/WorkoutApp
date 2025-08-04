import importlib.util
import os
import pytest

os.environ["KIVY_WINDOW"] = "mock"
# Skip tests entirely if Kivy (and KivyMD) are not installed
kivy_available = (
    importlib.util.find_spec("kivy") is not None
    and importlib.util.find_spec("kivymd") is not None
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
        EditMetricTypePopup,
        EditExerciseScreen,
        ExerciseSelectionPanel,
        PresetsScreen,
        EditPresetScreen,
        PresetDetailScreen,
        PresetOverviewScreen,
    )
    from ui.popups import AddMetricPopup, EditMetricPopup
    from ui.expandable_list_item import ExerciseSummaryItem
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
def test_optional_metrics_populated():
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    screen = MetricInputScreen()
    screen.populate_metrics(
        [
            {
                "name": "RPE",
                "type": "int",
                "input_timing": "post_set",
                "is_required": False,
            }
        ]
    )
    assert len(screen.prev_optional_list.children) == 1


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
    popup.input_widgets["type"].text = "str"
    filtered = popup.enum_values_field.input_filter("A B,C", False)
    assert filtered == "A B,C"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_enum_values_strip_spaces_after_comma():
    class DummyScreen:
        exercise_obj = type("obj", (), {"metrics": []})()

    popup = AddMetricPopup(DummyScreen(), mode="new")
    popup.input_widgets["type"].text = "str"
    filtered = popup.enum_values_field.input_filter("A, B ,  C", False)
    assert filtered == "A,B,C"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_add_metric_popup_has_single_enum_field():
    class DummyScreen:
        exercise_obj = type("obj", (), {"metrics": []})()

    popup = AddMetricPopup(DummyScreen(), mode="new")
    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 0
    popup.input_widgets["type"].text = "enum"
    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 1


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_metric_popup_has_single_enum_field():
    class DummyExercise:
        metrics = [
            {
                "name": "Machine",
                "type": "enum",
                "values": ["A", "B"],
            }
        ]
        updated = False

        def update_metric(self, *a, **k):
            self.updated = True

    class DummyScreen:
        exercise_obj = DummyExercise()

    metric = DummyScreen.exercise_obj.metrics[0]
    popup = EditMetricPopup(DummyScreen(), metric)
    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 1
    popup.input_widgets["type"].text = "str"

    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 0
    popup.input_widgets["type"].text = "enum"
    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 1


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_metric_popup_no_duplicate_field():
    class DummyExercise:
        metrics = [
            {
                "name": "Machine",
                "type": "enum",
                "values": ["A", "B"],
            }
        ]

    class DummyScreen:
        exercise_obj = DummyExercise()

    metric = DummyScreen.exercise_obj.metrics[0]
    popup1 = EditMetricPopup(DummyScreen(), metric)
    count1 = len(
        [
            c
            for c in popup1.content_cls.children[0].children
            if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
        ]
    )
    popup1.dismiss()

    popup2 = EditMetricPopup(DummyScreen(), metric)
    count2 = len(
        [
            c
            for c in popup2.content_cls.children[0].children
            if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
        ]
    )
    assert count1 == 1
    assert count2 == 1


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
def test_add_preset_metric_popup_filters_scope(monkeypatch):
    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {
            "preset_metrics": [{"name": "Focus"}],
            "add_metric": lambda self, *a, **k: None,
            "is_modified": lambda self=None: False,
        },
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)

    metrics = [
        {"name": "Focus", "scope": "preset"},
        {"name": "Level", "scope": "preset"},
        {"name": "Session", "scope": "session"},
    ]

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: metrics)
    screen = EditPresetScreen()
    popup = AddPresetMetricPopup(screen)
    list_view = popup.content_cls.children[0]
    names = {child.text for child in list_view.children}

    assert "Session" not in names
    assert "Focus" not in names
    assert "Level" in names


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_add_session_metric_popup_filters_scope(monkeypatch):
    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {
            "preset_metrics": [{"name": "Duration"}],
            "add_metric": lambda self, *a, **k: None,
            "is_modified": lambda self=None: False,
        },
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)

    metrics = [
        {"name": "Duration", "scope": "session"},
        {"name": "Mood", "scope": "session"},
        {"name": "Focus", "scope": "preset"},
    ]

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: metrics)
    screen = EditPresetScreen()
    popup = AddSessionMetricPopup(screen)
    list_view = popup.content_cls.children[0]
    names = {child.text for child in list_view.children}

    assert "Focus" not in names
    assert "Duration" not in names
    assert "Mood" in names


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
def test_edit_exercise_navigation_flags(monkeypatch):
    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {"sections": [{"name": "S1", "exercises": [{"name": "a"}, {"name": "b"}]}]},
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)
    screen = EditExerciseScreen()
    screen.section_index = 0
    screen.exercise_index = 0
    assert not screen.can_go_prev()
    assert screen.can_go_next()
    screen.exercise_index = 1
    assert screen.can_go_prev()
    assert not screen.can_go_next()


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_exercise_go_next(monkeypatch):
    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {"sections": [{"name": "S1", "exercises": [{"name": "a"}, {"name": "b"}]}]},
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)
    screen = EditExerciseScreen()
    screen.section_index = 0
    screen.exercise_index = 0
    screen.save_enabled = False
    called = {"idx": None}

    def nav(idx):
        called["idx"] = idx

    screen._navigate_to = nav
    screen.go_next_exercise()
    assert called["idx"] == 1


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_exercise_selection_panel_filters(monkeypatch):
    panel = ExerciseSelectionPanel()
    panel.exercise_list = type(
        "L",
        (),
        {
            "children": [],
            "clear_widgets": lambda self: self.children.clear(),
            "add_widget": lambda self, w: self.children.append(w),
        },
    )()

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
def test_presets_screen_preserves_selection_on_leave(monkeypatch):
    """Leaving the Presets screen keeps the app's selected preset."""
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    # Ensure the preset exists
    monkeypatch.setattr(core, "WORKOUT_PRESETS", [{"name": "Sample", "exercises": []}])

    # Provide an app instance with a selected_preset attribute
    class DummyApp:
        selected_preset = ""

    dummy_app = DummyApp()
    monkeypatch.setattr(App, "get_running_app", lambda: dummy_app)

    screen = PresetsScreen()
    dummy_item = type(
        "Obj",
        (),
        {"md_bg_color": (0, 0, 0, 0), "theme_text_color": "Primary", "text_color": (0, 0, 0, 1)},
    )()

    # Select a preset and verify the app reflects it
    screen.select_preset("Sample", dummy_item)
    assert dummy_app.selected_preset == "Sample"

    # Leaving the screen should not clear the app's selection
    screen.on_leave()
    assert dummy_app.selected_preset == "Sample"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_preset_detail_screen_populate(monkeypatch):
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    class DummyList:
        def __init__(self):
            self.children = []

        def clear_widgets(self):
            self.children.clear()

        def add_widget(self, widget):
            self.children.append(widget)

    screen = PresetDetailScreen()
    screen.summary_list = DummyList()

    class DummyApp:
        selected_preset = "Test"

        def init_preset_editor(self):
            self.preset_editor = type(
                "PE",
                (),
                {
                    "sections": [
                        {
                            "name": "Sec",
                            "exercises": [
                                {"name": "Push", "sets": 1},
                                {"name": "Pull", "sets": 2},
                            ],
                        }
                    ],
                    "preset_metrics": [
                        {"name": "Focus", "value": "Upper", "scope": "preset"},
                        {"name": "Notes", "value": "", "scope": "session"},
                    ],
                },
            )()

    dummy_app = DummyApp()
    monkeypatch.setattr(App, "get_running_app", lambda: dummy_app)

    screen.populate()

    texts = [getattr(c, "text", "") for c in screen.summary_list.children]
    assert "Focus: Upper" in texts
    assert "Push - 1 set" in texts
    assert "Pull - 2 sets" in texts


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_preset_overview_screen_populate(monkeypatch):
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    class DummyList:
        def __init__(self):
            self.children = []

        def clear_widgets(self):
            self.children.clear()

        def add_widget(self, widget):
            self.children.append(widget)

    screen = PresetOverviewScreen()
    screen.overview_list = DummyList()

    class DummyApp:
        selected_preset = "Test"

        def init_preset_editor(self):
            self.preset_editor = type(
                "PE",
                (),
                {
                    "sections": [
                        {"name": "Sec", "exercises": [{"name": "Push", "sets": 1}]}
                    ]
                },
            )()

    dummy_app = DummyApp()
    monkeypatch.setattr(App, "get_running_app", lambda: dummy_app)

    monkeypatch.setattr(
        core,
        "get_exercise_details",
        lambda name, *a, **k: {
            "name": name,
            "description": "Desc",
            "is_user_created": False,
        },
    )
    screen.populate()

    entries = [getattr(c, "text", "") for c in screen.overview_list.children]
    assert "Push\nsets 1 | rest: 0s\nDesc" in entries


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_save_exercise_duplicate_name(monkeypatch, tmp_path):
    """Saving with a duplicate user-defined name shows an error."""
    import sqlite3
    from pathlib import Path

    schema = Path(__file__).resolve().parents[1] / "data" / "workout_schema.sql"
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
def test_edit_metric_type_popup_enum_field_visibility():
    class DummyScreen:
        all_metrics = [
            {
                "name": "Speed",
                "type": "int",
                "is_user_created": True,
            }
        ]

    popup = EditMetricTypePopup(DummyScreen(), "Speed", True)
    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 0
    popup.input_widgets["type"].text = "enum"
    children = popup.content_cls.children[0].children
    enum_fields = [
        c
        for c in children
        if getattr(c, "hint_text", "") == "Enum Values (comma separated)"
    ]
    assert len(enum_fields) == 1


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_metric_type_popup_loads_enum_values():
    class DummyScreen:
        all_metrics = [
            {
                "name": "Side",
                "type": "enum",
                "is_user_created": True,
                "enum_values_json": '["Left", "Right", "None"]',
            }
        ]

    popup = EditMetricTypePopup(DummyScreen(), "Side", True)
    assert popup.enum_values_field.text == "Left, Right, None"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_metric_type_popup_shows_affected(monkeypatch):
    class DummyScreen:
        all_metrics = [
            {
                "name": "Speed",
                "type": "int",
                "is_user_created": True,
            }
        ]

    monkeypatch.setattr(
        core, "find_exercises_using_metric_type", lambda *a, **k: ["A", "B"]
    )
    popup = EditMetricTypePopup(DummyScreen(), "Speed", True)
    labels = [
        c.text
        for c in popup.content_cls.children
        if hasattr(c, "text") and isinstance(c.text, str)
    ]
    assert any("Affects 2" in t for t in labels)


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
    dummy = type(
        "Obj",
        (),
        {
            "md_bg_color": (0, 0, 0, 0),
            "theme_text_color": "Primary",
            "text_color": (0, 0, 0, 1),
        },
    )()
    screen.select_preset("Sample", dummy)

    assert dummy.md_bg_color == screen._selected_color


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_preset_selected_text_color_and_clear(monkeypatch):
    """Selecting a preset changes text color and is cleared on leave."""
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    monkeypatch.setattr(
        core,
        "WORKOUT_PRESETS",
        [{"name": "Sample", "exercises": []}],
    )

    screen = PresetsScreen()
    dummy = type(
        "Obj",
        (),
        {
            "md_bg_color": (0, 0, 0, 0),
            "theme_text_color": "Primary",
            "text_color": (0, 0, 0, 1),
        },
    )()
    screen.select_preset("Sample", dummy)

    assert dummy.theme_text_color == "Custom"
    assert dummy.text_color == screen._selected_text_color

    screen.on_leave()

    assert dummy.theme_text_color == "Primary"
    assert screen.selected_item is None


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_edit_preset_populate_details(monkeypatch):
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    metrics = [
        {
            "name": "Focus",
            "type": "str",
            "scope": "preset",
            "enum_values_json": None,
            "input_timing": "preset",
        },
        {
            "name": "Level",
            "type": "int",
            "scope": "preset",
            "enum_values_json": None,
            "input_timing": "preset",
        },
    ]

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: metrics)

    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {
            "preset_metrics": [
                {"name": "Focus", "value": "Legs"},
                {"name": "Level", "value": 2},
            ],
            "is_modified": lambda self=None: False,
            "update_metric": lambda self, *a, **k: None,
            "add_metric": lambda self, *a, **k: None,
        },
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)

    screen = EditPresetScreen()
    screen.populate_details()

    assert set(screen.preset_metric_widgets.keys()) == {"Focus", "Level"}
    assert screen.preset_metric_widgets["Focus"].text == "Legs"


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_preset_name_row_preserved(monkeypatch):
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: [])

    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {
            "preset_metrics": [],
            "is_modified": lambda self=None: False,
            "update_metric": lambda self, *a, **k: None,
            "add_metric": lambda self, *a, **k: None,
        },
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)

    screen = EditPresetScreen()
    screen.populate_details()

    assert screen.ids.preset_name_row in screen.details_box.children
    assert screen.ids.preset_name in screen.ids.preset_name_row.children


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_details_has_add_button(monkeypatch):
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: [])

    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {
            "preset_metrics": [],
            "is_modified": lambda self=None: False,
            "update_metric": lambda self, *a, **k: None,
            "add_metric": lambda self, *a, **k: None,
        },
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)

    screen = EditPresetScreen()
    screen.populate_details()

    assert "add_metric_btn" in screen.ids


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_metrics_has_add_button(monkeypatch):
    from kivy.lang import Builder
    from pathlib import Path

    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    monkeypatch.setattr(core, "get_all_metric_types", lambda *a, **k: [])

    app = _DummyApp()
    app.preset_editor = type(
        "PE",
        (),
        {
            "preset_metrics": [],
            "is_modified": lambda self=None: False,
            "update_metric": lambda self, *a, **k: None,
            "add_metric": lambda self, *a, **k: None,
        },
    )()
    monkeypatch.setattr(App, "get_running_app", lambda: app)

    screen = EditPresetScreen()
    screen.populate_metrics()

    assert "add_session_metric_btn" in screen.ids


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_fallback_input_timing_options(monkeypatch):
    """Fallback schema uses allowed input_timing values."""

    class DummyScreen:
        exercise_obj = type("obj", (), {"metrics": []})()

    monkeypatch.setattr(core, "get_metric_type_schema", lambda *a, **k: [])
    popup = AddMetricPopup(DummyScreen(), mode="new")
    opts = list(popup.input_widgets["input_timing"].values)
    assert opts == [
        "preset",
        "pre_session",
        "post_session",
        "pre_set",
        "post_set",
    ]


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_exercise_summary_item_toggle_expands_and_collapses():
    """ExerciseSummaryItem toggles without errors and updates state."""

    item = ExerciseSummaryItem(name="Push Ups", sets=2)
    item._toggle()  # expand
    assert item._expanded is True
    item._toggle()  # collapse
    assert item._expanded is False
