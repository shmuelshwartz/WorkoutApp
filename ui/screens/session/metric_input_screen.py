"""Workout metric entry screen for single-set input.

This implementation targets small-screen devices. It shows metrics for the
current set only and lets users move between sets using left and right arrows.
Each metric appears on its own row with the name taking 40% of the width and
the value input 60%. Rows grow vertically to accommodate long names or text
entry. Widgets write their values directly to ``session.metric_store`` to keep
memory usage low.
"""

from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.properties import ObjectProperty, StringProperty, BooleanProperty
from kivymd.uix.screen import MDScreen
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivymd.uix.label import MDLabel
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDFlatButton
from kivy.uix.boxlayout import BoxLayout
from ui.colors import PINK_BG, PURPLE_BG


class MetricInputScreen(MDScreen):
    """Screen for entering workout metrics for a single set."""

    metrics_list = ObjectProperty(None)
    label_text = StringProperty("")
    can_nav_left = BooleanProperty(False)
    can_nav_right = BooleanProperty(False)
    can_skip_left = BooleanProperty(False)
    can_skip_right = BooleanProperty(False)
    exercise_bar = ObjectProperty(None)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.session = None
        self.exercise_idx = 0
        self.set_idx = 0
        self.session_idx = 0
        self.sessions: list[dict] = []
        self.metric_cells = {}

    # ------------------------------------------------------------------
    # Screen lifecycle --------------------------------------------------
    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        self.session = getattr(app, "workout_session", None)
        if self.session:
            self.exercise_idx = self.session.current_exercise
        else:
            self.exercise_idx = 0
        self.populate_exercise_bar()
        self._load_history()
        self.update_display()
        return super().on_pre_enter(*args)

    def update_display(self):
        """Refresh exercise highlight, metric list and navigation label."""
        self.highlight_current_exercise()
        self._update_set_label()
        self.update_metrics()

    # ------------------------------------------------------------------
    # Exercise selection ------------------------------------------------
    def populate_exercise_bar(self):
        """Create buttons for all exercises in the session."""
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
        for idx, child in enumerate(self.exercise_bar.children):
            color = (0.2, 0.6, 0.86, 1) if (len(self.exercise_bar.children) - 1 - idx) == self.exercise_idx else (0, 0, 0, 0)
            if hasattr(child, "md_bg_color"):
                child.md_bg_color = color

    def select_exercise(self, index: int):
        self.exercise_idx = index
        self.set_idx = 0
        self._load_history()
        self.update_display()

    # ------------------------------------------------------------------
    # Navigation --------------------------------------------------------
    def _update_set_label(self):
        if not self.session or self.exercise_idx >= len(self.session.exercises):
            self.label_text = ""
            self.can_nav_left = False
            self.can_nav_right = False
            self.can_skip_left = False
            self.can_skip_right = False
            return

        current_is_latest = self.session_idx == len(self.sessions) - 1
        if current_is_latest:
            ex = self.session.exercises[self.exercise_idx]
            total_sets = ex["sets"]
            session_label = "Current session"
        else:
            sess = self.sessions[self.session_idx]
            total_sets = len(sess.get("sets", []))
            session_label = sess.get("date", "")
        self.label_text = f"{session_label}\nSet {self.set_idx + 1}"
        self.can_nav_left = self.set_idx > 0
        self.can_nav_right = self.set_idx < max(total_sets - 1, 0)
        self.can_skip_left = self.session_idx > 0
        self.can_skip_right = self.session_idx < len(self.sessions) - 1
        self.md_bg_color = PURPLE_BG if current_is_latest else PINK_BG

    def navigate_left(self):
        if self.set_idx > 0:
            self.set_idx -= 1
            self.update_display()

    def navigate_right(self):
        if not self.session:
            return
        if self.session_idx == len(self.sessions) - 1:
            total_sets = self.session.exercises[self.exercise_idx]["sets"]
        else:
            total_sets = len(self.sessions[self.session_idx].get("sets", []))
        if self.set_idx < total_sets - 1:
            self.set_idx += 1
            self.update_display()

    def skip_left(self):
        if self.session_idx > 0:
            self.session_idx -= 1
            self.set_idx = 0
            self.update_display()

    def skip_right(self):
        if self.session_idx < len(self.sessions) - 1:
            self.session_idx += 1
            self.set_idx = 0
            self.update_display()

    def _load_history(self):
        """Load past session data for the current exercise."""
        self.sessions = []
        if self.session and hasattr(self.session, "exercise_history"):
            history = self.session.exercise_history.get(self.exercise_idx, [])
            self.sessions.extend(history)
        # always append placeholder for the current session
        self.sessions.append({"date": None})
        self.session_idx = len(self.sessions) - 1

    # ------------------------------------------------------------------
    # Metric rendering --------------------------------------------------
    def _sort_key(self, metric):
        required = 0 if metric.get("is_required") else 2
        timing = 0 if metric.get("input_timing") == "pre_set" else 1
        return required + timing

    def _apply_filters(self, metrics):
        """Return metrics sorted in display order."""
        if not metrics:
            return []
        return sorted(metrics, key=self._sort_key)

    def update_metrics(self):
        if not self.metrics_list:
            return
        self.metrics_list.clear_widgets()
        self.metric_cells.clear()
        if not self.session or self.exercise_idx >= len(self.session.exercises):
            return

        if not self.sessions:
            self.sessions = [{"date": None}]
            self.session_idx = 0

        exercise = self.session.exercises[self.exercise_idx]
        metrics = self._apply_filters(exercise.get("metric_defs", []))

        if self.session_idx == len(self.sessions) - 1:
            results = exercise.get("results", [])
            store = self.session.metric_store.get((self.exercise_idx, self.set_idx), {})
            read_only = False
        else:
            past = self.sessions[self.session_idx]
            results = past.get("sets", [])
            store = {}
            read_only = True


        for metric in metrics:
            name = metric.get("name")
            value = None
            if self.set_idx < len(results):
                value = results[self.set_idx].get("metrics", {}).get(name)
            else:
                value = store.get(name)
            if value in (None, ""):
                value = metric.get("value")
            row = self._create_row(metric, value, read_only=read_only)

            self.metrics_list.add_widget(row)
            widget = self.metric_cells.get(name)
            if widget is not None:
                self._set_widget_value(widget, metric, value)

    def _create_row(self, metric, value, read_only=False):

        name = metric.get("name", "")
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(40))
        name_lbl = MDLabel(text=name, size_hint_x=0.4, size_hint_y=None, halign="left", valign="middle")
        name_lbl.bind(
            texture_size=lambda inst, _val: setattr(inst, "height", inst.texture_size[1]),
            width=lambda inst, _val: setattr(inst, "text_size", (inst.width, None)),
        )
        widget = self._create_input_widget(metric, value, read_only=read_only)

        widget.size_hint_x = 0.6
        widget.size_hint_y = None
        widget.height = dp(40)

        def update_height(*_):
            row.height = max(name_lbl.height, widget.height)

        name_lbl.bind(height=update_height)
        widget.bind(height=update_height)
        update_height()

        row.add_widget(name_lbl)
        row.add_widget(widget)
        self.metric_cells[name] = widget
        return row

    def _resize_textfield(self, widget):
        lines = widget.text.count("\n") + 1
        widget.height = dp(40) + (lines - 1) * dp(20)

    def _set_widget_value(self, widget, metric, value):
        """Assign ``value`` to ``widget`` after it has been added to the UI."""
        mtype = metric.get("type", "str")
        name = metric.get("name", "")
        if isinstance(widget, MDTextField):
            widget.text = "" if value in (None, "") else str(value)
            if name.lower() == "notes":
                self._resize_textfield(widget)
        elif isinstance(widget, MDSlider):
            widget.value = value if value not in (None, "") else 0
        elif isinstance(widget, Spinner):
            widget.text = str(value) if value not in (None, "") else ""
        elif isinstance(widget, MDCheckbox):
            widget.active = bool(value)

    def on_slider_touch_down(self, instance, touch):
        """Disable vertical scrolling when interacting with a slider."""
        if instance.collide_point(*touch.pos):
            scroll = self._parent_scroll(instance)
            if scroll:
                scroll.do_scroll_y = False
        return False

    def on_slider_touch_up(self, instance, touch):
        """Re-enable vertical scrolling after slider interaction."""
        scroll = self._parent_scroll(instance)
        if scroll:
            scroll.do_scroll_y = True
        return False

    def _parent_scroll(self, widget):
        parent = getattr(widget, "parent", None)
        while parent is not None and not hasattr(parent, "do_scroll_y"):
            parent = getattr(parent, "parent", None)
        return parent

    def _on_cell_change(self, name, mtype, set_idx, widget):
        """Persist changes from an input widget into the session store."""
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

    def _create_input_widget(self, metric, value, read_only=False):

        name = metric.get("name")
        mtype = metric.get("type", "str")
        values = metric.get("values", [])
        set_idx = self.set_idx
        if mtype == "slider":
            widget = MDSlider(min=0, max=1, value=value or 0, disabled=read_only)
            if not read_only:
                widget.bind(
                    value=lambda inst, val, name=name, mtype=mtype, set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst),
                    on_touch_down=self.on_slider_touch_down,
                    on_touch_up=self.on_slider_touch_up,
                )
        elif mtype == "enum":
            widget = Spinner(
                text=str(value) if value not in (None, "") else "",
                values=values,
                disabled=read_only,

            )
            if not read_only:
                widget.bind(
                    text=lambda inst, val, name=name, mtype=mtype, set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst)
                )
        elif mtype == "bool":
            widget = MDCheckbox(active=bool(value), disabled=read_only)
            if not read_only:
                widget.bind(
                    active=lambda inst, val, name=name, mtype=mtype, set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst),
                )

        else:
            input_filter = None
            if mtype == "int":
                input_filter = "int"
            elif mtype == "float":
                input_filter = "float"
            multiline = name.lower() == "notes"
            widget = MDTextField(
                multiline=multiline,
                input_filter=input_filter,
                text=str(value) if value not in (None, "") else "",
                disabled=read_only,

            )
            if not read_only:
                widget.bind(
                    text=lambda inst, val, name=name, mtype=mtype, set_idx=set_idx: self._on_cell_change(name, mtype, set_idx, inst)
                )
            if multiline:
                widget.bind(text=lambda inst, _val: self._resize_textfield(inst))
        widget.size_hint = (None, None)
        widget.height = dp(40)
        return widget

    # ------------------------------------------------------------------
    def save_metrics(self):
        """Persist entered metrics and return to the rest screen."""
        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)

        if app and session and getattr(app, "record_new_set", False):
            session.record_metrics(session.current_exercise, session.current_set, {})

        if app:
            app.record_new_set = False
            app.record_pre_set = False

        if getattr(self, "manager", None):
            self.manager.current = "rest"

