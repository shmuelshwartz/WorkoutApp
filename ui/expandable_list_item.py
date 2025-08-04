from kivy.metrics import dp
from kivy.clock import Clock
from kivy.uix.behaviors import ButtonBehavior
from kivymd.uix.list import OneLineListItem
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel


class ExpandableListItem(OneLineListItem):
    """List item that expands to show all text when tapped."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._expanded = False
        Clock.schedule_once(self._post_init)

    def _post_init(self, *_):
        self.bind(on_release=self._toggle)
        label = self.ids._lbl_primary
        label.shorten = True
        label.max_lines = 3
        label.text_size = (self.width, None)
        self._line_height = label.line_height
        self._collapsed_height = self._line_height * 3 + dp(20)
        label.texture_update()
        self.height = min(label.texture_size[1] + dp(20), self._collapsed_height)
        self.bind(width=self._update_width)

    def _update_width(self, *_):
        label = self.ids._lbl_primary
        label.text_size = (self.width, None)
        label.texture_update()
        if self._expanded:
            self.height = label.texture_size[1] + dp(20)
        else:
            self.height = min(label.texture_size[1] + dp(20), self._collapsed_height)

    def _toggle(self, *_):
        label = self.ids._lbl_primary
        if self._expanded:
            self._expanded = False
            label.max_lines = 3
            label.shorten = True
            label.texture_update()
            self.height = min(label.texture_size[1] + dp(20), self._collapsed_height)
        else:
            self._expanded = True
            label.max_lines = 0
            label.shorten = False
            label.texture_update()
            self.height = label.texture_size[1] + dp(20)


class ExerciseSummaryItem(ButtonBehavior, MDBoxLayout):
    """Collapsible list item used on the preset detail screen.

    Displays the exercise name and number of sets. When collapsed the
    exercise name is shortened with an ellipsis to ensure the set count is
    always visible. Tapping the item expands it to show the full exercise
    name and moves the set count onto a new line."""

    def __init__(self, name: str, sets: int, **kwargs):
        super().__init__(orientation="vertical", padding=(dp(16), dp(8)), spacing=dp(4), size_hint_y=None, **kwargs)
        self._expanded = False
        self._name_text = name
        label = "set" if sets == 1 else "sets"
        self._sets_text = f"{sets} {label}"

        # top row for collapsed state
        self._top_row = MDBoxLayout(orientation="horizontal")
        self.name_label = MDLabel(text=name, shorten=True, max_lines=1)
        self.sets_label = MDLabel(text=f"- {self._sets_text}", size_hint_x=None)
        self._top_row.add_widget(self.name_label)
        self._top_row.add_widget(self.sets_label)
        self.add_widget(self._top_row)

        Clock.schedule_once(self._post_init)

    def _post_init(self, *_):
        self.sets_label.texture_update()
        self.sets_label.width = self.sets_label.texture_size[0]
        self.bind(width=self._update_width)
        self._update_width()

    def _update_width(self, *_):
        # Ensure the exercise name accounts for the width of the set label
        # When expanded the set count is on a new line so the name can take
        # the full width. When collapsed the name should only use the width
        # that remains after the set count label.
        if self._expanded:
            avail = self.width
        else:
            avail = self.width - self.sets_label.width
            if avail < 0:
                avail = self.width
        self.name_label.text_size = (avail, None)
        self.name_label.texture_update()
        self.sets_label.texture_update()
        if self._expanded:
            height = self.name_label.texture_size[1] + self.sets_label.texture_size[1] + dp(16) + self.spacing
        else:
            height = max(self.name_label.texture_size[1], self.sets_label.texture_size[1]) + dp(16)
        self.height = height

    def on_touch_up(self, touch):
        if self.collide_point(*touch.pos):
            self._toggle()
            return True
        return super().on_touch_up(touch)

    def _toggle(self):
        if self._expanded:
            # Collapse
            self._expanded = False
            self.clear_widgets()
            # Remove labels from any previous parent before re-adding them
            if self.name_label.parent:
                self.name_label.parent.remove_widget(self.name_label)
            if self.sets_label.parent:
                self.sets_label.parent.remove_widget(self.sets_label)
            self.name_label.shorten = True
            self.name_label.max_lines = 1
            self.sets_label.text = f"- {self._sets_text}"
            self._top_row = MDBoxLayout(orientation="horizontal")
            self._top_row.add_widget(self.name_label)
            self._top_row.add_widget(self.sets_label)
            self.add_widget(self._top_row)
        else:
            # Expand
            self._expanded = True
            self.clear_widgets()
            if self.name_label.parent:
                self.name_label.parent.remove_widget(self.name_label)
            if self.sets_label.parent:
                self.sets_label.parent.remove_widget(self.sets_label)
            self.name_label.shorten = False
            self.name_label.max_lines = 0
            self.name_label.text_size = (self.width, None)
            self.sets_label.text = self._sets_text
            self.add_widget(self.name_label)
            self.add_widget(self.sets_label)
        self._update_width()

    @property
    def text(self) -> str:  # pragma: no cover - simple property for tests
        """Return a collapsed representation of the item."""
        return f"{self._name_text} - {self._sets_text}"

