from importlib.machinery import ModuleSpec
import types
import sys
from pathlib import Path
import importlib.util

# Stub modules for Kivy and KivyMD
kivy_modules = {
    "kivy": types.ModuleType("kivy"),
    "kivy.metrics": types.ModuleType("kivy.metrics"),
    "kivy.properties": types.ModuleType("kivy.properties"),
    "kivy.uix": types.ModuleType("kivy.uix"),
    "kivy.uix.scrollview": types.ModuleType("kivy.uix.scrollview"),
    "kivy.uix.spinner": types.ModuleType("kivy.uix.spinner"),
    "kivy.clock": types.ModuleType("kivy.clock"),
}

kivy_modules["kivy.metrics"].dp = lambda x: x

class _Prop:
    def __init__(self, *args, **kwargs):
        pass

kivy_modules["kivy.properties"].ObjectProperty = _Prop
kivy_modules["kivy.properties"].StringProperty = _Prop
kivy_modules["kivy.properties"].BooleanProperty = _Prop
kivy_modules["kivy.properties"].ListProperty = _Prop
kivy_modules["kivy.clock"].Clock = types.SimpleNamespace(
    schedule_once=lambda *args, **kwargs: types.SimpleNamespace(cancel=lambda: None)
)

for name, module in kivy_modules.items():
    module.__spec__ = ModuleSpec(name, loader=None)
    sys.modules[name] = module

kivymd_modules = {
    "kivymd": types.ModuleType("kivymd"),
    "kivymd.app": types.ModuleType("kivymd.app"),
    "kivymd.uix.screen": types.ModuleType("kivymd.uix.screen"),
    "kivymd.uix.boxlayout": types.ModuleType("kivymd.uix.boxlayout"),
    "kivymd.uix.textfield": types.ModuleType("kivymd.uix.textfield"),
    "kivymd.uix.slider": types.ModuleType("kivymd.uix.slider"),
    "kivymd.uix.label": types.ModuleType("kivymd.uix.label"),
    "kivymd.uix.selectioncontrol": types.ModuleType("kivymd.uix.selectioncontrol"),
}

class _DummyWidget:
    def __init__(self, *args, **kwargs):
        pass

class _BoxLayout(_DummyWidget):
    def __init__(self, *args, **kwargs):
        self.children = []

    def add_widget(self, widget):
        self.children.append(widget)

class _Spinner(_DummyWidget):
    def __init__(self, text="", values=()):
        self.text = text
        self.values = values

class _TextField(_DummyWidget):
    def __init__(self, text="", **kwargs):
        self.text = text

class _Slider(_DummyWidget):
    def __init__(self, value=0, **kwargs):
        self.value = value
        self._binding = None

    def bind(self, **kwargs):
        self._binding = kwargs.get("value")

class _Label(_DummyWidget):
    def __init__(self, text="", **kwargs):
        self.text = text

kivymd_modules["kivymd.uix.selectioncontrol"].MDCheckbox = type(
    "_Checkbox", (_DummyWidget,), {"__init__": lambda self, active=False, **k: setattr(self, "active", active)}
)
kivymd_modules["kivymd.app"].MDApp = _DummyWidget
kivymd_modules["kivymd.uix.screen"].MDScreen = _DummyWidget
kivymd_modules["kivymd.uix.boxlayout"].MDBoxLayout = _BoxLayout
kivymd_modules["kivymd.uix.textfield"].MDTextField = _TextField
kivymd_modules["kivymd.uix.slider"].MDSlider = _Slider
kivymd_modules["kivymd.uix.label"].MDLabel = _Label
kivy_modules["kivy.uix.spinner"].Spinner = _Spinner
kivy_modules["kivy.uix.scrollview"].ScrollView = _DummyWidget

for name, module in kivymd_modules.items():
    module.__spec__ = ModuleSpec(name, loader=None)
    sys.modules[name] = module

spec = importlib.util.spec_from_file_location(
    "metric_input_screen",
    Path(__file__).resolve().parents[1] / "ui" / "screens" / "metric_input_screen.py",
)
metric_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metric_module)
MetricInputScreen = metric_module.MetricInputScreen

# Cleanup stubs so other tests don't see fake modules
for name in list(kivy_modules.keys()) + list(kivymd_modules.keys()):
    sys.modules.pop(name, None)


def test_apply_filters_and_ordering():
    screen = MetricInputScreen()
    metrics = [
        {"name": "A", "is_required": True, "input_timing": "pre_set"},
        {"name": "B", "is_required": True, "input_timing": "post_set"},
        {"name": "C", "is_required": False, "input_timing": "pre_set"},
        {"name": "D", "is_required": False, "input_timing": "post_set"},
    ]

    visible = screen._apply_filters(metrics)
    assert [m["name"] for m in visible] == ["A", "B"]

    screen.toggle_filter("additional")
    visible = screen._apply_filters(metrics)
    assert [m["name"] for m in visible] == ["A", "B", "C", "D"]


def test_navigation_across_sets_and_exercises():
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.exercises = [
                {"name": "Bench", "sets": 2, "metric_defs": []},
                {"name": "Squat", "sets": 1, "metric_defs": []},
            ]
            self.current_exercise = 0
            self.current_set = 0
            self.section_starts = [0]
            self.exercise_sections = [0, 0]

    screen.session = DummySession()
    screen.update_display()

    assert screen.label_text == "Bench \u2013 Set 1 of 2"
    assert not screen.can_nav_left

    screen.navigate_right()
    assert screen.label_text == "Bench \u2013 Set 2 of 2"

    screen.navigate_right()
    assert screen.label_text == "Squat \u2013 Set 1 of 1"
    assert not screen.can_nav_right

    screen.navigate_left()
    assert screen.label_text == "Bench \u2013 Set 2 of 2"


def test_multi_tap_navigation():
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.exercises = [
                {"name": "Bench", "sets": 2, "metric_defs": []},
                {"name": "Squat", "sets": 2, "metric_defs": []},
                {"name": "Run", "sets": 1, "metric_defs": []},
            ]
            self.current_exercise = 0
            self.current_set = 0
            self.section_starts = [0, 2]
            self.exercise_sections = [0, 0, 1]

    screen.session = DummySession()
    screen.update_display()

    screen.navigate_right_double()
    assert (screen.exercise_idx, screen.set_idx) == (1, 0)

    screen.navigate_right_triple()
    assert (screen.exercise_idx, screen.set_idx) == (2, 0)

    screen.navigate_left_double()
    assert (screen.exercise_idx, screen.set_idx) == (1, 0)

    screen.navigate_left_triple()
    assert (screen.exercise_idx, screen.set_idx) == (0, 0)


def test_save_future_metrics_preserves_session_state():
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.exercises = [
                {"name": "Bench", "sets": 1, "results": []},
                {"name": "Squat", "sets": 1, "results": []},
            ]
            self.current_exercise = 0
            self.current_set = 0
            self.current_set_start_time = 0
            self.pending_pre_set_metrics = {}
            self.awaiting_post_set_metrics = False

        def record_metrics(self, metrics):
            ex = self.exercises[self.current_exercise]
            ex.setdefault("results", []).append({"metrics": metrics})
            self.current_set += 1
            if self.current_set >= ex["sets"]:
                self.current_set = 0
                self.current_exercise += 1
            self.pending_pre_set_metrics = {}
            self.awaiting_post_set_metrics = False
            return False

    dummy_session = DummySession()
    dummy_app = types.SimpleNamespace(workout_session=dummy_session)
    metric_module.MDApp.get_running_app = classmethod(lambda cls: dummy_app)


    class DummyList:
        def __init__(self):
            self.children = []

        def clear_widgets(self):
            pass

        def add_widget(self, widget):
            pass

    screen.metrics_list = DummyList()
    screen.session = dummy_session
    screen.exercise_idx = 1
    screen.set_idx = 0

    screen.save_metrics()

    assert dummy_session.current_exercise == 0
    assert dummy_session.current_set == 0
    assert len(dummy_session.exercises[1]["results"]) == 1


def test_slider_row_updates_label():
    screen = MetricInputScreen()
    row = screen._create_row({"name": "Intensity", "type": "slider"}, value=0.5)
    slider = row.input_widget
    value_label = next(
        child
        for child in row.children
        if getattr(child, "text", None) is not None and child.text != "Intensity"
    )
    assert value_label.text == "0.50"
    slider.value = 0.72
    slider._binding(slider, slider.value)
    assert value_label.text == "0.72"
    
def test_save_future_metrics_returns_to_rest():
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.exercises = [
                {"name": "Bench", "sets": 1, "results": []},
                {"name": "Squat", "sets": 1, "results": []},
            ]
            self.current_exercise = 0
            self.current_set = 0
            self.current_set_start_time = 0
            self.pending_pre_set_metrics = {}
            self.awaiting_post_set_metrics = False

        def record_metrics(self, metrics):
            ex = self.exercises[self.current_exercise]
            ex.setdefault("results", []).append({"metrics": metrics})
            self.current_set += 1
            if self.current_set >= ex["sets"]:
                self.current_set = 0
                self.current_exercise += 1
            self.pending_pre_set_metrics = {}
            self.awaiting_post_set_metrics = False
            return False

    dummy_session = DummySession()
    dummy_app = types.SimpleNamespace(workout_session=dummy_session)
    metric_module.MDApp.get_running_app = classmethod(lambda cls: dummy_app)

    class DummyList:
        def __init__(self):
            self.children = []

        def clear_widgets(self):
            pass

        def add_widget(self, widget):
            pass

    screen.metrics_list = DummyList()
    screen.session = dummy_session
    screen.exercise_idx = 1
    screen.set_idx = 0
    screen.manager = types.SimpleNamespace(current="metric_input")

    screen.save_metrics()

    assert screen.manager.current == "rest"

