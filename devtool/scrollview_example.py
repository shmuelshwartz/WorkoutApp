"""Reference component demonstrating proper ScrollView usage.
# TINY-SCREEN: scrollview snippet
"""
from kivy.uix.scrollview import ScrollView
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp


class LongContentExample(ScrollView):
    def __init__(self, **kwargs):
        super().__init__(do_scroll_x=False, **kwargs)
        box = BoxLayout(orientation="vertical", size_hint_y=None, padding=dp(10), spacing=dp(10))
        box.bind(minimum_height=box.setter("height"))
        self.add_widget(box)
        for i in range(20):
            box.add_widget(BoxLayout(size_hint_y=None, height=dp(40)))
