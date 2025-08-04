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
    prev_optional_list = ObjectProperty(None)
    next_optional_list = ObjectProperty(None)
    current_tab = StringProperty("previous")
    header_text = StringProperty("")
    exercise_name = StringProperty("")

    def _parent_scroll(self, widget):
        from kivy.uix.scrollview import ScrollView

        parent = widget.parent
        while parent:
            if isinstance(parent, ScrollView):
                return parent
            parent = parent.parent
        return None

    def on_slider_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            scroll = self._parent_scroll(instance)
            if scroll:
                scroll.do_scroll_y = False
        return False

    def on_slider_touch_up(self, instance, touch):
        scroll = self._parent_scroll(instance)
        if scroll:
            scroll.do_scroll_y = True
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
        if app and getattr(app, "record_pre_set", False):
            self.current_tab = "next"
        self.update_header()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        # Reset flag so leaving without saving doesn't advance sets later
        app = MDApp.get_running_app()
        if hasattr(app, "record_new_set"):
            app.record_new_set = False
        if hasattr(app, "record_pre_set"):
            app.record_pre_set = False
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
        prev_values = {}
        next_values = {}
        upcoming_ex = ""
        if app.workout_session:
            session = app.workout_session
            curr_ex = session.next_exercise_name()
            self.exercise_name = curr_ex
            all_metrics = get_metrics_for_exercise(
                curr_ex, preset_name=session.preset_name
            )
            prev_metrics = [m for m in all_metrics if m.get("input_timing") == "post_set"]
            prev_values = {}
            if session.current_exercise < len(session.exercises):
                ex = session.exercises[session.current_exercise]
                if session.current_set < len(ex.get("results", [])):
                    prev_values = ex["results"][session.current_set]

            upcoming_ex = session.upcoming_exercise_name()
            next_all = (
                get_metrics_for_exercise(
                    upcoming_ex, preset_name=session.preset_name
                )
                if upcoming_ex
                else []
            )
            next_metrics = [m for m in next_all if m.get("input_timing") == "pre_set"]
            next_values = session.pending_pre_set_metrics.copy()

            if getattr(app, "record_pre_set", False) and not prev_values:
                prev_metrics = []
        elif metrics is not None:
            prev_metrics = metrics
            next_metrics = metrics
            self.exercise_name = ""

        if not self.prev_metric_list or not self.next_metric_list:
            return
        self.prev_metric_list.clear_widgets()
        self.next_metric_list.clear_widgets()
        if self.prev_optional_list:
            self.prev_optional_list.clear_widgets()
        if self.next_optional_list:
            self.next_optional_list.clear_widgets()

        prev_required = [m for m in prev_metrics if m.get("is_required")]
        prev_optional = [m for m in prev_metrics if not m.get("is_required")]
        next_required = [m for m in next_metrics if m.get("is_required")]
        next_optional = [m for m in next_metrics if not m.get("is_required")]

        for m in prev_required:
            self.prev_metric_list.add_widget(
                self._create_row(m, prev_values.get(m.get("name")))
            )
        for m in next_required:
            self.next_metric_list.add_widget(
                self._create_row(m, next_values.get(m.get("name")))
            )
        for m in prev_optional:
            self.prev_optional_list.add_widget(
                self._create_row(m, prev_values.get(m.get("name")))
            )
        for m in next_optional:
            self.next_optional_list.add_widget(
                self._create_row(m, next_values.get(m.get("name")))
            )

        if prev_values:
            self.prev_optional_list.add_widget(
                self._create_row({"name": "Notes", "type": "str"}, prev_values.get("Notes"))
            )
        if upcoming_ex:
            self.next_optional_list.add_widget(
                self._create_row({"name": "Notes", "type": "str"}, next_values.get("Notes"))
            )

        self.update_header()
        self.highlight_missing_metrics()

    def _set_tab_color(self, tab, red: bool):
        if not tab:
            return
        tab.tab_label.theme_text_color = "Custom"
        tab.tab_label.text_color = (1, 0, 0, 1) if red else (1, 1, 1, 1)

    def highlight_missing_metrics(self):
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        missing_prev = False
        missing_next = False
        if session:
            missing_prev = not session.has_required_post_set_metrics()
            missing_next = not session.has_required_pre_set_metrics()
        ids = self.ids
        self._set_tab_color(ids.get("prev_tab"), missing_prev)
        self._set_tab_color(ids.get("prev_required_tab"), missing_prev)
        self._set_tab_color(ids.get("next_tab"), missing_next)
        self._set_tab_color(ids.get("next_required_tab"), missing_next)

    def _create_row(self, metric, value=None):
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
            widget = MDSlider(min=0, max=1, value=value or 0)
            widget.bind(
                on_touch_down=self.on_slider_touch_down,
                on_touch_up=self.on_slider_touch_up,
            )
        elif mtype == "enum":
            widget = Spinner(
                text=str(value) if value not in (None, "") else (values[0] if values else ""),
                values=values,
            )
        else:  # manual_text
            input_filter = None
            if mtype == "int":
                input_filter = "int"
            elif mtype == "float":
                input_filter = "float"
            multiline = name == "Notes"
            widget = MDTextField(
                multiline=multiline,
                input_filter=input_filter,
                text=str(value) if value not in (None, "") else "",
            )

        row.input_widget = widget
        row.add_widget(widget)
        return row

    def _collect_metrics(self, widget_list):
        data = {}
        if not widget_list:
            return data
        for row in reversed(widget_list.children):
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
            data[name] = value
        return data

    def save_metrics(self):
        prev_metrics = self._collect_metrics(self.prev_metric_list)
        prev_metrics.update(self._collect_metrics(self.prev_optional_list))
        next_metrics = self._collect_metrics(self.next_metric_list)
        next_metrics.update(self._collect_metrics(self.next_optional_list))
        app = MDApp.get_running_app()
        if app.workout_session and getattr(app, "record_pre_set", False):
            app.workout_session.set_pre_set_metrics(next_metrics)
            app.record_pre_set = False
            if self.manager:
                self.manager.current = "rest"
            return
        metrics = prev_metrics
        if app.workout_session and getattr(app, "record_new_set", False):
            finished = app.workout_session.record_metrics(metrics)
            app.record_new_set = False
            if next_metrics:
                app.workout_session.set_pre_set_metrics(next_metrics)
            if finished and self.manager:
                self.manager.current = "workout_summary"
            elif self.manager:
                self.manager.current = "rest"
        elif self.manager:
            self.manager.current = "rest"

