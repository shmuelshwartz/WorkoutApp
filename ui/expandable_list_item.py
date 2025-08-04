from kivy.metrics import dp
from kivy.clock import Clock
from kivymd.uix.list import OneLineListItem


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
