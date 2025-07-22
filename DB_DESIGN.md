# 🏋️‍♂️ workout_app Database Design (Prefixed Schema)

This document describes the database design for **workout_app**. The schema follows a **prefix-based naming convention** to clearly separate global, preset-specific, and session-specific data.  

This approach supports the app’s **offline-first**, highly customizable philosophy, enabling:  

- A **global exercise library** (shared across presets and sessions)  
- Reusable workout templates (**presets**) with per-preset overrides  
- Fully independent session logging (future), while still referencing global data for context  

---

## 🚀 Core Concepts

The database is structured into **three distinct parts**:  

| Prefix      | Scope                                     |
|-------------|-------------------------------------------|
| `library_`  | Global Exercise Library – shared across all presets and sessions |
| `preset_`   | Preset-Specific Data – reusable templates |
| `session_`  | (Future) Session-Specific Data – user workout logs |

This naming convention provides **clear ownership**, making it obvious which tables belong to each part.

---

## 🔵 Global Exercise Library (`library_`)

This is the **central repository** for defining exercises and their default attributes.  

| Table Name                          | Description                                      |
|-------------------------------------|--------------------------------------------------|
| `library_exercises`                 | Master list of exercises (name, description, user-created flag) |
| `library_exercise_metrics`          | Default metrics for each exercise (e.g., Reps, Weight, Tempo)  |
| `library_metric_types`              | Defines all metric types and their configurations |
| `library_exercise_enum_values`      | Custom enum values for enum-type metrics         |

✅ **Key Idea**:  
- These tables are **shared across all presets and sessions** via `exercise_id`.  
- Changes here (e.g., renaming “Bench Press”) are **immediately visible** wherever `exercise_id` is referenced.

### 📝 Metric Overrides (Per-Exercise Customization)

The `library_exercise_metrics` table now supports per-exercise customization of metric definitions. In addition to linking exercises to metric types, it includes optional override fields: `input_type`, `source_type`, `input_timing`, `is_required`, and `scope`. These fields are `NULL` by default, meaning the exercise inherits the global definition from `library_metric_types`. When populated, they allow a specific exercise (e.g., "5k Run") to redefine how a metric behaves compared to the standard (e.g., making "Distance" an enum with a preset value). This enables fine-grained control without affecting other exercises that use the same metric type.

---

## 🟢 Preset-Specific Data (`preset_`)

These tables store **workout templates (presets)**, including all their exercises, sections, and overridden metrics.  

| Table Name                             | Description                                                 |
|----------------------------------------|-------------------------------------------------------------|
| `preset_presets`                       | Workout templates containing ordered sections and exercises |
| `preset_sections`                      | Logical divisions of a preset (e.g., Warm-up, Main Workout) |
| `preset_section_exercises`             | Exercises within sections, includes position & set counts   |
| `preset_section_exercise_metrics`      | Per-preset metrics for each exercise, copied from library   |
| `preset_metadata`                      | Key-value pairs for preset-level information (e.g., “Day 1”, “Focus: Strength”) |

✅ **Key Idea**:  
- When a user adds an exercise from the library:  
  - All metrics from `library_exercise_metrics` are **copied** into `preset_section_exercise_metrics`.  
- Changes here only affect that **specific preset**.  

---

## 📦 Why Prefixes?  

| Prefix      | Purpose                                                      |
|-------------|--------------------------------------------------------------|
| `library_`  | Indicates data shared globally and referenced everywhere     |
| `preset_`   | Indicates data copied/overridden at the preset level         |
| `session_`  | (Planned) Fully self-contained session data for user logs    |

This prevents ambiguity and makes it easy to:  
- Understand which tables are **independent**  
- Know which changes propagate (library) and which don’t (preset/session)

---

## 🔥 How Metrics Work

1. **Defaults (Global)**  
   - Defined in `library_exercise_metrics`  
   - Includes all standard metrics for each exercise  

2. **Overrides (Preset-Specific)**  
   - Copied to `preset_section_exercise_metrics` when adding to a preset  
   - Editable per preset without affecting global defaults  

3. **Change Propagation Logic**  
   - Editing a global exercise or metric:  
     - ✅ Option to apply globally (affects all presets/sessions)  
     - 🚫 Or keep presets unchanged  
   - Editing inside a preset:  
     - ✅ Option to save as a new global default  
     - 🚫 Or keep change local to that preset  

---

## 📝 Example: “Bench Press” Metric Flow

| Level         | Table                                 | Action                              |
|---------------|---------------------------------------|-------------------------------------|
| Global        | `library_exercise_metrics`            | Defines default: Weight, Reps, Tempo|
| Preset        | `preset_section_exercise_metrics`     | Copied when adding to preset       |
| Session (future)| `session_exercise_metrics` (planned) | Tracks actual performed values      |

---

## 🗝️ Flexible Metadata

`preset_metadata` stores arbitrary details tied to presets:  

| Key           | Value           |
|---------------|-----------------|
| Day Number    | `1`             |
| Focus         | `Hypertrophy`   |
| Phase         | `Strength Cycle`|

This allows extensibility without changing table structure.

---

## 📦 Exercise Enums

`library_exercise_enum_values` supports enum-based metric values:  

📌 Example:  
- Metric: Machine  
- Exercise: Bench Press  
- Values:
  - Flat Barbell Bench
  - Incline Smith Machine
  - Hammer Strength Chest Press

---

## 🏋️ Preset Example: “Push Day”
- Preset: Push Day
  - Section: Warm-up
    - Exercise: Shoulder Circles
    - Exercise: Jumping Jacks
  - Section: Workout
    - Exercise: Bench Press
    - Exercise: Push-ups

Each exercise:
- Includes its own metrics (`preset_section_exercise_metrics`)
- Tracks number of sets and position in the section (`preset_section_exercises`)

---

## 💡 Design Philosophy

✔️ **Separation of Concerns**: Prefixes clarify data ownership  
✔️ **Snapshotting**: Preset tables store copies of names, descriptions, and metrics  
✔️ **Shared References**: Global exercise IDs ensure lightweight references for non-changing data  
✔️ **User Control**: All changes are explicit—no unintended side effects  

---

## 📋 Summary Table

| Feature                 | Table(s)                                     |
|-------------------------|-----------------------------------------------|
| Global Exercises        | `library_exercises`, `library_exercise_metrics`, `library_metric_types`, `library_exercise_enum_values` |
| Presets & Sections      | `preset_presets`, `preset_sections`          |
| Preset Exercises        | `preset_section_exercises`                   |
| Preset Exercise Metrics | `preset_section_exercise_metrics`            |
| Preset Metadata         | `preset_metadata`                            |

This schema provides a **modular, maintainable system** for defining workouts with full user flexibility. Prefixes make the schema **self-documenting** and prepare it for future expansion to session-level data (`session_`).

Note: The database has already been created and matches the schema defined in workout_db.sql. It is not an empty database.