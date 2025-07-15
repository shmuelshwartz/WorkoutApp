import types
import sys
import pytest

# Fixture to stub kivy/kivymd modules so main.py can be imported
@pytest.fixture()
def kivy_stubs(monkeypatch):
    class DummyProp:
        def __init__(self, *a, **k):
            pass

    class DummyWidget:
        def __init__(self, text=""):
            self.text = text
            self.error = False
            self.text_color = None
            self.helper_text = ""
            self.helper_text_mode = ""
            self.active = False

    class DummySpinner(DummyWidget):
        pass

    class DummyTextField(DummyWidget):
        pass

    class DummyCheckbox(DummyWidget):
        def __init__(self):
            super().__init__("")
            self.active = False

    modules = {
        "kivymd.app": {"MDApp": type("MDApp", (), {})},
        "kivymd.uix.screen": {"MDScreen": type("MDScreen", (), {})},
        "kivymd.uix.boxlayout": {"MDBoxLayout": type("MDBoxLayout", (), {})},
        "kivymd.uix.textfield": {"MDTextField": DummyTextField},
        "kivymd.uix.slider": {"MDSlider": type("MDSlider", (), {})},
        "kivymd.uix.label": {"MDLabel": type("MDLabel", (), {})},
        "kivymd.uix.list": {
            "OneLineListItem": type("OneLineListItem", (), {"bind": lambda self, **k: None}),
            "OneLineRightIconListItem": type("OneLineRightIconListItem", (), {}),
            "IconRightWidget": type("IconRightWidget", (), {}),
            "MDList": type("MDList", (), {"add_widget": lambda self, *a, **k: None}),
        },
        "kivymd.uix.selectioncontrol": {"MDCheckbox": DummyCheckbox},
        "kivymd.uix.button": {
            "MDIconButton": type("MDIconButton", (), {}),
            "MDRaisedButton": type("MDRaisedButton", (), {}),
        },
        "kivymd.uix.card": {"MDSeparator": type("MDSeparator", (), {})},
        "kivymd.uix.dialog": {"MDDialog": type("MDDialog", (), {})},
    }

    stubbed = []
    for name, attrs in modules.items():
        mod = types.ModuleType(name)
        for attr, value in attrs.items():
            setattr(mod, attr, value)
        monkeypatch.setitem(sys.modules, name, mod)
        stubbed.append(name)

    base = types.ModuleType("kivy")
    monkeypatch.setitem(sys.modules, "kivy", base)
    monkeypatch.setitem(sys.modules, "kivy.lang", types.ModuleType("kivy.lang"))
    sys.modules["kivy.lang"].Builder = type("Builder", (), {"load_file": staticmethod(lambda x: None)})
    monkeypatch.setitem(sys.modules, "kivy.clock", types.ModuleType("kivy.clock"))
    sys.modules["kivy.clock"].Clock = type("Clock", (), {"schedule_interval": staticmethod(lambda *a, **k: None)})
    monkeypatch.setitem(sys.modules, "kivy.metrics", types.ModuleType("kivy.metrics"))
    sys.modules["kivy.metrics"].dp = lambda x: x
    props = types.ModuleType("kivy.properties")
    for prop in ["NumericProperty", "StringProperty", "ObjectProperty", "BooleanProperty", "ListProperty"]:
        setattr(props, prop, DummyProp)
    monkeypatch.setitem(sys.modules, "kivy.properties", props)
    monkeypatch.setitem(sys.modules, "kivy.uix.spinner", types.ModuleType("kivy.uix.spinner"))
    sys.modules["kivy.uix.spinner"].Spinner = DummySpinner
    monkeypatch.setitem(sys.modules, "kivy.uix.scrollview", types.ModuleType("kivy.uix.scrollview"))
    sys.modules["kivy.uix.scrollview"].ScrollView = type("ScrollView", (), {"add_widget": lambda self, *a, **k: None})
    monkeypatch.setitem(sys.modules, "kivy.uix.screenmanager", types.ModuleType("kivy.uix.screenmanager"))
    sys.modules["kivy.uix.screenmanager"].NoTransition = type("NoTransition", (), {})
    monkeypatch.setitem(sys.modules, "kivy.core", types.ModuleType("kivy.core"))
    monkeypatch.setitem(sys.modules, "kivy.core.window", types.ModuleType("kivy.core.window"))
    sys.modules["kivy.core.window"].Window = type("Window", (), {"size": (0, 0)})

    yield

    for name in stubbed:
        monkeypatch.setitem(sys.modules, name, None)


def test_duplicate_metric_name_rejected(kivy_stubs):
    import main
    import core

    class FakeScreen:
        def __init__(self):
            self.exercise_obj = core.Exercise()
            self.save_enabled = False

        def populate(self):
            pass

    screen = FakeScreen()
    screen.exercise_obj.metrics = [{"name": "Reps"}]

    popup = main.AddMetricPopup.__new__(main.AddMetricPopup)
    popup.screen = screen
    popup.input_widgets = {
        "name": main.MDTextField(),
        "input_type": main.Spinner(),
        "source_type": main.Spinner(),
    }
    popup.input_widgets["name"].text = "Reps"
    popup.input_widgets["input_type"].text = "int"
    popup.input_widgets["source_type"].text = "manual_text"
    popup.enum_values_field = main.MDTextField()
    popup.show_metric_list = lambda *a, **k: None

    popup.save_metric()

    assert len(screen.exercise_obj.metrics) == 1
    assert popup.input_widgets["name"].error

