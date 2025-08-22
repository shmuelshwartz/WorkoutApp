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
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDFlatButton
from ui.row_controller import GridController


class MetricInputScreen(MDScreen):
    """Screen for entering workout metrics with navigation and filtering."""

    metrics_list = ObjectProperty(None)
    label_text = StringProperty("")
    can_nav_left = BooleanProperty(False)
    can_nav_right = BooleanProperty(False)
    exercise_bar = ObjectProperty(None)
    metric_grid = ObjectProperty(None)
    metric_scroll = ObjectProperty(None)

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

        self._notes_widget = None
        self.exercise_bar = None
        self.metric_grid = None
        self.metric_scroll = None
        self.metric_cells = {}
        # Controller keeping cells aligned within the grid.
        self.grid_controller = GridController()

    # ------------------------------------------------------------------
    # Navigation
    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        self.session = getattr(app, "workout_session", None)
        if self.session:
            self.exercise_idx = self.session.current_exercise
        else:
            self.exercise_idx = 0
        self.populate_exercise_bar()
        self.update_display()
        return super().on_pre_enter(*args)

    def update_display(self):
        self.highlight_current_exercise()
        self.update_metrics()

    def populate_exercise_bar(self):
        if not self.exercise_bar:
            return
        self.exercise_bar.clear_widgets()
        if not self.session:
            return
        for idx, ex in enumerate(self.session.exercises):
            btn = MDFlatButton(
                text=ex.get("name", f"Ex {idx+1}"),
                size_hint=(None, None),
                height=dp(40),
                width=dp(110),
                on_release=lambda _w, i=idx: self.select_exercise(i),
            )
            self.exercise_bar.add_widget(btn)

    def highlight_current_exercise(self):
        if not self.exercise_bar:
            return
        for idx, child in enumerate(reversed(self.exercise_bar.children)):
            color = (0.2, 0.6, 0.86, 1) if idx == self.exercise_idx else (0, 0, 0, 0)
            if hasattr(child, "md_bg_color"):
                child.md_bg_color = color

    def select_exercise(self, index: int):
        self.exercise_idx = index
        self.update_display()

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
        if not self.metric_grid:
            return
        self.metric_grid.clear_widgets()
        self.grid_controller.clear()
        self.metric_cells.clear()
        if not self.session or self.exercise_idx >= len(self.session.exercises):
            return
        exercise = self.session.exercises[self.exercise_idx]
        metrics = [
            m
            for m in exercise.get("metric_defs", [])
            if m.get("name") not in ("Notes",)
        ]
        metrics = self._apply_filters(metrics)
        set_count = exercise.get("sets", 0)
        self.metric_grid.cols = max(1, set_count + 1)

        # Header row: blank cell on the left and set labels to the right.  Any
        # decorative borders have been intentionally omitted so only the
        # widgets themselves are rendered.
        header_placeholder = MDLabel(size_hint=(None, None), height=dp(30))
        self.metric_grid.add_widget(header_placeholder)
        self.grid_controller.register(0, 0, header_placeholder)
        for s in range(set_count):
            lbl = MDLabel(
                text=f"Set {s + 1}",
                size_hint=(None, None),
                width=dp(100),
                height=dp(30),
            )
            # Wider labels keep column widths consistent with enlarged inputs.
            self.metric_grid.add_widget(lbl)
            self.grid_controller.register(0, s + 1, lbl)

        results = exercise.get("results", [])
        for row, metric in enumerate(metrics, start=1):
            name = metric.get("name")
            name_lbl = MDLabel(text=name, size_hint=(None, None))
            # Borders removed here as well to avoid unintended outlines.
            self.metric_grid.add_widget(name_lbl)
            self.grid_controller.register(row, 0, name_lbl)
            for s in range(set_count):
                store = self.session.metric_store.get((self.exercise_idx, s), {})
                value = None
                if s < len(results):
                    value = results[s].get("metrics", {}).get(name)
                else:
                    # Fallback to pre-set metrics stored in metric_store so
                    # previously entered values for unfinished sets reappear.
                    value = store.get(name)
                widget = self._create_input_widget(metric, value, s)
                self.metric_cells[(name, s)] = widget
                self.metric_grid.add_widget(widget)
                self.grid_controller.register(row, s + 1, widget)

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

    def _on_cell_change(self, name, mtype, set_idx, widget):
        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)
        if not session:
            return
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
        exercise = session.exercises[self.exercise_idx]
        results = exercise.get("results", [])
        if set_idx < len(results):
            session.edit_set_metrics(self.exercise_idx, set_idx, {name: value})
        else:
            session.set_pre_set_metrics({name: value}, self.exercise_idx, set_idx)

    def _create_input_widget(self, metric, value, set_idx):
        name = metric.get("name")
        mtype = metric.get("type", "str")
        values = metric.get("values", [])
        if mtype == "slider":
            widget = MDSlider(min=0, max=1, value=value or 0)
            widget.bind(
                # Capture loop variables to ensure each cell updates correctly
                value=lambda inst,
                val,
                name=name,
                mtype=mtype,
                set_idx=set_idx: self._on_cell_change(
                    name, mtype, set_idx, inst
                ),
                on_touch_down=self.on_slider_touch_down,
                on_touch_up=self.on_slider_touch_up,
            )
        elif mtype == "enum":
            widget = Spinner(text=str(value) if value not in (None, "") else "", values=values)
            widget.bind(
                text=lambda inst,
                val,
                name=name,
                mtype=mtype,
                set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst)
            )
        elif mtype == "bool":
            widget = MDCheckbox(active=bool(value))
            widget.bind(
                active=lambda inst,
                val,
                name=name,
                mtype=mtype,
                set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst)
            )
        else:
            input_filter = None
            if mtype == "int":
                input_filter = "int"
            elif mtype == "float":
                input_filter = "float"
            widget = MDTextField(
                multiline=False,
                input_filter=input_filter,
                text=str(value) if value not in (None, "") else "",
            )
            widget.bind(
                text=lambda inst,
                val,
                name=name,
                mtype=mtype,
                set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst)
            )
        widget.size_hint = (None, None)
        widget.height = dp(40)
        widget.width = dp(100)  # Increased for easier data entry on small screens.
        # Borders previously drawn here introduced unwanted visual clutter.
        # Removing them simplifies the interface without altering layout.
        return widget

    # ------------------------------------------------------------------
    def save_metrics(self):
        """Persist entered metrics and return to the rest screen.

        When a set has just been completed ``WorkoutSession.mark_set_completed``
        leaves the indices pointing at that set until
        :meth:`WorkoutSession.record_metrics` is called.  The ``Finish`` button
        on :class:`WorkoutActiveScreen` flags ``App.record_new_set`` so this
        method knows a set was finished and needs to be recorded.  Recording the
        metrics here ensures the session advances to the next set before
        returning to the rest screen.
        """

        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)

        if app and session and getattr(app, "record_new_set", False):
            # ``record_metrics`` consumes values already stored in
            # ``session.metric_store`` via ``_on_cell_change`` to avoid holding
            # additional state.
            session.record_metrics(session.current_exercise, session.current_set, {})

        if app:
            app.record_new_set = False
            app.record_pre_set = False

        if getattr(self, "manager", None):
            self.manager.current = "rest"
