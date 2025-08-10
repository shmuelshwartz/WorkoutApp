from kivy.uix.screenmanager import ScreenManager


class FlowRouter:
    """Router for flow tests that uses a ScreenManager."""

    def __init__(self, manager: ScreenManager) -> None:
        self.manager = manager

    def navigate(self, target: str) -> None:
        if target in self.manager.screen_names:
            self.manager.current = target
        else:
            print(f"unknown navigation target: {target}")
