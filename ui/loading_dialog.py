from kivymd.uix.dialog import MDDialog
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.label import MDLabel


class LoadingDialog(MDDialog):
    """Simple dialog displaying a spinner while work is performed."""

    def __init__(self, text: str = "Loading...", **kwargs):
        box = MDBoxLayout(
            orientation="vertical",
            spacing="8dp",
            size_hint_y=None,
            height="72dp",
        )
        spinner = MDSpinner(size_hint=(None, None), size=("48dp", "48dp"))
        spinner.pos_hint = {"center_x": 0.5}
        box.add_widget(spinner)
        box.add_widget(MDLabel(text=text, halign="center"))
        super().__init__(type="custom", content_cls=box, **kwargs)

