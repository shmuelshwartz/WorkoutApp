from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.properties import ObjectProperty
from kivymd.uix.list import OneLineListItem

import core


class PresetOverviewScreen(MDScreen):
    """Screen showing a summary of exercises in the selected preset."""

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
