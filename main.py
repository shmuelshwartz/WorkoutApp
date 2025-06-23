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
    current_screen_name = StringProperty()

    def on_enter(self):
        self.current_screen_name = self.manager.current

    def back_button_action(self):
        print("Back button pressed")

    def undo_button_action(self):
        print("Undo button pressed")
        manager.set_next_workout_start_time()

    def redo_button_action(self):
        print("Redo button pressed")

    def settings_button_action(self):
        print("Settings button pressed")

    def minus_button_action(self):
        print("Minus timer pressed")

    def plus_button_action(self):
        print("Plus timer pressed")

    def timer_button_action(self):
        print("Timer button pressed")

    def edit_workout_button_action(self):
        self.manager.current = "edit"

    def main_menu_button_action(self):
        self.manager.current = "main"

    def workout_data_button_action(self):
        self.manager.current = "data"


# ─── SCREENS ────────────────────────────────────────────────
class WorkoutMainScreen(BaseWorkoutScreen):
    pass


class EditWorkoutScreen(BaseWorkoutScreen):
    pass


class WorkOutDataScreen(BaseWorkoutScreen):
    pass


class ExerciseExecutionScreen(Screen):
    pass


class EndWorkoutScreen(Screen):
    pass


# ─── APP & SCREEN MANAGER ───────────────────────────────────
class WorkoutApp(App):
    def build(self):
        sm = ScreenManager(transition=NoTransition())  # <- this makes transitions instant
        sm.add_widget(WorkoutMainScreen(name="main"))
        sm.add_widget(EditWorkoutScreen(name="edit"))
        sm.add_widget(WorkOutDataScreen(name="data"))
        sm.add_widget(ExerciseExecutionScreen(name="exercise"))
        sm.add_widget(EndWorkoutScreen(name="end"))
        return sm


if __name__ == "__main__":
    WorkoutApp().run()