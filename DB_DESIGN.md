# workout_app Database Design

This document describes the database design for **workout_app**. The schema is designed for an **offline-first**, highly customizable fitness app where users can:

- Define exercises and their default metrics globally
- Build reusable workout templates (called presets)
- Customize metrics per preset without affecting the global defaults
- Track flexible metadata for presets

---

## 🚀 Core Concepts

The database cleanly separates:

### 🔵 Global Exercise Library
- `exercises`: Master list of all exercises
- `exercise_metrics`: Default metrics for each exercise
- `exercise_enum_values`: Custom enums for enum-type metrics

This acts as a central repository of exercises and their typical metrics.

---

### 🟢 Preset-Specific Data
- `presets`: Workout templates
- `sections`: Logical divisions of a preset (e.g., Warm-up, Workout)
- `section_exercises`: Exercises within sections, with position and set counts
- `section_exercise_metrics`: Per-preset metrics for each exercise, copied from defaults

When a user adds an exercise from the library to a preset:
- All associated metrics from `exercise_metrics` are **copied** into `section_exercise_metrics`
- Changes made in the preset only affect that preset

---

### 📝 Preset Metadata
Additional attributes tied to presets (e.g., “Day Number”, “Focus Area”):
- `preset_metadata`: Stores key-value pairs for each preset

This enables descriptive presets without altering the core schema.

---

---

## 🗂️ Main Tables

| Table                      | Description                                                                                    |
|----------------------------|------------------------------------------------------------------------------------------------|
| `exercises`                | Master list of all exercises (name, description, user-created flag)                            |
| `exercise_metrics`         | Default metrics for each exercise (referencing `metric_types`)                                 |
| `metric_types`             | Definitions of all possible metrics (e.g., Reps, Weight, RPE) and their input configurations   |
| `exercise_enum_values` | Custom enum values tied to specific metrics and exercises                                      |
| `presets`                  | Workout templates containing ordered sections and exercises                                    |
| `preset_metadata`          | Key-value pairs for preset-level information (e.g., “Day 1”, “Focus: Strength”)                |
| `sections`                 | Logical divisions of a preset (e.g., Warm-up, Workout)                                         |
| `section_exercises`        | Exercises within sections, with position and set counts; includes snapshot of name/description |
| `section_exercise_metrics` | Metrics tracked for exercises within a preset, possibly overriding global defaults             |

---

---

## 🔥 How Metrics Work

1. **Defaults (Global)**
   - `exercise_metrics` defines which metrics are tracked for each exercise by default

2. **Overrides (Preset-Specific)**
   - `section_exercise_metrics` copies defaults when adding an exercise to a preset
   - Changes made here only affect the specific preset

3. **Change Propagation**
   - When editing a global exercise or metric, the app asks:
     - ✅ Apply change globally?
     - ✅ Apply to selected presets?
     - 🚫 Keep existing presets unchanged?
   - When editing inside a preset:
     - ✅ Save as new default?
     - 🚫 Keep change local to the preset?

---

---

## 📝 Example: “Bench Press” Metric Flow

| Global                     | Preset-Specific                                           |
|----------------------------|-----------------------------------------------------------|
| `exercise_metrics`: Weight | Copied to `section_exercise_metrics` when added to preset |
| `exercise_metrics`: Reps   | Copied and editable per preset                            |

If the user changes "Reps" input timing for Bench Press inside a preset:
- They can decide if the change becomes the new default globally or stays local to the preset.

---

---

## 🗝️ Flexible Metadata

`preset_metadata` supports adding arbitrary details to presets, such as:
- Day Number: `1`
- Focus: `Hypertrophy`
- Phase: `Strength Cycle`

This enables descriptive presets without modifying core tables.

---

---

## 📦 Exercise Enums

`exercise_enum_values` allows adding custom enum values to metrics of type `manual_enum`.

📌 Example:
- Metric: Machine
- Exercise: Bench Press
- Values:
  - Flat Barbell Bench
  - Incline Smith Machine
  - Hammer Strength Chest Press

This gives users control over dropdown lists for their exercises.

---

---

## 🏋️ How Presets Are Structured

### Example: “Push Day”

- Preset: Push Day
  - Section: Warm-up
    - Exercise: Shoulder Circles
    - Exercise: Jumping Jacks
  - Section: Workout
    - Exercise: Bench Press
    - Exercise: Push-ups

Each exercise:
- Includes its own metrics (`section_exercise_metrics`)
- Tracks number of sets and position in the section (`section_exercises`)

---

---

## 💡 Design Philosophy

✔️ **Separation of Concerns**: Global library vs preset-specific data  
✔️ **User Control**: Change propagation is optional and user-driven  
✔️ **Flexibility**: Metadata system supports future preset attributes without schema changes  
✔️ **Snapshotting**: Preset tables store names/descriptions as they were at copy time  

---

---

## 📋 Summary

| Feature                 | Table(s)                        |
|-------------------------|---------------------------------|
| Global Exercises        | `exercises`, `exercise_metrics` |
| Presets & Sections      | `presets`, `sections`           |
| Preset Exercises        | `section_exercises`             |
| Preset Exercise Metrics | `section_exercise_metrics`      |
| Custom Enums            | `exercise_enum_values`      |
| Preset Metadata         | `preset_metadata`               |

This schema provides a **powerful, modular system** for defining workouts while giving users the freedom to tweak and reuse exercises flexibly.