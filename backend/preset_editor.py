import copy
import json
import sqlite3
from pathlib import Path

from core import (
    DEFAULT_DB_PATH,
    DEFAULT_SETS_PER_EXERCISE,
    DEFAULT_REST_DURATION,
    _to_db_timing,
    _from_db_timing,
)


class PresetEditor:
    """Helper for creating or editing workout presets in memory."""

    def __init__(
        self,
        preset_name: str | None = None,
        db_path: Path = DEFAULT_DB_PATH,
    ):
        """Create the editor and optionally load an existing preset."""

        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))

        self.preset_name: str = preset_name or ""
        self.sections: list[dict] = []
        self.preset_metrics: list[dict] = []
        self._preset_id: int | None = None
        self._original: dict | None = None

        if preset_name:
            self.load(preset_name)
        else:
            self._load_required_metrics()
            self._original = self.to_dict()

    def _load_required_metrics(self) -> None:
        """Load required preset metric types into ``preset_metrics``."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT name, description, type,
                   input_timing, is_required, scope, enum_values_json

              FROM library_metric_types
             WHERE deleted = 0 AND is_required = 1
               AND scope IN ('preset', 'session')
            ORDER BY id
            """
        )
        for (
            name,
            desc,
            mtype,
            timing,
            req,
            scope,
            enum_json,
        ) in cursor.fetchall():
            values = []
            if mtype == "enum" and enum_json:
                try:
                    values = json.loads(enum_json)
                except Exception:
                    values = []
            self.preset_metrics.append(
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": timing,
                    "is_required": bool(req),
                    "scope": scope,
                    "description": desc,
                    "values": values,
                    "value": None,
                }
            )

    def load(self, preset_name: str) -> None:
        """Load ``preset_name`` from the database into memory."""

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
            (preset_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Preset '{preset_name}' not found")

        preset_id = row[0]
        cursor.execute(
            "SELECT id, name FROM preset_preset_sections WHERE preset_id = ? AND deleted = 0 ORDER BY position",
            (preset_id,),
        )

        self.preset_name = preset_name
        self.sections.clear()
        self.preset_metrics.clear()

        for section_id, name in cursor.fetchall():
            cursor.execute(
                """
                SELECT id, exercise_name, number_of_sets, rest_time, library_exercise_id
                  FROM preset_section_exercises
                 WHERE section_id = ? AND deleted = 0
                 ORDER BY position
                """,
                (section_id,),
            )
            exercises = []
            for ex_id, ex_name, sets, rest, lib_id in cursor.fetchall():
                exercises.append(
                    {
                        "id": ex_id,
                        "name": ex_name,
                        "sets": sets,
                        "rest": rest,
                        "library_id": lib_id,
                    }
                )
            self.sections.append({"name": name, "exercises": exercises})

        cursor.execute(
            """
            SELECT metric_name, value, type,
                   input_timing, is_required, scope,
                   enum_values_json, metric_description
              FROM preset_preset_metrics
             WHERE preset_id = ? AND deleted = 0
             ORDER BY position
            """,
            (preset_id,),
        )
        for (
            name,
            value,
            mtype,
            timing,
            req,
            scope,
            enum_json,
            desc,
        ) in cursor.fetchall():
            if mtype == "int":
                try:
                    value = int(value)
                except Exception:
                    value = 0
            elif mtype in ("float", "slider"):
                try:
                    value = float(value)
                except Exception:
                    value = 0.0
            values = []
            if mtype == "enum" and enum_json:
                try:
                    values = json.loads(enum_json)
                except Exception:
                    values = []
            self.preset_metrics.append(
                {
                    "name": name,
                    "type": mtype,
                    "input_timing": _from_db_timing(timing),
                    "is_required": bool(req),
                    "scope": scope,
                    "description": desc,
                    "values": values,
                    "value": value,
                }
            )

        self._preset_id = preset_id
        self._original = self.to_dict()

    def add_section(self, name: str = "Section") -> int:
        """Add a new section and return its index."""

        self.sections.append({"name": name, "exercises": []})
        return len(self.sections) - 1

    def remove_section(self, index: int) -> None:
        """Remove the section at ``index`` if it exists."""

        if 0 <= index < len(self.sections):
            self.sections.pop(index)

    def rename_section(self, index: int, name: str) -> None:
        """Rename the section at ``index`` to ``name``."""

        if index < 0 or index >= len(self.sections):
            raise IndexError("Section index out of range")
        self.sections[index]["name"] = name

    def add_exercise(
        self,
        section_index: int,
        exercise_name: str,
        sets: int = DEFAULT_SETS_PER_EXERCISE,
        rest: int = DEFAULT_REST_DURATION,
    ) -> dict:
        """Add an exercise to the specified section."""

        if section_index < 0 or section_index >= len(self.sections):
            raise IndexError("Section index out of range")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
            (exercise_name,),
        )
        row = cursor.fetchone()
        if row is None:
            raise ValueError(f"Exercise '{exercise_name}' does not exist")

        ex = {
            "id": None,
            "name": exercise_name,
            "sets": sets,
            "rest": rest,
            "library_id": row[0],
        }
        self.sections[section_index]["exercises"].append(ex)
        return ex

    def update_exercise(
        self,
        section_index: int,
        exercise_index: int,
        *,
        sets: int | None = None,
        rest: int | None = None,
    ) -> None:
        """Update sets or rest time for an exercise in the preset."""

        if (
            section_index < 0
            or section_index >= len(self.sections)
            or exercise_index < 0
            or exercise_index >= len(self.sections[section_index]["exercises"])
        ):
            raise IndexError("Exercise index out of range")

        exercise = self.sections[section_index]["exercises"][exercise_index]
        if sets is not None:
            exercise["sets"] = sets
        if rest is not None:
            exercise["rest"] = rest

    def remove_exercise(self, section_index: int, exercise_index: int) -> None:
        """Remove an exercise from ``section_index`` at ``exercise_index``."""

        if (
            section_index < 0
            or section_index >= len(self.sections)
            or exercise_index < 0
            or exercise_index >= len(self.sections[section_index]["exercises"])
        ):
            raise IndexError("Exercise index out of range")

        self.sections[section_index]["exercises"].pop(exercise_index)

    def move_exercise(self, section_index: int, old_index: int, new_index: int) -> None:
        """Move an exercise within a section to ``new_index``."""

        if (
            section_index < 0
            or section_index >= len(self.sections)
            or old_index < 0
            or old_index >= len(self.sections[section_index]["exercises"])
            or new_index < 0
            or new_index >= len(self.sections[section_index]["exercises"])
        ):
            raise IndexError("Exercise index out of range")

        exercises = self.sections[section_index]["exercises"]
        ex = exercises.pop(old_index)
        exercises.insert(new_index, ex)

    # ------------------------------------------------------------------
    # Preset metric helpers
    # ------------------------------------------------------------------
    def add_metric(self, metric_name: str, *, value=None) -> None:
        """Add a metric defined in ``library_metric_types`` by name."""

        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT description, type, input_timing,
                   scope, is_required, enum_values_json
              FROM library_metric_types
             WHERE name = ? AND deleted = 0
            """,
            (metric_name,),
        )
        row = cursor.fetchone()
        if not row:
            raise ValueError(f"Metric '{metric_name}' not found")
        (
            desc,
            mtype,
            timing,
            scope,
            req,
            enum_json,
        ) = row
        values = []
        if mtype == "enum" and enum_json:
            try:
                values = json.loads(enum_json)
            except Exception:
                values = []
        self.preset_metrics.append(
            {
                "name": metric_name,
                "type": mtype,
                "input_timing": timing,
                "is_required": bool(req),
                "scope": scope,
                "description": desc,
                "values": values,
                "value": value,
            }
        )

    def remove_metric(self, metric_name: str) -> None:
        """Remove metric with ``metric_name`` if present."""

        self.preset_metrics = [
            m for m in self.preset_metrics if m.get("name") != metric_name
        ]

    def update_metric(self, metric_name: str, **updates) -> None:
        """Update metric named ``metric_name`` with ``updates``."""

        for metric in self.preset_metrics:
            if metric.get("name") == metric_name:
                metric.update(updates)
                break

    def to_dict(self) -> dict:
        """Return the preset data as a dictionary."""

        result = {
            "name": self.preset_name,
            "sections": [],
            "preset_metrics": copy.deepcopy(self.preset_metrics),
        }
        for sec in self.sections:
            ex_list = []
            for ex in sec.get("exercises", []):
                ex_copy = {k: v for k, v in ex.items() if k not in {"id", "library_id"}}
                ex_list.append(copy.deepcopy(ex_copy))
            result["sections"].append({"name": sec.get("name"), "exercises": ex_list})
        return result

    def close(self) -> None:
        self.conn.close()

    # ------------------------------------------------------------------
    # Modification tracking helpers
    # ------------------------------------------------------------------
    def is_modified(self) -> bool:
        """Return ``True`` if the preset differs from the original state."""

        return self._original != self.to_dict()

    def mark_saved(self) -> None:
        """Record the current state as the saved state."""

        self._preset_id = self._preset_id  # keep mypy happy
        self._original = self.to_dict()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def validate(self) -> None:
        """Run checks to ensure the preset can be saved without writing to the database."""

        if not self.preset_name.strip():
            raise ValueError("Preset name cannot be empty")

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id FROM preset_presets WHERE name = ? AND deleted = 0",
            (self.preset_name,),
        )
        row = cursor.fetchone()
        if row and (self._preset_id is None or row[0] != self._preset_id):
            raise ValueError("A preset with that name already exists")

        for sec in self.sections:
            for ex in sec.get("exercises", []):
                cursor.execute(
                    "SELECT 1 FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                    (ex.get("name"),),
                )
                if cursor.fetchone() is None:
                    raise ValueError(f"Exercise '{ex['name']}' does not exist")

    def save(self) -> None:
        """Write the current preset to the database. Assumes validation has been performed."""

        cursor = self.conn.cursor()

        if self._preset_id is not None:
            preset_id = self._preset_id
            cursor.execute(
                "UPDATE preset_presets SET name = ? WHERE id = ?",
                (self.preset_name, preset_id),
            )
            cursor.execute(
                "SELECT id FROM preset_preset_sections WHERE preset_id = ? AND deleted = 0 ORDER BY position",
                (preset_id,),
            )
            sec_ids = [r[0] for r in cursor.fetchall()]
        else:
            cursor.execute(
                "INSERT INTO preset_presets (name) VALUES (?)",
                (self.preset_name,),
            )
            preset_id = cursor.lastrowid
            self._preset_id = preset_id
            sec_ids = []

        for sec_pos, sec in enumerate(self.sections):
            if sec_pos < len(sec_ids):
                section_id = sec_ids[sec_pos]
                cursor.execute(
                    "UPDATE preset_preset_sections SET name = ?, position = ?, deleted = 0 WHERE id = ?",
                    (sec.get("name", f"Section {sec_pos + 1}"), sec_pos, section_id),
                )
            else:
                cursor.execute(
                    "INSERT INTO preset_preset_sections (preset_id, name, position) VALUES (?, ?, ?)",
                    (preset_id, sec.get("name", f"Section {sec_pos + 1}"), sec_pos),
                )
                section_id = cursor.lastrowid

            cursor.execute(
                "SELECT id, exercise_name, number_of_sets, rest_time, position, library_exercise_id FROM preset_section_exercises WHERE section_id = ? AND deleted = 0",
                (section_id,),
            )
            existing = {
                row_id: {
                    "name": n,
                    "sets": s,
                    "rest": r,
                    "pos": p,
                    "library_id": lib,
                }
                for row_id, n, s, r, p, lib in cursor.fetchall()
            }
            unused = set(existing.keys())

            for ex_pos, ex in enumerate(sec.get("exercises", [])):
                cursor.execute(
                    "SELECT id, description FROM library_exercises WHERE name = ? AND deleted = 0 ORDER BY is_user_created DESC LIMIT 1",
                    (ex["name"],),
                )
                lr = cursor.fetchone()
                if lr is None:
                    raise RuntimeError(f"Exercise '{ex['name']}' not found during save")
                lib_id, desc = lr[0], lr[1] or ""

                ex_id = ex.get("id")
                sets_val = ex.get("sets", DEFAULT_SETS_PER_EXERCISE)
                rest_val = ex.get("rest", DEFAULT_REST_DURATION)

                if ex_id is not None and ex_id not in existing:
                    ex_id = None
                    ex["id"] = None
                    for m in ex.get("metrics", []):
                        m.pop("id", None)
                        m.pop("section_exercise_id", None)

                if ex_id is not None and ex_id in existing:
                    row = existing[ex_id]
                    unused.discard(ex_id)
                    if (
                        row["name"] == ex["name"]
                        and row["sets"] == sets_val
                        and row["rest"] == rest_val
                        and row["library_id"] == lib_id
                    ):
                        if row["pos"] != ex_pos:
                            cursor.execute(
                                "UPDATE preset_section_exercises SET position = ? WHERE id = ?",
                                (ex_pos, ex_id),
                            )
                    else:
                        cursor.execute(
                            "UPDATE preset_section_exercises SET exercise_name = ?, exercise_description = ?, number_of_sets = ?, rest_time = ?, position = ?, library_exercise_id = ?, deleted = 0 WHERE id = ?",
                            (
                                ex["name"],
                                desc,
                                sets_val,
                                rest_val,
                                ex_pos,
                                lib_id,
                                ex_id,
                            ),
                        )

                        if row["library_id"] != lib_id:
                            for m in ex.get("metrics", []):
                                m.pop("id", None)
                                m.pop("section_exercise_id", None)
                            cursor.execute(
                                """
                              SELECT mt.name,
                                     mt.description,
                                     COALESCE(em.type, mt.type),
                                     COALESCE(em.input_timing, mt.input_timing),
                                     COALESCE(em.is_required, mt.is_required),
                                     COALESCE(em.scope, mt.scope),
                                     COALESCE(em.enum_values_json, mt.enum_values_json),
                                     em.position,
                                     mt.id
                              FROM library_exercise_metrics em
                              JOIN library_metric_types mt ON em.metric_type_id = mt.id

                             WHERE em.exercise_id = ?
                               AND em.deleted = 0 AND mt.deleted = 0

                             ORDER BY em.position
                            """,
                                (lib_id,),
                            )
                            lib_metrics = cursor.fetchall()
                            cursor.execute(
                                "SELECT id, metric_name FROM preset_exercise_metrics WHERE section_exercise_id = ? AND deleted = 0",
                                (ex_id,),
                            )
                            existing_metrics = {name: mid for mid, name in cursor.fetchall()}
                            for (
                                mt_name,
                                mt_desc,
                                m_input,
                                m_timing,
                                m_req,
                                m_scope,
                                m_enum_json,
                                mpos,
                                mt_id,
                            ) in lib_metrics:
                                if mt_name in existing_metrics:
                                    cursor.execute(
                                        "UPDATE preset_exercise_metrics SET deleted = 1 WHERE id = ?",
                                        (existing_metrics.pop(mt_name),),
                                    )
                                cursor.execute(
                                    "SELECT 1 FROM preset_exercise_metrics WHERE section_exercise_id = ? AND metric_name = ? AND deleted = 0",
                                    (ex_id, mt_name),
                                )
                                if cursor.fetchone():
                                    continue
                                cursor.execute(
                                    """INSERT INTO preset_exercise_metrics (section_exercise_id, metric_name, metric_description, type, input_timing, is_required, scope, enum_values_json, position, library_metric_type_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                    (
                                        ex_id,
                                        mt_name,
                                        mt_desc,
                                        m_input,
                                        m_timing,
                                        m_req,
                                        m_scope,
                                        m_enum_json,
                                        mpos,
                                        mt_id,
                                    ),
                                )
                            for mid in existing_metrics.values():
                                cursor.execute(
                                    "UPDATE preset_exercise_metrics SET deleted = 1 WHERE id = ?",
                                    (mid,),
                                )
                else:
                    cursor.execute(
                        """INSERT INTO preset_section_exercises (section_id, exercise_name, exercise_description, position, number_of_sets, library_exercise_id, rest_time) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            section_id,
                            ex["name"],
                            desc,
                            ex_pos,
                            sets_val,
                            lib_id,
                            rest_val,
                        ),
                    )
                    ex_id = cursor.lastrowid
                    ex["id"] = ex_id

                    cursor.execute(
                        """
                        SELECT mt.name,
                               mt.description,
                               COALESCE(em.type, mt.type),
                               COALESCE(em.input_timing, mt.input_timing),
                               COALESCE(em.is_required, mt.is_required),
                               COALESCE(em.scope, mt.scope),
                               COALESCE(em.enum_values_json, mt.enum_values_json),
                               em.position,
                               mt.id
                          FROM library_exercise_metrics em
                          JOIN library_metric_types mt ON em.metric_type_id = mt.id

                         WHERE em.exercise_id = ?
                           AND em.deleted = 0 AND mt.deleted = 0

                         ORDER BY em.position
                        """,
                        (lib_id,),
                    )
                    lib_metrics = cursor.fetchall()
                    cursor.execute(
                        "SELECT id, metric_name FROM preset_exercise_metrics WHERE section_exercise_id = ? AND deleted = 0",
                        (ex_id,),
                    )
                    existing_metrics = {name: mid for mid, name in cursor.fetchall()}
                    for (
                        mt_name,
                        mt_desc,
                        m_input,
                        m_timing,
                        m_req,
                        m_scope,
                        m_enum_json,
                        mpos,
                        mt_id,
                    ) in lib_metrics:
                        if mt_name in existing_metrics:
                            cursor.execute(
                                "UPDATE preset_exercise_metrics SET deleted = 1 WHERE id = ?",
                                (existing_metrics.pop(mt_name),),
                            )
                        cursor.execute(
                            "SELECT 1 FROM preset_exercise_metrics WHERE section_exercise_id = ? AND metric_name = ? AND deleted = 0",
                            (ex_id, mt_name),
                        )
                        if cursor.fetchone():
                            continue
                        cursor.execute(
                            """INSERT INTO preset_exercise_metrics (section_exercise_id, metric_name, metric_description, type, input_timing, is_required, scope, enum_values_json, position, library_metric_type_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                ex_id,
                                mt_name,
                                mt_desc,
                                m_input,
                                m_timing,
                                m_req,
                                m_scope,
                                m_enum_json,
                                mpos,
                                mt_id,
                            ),
                        )
                    for mid in existing_metrics.values():
                        cursor.execute(
                            "UPDATE preset_exercise_metrics SET deleted = 1 WHERE id = ?",
                            (mid,),
                        )

            for old_id in unused:
                cursor.execute(
                    "UPDATE preset_exercise_metrics SET deleted = 1 WHERE section_exercise_id = ?",
                    (old_id,),
                )
                cursor.execute(
                    "UPDATE preset_section_exercises SET deleted = 1 WHERE id = ?",
                    (old_id,),
                )

        for sid in sec_ids[len(self.sections) :]:
            cursor.execute(
                "SELECT id FROM preset_section_exercises WHERE section_id = ? AND deleted = 0",
                (sid,),
            )
            ex_ids = [r[0] for r in cursor.fetchall()]
            for eid in ex_ids:
                cursor.execute(
                    "UPDATE preset_exercise_metrics SET deleted = 1 WHERE section_exercise_id = ?",
                    (eid,),
                )
                cursor.execute(
                    "UPDATE preset_section_exercises SET deleted = 1 WHERE id = ?",
                    (eid,),
                )
            cursor.execute(
                "UPDATE preset_preset_sections SET deleted = 1 WHERE id = ?",
                (sid,),
            )

        cursor.execute(
            "SELECT id, library_metric_type_id FROM preset_preset_metrics"
            " WHERE preset_id = ? AND deleted = 0",
            (preset_id,),
        )
        existing = {lm_id: row_id for row_id, lm_id in cursor.fetchall()}

        for pos, metric in enumerate(self.preset_metrics):
            cursor.execute(
                "SELECT id FROM library_metric_types WHERE name = ? AND deleted = 0",
                (metric.get("name"),),
            )
            row = cursor.fetchone()
            if not row:
                continue
            mt_id = row[0]
            enum_json = (
                json.dumps(metric.get("values"))
                if metric.get("type") == "enum" and metric.get("values")
                else None
            )

            if mt_id in existing:
                cursor.execute(
                    """
                    UPDATE preset_preset_metrics
                       SET type = ?,
                           input_timing = ?,
                           scope = ?,
                           metric_name = ?,
                           metric_description = ?,
                           is_required = ?,
                           enum_values_json = ?,
                           position = ?,
                           value = ?,
                           deleted = 0
                     WHERE id = ?
                    """,
                    (
                        metric.get("type"),
                        _to_db_timing(metric.get("input_timing")),
                        metric.get("scope"),
                        metric.get("name"),
                        metric.get("description"),
                        int(metric.get("is_required", False)),
                        enum_json,
                        pos,
                        (
                            str(metric.get("value"))
                            if metric.get("value") is not None
                            else None
                        ),
                        existing.pop(mt_id),
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO preset_preset_metrics
                        (
                            preset_id,
                            library_metric_type_id,
                            metric_name,
                            metric_description,
                            type,
                            input_timing,
                            scope,
                            is_required,
                            enum_values_json,
                            position,
                            value
                        )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        preset_id,
                        mt_id,
                        metric.get("name"),
                        metric.get("description"),
                        metric.get("type"),
                        _to_db_timing(metric.get("input_timing")),
                        metric.get("scope"),
                        int(metric.get("is_required", False)),
                        enum_json,
                        pos,
                        (
                            str(metric.get("value"))
                            if metric.get("value") is not None
                            else None
                        ),
                    ),
                )

        for remaining_id in existing.values():
            cursor.execute(
                "UPDATE preset_preset_metrics SET deleted = 1 WHERE id = ?",
                (remaining_id,),
            )

        self.conn.commit()
        self.mark_saved()
