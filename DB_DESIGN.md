# 🏋️‍♂️ workout_app Database Design

> **Note:** The database has already been created and matches the schema defined in `workout_schema.sql`. It is not an empty database.

This document describes the database schema used in **workout_app** — a personal, offline-first fitness tracking app focused on calisthenics and progressive overload.

The design favors **clarity**, **customizability**, and **full local independence** across library, presets, and completed workout sessions. The schema uses **prefix-based naming** to clearly separate concerns and enable predictable data ownership.

---

## 🚀 Schema Overview

The schema is divided into **three domains**:

| Prefix       | Purpose                                        |
|--------------|------------------------------------------------|
| `library_`   | Global exercise and metric definitions         |
| `preset_`    | Fully self-contained workout templates         |
| `session_`   | Logged workout sessions and metrics            |

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
- `library_metric_types` defines what a metric *is*, including its type, scope, and optional enum values (in JSON).
- `library_exercise_metrics` links exercises to metric types and optionally overrides properties like `type`, `input_timing`, and `enum_values_json`.

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
| `preset_preset_metrics`   | Metrics that apply to the entire preset/session (e.g., RPE, Duration); stores `metric_name` and `metric_description` snapshots |

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
- Snapshotted fields like `metric_name`, `metric_description`, `type`, etc., ensure the preset behaves the same even if the original metric definition changes or is deleted.

---

## 🔠 Prefix Summary

| Prefix       | Scope                    | Key Behavior                             |
|--------------|--------------------------|------------------------------------------|
| `library_`   | Global references         | Shared; changes can propagate            |
| `preset_`    | Fully self-contained data | Snapshotted; immune to library changes   |
| `session_`   | Logged sessions           | Captures workout history and metrics |

---

## 📊 Metrics: Lifecycle & Logic

| Stage   | Table                              | Purpose                                  |
|---------|-------------------------------------|------------------------------------------|
| Global  | `library_metric_types`              | Defines what a metric is                 |
| Exercise| `library_exercise_metrics`          | Associates metrics to global exercises   |
| Preset  | `preset_exercise_metrics`           | Snapshots metrics for preset exercises   |
| Preset  | `preset_preset_metrics`             | Adds metrics tied to the whole preset    |

📌 All metric-related tables support:
- `type`: Data and input style (int, float, str, bool, enum, slider)
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
| Workout Sessions         | `session_sessions` |
| Session Sections        | `session_session_sections` |
| Session Exercises       | `session_section_exercises` |
| Exercise Sets           | `session_exercise_sets` |
| Session Metrics         | `session_session_metrics` |
| Exercise Metrics        | `session_exercise_metrics` |
| Set Metrics             | `session_set_metrics` |

---

## 🟠 Workout Sessions (`session_`)

The `session_` tables store completed workouts. Each session captures a snapshot of the preset at the time it was run and records all metrics entered during the workout.

### 📂 Tables

| Table | Description |
|-------|-------------|
| `session_sessions` | Top-level session entry containing the preset reference, start/end timestamps, notes and `deleted` flag |
| `session_session_sections` | Sections within a session; stores name, notes, position and `deleted` flag |
| `session_section_exercises` | Exercises performed in a section; includes `number_of_sets`, `rest_time`, notes and `deleted` flag |
| `session_exercise_sets` | Individual sets with `set_number`, `started_at`, `ended_at`, notes and `deleted` flag |
| `session_session_metrics` | Metrics applying to the entire session |
| `session_exercise_metrics` | Metrics recorded for each exercise |
| `session_set_metrics` | Metrics recorded for each set |

### 🧠 Design Notes

- All timestamp columns use epoch `REAL` values.
- Every table includes a `deleted` column for soft deletes.
- Metric tables enforce valid values via `CHECK` constraints on `input_timing` and `scope`.
- Notes fields allow optional user comments on sessions, exercises and sets.

