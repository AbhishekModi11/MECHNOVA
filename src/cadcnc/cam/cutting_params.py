"""Calculates spindle speeds and cutting feed rates based on workpiece and tool materials."""

import math
from typing import Dict, Tuple
from cadcnc.schemas.config import MaterialItem, ToolItem, MachineConfig, CuttingData

def calculate_cutting_parameters(
    tool: ToolItem,
    material: MaterialItem,
    machine_config: MachineConfig,
    operation_type: str = "milling"
) -> Tuple[float, float, float]:
    """Calculates RPM, cutting feed (mm/min), and plunge feed (mm/min).
    
    Returns:
        Tuple of (spindle_rpm, cutting_feed_mm_min, plunge_feed_mm_min) clamped to machine limits.
    """
    tool_mat = tool.tool_material if tool.tool_material in ("carbide", "hss") else "carbide"
    c_data = material.cutting_data.get(tool_mat) or material.cutting_data.get("carbide")
    if not c_data:
        c_data = CuttingData(cutting_speed_m_min=100.0, chip_load_mill_mm_tooth=0.05, chip_load_drill_mm_flute=0.05, plunge_factor=0.4)

    vc = c_data.cutting_speed_m_min
    diam = max(tool.diameter_mm, 1.0)

    # RPM = (1000 * Vc) / (pi * D)
    calc_rpm = (1000.0 * vc) / (math.pi * diam)
    # Clamp to tool and machine max RPM
    rpm = min(calc_rpm, tool.max_rpm, machine_config.machine.max_spindle_rpm)
    rpm = max(100.0, rpm)

    # Chip load
    if operation_type in ("drill", "peck_drill"):
        fz = c_data.chip_load_drill_mm_flute
    else:
        fz = c_data.chip_load_mill_mm_tooth

    # Feed = RPM * flutes * fz
    flutes = max(1, tool.flutes)
    calc_feed = rpm * flutes * fz
    feed = min(calc_feed, machine_config.machine.max_feed_mm_min)
    feed = max(10.0, feed)

    plunge_factor = c_data.plunge_factor
    plunge_feed = max(5.0, feed * plunge_factor)

    return round(rpm, 0), round(feed, 0), round(plunge_feed, 0)
