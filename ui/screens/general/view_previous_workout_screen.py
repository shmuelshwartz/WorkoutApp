from __future__ import annotations

from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDList, OneLineListItem, TwoLineListItem
from kivy.app import App

from backend.sessions import get_session_details


class ViewPreviousWorkoutScreen(MDScreen):
    """Display details for a past workout session."""

    session_start: float | None = None

    def on_pre_enter(self, *args):
        if self.session_start is not None:
            self.populate()
        return super().on_pre_enter(*args)

    def show_session(self, started_at: float) -> None:
        """Load data for ``started_at`` and switch to this screen."""
        self.session_start = started_at
        app = App.get_running_app()
        app.root.current = "view_previous_workout"

    def populate(self) -> None:
        details = get_session_details(self.session_start)
        lst: MDList = self.ids.get("details_list")  # type: ignore[arg-type]
        if not lst:
            return
        lst.clear_widgets()
        if not details:
            lst.add_widget(OneLineListItem(text="No details found"))
            return
        lst.add_widget(OneLineListItem(text=f"Preset: {details['preset_name']}"))
        if details.get("metrics"):
            lst.add_widget(OneLineListItem(text="Session metrics:"))
            for m in details["metrics"]:
                lst.add_widget(OneLineListItem(text=f"{m['name']}: {m['value']}"))
        for ex in details.get("exercises", []):
            lst.add_widget(OneLineListItem(text=f"Exercise: {ex['name']}"))
            for s in ex.get("sets", []):
                metrics = ", ".join(f"{md['name']}: {md['value']}" for md in s["metrics"])
                extra = []
                if s.get("rest") is not None:
                    extra.append(f"rest {int(s['rest'])}s")
                if s.get("duration") is not None:
                    extra.append(f"time {int(s['duration'])}s")
                desc = ", ".join(extra)
                item = TwoLineListItem(
                    text=f"Set {s['number']}" + (f" ({desc})" if desc else ""),
                    secondary_text=metrics or "",
                )
                lst.add_widget(item)
