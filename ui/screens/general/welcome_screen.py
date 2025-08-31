"""Implementation of the app's welcome screen.

The welcome screen is intentionally lightweight. It shows the application
version, allows editing of a short welcome message and provides an "Enter"
button to proceed to the main application.  The layout is defined in the
``main.kv`` file.
"""

try:  # pragma: no cover - fallback for environments without Kivy
    from kivymd.uix.screen import MDScreen
    from kivy.properties import StringProperty
except Exception:  # pragma: no cover - simple stubs
    MDScreen = object

    class StringProperty:  # type: ignore
        """Fallback stand-in used when Kivy is unavailable."""

        def __init__(self, default: str = ""):
            self.default = default


class WelcomeScreen(MDScreen):
    """Initial screen displayed when the app starts."""

    #: Editable message shown in the welcome screen's text box.
    message = StringProperty("Welcome - start your fitness journey")

