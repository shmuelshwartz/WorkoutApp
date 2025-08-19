from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivy.properties import ObjectProperty
from backend import metrics, exercises
from ui.expandable_list_item import ExpandableListItem, ExerciseSummaryItem
from ui.popups import PreSessionMetricPopup



class PresetOverviewScreen(MDScreen):
    """Display an overview of the selected preset."""

    details_list = ObjectProperty(None)
    workout_list = ObjectProperty(None)
    _pre_session_metric_data = None

    def on_pre_enter(self, *args):
        self.populate()
        self._pre_session_metric_data = None
        self._prompt_pre_session_metrics()
        return super().on_pre_enter(*args)

    def populate(self):
        if not self.details_list or not self.workout_list:
            return

        self.details_list.clear_widgets()
        self.workout_list.clear_widgets()

        app = MDApp.get_running_app()
        app.init_preset_editor()
        preset_name = app.selected_preset

        editor = app.preset_editor
        if not editor:
            return

        # Populate details tab with preset metrics and section summaries
        for metric in editor.preset_metrics:
            if metric.get("scope") == "preset":
                value = metric.get("value")
                text = (
                    f"{metric['name']}: {value}"
                    if value is not None
                    else metric["name"]
                )
                self.details_list.add_widget(ExpandableListItem(text=text))

        for section in editor.sections:
            self.details_list.add_widget(
                ExpandableListItem(text=f"Section: {section['name']}")
            )
            for ex in section.get("exercises", []):
                sets = ex.get("sets", 0) or 0
                self.details_list.add_widget(
                    ExerciseSummaryItem(name=ex["name"], sets=sets)
                )

        # Populate workout tab with full exercise details
        for section in editor.sections:
            for ex in section.get("exercises", []):
                desc_info = exercises.get_exercise_details(ex["name"])
                desc = desc_info.get("description", "") if desc_info else ""
                sets = ex.get("sets", 0) or 0
                rest = ex.get("rest", 0) or 0
                metric_defs = metrics.get_metrics_for_exercise(
                    ex["name"], preset_name=preset_name
                )
                metric_names = ", ".join(m["name"] for m in metric_defs)
                lines = [ex["name"], f"sets {sets} | rest: {rest}s", desc]
                if metric_names:
                    lines.append(metric_names)
                text = "\n".join(lines)
                self.workout_list.add_widget(ExpandableListItem(text=text))

    def start_workout(self):
        app = MDApp.get_running_app()
        preset_name = app.selected_preset
        app.start_workout(preset_name)
        if app.workout_session and self._pre_session_metric_data:
            app.workout_session.set_session_metrics(self._pre_session_metric_data)
            self._pre_session_metric_data = None
        if self.manager:
            self.manager.current = "rest"

    def open_metric_popup(self):
        self._prompt_pre_session_metrics(force=True)

    def _prompt_pre_session_metrics(self, force: bool = False):
        if self._pre_session_metric_data is not None and not force:
            return
        app = MDApp.get_running_app()
        preset_name = app.selected_preset
        metric_defs = metrics.get_metrics_for_preset(preset_name)
        pre_metrics = [m for m in metric_defs if m.get("input_timing") == "pre_session"]
        if pre_metrics:
            popup = PreSessionMetricPopup(
                pre_metrics, lambda data: self._store_session_metrics(data)
            )
            popup.open()

    def _store_session_metrics(self, data):
        self._pre_session_metric_data = data
