from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty, ObjectProperty
from ui.expandable_list_item import ExpandableListItem, ExerciseSummaryItem


class PresetDetailScreen(MDScreen):
    """Screen showing details for a workout preset."""

    preset_name = StringProperty("")
    summary_list = ObjectProperty(None)

    def __init__(self, data_provider=None, preset_name: str = "", test_mode: bool = False, **kwargs):
        super().__init__(**kwargs)
        if test_mode and data_provider is None:
            from ui.stubs.preset_detail_stub import StubPresetProvider

            data_provider = StubPresetProvider()
        self.data_provider = data_provider
        self.test_mode = test_mode
        if not preset_name and hasattr(self.data_provider, "get_default_preset_name"):
            preset_name = self.data_provider.get_default_preset_name()
        self.preset_name = preset_name

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.summary_list or self.data_provider is None:
            return
        self.summary_list.clear_widgets()
        data = self.data_provider.get_preset_summary(self.preset_name)
        for metric in data.get("metrics", []):
            if metric.get("scope") == "preset":
                value = metric.get("value")
                text = f"{metric['name']}: {value}" if value is not None else metric["name"]
                self.summary_list.add_widget(ExpandableListItem(text=text))
        for section in data.get("sections", []):
            self.summary_list.add_widget(
                ExpandableListItem(text=f"Section: {section['name']}")
            )
            for ex in section.get("exercises", []):
                sets = ex.get("sets", 0) or 0
                self.summary_list.add_widget(
                    ExerciseSummaryItem(name=ex["name"], sets=sets)
                )


if __name__ == "__main__":
    from kivymd.app import MDApp
    from kivy.lang import Builder

    KV = """
<PresetDetailScreen>:
    summary_list: summary_list
    BoxLayout:
        orientation: "vertical"
        spacing: "10dp"
        padding: "20dp"
        MDLabel:
            text: root.preset_name if root.preset_name else "Preset Detail - view exercises in this preset"
            halign: "center"
            theme_text_color: "Custom"
            text_color: 0.2, 0.6, 0.86, 1
        ScrollView:
            MDList:
                id: summary_list
        MDRaisedButton:
            text: "Edit Preset"
            on_release: print("Edit Preset clicked")
        MDRaisedButton:
            text: "Go to Preset Overview"
            on_release: print("Go to Preset Overview clicked")
        MDRaisedButton:
            text: "Back to Presets"
            on_release: print("Back to Presets clicked")
    """

    class _TestApp(MDApp):
        def build(self):
            from ui.stubs.preset_detail_stub import StubPresetProvider

            Builder.load_string(KV)
            return PresetDetailScreen(data_provider=StubPresetProvider(), test_mode=True)

    _TestApp().run()
