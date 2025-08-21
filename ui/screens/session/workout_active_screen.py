from kivymd.uix.screen import MDScreen
from kivy.properties import NumericProperty, StringProperty, ObjectProperty
from kivy.clock import Clock
from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivy.core.text import LabelBase
from kivymd.font_definitions import fonts_path
from pathlib import Path
import time

# Only register the custom font if it exists to avoid unnecessary errors and memory usage
DIGITAL_FONT = "RobotoMonoDigital"
_font_path = Path(fonts_path) / "RobotoMono-Regular.ttf"
if _font_path.exists():
    LabelBase.register(name=DIGITAL_FONT, fn_regular=str(_font_path))
else:
    DIGITAL_FONT = "Roboto"


class WorkoutActiveScreen(MDScreen):
    """Screen that shows an active workout with a stopwatch.

    A small ``TempoVisualizer`` renders the current exercise tempo so the
    user can follow along without relying solely on audio cues.
    """

    elapsed = NumericProperty(0.0)
    start_time = NumericProperty(0.0)
    formatted_time = StringProperty("00:00")
    exercise_name = StringProperty("")
    digital_font = StringProperty(DIGITAL_FONT)
    tempo_bar = ObjectProperty(None)
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
        if session:
            session.save_recovery_state()
        self._event = Clock.schedule_interval(self._update_elapsed, 0.1)
        self._update_elapsed(0)

    def on_pre_enter(self, *args):
        """Prepare the workout display when entering the screen."""
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        tempo = None
        if session and session.current_exercise < len(session.exercises):
            self.exercise_name = session.next_exercise_display()
            tempo = session.tempo_for_set(session.current_exercise, session.current_set)
        if not self._event:
            self.start_timer()
            if app and hasattr(app, "sound"):
                if tempo:
                    app.sound.start_tempo(tempo, skip_start=True, start_time=self.start_time)
                else:
                    app.sound.start_ticks()
        # Update tempo visualisation
        if self.tempo_bar:
            if tempo:
                self.tempo_bar.tempo = tempo
                self.tempo_bar.start(self.start_time)
                self.tempo_bar.opacity = 1
            else:
                self.tempo_bar.stop()
                self.tempo_bar.opacity = 0
        return super().on_pre_enter(*args)

    def stop_timer(self, *args):
        """Stop updating the stopwatch without clearing the start time."""
        if self._event:
            self._event.cancel()
            self._event = None

    def on_leave(self, *args):
        """Stop timers only when exiting to a non-settings screen."""
        next_screen = self.manager.current if self.manager else None
        if next_screen != "settings":
            app = MDApp.get_running_app()
            if app and hasattr(app, "sound"):
                app.sound.stop()
            self.stop_timer()
            if self.tempo_bar:
                self.tempo_bar.stop()
        return super().on_leave(*args)

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
