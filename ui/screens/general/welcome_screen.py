try:  # pragma: no cover - fallback for environments without Kivy
    from kivymd.uix.screen import MDScreen
except Exception:  # pragma: no cover - simple stubs
    MDScreen = object


class WelcomeScreen(MDScreen):
    """Initial screen displayed when the app starts."""

    pass
