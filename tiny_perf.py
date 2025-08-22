"""Lightweight performance logging utilities.
# TINY-SCREEN: perf logging
"""
import os
import time
from contextlib import contextmanager
from typing import Callable

from kivy.clock import Clock

ENABLED = bool(os.environ.get("TINY_PERF"))


def log_first_paint():
    if not ENABLED:
        return
    start = time.time()

    def _log(*_):
        dur = (time.time() - start) * 1000
        print(f"TINY-PERF: first-frame {dur:.1f}ms")

    Clock.schedule_once(_log, 0)


@contextmanager
def perf_timer(label: str):
    if not ENABLED:
        yield
        return
    start = time.time()
    try:
        yield
    finally:
        dur = (time.time() - start) * 1000
        print(f"TINY-PERF: {label} {dur:.1f}ms")


def perf_decorator(label: str) -> Callable:
    def deco(fn: Callable) -> Callable:
        def wrapper(*a, **k):
            with perf_timer(label):
                return fn(*a, **k)
        return wrapper
    return deco
