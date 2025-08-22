"""Dialog utilities reimplemented as full screens.

This module previously provided :class:`FullScreenDialog` as an
``MDDialog`` subclass. Popups proved unreliable on target devices, so the
project now replaces them with regular screens that behave like popups.
``FullScreenDialog`` exposes ``open`` and ``dismiss`` methods so existing
call sites continue to work, but internally it simply navigates to a new
screen in the application's ``ScreenManager``.

The simplified implementation intentionally avoids complex layout logic in
order to minimise memory usage and reduce the chance of modal issues. The
dialog content and buttons are stacked vertically and fill the window.

The back-button behaviour is handled by :class:`WorkoutApp` which keeps a
stack of open dialog screens. Pressing the Android back button pops the
stack, giving the appearance of dismissing a popup while using standard
screen navigation under the hood.
"""

from __future__ import annotations

try:  # pragma: no cover - Kivy is not available during unit tests
    from kivymd.app import MDApp
    from kivymd.uix.boxlayout import MDBoxLayout
    from kivymd.uix.label import MDLabel
    from kivymd.uix.screen import MDScreen
    from kivy.metrics import dp
except Exception:  # pragma: no cover - fallback when Kivy isn't available
    class FullScreenDialog:  # minimalist stub used for headless tests
        def __init__(self, *args, **kwargs):
            pass

        def open(self, *args, **kwargs):
            pass

        def dismiss(self, *args, **kwargs):
            pass

else:

    class FullScreenDialog(MDScreen):
        """Screen that mimics popup behaviour.

        Parameters
        ----------
        title:
            Optional title displayed at the top of the screen.
        text:
            Optional body text displayed above ``content_cls``. This mirrors
            the older ``MDDialog`` API so existing call sites can pass a
            message without constructing a custom widget.
        content_cls:
            Main widget displayed in the body of the screen.
        buttons:
            Iterable of widgets placed in a footer row.
        """

        def __init__(
            self,
            *,
            title: str = "",
            text: str = "",
            content_cls=None,
            buttons: list | tuple | None = None,
            **kwargs,
        ):
            # ``MDDialog`` accepted a ``type`` kwarg which is irrelevant for the
            # simplified ``FullScreenDialog``.  Pop it from ``kwargs`` so Kivy
            # doesn't raise ``TypeError`` for an unknown property.
            kwargs.pop("type", None)
            super().__init__(**kwargs)

            self.ids = {}
            layout = MDBoxLayout(orientation="vertical")

            if title:
                # Basic title label; minimal styling to save resources.
                layout.add_widget(
                    MDLabel(
                        text=title,
                        size_hint_y=None,
                        height=dp(48),
                        halign="center",
                        valign="center",
                    )
                )

            if text:
                # ``MDDialog`` allowed a message via ``text``. Re-create that
                # behaviour with a lightweight label to minimise widget count.
                layout.add_widget(
                    MDLabel(
                        text=text,
                        size_hint_y=None,
                        height=dp(48),
                        halign="center",
                        valign="center",
                    )
                )

            if content_cls is not None:
                layout.add_widget(content_cls)

            if buttons:
                button_box = MDBoxLayout(
                    size_hint_y=None,
                    height=dp(48),
                    spacing=dp(8),
                )
                for btn in buttons:
                    button_box.add_widget(btn)
                layout.add_widget(button_box)
                self.ids["button_box"] = button_box

            self.add_widget(layout)
            self._previous_screen = ""

        # ------------------------------------------------------------------
        # Navigation helpers
        # ------------------------------------------------------------------
        def open(self, *_) -> None:
            """Display the dialog by pushing a new screen.

            The current screen name is saved so ``dismiss`` can return the
            user to their previous location.
            """

            app = MDApp.get_running_app()
            self._previous_screen = app.root.current
            if not self.name:
                # Generate a unique name to avoid collisions in the manager.
                self.name = f"_dialog_{id(self)}"
            app.root.add_widget(self)
            app.root.current = self.name
            # ``WorkoutApp`` maintains this stack to handle the back button.
            app._dialog_stack.append(self)

        def dismiss(self, *_) -> None:
            """Close the dialog by returning to the previous screen."""

            app = MDApp.get_running_app()
            if self._previous_screen:
                app.root.current = self._previous_screen
            app.root.remove_widget(self)
            if app._dialog_stack:
                app._dialog_stack.pop()

