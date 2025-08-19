try:  # pragma: no cover - fallback for environments without Kivy
    from kivymd.app import MDApp
    from kivymd.uix.screen import MDScreen
    from kivymd.uix.dialog import MDDialog
    from kivymd.uix.button import MDFlatButton, MDRaisedButton
    from kivymd.toast import toast
    from kivy.clock import Clock
    from kivy.properties import (
        NumericProperty,
        StringProperty,
        BooleanProperty,
        ListProperty,
    )
except Exception:  # pragma: no cover - simple stubs
    MDApp = object
    MDScreen = object

    class MDDialog:  # minimal placeholder
        def __init__(self, *a, **k):
            pass

        def open(self, *a, **k):
            pass

        def dismiss(self, *a, **k):
            pass

    class MDFlatButton:  # minimal placeholder
        def __init__(self, *a, **k):
            pass

    class MDRaisedButton(MDFlatButton):
        pass

    class _Clock:
        def schedule_interval(self, *a, **k):
            pass

        def unschedule(self, *a, **k):
            pass

    Clock = _Clock()

    def NumericProperty(value=None):
        return value

    def StringProperty(value=None):
        return value

    def BooleanProperty(value=False):
        return value

    def ListProperty(value=None):
        return value

    def toast(*a, **k):
        pass

import time
import math
from core import DEFAULT_REST_DURATION
from backend.exercises import get_exercise_details


class RestScreen(MDScreen):
    """Screen shown between exercises with a rest timer."""

    timer_label = StringProperty("00:20")
    session_time_label = StringProperty("00:00")
    target_time = NumericProperty(0)
    session_start_time = NumericProperty(0)
    next_exercise_name = StringProperty("")
    next_exercise_desc = StringProperty("")
    next_set_info = StringProperty("")
    rest_time_info = StringProperty("")
    is_ready = BooleanProperty(False)
    timer_color = ListProperty([1, 0, 0, 1])
    undo_disabled = BooleanProperty(True)

    def on_pre_enter(self, *args):
        session = MDApp.get_running_app().workout_session
        if session:
            ex_name = session.next_exercise_name()
            self.next_exercise_name = ex_name
            self.next_set_info = (
                f"set {session.current_set + 1} of {session.exercises[session.current_exercise]['sets']}"
                if session.current_exercise < len(session.exercises)
                else ""
            )
            self.rest_time_info = f"{session.rest_duration} seconds rest time"
            details = get_exercise_details(ex_name, db_path=session.db_path)
            self.next_exercise_desc = details.get("description", "") if details else ""
            self.target_time = session.rest_target_time
            self.undo_disabled = (
                session.current_exercise == 0
                and session.current_set == 0
                and not session.exercises[0]["results"]
            )
            self.session_start_time = session.start_time
        else:
            now = time.time()
            self.target_time = now + DEFAULT_REST_DURATION
            self.next_exercise_name = ""
            self.next_set_info = ""
            self.rest_time_info = ""
            self.next_exercise_desc = ""
            self.undo_disabled = True
            self.session_start_time = now
        self.is_ready = False
        self.timer_color = (1, 0, 0, 1)
        self.update_timer(0)
        self._ensure_clock_event()
        self.update_record_button_color()
        return super().on_pre_enter(*args)

    def on_enter(self, *args):
        return super().on_enter(*args)

    def on_leave(self, *args):
        if hasattr(self, "_event") and self._event:
            self._event.cancel()
            self._event = None
        return super().on_leave(*args)

    def _ensure_clock_event(self):
        """Ensure the timer update event is running."""
        if not getattr(getattr(self, "_event", None), "is_triggered", False):
            self._event = Clock.schedule_interval(self.update_timer, 0.1)

    def toggle_ready(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        # Allow toggling ready state regardless of whether required metrics
        # have been recorded. Previously, missing required metrics prevented
        # the user from proceeding. Removing the guard ensures the "ready"
        # button always works.
        self.is_ready = not self.is_ready
        self.timer_color = (0, 1, 0, 1) if self.is_ready else (1, 0, 0, 1)
        if self.is_ready and self.target_time <= time.time() and self.manager:
            self.manager.current = "workout_active"

    def unready(self):
        """Reset the ready state without toggling."""
        if self.is_ready:
            self.is_ready = False
            self.timer_color = (1, 0, 0, 1)

    def update_record_button_color(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        btn = self.ids.get("record_btn")
        if not btn:
            return
        missing = False
        if session and (
            not session.has_required_pre_set_metrics()
            or not session.has_required_post_set_metrics()
        ):
            missing = True
        btn.theme_text_color = "Custom"
        btn.text_color = (1, 0, 0, 1) if missing else (0, 0, 0, 1)

    def open_metric_input(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        app.record_new_set = False
        app.record_pre_set = True
        if session and not session.has_required_post_set_metrics():
            app.record_pre_set = False
            app.record_new_set = True
        if app.root:
            app.root.current = "metric_input"

    def show_undo_confirmation(self):
        if self.undo_disabled:
            return
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        was_skip = session.last_action_was_skip() if session else False
        text = (
            "Undo skipped exercise?"
            if was_skip
            else "Are you sure you want to undo the last set and resume it?"
        )
        if not hasattr(self, "_undo_dialog") or not self._undo_dialog:
            self._undo_dialog = MDDialog(
                text=text,
                buttons=[
                    MDFlatButton(text="Cancel", on_release=lambda *_: self._undo_dialog.dismiss()),
                    MDFlatButton(text="Confirm", on_release=self._perform_undo),
                ],
            )
        else:
            self._undo_dialog.text = text
        self._undo_dialog.open()

    def _perform_undo(self, *args):
        if hasattr(self, "_undo_dialog") and self._undo_dialog:
            self._undo_dialog.dismiss()
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if session:
            was_skip = session.last_action_was_skip()
            if session.undo_last_set():
                if was_skip:
                    self.next_exercise_name = session.next_exercise_name()
                    self.next_set_info = (
                        f"set {session.current_set + 1} of {session.exercises[session.current_exercise]['sets']}"
                        if session.current_exercise < len(session.exercises)
                        else ""
                    )
                    self.rest_time_info = f"{session.rest_duration} seconds rest time"
                    details = get_exercise_details(
                        self.next_exercise_name, db_path=session.db_path
                    )
                    self.next_exercise_desc = details.get("description", "") if details else ""
                    self.target_time = session.rest_target_time
                    self.undo_disabled = (
                        session.current_exercise == 0
                        and session.current_set == 0
                        and not session.exercises[0]["results"]
                    )
                    self.update_timer(0)
                    self._ensure_clock_event()
                elif self.manager:
                    self.manager.current = "workout_active"

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
            self.next_exercise_name = session.next_exercise_name()
            self.next_set_info = (
                f"set {session.current_set + 1} of {session.exercises[session.current_exercise]['sets']}"
                if session.current_exercise < len(session.exercises)
                else ""
            )
            self.rest_time_info = f"{session.rest_duration} seconds rest time"
            details = get_exercise_details(
                self.next_exercise_name, db_path=session.db_path
            )
            self.next_exercise_desc = details.get("description", "") if details else ""
            self.target_time = session.rest_target_time
            self.undo_disabled = (
                session.current_exercise == 0
                and session.current_set == 0
                and not session.exercises[0]["results"]
            )
            self.update_timer(0)
            self._ensure_clock_event()
        else:
            toast("No next exercise")
                
    def confirm_finish(self):
        dialog = None

        def do_finish(*_args):
            app = MDApp.get_running_app()
            if app:
                session = getattr(app, "workout_session", None)
                if session and session.end_time is None:
                    session.end_time = time.time()
            if app and app.root:
                app.root.current = "workout_summary"
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Finish Workout?",
            text="Are you sure you want to finish this workout?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *_: dialog.dismiss()),
                MDRaisedButton(text="Finish", on_release=do_finish),
            ],
        )
        dialog.open()

    def on_touch_down(self, touch):
        if self.ids.timer_label.collide_point(*touch.pos):
            self.toggle_ready()
            return True
        return super().on_touch_down(touch)

    def update_timer(self, dt):
        remaining = self.target_time - time.time()
        if remaining <= 0:
            self.timer_label = "00:00"
            if self.is_ready and self.manager:
                self.manager.current = "workout_active"
        else:
            total_seconds = math.ceil(remaining)
            minutes, seconds = divmod(total_seconds, 60)
            self.timer_label = f"{minutes:02d}:{seconds:02d}"

        elapsed = int(time.time() - (self.session_start_time or time.time()))
        minutes, seconds = divmod(elapsed, 60)
        self.session_time_label = f"{minutes:02d}:{seconds:02d}"

    def _adjust_step(self) -> int:
        """Return adjustment step based on remaining rest time."""
        remaining = max(0, self.target_time - time.time())
        if remaining < 60:
            return 10
        if remaining < 300:
            return 30
        return 60

    def adjust_timer_by_direction(self, direction: int) -> None:
        """Adjust timer forward/backward based on remaining time."""
        self.adjust_timer(direction * self._adjust_step())

    def adjust_timer(self, seconds):
        session = MDApp.get_running_app().workout_session
        if session:
            session.adjust_rest_timer(seconds)
            self.target_time = session.rest_target_time
        else:
            now = time.time()
            if self.target_time <= now:
                self.target_time = now
            self.target_time += seconds
            if self.target_time <= now:
                self.target_time = now
        should_change = (
            self.target_time <= time.time() and self.is_ready and self.manager
        )
        if should_change:
            self.manager.current = "workout_active"
        self.update_timer(0)
        if not should_change:
            self._ensure_clock_event()
