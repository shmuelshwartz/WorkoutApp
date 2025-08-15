from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, ObjectProperty
from ui.expandable_list_item import ExpandableListItem, ExerciseSummaryItem


class PresetDetailScreen(MDScreen):
    """Screen showing details for a workout preset."""

    preset_name = StringProperty("")
    summary_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.summary_list:
            return
        self.summary_list.clear_widgets()
        app = MDApp.get_running_app()
        self.preset_name = app.selected_preset
        app.init_preset_editor()
        editor = app.preset_editor
        if not editor:
            return

        for metric in editor.preset_metrics:
            if metric.get("scope") == "preset":
                value = metric.get("value")
                text = f"{metric['name']}: {value}" if value is not None else metric["name"]
                self.summary_list.add_widget(ExpandableListItem(text=text))

        for section in editor.sections:
            self.summary_list.add_widget(
                ExpandableListItem(text=f"Section: {section['name']}")
            )
            for ex in section.get("exercises", []):
                sets = ex.get("sets", 0) or 0
                self.summary_list.add_widget(
                    ExerciseSummaryItem(name=ex["name"], sets=sets)
                )

