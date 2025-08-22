"""Exercise library screen module for WorkoutApp."""

from __future__ import annotations

from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
    ListProperty,
)
from kivymd.uix.screen import MDScreen
from ui.dialogs import FullScreenDialog
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel

import os
from backend import metrics, exercises
from core import DEFAULT_DB_PATH


class ExerciseLibraryScreen(MDScreen):
    """Screen allowing the user to manage exercises and metric types."""

    previous_screen = StringProperty("home")
    exercise_list = ObjectProperty(None)
    metric_list = ObjectProperty(None)
    search_text = StringProperty("")
    metric_search_text = StringProperty("")
    current_tab = StringProperty("exercises")
    # Cached list of all exercises including user-created ones
    all_exercises = ListProperty(None, allownone=True)
    # Cached list of all metric types
    all_metrics = ListProperty(None, allownone=True)
    # Version numbers when caches were loaded
    cache_version = NumericProperty(-1)
    metric_cache_version = NumericProperty(-1)

    loading_dialog = ObjectProperty(None, allownone=True)

    _search_event = None
    _metric_search_event = None

    def on_pre_enter(self, *args):
        """Populate the list widgets when the screen is shown."""
        if self.loading_dialog:
            # A loading dialog is already active, so avoid repopulating the
            # lists. This prevents the spinner from reopening when returning
            # from other dialogs that temporarily obscure the screen.
            return super().on_pre_enter(*args)

        app = MDApp.get_running_app()
        if self.all_exercises is None or (
            app and self.cache_version != getattr(app, "exercise_library_version", 0)
        ):
            db_path = DEFAULT_DB_PATH
            self.all_exercises = exercises.get_all_exercises(
                db_path, include_user_created=True
            )
            if app:
                self.cache_version = app.exercise_library_version

        if self.all_metrics is None or (
            app
            and self.metric_cache_version != getattr(app, "metric_library_version", 0)
        ):
            db_path = DEFAULT_DB_PATH
            self.all_metrics = metrics.get_all_metric_types(
                db_path, include_user_created=True
            )
            if app:
                self.metric_cache_version = app.metric_library_version

        self.populate(True)

        return super().on_pre_enter(*args)

    def populate(self, show_loading: bool = False):
        """Populate exercises or metrics depending on current tab.

        Parameters
        ----------
        show_loading: bool
            If ``True`` a modal loading spinner is displayed while the
            population work is carried out.  The dialog is guaranteed to be
            dismissed even if an error occurs, preventing the screen from
            appearing to load indefinitely.
        """

        if show_loading and not os.environ.get("KIVY_UNITTEST"):
            from main import LoadingDialog  # local import to avoid circular dependency

            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(self._populate_with_dismiss, 0)
        else:
            self._populate_with_dismiss(0)

    def _populate_with_dismiss(self, dt: float) -> None:
        """Populate the current tab and close the loading dialog safely.

        The method wraps :meth:`_populate_impl` ensuring that the loading
        dialog is dismissed regardless of success or failure so that the
        user always sees the screen contents.

        Parameters
        ----------
        dt: float
            Time delta from :func:`Clock.schedule_once` (unused).
        """

        try:
            self._populate_impl()
        except Exception as exc:  # pragma: no cover - logged for debugging
            # Log the error rather than leaving the user stuck on a spinner.
            print(f"Error populating library: {exc}")
        finally:
            if self.loading_dialog:
                self.loading_dialog.dismiss()
                self.loading_dialog = None

    def _populate_impl(self, dt: float | None = None):
        if self.current_tab == "exercises":
            self._populate_exercises()
        else:
            self._populate_metrics()

    def _populate_exercises(self):
        if not self.exercise_list:
            return
        self.exercise_list.data = []
        app = MDApp.get_running_app()
        if self.all_exercises is None or (
            app and self.cache_version != getattr(app, "exercise_library_version", 0)
        ):
            db_path = DEFAULT_DB_PATH
            self.all_exercises = exercises.get_all_exercises(
                db_path, include_user_created=True
            )
            if app:
                self.cache_version = app.exercise_library_version
        exercise_rows = self.all_exercises or []

        if self.search_text:
            s = self.search_text.lower()
            exercise_rows = [ex for ex in exercise_rows if s in ex[0].lower()]
        data = []
        for name, is_user in exercise_rows:
            data.append(
                {
                    "name": name,
                    "text": name,
                    "is_user_created": is_user,
                    "edit_callback": self.open_edit_exercise_popup,
                    "delete_callback": self.confirm_delete_exercise,
                }
            )
        self.exercise_list.data = data

    def _populate_metrics(self):
        if not self.metric_list:
            return
        self.metric_list.data = []
        app = MDApp.get_running_app()
        if self.all_metrics is None or (
            app
            and self.metric_cache_version != getattr(app, "metric_library_version", 0)
        ):
            db_path = DEFAULT_DB_PATH
            self.all_metrics = metrics.get_all_metric_types(
                db_path, include_user_created=True
            )
            if app:
                self.metric_cache_version = app.metric_library_version
        metrics = self.all_metrics or []
        if self.metric_search_text:
            s = self.metric_search_text.lower()
            metrics = [m for m in metrics if s in m["name"].lower()]
        data = []
        for m in metrics:
            data.append(
                {
                    "name": m["name"],
                    "text": m["name"],
                    "is_user_created": m["is_user_created"],
                    "edit_callback": self.open_edit_metric_popup,
                    "delete_callback": self.confirm_delete_metric,
                }
            )
        self.metric_list.data = data

    def update_search(self, text):
        """Update search text with debounce to limit populate frequency."""
        if self.current_tab == "exercises":
            self.search_text = text
            if self._search_event:
                self._search_event.cancel()

            def do_populate(dt):
                self._search_event = None
                self.populate()

            self._search_event = Clock.schedule_once(do_populate, 0.2)
        else:
            self.metric_search_text = text
            if self._metric_search_event:
                self._metric_search_event.cancel()

            def do_populate(dt):
                self._metric_search_event = None
                self.populate()

            self._metric_search_event = Clock.schedule_once(do_populate, 0.2)

    def open_edit_exercise_popup(self, exercise_name, is_user_created):
        """Navigate to ``EditExerciseScreen`` with ``exercise_name`` loaded."""
        app = MDApp.get_running_app()
        if not app or not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = exercise_name
        screen.is_user_created = is_user_created
        screen.section_index = -1
        screen.exercise_index = -1
        screen.previous_screen = "exercise_library"
        app.root.current = "edit_exercise"

    def confirm_delete_exercise(self, exercise_name):
        dialog = None

        def do_delete(*args):
            db_path = DEFAULT_DB_PATH
            try:
                exercises.delete_exercise(
                    exercise_name, db_path=db_path, is_user_created=True
                )
                app = MDApp.get_running_app()
                if app:
                    app.exercise_library_version += 1
            except Exception:
                pass
            self.all_exercises = None
            self.populate()
            if dialog:
                dialog.dismiss()

        dialog = FullScreenDialog(
            title="Delete Exercise?",
            content_cls=MDLabel(
                text=f"Delete {exercise_name}?",
                halign="center",
            ),
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def confirm_delete_metric(self, metric_name):
        dialog = None

        def do_delete(*args):
            db_path = DEFAULT_DB_PATH
            try:
                metrics.delete_metric_type(
                    metric_name, db_path=db_path, is_user_created=True
                )
                app = MDApp.get_running_app()
                if app:
                    app.metric_library_version += 1
            except Exception:
                pass
            self.all_metrics = None
            self.populate()
            if dialog:
                dialog.dismiss()

        dialog = FullScreenDialog(
            title="Delete Metric?",
            content_cls=MDLabel(
                text=f"Delete {metric_name}?",
                halign="center",
            ),
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def new_exercise(self):
        """Open ``EditExerciseScreen`` to create a new exercise."""
        app = MDApp.get_running_app()
        if not app or not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = ""
        screen.is_user_created = True
        screen.section_index = -1
        screen.exercise_index = -1
        screen.previous_screen = "exercise_library"
        app.root.current = "edit_exercise"

    def open_edit_metric_popup(self, metric_name, is_user_created):
        from main import EditMetricTypePopup  # local import to avoid circular dependency

        popup = EditMetricTypePopup(self, metric_name, is_user_created)
        popup.open()

    def new_metric(self):
        from main import EditMetricTypePopup  # local import to avoid circular dependency

        popup = EditMetricTypePopup(self, None, True)
        popup.open()

    def switch_tab(self, tab: str):
        if tab in ("exercises", "metrics"):
            self.current_tab = tab
            if "library_tabs" in self.ids:
                self.ids.library_tabs.current = tab
            self.populate()

    def go_back(self):
        if self.manager:
            self.manager.current = self.previous_screen
