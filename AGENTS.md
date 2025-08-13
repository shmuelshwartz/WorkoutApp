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

