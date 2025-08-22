# AGENTS

## Purpose

This document guides contributors on the design and implementation
constraints for this project. The target device is a low-spec phone with a
very small screen and limited memory, so every decision must respect these
constraints.

## 1. Screen Size Constraints

The app will run on devices with small display sizes (both in resolution
and physical size). All UI components must:

- Be compact yet clear and legible.
- Avoid unnecessary padding and large empty spaces.
- Use scrollable layouts when content cannot fit.
- Group related widgets into collapsible sections where possible.
- Minimize modal popups that require extra navigation—prefer in-place
  updates.
- Prioritize touch-friendly hit areas despite limited space (avoid tiny
  buttons).

**Design goal:** Maximum information density without overwhelming the user.

## 2. Memory Usage Constraints

The target device has limited RAM, so:

- Avoid loading unnecessary assets (images, fonts, data) until needed.
- Prefer lazy loading for heavy content.
- Reuse widgets where possible instead of recreating them.
- Clear references to unused objects to allow garbage collection.
- Avoid large in-memory data structures—store to SQLite when not actively
  in use.
- Keep animations minimal to reduce CPU/GPU load.

**Performance goal:** Fast and responsive app with minimal memory
footprint.

## 3. Developer Guidelines

When adding new code:

- Always ask: *Can this be smaller, lighter, or faster?*
- Test layouts on the smallest screen size we target.
- Profile memory usage when adding new features.
- Prioritize offline efficiency over visual complexity.
- Keep Kivy widget trees shallow where possible.
- Use vector assets or lightweight PNGs (no unnecessary large images).
- Avoid deep widget nesting unless absolutely necessary.

## 4. Summary

This app is for small-screen, low-memory devices. Every decision in UI,
memory usage, and architecture must respect this. If in doubt:

- Simplify the UI.
- Reduce memory usage.
- Test on the lowest-end device you have.


## Tiny-screen additions

Files touched: `tiny_screen.py`, `tiny_overlay.py`, `tiny_dialog.py`, `tiny_perf.py`, `devtool/scrollview_example.py`, `main.py`, `main.kv`, `ui/screens/general/home_screen.py`, `ui/popups.py`.

New flags: `TINY_FORCE_DENSITY`, `TINY_FONT_SCALE`, `TINY_DEVICE_PROFILE`, `TINY_COMPACT_OVERRIDE`, `TINY_OVERLAY`, `TINY_PERF`.

Revert with:
```
git restore tiny_screen.py tiny_overlay.py tiny_dialog.py tiny_perf.py devtool/scrollview_example.py main.py main.kv ui/screens/general/home_screen.py ui/popups.py
```

Exemplar integrations: font scaling in `main.kv`, safe-area padding in `HomeScreen`, dialog safety via `EditMetricPopup`.

### Tiny-Screen Dev Mode

The global compact rule triggers when the **smallest-width (sw)** is
`min(Window.width, Window.height) / Metrics.density <= 360dp`. The helper
`tiny_screen.bind_window()` updates `tiny_screen.IS_COMPACT` as the window
resizes.

#### Environment Flags

Set these before launching the app to emulate different devices:

- `TINY_FORCE_DENSITY` – float to override density/DPI.
- `TINY_FONT_SCALE` – multiplier for text sizes (1.0–1.3).
- `TINY_DEVICE_PROFILE` – path to JSON file
  `{"density":1.5,"fontscale":1.2,"safe_area":{"top":24,"bottom":24}}`.
- `TINY_COMPACT_OVERRIDE` – `0`/`1`/`auto` to force compact mode.
- `TINY_OVERLAY` – `1` to show the metrics overlay on start.
- `TINY_PERF` – `1` to enable performance logging.

#### Device Profiles

Store JSON profiles (e.g. `data/device_profiles/compact_phone.json`) with
keys `density`, `fontscale`, and `safe_area` (`top`, `bottom`). These are read
by `tiny_screen.apply_env_overrides()` before Kivy metrics are used.

#### Metrics Overlay

Toggle with `Ctrl+O` or start with `TINY_OVERLAY=1`. The overlay displays
window size, density, dp/sp pixel conversions, smallest-width, font scale and
safe-area insets.

#### Compact Mode

Other screens may check `tiny_screen.IS_COMPACT` to swap layouts (e.g.
icon-only buttons or reduced padding). This supplements existing behaviors
such as vertical button bars under 400dp.

#### Safe Area and Font Scale

`tiny_screen.apply_safe_area_padding(widget, top=True, bottom=True)` pads a
widget by the active safe-area values. `tiny_screen.scaled_sp(value)` applies
the font-scale multiplier before calling `sp`.

#### Performance Logging

Enable `TINY_PERF=1` to log first-frame time and screen switch durations with
the `TINY-PERF:` prefix.

#### ScrollView Pattern

See `devtool/scrollview_example.py` for the correct `ScrollView` pattern:
`ScrollView -> child(size_hint_y=None, height=<bind minimum_height>)`.

#### Quick Test Matrix

- Portrait ~320dp with font scale `1.0`, `1.2`, `1.3`
- Keyboard shown/hidden
- One dialog exceeding viewport
- One long list using `ScrollView`

Ensure no content is clipped and tap targets remain 40–48dp.

#### Compatibility Notes

`half_screen` and `HalfScreenWrapper` remain unchanged and can be combined
with the above environment flags. Existing behaviors like vertical button bars
under 400dp remain active; `IS_COMPACT` simply provides an additional global
check.
