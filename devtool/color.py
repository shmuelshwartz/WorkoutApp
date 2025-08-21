# App to visualize and test color palettes for the Workout app

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton, MDIconButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivymd.uix.segmentedcontrol import (
    MDSegmentedControl,
    MDSegmentedControlItem,
)
from kivymd.uix.picker import MDColorPicker
from kivymd.uix.selectioncontrol import MDCheckbox, MDSwitch
from kivymd.uix.card import MDCard
from kivymd.uix.spinner import MDSpinner
from kivy.properties import StringProperty
from kivy.clock import Clock
from kivy.utils import get_color_from_hex, get_hex_from_color
import json
import os
import copy
from ui.colors import PINK_BG


def _rel_lum(c: float) -> float:
    c = c / 1.0
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _contrast_ratio(a, b) -> float:
    l1 = 0.2126 * _rel_lum(a[0]) + 0.7152 * _rel_lum(a[1]) + 0.0722 * _rel_lum(a[2])
    l2 = 0.2126 * _rel_lum(b[0]) + 0.7152 * _rel_lum(b[1]) + 0.0722 * _rel_lum(b[2])
    if l1 < l2:
        l1, l2 = l2, l1
    return (l1 + 0.05) / (l2 + 0.05)


class EditColorsScreen(MDScreen):
    md_bg_color = PINK_BG
    """Screen for editing colors."""

    active_target = StringProperty("text")

    def on_pre_enter(self, *args):
        self.update_fields_from_colors()
        self._update_contrast()

    def update_fields_from_colors(self):
        app = MDApp.get_running_app()
        rgb = app.colors[self.active_target]
        for i, box in enumerate(self.rgb_inputs):
            box.text = str(int(rgb[i] * 255))
        self.hex_input.text = get_hex_from_color(rgb)

    def build(self):
        layout = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp")

        seg = MDSegmentedControl()
        for name in (
            "Text",
            "Hint Text",
            "Screen BG",
            "Button BG",
            "Button Text",
            "Icon",
            "Slider",
        ):
            item = MDSegmentedControlItem(text=name)
            seg.add_widget(item)
            if name == "Text":
                item.active = True  # set default selected tab here
        seg.bind(on_active=self.on_segment_switch)
        layout.add_widget(seg)

        self.rgb_inputs = [
            MDTextField(hint_text="Red", input_filter="int"),
            MDTextField(hint_text="Green", input_filter="int"),
            MDTextField(hint_text="Blue", input_filter="int"),
        ]
        for field in self.rgb_inputs:
            field.bind(text=self.on_rgb_change)
            layout.add_widget(field)

        self.hex_input = MDTextField(hint_text="Hex #RRGGBB")
        self.hex_input.bind(text=self.on_hex_change)
        layout.add_widget(self.hex_input)

        pick_btn = MDRaisedButton(text="Pick Color")
        pick_btn.bind(on_release=self.open_picker)
        layout.add_widget(pick_btn)

        save_btn = MDRaisedButton(text="Save Color", pos_hint={"center_x": 0.5})
        save_btn.bind(on_release=self.save_color)
        layout.add_widget(save_btn)

        self.preset_name = MDTextField(hint_text="Preset Name")
        layout.add_widget(self.preset_name)
        preset_buttons = MDBoxLayout(size_hint_y=None, height="48dp", spacing="12dp")
        btn_save_preset = MDFlatButton(text="Save Preset")
        btn_load_preset = MDFlatButton(text="Load Preset")
        btn_delete_preset = MDFlatButton(text="Delete Preset")
        btn_save_preset.bind(on_release=self.save_preset)
        btn_load_preset.bind(on_release=self.load_preset)
        btn_delete_preset.bind(on_release=self.delete_preset)
        preset_buttons.add_widget(btn_save_preset)
        preset_buttons.add_widget(btn_load_preset)
        preset_buttons.add_widget(btn_delete_preset)
        layout.add_widget(preset_buttons)

        action_buttons = MDBoxLayout(size_hint_y=None, height="48dp", spacing="12dp")
        undo_btn = MDFlatButton(text="Undo")
        redo_btn = MDFlatButton(text="Redo")
        theme_btn = MDFlatButton(text="Toggle Theme")
        undo_btn.bind(on_release=lambda *_: MDApp.get_running_app().undo())
        redo_btn.bind(on_release=lambda *_: MDApp.get_running_app().redo())
        theme_btn.bind(on_release=lambda *_: MDApp.get_running_app().toggle_theme())
        action_buttons.add_widget(undo_btn)
        action_buttons.add_widget(redo_btn)
        action_buttons.add_widget(theme_btn)
        layout.add_widget(action_buttons)

        self.contrast_label = MDLabel(text="", halign="center")
        layout.add_widget(self.contrast_label)

        nav = MDBoxLayout(size_hint_y=None, height="48dp", spacing="12dp")
        prev1 = MDFlatButton(text="Preview 1")
        prev2 = MDFlatButton(text="Preview 2")
        snap = MDFlatButton(text="Snapshot")
        prev1.bind(on_release=self.go_to_preview1)
        prev2.bind(on_release=self.go_to_preview2)
        snap.bind(on_release=self.go_to_snapshot)
        nav.add_widget(prev1)
        nav.add_widget(prev2)
        nav.add_widget(snap)
        layout.add_widget(nav)

        self.add_widget(layout)

    def go_to_preview1(self, *args):
        self.manager.current = "preview1"

    def go_to_preview2(self, *args):
        self.manager.current = "preview2"

    def go_to_snapshot(self, *args):
        self.manager.current = "snapshot"
    def on_segment_switch(self, control, segment):
        self.active_target = segment.text.lower().replace(" ", "_")
        self.update_fields_from_colors()

    def save_color(self, *_):
        app = MDApp.get_running_app()
        try:
            r = max(0, min(255, int(self.rgb_inputs[0].text))) / 255
            g = max(0, min(255, int(self.rgb_inputs[1].text))) / 255
            b = max(0, min(255, int(self.rgb_inputs[2].text))) / 255
        except ValueError:
            return
        app.push_undo()
        app.colors[self.active_target] = [r, g, b, 1]
        app.apply_colors()
        self._update_contrast()

    def on_rgb_change(self, *_):
        Clock.schedule_once(lambda *_: self.save_color(), 0)

    def on_hex_change(self, instance, value):
        if not value.startswith("#") or len(value) not in (7, 9):
            return
        try:
            rgb = get_color_from_hex(value)
        except Exception:
            return
        for i in range(3):
            self.rgb_inputs[i].text = str(int(rgb[i] * 255))
        Clock.schedule_once(lambda *_: self.save_color(), 0)

    def open_picker(self, *_):
        app = MDApp.get_running_app()
        color = app.colors[self.active_target]

        def on_select(instance, color: list) -> None:
            for i in range(3):
                self.rgb_inputs[i].text = str(int(color[i] * 255))
            self.save_color()

        picker = MDColorPicker()
        picker.set_color(color)
        picker.bind(on_select_color=on_select)
        picker.open()

    def _update_contrast(self):
        app = MDApp.get_running_app()
        t = app.colors["text"]
        bg = app.colors["screen_bg"]
        ratio = _contrast_ratio(t, bg)
        self.contrast_label.text = f"Contrast ratio: {ratio:.2f}" + (
            " (good)" if ratio >= 4.5 else " (low)"
        )

    def save_preset(self, *_):
        name = self.preset_name.text.strip()
        if not name:
            return
        MDApp.get_running_app().save_preset(name)

    def load_preset(self, *_):
        name = self.preset_name.text.strip()
        if not name:
            return
        MDApp.get_running_app().load_preset(name)
        self.update_fields_from_colors()

    def delete_preset(self, *_):
        name = self.preset_name.text.strip()
        if not name:
            return
        app = MDApp.get_running_app()
        if name in app.presets:
            del app.presets[name]
            app.save_presets()


class PreviewScreen(MDScreen):
    md_bg_color = PINK_BG
    """Base class for preview screens."""

    label_text = StringProperty("")

    def build(self):
        layout = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp")
        self.label = MDLabel(text=self.label_text, halign="center", theme_text_color="Custom")
        self.text_field = MDTextField(hint_text="Enter text")
        self.button = MDRaisedButton(text="Button", pos_hint={"center_x": 0.5}, theme_text_color="Custom")
        self.icon = MDIconButton(icon="star", theme_text_color="Custom")
        self.slider = MDSlider()
        self.switch = MDSwitch()
        self.checkbox = MDCheckbox()
        self.spinner = MDSpinner(size_hint=(None, None), size=(48, 48))
        self.card = MDCard(size_hint=(1, None), height="80dp")
        self.card.add_widget(MDLabel(text="Card", halign="center"))
        layout.add_widget(self.label)
        layout.add_widget(self.text_field)
        layout.add_widget(self.button)
        layout.add_widget(self.icon)
        layout.add_widget(self.slider)
        layout.add_widget(self.switch)
        layout.add_widget(self.checkbox)
        layout.add_widget(self.spinner)
        layout.add_widget(self.card)

        nav = MDBoxLayout(size_hint_y=None, height="48dp", spacing="12dp")
        self.btn_edit = MDFlatButton(text="Edit Colors", theme_text_color="Custom")
        self.btn_other = MDFlatButton(text="Other Preview", theme_text_color="Custom")
        nav.add_widget(self.btn_edit)
        nav.add_widget(self.btn_other)
        layout.add_widget(nav)

        self.add_widget(layout)


class SnapshotScreen(MDScreen):
    md_bg_color = PINK_BG
    """Full screen preview of all components."""

    def build(self):
        layout = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp")
        self.preview = PreviewScreen()
        self.preview.build()
        self.preview.btn_other.text = "Back"
        self.preview.btn_other.bind(on_release=lambda *_: setattr(self.manager, "current", "edit"))
        layout.add_widget(self.preview)
        self.add_widget(layout)


class ColorApp(MDApp):
    """App for previewing color palettes."""

    colors = {
        "text": [1, 1, 1, 1],
        "hint_text": [0.7, 0.7, 0.7, 1],
        "screen_bg": [0, 0, 0, 1],
        "button_bg": [0.2, 0.6, 0.86, 1],
        "button_text": [1, 1, 1, 1],
        "icon": [1, 0.84, 0, 1],
        "slider": [0.2, 0.6, 0.86, 1],
    }

    def build(self):
        self.theme_cls.theme_style = "Light"
        manager = ScreenManager()

        self.edit_screen = EditColorsScreen(name="edit")
        self.edit_screen.build()
        manager.add_widget(self.edit_screen)

        self.preview1 = PreviewScreen(name="preview1", label_text="Preview 1")
        self.preview1.build()
        self.preview1.btn_edit.bind(on_release=lambda *_: self.switch_screen("edit"))
        self.preview1.btn_other.bind(on_release=lambda *_: self.switch_screen("preview2"))
        manager.add_widget(self.preview1)

        self.preview2 = PreviewScreen(name="preview2", label_text="Preview 2")
        self.preview2.build()
        self.preview2.btn_edit.bind(on_release=lambda *_: self.switch_screen("edit"))
        self.preview2.btn_other.bind(on_release=lambda *_: self.switch_screen("preview1"))
        manager.add_widget(self.preview2)

        self.snapshot = SnapshotScreen(name="snapshot")
        self.snapshot.build()
        manager.add_widget(self.snapshot)

        self.presets_file = os.path.join(os.path.dirname(__file__), "color_presets.json")
        self.history = []
        self.future = []
        self.presets = {}
        self.load_presets()

        self.manager = manager
        self.apply_colors()
        return manager

    def switch_screen(self, name):
        self.manager.current = name

    def push_undo(self):
        self.history.append(copy.deepcopy(self.colors))
        if len(self.history) > 20:
            self.history.pop(0)
        self.future.clear()

    def undo(self):
        if not self.history:
            return
        self.future.append(copy.deepcopy(self.colors))
        self.colors = self.history.pop()
        self.apply_colors()

    def redo(self):
        if not self.future:
            return
        self.history.append(copy.deepcopy(self.colors))
        self.colors = self.future.pop()
        self.apply_colors()

    def toggle_theme(self, *_):
        self.theme_cls.theme_style = "Dark" if self.theme_cls.theme_style == "Light" else "Light"

    def apply_colors(self):
        t = self.colors["text"]
        hint = self.colors["hint_text"]
        bg = self.colors["screen_bg"]
        btn_bg = self.colors["button_bg"]
        btn_text = self.colors["button_text"]
        icon = self.colors["icon"]
        slider = self.colors["slider"]

        for screen in (self.preview1, self.preview2, self.snapshot.preview):
            screen.label.theme_text_color = "Custom"
            screen.label.text_color = t
            screen.text_field.text_color = t
            screen.text_field.hint_text_color = hint
            screen.button.md_bg_color = btn_bg
            screen.button.text_color = btn_text
            screen.slider.color = slider
            screen.icon.text_color = icon
            screen.switch.thumb_color_down = slider
            screen.switch.thumb_color_normal = slider
            screen.checkbox.active = True
            screen.spinner.color = icon
            screen.btn_edit.text_color = t
            screen.btn_other.text_color = t
            screen.md_bg_color = bg

        self.edit_screen.md_bg_color = bg

    def save_presets(self):
        with open(self.presets_file, "w", encoding="utf-8") as fh:
            json.dump(self.presets, fh, indent=2)

    def load_presets(self):
        if os.path.exists(self.presets_file):
            with open(self.presets_file, "r", encoding="utf-8") as fh:
                self.presets = json.load(fh)

    def save_preset(self, name: str):
        self.presets[name] = copy.deepcopy(self.colors)
        self.save_presets()

    def load_preset(self, name: str):
        if name in self.presets:
            self.push_undo()
            self.colors = copy.deepcopy(self.presets[name])
            self.apply_colors()


if __name__ == "__main__":
    ColorApp().run()
