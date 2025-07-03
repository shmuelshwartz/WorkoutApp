import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import core


def test_load_workout_presets_sets():
    db_path = Path(__file__).resolve().parents[1] / "data" / "workout.db"
    presets = core.load_workout_presets(db_path)
    assert presets, "No presets loaded"
    first = presets[0]
    assert "exercises" in first
    assert isinstance(first["exercises"], list)
    assert first["exercises"]
    # All exercises in sample DB have 3 sets
    for ex in first["exercises"]:
        assert ex["sets"] == 3

