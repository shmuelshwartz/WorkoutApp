"""Utility helpers used across backend modules."""

# Map ``input_timing`` values to the canonical ones expected by the
# ``preset_preset_metrics`` table. Legacy aliases have been removed so the
# mapping is now identity based.
_TIMING_TO_DB = {
    "pre_session": "pre_session",
    "post_session": "post_session",
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

