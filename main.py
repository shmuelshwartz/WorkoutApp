import json
import os
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "workout_app", "settings", "config.json")
DEFAULT_COLOR = "Blue"


def load_config():
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump({"color_scheme": DEFAULT_COLOR}, f)
        return DEFAULT_COLOR
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return data.get("color_scheme", DEFAULT_COLOR)


def save_config(color):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump({"color_scheme": color}, f)


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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color_scheme = load_config()

    def build(self):
        self.theme_cls.primary_palette = self.color_scheme
        return Builder.load_file("main.kv")

    def change_color_scheme(self, color):
        self.theme_cls.primary_palette = color
        self.color_scheme = color
        save_config(color)

    def go_home(self):
        self.root.current = "home"


if __name__ == "__main__":
    WorkoutApp().run()
