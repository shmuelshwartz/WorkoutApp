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


if os.name == "nt" or sys.platform.startswith("win"):
    Window.size = (280, 280 * (20 / 9))

# Order of fields for metric editing popups
METRIC_FIELD_ORDER = [
    "name",
    "description",
    "type",
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






        if self.selected_item:
            self.selected_item.md_bg_color = (0, 0, 0, 0)
            self.selected_item.theme_text_color = "Primary"
        self.selected_item = item
        self.selected_item.md_bg_color = self._selected_color
        self.selected_item.theme_text_color = "Custom"
        self.selected_item.text_color = self._selected_text_color
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


class AddMetricPopup(MDDialog):
    """Popup dialog for choosing an action, selecting metrics or creating a new one."""

    def __init__(self, screen: "EditExerciseScreen", mode: str = "select", **kwargs):
        self.screen = screen
        self.mode = mode

        if mode == "select":
            content, buttons, title = self._build_select_widgets()
        elif mode == "new":
            content, buttons, title = self._build_new_metric_widgets()
        else:  # initial choice
            content, buttons, title = self._build_choice_widgets()

        super().__init__(
            title=title, type="custom", content_cls=content, buttons=buttons, **kwargs
        )

    # ------------------------------------------------------------------
    # Building widgets for both modes
    # ------------------------------------------------------------------
    def _build_select_widgets(self):
        metrics = core.get_all_metric_types()
        existing = {m.get("name") for m in self.screen.exercise_obj.metrics}
        metrics = [
            m
            for m in metrics
            if m["name"] not in existing and m.get("scope") in ("set", "exercise")
        ]
        list_view = MDList()
        for m in metrics:
            item = OneLineListItem(text=m["name"])
            item.bind(on_release=lambda inst, name=m["name"]: self.add_metric(name))
            list_view.add_widget(item)

        scroll = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        scroll.add_widget(list_view)

        new_btn = MDRaisedButton(
            text="New Metric", on_release=self.show_new_metric_form
        )
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
                {
                    "name": "scope",
                    "options": ["session", "section", "exercise", "set"],
                },
                {"name": "is_required"},
            ]
        else:
            order_map = {field["name"]: field for field in schema}
            schema = [
                order_map[name] for name in METRIC_FIELD_ORDER if name in order_map
            ] + [field for field in schema if field["name"] not in METRIC_FIELD_ORDER]

        form = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
        )
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
                # Older versions of KivyMD do not accept the
                # ``hint_text_font_size`` kwarg. Set the property
                # after creation to avoid ``TypeError``.
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

        # Text box for enum values. This field only appears when the
        # metric's type is ``enum``.
        self.enum_values_field = MDTextField(
            hint_text="Enum Values (comma separated)",
            size_hint_y=None,
            height=default_height,
            multiline=True,
        )
        self.enum_values_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.enum_values_field)

        # Helper that toggles visibility based on ``type``.

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

            else:  # default to str
                allowed = string.ascii_letters + " ,"

            def _filter(value, from_undo):
                filtered = "".join(ch for ch in value if ch in allowed)
                return re.sub(r",\s+", ",", filtered)

            self.enum_values_field.input_filter = _filter

        if "type" in self.input_widgets:
            self.input_widgets["type"].bind(text=lambda *a: (update_enum_visibility(), update_enum_filter()))

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
        new_btn = MDRaisedButton(
            text="New Metric", on_release=self.show_new_metric_form
        )
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
        metric_type = self.input_widgets["type"].text


        if not name:
            errors.append("name")

        # check for duplicate metric name
        existing_names = {m.get("name") for m in self.screen.exercise_obj.metrics}
        if name and name in existing_names:
            errors.append("name")
            if hasattr(self.input_widgets["name"], "helper_text"):
                self.input_widgets["name"].helper_text = "Duplicate name"
                self.input_widgets["name"].helper_text_mode = "on_error"

        values = []
        if metric_type == "enum":

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
        metric_type = metric.pop("type", metric_type)
        metric["type"] = metric_type
        if values:
            metric["values"] = values

        db_path = DEFAULT_DB_PATH
        try:
            core.add_metric_type(
                metric["name"],
                metric["type"],
                metric["input_timing"],
                metric["scope"],
                metric.get("description", ""),
                metric.get("is_required", False),
                metric.get("values"),
                db_path=db_path,
            )
        except sqlite3.IntegrityError:
            self.input_widgets["name"].error = True
            return

        app = MDApp.get_running_app()
        if app:
            app.metric_library_version += 1

        self.screen.exercise_obj.add_metric(metric)
        self.screen.populate()
        self.screen.save_enabled = self.screen.exercise_obj.is_modified()
        self.show_metric_list()


class EditMetricPopup(MDDialog):
    """Popup for editing an existing metric."""

    def __init__(self, screen: "EditExerciseScreen", metric: dict, **kwargs):
        self.screen = screen
        self.metric = metric
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
                {
                    "name": "scope",
                    "options": ["session", "section", "exercise", "set"],
                },
                {"name": "is_required"},
            ]
        else:
            order_map = {field["name"]: field for field in schema}
            schema = [
                order_map[name] for name in METRIC_FIELD_ORDER if name in order_map
            ] + [field for field in schema if field["name"] not in METRIC_FIELD_ORDER]

        form = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
        )
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
                # handled separately below
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
                enable_auto_resize(widget)
                form.add_widget(widget)

            self.input_widgets[name] = widget

        # Text box for enum values shown when ``type`` is ``enum``
        self.enum_values_field = MDTextField(
            hint_text="Enum Values (comma separated)",
            size_hint_y=None,
            height=default_height,
            multiline=True,
        )
        self.enum_values_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.enum_values_field)

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

        # populate enum values
        metric_type = self.metric.get("type", "str")
        if metric_type == "enum":
            if self.enum_values_field.parent is None:
                form.add_widget(self.enum_values_field)
            values = ", ".join(self.metric.get("values", []))
            self.enum_values_field.text = values
        else:
            if self.enum_values_field.parent is not None:
                form.remove_widget(self.enum_values_field)

        def update_enum_visibility(*args):
            show = self.input_widgets["type"].text == "enum"
            has_parent = self.enum_values_field.parent is not None
            if show and not has_parent:
                form.add_widget(self.enum_values_field)
            elif not show and has_parent:
                form.remove_widget(self.enum_values_field)

        def update_enum_filter(*args):
            mtype = self.input_widgets["type"].text
            if mtype == "int":
                allowed = string.digits + ","
            elif mtype in ("float", "slider"):
                allowed = string.digits + ".,"
            else:
                allowed = string.ascii_letters + " ,"

            def _filter(value, from_undo):
                filtered = "".join(ch for ch in value if ch in allowed)
                return re.sub(r",\s+", ",", filtered)

            self.enum_values_field.input_filter = _filter

        if "type" in self.input_widgets:
            self.input_widgets["type"].bind(text=lambda *a: (update_enum_filter(), update_enum_visibility()))
            update_enum_visibility()
            update_enum_filter()

        layout = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        layout.add_widget(form)

        save_btn = MDRaisedButton(text="Save", on_release=self.save_metric)
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        buttons = [save_btn, cancel_btn]
        return layout, buttons, "Edit Metric"

    def save_metric(self, *args):
        """Update the metric on the exercise object with the new values."""
        errors = []
        updates = {}
        for key, widget in self.input_widgets.items():
            if isinstance(widget, MDCheckbox):
                updates[key] = bool(widget.active)
            else:
                updates[key] = widget.text

        if "type" in updates:
            updates["type"] = updates.pop("type")


        if self.enum_values_field.parent is not None:
            text = self.enum_values_field.text.strip()
            updates["values"] = [v.strip() for v in text.split(",") if v.strip()]

        name = updates.get("name", "").strip()

        if not name:
            errors.append("name")

        existing_names = {
            m.get("name")
            for m in self.screen.exercise_obj.metrics
            if m.get("name") != self.metric.get("name")
        }
        if name and name in existing_names:
            errors.append("name")
            if hasattr(self.input_widgets["name"], "helper_text"):
                self.input_widgets["name"].helper_text = "Duplicate name"
                self.input_widgets["name"].helper_text_mode = "on_error"

        red = (1, 0, 0, 1)
        for key, widget in self.input_widgets.items():
            if isinstance(widget, Spinner):
                widget.text_color = red if key in errors else (1, 1, 1, 1)
            elif isinstance(widget, MDTextField):
                widget.error = key in errors

        if errors:
            return

        def apply_updates():
            self.screen.exercise_obj.update_metric(self.metric["name"], **updates)
            self.dismiss()
            self.screen.populate()
            self.screen.save_enabled = self.screen.exercise_obj.is_modified()

        db_path = DEFAULT_DB_PATH
        app = MDApp.get_running_app()
        from_preset = (
            app
            and app.preset_editor
            and self.screen.section_index >= 0
            and self.screen.exercise_index >= 0
        )

        if from_preset:
            dialog = None

            def cancel_action(*a):
                if dialog:
                    dialog.dismiss()

            cb_type = MDCheckbox(
                group="apply", size_hint=(None, None), height="40dp", width="40dp"
            )
            cb_ex = MDCheckbox(
                group="apply", size_hint=(None, None), height="40dp", width="40dp"
            )
            cb_preset = MDCheckbox(
                group="apply",
                size_hint=(None, None),
                height="40dp",
                width="40dp",
                active=True,
            )
            row1 = MDBoxLayout(
                orientation="horizontal", spacing="8dp", size_hint_y=None, height="40dp"
            )
            row1.add_widget(cb_type)
            row1.add_widget(MDLabel(text="Set as default metric type", halign="left"))
            row2 = MDBoxLayout(
                orientation="horizontal", spacing="8dp", size_hint_y=None, height="40dp"
            )
            row2.add_widget(cb_ex)
            row2.add_widget(
                MDLabel(text="Apply to all instances of this exercise", halign="left")
            )
            row3 = MDBoxLayout(
                orientation="horizontal", spacing="8dp", size_hint_y=None, height="40dp"
            )
            row3.add_widget(cb_preset)
            row3.add_widget(MDLabel(text="Apply only to this preset", halign="left"))
            content = MDBoxLayout(
                orientation="vertical", spacing="8dp", size_hint_y=None
            )
            content.add_widget(row1)
            content.add_widget(row2)
            content.add_widget(row3)

            def on_save(*a):
                metric_saved = self.screen.exercise_obj.had_metric(self.metric["name"])
                if cb_type.active:
                    core.update_metric_type(
                        self.metric["name"],
                        mtype=updates.get("type"),
                        input_timing=updates.get("input_timing"),
                        scope=updates.get("scope"),
                        description=updates.get("description"),
                        is_required=updates.get("is_required"),
                        enum_values=updates.get("values"),
                        db_path=db_path,
                    )
                    if metric_saved:
                        core.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            db_path=db_path,
                        )
                elif cb_ex.active:
                    if metric_saved:
                        core.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            mtype=updates.get("type"),
                            input_timing=updates.get("input_timing"),
                            is_required=updates.get("is_required"),
                            scope=updates.get("scope"),
                            enum_values=updates.get("values"),
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            db_path=db_path,
                        )
                else:
                    preset_name = app.preset_editor.preset_name if app else ""
                    core.set_section_exercise_metric_override(
                        preset_name,
                        self.screen.section_index,
                        self.screen.exercise_obj.name,
                        self.metric["name"],
                        input_timing=updates.get("input_timing"),
                        is_required=bool(updates.get("is_required")),
                        scope=updates.get("scope", "set"),
                        enum_values=updates.get("values"),
                        db_path=db_path,
                    )
                cancel_action()
                apply_updates()

            dialog = MDDialog(
                title="Save Metric",
                type="custom",
                content_cls=content,
                buttons=[
                    MDRaisedButton(text="Cancel", on_release=cancel_action),
                    MDRaisedButton(text="Save", on_release=on_save),
                ],
            )

            def _on_open(instance):
                if hasattr(instance, "ids") and "buttons" in instance.ids:
                    instance.ids.buttons.orientation = (
                        "vertical" if Window.width < dp(400) else "horizontal"
                    )

            dialog.bind(on_open=_on_open)
            dialog.open()
        elif core.is_metric_type_user_created(self.metric["name"], db_path=db_path):
            dialog = None

            def cancel_action(*a):
                if dialog:
                    dialog.dismiss()

            checkbox = MDCheckbox(size_hint=(None, None), height="40dp", width="40dp")
            label = MDLabel(
                text="Apply changes to all exercises using this metric",
                halign="left",
            )
            content = MDBoxLayout(
                orientation="horizontal",
                spacing="8dp",
                size_hint_y=None,
                height="40dp",
            )
            content.add_widget(checkbox)
            content.add_widget(label)

            def on_save(*a):
                metric_saved = self.screen.exercise_obj.had_metric(self.metric["name"])
                if checkbox.active:
                    core.update_metric_type(
                        self.metric["name"],
                        mtype=updates.get("type"),
                        input_timing=updates.get("input_timing"),
                        scope=updates.get("scope"),
                        description=updates.get("description"),
                        is_required=updates.get("is_required"),
                        is_user_created=self.metric.get("is_user_created"),
                        db_path=db_path,
                    )
                    if metric_saved:
                        core.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            db_path=db_path,
                        )
                else:
                    if metric_saved:
                        core.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            mtype=updates.get("type"),
                            input_timing=updates.get("input_timing"),
                            is_required=updates.get("is_required"),
                            scope=updates.get("scope"),
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            db_path=db_path,
                        )
                cancel_action()
                apply_updates()

            dialog = MDDialog(
                title="Save Metric",
                type="custom",
                content_cls=content,
                buttons=[
                    MDRaisedButton(text="Cancel", on_release=cancel_action),
                    MDRaisedButton(text="Save", on_release=on_save),
                ],
            )

            def _on_open(instance):
                if hasattr(instance, "ids") and "buttons" in instance.ids:
                    instance.ids.buttons.orientation = (
                        "vertical" if Window.width < dp(400) else "horizontal"
                    )

            dialog.bind(on_open=_on_open)
            dialog.open()
        else:
            apply_updates()


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
            self.input_widgets["type"].bind(text=lambda *a: (update_enum_filter(), update_enum_visibility()))
            update_enum_visibility()
            update_enum_filter()

        layout = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        info_box = None
        if self.metric and not self.is_user_created:
            has_copy = False
            if self.screen and self.metric_name:
                for m in self.screen.all_metrics or []:
                    if m.get("name") == self.metric_name and m.get("is_user_created"):
                        has_copy = True
                        break
            if has_copy:
                msg = (
                    "Built-in metric. Saving will overwrite your existing user copy."
                )
            else:
                msg = (
                    "Built-in metric. Saving will create a user copy you can edit."
                )
            info_box = MDLabel(text=msg, halign="center")
        elif self.metric and self.is_user_created:
            msg = (
                "Changes here update the metric defaults. Exercises using this "
                "metric without overrides will reflect the changes."
            )
            info_box = MDLabel(text=msg, halign="center")
        layout.add_widget(form)
        buttons = [
            MDRaisedButton(text="Save", on_release=self.save_metric),
            MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss()),
        ]
        if info_box:
            wrapper = MDBoxLayout(
                orientation="vertical",
                spacing="8dp",
                size_hint_y=None,
            )
            wrapper.bind(minimum_height=wrapper.setter("height"))
            wrapper.add_widget(info_box)
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
    exercise_sets = NumericProperty(DEFAULT_SETS_PER_EXERCISE)
    exercise_rest = NumericProperty(DEFAULT_REST_DURATION)
    section_length = NumericProperty(0)

    def switch_tab(self, tab: str):
        """Switch between available tabs."""
        if tab in ("metrics", "details", "config"):
            self.current_tab = tab
            if "exercise_tabs" in self.ids:
                self.ids.exercise_tabs.current = tab

    def can_go_prev(self) -> bool:
        app = MDApp.get_running_app()
        if (
            not app
            or not app.preset_editor
            or self.section_index < 0
            or self.exercise_index <= 0
        ):
            return False
        return True

    def can_go_next(self) -> bool:
        app = MDApp.get_running_app()
        if not app or not app.preset_editor or self.section_index < 0:
            return False
        sec = app.preset_editor.sections[self.section_index]
        return self.exercise_index < len(sec["exercises"]) - 1

    def _navigate_to(self, new_index: int) -> None:
        app = MDApp.get_running_app()
        if not app or not app.preset_editor or self.section_index < 0:
            return
        sec = app.preset_editor.sections[self.section_index]
        if new_index < 0 or new_index >= len(sec["exercises"]):
            return
        self.exercise_index = new_index
        self.exercise_name = sec["exercises"][new_index]["name"]
        self._load_exercise()

    def _confirm_navigation(self, new_index: int) -> None:
        dialog = None

        def do_nav(*args):
            if dialog:
                dialog.dismiss()
            self._navigate_to(new_index)

        dialog = MDDialog(
            title="Discard Changes?",
            text="You have unsaved changes. Discard them?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Discard", on_release=do_nav),
            ],
        )
        dialog.open()

    def go_prev_exercise(self) -> None:
        if not self.can_go_prev():
            return
        if self.save_enabled:
            self._confirm_navigation(self.exercise_index - 1)
        else:
            self._navigate_to(self.exercise_index - 1)

    def go_next_exercise(self) -> None:
        if not self.can_go_next():
            return
        if self.save_enabled:
            self._confirm_navigation(self.exercise_index + 1)
        else:
            self._navigate_to(self.exercise_index + 1)

    def on_pre_enter(self, *args):
        if self.previous_screen == "edit_preset":
            self.switch_tab("config")
        else:
            self.switch_tab("metrics")
        if os.environ.get("KIVY_UNITTEST"):
            self._load_exercise()
        else:
            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(lambda dt: self._load_exercise(), 0)
        return super().on_pre_enter(*args)

    def _load_exercise(self):
        db_path = DEFAULT_DB_PATH
        self.exercise_obj = core.Exercise(
            self.exercise_name,
            db_path=db_path,
            is_user_created=self.is_user_created,
        )
        self.is_user_created = self.exercise_obj.is_user_created
        self.exercise_name = self.exercise_obj.name
        self.exercise_description = self.exercise_obj.description
        if self.section_index >= 0 and self.exercise_index >= 0:
            app = MDApp.get_running_app()
            if app.preset_editor and self.section_index < len(
                app.preset_editor.sections
            ):
                exercises = app.preset_editor.sections[self.section_index]["exercises"]
                self.section_length = len(exercises)
                if self.exercise_index < len(exercises):
                    ex = exercises[self.exercise_index]
                    self.exercise_sets = ex.get("sets", DEFAULT_SETS_PER_EXERCISE)
                    self.exercise_rest = ex.get("rest", DEFAULT_REST_DURATION)
            else:
                self.section_length = 0
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
            edit_btn.bind(
                on_release=lambda inst, metric=m: self.open_edit_metric_popup(metric)
            )
            row.add_widget(edit_btn)
            remove_btn = MDIconButton(
                icon="delete",
                theme_text_color="Custom",
                text_color=(1, 0, 0, 1),
            )
            remove_btn.bind(
                on_release=lambda inst, name=m.get(
                    "name", ""
                ): self.confirm_remove_metric(name)
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

    def update_sets(self, val: str):
        try:
            self.exercise_sets = int(val)
        except ValueError:
            return
        self.save_enabled = True

    def update_rest(self, val: str):
        try:
            self.exercise_rest = int(val)
        except ValueError:
            return
        self.save_enabled = True

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

        # Only update the preset if editing from preset editor
        app = MDApp.get_running_app()
        if (
            app
            and self.section_index >= 0
            and self.exercise_index >= 0
            and app.preset_editor
        ):
            update_in_preset = True
        else:
            update_in_preset = False

        if not self.exercise_obj.is_modified():
            if update_in_preset:
                app.preset_editor.update_exercise(
                    self.section_index,
                    self.exercise_index,
                    sets=self.exercise_sets,
                    rest=self.exercise_rest,
                )
            self.save_enabled = False
            return

        # ------------------------------------------------------------------
        # Validation
        # ------------------------------------------------------------------
        name = self.exercise_obj.name.strip()

        db_path = DEFAULT_DB_PATH

        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        if not name:
            if self.name_field:
                self.name_field.error = True
            conn.close()
            dialog = MDDialog(
                title="Error",
                text="Name cannot be empty",
                buttons=[
                    MDRaisedButton(text="OK", on_release=lambda *a: dialog.dismiss())
                ],
            )
            dialog.open()
            return

        cursor.execute(
            "SELECT 1 FROM library_exercises WHERE name = ? AND is_user_created = 1",
            (name,),
        )
        exists = cursor.fetchone()
        original_name = None
        if self.exercise_obj._original:
            original_name = self.exercise_obj._original.get("name")
        if exists and (original_name != name or not self.exercise_obj.is_user_created):
            if self.name_field:
                self.name_field.error = True
            conn.close()
            dialog = MDDialog(
                title="Error",
                text="Duplicate name",
                buttons=[
                    MDRaisedButton(text="OK", on_release=lambda *a: dialog.dismiss())
                ],
            )
            dialog.open()
            return

        msg = "Save changes to this exercise?"
        if not self.exercise_obj.is_user_created:
            cursor.execute(
                "SELECT 1 FROM library_exercises WHERE name = ? AND is_user_created = 1",
                (self.exercise_obj.name,),
            )
            exists = cursor.fetchone()
            if exists:
                msg = f"A user-defined copy of {self.exercise_obj.name} exists and will be overwritten."
            else:
                msg = f"{self.exercise_obj.name} is predefined. A user-defined copy will be created."
        conn.close()

        dialog = None

        def do_save(*args):
            update_library = (not update_in_preset) or (checkbox and checkbox.active)
            if update_library:
                core.save_exercise(self.exercise_obj)
                if app:
                    app.exercise_library_version += 1
            if update_in_preset:
                app.preset_editor.update_exercise(
                    self.section_index,
                    self.exercise_index,
                    sets=self.exercise_sets,
                    rest=self.exercise_rest,
                )
                if not update_library:
                    preset_name = app.preset_editor.preset_name
                    orig = {
                        m.get("name"): m
                        for m in (self.exercise_obj._original or {}).get("metrics", [])
                    }
                    current = {m.get("name"): m for m in self.exercise_obj.metrics}
                    for name, metric in current.items():
                        old = orig.get(name)
                        if old is None or any(
                            metric.get(field) != old.get(field)
                            for field in ("input_timing", "is_required", "scope")
                        ):
                            core.set_section_exercise_metric_override(
                                preset_name,
                                self.section_index,
                                self.exercise_obj.name,
                                name,
                                input_timing=metric.get("input_timing"),
                                is_required=bool(metric.get("is_required")),
                                scope=metric.get("scope", "set"),
                            )

                    removed = [name for name in orig if name not in current]
                    if removed:
                        db_path = (
                            Path(__file__).resolve().parent / "data" / "workout.db"
                        )
                        conn = sqlite3.connect(str(db_path))
                        cur = conn.cursor()
                        cur.execute(
                            "SELECT id FROM preset_presets WHERE name = ?",
                            (preset_name,),
                        )
                        row = cur.fetchone()
                        if row:
                            preset_id = row[0]
                            cur.execute(
                                "SELECT id FROM preset_preset_sections WHERE preset_id = ? ORDER BY position",
                                (preset_id,),
                            )
                            sections = cur.fetchall()
                            if 0 <= self.section_index < len(sections):
                                section_id = sections[self.section_index][0]
                                cur.execute(
                                    """SELECT id FROM preset_section_exercises WHERE section_id = ? AND exercise_name = ? ORDER BY position LIMIT 1""",
                                    (section_id, self.exercise_obj.name),
                                )
                                se_row = cur.fetchone()
                                if se_row:
                                    se_id = se_row[0]
                                    for mname in removed:
                                        cur.execute(
                                            "DELETE FROM preset_exercise_metrics WHERE section_exercise_id = ? AND metric_name = ?",
                                            (se_id, mname),
                                        )
                                    conn.commit()
                        conn.close()

            self.save_enabled = False
            if dialog:
                dialog.dismiss()

        if update_in_preset:
            label_text = (
                "Update exercise in library"
                if self.exercise_obj.is_user_created
                else "Create editable copy in library"
            )
            msg = (
                "Changes will apply only to this preset."
                if self.exercise_obj.is_user_created
                else f"{self.exercise_obj.name} is predefined and cannot be edited."
            )
            checkbox = MDCheckbox(size_hint=(None, None), height="40dp", width="40dp")
            label = MDLabel(text=label_text, halign="left")
            content = MDBoxLayout(
                orientation="horizontal",
                spacing="8dp",
                size_hint_y=None,
                height="40dp",
            )
            content.add_widget(checkbox)
            content.add_widget(label)
            dialog = MDDialog(
                title="Confirm Save",
                type="custom",
                text=msg,
                content_cls=content,
                buttons=[
                    MDRaisedButton(
                        text="Cancel", on_release=lambda *a: dialog.dismiss()
                    ),
                    MDRaisedButton(text="Save", on_release=do_save),
                ],
            )
        else:
            checkbox = None
            dialog = MDDialog(
                title="Confirm Save",
                text=msg,
                buttons=[
                    MDRaisedButton(
                        text="Cancel", on_release=lambda *a: dialog.dismiss()
                    ),
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
