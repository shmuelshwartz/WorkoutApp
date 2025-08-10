# UI Development Guidelines

## Purpose
The `ui/` directory contains all Kivy screens and UI components.  
Each screen must:
1. Be **importable** by other parts of the app (e.g., `main.py`, flow runners).
   2. Be **runnable directly** for quick visual testing with stub data.

Visual testing is primarily for verifying **look, layout, and basic interactions** — not business logic.

---

## Core Requirements

### 1) Importable AND Runnable
- A screen must work when:
  - Imported into another module.
  - Run directly with `python screen_file.py`.
  - Direct runs must launch a preview in one of two **test modes** (see below).

### 2) Two Test Modes
Every screen must support **two** test modes for when the file is run directly:

1. **Single-Screen Test (`single`)**
   - Purpose: Verify the layout and interactions of this screen only.
   - Navigation events (e.g., button presses to go to another screen) are intercepted and logged as:
     ```
     navigation to <target_screen_name>
     ```
   - The screen remains visible and does not actually navigate.
   - Data is loaded only from local stub providers relevant to this screen.

   2. **Flow Test (`flow`)**
      - Purpose: Test navigation and interactions across multiple screens with stub data.
      - Navigation works normally through a `FlowRouter` and `ScreenManager`.
      - A shared stub `AppContext` is loaded from `ui/stubs/scenarios/` so all screens in the flow share consistent fake state.
      - Example: Even if you tap "legs", the stub context may have `selected_preset="push"`, so the flow behaves predictably.

---

## 3) Running a Screen Directly
When a screen file is executed directly (`__name__ == "__main__"`):
1. The script must **prompt in the terminal**:
Type 1 for single-screen test
Type 2 for flow test


2. Based on the selection:
   - Mode 1 → Initialize `SingleRouter` and relevant stub provider(s).
   - Mode 2 → Initialize `FlowRouter`, load a scenario into `AppContext`, and build a small `ScreenManager` flow.
   3. If the user presses Enter without typing anything, default to **single** mode.

---

## 4) Separation from Backend and DB
- Do **not** import from `backend/` or `data/` in UI screens.
  - All data must come from:
  - A **data provider** (real or stub) passed into the screen.
  - Or a `test_mode`/`AppContext`-based stub source during testing.
  - Screens must not manage business logic or persistence.

---

## 5) Thin, Declarative Screens
- Keep screens focused on layout, widgets, and basic UI interactions.
  - Any data formatting or shape conversion belongs in `ui/adapters/`, not in the screen.
  - Screens should be kept under ~300 LOC; extract widgets/helpers if larger.

---

## Directory Layout

ui/
screens/ # one file per screen (with two test modes)
stubs/ # stub data providers and scenarios for test modes
adapters/ # optional: backend → UI data translators
testing/
routers/ # SingleRouter, FlowRouter
runners/ # helper functions for starting test modes
AGENTS.md

---

## State Management Rules
- UI holds only **transient view state** (e.g., selected tab, open modal).
  - All business state (e.g., workout progress, selected preset) lives outside the screen, in the data provider or `AppContext`.
  - Avoid hidden state that persists beyond the screen’s lifecycle.

---

## Visual Testing Requirements
- **Single** mode: Local stub data only, no navigation.
  - **Flow** mode: Uses `AppContext` from a stub scenario, navigation works through the router.
  - Screens must handle:
    - Empty datasets.
    - Large lists.
    - Long strings and special characters.
  - All button presses and input fields should behave correctly in both modes.

---

## Do / Don’t Summary

**Do**
- Accept `data_provider`, `router`, and `test_mode` in the screen constructor.
  - Use `ui/stubs/` for all test data.
  - Use the interactive terminal prompt to choose test mode when run directly.
  - Keep screens UI-focused and document expected data shapes.

**Don’t**
- Import backend or data modules.
  - Store business logic or DB access in screens.
  - Depend on global singletons or hidden side effects.

---

## Codex Guidance (for this folder)
- Always implement both **single** and **flow** modes in the `__main__` block of a new screen.
  - Use `SingleRouter` to log navigation in single mode, `FlowRouter` to navigate in flow mode.
  - Load all stub data and scenarios from `ui/stubs/`, never inline in the screen.
  - Keep changes localized to the screen unless explicitly updating shared routers, context, or adapters.