from tempo import TempoCycle


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
