from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.properties import (
    ObjectProperty,
    StringProperty,
    BooleanProperty,
    ListProperty,
)
from kivy.clock import Clock
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

    def __init__(self, data_provider=None, router=None, test_mode=False, **kwargs):
        super().__init__(**kwargs)
        self.test_mode = test_mode
        self.router = router
        self.data_provider = data_provider
        if self.test_mode and self.data_provider is None:
            try:
                from ui.stubs.metric_input_stub import StubDataProvider

                self.data_provider = StubDataProvider()
            except Exception:  # pragma: no cover - stubs optional
                self.data_provider = None
        self.session = None
        self.exercise_idx = 0
        self.set_idx = 0
        self._left_taps = 0
        self._right_taps = 0
        self._left_event = None
        self._right_event = None
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
    def _get_session(self):
        if self.data_provider:
            try:
                return self.data_provider.get_session()
            except AttributeError:
                return None
        app = MDApp.get_running_app()
        return getattr(app, "workout_session", None)

    def on_pre_enter(self, *args):
        self.session = self._get_session()
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

    def register_left_tap(self):
        self._left_taps += 1
        if self._left_event:
            self._left_event.cancel()
        self._left_event = Clock.schedule_once(self._process_left_tap, 0.3)

    def _process_left_tap(self, _dt):
        count = self._left_taps
        self._left_taps = 0
        self._left_event = None
        if count >= 3:
            self.navigate_left_triple()
        elif count == 2:
            self.navigate_left_double()
        else:
            self.navigate_left()

    def register_right_tap(self):
        self._right_taps += 1
        if self._right_event:
            self._right_event.cancel()
        self._right_event = Clock.schedule_once(self._process_right_tap, 0.3)

    def _process_right_tap(self, _dt):
        count = self._right_taps
        self._right_taps = 0
        self._right_event = None
        if count >= 3:
            self.navigate_right_triple()
        elif count == 2:
            self.navigate_right_double()
        else:
            self.navigate_right()

    def navigate_left(self):
        if not self.can_nav_left:
            return
        if self.set_idx > 0:
            self.set_idx -= 1
        else:
            self.exercise_idx -= 1
            self.set_idx = self.session.exercises[self.exercise_idx]["sets"] - 1
        self.update_display()

    def navigate_left_double(self):
        if self.set_idx > 0:
            self.set_idx = 0
        elif self.exercise_idx > 0:
            self.exercise_idx -= 1
            self.set_idx = 0
        self.update_display()

    def navigate_left_triple(self):
        if not self.session:
            return
        sections = getattr(self.session, "section_starts", [])
        if not sections:
            return
        current_section = self.session.exercise_sections[self.exercise_idx]
        first_idx = sections[current_section]
        if self.exercise_idx != first_idx or self.set_idx != 0:
            self.exercise_idx = first_idx
            self.set_idx = 0
        elif current_section > 0:
            self.exercise_idx = sections[current_section - 1]
            self.set_idx = 0
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

    def navigate_right_double(self):
        if self.exercise_idx < len(self.session.exercises) - 1:
            self.exercise_idx += 1
            self.set_idx = 0
            self.update_display()

    def navigate_right_triple(self):
        if not self.session:
            return
        sections = getattr(self.session, "section_starts", [])
        if not sections:
            return
        current_section = self.session.exercise_sections[self.exercise_idx]
        next_section = current_section + 1
        if next_section < len(sections):
            self.exercise_idx = sections[next_section]
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
        else:
            values = self.session.pending_pre_set_metrics.get(
                (self.exercise_idx, self.set_idx), {}
            )
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
            widget.size_hint_x = 0.4
            value_label = MDLabel(
                text=f"{widget.value:.2f}", size_hint_x=0.2
            )
            widget.bind(
                value=lambda _w, val: setattr(value_label, "text", f"{val:.2f}"),
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
        if mtype == "slider":
            row.add_widget(value_label)
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
        if getattr(app, "record_pre_set", False) and not getattr(
            app, "record_new_set", False
        ):
            session.set_pre_set_metrics(metrics, self.exercise_idx, self.set_idx)
            app.record_pre_set = False
            if getattr(self, "manager", None):
                self.manager.current = "rest"
            return

        orig_ex = session.current_exercise
        orig_set = session.current_set

        sel_ex = self.exercise_idx
        sel_set = self.set_idx

        finished = False
        if getattr(app, "record_new_set", False):
            post_metrics = metrics if (sel_ex == orig_ex and sel_set == orig_set) else {}
            finished = session.record_metrics(orig_ex, orig_set, post_metrics)
            if (sel_ex, sel_set) != (orig_ex, orig_set):
                session.set_pre_set_metrics(metrics, sel_ex, sel_set)
        else:
            finished = session.record_metrics(sel_ex, sel_set, metrics)

        app.record_new_set = False
        app.record_pre_set = False

        self.exercise_idx = session.current_exercise
        self.set_idx = session.current_set
        self.update_display()
        if finished:
            if self.router:
                self.router.navigate("workout_summary")
            elif getattr(self, "manager", None):
                self.manager.current = "workout_summary"
        else:
            if self.router:
                self.router.navigate("rest")
            elif getattr(self, "manager", None):
                self.manager.current = "rest"


if __name__ == "__main__":  # pragma: no cover - manual visual test
    choice = (
        input("Type 1 for single-screen test\nType 2 for flow test\n").strip()
        or "1"
    )
    if choice == "2":
        from ui.testing.runners.flow_runner import run

        run("metric_input_screen")
    else:
        from kivymd.app import MDApp
        from ui.routers import SingleRouter
        from ui.stubs.metric_input_stub import StubDataProvider

        class _TestApp(MDApp):
            def build(self):
                provider = StubDataProvider()
                return MetricInputScreen(
                    data_provider=provider, router=SingleRouter(), test_mode=True
                )

        _TestApp().run()
