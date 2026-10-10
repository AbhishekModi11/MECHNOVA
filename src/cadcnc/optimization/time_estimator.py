"""Machining cycle time estimation engine with documented transparent formulas."""

from typing import List, Tuple
from cadcnc.schemas.config import MachineConfig

def estimate_linear_move_time_s(length_mm: float, feed_mm_min: float) -> float:
    """Cutting time (s) = (distance_mm / feed_mm_min) * 60."""
    if feed_mm_min <= 0.0 or length_mm <= 0.0:
        return 0.0
    return (length_mm / feed_mm_min) * 60.0

def estimate_rapid_move_time_s(distance_mm: float, rapid_rate_mm_min: float) -> float:
    """Rapid traverse time (s) = (distance_mm / rapid_rate_mm_min) * 60."""
    if rapid_rate_mm_min <= 0.0 or distance_mm <= 0.0:
        return 0.0
    return (distance_mm / rapid_rate_mm_min) * 60.0

def estimate_drilling_time_s(
    depth_mm: float,
    feed_mm_min: float,
    plunge_feed_mm_min: float,
    is_peck: bool = False,
    peck_count: int = 1
) -> float:
    """Estimates drilling time including plunges, cuts, and retracts."""
    cut_time = estimate_linear_move_time_s(depth_mm, feed_mm_min)
    if is_peck and peck_count > 1:
        # Additional retract and plunge travel per peck
        retract_time = peck_count * 0.8  # ~0.8s rapid retract and return per peck
        return cut_time + retract_time
    return cut_time

def estimate_tool_change_time_s(tool_changes_count: int, time_per_change_s: float = 8.0) -> float:
    """Total ATC time = number of tool changes * configured time per change."""
    return max(0, tool_changes_count) * time_per_change_s

def estimate_setup_change_time_s(setup_changes_count: int, time_per_setup_s: float = 300.0) -> float:
    """Total setup fixture time = number of setup changes * configured time per setup."""
    return max(0, setup_changes_count) * time_per_setup_s
