from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.properties import ObjectProperty, StringProperty, ListProperty
from kivymd.uix.list import OneLineListItem
from backend import presets


class PresetsScreen(MDScreen):
    """Screen to select a workout preset."""

    preset_list = ObjectProperty(None)
    selected_preset = StringProperty("")
    selected_item = ObjectProperty(None, allownone=True)

    _selected_color = (0, 1, 0, 1)
    _selected_text_color = (0, 1, 0, 1)
    _default_btn_color = ListProperty(None, allownone=True)

    def on_kv_post(self, base_widget):
        # Store the default color of the "Select" button so it can be restored
        self._default_btn_color = self.ids.select_btn.md_bg_color
        return super().on_kv_post(base_widget)

    def clear_selection(self, reset_app: bool = True):
        """Reset any selected preset and remove highlight.

        ``reset_app`` controls whether the app-level ``selected_preset``
        attribute is cleared. When leaving this screen for another screen,
        we want to preserve the global selection so the detail or edit
        screens can load the chosen preset. When entering this screen
        anew, we clear the global selection so no stale state remains.
        """
        if self.selected_item:
            self.selected_item.md_bg_color = (0, 0, 0, 0)
            self.selected_item.theme_text_color = "Primary"
        self.selected_item = None
        self.selected_preset = ""
        if reset_app:
            app = MDApp.get_running_app()
            if app:
                app.selected_preset = ""
        if self._default_btn_color is not None:
            self.ids.select_btn.md_bg_color = self._default_btn_color

    def on_pre_enter(self, *args):
        self.clear_selection()
        self.populate()
        return super().on_pre_enter(*args)

    def on_leave(self, *args):
        # Preserve app.selected_preset so other screens know which preset
        # was chosen when navigating away from this screen.
        self.clear_selection(reset_app=False)
        return super().on_leave(*args)

    def populate(self):
        if not self.preset_list:
            return
        self.preset_list.clear_widgets()
        for preset in presets.WORKOUT_PRESETS:
            item = OneLineListItem(text=preset["name"])
            item.bind(
                on_release=lambda inst, name=preset["name"]: self.select_preset(
                    name, inst
                )
            )
            self.preset_list.add_widget(item)

    def select_preset(self, name, item):
        """Select a preset from WORKOUT_PRESETS and highlight item."""
        if self.selected_item is item:
            # Toggle off selection if tapping the already selected item
            item.md_bg_color = (0, 0, 0, 0)
            item.theme_text_color = "Primary"
            self.selected_item = None
            self.selected_preset = ""
            MDApp.get_running_app().selected_preset = ""
            return

        if self.selected_item:
            self.selected_item.md_bg_color = (0, 0, 0, 0)
            self.selected_item.theme_text_color = "Primary"
        self.selected_item = item
        self.selected_item.md_bg_color = self._selected_color
        self.selected_item.theme_text_color = "Custom"
        self.selected_item.text_color = self._selected_text_color
        if any(p["name"] == name for p in presets.WORKOUT_PRESETS):
            self.selected_preset = name
            MDApp.get_running_app().selected_preset = name

    def confirm_selection(self):
        if self.selected_preset and self.manager:
            detail = self.manager.get_screen("preset_detail")
            detail.preset_name = self.selected_preset
            self.manager.current = "preset_detail"
