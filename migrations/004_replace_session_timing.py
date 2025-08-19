import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

OLD_PRE = "pre_" + "workout"
OLD_POST = "post_" + "workout"
LEGACY_MAP = {OLD_PRE: "pre_session", OLD_POST: "post_session"}
LEGACY_KEYS = tuple(LEGACY_MAP.keys())


def main() -> None:
    base = Path(__file__).resolve().parent.parent
    db_dir = base / "data"
    old_db = db_dir / "workout.db"
    backup_dir = base / "backups"
    backup_dir.mkdir(exist_ok=True)
    backup_file = backup_dir / f"workout_{int(time.time())}.db.bak"
    shutil.copyfile(old_db, backup_file)
    new_db = db_dir / "workout_new.db"
    shutil.copyfile(old_db, new_db)
    os.remove(new_db)

    src = sqlite3.connect(old_db)
    dst = sqlite3.connect(new_db)
    try:
        dst.execute("PRAGMA foreign_keys = OFF;")
        schema_sql = (db_dir / "workout_schema.sql").read_text().replace("IF NOT EXISTS", "")
        dst.executescript(schema_sql)

        tables = [r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table' AND name!='sqlite_sequence'")]
        for table in tables:
            cols = [c[1] for c in src.execute(f"PRAGMA table_info({table})")]
            placeholders = ",".join(["?"] * len(cols))
            select_rows = src.execute(f"SELECT {', '.join(cols)} FROM {table}")
            rows = []
            for row in select_rows:
                row = list(row)
                for i, val in enumerate(row):
                    if isinstance(val, str) and val in LEGACY_MAP:
                        row[i] = LEGACY_MAP[val]
                rows.append(row)
            dst.executemany(
                f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})",
                rows,
            )
            src_count = src.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            dst_count = dst.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            if src_count != dst_count:
                raise RuntimeError(f"Row count mismatch for {table}: {src_count} != {dst_count}")
            print(f"✅ Copied {src_count} rows from table: {table}")

        try:
            seq_rows = src.execute("SELECT name, seq FROM sqlite_sequence").fetchall()
            dst.execute("DELETE FROM sqlite_sequence")
            dst.executemany("INSERT INTO sqlite_sequence(name, seq) VALUES (?, ?)", seq_rows)
            print(f"✅ Copied {len(seq_rows)} rows from table: sqlite_sequence")
        except sqlite3.OperationalError:
            pass

        dst.execute("PRAGMA foreign_keys = ON;")
        fk_errors = dst.execute("PRAGMA foreign_key_check;").fetchall()
        if fk_errors:
            raise RuntimeError(f"Foreign key violations detected: {fk_errors}")

        bad = []
        for table in tables:
            cols = [c[1] for c in dst.execute(f"PRAGMA table_info({table})")]
            for col in cols:
                query = f"SELECT COUNT(*) FROM {table} WHERE {col} IN (?, ?)"
                count = dst.execute(query, LEGACY_KEYS).fetchone()[0]
                if count:
                    bad.append((table, col, count))
        if bad:
            raise RuntimeError(f"Found legacy timing values: {bad}")

        dst.commit()
    except Exception as exc:
        dst.rollback()
        print(f"Migration failed: {exc}")
        sys.exit(1)
    finally:
        src.close()
        dst.close()

    shutil.move(str(new_db), str(old_db))
    print("✅ Migration completed successfully.")


if __name__ == "__main__":
    main()
