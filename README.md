# Workout App

**Workout App** is a cross-platform fitness tracker built with **Kivy** and **KivyMD**. All data lives in a local SQLite database so the app works completely offline. The schema cleanly separates a global exercise library from workout presets so you can tweak a preset without affecting others. A detailed breakdown of the tables is available in [DB_DESIGN.md](DB_DESIGN.md).

## Features

- **Exercise Library** – store your favorite exercises with default metrics (reps, weight, etc.).
- **Metric Types** – define custom metrics with different input modes (text, enum, slider) and when to enter them (before/after a set or workout).
- **Workout Presets** – build reusable routines composed of ordered sections and exercises. Each preset can override metric settings or rest times.
- **Session Runner** – guides you through a workout with rest timer controls and quick metric entry screens.
- **Progress Tracking** – completed workouts are stored for review.
- **Settings & Themes** – tweak colors and timer behavior.
- **Offline First** – no network connection required once installed.

## Quick Start

1. **Install Python 3.11 or later.** Using a virtual environment is recommended.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Create the database schema** (only needed on first run):
   ```bash
   sqlite3 data/workout.db < data/workout.sql
   ```
4. **Populate the database.** The provided schema contains no sample exercises or presets. Use the Exercise Library and Preset Editor screens to create your own or import data manually using `sqlite3`.
5. **Launch the application**:
   ```bash
   python main.py
   ```
   The Kivy window will open with navigation to the library, presets and settings.

## Typical Workflow

1. Open **Exercise Library** and add exercises. For each exercise choose which metrics to track. You can create new metric types (e.g. `Weight`, `Reps`, `Time`) or reuse existing ones.
2. Navigate to **Presets** and create a new preset. Organize exercises into sections such as *Warm-up* or *Main Workout*. Adjust the number of sets and rest duration per exercise if needed.
3. Select a preset and start a **Workout Session**. The session runner shows each exercise in order, lets you record metrics after every set and includes a rest timer between sets. When all sets are finished you are presented with a summary.
4. Browse the **Workout History** screen to review past sessions and track progress over time.

## Repository Layout

- `main.py` – Kivy application entry point.
- `main.kv` – UI layout definitions.
- `core.py` – database helpers and workout logic.
- `data/` – contains the empty `workout.db` database and the `workout.sql` schema script.
- `tests/` – unit tests covering database utilities and the preset editor.

## Database

The app uses a single SQLite file located at `data/workout.db`. If the file does not exist it can be created from `data/workout.sql`. Tables include `exercises`, `metric_types`, `presets`, `sections`, and several linking tables. Consult [DB_DESIGN.md](DB_DESIGN.md) for explanations of each table and how presets copy data from the global exercise library.

## Running the Tests

Unit tests require the database to contain a preset called `Push Day` with a handful of exercises. Populate `workout.db` accordingly, then run:

```bash
pytest -q
```

Tests cover loading presets, editing them and basic workout session logic. They will fail if the database is empty.
