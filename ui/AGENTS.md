
markdown
Edit
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
- Direct runs must launch a minimal preview using only stub data.

### 2) Test Mode
- **Every screen class must have a `test_mode` flag** (or equivalent stub-data injection) in its constructor.
- When `test_mode=True`:
  - All data must come from `ui/stubs/`.
  - No backend or DB calls are allowed.
  - The screen must still be fully functional for navigation and visual testing.
- This mode is the default when running the file directly.

### 3) Separation from Backend and DB
- Do **not** import from `backend/` or `data/` in UI screens.
- All data comes from an injected `data_provider` or adapter interface.
- Screens must not own or manage business logic or persistence.

### 4) Thin, Declarative Screens
- Screens focus on layout, widgets, and UI-level interactions.
- Data formatting/translation happens in `ui/adapters/`, not inside screens.
- Large screens (>300 LOC) should extract reusable widgets/helpers.

---

## Directory Layout

ui/
screens/ # one file per screen (with test mode)
stubs/ # stub data providers for previews
adapters/ # optional: backend → UI data translation
runners/ # multi-screen flow previews
AGENTS.md

---

## State Management Rules
- UI holds only **transient view state** (e.g., selected tab, scroll position).
- All business state (e.g., workout progress) lives outside and is accessed via the `data_provider` or callbacks.
- Avoid hidden state that persists beyond the screen’s lifecycle.

---

## Visual Testing Requirements
When running a screen file directly:
- Use `test_mode=True` and load only from stubs.
- Render without errors.
- Display correctly for small, large, and edge-case data.
- Handle empty data gracefully.
- All buttons and inputs must still function with stub callbacks (even if they just log to console).

---

## Do / Don’t Summary

**Do**
- Accept `data_provider` and `test_mode` in constructor.
- Always provide a runnable preview using `ui/stubs/`.
- Keep screens UI-focused and under ~300 LOC when possible.
- Document expected input/output shapes at the top of the file.

**Don’t**
- Import backend or data modules.
- Store business logic or DB access in screens.
- Depend on global singletons or hidden side effects.

---

## Codex Guidance (for this folder)
- Always implement `test_mode` logic when creating a new screen.
- Stub data lives in `ui/stubs/`, never in the screen file.
- If more data is needed, update the `data_provider` interface and stub provider first.
- Keep changes localized to a single screen unless asked to update shared widgets or adapters.