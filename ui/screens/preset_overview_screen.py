from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivy.properties import ObjectProperty
import core
from ui.expandable_list_item import ExpandableListItem


class PresetOverviewScreen(MDScreen):
    """Display an overview of the selected preset."""

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
        app.init_preset_editor()
        preset_name = app.selected_preset
        self.preset_label.text = (
            preset_name
            if preset_name
            else "Preset Overview - summary of the chosen preset"
        )
        editor = app.preset_editor
        if not editor:
            return
        for section in editor.sections:
            self.overview_list.add_widget(
                MDLabel(text=f"Section: {section['name']}")
            )
            for ex in section.get("exercises", []):
                desc_info = core.get_exercise_details(ex["name"])
                desc = desc_info.get("description", "") if desc_info else ""
                sets = ex.get("sets", 0) or 0
                rest = ex.get("rest", 0) or 0
                lines = [ex["name"], f"sets {sets} | rest: {rest}s", desc]
                text = "\n".join(lines)
                self.overview_list.add_widget(ExpandableListItem(text=text))

    def start_workout(self):
        app = MDApp.get_running_app()
        preset_name = app.selected_preset
        app.start_workout(preset_name)
        if self.manager:
            self.manager.current = "rest"
