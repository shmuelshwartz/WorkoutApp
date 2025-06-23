from time import time


class Manager:
    def __init__(self):
        self.next_workout_start_time = time()
        self.pause_time = None
        self.is_ready = False

    def set_next_workout_start_time(self):
        self.next_workout_start_time = time() + 15