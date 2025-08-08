# Codex Mistakes Log

This file documents recurring mistakes or quirks that happen when using Codex/ChatGPT to generate code for this project (`workout_app`). It helps prevent repeated bugs — especially visual/UI errors that are easy to miss in code but obvious during app testing.

Every entry includes:
- **Context** – Where the issue appeared (e.g., screen, widget, function)
- **Mistake** – What Codex/ChatGPT did wrong
- **Problem** – What went wrong when the code was run
- **Fix** – How the issue was resolved
- **Lesson** – How to avoid it next time (prompting tips or implementation rules)

---

Add new entries below as issues are encountered. Over time this becomes a reference to improve prompting and code reviews when using Codex/ChatGPT.

### Missing titles for custom tabs

- **Context** – `PresetOverviewScreen` tabs `DetailsTab` and `WorkoutTab`
- **Mistake** – Tabs were generated without titles or icons
- **Problem** – App crashed with `ValueError: No valid Icon was found. No valid Title was found.`
- **Fix** – Added titles for `DetailsTab` and `WorkoutTab` in `main.kv`
- **Lesson** – Always specify a title or icon for each KivyMD tab to satisfy initialization requirements

### MDFlatButton width calculation crash

- **Context** – MetricInputScreen filter buttons in `main.kv`
- **Mistake** – Used `self.texture_size` to set button width even though `MDFlatButton` lacks this attribute
- **Problem** – App raised `AttributeError: 'MDFlatButton' object has no attribute 'texture_size'`
- **Fix** – Removed dependency on `texture_size` and assigned fixed widths using `dp(110)`
- **Lesson** – MDFlatButton doesn't expose `texture_size`; prefer fixed dimensions or other sizing methods

### Incorrect MDIcon import path

- **Context** – `EditExerciseScreen`
- **Mistake** – Imported `MDIcon` from `kivymd.uix.icon`, which doesn't exist in KivyMD 1.x
- **Problem** – App crashed with `ModuleNotFoundError: No module named 'kivymd.uix.icon'`
- **Fix** – Import `MDIcon` from `kivymd.uix.label`
- **Lesson** – In KivyMD 1.x, use `kivymd.uix.label.MDIcon`; `kivymd.uix.icon` only exists in KivyMD 2.x
