import sqlite3

from backend.preset_editor import PresetEditor


def test_save_preset_exercise_metric_not_duplicated(sample_db):
    """Saving a preset twice should not duplicate exercise metrics."""
    editor = PresetEditor(db_path=sample_db)
    editor.preset_name = "MetricPreset"
    editor.add_section("Main")
    editor.add_exercise(0, "Push-up")

    # First save creates the preset and associated exercise metric rows
    editor.save()

    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*)
          FROM preset_exercise_metrics pem
          JOIN preset_section_exercises se ON pem.section_exercise_id = se.id
          JOIN preset_preset_sections ps ON se.section_id = ps.id
          JOIN preset_presets p ON ps.preset_id = p.id
         WHERE p.name = ? AND pem.metric_name = ? AND pem.deleted = 0
        """,
        ("MetricPreset", "Reps"),
    )
    assert cur.fetchone()[0] == 1

    # Saving again should not insert duplicate metric rows
    editor.save()

    cur.execute(
        """
        SELECT COUNT(*)
          FROM preset_exercise_metrics pem
          JOIN preset_section_exercises se ON pem.section_exercise_id = se.id
          JOIN preset_preset_sections ps ON se.section_id = ps.id
          JOIN preset_presets p ON ps.preset_id = p.id
         WHERE p.name = ? AND pem.metric_name = ? AND pem.deleted = 0
        """,
        ("MetricPreset", "Reps"),
    )
    count = cur.fetchone()[0]
    conn.close()
    editor.close()

    assert count == 1
