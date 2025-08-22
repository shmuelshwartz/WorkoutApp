"""Dialog helpers for safe display on tiny screens.
# TINY-SCREEN: dialog safety mixin
"""
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import dp

from tiny_screen import get_safe_area_insets


class SafeDialogMixin:
    """Mixin to cap dialog height within the visible viewport."""

    def open(self, *a, **k):  # type: ignore[override]
        super().open(*a, **k)  # type: ignore[misc]
        Clock.schedule_once(self._enforce_max_height, 0)

    def _enforce_max_height(self, *_):
        sa = get_safe_area_insets()
        max_h = Window.height - dp(sa.get("top", 0) + sa.get("bottom", 0))
        if self.height > max_h:
            self.height = max_h
