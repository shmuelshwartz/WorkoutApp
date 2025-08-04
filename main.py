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
from ui.screens.preset_detail_screen import PresetDetailScreen
from ui.screens.preset_overview_screen import PresetOverviewScreen
from pathlib import Path
import os
import sys
import re
import json

from ui.screens import ExerciseLibraryScreen

# Import core so we can always reference the up-to-date WORKOUT_PRESETS list
import core
from core import (
    WorkoutSession,
    load_workout_presets,
    get_metrics_for_exercise,
    PresetEditor,
    DEFAULT_SETS_PER_EXERCISE,
    DEFAULT_REST_DURATION,
    DEFAULT_DB_PATH,
)
from ui.screens.metric_input_screen import MetricInputScreen
from ui.screens.edit_exercise_screen import EditExerciseScreen

from ui.screens.rest_screen import RestScreen


# Load workout presets from the database at startup
load_workout_presets(DEFAULT_DB_PATH)
import time
import math

from kivy.core.window import Window
import string
import sqlite3
from ui.screens.presets_screen import PresetsScreen
from ui.screens.workout_active_screen import WorkoutActiveScreen
from ui.screens.edit_preset_screen import (
    EditPresetScreen,
    SectionWidget,
    SelectedExerciseItem,
    ExerciseSelectionPanel,
    AddPresetMetricPopup,
    AddSessionMetricPopup,
)

from ui.screens.workout_summary_screen import WorkoutSummaryScreen
from ui.popups import AddMetricPopup, EditMetricPopup, METRIC_FIELD_ORDER


if os.name == "nt" or sys.platform.startswith("win"):
    Window.size = (280, 280 * (20 / 9))


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


class EditMetricTypePopup(MDDialog):
    """Popup for editing or creating metric types from the library."""

    def __init__(
        self,
        screen: "ExerciseLibraryScreen",
        metric_name: str | None,
        is_user_created: bool,
        **kwargs,
    ):
        self.screen = screen
        self.metric_name = metric_name
        self.is_user_created = is_user_created
        self.metric = None
        if metric_name:
            for m in screen.all_metrics or []:
                if (
                    m["name"] == metric_name
                    and m.get("is_user_created", False) == is_user_created
                ):
                    self.metric = m
                    break
        content, buttons, title = self._build_widgets()
        super().__init__(
            title=title, type="custom", content_cls=content, buttons=buttons, **kwargs
        )

    def _build_widgets(self):
        default_height = dp(48)
        self.input_widgets = {}
        schema = core.get_metric_type_schema()
        if not schema:
            schema = [
                {"name": "name"},
                {"name": "description"},
                {
                    "name": "type",
                    "options": ["int", "float", "str", "bool", "enum", "slider"],
                },
                {
                    "name": "input_timing",
                    "options": [
                        "preset",
                        "pre_session",
                        "post_session",
                        "pre_set",
                        "post_set",
                    ],
                },
                {"name": "scope", "options": ["session", "section", "exercise", "set"]},
                {"name": "is_required"},
            ]
        else:
            order_map = {field["name"]: field for field in schema}
            schema = [
                order_map[name] for name in METRIC_FIELD_ORDER if name in order_map
            ] + [field for field in schema if field["name"] not in METRIC_FIELD_ORDER]

        form = MDBoxLayout(orientation="vertical", spacing="8dp", size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))

        def enable_auto_resize(text_field: MDTextField):
            text_field.bind(
                text=lambda inst, val: setattr(
                    inst, "height", max(default_height, inst.minimum_height)
                )
            )

        for field in schema:
            name = field["name"]
            if name == "enum_values_json":
                # handled separately via ``enum_values_field``
                continue
            options = field.get("options")
            if name == "is_required":
                row = MDBoxLayout(
                    orientation="horizontal", size_hint_y=None, height="40dp"
                )
                widget = MDCheckbox(size_hint_y=None, height=default_height)
                row.add_widget(widget)
                row.add_widget(MDLabel(text="Required"))
                form.add_widget(row)
            elif options:
                widget = Spinner(
                    text=options[0],
                    values=options,
                    size_hint_y=None,
                    height=default_height,
                )
                form.add_widget(widget)
            else:
                widget = MDTextField(
                    hint_text=name.replace("_", " ").title(),
                    size_hint_y=None,
                    height=default_height,
                    multiline=True,
                )
                widget.hint_text_font_size = "12sp"
                enable_auto_resize(widget)
                form.add_widget(widget)
            self.input_widgets[name] = widget

        # Text box for enum values. Only shown for manual enum metrics
        self.enum_values_field = MDTextField(
            hint_text="Enum Values (comma separated)",
            size_hint_y=None,
            height=default_height,
            multiline=True,
        )
        self.enum_values_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.enum_values_field)

        if self.metric:
            for key, widget in self.input_widgets.items():
                if key not in self.metric:
                    continue
                val = self.metric[key]
                if isinstance(widget, MDCheckbox):
                    widget.active = bool(val)
                elif isinstance(widget, Spinner):
                    if val in widget.values:
                        widget.text = val
                else:
                    widget.text = str(val)

        # show enum values if current metric uses enum type
        if self.metric and self.metric.get("type") == "enum":
            if self.enum_values_field.parent is None:
                form.add_widget(self.enum_values_field)
            values = []
            if "values" in self.metric and self.metric["values"]:
                values = self.metric["values"]
            elif self.metric.get("enum_values_json"):
                try:
                    values = json.loads(self.metric["enum_values_json"])
                except Exception:
                    values = []
            self.enum_values_field.text = ", ".join(values)

        def update_enum_visibility(*args):
            show = self.input_widgets["type"].text == "enum"
            has_parent = self.enum_values_field.parent is not None
            if show and not has_parent:
                form.add_widget(self.enum_values_field)
            elif not show and has_parent:
                form.remove_widget(self.enum_values_field)

        def update_enum_filter(*args):
            metric_type = self.input_widgets["type"].text
            if metric_type == "int":
                allowed = string.digits + ","
            elif metric_type == "float":
                allowed = string.digits + ",."
            else:
                allowed = string.ascii_letters + " ,"

            def _filter(value, from_undo):
                filtered = "".join(ch for ch in value if ch in allowed)
                return re.sub(r",\s+", ",", filtered)

            self.enum_values_field.input_filter = _filter

        if "type" in self.input_widgets:
            self.input_widgets["type"].bind(
                text=lambda *a: (update_enum_filter(), update_enum_visibility())
            )
            update_enum_visibility()
            update_enum_filter()

        layout = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        info_widgets = []
        if self.metric and not self.is_user_created:
            has_copy = False
            if self.screen and self.metric_name:
                for m in self.screen.all_metrics or []:
                    if m.get("name") == self.metric_name and m.get("is_user_created"):
                        has_copy = True
                        break
            if has_copy:
                msg = "Built-in metric. Saving will overwrite your existing user copy."
            else:
                msg = "Built-in metric. Saving will create a user copy you can edit."
            info_widgets.append(MDLabel(text=msg, halign="center"))
        elif self.metric and self.is_user_created:
            msg = (
                "Changes here update the metric defaults. Exercises using this "
                "metric without overrides will reflect the changes."
            )
            info_widgets.append(MDLabel(text=msg, halign="center"))

        if self.metric:
            affected = core.find_exercises_using_metric_type(self.metric_name)
            if affected:
                label = MDLabel(
                    text=f"Affects {len(affected)} exercises", halign="center"
                )
                info_widgets.append(label)
        layout.add_widget(form)
        buttons = [
            MDRaisedButton(text="Save", on_release=self.save_metric),
            MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss()),
        ]
        if info_widgets:
            wrapper = MDBoxLayout(
                orientation="vertical",
                spacing="8dp",
                size_hint_y=None,
            )
            wrapper.bind(minimum_height=wrapper.setter("height"))
            for widget in info_widgets:
                wrapper.add_widget(widget)
            wrapper.add_widget(layout)
            return wrapper, buttons, "Edit Metric"
        return layout, buttons, "Edit Metric" if self.metric else "New Metric"

    def save_metric(self, *args):
        data = {}
        for key, widget in self.input_widgets.items():
            if isinstance(widget, MDCheckbox):
                data[key] = bool(widget.active)
            else:
                data[key] = widget.text

        enum_values = None
        if self.enum_values_field.parent is not None:
            text = self.enum_values_field.text.strip()
            if text:
                enum_values = [v.strip() for v in text.split(",") if v.strip()]

        db_path = DEFAULT_DB_PATH
        if self.metric and self.is_user_created:
            core.update_metric_type(
                self.metric_name,
                mtype=data.get("type"),
                input_timing=data.get("input_timing"),
                scope=data.get("scope"),
                description=data.get("description"),
                is_required=data.get("is_required"),
                enum_values=enum_values,
                is_user_created=True,
                db_path=db_path,
            )
        else:
            try:
                core.add_metric_type(
                    data.get("name"),
                    data.get("type"),
                    data.get("input_timing"),
                    data.get("scope"),
                    data.get("description", ""),
                    data.get("is_required", False),
                    enum_values,
                    db_path=db_path,
                )
            except sqlite3.IntegrityError:
                if "name" in self.input_widgets:
                    self.input_widgets["name"].error = True
                return

        app = MDApp.get_running_app()
        if app:
            app.metric_library_version += 1
        self.screen.all_metrics = None
        self.screen.populate()
        self.dismiss()


class WorkoutApp(MDApp):
    workout_session = None
    selected_preset = ""
    preset_editor: PresetEditor | None = None
    editing_section_index: int = -1
    editing_exercise_index: int = -1
    # True when metrics being entered correspond to a newly completed set
    record_new_set = False
    # True when entering metrics for the upcoming set
    record_pre_set = False
    # Incremented whenever an exercise is added, edited or deleted
    exercise_library_version: int = 0
    # Incremented when a metric type is added or edited
    metric_library_version: int = 0

    def build(self):
        return Builder.load_file(str(Path(__file__).with_name("main.kv")))

    def init_preset_editor(self, force_reload: bool = False):
        """Create or reload the ``PresetEditor`` for the selected preset."""

        db_path = DEFAULT_DB_PATH
        if self.selected_preset:
            if (
                not self.preset_editor
                or self.preset_editor.preset_name != self.selected_preset
            ):
                if self.preset_editor:
                    self.preset_editor.close()
                self.preset_editor = PresetEditor(self.selected_preset, db_path)
            elif force_reload:
                self.preset_editor.load(self.selected_preset)
        else:
            if self.preset_editor:
                self.preset_editor.close()
            self.preset_editor = PresetEditor(db_path=db_path)

    def start_new_preset(self):
        """Reset state so the editor loads a blank preset."""
        if self.preset_editor:
            self.preset_editor.close()
            self.preset_editor = None
        self.selected_preset = ""

    def start_workout(self, preset_name: str):
        """Initialize a :class:`WorkoutSession` for ``preset_name``.

        The entire preset is loaded from the database when the session is
        created so no further database access is required while the workout
        is in progress.
        """

        if preset_name:
            self.workout_session = WorkoutSession(preset_name, db_path=DEFAULT_DB_PATH)
        else:
            self.workout_session = None

        # ensure metric input doesn't accidentally advance sets
        self.record_new_set = False

    def mark_set_complete(self):
        if self.workout_session:
            self.workout_session.mark_set_completed()


if __name__ == "__main__":
    WorkoutApp().run()
