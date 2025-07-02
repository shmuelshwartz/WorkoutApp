from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
)
from kivymd.uix.screen import MDScreen
from core import WORKOUT_PRESETS

import time
import math


class WorkoutActiveScreen(MDScreen):
    """Screen that shows an active workout with a stopwatch."""

    elapsed = NumericProperty(0.0)
    start_time = NumericProperty(0.0)
    _event = None

    def start_timer(self, *args):
        """Start or resume the stopwatch."""
        self.stop_timer()
        self.elapsed = 0.0
        self.start_time = time.time()
        self._event = Clock.schedule_interval(self._update_elapsed, 0.1)

    def stop_timer(self, *args):
        """Stop updating the stopwatch without clearing the start time."""
        if self._event:
            self._event.cancel()
            self._event = None

    def _update_elapsed(self, dt):
        self.elapsed = time.time() - self.start_time

    def format_time(self):

        minutes, seconds = divmod(int(self.elapsed), 60)
        return f"{minutes:02d}:{seconds:02d}"




class RestScreen(MDScreen):
    timer_label = StringProperty("20")
    target_time = NumericProperty(0)

    def on_enter(self, *args):
        if not self.target_time or self.target_time <= time.time():
            self.target_time = time.time() + 20
        self.update_timer(0)
        self._event = Clock.schedule_interval(self.update_timer, 0.1)
        return super().on_enter(*args)

    def on_leave(self, *args):
        if hasattr(self, "_event") and self._event:
            self._event.cancel()
        return super().on_leave(*args)

    def update_timer(self, dt):
        remaining = self.target_time - time.time()
        if remaining <= 0:
            self.timer_label = "0"
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
            if self.manager:
                self.manager.current = "workout_active"
        else:
            self.timer_label = str(math.ceil(remaining))

    def adjust_timer(self, seconds):
        self.target_time += seconds
        if self.target_time <= time.time():
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
            if self.manager:
                self.manager.current = "workout_active"


class PresetsScreen(MDScreen):
    """Screen to select a workout preset."""

    selected_preset = StringProperty("")
    selected_item = ObjectProperty(None, allownone=True)

    def select_preset(self, name, item):
        """Select a preset from WORKOUT_PRESETS and highlight item."""
        if self.selected_item:
            self.selected_item.md_bg_color = (0, 0, 0, 0)
        self.selected_item = item
        self.selected_item.md_bg_color = MDApp.get_running_app().theme_cls.primary_light
        if name in WORKOUT_PRESETS:
            self.selected_preset = name

    def confirm_selection(self):
        if self.selected_preset and self.manager:
            detail = self.manager.get_screen("preset_detail")
            detail.preset_name = self.selected_preset
            self.manager.current = "preset_detail"


class PresetDetailScreen(MDScreen):
    preset_name = StringProperty("")


class ExerciseLibraryScreen(MDScreen):
    previous_screen = StringProperty("home")

    def go_back(self):
        if self.manager:
            self.manager.current = self.previous_screen


class WorkoutApp(MDApp):
    def build(self):
        return Builder.load_file("main.kv")


if __name__ == "__main__":
    WorkoutApp().run()
