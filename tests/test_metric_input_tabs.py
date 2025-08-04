import importlib.util
import sys
import types
from pathlib import Path
from importlib.machinery import ModuleSpec

# Create stub modules for Kivy and KivyMD to avoid heavy dependencies
kivy_modules = {
    "kivy": types.ModuleType("kivy"),
    "kivy.metrics": types.ModuleType("kivy.metrics"),
    "kivy.properties": types.ModuleType("kivy.properties"),
    "kivy.uix": types.ModuleType("kivy.uix"),
    "kivy.uix.scrollview": types.ModuleType("kivy.uix.scrollview"),
    "kivy.uix.spinner": types.ModuleType("kivy.uix.spinner"),
}

kivy_modules["kivy.metrics"].dp = lambda x: x

class _Prop:
    def __init__(self, *args, **kwargs):
        pass

kivy_modules["kivy.properties"].ObjectProperty = _Prop
kivy_modules["kivy.properties"].StringProperty = _Prop

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
}

class _DummyWidget:
    pass

kivymd_modules["kivymd.app"].MDApp = _DummyWidget
kivymd_modules["kivymd.uix.screen"].MDScreen = _DummyWidget
kivymd_modules["kivymd.uix.boxlayout"].MDBoxLayout = _DummyWidget
kivymd_modules["kivymd.uix.textfield"].MDTextField = _DummyWidget
kivymd_modules["kivymd.uix.slider"].MDSlider = _DummyWidget
kivymd_modules["kivymd.uix.label"].MDLabel = _DummyWidget
kivy_modules["kivy.uix.spinner"].Spinner = _DummyWidget
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


class DummyHeader:
    def __init__(self, tab):
        self.tab = tab


class DummyTabs:
    def __init__(self, tabs):
        self._headers = [DummyHeader(t) for t in tabs]
        self.switched_to = None

    def switch_tab(self, header):
        self.switched_to = header

    def get_tab_list(self):
        return self._headers


class DummyTab:
    pass


def test_reset_tabs_switches_to_correct_content():
    prev_tab = DummyTab()
    next_tab = DummyTab()
    prev_req = DummyTab()
    next_req = DummyTab()

    outer_tabs = DummyTabs([prev_tab, next_tab])
    inner_prev = DummyTabs([prev_req])
    inner_next = DummyTabs([next_req])
    prev_req.parent = inner_prev
    next_req.parent = inner_next

    screen = MetricInputScreen()
    screen.ids = {
        "set_tabs": outer_tabs,
        "prev_tab": prev_tab,
        "next_tab": next_tab,
        "prev_required_tab": prev_req,
        "next_required_tab": next_req,
    }

    screen.current_tab = "next"
    screen.reset_tabs()

    assert outer_tabs.switched_to.tab is next_tab
    assert inner_next.switched_to.tab is next_req
