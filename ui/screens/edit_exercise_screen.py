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
from kivymd.uix.button import MDIconButton, MDRaisedButton
from kivymd.uix.card import MDSeparator
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDIcon
from ui.popups import AddMetricPopup, EditMetricPopup

import os

# Default values duplicated here to avoid backend imports
DEFAULT_SETS_PER_EXERCISE = 3
DEFAULT_REST_DURATION = 120

from ui.screens.metric_input_screen import MetricInputScreen


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
    data_provider = ObjectProperty(None, allownone=True)
    test_mode = BooleanProperty(False)

    def __init__(
        self,
        mode: str = "library",
        data_provider=None,
        router=None,
        test_mode: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.mode = mode
        self.test_mode = test_mode
        self.router = router
        if data_provider is None:
            if test_mode:
                from ui.stubs.exercise_data_provider import (
                    StubExerciseDataProvider,
                )

                self.data_provider = StubExerciseDataProvider()
            else:
                from ui.adapters.exercise_data_provider import (
                    ExerciseDataProvider,
                )

                self.data_provider = ExerciseDataProvider()
        else:
            self.data_provider = data_provider

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
            from main import LoadingDialog  # local import to avoid circular dependency

            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(lambda dt: self._load_exercise(), 0)
        return super().on_pre_enter(*args)

    def _load_exercise(self):
        self.exercise_obj = self.data_provider.get_exercise(
            self.exercise_name, is_user_created=self.is_user_created
        )
        self.is_user_created = getattr(self.exercise_obj, "is_user_created", True)
        self.exercise_name = getattr(self.exercise_obj, "name", "")
        self.exercise_description = getattr(self.exercise_obj, "description", "")
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
        if not self.exercise_obj:
            return

        app = MDApp.get_running_app()
        if (
            app
            and self.section_index >= 0
            and self.exercise_index >= 0
            and app.preset_editor
        ):
            app.preset_editor.update_exercise(
                self.section_index,
                self.exercise_index,
                sets=self.exercise_sets,
                rest=self.exercise_rest,
            )

        self.data_provider.save_exercise(self.exercise_obj)
        self.save_enabled = False

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


if __name__ == "__main__":  # pragma: no cover - manual visual test
    choice = (
        input("Type 1 for single-screen test\nType 2 for flow test\n").strip()
        or "1"
    )
    if choice == "2":
        from ui.testing.runners.flow_runner import run

        run("edit_exercise_screen")
    else:
        from kivymd.app import MDApp
        from ui.routers import SingleRouter

        class _TestApp(MDApp):
            def build(self):
                return EditExerciseScreen(router=SingleRouter(), test_mode=True)

        _TestApp().run()
