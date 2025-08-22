"""Full-screen dialog for entering pre-session metrics.

Migrated from :mod:`ui.popups` and now implemented as an ``MDScreen``
that overlays the current app screen.
"""

from __future__ import annotations

from kivy.core.window import Window
from kivy.metrics import dp
from kivy.properties import StringProperty
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.label import MDLabel
from kivymd.uix.list import MDList
from kivymd.uix.screen import MDScreen
from kivymd.uix.slider import MDSlider
from kivymd.uix.textfield import MDTextField


class PreSessionMetricPopup(MDScreen):
    """Screen-based dialog for collecting pre-session metrics."""

    previous_screen = StringProperty()

    def __init__(self, metrics: list[dict], on_save, previous_screen: str, **kwargs):
        super().__init__(**kwargs)
        self.metrics = metrics
        self.on_save = on_save
        self.previous_screen = previous_screen
        self._build_ui()

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------
    def on_pre_enter(self, *args):  # pragma: no cover - requires Kivy
        Window.bind(on_keyboard=self._handle_keyboard)
        return super().on_pre_enter(*args)

    def on_pre_leave(self, *args):  # pragma: no cover - requires Kivy
        Window.unbind(on_keyboard=self._handle_keyboard)
        return super().on_pre_leave(*args)

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def open(self, *_):  # pragma: no cover - requires Kivy
        from kivymd.app import MDApp

        app = MDApp.get_running_app()
        if not self.name:
            self.name = f"_dialog_{id(self)}"
        app.root.add_widget(self)
        app.root.current = self.name

    def close(self, *args):  # pragma: no cover - requires Kivy
        if self.manager:
            self.manager.current = self.previous_screen

    def _handle_keyboard(self, _window, key, *_):  # pragma: no cover - requires Kivy
        if key in (27, 1001):  # ESC or Android back
            self.close()
            return True
        return False

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8))

        header = MDLabel(
            text="Session Metrics",
            size_hint_y=None,
            height=dp(48),
            halign="center",
            valign="center",
        )
        header.bind(size=header.setter("text_size"))
        layout.add_widget(header)

        self.metric_list = MDList(adaptive_height=True)
        self.metric_list.bind(minimum_height=self.metric_list.setter("height"))
        for m in self.metrics:
            self.metric_list.add_widget(self._create_row(m))
        scroll = ScrollView(do_scroll_y=True, size_hint=(1, 1))
        scroll.add_widget(self.metric_list)
        layout.add_widget(scroll)

        button_box = MDBoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(8),
            padding=(dp(8), dp(8)),
        )
        save_btn = MDRaisedButton(text="Save", on_release=lambda *_: self._on_save())
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *_: self.close())
        button_box.add_widget(save_btn)
        button_box.add_widget(cancel_btn)
        layout.add_widget(button_box)

        self.add_widget(layout)

    # ------------------------------------------------------------------
    # Data handling
    # ------------------------------------------------------------------
    def _create_row(self, metric):
        name = metric.get("name")
        mtype = metric.get("type", "str")
        values = metric.get("values", [])
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
        row.metric_name = name
        row.type = mtype
        row.required = metric.get("is_required", False)
        row.add_widget(MDLabel(text=name, size_hint_x=0.4))
        default = metric.get("value")
        if mtype == "slider":
            widget = MDSlider(min=0, max=1, value=default or 0)
        elif mtype == "enum":
            text = default if default not in (None, "") else (values[0] if values else "")
            widget = Spinner(text=text, values=values)
        else:
            input_filter = None
            if mtype == "int":
                input_filter = "int"
            elif mtype == "float":
                input_filter = "float"
            text = "" if default in (None, "") else str(default)
            widget = MDTextField(multiline=False, input_filter=input_filter, text=text)
        row.input_widget = widget
        row.add_widget(widget)
        return row

    def _collect(self):
        data = {}
        valid = True
        for row in reversed(self.metric_list.children):
            name = getattr(row, "metric_name", "")
            widget = getattr(row, "input_widget", None)
            mtype = getattr(row, "type", "str")
            required = getattr(row, "required", False)
            value = None
            if isinstance(widget, MDTextField):
                text = widget.text.strip()
                if required and text == "":
                    widget.error = True
                    valid = False
                    continue
                if mtype == "int":
                    try:
                        value = int(text)
                    except Exception:
                        widget.error = True
                        valid = False
                        continue
                elif mtype == "float":
                    try:
                        value = float(text)
                    except Exception:
                        widget.error = True
                        valid = False
                        continue
                elif mtype == "bool":
                    low = text.lower()
                    if low in ("true", "1", "yes"):
                        value = True
                    elif low in ("false", "0", "no"):
                        value = False
                    else:
                        widget.error = True
                        valid = False
                        continue
                else:
                    value = text
            elif isinstance(widget, MDSlider):
                value = float(widget.value)
            elif isinstance(widget, Spinner):
                value = widget.text
                if required and value == "":
                    valid = False
                    continue
            data[name] = value
        return valid, data

    def _on_save(self):
        valid, data = self._collect()
        if not valid:
            return
        if self.on_save:
            self.on_save(data)
        self.close()
