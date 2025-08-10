import argparse
import importlib
from kivymd.app import MDApp
from kivy.uix.screenmanager import ScreenManager
from ui.routers import FlowRouter


def run(start: str, scenario: str | None = None) -> None:
    """Run a flow test starting at the given screen module."""
    module = importlib.import_module(f"ui.screens.{start}")
    screen_cls = None
    for attr in dir(module):
        obj = getattr(module, attr)
        try:
            from kivy.uix.screenmanager import Screen

            if isinstance(obj, type) and issubclass(obj, Screen):
                screen_cls = obj
                break
        except Exception:  # pragma: no cover - defensive
            continue
    if screen_cls is None:
        raise SystemExit(f"No Screen subclass found in ui.screens.{start}")

    class _FlowApp(MDApp):
        def build(self):
            manager = ScreenManager()
            router = FlowRouter(manager)
            screen = screen_cls(router=router, test_mode=True)
            screen.name = start
            manager.add_widget(screen)
            return manager

    _FlowApp().run()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", required=True, help="screen module to start")
    parser.add_argument("--scenario", help="unused stub scenario", default=None)
    args = parser.parse_args()
    run(args.start, args.scenario)


if __name__ == "__main__":  # pragma: no cover
    main()
