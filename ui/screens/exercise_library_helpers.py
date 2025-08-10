"""Helper functions for :mod:`exercise_library` screen."""

from __future__ import annotations

from typing import Any

from kivymd.app import MDApp
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDRaisedButton


def populate_exercises(screen: Any) -> None:
    if not screen.exercise_list:
        if screen.loading_dialog:
            screen.loading_dialog.dismiss()
            screen.loading_dialog = None
        return
    screen.exercise_list.data = []
    app = MDApp.get_running_app()
    if screen.all_exercises is None or (
        app and screen.cache_version != getattr(app, "exercise_library_version", 0)
    ):
        provider = getattr(screen, "data_provider", None)
        screen.all_exercises = (
            provider.get_all_exercises(include_user_created=True) if provider else []
        )
        if app:
            screen.cache_version = app.exercise_library_version
    exercises = screen.all_exercises or []

    mode = screen.filter_mode
    if mode == "user":
        exercises = [ex for ex in exercises if ex[1]]
    elif mode == "premade":
        exercises = [ex for ex in exercises if not ex[1]]
    if screen.search_text:
        s = screen.search_text.lower()
        exercises = [ex for ex in exercises if s in ex[0].lower()]
    data = []
    for name, is_user in exercises:
        data.append(
            {
                "name": name,
                "text": name,
                "is_user_created": is_user,
                "edit_callback": screen.open_edit_exercise_popup,
                "delete_callback": screen.confirm_delete_exercise,
            }
        )
    screen.exercise_list.data = data
    if screen.loading_dialog:
        screen.loading_dialog.dismiss()
        screen.loading_dialog = None


def populate_metrics(screen: Any) -> None:
    if not screen.metric_list:
        if screen.loading_dialog:
            screen.loading_dialog.dismiss()
            screen.loading_dialog = None
        return
    screen.metric_list.data = []
    app = MDApp.get_running_app()
    if screen.all_metrics is None or (
        app and screen.metric_cache_version != getattr(app, "metric_library_version", 0)
    ):
        provider = getattr(screen, "data_provider", None)
        screen.all_metrics = (
            provider.get_all_metric_types(include_user_created=True) if provider else []
        )
        if app:
            screen.metric_cache_version = app.metric_library_version
    metrics = screen.all_metrics or []
    mode = screen.metric_filter_mode
    if mode == "user":
        metrics = [m for m in metrics if m["is_user_created"]]
    elif mode == "premade":
        metrics = [m for m in metrics if not m["is_user_created"]]
    if screen.metric_search_text:
        s = screen.metric_search_text.lower()
        metrics = [m for m in metrics if s in m["name"].lower()]
    data = []
    for m in metrics:
        data.append(
            {
                "name": m["name"],
                "text": m["name"],
                "is_user_created": m["is_user_created"],
                "edit_callback": screen.open_edit_metric_popup,
                "delete_callback": screen.confirm_delete_metric,
            }
        )
    screen.metric_list.data = data
    if screen.loading_dialog:
        screen.loading_dialog.dismiss()
        screen.loading_dialog = None


def confirm_delete_exercise(screen: Any, exercise_name: str) -> None:
    dialog = None

    def do_delete(*args):
        try:
            provider = getattr(screen, "data_provider", None)
            if provider:
                provider.delete_exercise(exercise_name)
            app = MDApp.get_running_app()
            if app:
                app.exercise_library_version += 1
        except Exception:
            pass
        screen.all_exercises = None
        screen.populate()
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


def confirm_delete_metric(screen: Any, metric_name: str) -> None:
    dialog = None

    def do_delete(*args):
        try:
            provider = getattr(screen, "data_provider", None)
            if provider:
                provider.delete_metric_type(metric_name)
            app = MDApp.get_running_app()
            if app:
                app.metric_library_version += 1
        except Exception:
            pass
        screen.all_metrics = None
        screen.populate()
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
