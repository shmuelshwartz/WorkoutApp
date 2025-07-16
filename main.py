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
from kivymd.uix.list import (
    OneLineListItem,
    MDList,
)
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDIconButton
from kivymd.uix.card import MDSeparator
from kivymd.uix.dialog import MDDialog
try:
    from kivymd.uix.spinner import MDSpinner
except Exception:  # pragma: no cover - fallback for tests without kivymd
    from kivy.uix.spinner import Spinner as MDSpinner
from kivymd.uix.button import MDRaisedButton
from kivy.uix.screenmanager import NoTransition
from pathlib import Path
import os

# Import core so we can always reference the up-to-date WORKOUT_PRESETS list
import core
from core import (
    WorkoutSession,
    load_workout_presets,
    get_metrics_for_exercise,
    PresetEditor,
    DEFAULT_SETS_PER_EXERCISE,
    DEFAULT_REST_DURATION,
)

# Load workout presets from the database at startup
load_workout_presets(Path(__file__).resolve().parent / "data" / "workout.db")
import time
import math

from kivy.core.window import Window
import string
import sqlite3
Window.size = (280, 280 * (20 / 9))

# Order of fields for metric editing popups
METRIC_FIELD_ORDER = [
    "name",
    "description",
    "input_type",
    "source_type",
    "input_timing",
    "scope",
    "is_required",
]



class LoadingDialog(MDDialog):
    """Simple dialog displaying a spinner while work is performed."""

    def __init__(self, text: str = "Loading...", **kwargs):
        box = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
            height="72dp",
        )
        spinner = MDSpinner(size_hint=(None, None), size=("48dp", "48dp"))
        spinner.pos_hint = {"center_x": 0.5}
        box.add_widget(spinner)
        box.add_widget(MDLabel(text=text, halign="center"))
        super().__init__(type="custom", content_cls=box, **kwargs)


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
            self.target_time = session.rest_target_time
        else:
            self.target_time = time.time() + DEFAULT_REST_DURATION
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
                get_metrics_for_exercise(upcoming_ex, preset_name=app.workout_session.preset_name)
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
        if app.workout_session and getattr(app, "record_new_set", False):
            finished = app.workout_session.record_metrics(metrics)
            app.record_new_set = False
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
    exercise_list = ObjectProperty(None)
    filter_mode = StringProperty("both")
    filter_dialog = ObjectProperty(None, allownone=True)
    search_text = StringProperty("")
    # Cached list of all exercises including user-created ones
    all_exercises = ListProperty(None, allownone=True)
    # Version of the exercise library when the cache was loaded
    cache_version = NumericProperty(-1)

    loading_dialog = ObjectProperty(None, allownone=True)

    _search_event = None


    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        if (
            self.all_exercises is None
            or (app and self.cache_version != getattr(app, "exercise_library_version", 0))
        ):
            db_path = Path(__file__).resolve().parent / "data" / "workout.db"
            self.all_exercises = core.get_all_exercises(db_path, include_user_created=True)
            if app:
                self.cache_version = app.exercise_library_version

        self.populate(True)

        return super().on_pre_enter(*args)

    def populate(self, show_loading: bool = False):
        if show_loading and not os.environ.get("KIVY_UNITTEST"):
            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(self._populate_impl, 0)
        else:
            self._populate_impl()

    def _populate_impl(self, dt: float | None = None):
        if not self.exercise_list:
            if self.loading_dialog:
                self.loading_dialog.dismiss()
                self.loading_dialog = None
            return
        # Clearing widgets directly can remove the internal layout manager of
        # ``RecycleView``. Reset the data list instead so the manager stays
        # intact and items refresh correctly.
        self.exercise_list.data = []
        app = MDApp.get_running_app()
        if (
            self.all_exercises is None
            or (app and self.cache_version != getattr(app, "exercise_library_version", 0))
        ):
            db_path = Path(__file__).resolve().parent / "data" / "workout.db"
            self.all_exercises = core.get_all_exercises(db_path, include_user_created=True)
            if app:
                self.cache_version = app.exercise_library_version
        exercises = self.all_exercises or []

        if self.filter_mode == "user":
            exercises = [ex for ex in exercises if ex[1]]
        elif self.filter_mode == "premade":
            exercises = [ex for ex in exercises if not ex[1]]
        if self.search_text:
            s = self.search_text.lower()
            exercises = [ex for ex in exercises if s in ex[0].lower()]
        data = []
        for name, is_user in exercises:
            item = {
                "name": name,
                "text": name,
                "is_user_created": is_user,
                "edit_callback": self.open_edit_popup,
                "delete_callback": self.confirm_delete_exercise,
            }
            data.append(item)

        # ``RecycleView`` expects ``data`` to contain dictionaries describing
        # how the viewclass should be configured. Adding widgets directly to the
        # view is incorrect and results in ``WidgetException``.  The data list is
        # assigned at once to refresh the view.
        self.exercise_list.data = data
        if self.loading_dialog:
            self.loading_dialog.dismiss()
            self.loading_dialog = None


    def open_filter_popup(self):
        list_view = MDList()
        options = [
            ("User Created", "user"),
            ("Premade", "premade"),
            ("Both", "both"),
        ]
        for label, mode in options:
            item = OneLineListItem(text=label)
            item.bind(on_release=lambda inst, m=mode: self.apply_filter(m))
            list_view.add_widget(item)
        scroll = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(200))
        scroll.add_widget(list_view)
        close_btn = MDRaisedButton(
            text="Close", on_release=lambda *a: self.filter_dialog.dismiss()
        )
        self.filter_dialog = MDDialog(
            title="Filter Exercises", type="custom", content_cls=scroll, buttons=[close_btn]
        )
        self.filter_dialog.open()

    def update_search(self, text):
        """Update search text with debounce to limit populate frequency."""
        self.search_text = text
        if self._search_event:
            self._search_event.cancel()

        def do_populate(dt):
            self._search_event = None
            self.populate()

        # schedule populate with a short delay to debounce rapid input
        self._search_event = Clock.schedule_once(do_populate, 0.2)

    def apply_filter(self, mode, *args):
        self.filter_mode = mode
        if self.filter_dialog:
            self.filter_dialog.dismiss()
            self.filter_dialog = None
        self.populate()

    def open_edit_popup(self, exercise_name, is_user_created):
        """Navigate to ``EditExerciseScreen`` with ``exercise_name`` loaded."""
        app = MDApp.get_running_app()
        if not app or not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = exercise_name
        screen.is_user_created = is_user_created
        screen.section_index = -1
        screen.exercise_index = -1
        screen.previous_screen = "exercise_library"
        app.root.current = "edit_exercise"

    def confirm_delete_exercise(self, exercise_name):
        dialog = None

        def do_delete(*args):
            db_path = Path(__file__).resolve().parent / "data" / "workout.db"
            try:
                core.delete_exercise(exercise_name, db_path=db_path, is_user_created=True)
                app = MDApp.get_running_app()
                if app:
                    app.exercise_library_version += 1
            except Exception:
                pass
            self.all_exercises = None
            self.populate()
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Delete Exercise?",
            text=f"Delete {exercise_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def new_exercise(self):
        """Open ``EditExerciseScreen`` to create a new exercise."""
        app = MDApp.get_running_app()
        if not app or not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = ""
        screen.is_user_created = True
        screen.section_index = -1
        screen.exercise_index = -1
        screen.previous_screen = "exercise_library"
        app.root.current = "edit_exercise"

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
        for idx, ex in enumerate(app.preset_editor.sections[self.section_index]["exercises"]):
            box.add_widget(
                SelectedExerciseItem(
                    text=ex["name"],
                    section_index=self.section_index,
                    exercise_index=idx,
                )
            )

    def confirm_delete(self):
        dialog = None

        def do_delete(*args):
            app = MDApp.get_running_app()
            if app.preset_editor:
                app.preset_editor.remove_section(self.section_index)
            if app.root:
                edit = app.root.get_screen("edit_preset")
                edit.refresh_sections()
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Remove Section?",
            text=f"Delete {self.section_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()


class EditPresetScreen(MDScreen):
    """Screen to edit a workout preset."""

    preset_name = StringProperty("Preset")
    sections_box = ObjectProperty(None)
    panel_visible = BooleanProperty(False)
    exercise_panel = ObjectProperty(None)
    current_tab = StringProperty("sections")

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
        self.current_tab = "sections"
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

    def switch_tab(self, tab: str):
        """Switch between the sections and details tabs."""
        if tab in ("sections", "details"):
            self.current_tab = tab

    def update_preset_name(self, name: str):
        """Update the preset name in the editor."""
        self.preset_name = name
        app = MDApp.get_running_app()
        if app.preset_editor:
            app.preset_editor.preset_name = name



class SelectedExerciseItem(MDBoxLayout):
    """Widget representing a selected exercise with reorder controls."""

    text = StringProperty("")
    section_index = NumericProperty(0)
    exercise_index = NumericProperty(0)

    def edit(self):
        """Open the EditExerciseScreen for this exercise."""
        app = MDApp.get_running_app()
        if not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = self.text
        screen.section_index = self.section_index
        screen.exercise_index = self.exercise_index
        screen.previous_screen = "edit_preset"
        app.editing_section_index = self.section_index
        app.editing_exercise_index = self.exercise_index
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
        dialog = None

        def do_delete(*args):
            parent = self.parent
            if parent:
                parent.remove_widget(self)
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Remove Exercise?",
            text=f"Delete {self.text} from this workout?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()


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
    """Popup dialog for choosing an action, selecting metrics or creating a new one."""

    def __init__(self, screen: 'EditExerciseScreen', mode: str = "select", **kwargs):
        self.screen = screen
        self.mode = mode

        if mode == "select":
            content, buttons, title = self._build_select_widgets()
        elif mode == "new":
            content, buttons, title = self._build_new_metric_widgets()
        else:  # initial choice
            content, buttons, title = self._build_choice_widgets()

        super().__init__(title=title, type="custom", content_cls=content, buttons=buttons, **kwargs)

    # ------------------------------------------------------------------
    # Building widgets for both modes
    # ------------------------------------------------------------------
    def _build_select_widgets(self):
        metrics = core.get_all_metric_types()
        existing = {m.get("name") for m in self.screen.exercise_obj.metrics}
        metrics = [m for m in metrics if m["name"] not in existing]
        list_view = MDList()
        for m in metrics:
            item = OneLineListItem(text=m["name"])
            item.bind(on_release=lambda inst, name=m["name"]: self.add_metric(name))
            list_view.add_widget(item)

        scroll = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        scroll.add_widget(list_view)

        new_btn = MDRaisedButton(text="New Metric", on_release=self.show_new_metric_form)
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        buttons = [new_btn, cancel_btn]
        return scroll, buttons, "Select Metric"

    def _build_new_metric_widgets(self):
        default_height = dp(48)
        self.input_widgets = {}

        schema = core.get_metric_type_schema()
        if not schema:
            schema = [
                {"name": "name"},
                {"name": "description"},
                {"name": "input_type", "options": ["int", "float", "str", "bool"]},
                {
                    "name": "source_type",
                    "options": ["manual_text", "manual_enum", "manual_slider"],
                },
                {
                    "name": "input_timing",
                    "options": [
                        "preset",
                        "pre_workout",
                        "post_workout",
                        "pre_set",
                        "post_set",
                    ],
                },
                {
                    "name": "scope",
                    "options": ["session", "section", "exercise", "set"],
                },
                {"name": "is_required"},
            ]
        else:
            order_map = {field["name"]: field for field in schema}
            schema = [
                order_map[name]
                for name in METRIC_FIELD_ORDER
                if name in order_map
            ] + [
                field
                for field in schema
                if field["name"] not in METRIC_FIELD_ORDER
            ]

        form = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
        )
        form.bind(minimum_height=form.setter("height"))

        def enable_auto_resize(text_field: MDTextField):
            text_field.bind(
                text=lambda inst, val: setattr(inst, "height", max(default_height, inst.minimum_height))
            )

        for field in schema:
            name = field["name"]
            options = field.get("options")
            if name == "is_required":
                row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="40dp")
                widget = MDCheckbox(size_hint_y=None, height=default_height)
                row.add_widget(widget)
                row.add_widget(MDLabel(text="Required"))
                form.add_widget(row)
            elif options:
                widget = Spinner(text=options[0], values=options, size_hint_y=None, height=default_height)
                form.add_widget(widget)
            else:
                # Older versions of KivyMD do not accept the
                # ``hint_text_font_size`` kwarg. Set the property
                # after creation to avoid ``TypeError``.
                widget = MDTextField(
                    hint_text=name.replace("_", " ").title(),
                    size_hint_y=None,
                    height=default_height,
                )
                widget.hint_text_font_size = "12sp"
                enable_auto_resize(widget)
                form.add_widget(widget)

            self.input_widgets[name] = widget

        # Text box for enum values. This field only appears when the
        # metric's source type is ``manual_enum``.
        self.enum_values_field = MDTextField(
            hint_text="Enum Values (comma separated)",
            size_hint_y=None,
            height=default_height,
        )
        self.enum_values_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.enum_values_field)
        form.add_widget(self.enum_values_field)

        # Helper that toggles visibility based on ``source_type``.

        def update_enum_visibility(*args):
            show = self.input_widgets["source_type"].text == "manual_enum"
            if show:
                if self.enum_values_field.parent is None:
                    form.add_widget(self.enum_values_field)
                self.enum_values_field.opacity = 1
                # self.enum_values_field.height = default_height
            else:
                if self.enum_values_field.parent is not None:
                    form.remove_widget(self.enum_values_field)
                # self.enum_values_field.opacity = 0
                # self.enum_values_field.height = 0

        def update_enum_filter(*args):
            input_type = self.input_widgets["input_type"].text
            if input_type == "int":
                allowed = string.digits + ","
            elif input_type == "float":
                allowed = string.digits + ".,"
            else:  # default to str
                allowed = string.ascii_letters + ","

            def _filter(value, from_undo):
                return "".join(ch for ch in value if ch in allowed)

            self.enum_values_field.input_filter = _filter
        if "source_type" in self.input_widgets and "input_type" in self.input_widgets:
            self.input_widgets["input_type"].bind(text=lambda *a: update_enum_filter())
            self.input_widgets["source_type"].bind(text=lambda *a: update_enum_visibility())
            update_enum_visibility()
            update_enum_filter()

        layout = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        layout.add_widget(form)

        save_btn = MDRaisedButton(text="Save", on_release=self.save_metric)
        back_btn = MDRaisedButton(text="Back", on_release=lambda *a: self.dismiss())
        buttons = [save_btn, back_btn]
        return layout, buttons, "New Metric"

    def _build_choice_widgets(self):
        label = MDLabel(text="Choose an option", halign="center")
        add_btn = MDRaisedButton(text="Add Metric", on_release=self.show_metric_list)
        new_btn = MDRaisedButton(text="New Metric", on_release=self.show_new_metric_form)
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        content = MDBoxLayout(orientation="vertical", spacing="8dp")
        content.add_widget(label)
        buttons = [add_btn, new_btn, cancel_btn]
        return content, buttons, "Metric Options"

    # ------------------------------------------------------------------
    # Mode switching helpers
    # ------------------------------------------------------------------
    def show_new_metric_form(self, *args):
        self.dismiss()
        popup = AddMetricPopup(self.screen, mode="new")
        popup.open()

    def show_metric_list(self, *args):
        self.dismiss()
        popup = AddMetricPopup(self.screen, mode="select")
        popup.open()

    def add_metric(self, name, *args):
        """Add the selected metric type to the exercise object."""
        metric_defs = core.get_all_metric_types()
        for m in metric_defs:
            if m["name"] == name:
                self.screen.exercise_obj.add_metric(m)
                break
        self.dismiss()
        self.screen.populate()
        self.screen.save_enabled = self.screen.exercise_obj.is_modified()

    def save_metric(self, *args):
        """Validate fields and add the new metric to the exercise object."""
        errors = []

        name = self.input_widgets["name"].text.strip()
        input_type = self.input_widgets["input_type"].text
        source_type = self.input_widgets["source_type"].text

        if not name:
            errors.append("name")

        # check for duplicate metric name
        existing_names = {m.get("name") for m in self.screen.exercise_obj.metrics}
        if name and name in existing_names:
            errors.append("name")
            if hasattr(self.input_widgets["name"], "helper_text"):
                self.input_widgets["name"].helper_text = "Duplicate name"
                self.input_widgets["name"].helper_text_mode = "on_error"

        if input_type == "bool" and source_type == "manual_enum":
            errors.extend(["input_type", "source_type"])

        if source_type == "manual_slider" and input_type != "float":
            errors.extend(["input_type", "source_type"])

        values = []
        if source_type == "manual_enum":
            text = self.enum_values_field.text.strip()
            if not text:
                errors.append("enum_values")
            else:
                values = [v.strip() for v in text.split(",") if v.strip()]
                if not values:
                    errors.append("enum_values")

        red = (1, 0, 0, 1)
        for key, widget in self.input_widgets.items():
            if isinstance(widget, Spinner):
                widget.text_color = red if key in errors else (1, 1, 1, 1)
            elif isinstance(widget, MDTextField):
                widget.error = key in errors
        self.enum_values_field.error = "enum_values" in errors

        if errors:
            return

        metric = {}
        for key, widget in self.input_widgets.items():
            if isinstance(widget, MDCheckbox):
                metric[key] = bool(widget.active)
            else:
                metric[key] = widget.text
        if values:
            metric["values"] = values

        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        try:
            core.add_metric_type(
                metric["name"],
                metric["input_type"],
                metric["source_type"],
                metric["input_timing"],
                metric["scope"],
                metric.get("description", ""),
                metric.get("is_required", False),
                db_path=db_path,
            )
        except sqlite3.IntegrityError:
            self.input_widgets["name"].error = True
            return

        self.screen.exercise_obj.add_metric(metric)
        self.show_metric_list()
        self.screen.save_enabled = self.screen.exercise_obj.is_modified()


class EditMetricPopup(MDDialog):
    """Popup for editing an existing metric."""

    def __init__(self, screen: 'EditExerciseScreen', metric: dict, **kwargs):
        self.screen = screen
        self.metric = metric
        content, buttons, title = self._build_widgets()
        super().__init__(title=title, type="custom", content_cls=content, buttons=buttons, **kwargs)

    def _build_widgets(self):
        default_height = "48dp"
        self.input_widgets = {}

        schema = core.get_metric_type_schema()
        if not schema:
            schema = [
                {"name": "name"},
                {"name": "description"},
                {"name": "input_type", "options": ["int", "float", "str", "bool"]},
                {
                    "name": "source_type",
                    "options": ["manual_text", "manual_enum", "manual_slider"],
                },
                {
                    "name": "input_timing",
                    "options": [
                        "preset",
                        "pre_workout",
                        "post_workout",
                        "pre_set",
                        "post_set",
                    ],
                },
                {
                    "name": "scope",
                    "options": ["session", "section", "exercise", "set"],
                },
                {"name": "is_required"},
            ]
        else:
            order_map = {field["name"]: field for field in schema}
            schema = [
                order_map[name]
                for name in METRIC_FIELD_ORDER
                if name in order_map
            ] + [
                field
                for field in schema
                if field["name"] not in METRIC_FIELD_ORDER
            ]

        form = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
        )
        form.bind(minimum_height=form.setter("height"))

        for field in schema:
            name = field["name"]
            options = field.get("options")
            if name == "is_required":
                row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="40dp")
                widget = MDCheckbox(size_hint_y=None, height=default_height)
                row.add_widget(widget)
                row.add_widget(MDLabel(text="Required"))
                form.add_widget(row)
            elif options:
                widget = Spinner(text=options[0], values=options, size_hint_y=None, height=default_height)
                form.add_widget(widget)
            else:
                widget = MDTextField(hint_text=name.replace("_", " ").title(), size_hint_y=None, height=default_height)
                form.add_widget(widget)

            self.input_widgets[name] = widget

        # populate values
        for key, widget in self.input_widgets.items():
            if key not in self.metric:
                continue
            value = self.metric[key]
            if isinstance(widget, MDCheckbox):
                widget.active = bool(value)
            elif isinstance(widget, Spinner):
                if value in widget.values:
                    widget.text = value
            elif isinstance(widget, MDTextField):
                widget.text = str(value)

        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height="40dp")
        self.make_default = MDCheckbox(active=True)
        row.add_widget(self.make_default)
        row.add_widget(MDLabel(text="Make default"))
        form.add_widget(row)

        layout = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        layout.add_widget(form)

        save_btn = MDRaisedButton(text="Save", on_release=self.save_metric)
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        buttons = [save_btn, cancel_btn]
        return layout, buttons, "Edit Metric"

    def save_metric(self, *args):
        """Update the metric on the exercise object with the new values."""
        updates = {}
        for key, widget in self.input_widgets.items():
            if isinstance(widget, MDCheckbox):
                updates[key] = bool(widget.active)
            else:
                updates[key] = widget.text
        self.screen.exercise_obj.update_metric(self.metric["name"], **updates)
        self.dismiss()
        self.screen.populate()
        self.screen.save_enabled = self.screen.exercise_obj.is_modified()



class EditExerciseScreen(MDScreen):
    """Screen for editing an individual exercise within a preset."""

    exercise_name = StringProperty("")
    exercise_description = StringProperty("")
    section_index = NumericProperty(-1)
    exercise_index = NumericProperty(-1)
    previous_screen = StringProperty("edit_preset")
    metrics_list = ObjectProperty(None)
    name_field = ObjectProperty(None)
    description_field = ObjectProperty(None)
    exercise_obj = ObjectProperty(None, rebind=True)
    current_tab = StringProperty("metrics")
    save_enabled = BooleanProperty(False)
    is_user_created = ObjectProperty(None, allownone=True)
    loading_dialog = ObjectProperty(None, allownone=True)

    def switch_tab(self, tab: str):
        """Switch between the metrics and details tabs."""
        if tab in ("metrics", "details"):
            self.current_tab = tab
            if "exercise_tabs" in self.ids:
                self.ids.exercise_tabs.current = tab
    def on_pre_enter(self, *args):
        if os.environ.get("KIVY_UNITTEST"):
            self._load_exercise()
        else:
            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(lambda dt: self._load_exercise(), 0)
        return super().on_pre_enter(*args)

    def _load_exercise(self):
        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        self.exercise_obj = core.Exercise(
            self.exercise_name,
            db_path=db_path,
            is_user_created=self.is_user_created,
        )
        self.is_user_created = self.exercise_obj.is_user_created
        self.exercise_name = self.exercise_obj.name
        self.exercise_description = self.exercise_obj.description
        self.save_enabled = False
        self.populate()
        if self.loading_dialog:
            self.loading_dialog.dismiss()
            self.loading_dialog = None

    def populate(self):
        self.populate_metrics()
        self.populate_details()

    def populate_metrics(self):
        if not self.metrics_list or not self.exercise_obj:
            return
        self.metrics_list.clear_widgets()
        metrics = self.exercise_obj.metrics
        for m in metrics:
            row = MDBoxLayout(size_hint_y=None, height="40dp")
            lbl = MDLabel(text=m.get("name", ""), halign="left")
            row.add_widget(lbl)
            edit_btn = MDIconButton(icon="pencil")
            edit_btn.bind(on_release=lambda inst, metric=m: self.open_edit_metric_popup(metric))
            row.add_widget(edit_btn)
            remove_btn = MDIconButton(
                icon="delete",
                theme_text_color="Custom",
                text_color=(1, 0, 0, 1),
            )
            remove_btn.bind(
                on_release=lambda inst, name=m.get("name", ""): self.confirm_remove_metric(name)
            )
            row.add_widget(remove_btn)
            self.metrics_list.add_widget(row)
            self.metrics_list.add_widget(MDSeparator())

    def populate_details(self):
        if not self.exercise_obj:
            return
        if self.name_field:
            self.name_field.text = self.exercise_obj.name
        if self.description_field:
            self.description_field.text = self.exercise_obj.description

    def update_name(self, name: str):
        if self.exercise_obj is not None:
            self.exercise_obj.name = name
            self.save_enabled = self.exercise_obj.is_modified()
        else:
            self.save_enabled = False
        self.exercise_name = name

    def update_description(self, desc: str):
        if self.exercise_obj is not None:
            self.exercise_obj.description = desc
            self.save_enabled = self.exercise_obj.is_modified()
        else:
            self.save_enabled = False
        self.exercise_description = desc

    def remove_metric(self, metric_name):
        if self.exercise_obj:
            self.exercise_obj.remove_metric(metric_name)
        self.populate()
        if self.exercise_obj:
            self.save_enabled = self.exercise_obj.is_modified()

    def confirm_remove_metric(self, metric_name):
        dialog = None

        def do_delete(*args):
            self.remove_metric(metric_name)
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Remove Metric?",
            text=f"Delete {metric_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def open_add_metric_popup(self):
        popup = AddMetricPopup(self, mode="select")
        popup.open()

    def open_new_metric_popup(self):
        popup = AddMetricPopup(self, mode="new")
        popup.open()

    def open_edit_metric_popup(self, metric):
        popup = EditMetricPopup(self, metric)
        popup.open()

    def save_exercise(self):
        if not self.exercise_obj:
            return

        db_path = Path(__file__).resolve().parent / "data" / "workout.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        msg = "Save changes to this exercise?"
        if not self.exercise_obj.is_user_created:
            cursor.execute(
                "SELECT 1 FROM exercises WHERE name = ? AND is_user_created = 1",
                (self.exercise_obj.name,),
            )
            exists = cursor.fetchone()
            if exists:
                msg = (
                    f"A user-defined copy of {self.exercise_obj.name} exists and will be overwritten."
                )
            else:
                msg = (
                    f"{self.exercise_obj.name} is predefined. A user-defined copy will be created."
                )
        conn.close()

        dialog = None

        def do_save(*args):
            core.save_exercise(self.exercise_obj)
            app = MDApp.get_running_app()
            if app:
                app.exercise_library_version += 1
            self.save_enabled = False
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Confirm Save",
            text=msg,
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Save", on_release=do_save),
            ],
        )
        dialog.open()

    def go_back(self):
        if self.save_enabled:
            dialog = None

            def discard(*args):
                if dialog:
                    dialog.dismiss()
                if self.manager:
                    self.manager.current = self.previous_screen

            dialog = MDDialog(
                title="Discard Changes?",
                text="You have unsaved changes. Discard them?",
                buttons=[
                    MDRaisedButton(
                        text="Cancel", on_release=lambda *a: dialog.dismiss()
                    ),
                    MDRaisedButton(text="Discard", on_release=discard),
                ],
            )
            dialog.open()
        else:
            if self.manager:
                self.manager.current = self.previous_screen

class WorkoutApp(MDApp):
    workout_session = None
    selected_preset = ""
    preset_editor: PresetEditor | None = None
    editing_section_index: int = -1
    editing_exercise_index: int = -1
    # True when metrics being entered correspond to a newly completed set
    record_new_set = False
    # Incremented whenever an exercise is added, edited or deleted
    exercise_library_version: int = 0

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

        # ensure metric input doesn't accidentally advance sets
        self.record_new_set = False

    def mark_set_complete(self):
        if self.workout_session:
            self.workout_session.mark_set_completed()


if __name__ == "__main__":
    WorkoutApp().run()
