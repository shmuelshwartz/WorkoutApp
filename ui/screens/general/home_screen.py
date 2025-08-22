try:  # pragma: no cover - fallback for environments without Kivy
    from kivymd.app import MDApp
    from kivymd.uix.screen import MDScreen
    from kivymd.uix.dialog import MDDialog
    from kivymd.uix.button import MDFlatButton, MDRaisedButton
except Exception:  # pragma: no cover - simple stubs
    MDApp = object
    MDScreen = object

    class MDDialog:
        def __init__(self, *a, **k):
            pass

        def open(self, *a, **k):
            pass

        def dismiss(self, *a, **k):
            pass

    class MDFlatButton:
        def __init__(self, *a, **k):
            pass

    class MDRaisedButton(MDFlatButton):
        pass

from backend.workout_session import WorkoutSession
from tiny_screen import apply_safe_area_padding  # TINY-SCREEN: safe area


class HomeScreen(MDScreen):
    """Primary screen that prompts to resume a recovered session if available."""

    def on_kv_post(self, base_widget):
        apply_safe_area_padding(self.ids.content_box, top=True, bottom=True)  # TINY-SCREEN: safe area padding
        return super().on_kv_post(base_widget)

    def on_enter(self, *args):
        """Attempt to restore any previous workout session."""
        session = WorkoutSession.load_from_recovery()
        if session:
            self._show_recovery_dialog(session)
        return super().on_enter(*args)

    def _show_recovery_dialog(self, session: WorkoutSession) -> None:
        app = MDApp.get_running_app()

        def recover(*_):
            dialog.dismiss()
            if app:
                app.workout_session = session
                if session.is_set_active():
                    session.resume_from_last_start = True
                    if app.root:
                        app.root.current = "workout_active"
                else:
                    if app.root:
                        app.root.current = "rest"

        def discard(*_):
            session.clear_recovery_files()
            dialog.dismiss()

        dialog = MDDialog(
            text="Recover previous workout session?",
            buttons=[
                MDFlatButton(text="No", on_release=discard),
                MDRaisedButton(text="Yes", on_release=recover),
            ],
        )
        dialog.open()
        self._recovery_dialog = dialog
