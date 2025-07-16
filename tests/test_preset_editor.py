import sqlite3
import core


def _save_editor(editor: core.PresetEditor):
    conn = editor.conn
    cur = conn.cursor()
    cur.execute("DELETE FROM presets WHERE name = ?", (editor.preset_name,))
    cur.execute("INSERT INTO presets (name) VALUES (?)", (editor.preset_name,))
    preset_id = cur.lastrowid
    for s_pos, sec in enumerate(editor.sections):
        cur.execute(
            "INSERT INTO sections (preset_id, name, position) VALUES (?, ?, ?)",
            (preset_id, sec["name"], s_pos),
        )
        section_id = cur.lastrowid
        for e_pos, ex in enumerate(sec["exercises"]):
            cur.execute("SELECT id FROM exercises WHERE name=?", (ex["name"],))
            ex_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO section_exercises (section_id, exercise_id, position, number_of_sets, exercise_name, exercise_description) VALUES (?, ?, ?, ?, ?, '')",
                (section_id, ex_id, e_pos, ex.get("sets", 1), ex["name"]),
            )
    conn.commit()


def test_preset_editor_basic(sample_db):
    editor = core.PresetEditor(db_path=sample_db)
    editor.preset_name = "Custom Day"
    warm = editor.add_section("Warm-up")
    editor.add_exercise(warm, "Push-up", sets=1)
    main = editor.add_section("Main")
    editor.add_exercise(main, "Bench Press", sets=3)
    _save_editor(editor)
    editor.close()

    loaded = core.PresetEditor("Custom Day", db_path=sample_db)
    assert len(loaded.sections) == 2
    assert loaded.sections[0]["name"] == "Warm-up"
    assert loaded.sections[1]["exercises"][0]["name"] == "Bench Press"
    loaded.remove_section(0)
    _save_editor(loaded)
    loaded.close()

    check = core.PresetEditor("Custom Day", db_path=sample_db)
    assert len(check.sections) == 1
    check.close()
