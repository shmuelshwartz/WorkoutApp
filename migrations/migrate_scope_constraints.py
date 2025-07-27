import sqlite3
from pathlib import Path
import argparse

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "workout.db"

SCOPE_VALUES = "('preset', 'session', 'section', 'exercise', 'set')"

CREATE_LIBRARY_METRIC_TYPES = f"""
CREATE TABLE library_metric_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    input_type TEXT NOT NULL CHECK(input_type IN ('int', 'float', 'str', 'bool')),
    source_type TEXT NOT NULL CHECK(source_type IN ('manual_text', 'manual_enum', 'manual_slider')),
    input_timing TEXT NOT NULL CHECK(input_timing IN ('library', 'preset', 'pre_workout', 'post_workout', 'pre_set', 'post_set')),
    is_required BOOLEAN DEFAULT FALSE,
    scope TEXT NOT NULL CHECK(scope IN {SCOPE_VALUES}),
    description TEXT,
    is_user_created BOOLEAN NOT NULL DEFAULT 0,
    enum_values_json TEXT,
    deleted INTEGER DEFAULT 0
);
"""

CREATE_LIBRARY_EXERCISE_METRICS = f"""
CREATE TABLE library_exercise_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id INTEGER NOT NULL,
    metric_type_id INTEGER NOT NULL,
    position INTEGER DEFAULT 0,
    input_type TEXT,
    source_type TEXT,
    input_timing TEXT,
    is_required BOOLEAN,
    scope TEXT CHECK(scope IS NULL OR scope IN {SCOPE_VALUES}),
    enum_values_json TEXT,
    deleted INTEGER DEFAULT 0,
    FOREIGN KEY(exercise_id) REFERENCES library_exercises(id) ON DELETE CASCADE,
    FOREIGN KEY(metric_type_id) REFERENCES library_metric_types(id) ON DELETE CASCADE
);
"""

CREATE_PRESET_SECTION_EXERCISE_METRICS = f"""
CREATE TABLE preset_section_exercise_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_exercise_id INTEGER NOT NULL,
    metric_name TEXT NOT NULL,
    input_type TEXT NOT NULL,
    source_type TEXT NOT NULL,
    input_timing TEXT NOT NULL,
    is_required BOOLEAN NOT NULL DEFAULT 0,
    scope TEXT CHECK(scope IS NULL OR scope IN {SCOPE_VALUES}),
    position INTEGER NOT NULL DEFAULT 0,
    library_metric_type_id INTEGER,
    enum_values_json TEXT,
    deleted INTEGER DEFAULT 0,
    FOREIGN KEY(section_exercise_id) REFERENCES preset_section_exercises(id) ON DELETE CASCADE
);
"""

CREATE_VIEW_LIBRARY_EXERCISE_METRICS = """
CREATE VIEW library_view_exercise_metrics AS
SELECT
    em.id AS exercise_metric_id,
    em.exercise_id,
    e.name AS exercise_name,
    em.metric_type_id,
    mt.name AS metric_type_name
FROM
    library_exercise_metrics em
JOIN
    library_exercises e ON em.exercise_id = e.id
JOIN
    library_metric_types mt ON em.metric_type_id = mt.id;
"""

CREATE_IDX_METRIC_TYPES_NAME = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_library_metric_types_name_user_created
    ON library_metric_types (name, is_user_created);
"""

def _migrate_table(cur, table, create_sql):
    cur.execute(f"ALTER TABLE {table} RENAME TO {table}_old;")
    cur.execute(create_sql)
    cols = [row[1] for row in cur.execute(f"PRAGMA table_info({table}_old);")]
    col_list = ", ".join(cols)
    cur.execute(f"INSERT INTO {table} ({col_list}) SELECT {col_list} FROM {table}_old;")
    cur.execute(f"DROP TABLE {table}_old;")


def apply_migration(db_path: Path = DEFAULT_DB_PATH) -> None:
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=OFF;")
    cur.execute("BEGIN;")

    # drop dependent view
    cur.execute("DROP VIEW IF EXISTS library_view_exercise_metrics;")

    _migrate_table(cur, "library_metric_types", CREATE_LIBRARY_METRIC_TYPES)
    _migrate_table(cur, "library_exercise_metrics", CREATE_LIBRARY_EXERCISE_METRICS)
    _migrate_table(cur, "preset_section_exercise_metrics", CREATE_PRESET_SECTION_EXERCISE_METRICS)

    cur.execute(CREATE_VIEW_LIBRARY_EXERCISE_METRICS)
    cur.execute(CREATE_IDX_METRIC_TYPES_NAME)

    cur.execute("COMMIT;")
    cur.execute("PRAGMA foreign_keys=ON;")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add scope constraints to tables")
    parser.add_argument("db_path", nargs="?", default=str(DEFAULT_DB_PATH))
    args = parser.parse_args()
    apply_migration(Path(args.db_path))
