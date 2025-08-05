from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
from kivymd.app import MDApp
import time


class WorkoutActiveScreen(MDScreen):
    """Screen that shows an active workout with a stopwatch."""

    elapsed = NumericProperty(0.0)
    start_time = NumericProperty(0.0)
    formatted_time = StringProperty("00:00")
    exercise_name = StringProperty("")
    _event = None

    def start_timer(self, *args):
        """Start or resume the stopwatch."""
        self.stop_timer()
        session = MDApp.get_running_app().workout_session
        if session and getattr(session, "resume_from_last_start", False):
            self.start_time = session.current_set_start_time
            session.resume_from_last_start = False
        else:
            self.start_time = time.time()
            if session:
                session.current_set_start_time = self.start_time
        self._event = Clock.schedule_interval(self._update_elapsed, 0.1)
        self._update_elapsed(0)

    def on_pre_enter(self, *args):
        session = MDApp.get_running_app().workout_session
        if session:
            self.exercise_name = session.next_exercise_display()
        self.start_timer()
        return super().on_pre_enter(*args)

    def stop_timer(self, *args):
        """Stop updating the stopwatch without clearing the start time."""
        if self._event:
            self._event.cancel()
            self._event = None

    def _update_elapsed(self, dt):
        self.elapsed = time.time() - self.start_time
        minutes, seconds = divmod(int(self.elapsed), 60)
        self.formatted_time = f"{minutes:02d}:{seconds:02d}"
