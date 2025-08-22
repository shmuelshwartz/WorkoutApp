try:
    from kivymd.uix.dialog import MDDialog
    from kivymd.app import MDApp
    from kivy.core.window import Window
    from kivy.clock import Clock
except Exception:  # pragma: no cover - fallback when Kivy isn't available
    class MDDialog:  # minimal stub
        def __init__(self, *a, **k):
            pass
        def open(self, *a, **k):
            pass
        def dismiss(self, *a, **k):
            pass
    class FullScreenDialog(MDDialog):
        """Stub used when Kivy isn't installed."""
        pass
else:
    class FullScreenDialog(MDDialog):
        """MDDialog that expands to cover the entire window."""
        def __init__(self, **kwargs):
            self._scroll_view = getattr(self, "_scroll_view", None)
            kwargs.setdefault("size_hint", (1, None))
            kwargs.setdefault("radius", [0, 0, 0, 0])
            app = MDApp.get_running_app()
            bg = getattr(getattr(app, "theme_cls", None), "bg_light", (1, 1, 1, 1))
            kwargs.setdefault("md_bg_color", bg)
            super().__init__(**kwargs)
            self.bind(on_open=self._resize_to_window)
        def _resize_to_window(self, *_):
            self.width = Window.width
            self.height = Window.height
            if self._scroll_view is None:
                return
            def _adjust(*_):
                btn_h = self.ids.button_box.height if "button_box" in self.ids else 0
                self._scroll_view.height = max(0, Window.height - btn_h)
            Clock.schedule_once(_adjust, 0)
