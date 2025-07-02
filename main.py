from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, NumericProperty
from core import WORKOUT_PRESETS
from kivy.clock import Clock
import time


class RestScreen(MDScreen):
    timer_label = StringProperty("20")
    target_time = NumericProperty(0)

    def on_enter(self, *args):
        self.target_time = time.time() + 20
        self.update_timer(0)
        self._event = Clock.schedule_interval(self.update_timer, 1)
        return super().on_enter(*args)

    def on_leave(self, *args):
        if hasattr(self, "_event") and self._event:
            self._event.cancel()
        return super().on_leave(*args)

    def update_timer(self, dt):
        remaining = int(self.target_time - time.time())
        if remaining <= 0:
            self.timer_label = "0"
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
            if self.manager:
                self.manager.current = "workout_active"
        else:
            self.timer_label = str(remaining)

    def adjust_timer(self, seconds):
        self.target_time += seconds
        if self.target_time - time.time() <= 0:
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
            if self.manager:
                self.manager.current = "workout_active"


class PresetsScreen(MDScreen):
    """Screen to select a workout preset."""

    selected_preset = StringProperty("")

    def select_preset(self, name):
        """Select a preset from WORKOUT_PRESETS."""
        if name in WORKOUT_PRESETS:
            self.selected_preset = name




class WorkoutApp(MDApp):
    def build(self):
        return Builder.load_file("main.kv")


if __name__ == "__main__":
    WorkoutApp().run()
