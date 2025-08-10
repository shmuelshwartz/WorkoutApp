"""Exercise library screen module for WorkoutApp.

Expected ``data_provider`` interface::

    get_all_exercises(include_user_created=True) -> list[tuple[str, bool]]
    get_all_metric_types(include_user_created=True) -> list[dict]
    delete_exercise(name: str) -> None
    delete_metric_type(name: str) -> None
"""

from __future__ import annotations

from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
    ListProperty,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDList, OneLineListItem
from kivy.uix.scrollview import ScrollView
import os
try:  # pragma: no cover - support running as script
    from .exercise_library_helpers import (
        populate_exercises as _populate_exercises_helper,
        populate_metrics as _populate_metrics_helper,
        confirm_delete_exercise as _confirm_delete_exercise_helper,
        confirm_delete_metric as _confirm_delete_metric_helper,
    )
except Exception:  # pragma: no cover - direct script execution
    from exercise_library_helpers import (
        populate_exercises as _populate_exercises_helper,
        populate_metrics as _populate_metrics_helper,
        confirm_delete_exercise as _confirm_delete_exercise_helper,
        confirm_delete_metric as _confirm_delete_metric_helper,
    )


class ExerciseLibraryScreen(MDScreen):
    """Screen allowing the user to manage exercises and metric types."""

    def __init__(self, data_provider=None, test_mode: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.test_mode = test_mode
        if data_provider is not None:
            self.data_provider = data_provider
        elif test_mode:
            from ui.stubs.exercise_library import StubExerciseLibraryProvider

            self.data_provider = StubExerciseLibraryProvider()
        else:
            self.data_provider = None

    previous_screen = StringProperty("home")
    exercise_list = ObjectProperty(None)
    metric_list = ObjectProperty(None)
    filter_mode = StringProperty("both")
    metric_filter_mode = StringProperty("both")
    filter_dialog = ObjectProperty(None, allownone=True)
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
        app = MDApp.get_running_app()
        if self.all_exercises is None or (
            app and self.cache_version != getattr(app, "exercise_library_version", 0)
        ):
            provider = getattr(self, "data_provider", None)
            self.all_exercises = (
                provider.get_all_exercises(include_user_created=True)
                if provider
                else []
            )
            if app:
                self.cache_version = app.exercise_library_version

        if self.all_metrics is None or (
            app
            and self.metric_cache_version != getattr(app, "metric_library_version", 0)
        ):
            provider = getattr(self, "data_provider", None)
            self.all_metrics = (
                provider.get_all_metric_types(include_user_created=True)
                if provider
                else []
            )
            if app:
                self.metric_cache_version = app.metric_library_version

        self.populate(True)

        return super().on_pre_enter(*args)

    def populate(self, show_loading: bool = False):
        """Populate exercises or metrics depending on current tab."""
        if show_loading and not os.environ.get("KIVY_UNITTEST"):
            try:
                from main import LoadingDialog  # local import to avoid circular dependency
            except Exception:  # pragma: no cover - preview fallback
                LoadingDialog = None

            if LoadingDialog:
                self.loading_dialog = LoadingDialog()
                self.loading_dialog.open()
                Clock.schedule_once(self._populate_impl, 0)
                return
        self._populate_impl()

    def _populate_impl(self, dt: float | None = None):
        if self.current_tab == "exercises":
            self._populate_exercises()
        else:
            self._populate_metrics()

    def _populate_exercises(self):
        _populate_exercises_helper(self)

    def _populate_metrics(self):
        _populate_metrics_helper(self)

    def open_filter_popup(self):
        """Open the filter dialog."""
        list_view = MDList()
        options = [
            ("User Created", "user"),
            ("Premade", "premade"),
            ("Both", "both"),
        ]
        for label, mode in options:
            item = OneLineListItem(text=label)
            item.bind(on_release=lambda inst, m=mode: self.apply_filter(m))
            list_view.add_widget(item)
        scroll = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(200))
        scroll.add_widget(list_view)
        close_btn = MDRaisedButton(
            text="Close", on_release=lambda *a: self.filter_dialog.dismiss()
        )
        title = (
            "Filter Exercises" if self.current_tab == "exercises" else "Filter Metrics"
        )
        self.filter_dialog = MDDialog(
            title=title, type="custom", content_cls=scroll, buttons=[close_btn]
        )
        self.filter_dialog.open()

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

    def apply_filter(self, mode, *args):
        if self.current_tab == "exercises":
            self.filter_mode = mode
        else:
            self.metric_filter_mode = mode
        if self.filter_dialog:
            self.filter_dialog.dismiss()
            self.filter_dialog = None
        self.populate()

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
        _confirm_delete_exercise_helper(self, exercise_name)

    def confirm_delete_metric(self, metric_name):
        _confirm_delete_metric_helper(self, metric_name)

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
        try:
            from main import EditMetricTypePopup  # local import to avoid circular dependency
        except Exception:  # pragma: no cover - preview fallback
            EditMetricTypePopup = None

        if EditMetricTypePopup:
            popup = EditMetricTypePopup(self, metric_name, is_user_created)
            popup.open()

    def new_metric(self):
        try:
            from main import EditMetricTypePopup  # local import to avoid circular dependency
        except Exception:  # pragma: no cover - preview fallback
            EditMetricTypePopup = None

        if EditMetricTypePopup:
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


if __name__ == "__main__":
    class _ExerciseLibraryApp(MDApp):
        def build(self):  # pragma: no cover - manual testing
            return ExerciseLibraryScreen(test_mode=True)

    _ExerciseLibraryApp().run()
