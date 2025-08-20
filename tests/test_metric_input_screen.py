from importlib.machinery import ModuleSpec
import types
import sys
from pathlib import Path
import importlib.util

# Stub minimal Kivy/KivyMD modules required by metric_input_screen
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
    "kivymd.uix.textfield": types.ModuleType("kivymd.uix.textfield"),
    "kivymd.uix.slider": types.ModuleType("kivymd.uix.slider"),
    "kivymd.uix.label": types.ModuleType("kivymd.uix.label"),
    "kivymd.uix.selectioncontrol": types.ModuleType("kivymd.uix.selectioncontrol"),
    "kivymd.uix.button": types.ModuleType("kivymd.uix.button"),
}

class _DummyWidget:
    def __init__(self, *args, **kwargs):
        pass

class _TextField(_DummyWidget):
    def __init__(self, text="", **kwargs):
        self.text = text
    def bind(self, **kwargs):
        self._binding = kwargs

class _Slider(_DummyWidget):
    def __init__(self, value=0, **kwargs):
        self.value = value
    def bind(self, **kwargs):
        self._binding = kwargs

class _Spinner(_DummyWidget):
    def __init__(self, text="", values=()):
        self.text = text
        self.values = values
    def bind(self, **kwargs):
        self._binding = kwargs

class _Checkbox(_DummyWidget):
    def __init__(self, active=False):
        self.active = active
    def bind(self, **kwargs):
        self._binding = kwargs

class _Label(_DummyWidget):
    def __init__(self, text="", **kwargs):
        self.text = text

class _Layout(list):
    """Minimal container to emulate Kivy layouts in tests."""
    def __init__(self):
        super().__init__()
        self.cols = 0

    def clear_widgets(self):
        self.clear()

    def add_widget(self, widget):
        self.append(widget)

    def __bool__(self):
        return True

kivymd_modules["kivymd.app"].MDApp = _DummyWidget
kivymd_modules["kivymd.uix.screen"].MDScreen = _DummyWidget
kivymd_modules["kivymd.uix.textfield"].MDTextField = _TextField
kivymd_modules["kivymd.uix.slider"].MDSlider = _Slider
kivymd_modules["kivymd.uix.label"].MDLabel = _Label
kivymd_modules["kivymd.uix.selectioncontrol"].MDCheckbox = _Checkbox
kivymd_modules["kivymd.uix.button"].MDFlatButton = _DummyWidget
kivy_modules["kivy.uix.spinner"].Spinner = _Spinner
kivy_modules["kivy.uix.scrollview"].ScrollView = _DummyWidget

for name, module in kivymd_modules.items():
    module.__spec__ = ModuleSpec(name, loader=None)
    sys.modules[name] = module

spec = importlib.util.spec_from_file_location(
    "metric_input_screen",
    Path(__file__).resolve().parents[1] / "ui" / "screens" / "session" / "metric_input_screen.py",
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


def test_on_cell_change_updates_session():
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.exercises = [{"name": "Bench", "sets": 1, "results": [{"metrics": {}}]}]
            self.edited = None
            self.pending = {}

        def edit_set_metrics(self, ex, st, data):
            self.edited = (ex, st, data)

        def set_pre_set_metrics(self, data, ex, st):
            self.pending[(ex, st)] = data

    dummy_session = DummySession()
    dummy_app = types.SimpleNamespace(workout_session=dummy_session)
    metric_module.MDApp.get_running_app = classmethod(lambda cls: dummy_app)

    screen.session = dummy_session
    widget = metric_module.MDTextField(text="5")
    screen._on_cell_change("Reps", "int", 0, widget)
    assert dummy_session.edited == (0, 0, {"Reps": 5})

    dummy_session.exercises[0]["results"] = []
    screen._on_cell_change("Reps", "int", 0, widget)
    assert dummy_session.pending[(0, 0)] == {"Reps": 5}


def test_metric_store_fallback_on_rebuild():
    """Widget should prefill metrics from session.metric_store for unfinished sets."""
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.exercises = [
                {
                    "name": "Bench",
                    "sets": 1,
                    "metric_defs": [
                        {
                            "name": "Reps",
                            "type": "int",
                            "is_required": True,
                            "input_timing": "post_set",
                        }
                    ],
                    "results": [],
                }
            ]
            self.metric_store = {}

        def set_pre_set_metrics(self, data, ex, st):
            self.metric_store[(ex, st)] = data

    dummy_session = DummySession()
    dummy_app = types.SimpleNamespace(workout_session=dummy_session)
    metric_module.MDApp.get_running_app = classmethod(lambda cls: dummy_app)

    screen.session = dummy_session
    screen.metric_names = _Layout()
    screen.metric_values = _Layout()
    screen.set_headers = _Layout()

    screen.update_metrics()
    screen._on_cell_change("Reps", "int", 0, metric_module.MDTextField(text="5"))
    screen.update_metrics()
    assert screen.metric_cells[("Reps", 0)].text == "5"


def test_save_metrics_records_new_set(monkeypatch):
    """Saving metrics should finalize the recently completed set."""
    screen = MetricInputScreen()

    class DummySession:
        def __init__(self):
            self.current_exercise = 0
            self.current_set = 0
            self.exercises = [{"name": "Bench", "sets": 1, "results": []}]
            # pending_pre_set_metrics stores entries from _on_cell_change
            self.pending_pre_set_metrics = {(0, 0): {"Reps": 5}}
            self.metric_store = {(0, 0): {"Reps": 5}}
            self.recorded = False

        def record_metrics(self, ex, st, metrics):
            if ex == 0 and st == 0:
                self.recorded = True

    dummy_session = DummySession()
    dummy_app = types.SimpleNamespace(
        workout_session=dummy_session, record_new_set=True, record_pre_set=False
    )
    monkeypatch.setattr(metric_module.MDApp, "get_running_app", classmethod(lambda cls: dummy_app))

    manager = types.SimpleNamespace(current="metric_input")
    screen.manager = manager

    screen.save_metrics()

    assert dummy_session.recorded
    assert manager.current == "rest"
    assert dummy_app.record_new_set is False
