"""Stub data provider for :class:`MetricInputScreen` visual tests."""

class StubSession:
    """Minimal workout session stub used for screen previews."""

    def __init__(self):
        # example exercises with metric definitions
        self.exercises = [
            {
                "name": "Bench",
                "sets": 2,
                "metric_defs": [
                    {"name": "Weight", "type": "float", "is_required": True},
                    {"name": "Notes", "type": "str", "is_required": False},
                ],
                "results": [],
            },
            {
                "name": "Squat",
                "sets": 1,
                "metric_defs": [],
                "results": [],
            },
        ]
        self.current_exercise = 0
        self.current_set = 0
        self.section_starts = [0]
        self.exercise_sections = [0, 0]
        self.pending_pre_set_metrics = {}

    def record_metrics(self, ex_idx, set_idx, metrics):
        """Pretend to store metrics; always return ``False`` to stay in flow."""
        return False

    def set_pre_set_metrics(self, metrics, ex_idx, set_idx):
        self.pending_pre_set_metrics[(ex_idx, set_idx)] = metrics


class StubDataProvider:
    """Provides stubbed workout session data."""

    def __init__(self):
        self._session = StubSession()

    def get_session(self):
        return self._session
