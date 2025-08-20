from __future__ import annotations

import time

from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.widget import Widget

from tempo import TempoCycle


class _TempoSegment(Widget):
    """Single colored segment that fills left to right."""

    color = ListProperty([1, 1, 1, 1])
    progress = NumericProperty(0.0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas:
            self._bg_color = Color(rgba=(*self.color[:3], 0.3))
            self._bg_rect = Rectangle(pos=self.pos, size=self.size)
            self._fg_color = Color(rgba=self.color)
            self._fg_rect = Rectangle(pos=self.pos, size=(0, self.height))
        self.bind(
            pos=self._update_graphics,
            size=self._update_graphics,
            progress=self._update_graphics,
            color=self._recolor,
        )

    def _recolor(self, *args):
        self._bg_color.rgba = (*self.color[:3], 0.3)
        self._fg_color.rgba = self.color

    def _update_graphics(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size
        self._fg_rect.pos = self.pos
        self._fg_rect.size = (self.width * self.progress, self.height)


class TempoVisualizer(BoxLayout):
    """Displays a tempo as a horizontal progress bar."""

    tempo = StringProperty("0000")
    colors = ListProperty(
        [
            [1, 0.2, 0.2, 1],  # concentric
            [1, 0.6, 0.2, 1],  # pause top
            [0.2, 0.6, 1, 1],  # eccentric
            [0.2, 1, 0.6, 1],  # pause bottom
        ]
    )

    def __init__(self, **kwargs):
        super().__init__(orientation="horizontal", **kwargs)
        self._cycle: TempoCycle | None = None
        self._segments: list[_TempoSegment] = []
        self._event = None
        self.bind(tempo=self._build)
        if self.tempo:
            self._build()

    def _build(self, *args):
        self.clear_widgets()
        self._segments = []
        self._cycle = TempoCycle(self.tempo)
        total = self._cycle.total or 1
        for i, phase in enumerate(self._cycle.phases):
            seg = _TempoSegment(color=self.colors[i], size_hint_x=phase.duration / total)
            self._segments.append(seg)
            self.add_widget(seg)

    def start(self, start_time: float | None = None) -> None:
        """Begin visual playback of the tempo cycle.

        ``start_time`` can optionally be provided to align the visualisation
        with an external clock (e.g. the sound system). If omitted, the
        animation starts from the current moment.
        """

        now = time.perf_counter()
        if start_time is None:
            self._start = now
        else:
            # ``start_time`` is based on ``time.time()`` so convert it to the
            # ``perf_counter`` reference to keep progress in sync.
            self._start = now - (time.time() - start_time)

        if self._event:
            self._event.cancel()
        self._event = Clock.schedule_interval(self._update, 1 / 30)

    def stop(self):
        if self._event:
            self._event.cancel()
            self._event = None

    def _update(self, dt):
        if not self._cycle:
            return
        elapsed = time.perf_counter() - self._start
        idx, frac, _ = self._cycle.phase_at(elapsed)
        for i, seg in enumerate(self._segments):
            if i < idx:
                seg.progress = 1
            elif i == idx:
                seg.progress = frac
            else:
                seg.progress = 0
