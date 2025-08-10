class StubPresetProvider:
    """Stub provider returning example preset details."""

    def get_default_preset_name(self) -> str:
        return "Sample Preset"

    def get_preset_summary(self, preset_name: str):
        return {
            "metrics": [
                {"name": "Difficulty", "scope": "preset", "value": "Medium"},
                {"name": "Duration", "scope": "preset", "value": "45 min"},
            ],
            "sections": [
                {
                    "name": "Warmup",
                    "exercises": [
                        {"name": "Jumping Jacks", "sets": 3},
                        {"name": "Stretching", "sets": 2},
                    ],
                },
                {
                    "name": "Workout",
                    "exercises": [
                        {"name": "Push-ups", "sets": 3},
                        {"name": "Squats", "sets": 3},
                    ],
                },
            ],
        }
