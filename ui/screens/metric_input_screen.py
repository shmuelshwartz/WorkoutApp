from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.properties import (
    ObjectProperty,
    StringProperty,
    BooleanProperty,
    ListProperty,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDCheckbox


class MetricInputScreen(MDScreen):
    """Screen for entering workout metrics with navigation and filtering."""

    metrics_list = ObjectProperty(None)
    label_text = StringProperty("")
    can_nav_left = BooleanProperty(False)
    can_nav_right = BooleanProperty(False)

    show_required = BooleanProperty(True)
    show_additional = BooleanProperty(False)
    show_pre = BooleanProperty(True)
    show_post = BooleanProperty(True)

    required_color = ListProperty([0, 1, 0, 1])
    additional_color = ListProperty([0, 0, 0, 1])
    pre_color = ListProperty([0, 1, 0, 1])
    post_color = ListProperty([0, 1, 0, 1])

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = None
        self.exercise_idx = 0
        self.set_idx = 0
        # Explicit defaults for stubbed property behavior in tests
        self.metrics_list = None
        self.label_text = ""
        self.can_nav_left = False
        self.can_nav_right = False
        self.show_required = True
        self.show_additional = False
        self.show_pre = True
        self.show_post = True
        self._update_filter_colors()

    # ------------------------------------------------------------------
    # Navigation
    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        self.session = getattr(app, "workout_session", None)
        if self.session:
            self.exercise_idx = self.session.current_exercise
            self.set_idx = self.session.current_set
        else:
            self.exercise_idx = 0
            self.set_idx = 0
        self.update_display()
        return super().on_pre_enter(*args)

    def update_display(self):
        self._update_navigation_label()
        self.update_metrics()

    def _update_navigation_label(self):
        if not self.session or self.exercise_idx >= len(self.session.exercises):
            self.label_text = ""
            self.can_nav_left = False
            self.can_nav_right = False
            return

        ex = self.session.exercises[self.exercise_idx]
        self.label_text = (
            f"{ex['name']} \u2013 Set {self.set_idx + 1} of {ex['sets']}"
        )

        self.can_nav_left = not (
            self.exercise_idx == 0 and self.set_idx == 0
        )
        last_ex = self.exercise_idx == len(self.session.exercises) - 1
        last_set = self.set_idx == ex["sets"] - 1
        self.can_nav_right = not (last_ex and last_set)

    def navigate_left(self):
        if not self.can_nav_left:
            return
        if self.set_idx > 0:
            self.set_idx -= 1
        else:
            self.exercise_idx -= 1
            self.set_idx = self.session.exercises[self.exercise_idx]["sets"] - 1
        self.update_display()

    def navigate_right(self):
        if not self.can_nav_right:
            return
        ex = self.session.exercises[self.exercise_idx]
        if self.set_idx < ex["sets"] - 1:
            self.set_idx += 1
        else:
            self.exercise_idx += 1
            self.set_idx = 0
        self.update_display()

    # ------------------------------------------------------------------
    # Filter buttons
    def toggle_filter(self, name: str):
        attr = {
            "required": "show_required",
            "additional": "show_additional",
            "pre": "show_pre",
            "post": "show_post",
        }.get(name)
        if attr:
            setattr(self, attr, not getattr(self, attr))
            self._update_filter_colors()
            self.update_metrics()

    def filter_color(self, name: str):
        attr = {
            "required": "show_required",
            "additional": "show_additional",
            "pre": "show_pre",
            "post": "show_post",
        }.get(name)
        return (0, 1, 0, 1) if attr and getattr(self, attr) else (1, 1, 1, 1)

    def _update_filter_colors(self):
        self.required_color = self.filter_color("required")
        self.additional_color = self.filter_color("additional")
        self.pre_color = self.filter_color("pre")
        self.post_color = self.filter_color("post")

    # ------------------------------------------------------------------
    # Metrics
    def _sort_key(self, metric):
        required = 0 if metric.get("is_required") else 2
        timing = 0 if metric.get("input_timing") == "pre_set" else 1
        return required + timing

    def _apply_filters(self, metrics):
        visible = []
        for m in sorted(metrics, key=self._sort_key):
            required = m.get("is_required", False)
            timing = m.get("input_timing", "post_set")
            if required and not self.show_required:
                continue
            if not required and not self.show_additional:
                continue
            if timing == "pre_set" and not self.show_pre:
                continue
            if timing == "post_set" and not self.show_post:
                continue
            visible.append(m)
        return visible

    def update_metrics(self):
        if not self.metrics_list:
            return
        self.metrics_list.clear_widgets()
        if not self.session or self.exercise_idx >= len(self.session.exercises):
            return
        exercise = self.session.exercises[self.exercise_idx]
        metrics = exercise.get("metric_defs", [])
        # Determine any previously recorded values for this set
        values = {}
        results = exercise.get("results", [])
        if self.set_idx < len(results):
            values = results[self.set_idx].get("metrics", {})
        elif (
            getattr(self.session, "current_exercise", None) == self.exercise_idx
            and getattr(self.session, "current_set", None) == self.set_idx
        ):
            # show pending pre-set metrics for the upcoming set
            values = getattr(self.session, "pending_pre_set_metrics", {})
        for metric in self._apply_filters(metrics):
            name = metric.get("name")
            self.metrics_list.add_widget(
                self._create_row(metric, values.get(name))
            )

    # ------------------------------------------------------------------
    # Metric row helpers
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
                text=str(value) if value not in (None, "") else "",
                values=values,
            )
        elif mtype == "bool":
            widget = MDCheckbox(active=bool(value))
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
            elif isinstance(widget, MDCheckbox):
                value = widget.active
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

    # ------------------------------------------------------------------
    def save_metrics(self):
        metrics = self._collect_metrics(self.metrics_list)
        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)
        if not session:
            return

        target_ex = self.exercise_idx
        target_set = self.set_idx

        orig_ex = session.current_exercise
        orig_set = session.current_set
        orig_start = session.current_set_start_time
        orig_pending = session.pending_pre_set_metrics.copy()
        orig_awaiting = session.awaiting_post_set_metrics

        session.current_exercise = target_ex
        session.current_set = target_set
        finished = session.record_metrics(metrics)

        if target_ex == orig_ex and target_set == orig_set:
            self.exercise_idx = session.current_exercise
            self.set_idx = session.current_set
            self.update_display()
            if finished and self.manager:
                self.manager.current = "workout_summary"
            elif self.manager:
                self.manager.current = "rest"
        else:
            session.current_exercise = orig_ex
            session.current_set = orig_set
            session.current_set_start_time = orig_start
            session.pending_pre_set_metrics = orig_pending
            session.awaiting_post_set_metrics = orig_awaiting
            self.exercise_idx = target_ex
            self.set_idx = target_set
            self.update_display()
