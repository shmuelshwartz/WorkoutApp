"""Simple CLI to inspect the SQLite workout database.

Lists tables and optionally previews rows from a specified table.
"""
import argparse
import sqlite3
from pathlib import Path

# Path to the main workout database
default_db = Path(__file__).resolve().parents[1] / "data" / "workout.db"

def list_tables(cursor):
    """Return a list of table names in the connected database."""
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    return [row[0] for row in cursor.fetchall()]

def preview_table(cursor, table, limit):
    """Fetch up to *limit* rows from *table*.

    Args:
        cursor: SQLite cursor.
        table (str): Table name to query.
        limit (int): Number of rows to return.
    """
    cursor.execute(f"SELECT * FROM {table} LIMIT ?", (limit,))
    return cursor.fetchall()

def main():
    parser = argparse.ArgumentParser(description="Inspect the workout SQLite database.")
    parser.add_argument("--table", "-t", help="Table name to preview")
    parser.add_argument("--limit", "-l", type=int, default=5, help="Number of rows to display")
    parser.add_argument("--db", type=Path, default=default_db, help="Path to the SQLite database")
    args = parser.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    cur = conn.cursor()

    tables = list_tables(cur)
    print("Tables:")
    for name in tables:
        print(f"  - {name}")

    if args.table:
        if args.table not in tables:
            print(f"\nTable '{args.table}' not found.")
        else:
            print(f"\nRows from '{args.table}':")
            rows = preview_table(cur, args.table, args.limit)
            for row in rows:
                print(row)

    conn.close()

if __name__ == "__main__":
    main()
