#!/usr/bin/env python3
"""SQLite migration for workout app database.

This script migrates a source database using the old `(name, is_user_created)`
uniqueness rules to a destination database where `name` is the only unique
column for `library_exercises` and `library_metric_types`.

Duplicates based on `name` are merged, all foreign keys are rewired to the
chosen primary rows, and the schema is recreated with the new unique indexes.

Usage
-----
```
python migrate_is_user_created_unify_names.py --src old.db --dst new.db
```
"""

from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def fetch_all(cur: sqlite3.Cursor, table: str) -> Tuple[List[sqlite3.Row], List[str]]:
    """Return all rows and column names for *table* from the cursor."""
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    return rows, cols


def insert_rows(cur: sqlite3.Cursor, table: str, cols: Iterable[str], rows: Iterable[sqlite3.Row]) -> None:
    """Insert *rows* into *table* using explicit *cols* order."""
    placeholders = ",".join(["?"] * len(cols))
    col_list = ",".join(cols)
    for row in rows:
        cur.execute(
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders})",
            [row[c] for c in cols],
        )

# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def create_tables(src_cur: sqlite3.Cursor, dst_cur: sqlite3.Cursor) -> None:
    """Create all tables in the destination database."""
    for sql, in src_cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ):
        dst_cur.execute(sql)


def create_indexes(src_cur: sqlite3.Cursor, dst_cur: sqlite3.Cursor) -> None:
    """Recreate indexes in destination with updated uniqueness rules."""
    drop_indexes = {
        "idx_library_exercises_name_user_created",
        "idx_library_metric_types_name_user_created",
    }
    for name, sql in src_cur.execute(
        "SELECT name, sql FROM sqlite_master WHERE type='index' AND sql NOT NULL"
    ):
        if name in drop_indexes:
            continue
        dst_cur.execute(sql)

    # New unique indexes
    dst_cur.execute(
        """
        CREATE UNIQUE INDEX idx_library_exercises_name_unique
        ON library_exercises(name);
        """
    )
    dst_cur.execute(
        """
        CREATE UNIQUE INDEX idx_library_metric_types_name_unique
        ON library_metric_types(name);
        """
    )

# ---------------------------------------------------------------------------
# Deduplication logic
# ---------------------------------------------------------------------------


def choose_primary(rows: List[sqlite3.Row]) -> sqlite3.Row:
    """Return the primary row from *rows* based on deduplication rules."""
    def sort_key(r: sqlite3.Row) -> Tuple[int, int, int]:
        deleted_key = r["deleted"]
        desc_key = 1 if not r["description"] else 0
        return (deleted_key, desc_key, r["id"])

    return sorted(rows, key=sort_key)[0]


def merge_description(primary: sqlite3.Row, group: List[sqlite3.Row]) -> str:
    """Return description for primary, filling from duplicates if needed."""
    if primary["description"]:
        return primary["description"]
    for row in group:
        if row["id"] != primary["id"] and row["description"]:
            return row["description"]
    return primary["description"]


def dedup_table(
    src_cur: sqlite3.Cursor,
    dst_cur: sqlite3.Cursor,
    table: str,
    key: str,
) -> Tuple[Dict[int, int], int]:
    """Generic deduplication for library tables keyed by name."""
    rows, cols = fetch_all(src_cur, table)
    groups: Dict[str, List[sqlite3.Row]] = defaultdict(list)
    for row in rows:
        groups[row[key]].append({c: row[c] for c in cols})

    id_map: Dict[int, int] = {}
    deduped = 0
    to_insert: List[Dict[str, object]] = []

    for name, group in groups.items():
        primary = choose_primary(group)
        primary_desc = merge_description(primary, group)
        primary["description"] = primary_desc
        to_insert.append(primary)
        for row in group:
            id_map[row["id"]] = primary["id"]
        deduped += len(group) - 1
        if len(group) > 1:
            dup_ids = [str(r["id"]) for r in group if r["id"] != primary["id"]]
            print(f"Deduplicated {table[:-1]} '{name}': kept {primary['id']}, merged {', '.join(dup_ids)}")

    insert_rows(dst_cur, table, cols, to_insert)
    # Log row count for verification
    print(f"✅ Migrated {len(to_insert)} rows into {table}")
    return id_map, deduped

# ---------------------------------------------------------------------------
# Table copy helpers
# ---------------------------------------------------------------------------

def copy_with_maps(
    src_cur: sqlite3.Cursor,
    dst_cur: sqlite3.Cursor,
    table: str,
    map_spec: Dict[str, Tuple[Dict[int, int], str]],
    counters: Dict[str, int],
) -> None:
    """Copy table applying ID maps according to *map_spec*.

    map_spec maps column names to tuples of (id_map, counter_key).
    """
    rows, cols = fetch_all(src_cur, table)
    processed: List[Dict[str, object]] = []
    for row in rows:
        new_row = {c: row[c] for c in cols}
        for col, (id_map, counter_key) in map_spec.items():
            old = new_row[col]
            new = id_map.get(old, old)
            if new != old:
                counters[counter_key] += 1
            new_row[col] = new
        processed.append(new_row)
    insert_rows(dst_cur, table, cols, processed)
    # Log row count for verification
    print(f"✅ Migrated {len(processed)} rows into {table}")


def copy_library_exercise_metrics(
    src_cur: sqlite3.Cursor,
    dst_cur: sqlite3.Cursor,
    exercise_map: Dict[int, int],
    metric_map: Dict[int, int],
    counters: Dict[str, int],
) -> None:
    """Copy `library_exercise_metrics` with deduplication after rewiring."""
    rows, cols = fetch_all(src_cur, "library_exercise_metrics")
    groups: Dict[Tuple[int, int], List[Dict[str, object]]] = defaultdict(list)
    for row in rows:
        new_row = {c: row[c] for c in cols}
        old_e = new_row["exercise_id"]
        old_m = new_row["metric_type_id"]
        new_e = exercise_map.get(old_e, old_e)
        new_m = metric_map.get(old_m, old_m)
        if new_e != old_e:
            counters["exercise"] += 1
        if new_m != old_m:
            counters["metric"] += 1
        new_row["exercise_id"] = new_e
        new_row["metric_type_id"] = new_m
        groups[(new_e, new_m)].append(new_row)

    out_rows: List[Dict[str, object]] = []
    for (_, _), group in groups.items():
        non_deleted = [r for r in group if r["deleted"] == 0]
        if len(non_deleted) > 1:
            keep = min(non_deleted, key=lambda r: r["id"])
            for r in non_deleted:
                if r is not keep:
                    r["deleted"] = 1
        out_rows.extend(group)

    insert_rows(dst_cur, "library_exercise_metrics", cols, out_rows)
    # Log row count for verification
    print(f"✅ Migrated {len(out_rows)} rows into library_exercise_metrics")

# ---------------------------------------------------------------------------
# Remaining tables
# ---------------------------------------------------------------------------

def copy_remaining_tables(
    src_cur: sqlite3.Cursor,
    dst_cur: sqlite3.Cursor,
    processed: Iterable[str],
) -> None:
    """Copy any tables not yet processed."""
    processed_set = set(processed)
    table_names = [
        name
        for name, in src_cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
        if name not in processed_set
    ]
    for table in table_names:
        rows, cols = fetch_all(src_cur, table)
        insert_rows(dst_cur, table, cols, rows)
        # Log row count for verification
        print(f"✅ Migrated {len(rows)} rows into {table}")

# ---------------------------------------------------------------------------
# Verification helpers
# ---------------------------------------------------------------------------

def verify_no_duplicates(cur: sqlite3.Cursor, table: str) -> None:
    """Ensure *table* has unique names."""
    cur.execute(f"SELECT name, COUNT(*) FROM {table} GROUP BY name HAVING COUNT(*) > 1")
    if cur.fetchone():
        raise ValueError(f"Duplicate names found in {table}")
    cur.execute(f"SELECT COUNT(*) FROM {table} WHERE name IS NULL")
    # Detect multiple NULL names defensively
    if cur.fetchone()[0] > 1:
        raise ValueError(f"Multiple NULL names found in {table}")


def verify_active_metric_uniqueness(cur: sqlite3.Cursor) -> None:
    """Ensure active library_exercise_metrics are unique."""
    cur.execute(
        """
        SELECT exercise_id, metric_type_id, COUNT(*)
        FROM library_exercise_metrics
        WHERE deleted = 0
        GROUP BY exercise_id, metric_type_id
        HAVING COUNT(*) > 1
        """
    )
    if cur.fetchone():
        raise ValueError("Active library_exercise_metrics duplicates detected")

# ---------------------------------------------------------------------------
# Main routine
# ---------------------------------------------------------------------------

def migrate(src: str, dst: str) -> None:
    if os.path.exists(dst):
        raise FileExistsError(f"Destination database '{dst}' already exists")

    counters = {"exercise": 0, "metric": 0}
    src_con = dst_con = None

    try:
        src_con = sqlite3.connect(src)
        src_con.row_factory = sqlite3.Row
        dst_con = sqlite3.connect(dst)
        dst_con.row_factory = sqlite3.Row
        src_cur = src_con.cursor()
        dst_cur = dst_con.cursor()

        dst_cur.execute("PRAGMA foreign_keys=OFF;")
        dst_con.commit()

        # Schema setup
        create_tables(src_cur, dst_cur)

        # Dedup library tables
        exercise_map, ex_dedup = dedup_table(src_cur, dst_cur, "library_exercises", "name")
        metric_map, mt_dedup = dedup_table(src_cur, dst_cur, "library_metric_types", "name")

        # library_exercise_metrics requires both maps and dedup
        copy_library_exercise_metrics(src_cur, dst_cur, exercise_map, metric_map, counters)

        processed = {
            "library_exercises",
            "library_metric_types",
            "library_exercise_metrics",
        }

        # Preset tables
        copy_with_maps(src_cur, dst_cur, "preset_presets", {}, counters)
        processed.add("preset_presets")
        copy_with_maps(src_cur, dst_cur, "preset_preset_sections", {}, counters)
        processed.add("preset_preset_sections")
        copy_with_maps(
            src_cur,
            dst_cur,
            "preset_section_exercises",
            {"library_exercise_id": (exercise_map, "exercise")},
            counters,
        )
        processed.add("preset_section_exercises")
        copy_with_maps(
            src_cur,
            dst_cur,
            "preset_preset_metrics",
            {"library_metric_type_id": (metric_map, "metric")},
            counters,
        )
        processed.add("preset_preset_metrics")
        copy_with_maps(
            src_cur,
            dst_cur,
            "preset_exercise_metrics",
            {"library_metric_type_id": (metric_map, "metric")},
            counters,
        )
        processed.add("preset_exercise_metrics")

        # Session tables
        copy_with_maps(src_cur, dst_cur, "session_sessions", {}, counters)
        processed.add("session_sessions")
        copy_with_maps(src_cur, dst_cur, "session_session_sections", {}, counters)
        processed.add("session_session_sections")
        copy_with_maps(
            src_cur,
            dst_cur,
            "session_section_exercises",
            {"library_exercise_id": (exercise_map, "exercise")},
            counters,
        )
        processed.add("session_section_exercises")
        copy_with_maps(src_cur, dst_cur, "session_exercise_sets", {}, counters)
        processed.add("session_exercise_sets")
        copy_with_maps(
            src_cur,
            dst_cur,
            "session_session_metrics",
            {"library_metric_type_id": (metric_map, "metric")},
            counters,
        )
        processed.add("session_session_metrics")
        copy_with_maps(
            src_cur,
            dst_cur,
            "session_exercise_metrics",
            {"library_metric_type_id": (metric_map, "metric")},
            counters,
        )
        processed.add("session_exercise_metrics")
        copy_with_maps(src_cur, dst_cur, "session_set_metrics", {}, counters)
        processed.add("session_set_metrics")

        # Any remaining tables copied as-is
        copy_remaining_tables(src_cur, dst_cur, processed)

        # Create indexes after data load
        create_indexes(src_cur, dst_cur)
        dst_con.commit()

        # Verification
        verify_no_duplicates(dst_cur, "library_exercises")
        verify_no_duplicates(dst_cur, "library_metric_types")
        verify_active_metric_uniqueness(dst_cur)
        dst_cur.execute("PRAGMA foreign_keys=ON;")
        fk_violations = list(dst_cur.execute("PRAGMA foreign_key_check;"))
        if fk_violations:
            raise ValueError(f"Foreign key violations: {fk_violations}")

        dst_con.commit()
        src_con.close()
        dst_con.close()

        print(
            f"Deduplicated {ex_dedup} exercises and {mt_dedup} metric types."
        )
        print(
            f"Rewired {counters['exercise']} exercise references and {counters['metric']} metric type references."
        )
        print("Migration completed successfully.")
    except Exception as exc:  # noqa: BLE001 - we want to capture all errors
        print(f"Migration failed: {exc}")
        for con in (src_con, dst_con):
            try:
                if con is not None:
                    con.close()
            except Exception:
                pass
        if os.path.exists(dst):
            os.remove(dst)
        sys.exit(1)


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate workout DB to unified name schema")
    parser.add_argument("--src", required=True, help="Path to source .db file")
    parser.add_argument("--dst", required=True, help="Path to destination .db file")
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    migrate(args.src, args.dst)
