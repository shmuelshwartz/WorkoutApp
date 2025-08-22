"""Tests for the GridController sizing behaviour."""

from importlib.machinery import ModuleSpec
import importlib.util
from pathlib import Path
import sys
import types


# ---------------------------------------------------------------------------
# Provide minimal Kivy Clock stub so GridController can be imported without
# the real Kivy dependency. ``schedule_once`` executes callbacks immediately
# to keep tests synchronous.
clock_mod = types.ModuleType("kivy.clock")
clock_mod.Clock = types.SimpleNamespace(schedule_once=lambda func, _dt=0: func(0))
clock_mod.__spec__ = ModuleSpec("kivy.clock", loader=None)
sys.modules["kivy.clock"] = clock_mod
sys.modules["kivy"] = types.ModuleType("kivy")

# Import GridController from the project.
spec = importlib.util.spec_from_file_location(
    "row_controller", Path(__file__).resolve().parents[1] / "ui" / "row_controller.py"
)
row_controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(row_controller)
GridController = row_controller.GridController

# Clean up stubs so they don't leak into other tests.
sys.modules.pop("kivy.clock", None)
sys.modules.pop("kivy", None)


def test_column_width_expands_to_largest_widget():
    """Column width should match the widest widget registered."""

    class Widget:
        def __init__(self, width: float):
            self.width = width
            self.height = 10

        def bind(self, **kwargs):
            # GridController hooks into size changes; binding support is
            # recorded but unused in this lightweight test widget.
            self._bindings = kwargs

    gc = GridController()
    w1 = Widget(50)
    w2 = Widget(120)
    gc.register(0, 0, w1)
    gc.register(1, 0, w2)

    assert w1.width == 120
    assert w2.width == 120
