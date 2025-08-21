from __future__ import annotations

"""Screen for modifying app settings."""

try:
    from kivymd.uix.screen import MDScreen
    from kivymd.app import MDApp
    from kivymd.toast import toast
except Exception:  # pragma: no cover - minimal stubs for testing
    MDApp = object

    class MDScreen:  # type: ignore[misc]
        pass

    def toast(*_, **__):  # type: ignore[misc]
        pass

from kivy.properties import StringProperty
import logging

from backend import settings as app_settings
from backend import db_io
from backend import saf_backup
from backend.db_io import DB_PATH


class SettingsScreen(MDScreen):
    """Display and persist user-configurable settings."""

    return_to = StringProperty("home")
    """Name of the screen to return to when leaving settings."""

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

    # ------------------------------------------------------------------
    # Database import/export helpers
    # ------------------------------------------------------------------
    def export_db(self) -> None:
        """Launch Android's 'Save as' picker to export the database."""
        try:
            saf_backup.start_export(DB_PATH, suggested_name="workout.db")
        except Exception as exc:
            logging.exception("Database export failed")
            toast(f"Export failed: {exc}")

    def export_json(self) -> None:
        """Export the SQLite database as a JSON file."""
        try:
            path = db_io.export_database_json()
            logging.info("Database JSON exported to %s", path)
            toast(f"Exported to {path}")
        except FileNotFoundError:
            logging.exception("JSON export failed: destination missing")
            toast("Export failed: destination missing")
        except PermissionError:
            logging.exception("JSON export failed: permission denied")
            toast(
                "Export failed: All files access not granted. "
                "Please enable 'All files access' for Workout App in system settings."
            )
        except OSError as exc:
            logging.exception("JSON export failed")
            toast(f"Export failed: {exc}")

    def open_import_db(self) -> None:
        """Launch Android's file picker to select a database for import."""
        try:
            saf_backup.start_import()
        except Exception as exc:
            logging.exception("Import failed to start")
            toast(f"Import failed: {exc}")
