"""Tiny screen utilities for environment overrides and sizing helpers.
# TINY-SCREEN: new module for compact mode helpers
"""
import os
import json
from typing import Dict

from kivy.metrics import Metrics, dp, sp
from kivy.core.window import Window

# --- Environment flags -----------------------------------------------------
_FORCE_DENSITY = os.environ.get("TINY_FORCE_DENSITY")
_FONT_SCALE_ENV = os.environ.get("TINY_FONT_SCALE")
_DEVICE_PROFILE = os.environ.get("TINY_DEVICE_PROFILE")
_COMPACT_OVERRIDE = os.environ.get("TINY_COMPACT_OVERRIDE", "auto")
_OVERLAY_STARTUP = os.environ.get("TINY_OVERLAY") == "1"

SAFE_AREA = {"top": 0.0, "bottom": 0.0}
_FONT_SCALE = 1.0


def apply_env_overrides() -> None:
    """Apply density/font-scale overrides before other Kivy metrics are used."""
    global _FONT_SCALE, SAFE_AREA
    profile = {}
    if _DEVICE_PROFILE:
        try:
            with open(_DEVICE_PROFILE, "r", encoding="utf8") as fh:
                profile = json.load(fh)
        except Exception:
            profile = {}
    density = None
    if "density" in profile:
        density = float(profile["density"])
    if _FORCE_DENSITY:
        density = float(_FORCE_DENSITY)
    if density:
        Metrics.density = density
        Metrics.dpi = density * 160
    if "fontscale" in profile:
        _FONT_SCALE = float(profile["fontscale"])
    if _FONT_SCALE_ENV:
        _FONT_SCALE = float(_FONT_SCALE_ENV)
    if "safe_area" in profile:
        SAFE_AREA.update(profile.get("safe_area", {}))


def get_font_scale() -> float:
    return _FONT_SCALE


def scaled_sp(value: float) -> float:
    """Return ``sp`` scaled by the active font scale."""
    return sp(value * _FONT_SCALE)


def get_safe_area_insets() -> Dict[str, float]:
    """Return safe area insets in dp for top and bottom."""
    return SAFE_AREA.copy()


def apply_safe_area_padding(widget, top: bool = False, bottom: bool = False) -> None:
    """Add safe-area padding to ``widget`` in-place."""
    sa = get_safe_area_insets()
    pad = list(getattr(widget, "padding", (0, 0, 0, 0)))
    if top:
        pad[1] += dp(sa.get("top", 0))
    if bottom:
        pad[3] += dp(sa.get("bottom", 0))
    widget.padding = pad


def get_smallest_width_dp() -> float:
    """Compute smallest width in dp for current window."""
    return min(Window.width, Window.height) / Metrics.density


IS_COMPACT = False


def _recompute_compact(*_args):
    global IS_COMPACT
    if _COMPACT_OVERRIDE == "1":
        IS_COMPACT = True
    elif _COMPACT_OVERRIDE == "0":
        IS_COMPACT = False
    else:
        IS_COMPACT = get_smallest_width_dp() <= 360


def bind_window() -> None:
    """Bind window size to recompute compact status."""
    _recompute_compact()
    Window.bind(size=_recompute_compact)


__all__ = [
    "apply_env_overrides",
    "scaled_sp",
    "get_safe_area_insets",
    "apply_safe_area_padding",
    "get_smallest_width_dp",
    "IS_COMPACT",
    "bind_window",
    "get_font_scale",
    "_OVERLAY_STARTUP",
]
