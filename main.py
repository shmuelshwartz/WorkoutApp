from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.properties import NumericProperty
from kivymd.uix.screen import MDScreen


class WorkoutActiveScreen(MDScreen):
    """Screen that shows an active workout with a stopwatch."""

    elapsed = NumericProperty(0)
    _event = None

    def start_timer(self, *args):
        """Start the stopwatch from zero."""
        self.elapsed = 0
        self.stop_timer()
        self._event = Clock.schedule_interval(self._increment, 1)

    def stop_timer(self, *args):
        """Stop the stopwatch if it is running."""
        if self._event:
            self._event.cancel()
            self._event = None

    def _increment(self, dt):
        self.elapsed += 1

    def format_time(self):
        minutes, seconds = divmod(int(self.elapsed), 60)
        return f"{minutes:02d}:{seconds:02d}"


class WorkoutApp(MDApp):
    def build(self):
        return Builder.load_file("main.kv")


if __name__ == "__main__":
    WorkoutApp().run()
