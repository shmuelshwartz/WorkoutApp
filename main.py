from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import Screen, ScreenManager


class WelcomeScreen(Screen):
    pass


class HomeScreen(Screen):
    pass


class SelectWorkoutScreen(Screen):
    pass


class SettingsScreen(Screen):
    pass


class StartWorkoutScreen(Screen):
    pass


class ActiveScreen(Screen):
    pass


class RestScreen(Screen):
    pass


class WorkoutApp(App):
    def build(self):
        return Builder.load_file("main.kv")


if __name__ == "__main__":
    WorkoutApp().run()
