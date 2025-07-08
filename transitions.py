from kivy.uix.screenmanager import SlideTransition
from kivy.animation import Animation

class OverlaySlideTransition(SlideTransition):
    """Slide transition that overlays the new screen without moving the
    previous screen."""

    def start(self, manager):
        # Keep references to screens involved in the transition
        self.manager = manager
        self.screen_in = manager.next_screen
        self.screen_out = manager.current_screen
        width, height = manager.size

        if self.direction == "up":
            # New screen slides from the bottom over the current screen
            self.screen_in.pos = (0, -height)
            anim = Animation(y=0, duration=self.duration, t=self.t)
            anim.bind(on_complete=lambda *a: self.dispatch("on_complete"))
            anim.start(self.screen_in)
        elif self.direction == "down":
            # Current screen slides down revealing the screen below
            anim = Animation(y=-height, duration=self.duration, t=self.t)
            anim.bind(on_complete=lambda *a: self.dispatch("on_complete"))
            anim.start(self.screen_out)
        else:
            super().start(manager)
