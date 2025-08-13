from pathlib import Path

from backend import DEFAULT_DB_PATH
from backend.metrics import get_metrics_for_exercise
from backend.exercises import get_exercise_details


class Exercise:
    """Editable exercise loaded from the database.

    This is a lightweight helper used by the ``EditExerciseScreen``.  It
    mirrors the details stored in the database and keeps all modifications
    in memory.  The database is updated only when the caller explicitly
    chooses to persist the changes.
    """

    def __init__(
        self,
        name: str = "",
        *,
        db_path: Path = DEFAULT_DB_PATH,
        is_user_created: bool | None = None,
    ) -> None:
        self.db_path = Path(db_path)
        self.name: str = name
        self.description: str = ""
        self.metrics: list[dict] = []
        self.is_user_created: bool = True
        self._original: dict | None = None

        if name:
            self.load(name, is_user_created=is_user_created)
        else:
            self._original = self.to_dict()

    def load(self, name: str, *, is_user_created: bool | None = None) -> None:
        """Load ``name`` from ``db_path`` into this object."""

        details = get_exercise_details(name, self.db_path, is_user_created)
        if details:
            self.name = details.get("name", name)
            self.description = details.get("description", "")
            self.is_user_created = details.get("is_user_created", True)
        else:
            self.is_user_created = (
                bool(is_user_created) if is_user_created is not None else True
            )
        self.metrics = get_metrics_for_exercise(
            name,
            db_path=self.db_path,
            is_user_created=(
                details.get("is_user_created") if details else is_user_created
            ),
        )
        self._original = self.to_dict()

    # ------------------------------------------------------------------
    # Modification helpers.  These operate only on the in-memory object
    # until the exercise is explicitly saved back to the database.
    # ------------------------------------------------------------------
    def add_metric(self, metric: dict) -> None:
        """Append ``metric`` to the metrics list."""

        self.metrics.append(metric)

    def remove_metric(self, metric_name: str) -> None:
        """Remove metric with ``metric_name`` if present."""

        self.metrics = [m for m in self.metrics if m.get("name") != metric_name]

    def update_metric(self, metric_name: str, **updates) -> None:
        """Update metric named ``metric_name`` with ``updates``."""

        for metric in self.metrics:
            if metric.get("name") == metric_name:
                metric.update(updates)
                break

    def to_dict(self) -> dict:
        """Return a ``dict`` representation of the exercise."""

        return {
            "name": self.name,
            "description": self.description,
            "metrics": [m.copy() for m in self.metrics],
        }

    def is_modified(self) -> bool:
        """Return ``True`` if the exercise differs from its original state."""

        return self._original != self.to_dict()

    def mark_saved(self) -> None:
        """Reset the original state to the current data."""

        self._original = self.to_dict()

    def had_metric(self, metric_name: str) -> bool:
        """Return ``True`` if ``metric_name`` existed when loaded."""

        if not self._original:
            return False
        for m in self._original.get("metrics", []):
            if m.get("name") == metric_name:
                return True
        return False

