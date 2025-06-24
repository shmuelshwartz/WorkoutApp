"""Utility classes that encapsulate simple workout timing logic."""

from time import time


class Manager:
    """Keep track of workout timing state."""

    def __init__(self):
        """Initialize timer related state."""
        self.next_workout_start_time = time()
        self.pause_time = None
        self.is_ready = False

    def set_next_workout_start_time(self):
        """Schedule the next workout 15 seconds from now."""
        self.next_workout_start_time = time() + 15