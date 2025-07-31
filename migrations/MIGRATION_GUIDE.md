# 🛠 Instructions for Writing Safe One-Time Migration Scripts

📂 **Location**: Store migration scripts in the `migrations/` directory  
🧠 **Purpose**: Perform safe schema changes that require data transformation, constraint changes, or table reconstruction.

---

## 🧱 1. BACKUP STRATEGY

### Backup the original database file
- Copy `workout.db` to `backups/workout_<EPOCHTIME>.db.bak`
- **Never skip this step** — this is your rollback path if anything fails.

### Create a working copy
- Copy `workout.db` → `workout_new.db` (same directory as `workout.db`)
- All migration operations are performed on `workout_new.db`, **not the original**.

---

## 🧾 2. DEFINE THE NEW SCHEMA

- Define the full schema for `workout_new.db`
- Recreate all tables explicitly (no `IF NOT EXISTS`)
- Incorporate schema changes (e.g., added/removed columns, constraint modifications)
- Ensure all foreign key relationships are logically valid
- Include `ON DELETE` / `ON UPDATE` clauses if applicable

---

## 🔁 3. DATA MIGRATION STRATEGY

Use explicit **Python scripts** to transfer data from `workout.db` to `workout_new.db`, applying transformations as needed.

### 🔸 Simple Change Examples

- **Relaxing a constraint** (`NOT NULL` → allows `NULL`):  
  → Copy data directly; no transformation needed.

- **Tightening a constraint** (allows `NULL` → `NOT NULL`):  
  → Replace `NULL` values with fallbacks (`""`, `0`, `"unknown"`, etc.)

- **Renaming columns**:  
  → Use `SELECT ... AS` or transform in Python.

- **Adding columns**:  
  → Provide default values or compute them during migration.

- **Dropping columns**:  
  → Omit them in the SELECT/copy step.

- **Dropping a column expected to be empty**:  
  - Scan the column before migrating.
  - If any non-null value exists, **abort** with:

    ```
    Column 'xyz' expected to be empty, but found non-null values.
    Aborting migration.
    ```

---

### 🔸 Complex Change Examples

- **Consolidating tables** (e.g., merging enum values into a JSON field):
  - Load related rows
  - Convert into a list or structured format
  - Save to a single column

- **Splitting tables**:
  - Extract and distribute data to new tables based on logic

- **Enum transformations**:
  - Convert between `manual_enum` rows and JSON fields

---

## ⚠️ 4. FOREIGN KEY SAFETY

- Disable foreign key checks **before** any changes:

    ```sql
    PRAGMA foreign_keys = OFF;
    ```

- Insert data in correct dependency order (parent → child, referenced → referencing).

- After migration, re-enable foreign keys and validate:

    ```sql
    PRAGMA foreign_keys = ON;
    PRAGMA foreign_key_check;
    ```

- If violations are found, abort the process and report them.

---

## 🧪 5. INTEGRITY CHECKS

After each table is migrated:

- Check row counts match using `SELECT COUNT(*)`
- Optionally checksum important data
- Print logs like:

    ```
    ✅ Migrated 250 rows from table: library_exercises
    ```

---

## 🔒 6. TRANSACTIONAL CONTROL

- Never modify `workout.db` directly.
- Do not call `PRAGMA foreign_keys = ON` or `COMMIT` after the DB connection is closed.
- Do not create views or indexes until after data migration completes.

---

## 🧹 7. FINALIZATION

After successful migration:

- Replace `workout.db` with `workout_new.db`
- Retain `.bak` file permanently for rollback
- Optionally rename `workout_new.db` to `workout.db` (only if all checks pass)
- Print clear success or failure message

---

## 📌 Summary: Migration Script Checklist

| ✅ Step     | Description                                  |
|------------|----------------------------------------------|
| 🔒 Backup  | Save workout_<time>.db.bak                   |
| 📄 Schema  | Build workout_new.db schema manually          |
| 🔁 Data    | Transform and copy each table carefully       |
| ⚠️ FK Off  | Keep FKs OFF during data operations           |
| ✅ FK Check| Enable and validate with foreign_key_check    |
| 🧪 Verify  | Match row counts, print debug logs            |
| 🧼 Swap    | Replace old DB only after success             |
| 🧯 On Error| Abort cleanly, keep .bak for recovery         |

---

## 👀 Additional Best Practices

- Always test `workout_new.db` with the app before replacing the live DB.
- Log every migration phase and any unexpected findings.
- For major changes, consider adding a "dry run" mode in scripts.
- Name migration scripts with an incrementing number and a short description, e.g., `003_add_duration_column.py`.
- If you hit an error, restore the backup:  
  `cp backups/workout_<EPOCH>.db.bak workout.db`
- Never modify `workout.db` except via reviewed migration scripts.
- Never ignore foreign key violations or silent errors.

---

## 📝 Example Minimal Migration Script

```python
import shutil
import sqlite3

# Step 1: Backup
shutil.copyfile('workout.db', 'backups/workout_1699320031.db.bak')
shutil.copyfile('workout.db', 'workout_new.db')

# Step 2: Connect and test schema change (example: add a column)
conn = sqlite3.connect('workout_new.db')
conn.execute('PRAGMA foreign_keys = OFF;')
conn.execute('ALTER TABLE library_exercises ADD COLUMN new_col TEXT;')
conn.commit()
conn.close()

print("Migration completed. Check logs and test the new DB before swapping.")
```