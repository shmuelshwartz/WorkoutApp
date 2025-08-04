from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.clock import Clock
from kivy.properties import NumericProperty, StringProperty, BooleanProperty, ListProperty
import time
import math
from core import DEFAULT_REST_DURATION, get_exercise_details


class RestScreen(MDScreen):
    """Screen shown between exercises with a rest timer."""

    timer_label = StringProperty("00:20")
    target_time = NumericProperty(0)
    next_exercise_name = StringProperty("")
    next_exercise_desc = StringProperty("")
    next_set_info = StringProperty("")
    rest_time_info = StringProperty("")
    is_ready = BooleanProperty(False)
    timer_color = ListProperty([1, 0, 0, 1])

    def on_enter(self, *args):
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
        else:
            self.target_time = time.time() + DEFAULT_REST_DURATION
            self.next_exercise_name = ""
            self.next_set_info = ""
            self.rest_time_info = ""
            self.next_exercise_desc = ""
        self.is_ready = False
        self.timer_color = (1, 0, 0, 1)
        self.update_timer(0)
        self._event = Clock.schedule_interval(self.update_timer, 0.1)
        self.update_record_button_color()
        return super().on_enter(*args)

    def on_leave(self, *args):
        if hasattr(self, "_event") and self._event:
            self._event.cancel()
        return super().on_leave(*args)

    def toggle_ready(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if session and not self.is_ready:
            if not (
                session.has_required_pre_set_metrics()
                and session.has_required_post_set_metrics()
            ):
                self.update_record_button_color()
                return
        self.is_ready = not self.is_ready
        self.timer_color = (0, 1, 0, 1) if self.is_ready else (1, 0, 0, 1)
        if self.is_ready and self.target_time <= time.time():
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
                self._event = None
            if self.manager:
                self.manager.current = "workout_active"

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
        btn.text_color = (1, 0, 0, 1) if missing else (1, 1, 1, 1)

    def on_touch_down(self, touch):
        if self.ids.timer_label.collide_point(*touch.pos):
            self.toggle_ready()
            return True
        return super().on_touch_down(touch)

    def update_timer(self, dt):
        remaining = self.target_time - time.time()
        if remaining <= 0:
            self.timer_label = "00:00"
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
                self._event = None
            if self.is_ready and self.manager:
                self.manager.current = "workout_active"
        else:
            total_seconds = math.ceil(remaining)
            minutes, seconds = divmod(total_seconds, 60)
            self.timer_label = f"{minutes:02d}:{seconds:02d}"

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
        if self.target_time <= time.time():
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
                self._event = None
            self.update_timer(0)
            if self.is_ready and self.manager:
                self.manager.current = "workout_active"
        else:
            if not hasattr(self, "_event") or not self._event:
                self._event = Clock.schedule_interval(self.update_timer, 0.1)
            self.update_timer(0)
