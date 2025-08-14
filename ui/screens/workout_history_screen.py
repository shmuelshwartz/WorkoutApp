from datetime import datetime

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import TwoLineListItem

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
            )
            lst.add_widget(item)
