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
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem
from kivymd.uix.button import MDIconButton
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

    metric_list = ObjectProperty(None)
    metrics_scroll = ObjectProperty(None)

    def on_slider_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos) and self.metrics_scroll:
            self.metrics_scroll.do_scroll_y = False
        return False

    def on_slider_touch_up(self, instance, touch):
        if self.metrics_scroll:
            self.metrics_scroll.do_scroll_y = True
        return False

    def populate_metrics(self, metrics=None):
        """Populate the metric list based on the current exercise."""
        app = MDApp.get_running_app()
        if app.workout_session:
            exercise = app.workout_session.next_exercise_name()
            metrics = get_metrics_for_exercise(exercise)
        # Do not fall back to default metrics if none are defined
        if metrics is None:
            metrics = []
        if not self.metric_list:
            return
        self.metric_list.clear_widgets()
        for m in metrics:
            if isinstance(m, str):
                name = m
                input_type = "str"
                source_type = "manual_text"
                values = []
            else:
                name = m.get("name")
                input_type = m.get("input_type", "str")
                source_type = m.get("source_type", "manual_text")
                values = m.get("values", [])

            row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
            row.metric_name = name
            row.input_type = input_type
            row.source_type = source_type

            row.add_widget(MDLabel(text=name, size_hint_x=0.4))

            if source_type == "manual_slider":
                widget = MDSlider(min=0, max=1, value=0)
                widget.bind(
                    on_touch_down=self.on_slider_touch_down,
                    on_touch_up=self.on_slider_touch_up,
                )
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
            self.metric_list.add_widget(row)

    def save_metrics(self):
        metrics = {}
        for row in reversed(self.metric_list.children):
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
