from kivymd.app import MDApp
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
    BooleanProperty,
    ListProperty,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDSeparator
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton
from pathlib import Path

# Import core so we can always reference the up-to-date WORKOUT_PRESETS list
import core
from core import (
    WorkoutSession,
    load_workout_presets,
    get_metrics_for_exercise,
    PresetEditor,
    DEFAULT_SETS_PER_EXERCISE,
)

# Load workout presets from the database at startup
load_workout_presets(Path(__file__).resolve().parent / "data" / "workout.db")
import time
import math



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
        self.elapsed = 0.0
        self.formatted_time = "00:00"
        self.start_time = time.time()
        self._event = Clock.schedule_interval(self._update_elapsed, 0.1)

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




class RestScreen(MDScreen):
    timer_label = StringProperty("00:20")
    target_time = NumericProperty(0)
    next_exercise_name = StringProperty("")
    is_ready = BooleanProperty(False)
    timer_color = ListProperty([1, 0, 0, 1])

    def on_enter(self, *args):
        session = MDApp.get_running_app().workout_session
        if session:
            self.next_exercise_name = session.next_exercise_display()
        if not self.target_time or self.target_time <= time.time():
            self.target_time = time.time() + 20
        self.is_ready = False
        self.timer_color = (1, 0, 0, 1)
        self.update_timer(0)
        self._event = Clock.schedule_interval(self.update_timer, 0.1)
        return super().on_enter(*args)

    def on_leave(self, *args):
        if hasattr(self, "_event") and self._event:
            self._event.cancel()
        return super().on_leave(*args)

    def toggle_ready(self):
        self.is_ready = not self.is_ready
        self.timer_color = (0, 1, 0, 1) if self.is_ready else (1, 0, 0, 1)
        if self.is_ready and self.target_time <= time.time():
            if hasattr(self, "_event") and self._event:
                self._event.cancel()
                self._event = None
            if self.manager:
                self.manager.current = "workout_active"

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
        now = time.time()
        if self.target_time <= now:
            self.target_time = now
        self.target_time += seconds
        if self.target_time <= now:
            self.target_time = now
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


class MetricInputScreen(MDScreen):
    """Screen for entering workout metrics."""

    prev_metric_list = ObjectProperty(None)
    next_metric_list = ObjectProperty(None)
    metrics_scroll = ObjectProperty(None)
    current_tab = StringProperty("previous")
    header_text = StringProperty("")

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
        self.update_header()
        return super().on_pre_enter(*args)

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
            all_metrics = get_metrics_for_exercise(curr_ex)
            prev_metrics = [m for m in all_metrics if m.get("input_timing") == "post_set"]

            upcoming_ex = app.workout_session.upcoming_exercise_name()
            next_all = get_metrics_for_exercise(upcoming_ex) if upcoming_ex else []
            next_metrics = [m for m in next_all if m.get("input_timing") == "pre_set"]
        elif metrics is not None:
            prev_metrics = metrics
            next_metrics = metrics

        if not self.prev_metric_list or not self.next_metric_list:
            return
        self.prev_metric_list.clear_widgets()
        self.next_metric_list.clear_widgets()

        def _create_row(metric):
            if isinstance(metric, str):
                name = metric
                input_type = "str"
                source_type = "manual_text"
                values = []
            else:
                name = metric.get("name")
                input_type = metric.get("input_type", "str")
                source_type = metric.get("source_type", "manual_text")
                values = metric.get("values", [])

            row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
            row.metric_name = name
            row.input_type = input_type
            row.source_type = source_type
            row.add_widget(MDLabel(text=name, size_hint_x=0.4))

            if source_type == "manual_slider":
                widget = MDSlider(min=0, max=1, value=0)
                widget.bind(on_touch_down=self.on_slider_touch_down, on_touch_up=self.on_slider_touch_up)
            elif source_type == "manual_enum":
                widget = Spinner(text=values[0] if values else "", values=values)
            else:  # manual_text
                input_filter = None
                if input_type == "int":
                    input_filter = "int"
                elif input_type == "float":
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
            input_type = getattr(row, "input_type", "str")
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
                value = 0 if input_type in ("int", "float") else ""
            if input_type == "int":
                try:
                    value = int(value)
                except ValueError:
                    value = 0
            elif input_type == "float":
                try:
                    value = float(value)
                except ValueError:
                    value = 0.0
            metrics[name] = value
        app = MDApp.get_running_app()
        if app.workout_session:
            finished = app.workout_session.record_metrics(metrics)
            if finished and self.manager:
                self.manager.current = "workout_summary"
            elif self.manager:
                self.manager.current = "rest"
        elif self.manager:
            self.manager.current = "rest"

class PresetsScreen(MDScreen):
    """Screen to select a workout preset."""

    preset_list = ObjectProperty(None)
    selected_preset = StringProperty("")
    selected_item = ObjectProperty(None, allownone=True)

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.preset_list:
            return
        self.preset_list.clear_widgets()
        for preset in core.WORKOUT_PRESETS:
            item = OneLineListItem(text=preset["name"])
            item.bind(on_release=lambda inst, name=preset["name"]: self.select_preset(name, inst))
            self.preset_list.add_widget(item)

    def select_preset(self, name, item):
        """Select a preset from WORKOUT_PRESETS and highlight item."""
        if self.selected_item:
            self.selected_item.md_bg_color = (0, 0, 0, 0)
        self.selected_item = item
        self.selected_item.md_bg_color = MDApp.get_running_app().theme_cls.primary_light
        if any(p["name"] == name for p in core.WORKOUT_PRESETS):
            self.selected_preset = name
            MDApp.get_running_app().selected_preset = name

    def confirm_selection(self):
        if self.selected_preset and self.manager:
            detail = self.manager.get_screen("preset_detail")
            detail.preset_name = self.selected_preset
            self.manager.current = "preset_detail"


class PresetDetailScreen(MDScreen):
    preset_name = StringProperty("")


class ExerciseLibraryScreen(MDScreen):
    previous_screen = StringProperty("home")

    def go_back(self):
        if self.manager:
            self.manager.current = self.previous_screen


class PresetOverviewScreen(MDScreen):
    overview_list = ObjectProperty(None)
    preset_label = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.overview_list or not self.preset_label:
            return
        self.overview_list.clear_widgets()
        app = MDApp.get_running_app()
        preset_name = app.selected_preset
        self.preset_label.text = (
            preset_name if preset_name else "Preset Overview - summary of the chosen preset"
        )
        for p in core.WORKOUT_PRESETS:
            if p["name"] == preset_name:
                for ex in p["exercises"]:
                    self.overview_list.add_widget(
                        OneLineListItem(text=f"{ex['name']} - sets: {ex['sets']}")
                    )
                break

    def start_workout(self):
        app = MDApp.get_running_app()
        preset_name = app.selected_preset
        app.start_workout(preset_name)
        if self.manager:
            self.manager.current = "rest"


class WorkoutSummaryScreen(MDScreen):
    summary_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.summary_list:
            return
        self.summary_list.clear_widgets()
        app = MDApp.get_running_app()
        session = app.workout_session
        if not session:
            return
        print(session.summary())
        for exercise in session.exercises:
            self.summary_list.add_widget(OneLineListItem(text=exercise["name"]))
            for idx, metrics in enumerate(exercise["results"], 1):
                metrics_text = ", ".join(f"{k}: {v}" for k, v in metrics.items())
                self.summary_list.add_widget(
                    OneLineListItem(text=f"Set {idx}: {metrics_text}")
                )


class SectionWidget(MDBoxLayout):
    """Single preset section containing exercises."""

    section_name = StringProperty("Section")
    section_index = NumericProperty(0)
    color = ListProperty([1, 1, 1, 1])
    expanded = BooleanProperty(True)

    def toggle(self):
        self.expanded = not self.expanded

    def open_exercise_selection(self):
        app = MDApp.get_running_app()
        app.editing_section_index = self.section_index
        if app.root:
            edit = app.root.get_screen("edit_preset")
            edit.show_only_section(self.section_index)
            edit.open_exercise_panel()

    def refresh_exercises(self):
        app = MDApp.get_running_app()
        if not app.preset_editor:
            return
        if self.section_index >= len(app.preset_editor.sections):
            return
        box = self.ids.exercise_list
        box.clear_widgets()
        for ex in app.preset_editor.sections[self.section_index]["exercises"]:
            box.add_widget(SelectedExerciseItem(text=ex["name"]))


class EditPresetScreen(MDScreen):
    """Screen to edit a workout preset."""

    preset_name = StringProperty("Preset")
    sections_box = ObjectProperty(None)
    panel_visible = BooleanProperty(False)
    exercise_panel = ObjectProperty(None)

    _colors = [
        (1, 0.9, 0.9, 1),
        (0.9, 1, 0.9, 1),
        (0.9, 0.9, 1, 1),
        (1, 1, 0.9, 1),
        (0.9, 1, 1, 1),
        (1, 0.9, 1, 1),
    ]

    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        app.init_preset_editor()
        self.preset_name = app.preset_editor.preset_name or "Preset"
        if self.sections_box:
            self.sections_box.clear_widgets()
            for idx, sec in enumerate(app.preset_editor.sections):
                self.add_section(sec["name"], index=idx)
            if not app.preset_editor.sections:
                self.add_section()
        return super().on_pre_enter(*args)

    def refresh_sections(self):
        """Repopulate the section widgets from the preset editor."""
        app = MDApp.get_running_app()
        if not self.sections_box:
            return
        self.sections_box.clear_widgets()
        for idx, sec in enumerate(app.preset_editor.sections):
            self.add_section(sec["name"], index=idx)
        if not app.preset_editor.sections:
            self.add_section()

    def open_exercise_panel(self):
        if self.exercise_panel:
            self.exercise_panel.on_open()
        self.panel_visible = True

    def close_exercise_panel(self):
        if self.exercise_panel:
            self.exercise_panel.save_selection()
        self.panel_visible = False
        self.refresh_sections()

    def show_only_section(self, index: int):
        """Hide all sections except the one with ``index``."""
        if not self.sections_box:
            return
        for child in list(self.sections_box.children):
            if isinstance(child, SectionWidget) and child.section_index != index:
                self.sections_box.remove_widget(child)

    def add_section(self, name: str | None = None, index: int | None = None):
        """Add a new section to the preset and return the widget."""
        if not self.sections_box:
            return None
        app = MDApp.get_running_app()
        if index is None:
            if not name:
                name = f"Section {len(app.preset_editor.sections) + 1}"
            index = app.preset_editor.add_section(name)
        color = self._colors[len(self.sections_box.children) % len(self._colors)]
        section = SectionWidget(section_name=name, color=color, section_index=index)
        self.sections_box.add_widget(section)
        section.refresh_exercises()
        return section


class SelectedExerciseItem(MDBoxLayout):
    """Widget representing a selected exercise with reorder controls."""

    text = StringProperty("")

    def edit(self):
        """Open the EditExerciseScreen for this exercise."""
        app = MDApp.get_running_app()
        if not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = self.text
        app.root.current = "edit_exercise"

    def move_up(self):
        parent = self.parent
        if not parent:
            return
        idx = parent.children.index(self)
        if idx < len(parent.children) - 1:
            parent.remove_widget(self)
            parent.add_widget(self, index=idx + 1)

    def move_down(self):
        parent = self.parent
        if not parent:
            return
        idx = parent.children.index(self)
        if idx > 0:
            parent.remove_widget(self)
            parent.add_widget(self, index=idx - 1)

    def remove_self(self):
        parent = self.parent
        if parent:
            parent.remove_widget(self)


class ExerciseSelectionPanel(MDBoxLayout):
    """Panel for selecting exercises to add to a preset section."""

    exercise_list = ObjectProperty(None)

    def on_open(self):
        self.populate_exercises()

    def populate_exercises(self):
        if not self.exercise_list:
            return
        self.exercise_list.clear_widgets()
        for name in core.get_all_exercises():
            item = OneLineListItem(text=name)
            item.bind(on_release=lambda inst, n=name: self.select_exercise(n))
            self.exercise_list.add_widget(item)

    def select_exercise(self, name):
        """Add ``name`` to the current section."""
        app = MDApp.get_running_app()
        idx = app.editing_section_index
        if app.preset_editor and 0 <= idx < len(app.preset_editor.sections):
            app.preset_editor.add_exercise(idx, name)
            edit = app.root.get_screen("edit_preset")
            for widget in edit.sections_box.children:
                if isinstance(widget, SectionWidget) and widget.section_index == idx:
                    widget.refresh_exercises()
                    break

    def save_selection(self):
        """No-op kept for API compatibility."""
        pass


class AddMetricPopup(MDDialog):
    """Popup dialog for selecting metrics or creating a new one."""

    def __init__(self, screen: 'EditExerciseScreen', mode: str = "select", **kwargs):
        self.screen = screen
        self.mode = mode

        if mode == "select":
            content, buttons, title = self._build_select_widgets()
        else:
            content, buttons, title = self._build_new_metric_widgets()

        super().__init__(title=title, type="custom", content_cls=content, buttons=buttons, **kwargs)

    # ------------------------------------------------------------------
    # Building widgets for both modes
    # ------------------------------------------------------------------
    def _build_select_widgets(self):
        metrics = core.get_all_metric_types()
        content = MDList()
        for m in metrics:
            item = OneLineListItem(text=m["name"])
            item.bind(on_release=lambda inst, name=m["name"]: self.add_metric(name))
            content.add_widget(item)
        new_btn = MDRaisedButton(text="New Metric", on_release=self.show_new_metric_form)
        buttons = [new_btn, MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())]
        return content, buttons, "Select Metric"

    def _build_new_metric_widgets(self):
        default_height = "48dp"
        self.name_input = MDTextField(hint_text="Name", size_hint_y=None, height=default_height)
        self.input_type = Spinner(text="int", values=["int", "float", "str", "bool"], size_hint_y=None, height=default_height)
        self.source_type = Spinner(
            text="manual_text",
            values=["manual_text", "manual_enum", "manual_slider"],
            size_hint_y=None,
            height=default_height,
        )
        self.input_timing = Spinner(
            text="post_set",
            values=["preset", "pre_workout", "post_workout", "pre_set", "post_set"],
            size_hint_y=None,
            height=default_height,
        )
        self.scope = Spinner(
            text="set",
            values=["session", "section", "exercise", "set"],
            size_hint_y=None,
            height=default_height,
        )
        self.desc_input = MDTextField(hint_text="Description", size_hint_y=None, height=default_height)
        self.required_check = MDCheckbox(size_hint_y=None, height=default_height)

        form = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
        )
        form.bind(minimum_height=form.setter("height"))
        form.add_widget(self.name_input)
        form.add_widget(self.input_type)
        form.add_widget(self.source_type)
        form.add_widget(self.input_timing)
        form.add_widget(self.scope)
        form.add_widget(self.desc_input)

        req_row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="40dp")
        req_row.add_widget(self.required_check)
        req_row.add_widget(MDLabel(text="Required"))
        form.add_widget(req_row)

        layout = ScrollView(do_scroll_y=True)
        layout.add_widget(form)

        save_btn = MDRaisedButton(text="Save", on_release=self.save_metric)
        back_btn = MDRaisedButton(text="Back", on_release=self.show_metric_list)
        buttons = [save_btn, back_btn]
        return layout, buttons, "New Metric"

    # ------------------------------------------------------------------
    # Mode switching helpers
    # ------------------------------------------------------------------
    def show_new_metric_form(self, *args):
        self.dismiss()
        popup = AddMetricPopup(self.screen, mode="new")
        popup.open()

    def show_metric_list(self, *args):
        self.dismiss()
        self.screen.open_add_metric_popup()

    def add_metric(self, name, *args):
        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        core.add_metric_to_exercise(self.screen.exercise_name, name, db_path)
        self.dismiss()
        self.screen.populate()

    def save_metric(self, *args):
        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        core.add_metric_type(
            self.name_input.text,
            self.input_type.text,
            self.source_type.text,
            self.input_timing.text,
            self.scope.text,
            description=self.desc_input.text,
            is_required=self.required_check.active,
            db_path=db_path,
        )
        self.show_metric_list()




class EditExerciseScreen(MDScreen):
    """Screen for editing an individual exercise within a preset."""

    exercise_name = StringProperty("")
    metrics_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.metrics_list or not self.exercise_name:
            return
        self.metrics_list.clear_widgets()
        metrics = core.get_metrics_for_exercise(self.exercise_name)
        timing_options = [
            "preset",
            "pre_workout",
            "post_workout",
            "pre_set",
            "post_set",
        ]

        for m in metrics:
            box = MDBoxLayout(
                orientation="vertical",
                padding="8dp",
                spacing="4dp",
                size_hint_y=None,
            )
            box.bind(minimum_height=box.setter("height"))

            def _make_label(text, **kwargs):
                lbl = MDLabel(text=text, size_hint_y=None, **kwargs)
                lbl.bind(texture_size=lambda inst, val: setattr(inst, "height", val[1]))
                lbl.height = lbl.texture_size[1]
                return lbl

            header = MDBoxLayout(size_hint_y=None, height="40dp")
            header.add_widget(
                _make_label(f"Metric: {m.get('name','')}", bold=True, size_hint_x=0.9)
            )
            remove_btn = MDIconButton(
                icon="delete",
                theme_text_color="Custom",
                text_color=(1, 0, 0, 1),
            )
            remove_btn.bind(
                on_release=lambda inst, name=m.get("name", ""): self.remove_metric(name)
            )
            header.add_widget(remove_btn)
            box.add_widget(header)

            box.add_widget(_make_label(f"Input type: {m.get('input_type','')}"))
            box.add_widget(_make_label(f"Source type: {m.get('source_type','')}"))

            timing_row = MDBoxLayout(size_hint_y=None, height="40dp")
            timing_row.add_widget(_make_label("Input timing:", size_hint_x=0.5))
            spinner = Spinner(text=m.get('input_timing','preset'), values=timing_options, size_hint_x=0.5)
            timing_row.add_widget(spinner)
            box.add_widget(timing_row)

            preset_row = MDBoxLayout(size_hint_y=None, height="40dp")
            preset_row.add_widget(_make_label("Preset value:", size_hint_x=0.5))
            preset_input = MDTextField(size_hint_x=0.5)
            preset_row.add_widget(preset_input)
            preset_row.opacity = 1 if spinner.text == "preset" else 0
            preset_row.disabled = spinner.text != "preset"

            def _update_preset_row(inst, val, row=preset_row):
                row.opacity = 1 if val == "preset" else 0
                row.disabled = val != "preset"

            spinner.bind(text=_update_preset_row)
            box.add_widget(preset_row)

            req_row = MDBoxLayout(size_hint_y=None, height="40dp")
            req_row.add_widget(_make_label("Required:", size_hint_x=0.5))
            req_checkbox = MDCheckbox(active=bool(m.get('is_required')), size_hint_x=None)
            req_row.add_widget(req_checkbox)
            box.add_widget(req_row)

            box.add_widget(_make_label(f"Scope: {m.get('scope','')}"))
            desc = m.get('description') or ""
            if desc:
                box.add_widget(_make_label(f"Description: {desc}", halign="left"))

            self.metrics_list.add_widget(box)
            self.metrics_list.add_widget(MDSeparator())

    def remove_metric(self, metric_name):
        if not self.exercise_name:
            return
        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        core.remove_metric_from_exercise(self.exercise_name, metric_name, db_path)
        self.populate()

    def open_add_metric_popup(self):
        popup = AddMetricPopup(self)
        popup.open()

    def open_new_metric_popup(self):
        popup = AddMetricPopup(self, mode="new")
        popup.open()


class WorkoutApp(MDApp):
    workout_session = None
    selected_preset = ""
    preset_editor: PresetEditor | None = None
    editing_section_index: int = -1

    def build(self):
        return Builder.load_file(str(Path(__file__).with_name("main.kv")))


    def init_preset_editor(self):
        """Create or reload the ``PresetEditor`` for the selected preset."""
        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        if self.selected_preset:
            if not self.preset_editor or self.preset_editor.preset_name != self.selected_preset:
                if self.preset_editor:
                    self.preset_editor.close()
                self.preset_editor = PresetEditor(self.selected_preset, db_path)
        else:
            if self.preset_editor:
                self.preset_editor.close()
            self.preset_editor = PresetEditor(db_path=db_path)

    def start_workout(self, exercises):
        if exercises:
            self.workout_session = WorkoutSession(exercises)

        else:
            self.workout_session = None


if __name__ == "__main__":
    WorkoutApp().run()
