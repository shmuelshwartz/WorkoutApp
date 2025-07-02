"""Core data structures for workout presets."""

# A very simple representation of workout presets. Each preset only
# includes a name and a list of exercises. Repetition schemes are not
# defined here so that workouts can be customised later on.

WORKOUT_PRESETS = [
    {
        "name": "Push",
        "exercises": [
            "Bench Press",
            "Overhead Press",
            "Tricep Dip",
        ],
    },
    {
        "name": "Pull",
        "exercises": [
            "Pull Up",
            "Barbell Row",
            "Bicep Curl",
        ],
    },
    {
        "name": "Legs",
        "exercises": [
            "Squat",
            "Lunge",
            "Calf Raise",
        ],
    },
]

