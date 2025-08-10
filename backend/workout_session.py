import sqlite3
import time
from pathlib import Path

from core import (
    DEFAULT_DB_PATH,
    DEFAULT_REST_DURATION,
    DEFAULT_SETS_PER_EXERCISE,
    get_metrics_for_exercise,
    get_metrics_for_preset,
)


class WorkoutSession:
    """In-memory representation of a workout session.

    The entire preset is fetched from the database when the session is
    created.  Once initialized all workout progress is kept purely in
    memory and the database is not accessed again.  Future versions may
    consult the database when adding unplanned exercises, but that
    functionality is not yet implemented.
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
                       se.library_exercise_id,
                       se.exercise_description
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
                    desc,
            ) in cursor.fetchall():
                if sec_name != current_section:
                    self.section_starts.append(len(exercises))
                    self.section_names.append(sec_name)
                    current_section = sec_name
                section_index = len(self.section_starts) - 1
                metric_defs = get_metrics_for_exercise(
                    name,
                    db_path=self.db_path,
                    preset_name=preset_name,
                )
                exercises.append(
                    {
                        "name": name,
                        "sets": sets or DEFAULT_SETS_PER_EXERCISE,
                        "rest": rest or rest_duration,
                        "results": [],
                        "library_exercise_id": lib_ex_id,
                        "preset_section_exercise_id": se_id,
                        "exercise_description": desc or "",
                        "metric_defs": metric_defs,
                        "section_index": section_index,
                        "section_name": sec_name,
                    }
                )
                exercise_sections.append(section_index)

            self.exercise_sections = exercise_sections

        self.exercises = exercises
        self.session_metric_defs = get_metrics_for_preset(
            preset_name, db_path=self.db_path
        )

        # build storage for all exercise metrics
        self.metric_store: dict[tuple[int, int], dict[str, object]] = {}
        for ex_idx, ex in enumerate(self.exercises):
            template = {m["name"]: None for m in ex.get("metric_defs", [])}
            for set_idx in range(ex["sets"]):
                self.metric_store[(ex_idx, set_idx)] = template.copy()

        self.current_exercise = 0
        self.current_set = 0
        self.start_time = time.time()
        self.end_time = None
        self.current_set_start_time = self.start_time

        initial_rest = (
            self.exercises[0]["rest"] if self.exercises else rest_duration
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

    def mark_set_completed(self, adjust_seconds: int = 0) -> None:
        """Record completion time and update rest timer for the next set.

        ``adjust_seconds`` allows backdating the completion timestamp by the
        specified number of seconds.  Negative values indicate the set finished
        earlier than the current clock time.
        """
        self.last_set_time = time.time() + adjust_seconds
        if self.current_exercise < len(self.exercises):
            upcoming = self.exercises[self.current_exercise]
            self.rest_duration = upcoming.get("rest", self.rest_duration)
        self.rest_target_time = self.last_set_time + self.rest_duration
        self.awaiting_post_set_metrics = True

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

    def next_exercise_name(self):
        if self.current_exercise < len(self.exercises):
            return self.exercises[self.current_exercise]["name"]
        return ""

    def next_exercise_display(self):
        if self.current_exercise < len(self.exercises):
            ex = self.exercises[self.current_exercise]
            return f"{ex['name']} set {self.current_set + 1} of {ex['sets']}"
        return ""

    def upcoming_exercise_name(self):
        """Return the exercise name for the next set to be performed."""
        if self.current_exercise >= len(self.exercises):
            return ""
        ex_idx = self.current_exercise
        set_idx = self.current_set + 1
        if set_idx >= self.exercises[ex_idx]["sets"]:
            ex_idx += 1
            set_idx = 0
        if ex_idx < len(self.exercises):
            return self.exercises[ex_idx]["name"]
        return ""

    def upcoming_exercise_display(self):
        """Return display string for the next set to be performed."""
        if self.current_exercise >= len(self.exercises):
            return ""
        ex_idx = self.current_exercise
        set_idx = self.current_set + 1
        if set_idx >= self.exercises[ex_idx]["sets"]:
            ex_idx += 1
            set_idx = 0
        if ex_idx < len(self.exercises):
            ex = self.exercises[ex_idx]
            return f"{ex['name']} set {set_idx + 1} of {ex['sets']}"
        return ""

    def last_recorded_set_metrics(self) -> dict:
        """Return metrics from the most recently completed set.

        If no sets have been completed yet, an empty dict is returned.
        """

        for ex in reversed(self.exercises[: self.current_exercise + 1]):
            if ex["results"]:
                return ex["results"][-1]["metrics"]
        return {}

    # --------------------------------------------------------------
    # Pre-set metric helpers
    # --------------------------------------------------------------

    def required_pre_set_metric_names(self) -> list[str]:
        """Return names of required pre-set metrics for the next set."""

        metrics = get_metrics_for_exercise(
            self.next_exercise_name(),
            db_path=self.db_path,
            preset_name=self.preset_name,
        )
        return [
            m["name"]
            for m in metrics
            if m.get("input_timing") == "pre_set" and m.get("is_required")
        ]

    def has_required_pre_set_metrics(self) -> bool:
        """Return ``True`` if all required pre-set metrics have been entered."""

        required = self.required_pre_set_metric_names()
        store = self.metric_store.get((self.current_exercise, self.current_set), {})
        return all(store.get(name) not in (None, "") for name in required)

    # --------------------------------------------------------------
    # Post-set metric helpers
    # --------------------------------------------------------------

    def required_post_set_metric_names(self) -> list[str]:
        """Return names of required post-set metrics for the last set."""

        if self.current_exercise >= len(self.exercises):
            ex_idx = len(self.exercises) - 1
        else:
            ex_idx = self.current_exercise
        if ex_idx < 0:
            return []
        ex_name = self.exercises[ex_idx]["name"]
        metrics = get_metrics_for_exercise(
            ex_name,
            db_path=self.db_path,
            preset_name=self.preset_name,
        )
        return [
            m["name"]
            for m in metrics
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
        store = self.metric_store.get((ex, st))
        if store is None:
            return
        pending = self.pending_pre_set_metrics.setdefault((ex, st), {})
        for name, value in metrics.items():
            if name == "Notes":
                pending["Notes"] = value
                continue
            if name not in store:
                raise KeyError(f"Unknown metric '{name}' for exercise {ex}")
            store[name] = value
            pending[name] = value

    def set_session_metrics(self, metrics: dict) -> None:
        """Store metrics that apply to the entire session."""

        self.session_metrics = metrics.copy()

    def record_metrics(self, exercise_index: int, set_index: int, metrics):
        if exercise_index >= len(self.exercises):
            if self.end_time is None:
                self.end_time = time.time()
            return True

        key = (exercise_index, set_index)
        store = self.metric_store.get(key)
        if store is None:
            raise IndexError("Invalid exercise/set index")
        combined = {**self.pending_pre_set_metrics.pop(key, {}), **metrics}
        notes = str(combined.pop("Notes", ""))

        for name, value in combined.items():
            if name not in store:
                raise KeyError(
                    f"Unknown metric '{name}' for exercise {exercise_index}"
                )
            store[name] = value

        end_time = time.time()

        ex = self.exercises[exercise_index]
        results = ex["results"]
        while len(results) <= set_index:
            results.append(None)
        start_time = (
            self.current_set_start_time
            if exercise_index == self.current_exercise and set_index == self.current_set
            else end_time
        )
        results[set_index] = {
            "metrics": store.copy(),
            "started_at": start_time,
            "ended_at": end_time,
            "notes": notes,
        }

        if exercise_index == self.current_exercise and set_index == self.current_set:
            self.current_set_start_time = end_time
            self.current_set += 1
            self.awaiting_post_set_metrics = False

            if self.current_set >= ex["sets"]:
                self.current_set = 0
                self.current_exercise += 1

            if self.current_exercise >= len(self.exercises):
                self.end_time = end_time
                return True

        return False

    def undo_last_set(self) -> bool:
        """Reopen the most recently completed set.

        Returns ``True`` if a set was restored, ``False`` otherwise.
        """

        # Determine whether any set has been completed yet
        if self.current_exercise == 0 and self.current_set == 0 and not self.exercises[0]["results"]:
            return False

        # Identify exercise and set index of last completed set
        ex_idx = self.current_exercise
        set_idx = self.current_set - 1
        if set_idx < 0:
            ex_idx -= 1
            if ex_idx < 0:
                return False
            set_idx = len(self.exercises[ex_idx]["results"]) - 1
        ex = self.exercises[ex_idx]
        if not ex["results"]:
            return False
        last = ex["results"].pop()

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

        return True

    def has_started_exercise(self, exercise_index: int) -> bool:
        """Return True if the exercise at ``exercise_index`` has begun."""
        if exercise_index < 0 or exercise_index >= len(self.exercises):
            return False
        if self.exercises[exercise_index]["results"]:
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
            else len(self.exercises)
        )
        for idx in range(start, end):
            if self.has_started_exercise(idx):
                return False
        return True

    def apply_edited_preset(self, sections: list[dict]) -> None:
        """Replace remaining exercises with ``sections`` data."""
        new_exercises: list[dict] = []
        section_starts: list[int] = []
        section_names: list[str] = []
        exercise_sections: list[int] = []
        for sec_idx, sec in enumerate(sections):
            section_starts.append(len(new_exercises))
            section_names.append(sec.get("name", f"Section {sec_idx + 1}"))
            for ex in sec.get("exercises", []):
                ex_copy = {
                    "name": ex.get("name", ""),
                    "sets": ex.get("sets", DEFAULT_SETS_PER_EXERCISE),
                    "rest": ex.get("rest", self.rest_duration),
                    "results": [],
                    "library_exercise_id": ex.get("library_exercise_id"),
                    "preset_section_exercise_id": ex.get(
                        "preset_section_exercise_id"
                    ),
                    "exercise_description": ex.get("exercise_description", ""),
                    "metric_defs": ex.get("metric_defs", []),
                    "section_index": sec_idx,
                    "section_name": section_names[-1],
                }
                new_exercises.append(ex_copy)
                exercise_sections.append(sec_idx)

        if self.current_exercise < len(self.exercises):
            current_name = self.exercises[self.current_exercise]["name"]
            for i, ex in enumerate(new_exercises):
                if ex["name"] == current_name:
                    self.current_exercise = i
                    break
            else:
                self.current_exercise = min(self.current_exercise, len(new_exercises))
                self.current_set = 0

        self.exercises = new_exercises
        self.section_starts = section_starts
        self.section_names = section_names
        self.exercise_sections = exercise_sections

    def adjust_rest_timer(self, seconds: int) -> None:
        """Adjust the target time for the current rest period."""
        now = time.time()
        if self.rest_target_time <= now:
            self.rest_target_time = now
        self.rest_target_time += seconds
        if self.rest_target_time <= now:
            self.rest_target_time = now

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