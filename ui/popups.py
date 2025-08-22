# Popup dialog classes moved from main.py
from __future__ import annotations

from kivymd.app import MDApp
from kivy.metrics import dp
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView

from ui.dialogs import FullScreenDialog
from ui.dialogs.add_metric_popup import METRIC_FIELD_ORDER
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivymd.uix.selectioncontrol import MDCheckbox
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.list import MDList
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider

import string
import re
import sqlite3

from core import DEFAULT_DB_PATH
from backend import metrics


class PreSessionMetricPopup(FullScreenDialog):
    """Popup for entering pre-session metrics."""

    def __init__(self, metrics: list[dict], on_save, **kwargs):
        self.metrics = metrics
        self.on_save = on_save
        # Track the active ScrollView so ``FullScreenDialog`` can size it on open.
        self._scroll_view = None
        # ``FullScreenDialog`` handles full-screen sizing.
        content, buttons = self._build_widgets()
        super().__init__(
            title="Session Metrics",
            type="custom",
            content_cls=content,
            buttons=buttons,
            **kwargs,
        )

    def _build_widgets(self):
        # Build a list of metric input rows. Binding ``minimum_height`` ensures
        # the list grows with its children so that it is fully scrollable.
        self.metric_list = MDList(adaptive_height=True)
        # Disable vertical size hint so the ``minimum_height`` binding updates
        # the list's height for scrolling.
        self.metric_list.bind(minimum_height=self.metric_list.setter("height"))
        for m in self.metrics:
            self.metric_list.add_widget(self._create_row(m))
        scroll = ScrollView(do_scroll_y=True, size_hint=(1, 1))
        scroll.add_widget(self.metric_list)
        # ``FullScreenDialog`` uses this reference to adjust height on open.
        self._scroll_view = scroll
        save_btn = MDRaisedButton(text="Save", on_release=lambda *_: self._on_save())
        cancel_btn = MDRaisedButton(text="Cancel", on_release=lambda *_: self.dismiss())
        return scroll, [save_btn, cancel_btn]

    def _create_row(self, metric):
        name = metric.get("name")
        mtype = metric.get("type", "str")
        values = metric.get("values", [])
        row = MDBoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48))
        row.metric_name = name
        row.type = mtype
        row.required = metric.get("is_required", False)
        row.add_widget(MDLabel(text=name, size_hint_x=0.4))
        if mtype == "slider":
            widget = MDSlider(min=0, max=1, value=0)
        elif mtype == "enum":
            widget = Spinner(text=values[0] if values else "", values=values)
        else:
            input_filter = None
            if mtype == "int":
                input_filter = "int"
            elif mtype == "float":
                input_filter = "float"
            widget = MDTextField(multiline=False, input_filter=input_filter)
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
        self.dismiss()
