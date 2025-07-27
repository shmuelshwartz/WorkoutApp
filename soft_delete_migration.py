import sqlite3
from pathlib import Path
import shutil
import sys

DEFAULT_DB_PATH = Path('data') / 'workout.db'

def column_exists(conn, table, column):
    cur = conn.execute(f"PRAGMA table_info({table})")
    return any(row[1] == column for row in cur.fetchall())

def add_deleted_column(conn, table):
    if not column_exists(conn, table, 'deleted'):
        conn.execute(f"ALTER TABLE {table} ADD COLUMN deleted INTEGER DEFAULT 0")
    conn.execute(f"UPDATE {table} SET deleted = 0 WHERE deleted IS NULL")

def main(db_path: Path):
    if not db_path.exists():
        print(f'Database not found: {db_path}')
        return
    backup_path = db_path.with_suffix('.bak')
    if not backup_path.exists():
        shutil.copy2(db_path, backup_path)
    conn = sqlite3.connect(str(db_path))
    tables = [
        'library_exercises',
        'library_metric_types',
        'library_exercise_metrics',
        'preset_presets',
        'preset_sections',
        'preset_section_exercises',
        'preset_section_exercise_metrics',
        'preset_metadata',
    ]
    for table in tables:
        add_deleted_column(conn, table)
    conn.commit()
    conn.close()
    print('Migration completed.')

if __name__ == '__main__':
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DB_PATH
    main(path)
