import sqlite3
import shutil
import time
from pathlib import Path
import sys


ALLOWED_TYPES = ("int", "float", "str", "bool", "enum", "slider")


def main():
    base = Path(__file__).resolve().parent.parent
    db_dir = base / 'data'
    old_db = db_dir / 'workout.db'
    backup_dir = base / 'backups'
    backup_dir.mkdir(exist_ok=True)
    backup_file = backup_dir / f"workout_{int(time.time())}.db.bak"
    shutil.copyfile(old_db, backup_file)
    new_db = db_dir / 'workout_new.db'
    shutil.copyfile(old_db, new_db)
    print(f"✅ Backup created at {backup_file}")

    conn = sqlite3.connect(new_db)
    try:
        conn.execute('PRAGMA foreign_keys = OFF;')

        conn.execute(
            """
            CREATE TABLE preset_preset_metrics_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                preset_id INTEGER NOT NULL,
                library_metric_type_id INTEGER,
                metric_name TEXT NOT NULL,
                metric_description TEXT,
                type TEXT NOT NULL CHECK(type IN ('int','float','str','bool','enum','slider')),
                input_timing TEXT NOT NULL CHECK(input_timing IN ('library','preset','pre_workout','post_workout')),
                scope TEXT NOT NULL CHECK(scope IN ('preset','session')),
                is_required BOOLEAN NOT NULL DEFAULT 0,
                enum_values_json TEXT,
                position INTEGER DEFAULT 0,
                deleted BOOLEAN NOT NULL DEFAULT 0,
                value TEXT,
                FOREIGN KEY(library_metric_type_id) REFERENCES library_metric_types(id) ON DELETE SET NULL,
                FOREIGN KEY(preset_id) REFERENCES preset_presets(id) ON DELETE CASCADE
            );
            """
        )
        conn.execute(
            """
            INSERT INTO preset_preset_metrics_new (
                id, preset_id, library_metric_type_id,
                metric_name, metric_description,
                type, input_timing, scope, is_required,
                enum_values_json, position, deleted, value
            )
            SELECT pm.id, pm.preset_id, pm.library_metric_type_id,
                   COALESCE(mt.name, ''), mt.description,
                   pm.type, pm.input_timing, pm.scope, pm.is_required,
                   pm.enum_values_json, pm.position, pm.deleted, pm.value
              FROM preset_preset_metrics pm
              LEFT JOIN library_metric_types mt ON pm.library_metric_type_id = mt.id;
            """
        )
        conn.execute("DROP TABLE preset_preset_metrics")
        conn.execute("ALTER TABLE preset_preset_metrics_new RENAME TO preset_preset_metrics")
        conn.execute(
            "CREATE UNIQUE INDEX idx_unique_preset_metric_active ON preset_preset_metrics (preset_id, library_metric_type_id) WHERE deleted = 0"
        )

        conn.execute('PRAGMA foreign_keys = ON;')
        fk_errors = conn.execute('PRAGMA foreign_key_check;').fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign key violations detected: {fk_errors}")
        conn.commit()
    except Exception as exc:
        conn.rollback()
        print(f"Migration failed: {exc}")
        sys.exit(1)
    finally:
        conn.close()

    shutil.move(str(new_db), str(old_db))
    print("✅ Migration completed successfully.")


if __name__ == '__main__':
    main()
