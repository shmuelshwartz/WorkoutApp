from kivymd.uix.screen import MDScreen
from kivy.properties import StringProperty


class PresetDetailScreen(MDScreen):
    """Screen showing details for a workout preset."""

    preset_name = StringProperty("")

