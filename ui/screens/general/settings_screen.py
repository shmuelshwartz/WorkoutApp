from __future__ import annotations

"""Screen for modifying app settings."""

try:
    from kivymd.uix.screen import MDScreen
    from kivymd.app import MDApp
    from kivymd.uix.filemanager import MDFileManager
    from kivymd.toast import toast
except Exception:  # pragma: no cover - minimal stubs for testing
    MDApp = object

    class MDScreen:  # type: ignore[misc]
        pass

    class MDFileManager:  # type: ignore[misc]
        def __init__(self, *_, **__):
            pass

        def show(self, *_, **__):
            pass

        def close(self, *_, **__):
            pass

    def toast(*_, **__):  # type: ignore[misc]
        pass

from kivy.properties import StringProperty
from pathlib import Path
import logging

from backend import settings as app_settings
from backend import db_io


class SettingsScreen(MDScreen):
    """Display and persist user-configurable settings."""

    return_to = StringProperty("home")
    """Name of the screen to return to when leaving settings."""
    file_manager: MDFileManager | None = None

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
        """Export the SQLite database as a ``.db`` file."""
        try:
            path = db_io.export_database()
            logging.info("Database exported to %s", path)
            toast("Database exported")
        except Exception as exc:  # pragma: no cover - defensive
            logging.error("Database export failed: %s", exc)
            toast("Export failed")

    def export_json(self) -> None:
        """Export the SQLite database as a JSON file."""
        try:
            path = db_io.export_database_json()
            logging.info("Database JSON exported to %s", path)
            toast("JSON exported")
        except Exception as exc:  # pragma: no cover - defensive
            logging.error("JSON export failed: %s", exc)
            toast("Export failed")

    def open_import_db(self) -> None:
        """Open a file picker to select a database for import."""
        if self.file_manager is None:
            self.file_manager = MDFileManager(
                exit_manager=self.close_file_manager,
                select_path=self.select_import_file,
                ext=[".db"],
            )
        try:
            # The downloads directory may be unavailable on some platforms.
            downloads_dir = db_io.get_downloads_dir()
        except Exception as exc:  # pragma: no cover - defensive
            logging.error("Downloads directory lookup failed: %s", exc)
            toast("Import unavailable")
            return
        self.file_manager.show(str(downloads_dir))

    def close_file_manager(self, *_) -> None:
        """Close the file picker if it is open."""
        if self.file_manager:
            self.file_manager.close()

    def select_import_file(self, path: str) -> None:
        """Validate and import the selected database file."""
        self.close_file_manager()
        if db_io.import_database(Path(path)):
            toast("Import successful")
        else:
            toast("Import failed")
