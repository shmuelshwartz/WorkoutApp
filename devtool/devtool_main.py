from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel


class DevToolApp(MDApp):
    """Lightweight app for database maintenance tasks."""

    def build(self):
        self.title = "Workout DevTool"
        self.theme_cls.primary_palette = "Blue"
        self.theme_cls.theme_style = "Light"
        screen = MDScreen()
        label = MDLabel(
            text="DevTool Dashboard",
            halign="center",
            valign="center",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            font_style="H4",
        )
        screen.add_widget(label)
        return screen


if __name__ == "__main__":
    DevToolApp().run()
