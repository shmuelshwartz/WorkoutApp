import json
import os
from kivy.lang import Builder
from kivy.properties import StringProperty
from kivy.utils import get_color_from_hex, get_hex_from_color
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.popup import Popup
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "workout_app", "settings", "config.json")
DEFAULT_COLOR = "Blue"
DEFAULT_SCREEN_COLOR = "#FFFFFF"
DEFAULT_BUTTON_COLOR = "#2196F3"


def load_config():
    defaults = {
        "color_scheme": DEFAULT_COLOR,
        "screen_color": DEFAULT_SCREEN_COLOR,
        "button_color": DEFAULT_BUTTON_COLOR,
    }
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(defaults, f)
        return defaults
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return {**defaults, **data}


def save_config(color_scheme, screen_color, button_color):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(
            {
                "color_scheme": color_scheme,
                "screen_color": screen_color,
                "button_color": button_color,
            },
            f,
        )


class WelcomeScreen(MDScreen):
    pass


class HomeScreen(MDScreen):
    pass


class SelectWorkoutScreen(MDScreen):
    pass


class SettingsScreen(MDScreen):
    pass


class StartWorkoutScreen(MDScreen):
    pass


class ActiveScreen(MDScreen):
    pass


class RestScreen(MDScreen):
    pass


class WorkoutApp(MDApp):
    screen_color = StringProperty(DEFAULT_SCREEN_COLOR)
    button_color = StringProperty(DEFAULT_BUTTON_COLOR)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cfg = load_config()
        self.color_scheme = cfg["color_scheme"]
        self.screen_color = cfg["screen_color"]
        self.button_color = cfg["button_color"]

    def build(self):
        self.theme_cls.primary_palette = self.color_scheme
        return Builder.load_file("main.kv")

    def change_color_scheme(self, color):
        self.theme_cls.primary_palette = color
        self.color_scheme = color
        save_config(self.color_scheme, self.screen_color, self.button_color)

    def change_screen_color(self, hex_color):
        self.screen_color = hex_color
        save_config(self.color_scheme, self.screen_color, self.button_color)

    def change_button_color(self, hex_color):
        self.button_color = hex_color
        save_config(self.color_scheme, self.screen_color, self.button_color)

    def get_color_tuple(self, hex_color):
        return get_color_from_hex(hex_color)

    def open_screen_color_picker(self):
        picker = ColorPicker()
        popup = Popup(title="Screen Color", content=picker, size_hint=(0.9, 0.9))

        def on_color(instance, value):
            self.change_screen_color(get_hex_from_color(value))
            popup.dismiss()

        picker.bind(color=on_color)
        popup.open()

    def open_button_color_picker(self):
        picker = ColorPicker()
        popup = Popup(title="Button Color", content=picker, size_hint=(0.9, 0.9))

        def on_color(instance, value):
            self.change_button_color(get_hex_from_color(value))
            popup.dismiss()

        picker.bind(color=on_color)
        popup.open()

    def go_home(self):
        self.root.current = "home"


if __name__ == "__main__":
    WorkoutApp().run()
