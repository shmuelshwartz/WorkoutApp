import importlib.util
import os
import pytest

os.environ["KIVY_WINDOW"] = "mock"

kivy_available = (
    importlib.util.find_spec("kivy") is not None
    and importlib.util.find_spec("kivymd") is not None
)

if kivy_available:
    from kivy.app import App
    from kivy.properties import ObjectProperty
    from kivy.lang import Builder
    from pathlib import Path
    from ui.screens.workout_history_screen import WorkoutHistoryScreen
    import ui.screens.workout_history_screen as w

    class _DummyApp:
        theme_cls = object()

        def property(self, name, default=None):
            return ObjectProperty(None)

    @pytest.fixture(autouse=True)
    def _provide_app(monkeypatch):
        monkeypatch.setattr(App, "get_running_app", lambda: _DummyApp())
        yield


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_history_entries_include_day(monkeypatch):
    Builder.load_file(str(Path(__file__).resolve().parents[1] / "main.kv"))

    class DummyDateTime:
        @classmethod
        def fromtimestamp(cls, ts):
            from datetime import datetime
            return datetime(2025, 8, 11, 14, 29)

    monkeypatch.setattr(w, "get_session_history", lambda: [{"preset_name": "Leg day", "started_at": 0}])
    monkeypatch.setattr(w, "datetime", DummyDateTime)

    screen = WorkoutHistoryScreen()
    screen.populate()
    lst = screen.ids["history_list"]
    assert lst.children, "No history items added"
    item = lst.children[0]
    assert item.secondary_text == "14:29 Mon 11/08/2025"
