"""Edit exercise screen module for WorkoutApp."""

from __future__ import annotations

from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
    BooleanProperty,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivymd.uix.label import MDLabel
from kivymd.uix.list import OneLineListItem, MDList
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDSeparator
from ui.dialogs import FullScreenDialog
from kivymd.uix.label import MDIcon
from ui.popups import AddMetricPopup, EditMetricPopup

import os
import string
import sqlite3

from backend import metrics, exercises
from backend.presets import find_presets_using_exercise, apply_exercise_changes_to_presets
from core import (
    DEFAULT_SETS_PER_EXERCISE,
    DEFAULT_REST_DURATION,
    DEFAULT_DB_PATH,
)
from backend.exercise import Exercise

from ..session.metric_input_screen import MetricInputScreen


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
    mode = StringProperty("library")

    def __init__(self, mode: str = "library", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

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
        presets = []

        def do_nav(*args):
            if dialog:
                dialog.dismiss()
            self._navigate_to(new_index)

        dialog = FullScreenDialog(
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
            from main import LoadingDialog  # local import to avoid circular dependency

            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(lambda dt: self._load_exercise(), 0)
        return super().on_pre_enter(*args)

    def _load_exercise(self):
        db_path = DEFAULT_DB_PATH
        self.exercise_obj = Exercise(
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
                section_exercises = app.preset_editor.sections[self.section_index]["exercises"]
                self.section_length = len(section_exercises)
                if self.exercise_index < len(section_exercises):
                    ex = section_exercises[self.exercise_index]
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
            if self.mode == "session":
                row.add_widget(MDIcon(icon="lock"))
            else:
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

        dialog = FullScreenDialog(
            title="Remove Metric?",
            text=f"Delete {metric_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def open_add_metric_popup(self):
        if self.mode == "session":
            return
        popup = AddMetricPopup(self, popup_mode="select", mode=self.mode)
        popup.open()

    def open_new_metric_popup(self):
        if self.mode == "session":
            return
        popup = AddMetricPopup(self, popup_mode="new", mode=self.mode)
        popup.open()

    def open_edit_metric_popup(self, metric):
        if self.mode == "session":
            return
        popup = EditMetricPopup(self, metric, mode=self.mode)
        popup.open()

    def save_exercise(self):
        """Validate and persist changes to the current exercise."""
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
            dialog = FullScreenDialog(
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
            dialog = FullScreenDialog(
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
            try:
                if update_library:
                    exercises.save_exercise(self.exercise_obj)
                    if app:
                        app.exercise_library_version += 1
                if (not update_in_preset) and checkbox and checkbox.active and presets:
                    apply_exercise_changes_to_presets(
                        self.exercise_obj,
                        presets,
                        db_path=DEFAULT_DB_PATH,
                    )
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
                                metrics.set_section_exercise_metric_override(
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
                            db_path = DEFAULT_DB_PATH
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
            except Exception as exc:  # pragma: no cover - user feedback
                if dialog:
                    dialog.dismiss()
                err = None

                def _dismiss(*_):
                    if err:
                        err.dismiss()

                err = FullScreenDialog(
                    title="Save Failed",
                    text=str(exc),
                    buttons=[MDRaisedButton(text="OK", on_release=_dismiss)],
                )
                err.open()

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
            dialog = FullScreenDialog(
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
            extra_content = None
            if self.previous_screen == "exercise_library":
                presets = find_presets_using_exercise(self.exercise_obj.name)
                if presets:
                    checkbox = MDCheckbox(
                        size_hint=(None, None), height="40dp", width="40dp"
                    )
                    label = MDLabel(
                        text="Update all presets that use this exercise", halign="left"
                    )
                    extra_content = MDBoxLayout(
                        orientation="horizontal",
                        spacing="8dp",
                        size_hint_y=None,
                        height="40dp",
                    )
                    extra_content.add_widget(checkbox)
                    extra_content.add_widget(label)
            dialog = FullScreenDialog(
                title="Confirm Save",
                type="custom" if extra_content else "simple",
                text=msg,
                content_cls=extra_content,
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

            dialog = FullScreenDialog(
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
