import sqlite3
import shutil
import time
import sys
from pathlib import Path


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
            UPDATE preset_exercise_metrics
               SET metric_description = (
                       SELECT description
                         FROM library_metric_types mt
                        WHERE mt.id = preset_exercise_metrics.library_metric_type_id
                   )
             WHERE metric_description IS NULL
            """
        )
        changed = conn.total_changes
        print(f"✅ Updated {changed} rows in preset_exercise_metrics")
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
