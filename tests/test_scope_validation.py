import sys
from pathlib import Path
import sqlite3

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend import metrics


def test_set_exercise_metric_override_invalid_scope(sample_db: Path) -> None:
    """Invalid scopes should be ignored without raising errors."""
    metrics.set_exercise_metric_override("Bench Press", "Reps", scope="session", db_path=sample_db)
    conn = sqlite3.connect(sample_db)
    cur = conn.execute(
        """SELECT em.scope FROM library_exercise_metrics em
            JOIN library_exercises e ON e.id = em.exercise_id
            JOIN library_metric_types mt ON mt.id = em.metric_type_id
            WHERE e.name='Bench Press' AND mt.name='Reps'"""
    )
    assert cur.fetchone()[0] is None
    conn.close()


def test_set_section_exercise_metric_override_invalid_scope(sample_db: Path) -> None:
    metrics.set_section_exercise_metric_override(
        "Push Day",
        0,
        "Bench Press",
        "Reps",
        input_timing="post_set",
        is_required=True,
        scope="session",
        db_path=sample_db,
    )
    conn = sqlite3.connect(sample_db)
    cur = conn.execute(
        """SELECT pem.scope FROM preset_exercise_metrics pem
            JOIN preset_section_exercises se ON pem.section_exercise_id = se.id
            JOIN preset_preset_sections pps ON se.section_id = pps.id
            JOIN preset_presets p ON pps.preset_id = p.id
            WHERE p.name='Push Day' AND se.exercise_name='Bench Press' AND pem.metric_name='Reps'"""
    )
    assert cur.fetchone()[0] == "set"
    conn.close()


def test_update_metric_type_invalid_scope(sample_db: Path) -> None:
    metrics.update_metric_type("Reps", scope="section", db_path=sample_db)
    conn = sqlite3.connect(sample_db)
    cur = conn.execute("SELECT scope FROM library_metric_types WHERE name='Reps'")
    assert cur.fetchone()[0] == "set"
    conn.close()
