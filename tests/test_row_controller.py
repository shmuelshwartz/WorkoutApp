"""Tests for :mod:`ui.row_controller` enforcing column width behaviour."""

import types
import sys
from importlib import util
from pathlib import Path


def _import_grid_controller():
    """Import :class:`GridController` with stubbed Kivy dependencies."""

    kivy = types.ModuleType("kivy")
    kivy_clock = types.ModuleType("kivy.clock")

    def schedule_once(func, *args, **kwargs):
        func(0)
        return types.SimpleNamespace(cancel=lambda: None)

    kivy_clock.Clock = types.SimpleNamespace(schedule_once=schedule_once)
    sys.modules["kivy"] = kivy
    sys.modules["kivy.clock"] = kivy_clock

    spec = util.spec_from_file_location(
        "row_controller", Path(__file__).resolve().parents[1] / "ui" / "row_controller.py"
    )
    module = util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Clean up stubs so other tests remain unaffected.
    sys.modules.pop("kivy.clock", None)
    sys.modules.pop("kivy", None)
    return module.GridController


class DummyWidget:
    """Minimal stand-in for Kivy widgets used in tests."""

    def __init__(self, width=0, height=0):
        self.width = width
        self.height = height
        self._width_cb = None
        self._height_cb = None

    def bind(self, **kwargs):
        self._width_cb = kwargs.get("width")
        self._height_cb = kwargs.get("height")

    def set_width(self, value):
        self.width = value
        if self._width_cb:
            self._width_cb(self, value)

    def set_height(self, value):
        self.height = value
        if self._height_cb:
            self._height_cb(self, value)


def test_column_width_matches_largest_widget():
    GridController = _import_grid_controller()
    controller = GridController()

    w1 = DummyWidget(width=50, height=20)
    w2 = DummyWidget(width=80, height=20)

    controller.register(0, 0, w1)
    controller.register(1, 0, w2)

    assert w1.width == 80 and w2.width == 80

    w1.set_width(120)
    assert w1.width == 120 and w2.width == 120

