# App to visualize and test color palettes for the Workout app

from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.label import MDLabel
from kivymd.uix.textfield import MDTextField
from kivymd.uix.slider import MDSlider
from kivymd.uix.segmentedcontrol import MDSegmentedControl, MDSegmentedControlItem
from kivy.properties import StringProperty


class EditColorsScreen(MDScreen):
    """Screen for editing colors."""

    active_target = StringProperty("text")

    def on_pre_enter(self, *args):
        self.update_fields_from_colors()

    def update_fields_from_colors(self):
        app = MDApp.get_running_app()
        rgb = app.colors[self.active_target]
        for i, box in enumerate(self.rgb_inputs):
            box.text = str(int(rgb[i] * 255))

    def build(self):
        layout = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp")

        seg = MDSegmentedControl()
        for name in ("Text", "Screen BG", "Button"):
            item = MDSegmentedControlItem(text=name)
            seg.add_widget(item)
            if name == "Text":
                item.active = True  # ✅ set default selected tab here
        seg.bind(on_active=self.on_segment_switch)
        layout.add_widget(seg)

        self.rgb_inputs = [
            MDTextField(hint_text="Red", input_filter="int"),
            MDTextField(hint_text="Green", input_filter="int"),
            MDTextField(hint_text="Blue", input_filter="int"),
        ]
        for field in self.rgb_inputs:
            layout.add_widget(field)

        save_btn = MDRaisedButton(text="Save Color", pos_hint={"center_x": 0.5})
        save_btn.bind(on_release=self.save_color)
        layout.add_widget(save_btn)

        nav = MDBoxLayout(size_hint_y=None, height="48dp", spacing="12dp")
        prev1 = MDFlatButton(text="Preview 1")
        prev2 = MDFlatButton(text="Preview 2")
        prev1.bind(on_release=self.go_to_preview1)
        prev2.bind(on_release=self.go_to_preview2)
        nav.add_widget(prev1)
        nav.add_widget(prev2)
        layout.add_widget(nav)

        self.add_widget(layout)

    def go_to_preview1(self, *args):
        self.manager.current = "preview1"

    def go_to_preview2(self, *args):
        self.manager.current = "preview2"
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
        app.colors[self.active_target] = [r, g, b, 1]
        app.apply_colors()


class PreviewScreen(MDScreen):
    """Base class for preview screens."""

    label_text = StringProperty("")

    def build(self):
        layout = MDBoxLayout(orientation="vertical", padding="12dp", spacing="12dp")
        self.label = MDLabel(text=self.label_text, halign="center", theme_text_color="Custom")
        self.text_field = MDTextField(hint_text="Enter text")
        self.button = MDRaisedButton(text="Button", pos_hint={"center_x": 0.5})
        self.slider = MDSlider()
        layout.add_widget(self.label)
        layout.add_widget(self.text_field)
        layout.add_widget(self.button)
        layout.add_widget(self.slider)

        nav = MDBoxLayout(size_hint_y=None, height="48dp", spacing="12dp")
        self.btn_edit = MDFlatButton(text="Edit Colors")
        self.btn_other = MDFlatButton(text="Other Preview")
        nav.add_widget(self.btn_edit)
        nav.add_widget(self.btn_other)
        layout.add_widget(nav)

        self.add_widget(layout)


class ColorApp(MDApp):
    """App for previewing color palettes."""

    colors = {
        "text": [1, 1, 1, 1],
        "screen_bg": [0, 0, 0, 1],
        "button": [0.2, 0.6, 0.86, 1],
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

        self.manager = manager
        self.apply_colors()
        return manager

    def switch_screen(self, name):
        self.manager.current = name

    def apply_colors(self):
        t = self.colors["text"]
        bg = self.colors["screen_bg"]
        btn = self.colors["button"]
        for screen in (self.preview1, self.preview2):
            screen.label.theme_text_color = "Custom"
            screen.label.text_color = t
            screen.text_field.text_color = t
            screen.text_field.hint_text_color = t
            screen.button.md_bg_color = btn
            screen.slider.color = btn
            screen.md_bg_color = bg
        self.edit_screen.md_bg_color = bg


if __name__ == "__main__":
    ColorApp().run()
