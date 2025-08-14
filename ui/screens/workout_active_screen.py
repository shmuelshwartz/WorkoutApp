from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, StringProperty
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.toast import toast
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

    def show_undo_confirmation(self):
        if not hasattr(self, "_undo_dialog") or not self._undo_dialog:
            self._undo_dialog = MDDialog(
                text="Are you sure you want to undo and return to rest?",
                buttons=[
                    MDFlatButton(text="Cancel", on_release=lambda *_: self._undo_dialog.dismiss()),
                    MDFlatButton(text="Confirm", on_release=self._perform_undo),
                ],
            )
        self._undo_dialog.open()

    def _perform_undo(self, *args):
        if hasattr(self, "_undo_dialog") and self._undo_dialog:
            self._undo_dialog.dismiss()
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if session:
            if session.last_action_was_skip():
                session.undo_last_set()
            else:
                session.undo_set_start()
        self.stop_timer()
        if self.manager:
            self.manager.current = "rest"

    def show_skip_confirmation(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if session and session.current_exercise >= len(session.preset_snapshot) - 1:
            toast("No next exercise")
            return
        if not hasattr(self, "_skip_dialog") or not self._skip_dialog:
            self._skip_dialog = MDDialog(
                text="Skip this exercise and move to the next?",
                buttons=[
                    MDFlatButton(text="Cancel", on_release=lambda *_: self._skip_dialog.dismiss()),
                    MDFlatButton(text="Confirm", on_release=self._perform_skip),
                ],
            )
        self._skip_dialog.open()

    def _perform_skip(self, *args):
        if hasattr(self, "_skip_dialog") and self._skip_dialog:
            self._skip_dialog.dismiss()
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if session and session.skip_exercise():
            self.exercise_name = session.next_exercise_display()
            self.start_timer()
        else:
            toast("No next exercise")
