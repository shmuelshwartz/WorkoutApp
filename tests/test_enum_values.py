import sqlite3
from pathlib import Path
from backend import exercises, metrics
from backend.exercise import Exercise


def test_enum_values_default_and_override(sample_db: Path) -> None:
    conn = sqlite3.connect(sample_db)
    conn.execute(
        "UPDATE library_metric_types SET enum_values_json='[\"A\",\"B\",\"C\"]' WHERE name='Machine'"
    )
    conn.commit()
    conn.close()

    # Add Machine metric to an exercise without override
    metrics.add_metric_to_exercise("Push-up", "Machine", db_path=sample_db)

    metrics_push = metrics.get_metrics_for_exercise("Push-up", db_path=sample_db)
    vals_push = next(m["values"] for m in metrics_push if m["name"] == "Machine")
    assert vals_push == ["A", "B", "C"]

    metrics_bench = metrics.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    vals_bench = next(m["values"] for m in metrics_bench if m["name"] == "Machine")
    assert vals_bench == ["A", "B"]

    # Override enum values for Bench Press
    ex = Exercise("Bench Press", db_path=sample_db)
    ex.update_metric("Machine", values=["A"])
    exercises.save_exercise(ex)

    metrics_bench2 = metrics.get_metrics_for_exercise("Bench Press", db_path=sample_db)
    vals_bench2 = next(m["values"] for m in metrics_bench2 if m["name"] == "Machine")
    assert vals_bench2 == ["A"]
