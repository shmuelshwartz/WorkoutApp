import json
import os
from kivy.lang import Builder
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock
from kivy.utils import get_color_from_hex, get_hex_from_color
from kivy.uix.colorpicker import ColorPicker
from kivy.uix.popup import Popup
from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.button import MDRaisedButton

DEFAULT_COLOR = "Blue"
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "settings", "config.json")
DEFAULT_SCREEN_COLOR = "#FFFFFF"
DEFAULT_BUTTON_TEXT_COLOR = "#FFFFFF"
DEFAULT_BUTTON_COLOR = "#2196F3"


def load_config():
    defaults = {
        "color_scheme": DEFAULT_COLOR,
        "screen_color": DEFAULT_SCREEN_COLOR,
        "button_color": DEFAULT_BUTTON_COLOR,
        "button_text_color": DEFAULT_BUTTON_TEXT_COLOR,
    }
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, "w") as f:
            json.dump(defaults, f)
        return defaults
    with open(CONFIG_PATH, "r") as f:
        data = json.load(f)
    return {**defaults, **data}


def save_config(color_scheme, screen_color, button_color, button_text_color):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(
            {
                "color_scheme": color_scheme,
                "screen_color": screen_color,
                "button_color": button_color,
                "button_text_color": button_text_color,
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
    time_elapsed = NumericProperty(0)
    _event = None

    def on_pre_enter(self, *args):
        self.time_elapsed = 0
        self._event = Clock.schedule_interval(self._update_time, 1)

    def on_leave(self, *args):
        if self._event:
            self._event.cancel()

    def _update_time(self, dt):
        self.time_elapsed += 1


class RestScreen(MDScreen):
    timer = NumericProperty(20)
    ready = BooleanProperty(False)
    _event = None

    def on_pre_enter(self, *args):
        self.timer = 20
        self.ready = False
        self._event = Clock.schedule_interval(self._tick, 1)

    def on_leave(self, *args):
        if self._event:
            self._event.cancel()

    def toggle_ready(self):
        self.ready = not self.ready
        if self.timer == 0 and self.ready:
            self.manager.current = "active"

    def _tick(self, dt):
        if self.ready and self.timer > 0:
            self.timer -= 1
            if self.timer <= 0:
                self.timer = 0
                if self.ready:
                    self.manager.current = "active"


class WorkoutApp(MDApp):
    screen_color = StringProperty(DEFAULT_SCREEN_COLOR)
    button_color = StringProperty(DEFAULT_BUTTON_COLOR)
    button_text_color = StringProperty(DEFAULT_BUTTON_TEXT_COLOR)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        cfg = load_config()
        self.color_scheme = cfg["color_scheme"]
        self.screen_color = cfg["screen_color"]
        self.button_color = cfg["button_color"]
        self.button_text_color = cfg.get("button_text_color", DEFAULT_BUTTON_TEXT_COLOR)

    def build(self):
        self.theme_cls.primary_palette = self.color_scheme
        return Builder.load_file("main.kv")

    def change_color_scheme(self, color):
        self.theme_cls.primary_palette = color
        self.color_scheme = color
        save_config(self.color_scheme, self.screen_color, self.button_color, self.button_text_color)

    def change_screen_color(self, hex_color):
        self.screen_color = hex_color
        save_config(self.color_scheme, self.screen_color, self.button_color, self.button_text_color)

    def change_button_color(self, hex_color):
        self.button_color = hex_color
        save_config(self.color_scheme, self.screen_color, self.button_color, self.button_text_color)

    def toggle_button_text_color(self):
        self.button_text_color = "#000000" if self.button_text_color == "#FFFFFF" else "#FFFFFF"
        save_config(self.color_scheme, self.screen_color, self.button_color, self.button_text_color)

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
        toggle = MDRaisedButton(text="Toggle Text Color")
        layout = BoxLayout(orientation="vertical")
        layout.add_widget(picker)
        layout.add_widget(toggle)
        popup = Popup(title="Button Color", content=layout, size_hint=(0.9, 0.9))

        def on_color(instance, value):
            self.change_button_color(get_hex_from_color(value))

        def on_toggle(instance):
            self.toggle_button_text_color()

        picker.bind(color=on_color)
        toggle.bind(on_release=on_toggle)
        popup.open()

    def go_home(self):
        self.root.current = "home"


if __name__ == "__main__":
    WorkoutApp().run()
