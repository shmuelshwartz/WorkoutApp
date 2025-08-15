from datetime import datetime

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import TwoLineListItem
from kivy.app import App

from backend.sessions import get_session_history


class WorkoutHistoryScreen(MDScreen):
    """Screen displaying a list of past workouts."""

    def on_pre_enter(self, *args):
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self) -> None:
        history = get_session_history()
        lst = self.ids.get("history_list")
        if not lst:
            return
        lst.clear_widgets()
        for entry in history:
            dt = datetime.fromtimestamp(entry["started_at"])
            item = TwoLineListItem(
                text=entry["preset_name"],
                secondary_text=dt.strftime("%H:%M %a %d/%m/%Y"),
                on_release=lambda _, ts=entry["started_at"]: self.open_session(ts),
            )
            lst.add_widget(item)

    def open_session(self, started_at: float) -> None:
        app = App.get_running_app()
        screen = app.root.get_screen("view_previous_workout")
        screen.show_session(started_at)
