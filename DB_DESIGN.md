# 🏋️‍♂️ workout_app Database Design

> **Note:** The database has already been created and matches the schema defined in `workout_db.sql`. It is not an empty database.

This document describes the database schema used in **workout_app** — a personal, offline-first fitness tracking app focused on calisthenics and progressive overload.

The design favors **clarity**, **customizability**, and **full local independence** across library, presets, and future workout sessions. The schema uses **prefix-based naming** to clearly separate concerns and enable predictable data ownership.

---

## 🚀 Schema Overview

The schema is divided into **two active domains**, with a third reserved for future use:

| Prefix       | Purpose                                        |
|--------------|------------------------------------------------|
| `library_`   | Global exercise and metric definitions         |
| `preset_`    | Fully self-contained workout templates         |
| `session_`   | _(Planned)_ Individual workout logs            |

This naming convention makes the structure intuitive and avoids accidental cross-dependencies.

---

## 🔵 Global Exercise Library (`library_`)

The `library_` tables form the **central repository** of exercise and metric definitions. These are shared references used when creating presets and, later, sessions.

### 📂 Tables

| Table                        | Description                                                  |
|-----------------------------|--------------------------------------------------------------|
| `library_exercises`         | Master list of exercises (user-created or built-in)          |
| `library_metric_types`      | Definitions of all possible metric types and behaviors       |
| `library_exercise_metrics`  | Metrics associated with each exercise, with optional overrides |

### 🧠 Design Notes

- `library_exercises` uses a `is_user_created` flag and a `UNIQUE(name, is_user_created)` constraint to support personalized variants.
- `library_metric_types` defines what a metric *is*, including type, source, scope, and optional enum values (in JSON).
- `library_exercise_metrics` links exercises to metric types and optionally overrides properties like `input_type`, `input_timing`, and `enum_values_json`.

📌 All `library_` data is **global** and may be referenced by presets and sessions. However, changes here only affect presets **at creation time** — not retroactively.

---

## 🟢 Preset Templates (`preset_`)

Presets represent **workout templates** made up of sections, exercises, and per-exercise metrics. All data is **snapshotted** from the `library_` tables when the preset is created.

### ✅ Full Independence
- **Presets do not rely on the library at runtime.** If you delete everything in `library_`, your presets remain fully intact.
- Foreign keys to library tables (e.g., `library_exercise_id`) use `ON DELETE SET NULL`, ensuring no cascade loss.

### 📂 Tables

| Table                      | Description                                                      |
|---------------------------|------------------------------------------------------------------|
| `preset_presets`          | Preset definitions (e.g., “Push Day”, “Cardio A”)                |
| `preset_preset_sections`  | Named sections within a preset (e.g., “Warm-Up”, “Main Set”)     |
| `preset_section_exercises`| Exercises within a section, with full local copies of name, etc. |
| `preset_exercise_metrics` | Metrics for each exercise — snapshotted and editable             |
| `preset_preset_metrics`   | Metrics that apply to the entire preset/session (e.g., RPE, Duration) |

---

### 🏗️ Preset Structure

Presets follow this structure:

- **Preset (`preset_presets`)**
  - Sections (`preset_preset_sections`)
    - Exercises (`preset_section_exercises`)
      - Metrics (`preset_exercise_metrics`)
  - Preset-level metrics (`preset_preset_metrics`)

This allows for fine-grained control of workout logic, data input timing, and UI flow.

---

### 🧠 Design Highlights

- All tables include `position` fields to control display order in the app.
- Soft deletes are implemented uniformly via a `deleted BOOLEAN DEFAULT 0` field.
- `enum_values_json` supports customizable metric inputs like drop-downs or sliders.
- Metrics store a `value` field, supporting pre-filled defaults in both presets and exercises.
- Snapshotted fields like `metric_name`, `input_type`, etc., ensure the preset behaves the same even if the original metric definition changes or is deleted.

---

## 🔠 Prefix Summary

| Prefix       | Scope                    | Key Behavior                             |
|--------------|--------------------------|------------------------------------------|
| `library_`   | Global references         | Shared; changes can propagate            |
| `preset_`    | Fully self-contained data | Snapshotted; immune to library changes   |
| `session_`   | _(Future)_ workout logs   | Will be structured similarly to presets  |

---

## 📊 Metrics: Lifecycle & Logic

| Stage   | Table                              | Purpose                                  |
|---------|-------------------------------------|------------------------------------------|
| Global  | `library_metric_types`              | Defines what a metric is                 |
| Exercise| `library_exercise_metrics`          | Associates metrics to global exercises   |
| Preset  | `preset_exercise_metrics`           | Snapshots metrics for preset exercises   |
| Preset  | `preset_preset_metrics`             | Adds metrics tied to the whole preset    |

📌 All metric-related tables support:
- `input_type`: What kind of value (int, float, str, bool)
- `source_type`: How input is collected (text, enum, slider)
- `input_timing`: When user enters it (pre/post exercise, session, etc.)
- `scope`: Whether it applies to a set, exercise, session, or preset
- `enum_values_json`: A JSON array of options for enums
- `value`: Optional pre-filled default

---

## 🔐 Constraints & Indexes

### ✅ Unique Constraints

| Index Name                             | Purpose                                               |
|----------------------------------------|-------------------------------------------------------|
| `idx_library_exercises_name_user_created`   | Prevent duplicate exercise names by creator type      |
| `idx_library_metric_types_name_user_created`| Same for metric types                                 |
| `idx_library_exercise_metric_unique_active` | Only one active metric type per exercise              |
| `idx_unique_exercise_metric_active`         | Prevent duplicate metric names per preset exercise    |
| `idx_unique_preset_metric_active`           | Prevent duplicate metrics per preset                  |

All unique indexes are scoped to `deleted = 0` to support soft deletes.

---

## 🧠 Design Philosophy

| Principle              | Implementation                                                   |
|------------------------|-------------------------------------------------------------------|
| **Offline-first**      | Fully local, no external dependencies                             |
| **Snapshot-based**     | Presets copy all relevant data from the library                  |
| **Editable Templates** | Metrics and exercise details in presets are customizable          |
| **Data Clarity**       | Prefixes make ownership and dependency clear                      |
| **UI-Friendly**        | `position`, `scope`, and `enum_values_json` fields support rendering |

---

## 📋 Summary Table

| Feature                  | Table(s)                                                       |
|--------------------------|-----------------------------------------------------------------|
| Global Exercises         | `library_exercises`, `library_exercise_metrics`, `library_metric_types` |
| Preset Templates         | `preset_presets`                                               |
| Sections in Presets      | `preset_preset_sections`                                       |
| Exercises in Presets     | `preset_section_exercises`                                     |
| Metrics for Exercises    | `preset_exercise_metrics`                                      |
| Preset-Level Metrics     | `preset_preset_metrics`                                        |

---

## 🔮 Next: Session Logging (Future)

The `session_` namespace will eventually support detailed workout logs:
- Which preset (if any) the session is based on
- Real-time or retrospective metric logging
- Set-by-set performance data

---

✅ **This schema is stable, extensible, and optimized for personal use.**  
Its use of snapshotting, soft deletes, and scoped uniqueness strikes the right balance between flexibility and data integrity.