import sqlite3
import time
import json
from pathlib import Path

from backend.metrics import (
    get_metrics_for_exercise,
    get_metrics_for_preset,
)
from core import (
    DEFAULT_SETS_PER_EXERCISE,
    DEFAULT_REST_DURATION,
    DEFAULT_DB_PATH,
)


# Directory for persisting in-progress session state.  This lives within the
# repository's ``data`` folder so the files are part of the code base and will
# survive across app restarts.
RECOVERY_DIR = Path(__file__).resolve().parents[1] / "data"
RECOVERY_FILE_1 = RECOVERY_DIR / "session_recovery_1.json"
RECOVERY_FILE_2 = RECOVERY_DIR / "session_recovery_2.json"


class WorkoutSession:
    """In-memory representation of a workout session.

    Only minimal metadata is loaded when the session is created. Detailed
    information such as metric definitions or exercise descriptions is
    retrieved on demand via :meth:`load_exercise_details` to keep memory usage
    low on small devices.
    """

    def __init__(
        self,
        preset_name: str,
        db_path: Path = DEFAULT_DB_PATH,
        rest_duration: int = DEFAULT_REST_DURATION,
    ):
        """Load ``preset_name`` from ``db_path`` and prepare the session."""

        self.preset_name = preset_name
        self.db_path = Path(db_path)

        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
                (preset_name,),
            )
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Preset '{preset_name}' not found")
            self.preset_id = row[0]

            cursor.execute(
                """
                SELECT ps.name,
                       se.id,
                       se.exercise_name,
                       se.number_of_sets,
                       se.rest_time,
                       se.library_exercise_id
                  FROM preset_preset_sections ps
                  JOIN preset_section_exercises se
                        ON se.section_id = ps.id AND se.deleted = 0
                 WHERE ps.preset_id = ? AND ps.deleted = 0
                 ORDER BY ps.position, se.position
                """,
                (self.preset_id,),
            )
            exercises: list[dict] = []
            self.section_starts: list[int] = []
            self.section_names: list[str] = []
            exercise_sections: list[int] = []
            current_section = None
            for (
                sec_name,
                se_id,
                name,
                sets,
                rest,
                lib_ex_id,
            ) in cursor.fetchall():
                if sec_name != current_section:
                    self.section_starts.append(len(exercises))
                    self.section_names.append(sec_name)
                    current_section = sec_name
                section_index = len(self.section_starts) - 1
                exercises.append(
                    {
                        "name": name,
                        "sets": sets or DEFAULT_SETS_PER_EXERCISE,
                        "rest": rest or rest_duration,
                        "library_exercise_id": lib_ex_id,
                        "preset_section_exercise_id": se_id,
                        "exercise_description": None,
                        "metric_defs": None,
                        "section_index": section_index,
                        "section_name": sec_name,
                    }
                )
                exercise_sections.append(section_index)

            self.exercise_sections = exercise_sections

        self.preset_snapshot = exercises
        self.session_data = [
            {"exercise_info": None, "results": []} for _ in self.preset_snapshot
        ]
        self.session_metric_defs = get_metrics_for_preset(
            preset_name, db_path=self.db_path
        )

        # build storage for all exercise metrics
        # individual exercise details are added on demand, so the metric store
        # starts empty for each set and expands when details are loaded
        self.metric_store: dict[tuple[int, int], dict[str, object]] = {}
        # dedicated storage for per-set notes
        self.set_notes: dict[tuple[int, int], str] = {}
        for ex_idx, ex in enumerate(self.preset_snapshot):
            for set_idx in range(ex["sets"]):
                self.metric_store[(ex_idx, set_idx)] = {}

        # Precompute merged exercise data so screens can access it instantly
        # without repeatedly building dictionaries. Each entry contains the
        # preset details and a reference to the per-set results list.
        self._rebuild_exercises()

        self.current_exercise = 0
        self.current_set = 0
        self.start_time = time.time()
        self.end_time = None
        self.current_set_start_time = self.start_time

        initial_rest = (
            self.preset_snapshot[0]["rest"] if self.preset_snapshot else rest_duration
        )
        self.rest_duration = initial_rest
        self.last_set_time = self.start_time
        self.rest_target_time = self.last_set_time + self.rest_duration

        # store session-level metrics
        self.session_metrics: dict[str, object] = {}
        # store metrics entered prior to individual upcoming sets
        self.pending_pre_set_metrics: dict[tuple[int, int], dict[str, object]] = {}
        # track whether post-set metrics still need to be recorded
        self.awaiting_post_set_metrics: bool = False
        # track whether this session has been saved to the database
        self.saved: bool = False
        # indicates the next active screen should resume from previous start
        self.resume_from_last_start: bool = False
        # stack of skipped exercises to support undo
        self._skip_history: list[tuple[int, int, float, float, float, int]] = []
        # flag to indicate the most recent action was a skip
        self._skip_pending: bool = False

        self.save_recovery_state()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _rebuild_exercises(self) -> None:
        """Populate ``_exercises`` with preset info and result references."""

        self._exercises: list[dict] = []
        for idx, preset in enumerate(self.preset_snapshot):
            data = self.session_data[idx]
            info = data.get("exercise_info") or preset
            data["exercise_info"] = info
            self._exercises.append({**info, "results": data["results"]})

    def _ensure_session_entry(self, exercise_index: int) -> None:
        """Ensure session data exists for ``exercise_index``."""
        entry = self.session_data[exercise_index]
        if entry["exercise_info"] is None:
            entry["exercise_info"] = self.preset_snapshot[exercise_index].copy()
            # keep the cached list in sync when lazily populating
            self._exercises[exercise_index] = {
                **entry["exercise_info"],
                "results": entry["results"],
            }

    def load_exercise_details(self, index: int) -> dict:
        """Load full details for the exercise at ``index`` if needed.

        The initial preset snapshot only contains identifiers and basic
        metadata. This method fetches the description and metric definitions
        from the database on demand and updates internal stores accordingly.
        The populated exercise info dictionary is returned.
        """

        if index < 0 or index >= len(self.preset_snapshot):
            raise IndexError("Invalid exercise index")
        info = self.preset_snapshot[index]
        if (
            info.get("exercise_description") is not None
            and info.get("metric_defs") is not None
        ):
            return info
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT exercise_description FROM preset_section_exercises WHERE id = ?",
                (info.get("preset_section_exercise_id"),),
            )
            row = cursor.fetchone()
            description = row[0] if row and row[0] else ""
        metric_defs = get_metrics_for_exercise(
            info["name"], db_path=self.db_path, preset_name=self.preset_name
        )
        info["exercise_description"] = description
        info["metric_defs"] = metric_defs
        template = {m["name"]: None for m in metric_defs}
        for set_idx in range(info["sets"]):
            store = self.metric_store.setdefault((index, set_idx), {})
            for name in template:
                store.setdefault(name, None)
        self._ensure_session_entry(index)
        self.session_data[index]["exercise_info"] = info
        self._exercises[index] = {**info, "results": self.session_data[index]["results"]}
        return info

    @property
    def exercises(self) -> list[dict]:
        """Return the precomputed list of exercises."""
        return self._exercises

    def mark_set_completed(self, adjust_seconds: int = 0) -> None:
        """Record completion time and update rest timer for the next set.

        ``adjust_seconds`` allows backdating the completion timestamp by the
        specified number of seconds.  Negative values indicate the set finished
        earlier than the current clock time.
        """
        self._skip_pending = False
        self.last_set_time = time.time() + adjust_seconds
        if self.current_exercise < len(self.preset_snapshot):
            upcoming = self.preset_snapshot[self.current_exercise]
            self.rest_duration = upcoming.get("rest", self.rest_duration)
        self.rest_target_time = self.last_set_time + self.rest_duration
        self.awaiting_post_set_metrics = True
        self.save_recovery_state()

    def undo_set_start(self) -> None:
        """Revert state to before the current set began."""

        # Reset start time to when the previous set ended
        self.current_set_start_time = self.last_set_time
        # Ensure no automatic resume behaviour
        self.resume_from_last_start = False
        # No post-set metrics should be expected
        self.awaiting_post_set_metrics = False
        # Restore rest timer based on the last completed set
        self.rest_target_time = self.last_set_time + self.rest_duration
        self._skip_pending = False
        self.save_recovery_state()

    def skip_exercise(self) -> bool:
        """Skip the remaining sets of the current exercise."""

        if self.current_exercise >= len(self.preset_snapshot) - 1:
            return False

        ex_idx = self.current_exercise
        original_sets = self.preset_snapshot[ex_idx]["sets"]
        skipped_count = max(0, original_sets - self.current_set)

        state = (
            self.current_exercise,
            self.current_set,
            self.current_set_start_time,
            self.last_set_time,
            self.rest_target_time,
            self.rest_duration,
            original_sets,
            self.session_data[ex_idx].get("skipped_sets", 0),
        )
        self._skip_history.append(state)

        if skipped_count:
            self.session_data[ex_idx]["skipped_sets"] = skipped_count
            for set_idx in range(self.current_set, original_sets):
                self.metric_store.pop((ex_idx, set_idx), None)
            self.preset_snapshot[ex_idx]["sets"] = self.current_set

        self.current_exercise += 1
        self.current_set = 0
        now = time.time()
        self.current_set_start_time = now
        self.last_set_time = now
        upcoming = self.preset_snapshot[self.current_exercise]
        self.rest_duration = upcoming.get("rest", self.rest_duration)
        self.rest_target_time = now + self.rest_duration
        self.awaiting_post_set_metrics = False
        self.resume_from_last_start = False
        self.end_time = None
        self._skip_pending = True
        self.save_recovery_state()

        return True

    def last_action_was_skip(self) -> bool:
        """Return ``True`` if the most recent action was a skip."""

        return self._skip_pending

    def next_exercise_name(self):
        if self.current_exercise < len(self.preset_snapshot):
            return self.preset_snapshot[self.current_exercise]["name"]
        return ""

    def next_exercise_display(self):
        if self.current_exercise < len(self.preset_snapshot):
            ex = self.preset_snapshot[self.current_exercise]
            return f"{ex['name']} set {self.current_set + 1} of {ex['sets']}"
        return ""

    def upcoming_exercise_name(self):
        """Return the exercise name for the next set to be performed."""
        if self.current_exercise >= len(self.preset_snapshot):
            return ""
        ex_idx = self.current_exercise
        set_idx = self.current_set + 1
        if set_idx >= self.preset_snapshot[ex_idx]["sets"]:
            ex_idx += 1
            set_idx = 0
        if ex_idx < len(self.preset_snapshot):
            return self.preset_snapshot[ex_idx]["name"]
        return ""

    def upcoming_exercise_display(self):
        """Return display string for the next set to be performed."""
        if self.current_exercise >= len(self.preset_snapshot):
            return ""
        ex_idx = self.current_exercise
        set_idx = self.current_set + 1
        if set_idx >= self.preset_snapshot[ex_idx]["sets"]:
            ex_idx += 1
            set_idx = 0
        if ex_idx < len(self.preset_snapshot):
            ex = self.preset_snapshot[ex_idx]
            return f"{ex['name']} set {set_idx + 1} of {ex['sets']}"
        return ""

    def last_recorded_set_metrics(self) -> dict:
        """Return metrics from the most recently completed set.

        If no sets have been completed yet, an empty dict is returned.
        """

        for idx in range(self.current_exercise, -1, -1):
            data = self.session_data[idx]
            if data["results"]:
                return data["results"][-1]["metrics"]
        return {}

    # --------------------------------------------------------------
    # Time metric helpers
    # --------------------------------------------------------------

    def get_set_duration(self, exercise_index: int, set_index: int) -> float | None:
        """Return the duration of the specified set in seconds."""

        if (
            self.awaiting_post_set_metrics
            and exercise_index == self.current_exercise
            and set_index == self.current_set
        ):
            return self.last_set_time - self.current_set_start_time

        self._ensure_session_entry(exercise_index)
        results = self.session_data[exercise_index]["results"]
        if set_index < len(results) and results[set_index]:
            start = results[set_index].get("started_at")
            end = results[set_index].get("ended_at")
            if start is not None and end is not None:
                return end - start
        return None

    def update_set_duration(
        self, exercise_index: int, set_index: int, duration: float
    ) -> None:
        """Adjust end time for the specified set without changing start time."""

        if (
            self.awaiting_post_set_metrics
            and exercise_index == self.current_exercise
            and set_index == self.current_set
        ):
            self.last_set_time = self.current_set_start_time + duration
            self.rest_target_time = self.last_set_time + self.rest_duration
            return

        self._ensure_session_entry(exercise_index)
        results = self.session_data[exercise_index]["results"]
        if set_index < len(results) and results[set_index]:
            start = results[set_index].get("started_at")
            if start is not None:
                results[set_index]["ended_at"] = start + duration

    # --------------------------------------------------------------
    # Pre-set metric helpers
    # --------------------------------------------------------------

    def required_pre_set_metric_names(self) -> list[str]:
        """Return names of required pre-set metrics for the next set.

        Exercise details are loaded lazily; ensure the current exercise has
        its definitions populated before evaluating requirements.
        """

        if self.current_exercise >= len(self.preset_snapshot):
            return []
        self.load_exercise_details(self.current_exercise)
        metric_defs = (
            self.preset_snapshot[self.current_exercise].get("metric_defs") or []
        )
        return [
            m["name"]
            for m in metric_defs
            if m.get("input_timing") == "pre_set" and m.get("is_required")
        ]

    def has_required_pre_set_metrics(self) -> bool:
        """Return ``True`` if all required pre-set metrics have been entered."""

        required = self.required_pre_set_metric_names()
        store = self.metric_store.get((self.current_exercise, self.current_set), {})
        return all(store.get(name) not in (None, "") for name in required)

    def tempo_for_set(self, exercise_index: int, set_index: int) -> str | None:
        """Return a 4-digit tempo string for the specified set, if present."""

        if exercise_index >= len(self.preset_snapshot):
            return None
        self.load_exercise_details(exercise_index)
        metric_defs = (
            self.preset_snapshot[exercise_index].get("metric_defs") or []
        )
        tempo_name = next(
            (
                m["name"]
                for m in metric_defs
                if m.get("library_metric_type_id") == 3
            ),
            None,
        )
        if not tempo_name:
            return None
        value = self.metric_store.get((exercise_index, set_index), {}).get(tempo_name)
        if value is None:
            return None
        tempo = str(value)
        if tempo.isdigit() and len(tempo) == 4:
            return tempo
        return None

    # --------------------------------------------------------------
    # Post-set metric helpers
    # --------------------------------------------------------------

    def required_post_set_metric_names(self) -> list[str]:
        """Return names of required post-set metrics for the last set."""

        if self.current_exercise >= len(self.preset_snapshot):
            ex_idx = len(self.preset_snapshot) - 1
        else:
            ex_idx = self.current_exercise
        if ex_idx < 0:
            return []
        self.load_exercise_details(ex_idx)
        metric_defs = self.preset_snapshot[ex_idx].get("metric_defs") or []
        return [
            m["name"]
            for m in metric_defs
            if m.get("input_timing") == "post_set" and m.get("is_required")
        ]

    def has_required_post_set_metrics(self) -> bool:
        """Return ``True`` if any required post-set metrics have been recorded."""

        if not self.awaiting_post_set_metrics:
            return True
        required = self.required_post_set_metric_names()
        return len(required) == 0

    def set_pre_set_metrics(
        self,
        metrics: dict,
        exercise_index: int | None = None,
        set_index: int | None = None,
    ) -> None:
        """Store metrics to be applied to a specific upcoming set."""

        ex = self.current_exercise if exercise_index is None else exercise_index
        st = self.current_set if set_index is None else set_index
        self.load_exercise_details(ex)
        store = self.metric_store.get((ex, st))
        if store is None:
            return
        pending = self.pending_pre_set_metrics.setdefault((ex, st), {})
        for name, value in metrics.items():
            if name not in store:
                raise KeyError(f"Unknown metric '{name}' for exercise {ex}")
            store[name] = value
            pending[name] = value
        self.save_recovery_state()

    def get_set_notes(self, ex_idx: int, set_idx: int) -> str:
        """Return stored notes for the specified set."""

        if 0 <= ex_idx < len(self.session_data):
            results = self.session_data[ex_idx]["results"]
            if 0 <= set_idx < len(results) and results[set_idx]:
                return results[set_idx].get("notes", "")
        return self.set_notes.get((ex_idx, set_idx), "")

    def set_set_notes(self, ex_idx: int, set_idx: int, text: str) -> None:
        """Store notes for the specified set."""

        key = (ex_idx, set_idx)
        self.set_notes[key] = text
        if 0 <= ex_idx < len(self.session_data):
            results = self.session_data[ex_idx]["results"]
            if 0 <= set_idx < len(results) and results[set_idx]:
                results[set_idx]["notes"] = text
        self.save_recovery_state()

    def set_session_metrics(self, metrics: dict) -> None:
        """Store metrics that apply to the entire session."""

        self.session_metrics = metrics.copy()
        self.save_recovery_state()

    def record_metrics(self, exercise_index: int, set_index: int, metrics):
        if exercise_index >= len(self.preset_snapshot):
            if self.end_time is None:
                self.end_time = time.time()
            self.save_recovery_state()
            return True

        self.load_exercise_details(exercise_index)
        key = (exercise_index, set_index)
        store = self.metric_store.get(key)
        if store is None:
            raise IndexError("Invalid exercise/set index")
        combined = {**self.pending_pre_set_metrics.pop(key, {}), **metrics}
        notes = self.set_notes.get(key, "")

        for name, value in combined.items():
            if name not in store:
                raise KeyError(
                    f"Unknown metric '{name}' for exercise {exercise_index}"
                )
            store[name] = value

        if (
            self.awaiting_post_set_metrics
            and exercise_index == self.current_exercise
            and set_index == self.current_set
        ):
            end_time = self.last_set_time
        else:
            end_time = time.time()

        self._ensure_session_entry(exercise_index)
        results = self.session_data[exercise_index]["results"]
        while len(results) <= set_index:
            results.append(None)
        start_time = (
            self.current_set_start_time
            if exercise_index == self.current_exercise and set_index == self.current_set
            else results[set_index]["started_at"]
            if set_index < len(results) and results[set_index]
            else end_time
        )
        results[set_index] = {
            "metrics": store.copy(),
            "started_at": start_time,
            "ended_at": end_time,
            "notes": notes,
        }
        self.set_notes[key] = notes
        if exercise_index == self.current_exercise and set_index == self.current_set:
            self.current_set_start_time = end_time
            self.current_set += 1
            self.awaiting_post_set_metrics = False

            if self.current_set >= self.preset_snapshot[exercise_index]["sets"]:
                self.current_set = 0
                self.current_exercise += 1

            if self.current_exercise >= len(self.preset_snapshot):
                self.end_time = end_time
                self.save_recovery_state()
                return True

        self.save_recovery_state()
        return False

    def edit_set_metrics(self, exercise_index: int, set_index: int, metrics: dict) -> None:
        """Update metrics for a previously completed set."""

        self._ensure_session_entry(exercise_index)
        if set_index >= len(self.session_data[exercise_index]["results"]):
            raise IndexError("Set not completed")
        key = (exercise_index, set_index)
        store = self.metric_store.get(key)
        if store is None:
            raise IndexError("Invalid exercise/set index")
        for name, value in metrics.items():
            if name not in store:
                raise KeyError(
                    f"Unknown metric '{name}' for exercise {exercise_index}"
                )
            store[name] = value
        self.session_data[exercise_index]["results"][set_index]["metrics"] = store.copy()
        self.save_recovery_state()

    def undo_last_set(self) -> bool:
        """Reopen the most recently completed set.

        Returns ``True`` if a set was restored, ``False`` otherwise.
        """
        if self._skip_history:
            (
                self.current_exercise,
                self.current_set,
                self.current_set_start_time,
                self.last_set_time,
                self.rest_target_time,
                self.rest_duration,
                original_sets,
                prev_skipped,
            ) = self._skip_history.pop()
            self.preset_snapshot[self.current_exercise]["sets"] = original_sets
            data = self.session_data[self.current_exercise]
            if prev_skipped:
                data["skipped_sets"] = prev_skipped
            else:
                data.pop("skipped_sets", None)
            template = {
                m["name"]: None
                for m in (
                    self.preset_snapshot[self.current_exercise].get("metric_defs")
                    or []
                )
            }
            for set_idx in range(self.current_set, original_sets):
                self.metric_store[(self.current_exercise, set_idx)] = template.copy()
            self.awaiting_post_set_metrics = False
            # Undoing a skipped exercise should return to the rest state
            # without resuming an active set.
            self.resume_from_last_start = False
            self._skip_pending = False
            self.end_time = None
            self.save_recovery_state()
            return True

        # Determine whether any set has been completed yet
        if (
            self.current_exercise == 0
            and self.current_set == 0
            and not self.session_data[0]["results"]
        ):
            return False

        # Identify exercise and set index of last completed set
        ex_idx = self.current_exercise
        set_idx = self.current_set - 1
        if set_idx < 0:
            ex_idx -= 1
            if ex_idx < 0:
                return False
            set_idx = len(self.session_data[ex_idx]["results"]) - 1
        data = self.session_data[ex_idx]
        if not data["results"]:
            return False
        last = data["results"].pop()
        self.set_notes.pop((ex_idx, set_idx), None)

        # Restore indices to point at the reopened set
        self.current_exercise = ex_idx
        self.current_set = set_idx

        # Preserve any previously entered metrics for the set
        self.pending_pre_set_metrics[(ex_idx, set_idx)] = {
            k: v
            for k, v in self.metric_store.get((ex_idx, set_idx), {}).items()
            if v not in (None, "")
        }
        self.awaiting_post_set_metrics = False

        # Resume timer from the original start time
        self.current_set_start_time = last.get("started_at", time.time())
        self.last_set_time = self.current_set_start_time
        self.rest_target_time = self.last_set_time + self.rest_duration

        # Ensure workout isn't marked finished
        self.end_time = None

        # Flag for WorkoutActiveScreen to resume from stored start time
        self.resume_from_last_start = True

        self.save_recovery_state()
        return True

    def has_started_exercise(self, exercise_index: int) -> bool:
        """Return True if the exercise at ``exercise_index`` has begun."""
        if exercise_index < 0 or exercise_index >= len(self.preset_snapshot):
            return False
        if self.session_data[exercise_index]["results"]:
            return True
        if exercise_index < self.current_exercise:
            return True
        if exercise_index == self.current_exercise and self.current_set > 0:
            return True
        return False

    def is_editable_section(self, section_index: int) -> bool:
        """Return True if no exercises in the section have started."""
        if section_index < 0 or section_index >= len(self.section_starts):
            return False
        start = self.section_starts[section_index]
        end = (
            self.section_starts[section_index + 1]
            if section_index + 1 < len(self.section_starts)
            else len(self.preset_snapshot)
        )
        for idx in range(start, end):
            if self.has_started_exercise(idx):
                return False
        return True

    def apply_edited_preset(self, sections: list[dict]) -> None:
        """Merge edited ``sections`` back into the active session."""

        # Map existing exercises by their preset_section_exercise_id to
        # preserve recorded results when possible.
        existing_index: dict[object, int] = {}
        for idx, ex in enumerate(self.preset_snapshot):
            ex_id = ex.get("preset_section_exercise_id")
            if ex_id is not None:
                existing_index[ex_id] = idx

        new_preset: list[dict] = []
        new_session_data: list[dict] = []
        new_metric_store: dict[tuple[int, int], dict[str, object]] = {}
        new_set_notes: dict[tuple[int, int], str] = {}
        section_starts: list[int] = []
        section_names: list[str] = []
        exercise_sections: list[int] = []

        new_ex_idx = 0
        for sec_idx, sec in enumerate(sections):
            section_starts.append(len(new_preset))
            sec_name = sec.get("name", f"Section {sec_idx + 1}")
            section_names.append(sec_name)
            for ex in sec.get("exercises", []):
                ex_name = ex.get("name", "")
                ex_sets = ex.get("sets", DEFAULT_SETS_PER_EXERCISE)
                ex_rest = ex.get("rest", self.rest_duration)
                ex_lib_id = ex.get("library_id") or ex.get("library_exercise_id")
                ex_id = ex.get("id") or ex.get("preset_section_exercise_id")
                ex_copy = {
                    "name": ex_name,
                    "sets": ex_sets,
                    "rest": ex_rest,
                    "library_exercise_id": ex_lib_id,
                    "preset_section_exercise_id": ex_id,
                    "exercise_description": ex.get("exercise_description"),
                    "metric_defs": None,
                    "section_index": sec_idx,
                    "section_name": sec_name,
                }
                new_preset.append(ex_copy)
                exercise_sections.append(sec_idx)

                if ex_id in existing_index:
                    old_idx = existing_index[ex_id]
                    data = self.session_data[old_idx]
                    results = data.get("results", [])[:ex_sets]
                    new_session_data.append(
                        {"exercise_info": data.get("exercise_info"), "results": results}
                    )
                    for set_idx in range(ex_sets):
                        key_old = (old_idx, set_idx)
                        key_new = (new_ex_idx, set_idx)
                        if key_old in self.metric_store:
                            new_metric_store[key_new] = self.metric_store[key_old].copy()
                        else:
                            new_metric_store[key_new] = {}
                        if key_old in self.set_notes:
                            new_set_notes[key_new] = self.set_notes[key_old]
                else:
                    new_session_data.append({"exercise_info": None, "results": []})
                    for set_idx in range(ex_sets):
                        new_metric_store[(new_ex_idx, set_idx)] = {}

                new_ex_idx += 1

        self.preset_snapshot = new_preset
        self.session_data = new_session_data
        self.metric_store = new_metric_store
        self.set_notes = new_set_notes
        self.section_starts = section_starts
        self.section_names = section_names
        self.exercise_sections = exercise_sections

        # Refresh cached exercise list to include edited preset structure
        self._rebuild_exercises()
        # Ensure metric definitions are available for the updated preset so
        # callers see a consistent view after editing
        for idx in range(len(self.preset_snapshot)):
            self.load_exercise_details(idx)

        # Ensure current indices remain within bounds
        if self.current_exercise >= len(self.preset_snapshot):
            self.current_exercise = max(0, len(self.preset_snapshot) - 1)
            self.current_set = 0
        else:
            max_sets = self.preset_snapshot[self.current_exercise].get("sets", 0)
            if self.current_set >= max_sets:
                self.current_set = 0
        self.save_recovery_state()

    def adjust_rest_timer(self, seconds: int) -> None:
        """Adjust the target time for the current rest period."""
        now = time.time()
        if self.rest_target_time <= now:
            self.rest_target_time = now
        self.rest_target_time += seconds
        if self.rest_target_time <= now:
            self.rest_target_time = now
        self.save_recovery_state()

    def rest_remaining(self) -> float:
        """Return seconds remaining in the current rest period."""
        return max(0.0, self.rest_target_time - time.time())

    def summary(self) -> str:
        """Return a formatted text summary of the session."""

        end_time = self.end_time or time.time()
        lines = [f"Workout: {self.preset_name}"]
        start = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time))
        end = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(end_time))
        dur = int(end_time - self.start_time)
        m, s = divmod(dur, 60)
        lines.append(f"Start: {start}")
        lines.append(f"End:   {end}")
        lines.append(f"Duration: {m}m {s}s")
        for ex in self.exercises:
            lines.append(f"\n{ex['name']}")
            for idx, result in enumerate(ex["results"], 1):
                metrics_text = ", ".join(
                    f"{k}: {v}" for k, v in result["metrics"].items()
                )
                lines.append(f"  Set {idx}: {metrics_text}")
        return "\n".join(lines)

    # --------------------------------------------------------------
    # Persistence helpers
    # --------------------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable representation of the session."""

        return {
            "preset_name": self.preset_name,
            "db_path": str(self.db_path),
            "preset_id": self.preset_id,
            "preset_snapshot": self.preset_snapshot,
            "session_data": self.session_data,
            "session_metric_defs": self.session_metric_defs,
            "metric_store": {
                f"{k[0]},{k[1]}": v for k, v in self.metric_store.items()
            },
            "set_notes": {f"{k[0]},{k[1]}": v for k, v in self.set_notes.items()},
            "current_exercise": self.current_exercise,
            "current_set": self.current_set,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "current_set_start_time": self.current_set_start_time,
            "rest_duration": self.rest_duration,
            "last_set_time": self.last_set_time,
            "rest_target_time": self.rest_target_time,
            "session_metrics": self.session_metrics,
            "pending_pre_set_metrics": {
                f"{k[0]},{k[1]}": v
                for k, v in self.pending_pre_set_metrics.items()
            },
            "awaiting_post_set_metrics": self.awaiting_post_set_metrics,
            "saved": self.saved,
            "resume_from_last_start": self.resume_from_last_start,
            "_skip_history": self._skip_history,
            "_skip_pending": self._skip_pending,
            "section_starts": self.section_starts,
            "section_names": self.section_names,
            "exercise_sections": self.exercise_sections,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkoutSession":
        """Reconstruct a :class:`WorkoutSession` from ``data``."""

        obj = cls.__new__(cls)
        obj.preset_name = data["preset_name"]
        obj.db_path = Path(data["db_path"])
        obj.preset_id = data["preset_id"]
        obj.preset_snapshot = data["preset_snapshot"]
        obj.session_data = data["session_data"]
        obj.session_metric_defs = data.get("session_metric_defs", [])
        obj.metric_store = {
            tuple(map(int, k.split(","))): v
            for k, v in data.get("metric_store", {}).items()
        }
        obj.set_notes = {
            tuple(map(int, k.split(","))): v
            for k, v in data.get("set_notes", {}).items()
        }
        obj.current_exercise = data["current_exercise"]
        obj.current_set = data["current_set"]
        obj.start_time = data["start_time"]
        obj.end_time = data["end_time"]
        obj.current_set_start_time = data["current_set_start_time"]
        obj.rest_duration = data["rest_duration"]
        obj.last_set_time = data["last_set_time"]
        obj.rest_target_time = data["rest_target_time"]
        obj.session_metrics = data.get("session_metrics", {})
        obj.pending_pre_set_metrics = {
            tuple(map(int, k.split(","))): v
            for k, v in data.get("pending_pre_set_metrics", {}).items()
        }
        obj.awaiting_post_set_metrics = data.get("awaiting_post_set_metrics", False)
        obj.saved = data.get("saved", False)
        obj.resume_from_last_start = data.get("resume_from_last_start", False)
        obj._skip_history = [tuple(item) for item in data.get("_skip_history", [])]
        obj._skip_pending = data.get("_skip_pending", False)
        obj.section_starts = data.get("section_starts", [])
        obj.section_names = data.get("section_names", [])
        obj.exercise_sections = data.get("exercise_sections", [])
        obj._rebuild_exercises()
        return obj

    def save_recovery_state(self) -> None:
        """Persist the current session state to recovery files."""

        payload = json.dumps(self.to_dict())
        try:
            RECOVERY_DIR.mkdir(parents=True, exist_ok=True)
            RECOVERY_FILE_1.write_text(payload)
            RECOVERY_FILE_2.write_text(payload)
        except Exception:
            pass

    @staticmethod
    def clear_recovery_files() -> None:
        """Remove any existing recovery files."""

        for path in (RECOVERY_FILE_1, RECOVERY_FILE_2):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    @classmethod
    def load_from_recovery(cls) -> "WorkoutSession | None":
        """Return a recovered session if available."""

        for path in (RECOVERY_FILE_1, RECOVERY_FILE_2):
            try:
                if not path.exists():
                    continue
                text = path.read_text().strip()
                if not text:
                    continue
                data = json.loads(text)
                return cls.from_dict(data)
            except Exception:
                continue
        return None

    def is_set_active(self) -> bool:
        """Return ``True`` if a set is currently in progress."""

        return (
            not self.awaiting_post_set_metrics
            and self.current_set_start_time > self.last_set_time
            and self.current_exercise < len(self.preset_snapshot)
        )

