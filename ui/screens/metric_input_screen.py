from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivymd.uix.label import MDLabel
from core import get_metrics_for_exercise


class MetricInputScreen(MDScreen):
    """Screen for entering workout metrics."""

    prev_metric_list = ObjectProperty(None)
    next_metric_list = ObjectProperty(None)
    metrics_scroll = ObjectProperty(None)
    current_tab = StringProperty("previous")
    header_text = StringProperty("")
    exercise_name = StringProperty("")

    def on_slider_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos) and self.metrics_scroll:
            self.metrics_scroll.do_scroll_y = False
        return False

    def on_slider_touch_up(self, instance, touch):
        if self.metrics_scroll:
            self.metrics_scroll.do_scroll_y = True
        return False

    def switch_tab(self, tab: str):
        """Switch between previous and next metric input views."""
        if tab in ("previous", "next"):
            self.current_tab = tab
            self.update_header()

    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        if app and app.workout_session:
            self.exercise_name = app.workout_session.next_exercise_name()
        else:
            self.exercise_name = ""
        self.update_header()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        # Reset flag so leaving without saving doesn't advance sets later
        app = MDApp.get_running_app()
        if hasattr(app, "record_new_set"):
            app.record_new_set = False
        return super().on_leave(*args)

    def update_header(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if not session:
            self.header_text = ""
            return

        if self.current_tab == "previous":
            if session.current_exercise >= len(session.exercises):
                self.header_text = "Previous Set Metrics"
                return
            ex = session.exercises[session.current_exercise]
            set_number = session.current_set + 1
            self.header_text = f"Previous Set Metrics {ex['name']} Set {set_number}"
        else:
            # upcoming set info
            ex_idx = session.current_exercise
            set_idx = session.current_set + 1
            if ex_idx < len(session.exercises):
                if set_idx >= session.exercises[ex_idx]["sets"]:
                    ex_idx += 1
                    set_idx = 0
            if ex_idx < len(session.exercises):
                ex = session.exercises[ex_idx]
                self.header_text = f"Next Set Metrics {ex['name']} Set {set_idx + 1}"
            else:
                self.header_text = "Next Set Metrics"

    def populate_metrics(self, metrics=None):
        """Populate metric lists for previous and next sets."""
        app = MDApp.get_running_app()
        prev_metrics = []
        next_metrics = []
        if app.workout_session:
            curr_ex = app.workout_session.next_exercise_name()
            self.exercise_name = curr_ex
            all_metrics = get_metrics_for_exercise(
                curr_ex, preset_name=app.workout_session.preset_name
            )
            prev_metrics = [m for m in all_metrics if m.get("input_timing") == "post_set"]

            upcoming_ex = app.workout_session.upcoming_exercise_name()
            next_all = (
                get_metrics_for_exercise(
                    upcoming_ex, preset_name=app.workout_session.preset_name
                )
                if upcoming_ex
                else []
            )
            next_metrics = [m for m in next_all if m.get("input_timing") == "pre_set"]
        elif metrics is not None:
            prev_metrics = metrics
            next_metrics = metrics
            self.exercise_name = ""

        if not self.prev_metric_list or not self.next_metric_list:
            return
        self.prev_metric_list.clear_widgets()
        self.next_metric_list.clear_widgets()

        def _create_row(metric):
            if isinstance(metric, str):
                name = metric
                mtype = "str"
                values = []
            else:
                name = metric.get("name")
                mtype = metric.get("type", "str")
                values = metric.get("values", [])

            row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
            row.metric_name = name
            row.type = mtype
            row.add_widget(MDLabel(text=name, size_hint_x=0.4))

            if mtype == "slider":
                widget = MDSlider(min=0, max=1, value=0)
                widget.bind(
                    on_touch_down=self.on_slider_touch_down,
                    on_touch_up=self.on_slider_touch_up,
                )
            elif mtype == "enum":
                widget = Spinner(text=values[0] if values else "", values=values)
            else:  # manual_text
                input_filter = None
                if mtype == "int":
                    input_filter = "int"
                elif mtype == "float":
                    input_filter = "float"
                widget = MDTextField(multiline=False, input_filter=input_filter)

            row.input_widget = widget
            row.add_widget(widget)
            return row

        for m in prev_metrics:
            self.prev_metric_list.add_widget(_create_row(m))
        for m in next_metrics:
            self.next_metric_list.add_widget(_create_row(m))

        self.update_header()

    def save_metrics(self):
        metrics = {}
        for row in reversed(self.prev_metric_list.children):
            name = getattr(row, "metric_name", "")
            widget = getattr(row, "input_widget", None)
            mtype = getattr(row, "type", "str")
            if widget is None:
                continue
            value = None
            if isinstance(widget, MDTextField):
                value = widget.text
            elif isinstance(widget, MDSlider):
                value = widget.value
            elif isinstance(widget, Spinner):
                value = widget.text
            if value in (None, ""):
                value = 0 if mtype in ("int", "float", "slider") else ""
            if mtype == "int":
                try:
                    value = int(value)
                except ValueError:
                    value = 0
            elif mtype in ("float", "slider"):
                try:
                    value = float(value)
                except ValueError:
                    value = 0.0
            metrics[name] = value
        app = MDApp.get_running_app()
        if app.workout_session and getattr(app, "record_new_set", False):
            finished = app.workout_session.record_metrics(metrics)
            app.record_new_set = False
            if finished and self.manager:
                self.manager.current = "workout_summary"
            elif self.manager:
                self.manager.current = "rest"
        elif self.manager:
            self.manager.current = "rest"

