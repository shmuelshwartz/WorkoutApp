"""Utilities for synchronizing row heights across multiple widgets.

The :class:`RowController` maintains a mapping of row indices to
widgets that should share the same height.  When any registered widget
changes size, the tallest height for that row is applied to all widgets
in the row.  This is required for the metric input screen where metric
names and values live in separate containers but must align perfectly.
"""

from collections import defaultdict
from typing import Dict, List, Any

from kivy.clock import Clock


class RowController:
    """Track and apply uniform heights for rows of widgets.

    Widgets register themselves with a row index via :meth:`register`.
    The controller ensures every widget in the same row always shares the
    maximum height seen for that row.  Updates are scheduled with
    ``Clock`` so layout calculations have finished before measurements
    occur.
    """

    def __init__(self) -> None:
        self._heights: Dict[int, float] = {}
        self._widgets: Dict[int, List[Any]] = defaultdict(list)

    # ------------------------------------------------------------------
    def register(self, row: int, widget: Any) -> None:
        """Register *widget* to participate in unified row sizing.

        Parameters
        ----------
        row:
            Row index the widget belongs to.
        widget:
            The widget whose ``height`` should match others in the row.
        """

        self._widgets[row].append(widget)
        if hasattr(widget, "bind"):
            widget.bind(height=lambda inst, val: self._update_row(row, val))
        # Defer initial sizing until after the next frame to ensure the
        # widget's preferred height is available.
        initial_height = getattr(widget, "height", 0)
        Clock.schedule_once(lambda _dt: self._update_row(row, initial_height))

    # ------------------------------------------------------------------
    def _update_row(self, row: int, height: float) -> None:
        """Apply ``height`` to all widgets in *row* if it is the maximum."""

        if height <= 0:
            return
        if height > self._heights.get(row, 0):
            self._heights[row] = height
            for w in self._widgets[row]:
                w.height = height

    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Forget all tracked widgets and heights."""

        self._heights.clear()
        self._widgets.clear()
