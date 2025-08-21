# Popup dialog classes moved from main.py
from __future__ import annotations

from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider

import string
import re
import sqlite3

from core import DEFAULT_DB_PATH
from backend.presets import find_presets_using_exercise, apply_exercise_changes_to_presets
from backend import metrics

# Order of fields for metric editing popups
METRIC_FIELD_ORDER = [
    "name",
    "description",
    "type",
    "input_timing",
    "scope",
    "is_required",
]


class AddMetricPopup(MDDialog):
    """Popup dialog for selecting or creating metrics."""

    def __init__(
        self,
        screen: "EditExerciseScreen",
        popup_mode: str = "select",
        mode: str = "library",
        **kwargs,
    ):
        self.screen = screen
        self.mode = mode
        self.popup_mode = popup_mode
        # Make the popup occupy most of the display on phones. ``MDDialog``
        # ignores ``size_hint_y`` so an explicit height is provided instead of
        # using :func:`Clock.schedule_once` to set it later.
        kwargs.setdefault("size_hint", (0.95, None))
        kwargs.setdefault("height", Window.height * 0.9)
        if self.mode == "session":
            content = MDBoxLayout()
            close_btn = MDRaisedButton(
                text="Close", on_release=lambda *a: self.dismiss()
            )
            super().__init__(
                title="Metrics Locked",
                type="custom",
                content_cls=content,
                buttons=[close_btn],
                **kwargs,
            )
            return

        if popup_mode == "select":
            content, buttons, title = self._build_select_widgets()
        elif popup_mode == "new":
            content, buttons, title = self._build_new_metric_widgets()
        else:
            content, buttons, title = self._build_choice_widgets()

        super().__init__(
            title=title, type="custom", content_cls=content, buttons=buttons, **kwargs
        )

    # ------------------------------------------------------------------
    # Building widgets for both modes
    # ------------------------------------------------------------------
    def _build_select_widgets(self):
        metric_types = metrics.get_all_metric_types()
        existing = {m.get("name") for m in self.screen.exercise_obj.metrics}
        metric_types = [
            m
            for m in metric_types
            if m["name"] not in existing and m.get("scope") in ("set", "exercise")
        ]
        list_view = MDList(adaptive_height=True)
        # Bind ``minimum_height`` so the list expands with its children. The
        # list itself has no vertical size hint so the surrounding ScrollView
        # can determine its height.
        list_view.bind(minimum_height=list_view.setter("height"))
        for m in metric_types:
            item = OneLineListItem(text=m["name"])
            item.bind(on_release=lambda inst, name=m["name"]: self.add_metric(name))
            list_view.add_widget(item)
        # Occupy most of the dialog and keep buttons visible by constraining
        # the scroll height.
        scroll = ScrollView(
            do_scroll_y=True, size_hint=(1, None), height=Window.height * 0.7
        )
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

        schema = metrics.get_metric_type_schema()
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

        # Text box for enum values. This field only appears when the metric type is ``enum``.
        self.enum_values_field = MDTextField(
            hint_text="Enum Values (comma separated)",
            size_hint_y=None,
            height=default_height,
            multiline=True,
        )
        self.enum_values_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.enum_values_field)

        self.value_field = MDTextField(
            hint_text="Value",
            size_hint_y=None,
            height=default_height,
            multiline=True,
        )
        self.value_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.value_field)

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
                text=lambda *a: (update_enum_visibility(), update_enum_filter())
            )
            update_enum_visibility()
            update_enum_filter()

        # Fill the dialog while keeping action buttons visible
        layout = ScrollView(
            do_scroll_y=True, size_hint=(1, None), height=Window.height * 0.7
        )
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
        popup = AddMetricPopup(self.screen, popup_mode="new", mode=self.mode)
        popup.open()

    def show_metric_list(self, *args):
        self.dismiss()
        popup = AddMetricPopup(self.screen, popup_mode="select", mode=self.mode)
        popup.open()

    def add_metric(self, name, *args):
        metric_defs = metrics.get_all_metric_types()
        for m in metric_defs:
            if m["name"] == name:
                self.screen.exercise_obj.add_metric(m)
                break
        self.dismiss()
        self.screen.populate()
        self.screen.save_enabled = self.screen.exercise_obj.is_modified()

    def save_metric(self, *args):
        errors = []

        name = self.input_widgets["name"].text.strip()
        metric_type = self.input_widgets["type"].text

        if not name:
            errors.append("name")

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
            metrics.add_metric_type(
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

    def __init__(
        self,
        screen: "EditExerciseScreen",
        metric: dict,
        mode: str = "library",
        **kwargs,
    ):
        self.screen = screen
        self.metric = metric
        self.mode = mode
        # Ensure dialog uses most of the screen on small devices. ``size_hint_y``
        # alone has no effect for :class:`MDDialog`, so we also specify the
        # height directly.
        kwargs.setdefault("size_hint", (0.95, None))
        kwargs.setdefault("height", Window.height * 0.9)
        if self.mode == "session":
            content = MDBoxLayout()
            close_btn = MDRaisedButton(
                text="Close", on_release=lambda *a: self.dismiss()
            )
            super().__init__(
                title="Metrics Locked",
                type="custom",
                content_cls=content,
                buttons=[close_btn],
                **kwargs,
            )
            return
        content, buttons, title = self._build_widgets()
        super().__init__(
            title=title, type="custom", content_cls=content, buttons=buttons, **kwargs
        )

    def _build_widgets(self):
        default_height = dp(48)
        self.input_widgets = {}

        schema = metrics.get_metric_type_schema()
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

        self.enum_values_field = MDTextField(
            hint_text="Enum Values (comma separated)",
            size_hint_y=None,
            height=default_height,
            multiline=True,
        )
        self.enum_values_field.hint_text_font_size = "12sp"
        enable_auto_resize(self.enum_values_field)

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

        metric_type = self.metric.get("type", "str")
        if metric_type == "enum":
            if self.enum_values_field.parent is None:
                form.add_widget(self.enum_values_field)
            values = ", ".join(self.metric.get("values", []))
            self.enum_values_field.text = values
        else:
            if self.enum_values_field.parent is not None:
                form.remove_widget(self.enum_values_field)

        self.value_field.text = self.metric.get("value", "")

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

        def update_value_visibility(*args):
            # Value defaults are currently supported only when editing an
            # exercise from the library. Other contexts will expose this field
            # in a future iteration.
            show = (
                self.mode == "library"
                and getattr(self.screen, "previous_screen", "") == "exercise_library"
                and "input_timing" in self.input_widgets
                and self.input_widgets["input_timing"].text == "library"
            )
            has_parent = self.value_field.parent is not None
            if show and not has_parent:
                form.add_widget(self.value_field)
            elif not show and has_parent:
                form.remove_widget(self.value_field)

        if "type" in self.input_widgets:
            self.input_widgets["type"].bind(
                text=lambda *a: (update_enum_filter(), update_enum_visibility())
            )
            update_enum_visibility()
            update_enum_filter()

        if "input_timing" in self.input_widgets:
            self.input_widgets["input_timing"].bind(
                text=lambda *a: update_value_visibility()
            )
            update_value_visibility()

        # Allow the form to scroll within the dialog and prevent clipping
        layout = ScrollView(do_scroll_y=True, size_hint=(1, 1))
        layout.add_widget(form)

        save_btn = MDRaisedButton(text="Save", on_release=self.save_metric)
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        buttons = [save_btn, cancel_btn]
        return layout, buttons, "Edit Metric"

    def save_metric(self, *args):
        errors = []
        updates = {}
        for key, widget in self.input_widgets.items():
            if isinstance(widget, MDCheckbox):
                updates[key] = bool(widget.active)
            else:
                updates[key] = widget.text

        if self.value_field.parent is not None:
            text = self.value_field.text.strip()
            if not text:
                errors.append("value")
            updates["value"] = text

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
        if self.value_field.parent is not None:
            self.value_field.error = "value" in errors

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
                    metrics.update_metric_type(
                        self.metric["name"],
                        mtype=updates.get("type"),
                        input_timing=updates.get("input_timing"),
                        scope=updates.get("scope"),
                        description=updates.get("description"),
                        is_required=updates.get("is_required"),
                        enum_values=updates.get("values"),
                        db_path=db_path,
                    )
                    # Ensure overrides are updated if the metric already existed
                    if metric_saved:
                        metrics.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            value=updates.get("value"),
                            db_path=db_path,
                        )
                elif cb_ex.active:
                    if metric_saved:
                        metrics.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            mtype=updates.get("type"),
                            input_timing=updates.get("input_timing"),
                            is_required=updates.get("is_required"),
                            scope=updates.get("scope"),
                            enum_values=updates.get("values"),
                            value=updates.get("value"),
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            db_path=db_path,
                        )
                else:
                    preset_name = app.preset_editor.preset_name if app else ""
                    metrics.set_section_exercise_metric_override(
                        preset_name,
                        self.screen.section_index,
                        self.screen.exercise_obj.name,
                        self.metric["name"],
                        input_timing=updates.get("input_timing"),
                        is_required=bool(updates.get("is_required")),
                        scope=updates.get("scope", "set"),
                        enum_values=updates.get("values"),
                        value=updates.get("value"),  # future support
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
        elif self.screen.previous_screen == "exercise_library":
            dialog = None

            def cancel_action(*a):
                if dialog:
                    dialog.dismiss()

            rows = []
            cb_default = None
            if metrics.is_metric_type_user_created(
                self.metric["name"], db_path=db_path
            ) and metrics.uses_default_metric(
                self.screen.exercise_obj.name,
                self.metric["name"],
                is_user_created=self.screen.exercise_obj.is_user_created,
                db_path=db_path,
            ):
                cb_default = MDCheckbox(
                    size_hint=(None, None), height="40dp", width="40dp"
                )
                row = MDBoxLayout(
                    orientation="horizontal",
                    spacing="8dp",
                    size_hint_y=None,
                    height="40dp",
                )
                row.add_widget(cb_default)
                row.add_widget(
                    MDLabel(
                        text="Make this the new default metric for all exercises",
                        halign="left",
                    )
                )
                rows.append(row)

            presets = find_presets_using_exercise(
                self.screen.exercise_obj.name, db_path=db_path
            )
            cb_presets = None
            if presets:
                cb_presets = MDCheckbox(
                    size_hint=(None, None), height="40dp", width="40dp"
                )
                row = MDBoxLayout(
                    orientation="horizontal",
                    spacing="8dp",
                    size_hint_y=None,
                    height="40dp",
                )
                row.add_widget(cb_presets)
                row.add_widget(
                    MDLabel(
                        text="Apply this metric change to all presets that use this exercise",
                        halign="left",
                    )
                )
                rows.append(row)

            if rows:
                content = MDBoxLayout(
                    orientation="vertical", spacing="8dp", size_hint_y=None
                )
                for r in rows:
                    content.add_widget(r)

                def on_save(*a):
                    metric_saved = self.screen.exercise_obj.had_metric(
                        self.metric["name"]
                    )
                    if cb_default and cb_default.active:
                        metrics.update_metric_type(
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
                            metrics.set_exercise_metric_override(
                                self.screen.exercise_obj.name,
                                self.metric["name"],
                                is_user_created=self.screen.exercise_obj.is_user_created,
                                value=updates.get("value"),
                                db_path=db_path,
                            )
                    else:
                        if metric_saved:
                            metrics.set_exercise_metric_override(
                                self.screen.exercise_obj.name,
                                self.metric["name"],
                                mtype=updates.get("type"),
                                input_timing=updates.get("input_timing"),
                                is_required=updates.get("is_required"),
                                scope=updates.get("scope"),
                                enum_values=updates.get("values"),
                                value=updates.get("value"),
                                is_user_created=self.screen.exercise_obj.is_user_created,
                                db_path=db_path,
                            )
                    if cb_presets and cb_presets.active:
                        apply_exercise_changes_to_presets(
                            self.screen.exercise_obj,
                            presets,
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

        elif metrics.is_metric_type_user_created(self.metric["name"], db_path=db_path):
            dialog = None

            def cancel_action(*a):
                if dialog:
                    dialog.dismiss()

            checkbox = MDCheckbox(size_hint=(None, None), height="40dp", width="40dp")
            label = MDLabel(
                text="Apply changes to all exercises using this metric", halign="left"
            )
            content = MDBoxLayout(
                orientation="horizontal", spacing="8dp", size_hint_y=None, height="40dp"
            )
            content.add_widget(checkbox)
            content.add_widget(label)

            def on_save(*a):
                metric_saved = self.screen.exercise_obj.had_metric(self.metric["name"])
                if checkbox.active:
                    metrics.update_metric_type(
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
                        metrics.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            is_user_created=self.screen.exercise_obj.is_user_created,
                            value=updates.get("value"),
                            db_path=db_path,
                        )
                else:
                    if metric_saved:
                        metrics.set_exercise_metric_override(
                            self.screen.exercise_obj.name,
                            self.metric["name"],
                            mtype=updates.get("type"),
                            input_timing=updates.get("input_timing"),
                            is_required=updates.get("is_required"),
                            scope=updates.get("scope"),
                            value=updates.get("value"),
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


class PreSessionMetricPopup(MDDialog):
    """Popup for entering pre-session metrics."""

    def __init__(self, metrics: list[dict], on_save, **kwargs):
        self.metrics = metrics
        self.on_save = on_save
        # Match the behaviour of the other metric popups by having the dialog
        # consume most of the available screen space on small devices. ``size_hint_y``
        # is ignored by :class:`MDDialog`, and it resets explicit heights during
        # construction, so height is assigned after initialization.
        kwargs.setdefault("size_hint", (0.95, None))
        content, buttons = self._build_widgets()
        super().__init__(
            title="Session Metrics", type="custom", content_cls=content, buttons=buttons, **kwargs
        )
        Clock.schedule_once(
            lambda *_: setattr(self, "height", Window.height * 0.9)
        )

    def _build_widgets(self):
        # Build a list of metric input rows. Binding ``minimum_height`` ensures
        # the list grows with its children so that it is fully scrollable.
        self.metric_list = MDList(adaptive_height=True)
        # Disable vertical size hint so the ``minimum_height`` binding updates
        # the list's height for scrolling.
        self.metric_list.bind(minimum_height=self.metric_list.setter("height"))
        for m in self.metrics:
            self.metric_list.add_widget(self._create_row(m))
        scroll = ScrollView(do_scroll_y=True, size_hint=(1, 1))
        scroll.add_widget(self.metric_list)
        save_btn = MDRaisedButton(text="Save", on_release=lambda *_: self._on_save())
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *_: self.dismiss())
        return scroll, [save_btn, cancel_btn]

    def _create_row(self, metric):
        name = metric.get("name")
        mtype = metric.get("type", "str")
        values = metric.get("values", [])
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
        row.metric_name = name
        row.type = mtype
        row.required = metric.get("is_required", False)
        row.add_widget(MDLabel(text=name, size_hint_x=0.4))
        if mtype == "slider":
            widget = MDSlider(min=0, max=1, value=0)
        elif mtype == "enum":
            widget = Spinner(text=values[0] if values else "", values=values)
        else:
            input_filter = None
            if mtype == "int":
                input_filter = "int"
            elif mtype == "float":
                input_filter = "float"
            widget = MDTextField(multiline=False, input_filter=input_filter)
        row.input_widget = widget
        row.add_widget(widget)
        return row

    def _collect(self):
        data = {}
        valid = True
        for row in reversed(self.metric_list.children):
            name = getattr(row, "metric_name", "")
            widget = getattr(row, "input_widget", None)
            mtype = getattr(row, "type", "str")
            required = getattr(row, "required", False)
            value = None
            if isinstance(widget, MDTextField):
                text = widget.text.strip()
                if required and text == "":
                    widget.error = True
                    valid = False
                    continue
                if mtype == "int":
                    try:
                        value = int(text)
                    except Exception:
                        widget.error = True
                        valid = False
                        continue
                elif mtype == "float":
                    try:
                        value = float(text)
                    except Exception:
                        widget.error = True
                        valid = False
                        continue
                elif mtype == "bool":
                    low = text.lower()
                    if low in ("true", "1", "yes"):
                        value = True
                    elif low in ("false", "0", "no"):
                        value = False
                    else:
                        widget.error = True
                        valid = False
                        continue
                else:
                    value = text
            elif isinstance(widget, MDSlider):
                value = float(widget.value)
            elif isinstance(widget, Spinner):
                value = widget.text
                if required and value == "":
                    valid = False
                    continue
            data[name] = value
        return valid, data

    def _on_save(self):
        valid, data = self._collect()
        if not valid:
            return
        if self.on_save:
            self.on_save(data)
        self.dismiss()
