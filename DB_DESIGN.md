# workout_app Database: Simple Design Overview

This database powers the workout_app and is built to be flexible, offline-first, and highly customizable.

## What It Does

- Lets users **create exercises**
- Lets users **build workout templates** (called presets), each with sections (like "Warm-up", "Main Workout") and exercises
- Lets users **track any kind of metric** (like reps, weight, RPE, or custom ones) for each exercise
- Saves all workout sessions and the details for future analysis

## How Metric Timing Works

- **Each metric** (for example, "Reps") has a default timing for when it's entered (e.g., after each set)
- **For any exercise in any workout preset**, you can override the timing for that metric (e.g., log "Reps" before starting a set for a challenge workout)
- This means most of the time, the defaults work, but you have full control to customize timing whenever you need to

## Main Tables

- **exercises**: All exercises (user-created or built-in)
- **metric_types**: The different metrics you can track (reps, weight, etc.), including their default timing
- **presets**: Workout templates
- **sections**: Parts of a preset (e.g., Warm-up, Main)
- **section_exercises**: Which exercises are in which section of a preset
- **exercise_metrics**: Which metrics are tracked for which exercise, and their default input timing
- **section_exercise_metrics**: (Overrides) Lets you change the timing for a metric for a specific exercise in a specific section

## How It All Works Together

- You set up which metrics (like Reps or Weight) to track for each exercise using **exercise_metrics**  
- If you want a special case—like logging "Reps" before a set in just one preset—you add a row to **section_exercise_metrics** for that section/exercise/metric  
- When the app needs to know when to ask for a metric, it first checks for an override in **section_exercise_metrics**; if none is found, it uses the default from **metric_types**

## Example

- Most of the time, you log "Reps" after each set
- For a "100 Push-Ups" challenge, you can set "Reps" to be logged before you start the set (as a target) just for that workout, without changing the default

---

**This approach makes the app powerful and user-friendly, allowing simple use by default, but giving total control when needed.**