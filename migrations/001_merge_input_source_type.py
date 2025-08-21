import sqlite3
from pathlib import Path
import shutil
import time
import sys

ALLOWED_TYPES = ("int", "float", "str", "bool", "enum", "slider")


def check_columns(conn, table):
    cols = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
    if "input_type" not in cols or "source_type" not in cols:
        raise RuntimeError(f"{table} is missing input_type or source_type column")


def validate_data(conn, table):
    mismatch_slider = conn.execute(
        f"SELECT id, input_type, source_type FROM {table} "
        "WHERE source_type='manual_slider' AND (input_type IS NULL OR input_type != 'float')"
    ).fetchall()
    if mismatch_slider:
        raise RuntimeError(f"{table}: expected input_type 'float' when source_type is manual_slider: {mismatch_slider}")

    mismatch_enum = conn.execute(
        f"SELECT id, input_type, source_type FROM {table} "
        "WHERE source_type='manual_enum' AND (input_type IS NULL OR input_type != 'str')"
    ).fetchall()
    if mismatch_enum:
        raise RuntimeError(f"{table}: expected input_type 'str' when source_type is manual_enum: {mismatch_enum}")


def migrate_library_metric_types(conn):
    conn.execute(
        """
        CREATE TABLE library_metric_types_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            type TEXT NOT NULL CHECK(type IN ('int','float','str','bool','enum','slider')),
            input_timing TEXT NOT NULL CHECK(input_timing IN ('library','preset','pre_session','post_session','pre_exercise','post_exercise','pre_set','post_set')),
            scope TEXT NOT NULL CHECK(scope IN ('preset','session','exercise','set')),
            is_required BOOLEAN DEFAULT FALSE,
            enum_values_json TEXT,
            is_user_created BOOLEAN NOT NULL DEFAULT 0,
            deleted BOOLEAN NOT NULL DEFAULT 0
        );
        """
    )

    conn.execute(
        """
        INSERT INTO library_metric_types_new (
            id, name, description, type, input_timing, scope,
            is_required, enum_values_json, is_user_created, deleted
        )
        SELECT id, name, description,
               CASE WHEN source_type='manual_enum' THEN 'enum'
                    WHEN source_type='manual_slider' THEN 'slider'
                    ELSE input_type END,
               input_timing, scope,
               is_required, enum_values_json, is_user_created, deleted
        FROM library_metric_types;
        """
    )
    conn.execute("DROP TABLE library_metric_types")
    conn.execute("ALTER TABLE library_metric_types_new RENAME TO library_metric_types")
    conn.execute(
        "CREATE UNIQUE INDEX idx_library_metric_types_name_user_created ON library_metric_types (name, is_user_created)"
    )


def migrate_library_exercise_metrics(conn):
    conn.execute(
        """
        CREATE TABLE library_exercise_metrics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            exercise_id INTEGER NOT NULL,
            metric_type_id INTEGER NOT NULL,
            type TEXT CHECK(type IS NULL OR type IN ('int','float','str','bool','enum','slider')),
            input_timing TEXT CHECK(input_timing IS NULL OR input_timing IN ('library','preset','pre_session','post_session','pre_exercise','post_exercise','pre_set','post_set')),
            scope TEXT CHECK(scope IS NULL OR scope IN ('exercise','set')),
            is_required BOOLEAN,
            enum_values_json TEXT,
            position INTEGER DEFAULT 0,
            deleted BOOLEAN NOT NULL DEFAULT 0,
            value TEXT,
            FOREIGN KEY(exercise_id) REFERENCES library_exercises(id) ON DELETE CASCADE,
            FOREIGN KEY(metric_type_id) REFERENCES library_metric_types(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        INSERT INTO library_exercise_metrics_new (
            id, exercise_id, metric_type_id, type, input_timing, scope,
            is_required, enum_values_json, position, deleted, value
        )
        SELECT id, exercise_id, metric_type_id,
               CASE WHEN source_type='manual_enum' THEN 'enum'
                    WHEN source_type='manual_slider' THEN 'slider'
                    ELSE input_type END,
               input_timing, scope, is_required, enum_values_json, position, deleted, value
        FROM library_exercise_metrics;
        """
    )
    conn.execute("DROP TABLE library_exercise_metrics")
    conn.execute("ALTER TABLE library_exercise_metrics_new RENAME TO library_exercise_metrics")
    conn.execute(
        "CREATE UNIQUE INDEX idx_library_exercise_metric_unique_active ON library_exercise_metrics (exercise_id, metric_type_id) WHERE deleted = 0"
    )


def migrate_preset_exercise_metrics(conn):
    conn.execute(
        """
        CREATE TABLE preset_exercise_metrics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            section_exercise_id INTEGER NOT NULL,
            library_metric_type_id INTEGER,
            metric_name TEXT NOT NULL,
            metric_description TEXT,
            type TEXT NOT NULL CHECK(type IN ('int','float','str','bool','enum','slider')),
            input_timing TEXT NOT NULL CHECK(input_timing IN ('preset','pre_session','post_session','pre_exercise','post_exercise','pre_set','post_set')),
            scope TEXT NOT NULL CHECK(scope IN ('exercise','set')),
            is_required BOOLEAN NOT NULL DEFAULT 0,
            enum_values_json TEXT,
            position INTEGER NOT NULL DEFAULT 0,
            deleted BOOLEAN NOT NULL DEFAULT 0,
            value TEXT,
            FOREIGN KEY(library_metric_type_id) REFERENCES library_metric_types(id) ON DELETE SET NULL,
            FOREIGN KEY(section_exercise_id) REFERENCES preset_section_exercises(id) ON DELETE CASCADE
        );
        """
    )
    conn.execute(
        """
        INSERT INTO preset_exercise_metrics_new (
            id, section_exercise_id, library_metric_type_id, metric_name, metric_description,
            type, input_timing, scope, is_required, enum_values_json,
            position, deleted, value
        )
        SELECT id, section_exercise_id, library_metric_type_id, metric_name, metric_description,
               CASE WHEN source_type='manual_enum' THEN 'enum'
                    WHEN source_type='manual_slider' THEN 'slider'
                    ELSE input_type END,
               input_timing, scope, is_required, enum_values_json,
               position, deleted, value
        FROM preset_exercise_metrics;
        """
    )
    conn.execute("DROP TABLE preset_exercise_metrics")
    conn.execute("ALTER TABLE preset_exercise_metrics_new RENAME TO preset_exercise_metrics")
    conn.execute(
        "CREATE UNIQUE INDEX idx_unique_exercise_metric_active ON preset_exercise_metrics (section_exercise_id, metric_name) WHERE deleted = 0"
    )


def migrate_preset_preset_metrics(conn):
    conn.execute(
        """
        CREATE TABLE preset_preset_metrics_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            preset_id INTEGER NOT NULL,
            library_metric_type_id INTEGER,
            type TEXT NOT NULL CHECK(type IN ('int','float','str','bool','enum','slider')),
            input_timing TEXT NOT NULL CHECK(input_timing IN ('library','preset','pre_session','post_session')),
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
            id, preset_id, library_metric_type_id, type, input_timing,
            scope, is_required, enum_values_json, position, deleted, value
        )
        SELECT id, preset_id, library_metric_type_id,
               CASE WHEN source_type='manual_enum' THEN 'enum'
                    WHEN source_type='manual_slider' THEN 'slider'
                    ELSE input_type END,
               input_timing, scope, is_required, enum_values_json, position, deleted, value
        FROM preset_preset_metrics;
        """
    )
    conn.execute("DROP TABLE preset_preset_metrics")
    conn.execute("ALTER TABLE preset_preset_metrics_new RENAME TO preset_preset_metrics")
    conn.execute(
        "CREATE UNIQUE INDEX idx_unique_preset_metric_active ON preset_preset_metrics (preset_id, library_metric_type_id) WHERE deleted = 0"
    )


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

        for table in [
            'library_metric_types',
            'library_exercise_metrics',
            'preset_exercise_metrics',
            'preset_preset_metrics',
        ]:
            check_columns(conn, table)
            validate_data(conn, table)

        migrate_library_metric_types(conn)
        migrate_library_exercise_metrics(conn)
        migrate_preset_exercise_metrics(conn)
        migrate_preset_preset_metrics(conn)

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
