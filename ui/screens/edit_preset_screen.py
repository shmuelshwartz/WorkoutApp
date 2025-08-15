"""Edit preset screen and related widgets."""

from __future__ import annotations

from kivymd.app import MDApp
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.properties import (
    NumericProperty,
    StringProperty,
    ObjectProperty,
    BooleanProperty,
    ListProperty,
)
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList, OneLineListItem
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.dialog import MDDialog
import os
import sqlite3

from backend import metrics, exercises
from backend.presets import load_workout_presets
from core import DEFAULT_DB_PATH, DEFAULT_SETS_PER_EXERCISE


class SectionWidget(MDBoxLayout):
    """Single preset section containing exercises."""

    section_name = StringProperty("Section")
    section_index = NumericProperty(0)
    color = ListProperty([1, 1, 1, 1])
    expanded = BooleanProperty(True)
    visible = BooleanProperty(True)
    locked = BooleanProperty(False)

    def on_section_name(self, instance, value):
        """Update the section name in the preset editor."""
        if self.locked:
            return
        app = MDApp.get_running_app()
        if app and app.preset_editor:
            try:
                app.preset_editor.rename_section(self.section_index, value)
            except IndexError:
                return
            edit = app.root.get_screen("edit_preset") if app.root else None
            if edit:
                edit.update_save_enabled()

    def toggle(self):
        self.expanded = not self.expanded

    def open_exercise_selection(self):
        if self.locked:
            return
        app = MDApp.get_running_app()
        app.editing_section_index = self.section_index
        if app.root:
            edit = app.root.get_screen("edit_preset")
            edit.show_only_section(self.section_index)
            edit.open_exercise_panel()

    def refresh_exercises(self):
        app = MDApp.get_running_app()
        if not app.preset_editor:
            return
        if self.section_index >= len(app.preset_editor.sections):
            return
        box = self.ids.exercise_list
        box.clear_widgets()
        edit = app.root.get_screen("edit_preset") if app.root else None
        for idx, ex in enumerate(
            app.preset_editor.sections[self.section_index]["exercises"]
        ):
            locked = self.locked
            if edit:
                locked = locked or edit._is_exercise_locked(self.section_index, idx)
            box.add_widget(
                SelectedExerciseItem(
                    text=ex["name"],
                    section_index=self.section_index,
                    exercise_index=idx,
                    locked=locked,
                )
            )

    def _update_indices(self) -> None:
        """Update ``exercise_index`` on child widgets to match their order."""
        box = self.ids.exercise_list
        for idx, child in enumerate(reversed(box.children)):
            if isinstance(child, SelectedExerciseItem):
                child.exercise_index = idx

    def move_exercise_widget(self, old_index: int, new_index: int) -> None:
        """Reorder displayed exercise widgets without rebuilding them."""
        box = self.ids.exercise_list
        children = list(reversed(box.children))
        if (
            old_index < 0
            or new_index < 0
            or old_index >= len(children)
            or new_index >= len(children)
        ):
            return
        widget = children[old_index]
        box.remove_widget(widget)
        insert_pos = len(box.children) - new_index
        box.add_widget(widget, index=insert_pos)
        self._update_indices()

    def add_exercise_widget(self, name: str, idx: int) -> None:
        """Append a single exercise widget to the list."""
        box = self.ids.exercise_list
        edit = MDApp.get_running_app().root.get_screen("edit_preset") if MDApp.get_running_app().root else None
        locked = self.locked
        if edit:
            locked = locked or edit._is_exercise_locked(self.section_index, idx)
        box.add_widget(
            SelectedExerciseItem(
                text=name,
                section_index=self.section_index,
                exercise_index=idx,
                locked=locked,
            )
        )

    def confirm_delete(self):
        if self.locked:
            return
        dialog = None

        def do_delete(*args):
            app = MDApp.get_running_app()
            if app.preset_editor:
                app.preset_editor.remove_section(self.section_index)
            if app.root:
                edit = app.root.get_screen("edit_preset")
                edit.refresh_sections()
                edit.update_save_enabled()
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Remove Section?",
            text=f"Delete {self.section_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()


class EditPresetScreen(MDScreen):
    """Screen to edit a workout preset."""

    preset_name = StringProperty("Preset")
    sections_box = ObjectProperty(None)
    panel_visible = BooleanProperty(False)
    exercise_panel = ObjectProperty(None)
    details_box = ObjectProperty(None)
    current_tab = StringProperty("sections")
    metrics_box = ObjectProperty(None)
    session_metric_list = ObjectProperty(None)
    save_enabled = BooleanProperty(False)
    loading_dialog = ObjectProperty(None, allownone=True)
    mode = StringProperty("library")

    preset_metric_widgets: dict = {}

    _colors = [
        (1, 0.9, 0.9, 1),
        (0.9, 1, 0.9, 1),
        (0.9, 0.9, 1, 1),
        (1, 1, 0.9, 1),
        (0.9, 1, 1, 1),
        (1, 0.9, 1, 1),
    ]

    def __init__(self, mode: str = "library", **kwargs):
        super().__init__(**kwargs)
        self.mode = mode

    def update_save_enabled(self):
        """Refresh ``save_enabled`` based on preset modifications."""
        app = MDApp.get_running_app()
        if app and app.preset_editor:
            self.save_enabled = app.preset_editor.is_modified()
        else:
            self.save_enabled = False

    def on_pre_enter(self, *args):
        app = MDApp.get_running_app()
        if app and app.editing_exercise_index >= 0:
            self.preset_name = app.preset_editor.preset_name or "Preset"
            self.current_tab = "sections"
            if self.sections_box:
                for widget in self.sections_box.children:
                    if (
                        isinstance(widget, SectionWidget)
                        and widget.section_index == app.editing_section_index
                    ):
                        widget.refresh_exercises()
                        break
            self.update_save_enabled()
            app.editing_section_index = -1
            app.editing_exercise_index = -1
            return super().on_pre_enter(*args)

        if os.environ.get("KIVY_UNITTEST"):
            self._load_preset()
        else:
            from main import LoadingDialog  # local import to avoid circular dependency

            self.loading_dialog = LoadingDialog()
            self.loading_dialog.open()
            Clock.schedule_once(lambda dt: self._load_preset(), 0)
        return super().on_pre_enter(*args)

    def _load_preset(self):
        app = MDApp.get_running_app()
        if self.mode == "session":
            self.preset_name = (
                app.preset_editor.preset_name if app.preset_editor else "Preset"
            )
            self.current_tab = "sections"
            if self.sections_box:
                self.sections_box.clear_widgets()
                for idx, sec in enumerate(app.preset_editor.sections):
                    locked = self._is_section_locked(idx)
                    self.add_section(sec["name"], index=idx, locked=locked)
                if not app.preset_editor.sections:
                    self.add_section()
            self.update_save_enabled()
        else:
            app.init_preset_editor()
            self.preset_name = app.preset_editor.preset_name or "Preset"
            self.current_tab = "sections"
            if self.sections_box:
                self.sections_box.clear_widgets()
                for idx, sec in enumerate(app.preset_editor.sections):
                    self.add_section(sec["name"], index=idx)
                if not app.preset_editor.sections:
                    self.add_section()
            self.update_save_enabled()
        if self.loading_dialog:
            self.loading_dialog.dismiss()
            self.loading_dialog = None

    def _is_section_locked(self, section_index: int) -> bool:
        """Return ``True`` if the section at ``section_index`` is locked."""
        if self.mode != "session":
            return False
        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)
        if not session:
            return False
        if section_index >= len(session.section_starts):
            return False
        start = session.section_starts[section_index]
        end = (
            session.section_starts[section_index + 1]
            if section_index + 1 < len(session.section_starts)
            else len(session.exercises)
        )
        if session.current_exercise >= end:
            return True
        if start <= session.current_exercise < end and session.current_set > 0:
            return True
        return False

    def _is_exercise_locked(self, section_index: int, exercise_index: int) -> bool:
        """Return ``True`` if the exercise is locked."""
        if self.mode != "session":
            return False
        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)
        if not session:
            return False
        if section_index >= len(session.section_starts):
            return False
        global_index = session.section_starts[section_index] + exercise_index
        if global_index < session.current_exercise:
            return True
        if global_index == session.current_exercise and session.current_set > 0:
            return True
        return False

    def apply_session_changes(self):
        """Merge edits back into the active workout session."""
        app = MDApp.get_running_app()
        session = getattr(app, "workout_session", None)
        editor = getattr(app, "preset_editor", None)
        if not session or not editor:
            return
        session.apply_edited_preset(editor.sections)


    def refresh_sections(self):
        """Repopulate the section widgets from the preset editor."""
        app = MDApp.get_running_app()
        if not self.sections_box:
            return
        self.sections_box.clear_widgets()
        for idx, sec in enumerate(app.preset_editor.sections):
            locked = self._is_section_locked(idx)
            self.add_section(sec["name"], index=idx, locked=locked)
        if not app.preset_editor.sections:
            self.add_section()

    def open_exercise_panel(self):
        if self.exercise_panel:
            self.exercise_panel.on_open()
        self.panel_visible = True

    def close_exercise_panel(self):
        if self.exercise_panel:
            self.exercise_panel.save_selection()
        self.panel_visible = False
        self.show_all_sections()
        self.update_save_enabled()

    def show_only_section(self, index: int):
        """Hide all sections except the one with ``index``."""
        if not self.sections_box:
            return
        for child in list(self.sections_box.children):
            if isinstance(child, SectionWidget):
                child.visible = child.section_index == index

    def show_all_sections(self):
        """Make all section widgets visible."""
        if not self.sections_box:
            return
        for child in list(self.sections_box.children):
            if isinstance(child, SectionWidget):
                child.visible = True

    def add_section(
        self,
        name: str | None = None,
        index: int | None = None,
        locked: bool = False,
    ):
        """Add a new section to the preset and return the widget."""
        if not self.sections_box:
            return None
        app = MDApp.get_running_app()
        if index is None:
            if not name:
                name = f"Section {len(app.preset_editor.sections) + 1}"
            index = app.preset_editor.add_section(name)
        color = self._colors[len(self.sections_box.children) % len(self._colors)]
        section = SectionWidget(
            section_index=index, section_name=name, color=color, locked=locked
        )
        self.sections_box.add_widget(section)
        section.refresh_exercises()
        self.update_save_enabled()
        return section

    def switch_tab(self, tab: str):
        """Switch between the sections, details, and metrics tabs."""
        if tab in ("sections", "details", "metrics"):
            self.current_tab = tab
            if tab == "details":
                self.populate_details()
            elif tab == "metrics":
                self.populate_metrics()

    def update_preset_name(self, name: str):
        """Update the preset name in the editor."""
        self.preset_name = name
        app = MDApp.get_running_app()
        if app.preset_editor:
            app.preset_editor.preset_name = name
        self.update_save_enabled()

    def populate_details(self):
        if not self.details_box or not self.metrics_box:
            return
        self.ids.preset_name.text = self.preset_name
        preset_row = self.ids.get("preset_name_row")

        # Ensure the preset name row is present in the layout
        if preset_row is not None:
            if preset_row.parent and preset_row.parent is not self.details_box:
                preset_row.parent.remove_widget(preset_row)
            if preset_row not in self.details_box.children:
                self.details_box.add_widget(preset_row, index=len(self.details_box.children))

        # Clear previous metric widgets without touching the preset name row
        if self.metrics_box:
            self.metrics_box.clear_widgets()


        self.preset_metric_widgets = {}
        app = MDApp.get_running_app()
        metrics = []
        if app and app.preset_editor:
            metrics = [
                m
                for m in app.preset_editor.preset_metrics
                if m.get("input_timing") == "preset" and m.get("scope") == "preset"
            ]

        for m in metrics:
            name = m.get("metric_name") or m.get("name")
            mtype = m.get("type")
            enum_vals = m.get("values") or []
            value = m.get("value")

            row = MDBoxLayout(size_hint_y=None, height="40dp")
            row.add_widget(MDLabel(text=name, size_hint_x=0.4))

            if mtype == "slider":
                widget = MDSlider(min=0, max=1, value=float(value or 0))
            elif mtype == "enum":
                default = str(value if value is not None else (enum_vals[0] if enum_vals else ""))
                widget = Spinner(text=default, values=enum_vals)
            elif mtype == "bool":
                widget = MDCheckbox(active=bool(value))
            else:
                input_filter = None
                if mtype == "int":
                    input_filter = "int"
                elif mtype == "float":
                    input_filter = "float"
                widget = MDTextField(text=str(value if value is not None else ""), multiline=False, input_filter=input_filter)
                if self.mode == "session":
                    widget.readonly = True

            if self.mode == "session" and not isinstance(widget, MDTextField):
                widget.disabled = True

            self.preset_metric_widgets[name] = widget

            def _on_change(instance, *a, metric=name, it=mtype):
                val = None
                if isinstance(instance, MDTextField):
                    val = instance.text
                elif isinstance(instance, MDSlider):
                    val = instance.value
                elif isinstance(instance, Spinner):
                    val = instance.text
                elif isinstance(instance, MDCheckbox):
                    val = instance.active
                if it == "int":
                    try:
                        val = int(val)
                    except Exception:
                        val = 0
                elif it == "float":
                    try:
                        val = float(val)
                    except Exception:
                        val = 0.0
                if app and app.preset_editor is not None:
                    app.preset_editor.update_metric(metric, value=val)
                self.update_save_enabled()

            if isinstance(widget, MDTextField):
                widget.bind(text=_on_change)
            elif isinstance(widget, MDSlider):
                widget.bind(value=_on_change)
            elif isinstance(widget, Spinner):
                widget.bind(text=_on_change)
            elif isinstance(widget, MDCheckbox):
                widget.bind(active=_on_change)

            row.add_widget(widget)
            if self.metrics_box:
                self.metrics_box.add_widget(row)

        # Ensure the preset name remains visible when entering the tab
        if "details_scroll" in self.ids:
            self.ids.details_scroll.scroll_y = 1

    def populate_metrics(self):
        """Populate the Metrics tab with session-scoped metrics."""
        rv = self.ids.get("session_metric_list")
        if not rv:
            return

        app = MDApp.get_running_app()
        metrics = []
        if app and app.preset_editor:
            metrics = [
                m
                for m in app.preset_editor.preset_metrics
                if m.get("scope") == "session"
            ]

        all_defs = {
            m["name"]: m
            for m in metrics.get_all_metric_types(include_user_created=True)
        }

        rv.data = [
            {
                "name": m.get("metric_name") or m.get("name"),
                "text": m.get("metric_name") or m.get("name"),
                "is_user_created": all_defs.get(
                    m.get("metric_name") or m.get("name"),
                    {},
                ).get(
                    "is_user_created", False
                ),
                "locked": self.mode == "session",
            }
            for m in metrics
        ]

    def open_add_preset_metric_popup(self):
        popup = AddPresetMetricPopup(self)
        popup.open()

    def open_add_session_metric_popup(self):
        popup = AddSessionMetricPopup(self)
        popup.open()

    def save_preset(self):
        app = MDApp.get_running_app()
        if not app.preset_editor:
            return

        try:
            # Validate before confirmation to show immediate error
            app.preset_editor.validate()
        except ValueError as exc:

            dialog = MDDialog(
                title="Error",
                text=str(exc),
                buttons=[
                    MDRaisedButton(text="OK", on_release=lambda *a: dialog.dismiss())
                ],
            )
            dialog.open()
            return

        dialog = None

        def do_confirm(*args):
            try:
                app.preset_editor.save()
                load_workout_presets(app.preset_editor.db_path)
                app.selected_preset = app.preset_editor.preset_name
                if dialog:
                    dialog.dismiss()
                if self.manager:
                    self.manager.current = "presets"
            except Exception as err:
                err_dialog = MDDialog(
                    title="Error",
                    text=str(err),
                    buttons=[
                        MDRaisedButton(
                            text="OK", on_release=lambda *a: err_dialog.dismiss()
                        )
                    ],
                )
                err_dialog.open()

        dialog = MDDialog(
            title="Confirm Save",
            text=f"Save changes to {app.preset_editor.preset_name}?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Save", on_release=do_confirm),
            ],
        )
        dialog.open()

    def go_back(self):
        app = MDApp.get_running_app()
        if self.mode == "session":
            self.apply_session_changes()
            if self.manager:
                self.manager.current = "rest"
            self.mode = "library"
        else:
            if app.preset_editor and app.preset_editor.is_modified():
                dialog = None

                def discard(*args):
                    if dialog:
                        dialog.dismiss()
                    app.init_preset_editor(force_reload=True)
                    if self.manager:
                        self.manager.current = "presets"

                dialog = MDDialog(
                    title="Discard Changes?",
                    text="You have unsaved changes. Discard them?",
                    buttons=[
                        MDRaisedButton(
                            text="Cancel", on_release=lambda *a: dialog.dismiss()
                        ),
                        MDRaisedButton(text="Discard", on_release=discard),
                    ],
                )
                dialog.open()
            else:
                if self.manager:
                    self.manager.current = "presets"


class SelectedExerciseItem(MDBoxLayout):
    """Widget representing a selected exercise with reorder controls."""

    text = StringProperty("")
    section_index = NumericProperty(0)
    exercise_index = NumericProperty(0)
    locked = BooleanProperty(False)

    def edit(self):
        """Open the EditExerciseScreen for this exercise."""
        if self.locked:
            return
        app = MDApp.get_running_app()
        if not app.root:
            return
        screen = app.root.get_screen("edit_exercise")
        screen.exercise_name = self.text
        screen.section_index = self.section_index
        screen.exercise_index = self.exercise_index
        screen.previous_screen = "edit_preset"
        app.editing_section_index = self.section_index
        app.editing_exercise_index = self.exercise_index
        app.root.current = "edit_exercise"

    def move_up(self):
        if self.locked:
            return
        app = MDApp.get_running_app()
        if not app or not app.preset_editor:
            return
        if self.exercise_index <= 0:
            return
        app.preset_editor.move_exercise(
            self.section_index, self.exercise_index, self.exercise_index - 1
        )
        edit = app.root.get_screen("edit_preset") if app.root else None
        if edit:
            for widget in edit.sections_box.children:
                if (
                    isinstance(widget, SectionWidget)
                    and widget.section_index == self.section_index
                ):
                    widget.move_exercise_widget(
                        self.exercise_index, self.exercise_index - 1
                    )
                    break
            edit.update_save_enabled()

    def move_down(self):
        if self.locked:
            return
        app = MDApp.get_running_app()
        if not app or not app.preset_editor:
            return
        sec = app.preset_editor.sections[self.section_index]
        if self.exercise_index >= len(sec["exercises"]) - 1:
            return
        app.preset_editor.move_exercise(
            self.section_index, self.exercise_index, self.exercise_index + 1
        )
        edit = app.root.get_screen("edit_preset") if app.root else None
        if edit:
            for widget in edit.sections_box.children:
                if (
                    isinstance(widget, SectionWidget)
                    and widget.section_index == self.section_index
                ):
                    widget.move_exercise_widget(
                        self.exercise_index, self.exercise_index + 1
                    )
                    break
            edit.update_save_enabled()

    def remove_self(self):
        if self.locked:
            return
        dialog = None

        def do_delete(*args):
            app = MDApp.get_running_app()
            if app and app.preset_editor:
                app.preset_editor.remove_exercise(
                    self.section_index, self.exercise_index
                )
                edit = app.root.get_screen("edit_preset") if app.root else None
                if edit:
                    for widget in edit.sections_box.children:
                        if (
                            isinstance(widget, SectionWidget)
                            and widget.section_index == self.section_index
                        ):
                            widget.refresh_exercises()
                            break
                    edit.update_save_enabled()
            if dialog:
                dialog.dismiss()

        dialog = MDDialog(
            title="Remove Exercise?",
            text=f"Delete {self.text} from this workout?",
            buttons=[
                MDRaisedButton(text="Cancel", on_release=lambda *a: dialog.dismiss()),
                MDRaisedButton(text="Delete", on_release=do_delete),
            ],
        )
        dialog.open()


class ExerciseSelectionPanel(MDBoxLayout):
    """Panel for selecting exercises to add to a preset section."""

    exercise_list = ObjectProperty(None)
    filter_mode = StringProperty("both")
    filter_dialog = ObjectProperty(None, allownone=True)
    search_text = StringProperty("")
    all_exercises = ListProperty(None, allownone=True)
    cache_version = NumericProperty(-1)

    _search_event = None

    def on_open(self):
        self.populate_exercises()

    def populate_exercises(self):
        if not self.exercise_list:
            return
        self.exercise_list.clear_widgets()

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

        exercises = self.all_exercises or []
        if self.filter_mode == "user":
            exercises = [ex for ex in exercises if ex[1]]
        elif self.filter_mode == "premade":
            exercises = [ex for ex in exercises if not ex[1]]
        if self.search_text:
            s = self.search_text.lower()
            exercises = [ex for ex in exercises if s in ex[0].lower()]

        for name, is_user in exercises:
            item = OneLineListItem(
                text=name,
                theme_text_color="Custom",
                text_color=(0.6, 0.2, 0.8, 1) if is_user else (0, 0, 0, 1),
            )
            item.bind(on_release=lambda inst, n=name: self.select_exercise(n))
            self.exercise_list.add_widget(item)

    def select_exercise(self, name):
        """Add ``name`` to the current section."""
        app = MDApp.get_running_app()
        idx = app.editing_section_index
        if app.preset_editor and 0 <= idx < len(app.preset_editor.sections):
            try:
                app.preset_editor.add_exercise(idx, name)
            except Exception as err:
                err_dialog = MDDialog(
                    title="Error",
                    text=str(err),
                    buttons=[
                        MDRaisedButton(
                            text="OK",
                            on_release=lambda *a: err_dialog.dismiss(),
                        )
                    ],
                )
                err_dialog.open()
                return
            ex_idx = len(app.preset_editor.sections[idx]["exercises"]) - 1
            edit = app.root.get_screen("edit_preset")
            for widget in edit.sections_box.children:
                if isinstance(widget, SectionWidget) and widget.section_index == idx:
                    widget.add_exercise_widget(name, ex_idx)
                    break
            edit.update_save_enabled()

    def save_selection(self):
        """No-op kept for API compatibility."""
        pass

    def open_filter_popup(self):
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
        self.filter_dialog = MDDialog(
            title="Filter Exercises",
            type="custom",
            content_cls=scroll,
            buttons=[close_btn],
        )
        self.filter_dialog.open()

    def update_search(self, text):
        self.search_text = text
        if self._search_event:
            self._search_event.cancel()

        def do_populate(dt):
            self._search_event = None
            self.populate_exercises()

        self._search_event = Clock.schedule_once(do_populate, 0.2)

    def apply_filter(self, mode, *args):
        self.filter_mode = mode
        if self.filter_dialog:
            self.filter_dialog.dismiss()
            self.filter_dialog = None
        self.populate_exercises()


class AddPresetMetricPopup(MDDialog):
    """Popup for adding preset-level metrics."""

    def __init__(self, screen: "EditPresetScreen", **kwargs):
        self.screen = screen
        content, buttons = self._build_widgets()
        super().__init__(
            title="Select Metric", type="custom", content_cls=content, buttons=buttons, **kwargs
        )

    def _build_widgets(self):
        app = MDApp.get_running_app()
        existing = set()
        if app and app.preset_editor:
            existing = {
                m.get("metric_name") or m.get("name")
                for m in app.preset_editor.preset_metrics
            }
        metrics = [
            m
            for m in metrics.get_all_metric_types()
            if m.get("scope") == "preset" and (
                m.get("name") not in existing and m.get("metric_name") not in existing
            )
        ]

        list_view = MDList()
        for m in metrics:
            item = OneLineListItem(text=m["name"])
            item.bind(on_release=lambda inst, name=m["name"]: self.add_metric(name))
            list_view.add_widget(item)

        scroll = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        scroll.add_widget(list_view)

        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        buttons = [cancel_btn]
        return scroll, buttons

    def add_metric(self, name, *args):
        app = MDApp.get_running_app()
        if app and app.preset_editor:
            app.preset_editor.add_metric(name)
        self.dismiss()
        self.screen.populate_details()
        self.screen.update_save_enabled()


class AddSessionMetricPopup(MDDialog):
    """Popup for adding session-level metrics."""

    def __init__(self, screen: "EditPresetScreen", **kwargs):
        self.screen = screen
        content, buttons = self._build_widgets()
        super().__init__(
            title="Select Metric",
            type="custom",
            content_cls=content,
            buttons=buttons,
            **kwargs,
        )

    def _build_widgets(self):
        app = MDApp.get_running_app()
        existing = set()
        if app and app.preset_editor:
            existing = {
                m.get("metric_name") or m.get("name")
                for m in app.preset_editor.preset_metrics
            }
        metrics = [
            m
            for m in metrics.get_all_metric_types()
            if m.get("scope") == "session" and (
                m.get("name") not in existing and m.get("metric_name") not in existing
            )
        ]

        list_view = MDList()
        for m in metrics:
            item = OneLineListItem(text=m["name"])
            item.bind(on_release=lambda inst, name=m["name"]: self.add_metric(name))
            list_view.add_widget(item)

        scroll = ScrollView(do_scroll_y=True, size_hint_y=None, height=dp(400))
        scroll.add_widget(list_view)

        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *a: self.dismiss())
        buttons = [cancel_btn]
        return scroll, buttons

    def add_metric(self, name, *args):
        app = MDApp.get_running_app()
        if app and app.preset_editor:
            app.preset_editor.add_metric(name)
        self.dismiss()
        self.screen.populate_metrics()
        self.screen.update_save_enabled()

