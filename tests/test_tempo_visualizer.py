from tempo import TempoCycle
import pytest
import time

try:  # pragma: no cover - optional Kivy dependency
    from ui.tempo_visualizer import TempoVisualizer
    kivy_available = True
except Exception:  # pragma: no cover - Kivy not installed
    TempoVisualizer = None
    kivy_available = False


def test_phase_progress_and_order():
    cycle = TempoCycle("3412")
    assert [p.duration for p in cycle.phases] == [1, 2, 3, 4]
    assert cycle.total == 10

    idx, frac, remaining = cycle.phase_at(3.4)
    assert idx == 2  # eccentric phase
    assert round(frac, 2) == round(0.4 / 3, 2)
    assert round(remaining, 1) == round(10 - 3.4, 1)


def test_wraps_after_total():
    cycle = TempoCycle("3412")
    idx, frac, _ = cycle.phase_at(10.5)
    assert idx == 0  # new rep, concentric
    assert round(frac, 2) == 0.5


@pytest.mark.skipif(not kivy_available, reason="Kivy and KivyMD are required")
def test_visualizer_uses_start_time(monkeypatch):
    viz = TempoVisualizer(tempo="1111")
    monkeypatch.setattr(time, "time", lambda: 105.0)
    monkeypatch.setattr(time, "perf_counter", lambda: 200.0)
    viz.start(start_time=100.0)
    assert viz._start == 195.0
    monkeypatch.setattr(time, "perf_counter", lambda: 197.0)
    viz._update(0)
    assert [s.progress for s in viz._segments[:2]] == [1, 1]
    assert viz._segments[2].progress == 0
