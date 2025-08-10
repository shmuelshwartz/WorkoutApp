# Backend Development Guidelines

## Purpose
The backend contains **all business logic and state management** for the workout app.
It can run entirely without the UI or database once initialized.
It should be usable:
1. From the Kivy UI through adapters.
2. From the CLI for testing and simulation.
3. From stub JSON data for isolated runs.

---

## Rules

### 1. No UI dependencies
- Do NOT import Kivy or any UI modules here.
- Backend should be UI-agnostic; all interaction happens via method calls and returned data.

### 2. Database independence during operation
- The backend may load data from the DB **only at initialization**.
- Once initialized, all state must be kept in memory (e.g., dictionaries, lists, dataclasses, JSON).
- This ensures the backend can run in offline simulation or test mode.

### 3. Clear data flow
- All input from the UI or CLI should be passed in as plain Python primitives or JSON-like dict/list objects.
- All output should be in the same plain format — no UI widgets or DB cursors.

### 4. One file per main component
- `workout_session.py` → Active workout session state & methods.
- `preset.py` → Logic for creating, editing, validating presets.
- `exercise.py` → Exercise definition logic.
- `settings.py` → App settings handling.
- `cli.py` → Command-line interface for backend testing.
- `utils.py` → Helper functions for backend logic.

### 5. State handling
- Immutable state: the loaded preset (e.g., stored as JSON or dataclass) should never be mutated.
- Mutable state: session progress (sets completed, times, notes) is stored separately and updated as the workout runs.

### 6. Testability
- All classes should be instantiable with **stub data** (no DB calls required).
- Any DB interaction should be wrapped in functions that can be replaced or mocked.

---

## Coding style for Codex
- Keep methods short and focused (under ~30 LOC if possible).
- Prefer descriptive names over abbreviations.
- Avoid large, deeply nested structures — break them into helper methods.
- Comment data formats (e.g., expected JSON structure for presets) in docstrings.
- Avoid circular imports — pass dependencies explicitly.

---

## Example backend flow
1. **Initialize**:
   - Load preset from DB adapter or JSON stub.
   - Create `WorkoutSession` object with that preset.
2. **Run**:
   - Add sets, update progress, calculate metrics — all in memory.
3. **Save**:
   - Commit final progress to DB or export as JSON.

---

## Future-proofing
- This layer should work the same whether the DB is SQLite, a file, or an API.
- The DB adapter will be swapped without changing backend logic.
- All time calculations, metrics, and workout logic must live here, not in UI or DB.
