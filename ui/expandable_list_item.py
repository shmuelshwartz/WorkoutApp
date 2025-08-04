from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.list import OneLineListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


class ExpandableListItem(OneLineListItem):
    """List item that automatically grows to fit its text."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Disable ripple/press behaviour so the item is static when tapped
        self.ripple_behavior = False
        Clock.schedule_once(self._post_init)

    def _post_init(self, *_):
        label = self.ids._lbl_primary
        label.shorten = False
        label.max_lines = 0
        label.text_size = (self.width, None)
        label.texture_update()
        self.height = label.texture_size[1] + dp(20)
        self.bind(width=self._update_width)

    def _update_width(self, *_):
        label = self.ids._lbl_primary
        label.text_size = (self.width, None)
        label.texture_update()
        self.height = label.texture_size[1] + dp(20)


class ExerciseSummaryItem(MDBoxLayout):
    """Static list item showing an exercise name and set count."""

    def __init__(self, name: str, sets: int, **kwargs):
        super().__init__(orientation="vertical", padding=(dp(16), dp(8)), size_hint_y=None, **kwargs)
        self._name_text = name
        label = "set" if sets == 1 else "sets"
        self._sets_text = f"{sets} {label}"
        self.label = MDLabel(text=self.text, shorten=False, max_lines=0)
        self.add_widget(self.label)
        # Update size after the widget has a width
        Clock.schedule_once(self._post_init)

    def _post_init(self, *_):
        self.bind(width=self._update_width)
        self._update_width()

    def _update_width(self, *_):
        avail = self.width - self.padding[0] * 2
        self.label.text = self.text
        self.label.text_size = (avail, None)
        self.label.texture_update()
        self.height = self.label.texture_size[1] + self.padding[1] * 2

    @property
    def text(self) -> str:  # pragma: no cover - simple property for tests
        """Return a collapsed representation of the item."""
        return f"{self._name_text} - {self._sets_text}"

