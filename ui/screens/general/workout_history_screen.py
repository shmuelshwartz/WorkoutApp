from datetime import datetime

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import TwoLineListItem
from kivy.app import App
from kivy.properties import StringProperty

from backend.sessions import get_session_history


class WorkoutHistoryScreen(MDScreen):
    """Display a list of past workouts and open their details.

    Attributes:
        return_to (str): Name of the screen to return to when the Back
            button is pressed. Defaults to ``"home"``.
    """

    return_to = StringProperty("home")
    """Name of the screen to return to when leaving the history screen."""

    def on_pre_enter(self, *args):
        """Populate the history list before the screen becomes visible."""
        self.populate()
        return super().on_pre_enter(*args)

    def populate(self) -> None:
        """Fill the history list with previous workout sessions."""
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
        """Open the details screen for the selected session.

        Args:
            started_at: UNIX timestamp when the session began.
        """
        app = App.get_running_app()
        screen = app.root.get_screen("view_previous_workout")
        screen.show_session(started_at)
