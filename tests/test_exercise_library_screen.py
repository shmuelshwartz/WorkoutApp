import importlib.util
import os
import pytest

os.environ["KIVY_WINDOW"] = "mock"

kivy_available = (
    importlib.util.find_spec("kivy") is not None
    and importlib.util.find_spec("kivymd") is not None
)

if kivy_available:
    os.environ.setdefault("KIVY_UNITTEST", "1")
    from kivy.app import App
    from kivy.properties import ObjectProperty
    from ui.screens.exercise_library import ExerciseLibraryScreen
    from ui.stubs.library_data import LibraryStubDataProvider

    class _DummyApp:
        theme_cls = object()

        def property(self, name, default=None):
            return ObjectProperty(None)

    @pytest.fixture(autouse=True)
    def _provide_app(monkeypatch):
        monkeypatch.setattr(App, "get_running_app", lambda: _DummyApp())
        yield


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_populate_with_stub_data():
    screen = ExerciseLibraryScreen(
        data_provider=LibraryStubDataProvider(), test_mode=True
    )
    screen.exercise_list = type("List", (), {"data": []})()
    screen.metric_list = type("List", (), {"data": []})()
    screen.populate()
    assert screen.exercise_list.data
    assert screen.metric_list.data
