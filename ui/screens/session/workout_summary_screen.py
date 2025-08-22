from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import OneLineListItem
from kivy.properties import ObjectProperty
from ui.dialogs import FullScreenDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel

from backend.sessions import save_completed_session, validate_workout_session


class WorkoutSummaryScreen(MDScreen):
    """Screen showing the summary of a completed workout."""

    summary_list = ObjectProperty(None)

    def on_pre_enter(self, *args):
        self.populate()
        app = MDApp.get_running_app()
        session = app.workout_session if app else None
        if session and not getattr(session, "saved", False):
            errors = validate_workout_session(session)
            if errors:
                self._show_error("\n".join(errors))
            else:
                try:
                    save_completed_session(session, db_path=session.db_path)
                except Exception as exc:
                    self._show_error(str(exc))
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.summary_list:
            return
        self.summary_list.clear_widgets()
        app = MDApp.get_running_app()
        session = app.workout_session
        if not session:
            return
        print(session.summary())
        for exercise in session.exercises:
            self.summary_list.add_widget(OneLineListItem(text=exercise["name"]))
            for idx, metrics in enumerate(exercise["results"], 1):
                metrics_text = ", ".join(f"{k}: {v}" for k, v in metrics.items())
                self.summary_list.add_widget(
                    OneLineListItem(text=f"Set {idx}: {metrics_text}")
                )

    def _show_error(self, message: str):
        def close_dialog(*_):
            dialog.dismiss()

        dialog = FullScreenDialog(
            title="Save Error",
            content_cls=MDLabel(text=message, halign="center"),
            buttons=[MDRaisedButton(text="OK", on_release=close_dialog)],
        )
        dialog.open()

