"""Utility helpers used across backend modules."""

# Map legacy session-level ``input_timing`` values to the canonical ones
# expected by the ``preset_preset_metrics`` table.
_TIMING_TO_DB = {
    "pre_session": "pre_workout",
    "post_session": "post_workout",
}
_TIMING_FROM_DB = {v: k for k, v in _TIMING_TO_DB.items()}


def _to_db_timing(value: str | None) -> str | None:
    """Return canonical timing value for database writes."""

    if value is None:
        return None
    return _TIMING_TO_DB.get(value, value)


def _from_db_timing(value: str | None) -> str | None:
    """Return UI-friendly timing value from the database."""

    if value is None:
        return None
    return _TIMING_FROM_DB.get(value, value)

