"""Kivy based application providing a very small workout UI demo."""

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.lang import Builder
import platform
from kivy.core.window import Window
from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.properties import StringProperty
from functionality import Manager

manager = Manager()


if not ((platform.system() == "Android") or (platform.system() == "Linux")):
    Window.size = (280, 280 * (20 / 9))

# Load the KV file
# Builder.load_file("workout.kv")


# ─── BASE CLASS WITH SHARED BUTTON HANDLERS ─────────────────
class BaseWorkoutScreen(Screen):
    """Screen with common button handlers shared by other screens."""

    current_screen_name = StringProperty()

    def on_enter(self):
        """Update the current screen name when entering the screen."""
        self.current_screen_name = self.manager.current

    def back_button_action(self):
        """Handle the back navigation button."""
        print("Back button pressed")

    def undo_button_action(self):
        """Undo the last action and adjust the workout start time."""
        print("Undo button pressed")
        manager.set_next_workout_start_time()

    def redo_button_action(self):
        """Redo the last undone action."""
        print("Redo button pressed")

    def settings_button_action(self):
        """Open the settings screen (placeholder)."""
        print("Settings button pressed")

    def minus_button_action(self):
        """Decrease the workout timer (placeholder)."""
        print("Minus timer pressed")

    def plus_button_action(self):
        """Increase the workout timer (placeholder)."""
        print("Plus timer pressed")

    def timer_button_action(self):
        """Start or stop the timer depending on state."""
        print("Timer button pressed")

    def edit_workout_button_action(self):
        """Switch to the screen used for editing workouts."""
        self.manager.current = "edit"

    def main_menu_button_action(self):
        """Return to the main menu screen."""
        self.manager.current = "main"

    def workout_data_button_action(self):
        """Open the workout data screen."""
        self.manager.current = "data"


# ─── SCREENS ────────────────────────────────────────────────
class WorkoutMainScreen(BaseWorkoutScreen):
    """Main workout selection screen."""

    pass


class EditWorkoutScreen(BaseWorkoutScreen):
  pass


class WorkOutDataScreen(BaseWorkoutScreen):
    """Displays historical workout statistics."""

    pass


class ExerciseExecutionScreen(Screen):
    """Runs when a single exercise is being performed."""

    pass


class EndWorkoutScreen(Screen):
    """Shown after the workout session is completed."""

    pass


# ─── APP & SCREEN MANAGER ───────────────────────────────────
class WorkoutApp(App):
    """Root application managing all workout related screens."""

    def build(self):
        """Construct the :class:`ScreenManager` and attach screens."""
        sm = ScreenManager(transition=NoTransition())  # transitions are instant
        sm.add_widget(WorkoutMainScreen(name="main"))
        sm.add_widget(EditWorkoutScreen(name="edit"))
        sm.add_widget(WorkOutDataScreen(name="data"))
        sm.add_widget(ExerciseExecutionScreen(name="exercise"))
        sm.add_widget(EndWorkoutScreen(name="end"))
        return sm


if __name__ == "__main__":
    WorkoutApp().run()