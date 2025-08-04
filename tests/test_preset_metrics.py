import sqlite3
import core

def test_get_metrics_for_preset_pre_session(sample_db):
    conn = sqlite3.connect(sample_db)
    cur = conn.cursor()
    preset_id = cur.execute(
        "SELECT id FROM preset_presets WHERE name='Push Day'"
    ).fetchone()[0]
    cur.execute(
        """
        INSERT INTO preset_preset_metrics
            (preset_id, metric_name, type, input_timing, scope, is_required, position)
        VALUES (?, 'Duration', 'int', 'pre_workout', 'session', 1, 0)
        """,
        (preset_id,),
    )
    conn.commit()
    conn.close()

    metrics = core.get_metrics_for_preset('Push Day', db_path=sample_db)
    duration = next(m for m in metrics if m["name"] == "Duration")
    assert duration["input_timing"] == "pre_session"
    assert duration["type"] == "int"
