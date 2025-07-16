import importlib.util
import os
import pytest

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

    from main import RestScreen, MetricInputScreen, WorkoutActiveScreen, AddMetricPopup
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
