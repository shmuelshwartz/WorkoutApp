"""Exercise library screen module for WorkoutApp."""

from __future__ import annotations

from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
    ListProperty,
    BooleanProperty,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.list import MDList, OneLineListItem
from kivy.uix.scrollview import ScrollView
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton

import os
from ui.adapters.library_adapter import LibraryAdapter


class ExerciseLibraryScreen(MDScreen):
    """Screen allowing the user to manage exercises and metric types."""

    previous_screen = StringProperty("home")
    exercise_list = ObjectProperty(None)
    metric_list = ObjectProperty(None)
    filter_mode = StringProperty("both")
    metric_filter_mode = StringProperty("both")
    filter_dialog = ObjectProperty(None, allownone=True)
    search_text = StringProperty("")
    metric_search_text = StringProperty("")
    current_tab = StringProperty("exercises")
    test_mode = BooleanProperty(False)
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

    def __init__(self, data_provider=None, router=None, test_mode=False, **kwargs):
        super().__init__(**kwargs)
        self.test_mode = test_mode
        self.router = router
        if data_provider is not None:
            self.data_provider = data_provider
        elif test_mode:
            from ui.stubs.library_data import LibraryStubDataProvider

            self.data_provider = LibraryStubDataProvider()
        else:
            self.data_provider = LibraryAdapter()

    def on_pre_enter(self, *args):
        """Populate the list widgets when the screen is shown."""
        app = MDApp.get_running_app()
        if self.all_exercises is None or (
            app and self.cache_version != getattr(app, "exercise_library_version", 0)
        ):
            self.all_exercises = self.data_provider.get_all_exercises(
                include_user_created=True
            )
            if app:
                self.cache_version = app.exercise_library_version

        if self.all_metrics is None or (
            app
            and self.metric_cache_version != getattr(app, "metric_library_version", 0)
        ):
            self.all_metrics = self.data_provider.get_all_metric_types(
                include_user_created=True
            )
            if app:
                self.metric_cache_version = app.metric_library_version

        self.populate(True)

        return super().on_pre_enter(*args)

    def populate(self, show_loading: bool = False):
        """Populate exercises or metrics depending on current tab."""
        if show_loading and not os.environ.get("KIVY_UNITTEST"):
            from main import LoadingDialog  # local import to avoid circular dependency

            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(self._populate_impl, 0)
        else:
            self._populate_impl()

    def _populate_impl(self, dt: float | None = None):
        if self.current_tab == "exercises":
            self._populate_exercises()
        else:
            self._populate_metrics()

    def _populate_exercises(self):
        if not self.exercise_list:
            if self.loading_dialog:
                self.loading_dialog.dismiss()
                self.loading_dialog = None
            return
        self.exercise_list.data = []
        app = MDApp.get_running_app()
        if self.all_exercises is None or (
            app and self.cache_version != getattr(app, "exercise_library_version", 0)
        ):
            self.all_exercises = self.data_provider.get_all_exercises(
                include_user_created=True
            )
            if app:
                self.cache_version = app.exercise_library_version
        exercises = self.all_exercises or []

        mode = self.filter_mode
        if mode == "user":
            exercises = [ex for ex in exercises if ex[1]]
        elif mode == "premade":
            exercises = [ex for ex in exercises if not ex[1]]
        if self.search_text:
            s = self.search_text.lower()
            exercises = [ex for ex in exercises if s in ex[0].lower()]
        data = []
        for name, is_user in exercises:
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
        if self.loading_dialog:
            self.loading_dialog.dismiss()
            self.loading_dialog = None

    def _populate_metrics(self):
        if not self.metric_list:
            if self.loading_dialog:
                self.loading_dialog.dismiss()
                self.loading_dialog = None
            return
        self.metric_list.data = []
        app = MDApp.get_running_app()
        if self.all_metrics is None or (
            app
            and self.metric_cache_version != getattr(app, "metric_library_version", 0)
        ):
            self.all_metrics = self.data_provider.get_all_metric_types(
                include_user_created=True
            )
            if app:
                self.metric_cache_version = app.metric_library_version
        metrics = self.all_metrics or []
        mode = self.metric_filter_mode
        if mode == "user":
            metrics = [m for m in metrics if m["is_user_created"]]
        elif mode == "premade":
            metrics = [m for m in metrics if not m["is_user_created"]]
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
        if self.loading_dialog:
            self.loading_dialog.dismiss()
            self.loading_dialog = None

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
        if self.test_mode:
            print(f"Edit exercise: {exercise_name}")
            return
        app = MDApp.get_running_app()
        if not app or not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = exercise_name
        screen.is_user_created = is_user_created
        screen.section_index = -1
        screen.exercise_index = -1
        screen.previous_screen = "exercise_library"
        if self.router:
            self.router.navigate("edit_exercise")
        else:
            app.root.current = "edit_exercise"

    def confirm_delete_exercise(self, exercise_name):
        dialog = None

        def do_delete(*args):
            try:
                self.data_provider.delete_exercise(exercise_name)
                app = MDApp.get_running_app()
                if app:
                    app.exercise_library_version += 1
            except Exception:
                pass
            self.all_exercises = None
            self.populate()
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Delete Exercise?",
            text=f"Delete {exercise_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def confirm_delete_metric(self, metric_name):
        dialog = None

        def do_delete(*args):
            try:
                self.data_provider.delete_metric_type(metric_name)
                app = MDApp.get_running_app()
                if app:
                    app.metric_library_version += 1
            except Exception:
                pass
            self.all_metrics = None
            self.populate()
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Delete Metric?",
            text=f"Delete {metric_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()

    def new_exercise(self):
        """Open ``EditExerciseScreen`` to create a new exercise."""
        if self.test_mode:
            print("Create new exercise")
            return
        app = MDApp.get_running_app()
        if not app or not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = ""
        screen.is_user_created = True
        screen.section_index = -1
        screen.exercise_index = -1
        screen.previous_screen = "exercise_library"
        if self.router:
            self.router.navigate("edit_exercise")
        else:
            app.root.current = "edit_exercise"

    def open_edit_metric_popup(self, metric_name, is_user_created):
        if self.test_mode:
            print(f"Edit metric: {metric_name}")
            return
        from main import EditMetricTypePopup  # local import to avoid circular dependency

        popup = EditMetricTypePopup(self, metric_name, is_user_created)
        popup.open()

    def new_metric(self):
        if self.test_mode:
            print("Create new metric")
            return
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
            if self.router:
                self.router.navigate(self.previous_screen)
            elif self.manager:
                self.manager.current = self.previous_screen


if __name__ == "__main__":  # pragma: no cover - manual visual test
    choice = (
        input("Type 1 for single-screen test\nType 2 for flow test\n").strip()
        or "1"
    )
    if choice == "2":
        from ui.testing.runners.flow_runner import run

        run("exercise_library")
    else:
        from kivymd.app import MDApp
        from ui.routers import SingleRouter
        from ui.stubs.library_data import LibraryStubDataProvider

        class _TestApp(MDApp):
            def build(self):
                provider = LibraryStubDataProvider()
                return ExerciseLibraryScreen(
                    data_provider=provider, router=SingleRouter(), test_mode=True
                )

        _TestApp().run()
