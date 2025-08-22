"""Utilities for aligning widgets in a 2D grid.

The original implementation only synchronised row heights.  The metric
input screen now renders a single grid where both rows and columns must
align.  This module therefore provides :class:`GridController` which
normalises row heights and column widths simultaneously.  Every widget in
the same row shares the *minimum* height observed for that row while
widgets in the same column expand to match the *maximum* width observed in
that column.  Using the minimum for height preserves vertical compactness
on small screens, whereas taking the maximum width ensures columns are wide
enough for their largest widget.
"""

from collections import defaultdict
from typing import Dict, List, Any

from kivy.clock import Clock


class GridController:
    """Maintain uniform row heights and column widths.

    Widgets register with a ``row`` and ``col`` index via :meth:`register`.
    When a widget's size changes the controller recomputes the minimum
    height for that row and the maximum width for that column, applying
    those dimensions to all widgets in the same row or column.  Updates
    are scheduled with :class:`~kivy.clock.Clock` so the widget's natural
    size is available before measurements occur.
    """

    def __init__(self) -> None:
        self._row_heights: Dict[int, float] = {}
        self._col_widths: Dict[int, float] = {}
        self._rows: Dict[int, List[Any]] = defaultdict(list)
        self._cols: Dict[int, List[Any]] = defaultdict(list)

    # ------------------------------------------------------------------
    def register(self, row: int, col: int, widget: Any) -> None:
        """Register *widget* to participate in grid sizing.

        Parameters
        ----------
        row:
            Row index the widget belongs to.
        col:
            Column index the widget belongs to.
        widget:
            The widget whose ``height`` and ``width`` should match others in
            the same row and column.
        """

        self._rows[row].append(widget)
        self._cols[col].append(widget)
        if hasattr(widget, "bind"):
            widget.bind(
                height=lambda inst, val: self._update_row(row),
                width=lambda inst, val: self._update_col(col),
            )
        # Defer initial sizing until after the next frame to ensure the
        # widget's preferred size is available.
        Clock.schedule_once(lambda _dt: self._update(row, col))

    # ------------------------------------------------------------------
    def _update_row(self, row: int) -> None:
        """Apply the minimum height of row *row* to all its widgets."""

        heights = [getattr(w, "height", 0) for w in self._rows[row] if getattr(w, "height", 0) > 0]
        if not heights:
            return
        min_height = min(heights)
        if min_height != self._row_heights.get(row):
            self._row_heights[row] = min_height
            for w in self._rows[row]:
                w.height = min_height

    # ------------------------------------------------------------------
    def _update_col(self, col: int) -> None:
        """Apply the maximum width of column *col* to all its widgets."""

        widths = [getattr(w, "width", 0) for w in self._cols[col] if getattr(w, "width", 0) > 0]
        if not widths:
            return
        max_width = max(widths)
        if max_width != self._col_widths.get(col):
            self._col_widths[col] = max_width
            for w in self._cols[col]:
                w.width = max_width

    # ------------------------------------------------------------------
    def _update(self, row: int, col: int) -> None:
        """Update both row and column sizing for the given cell."""

        self._update_row(row)
        self._update_col(col)

    # ------------------------------------------------------------------
    def clear(self) -> None:
        """Forget all tracked widgets and dimensions."""

        self._row_heights.clear()
        self._col_widths.clear()
        self._rows.clear()
        self._cols.clear()


# Backwards compatible alias -------------------------------------------------
# ``RowController`` previously only handled rows.  Expose it as an alias for
# ``GridController`` so existing imports keep working.
RowController = GridController

