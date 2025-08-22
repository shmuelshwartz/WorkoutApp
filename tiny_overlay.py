"""Developer metrics overlay to inspect sizing parameters.
# TINY-SCREEN: overlay widget
"""
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.metrics import Metrics, dp, sp

from tiny_screen import get_smallest_width_dp, get_safe_area_insets, get_font_scale


class TinyOverlay(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(size_hint=(None, None), size=(220, 130), **kwargs)
        self.label = Label(size=self.size, halign="left", valign="top")
        self.label.bind(size=self.label.setter("text_size"))
        self.add_widget(self.label)
        self.opacity = 0.8
        self.canvas.opacity = 0.8
        Window.bind(size=self._reposition)
        self._reposition()
        Clock.schedule_interval(self.update, 0.5)

    def _reposition(self, *args):
        self.pos = (0, Window.height - self.height)

    def update(self, *_):
        sa = get_safe_area_insets()
        text = (
            f"size: {Window.width}x{Window.height}\n"
            f"dpi: {Window.dpi:.1f} dens:{Metrics.density:.2f}\n"
            f"dp1:{dp(1):.1f}px sp1:{sp(1):.1f}px\n"
            f"sw:{get_smallest_width_dp():.0f}dp font:{get_font_scale():.2f}\n"
            f"safe:{sa}"
        )
        self.label.text = text


def enable_overlay():
    if getattr(Window, "_tiny_overlay", None) is None:
        overlay = TinyOverlay()
        Window.add_widget(overlay)
        Window._tiny_overlay = overlay
    else:
        Window._tiny_overlay.update()


def toggle_overlay(*_):
    overlay = getattr(Window, "_tiny_overlay", None)
    if not overlay:
        enable_overlay()
        return
    overlay.opacity = 0 if overlay.opacity else 0.8
