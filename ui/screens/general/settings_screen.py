from __future__ import annotations

"""Screen for modifying app settings."""

from kivymd.uix.screen import MDScreen
from kivymd.app import MDApp
from backend import settings as app_settings


class SettingsScreen(MDScreen):
    """Display and persist user-configurable settings."""

    def on_pre_enter(self, *args) -> None:
        """Populate controls from stored settings."""
        self.ids.sound_level_slider.value = app_settings.get_value("sound_level") or 1.0
        sound_on = app_settings.get_value("sound_on")
        self.ids.sound_toggle.active = True if sound_on is None else bool(sound_on)

    def on_sound_level(self, slider, value: float) -> None:
        """Handle volume slider changes."""
        app_settings.set_value("sound_level", value)
        MDApp.get_running_app().sound.set_volume(value)

    def on_sound_toggle(self, switch, value: bool) -> None:
        """Handle sound enable/disable toggling."""
        app_settings.set_value("sound_on", value)
        MDApp.get_running_app().sound.set_enabled(value)
