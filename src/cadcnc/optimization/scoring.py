"""Tool scoring engine evaluating candidate tools against feature geometry and material."""

from typing import List, Tuple, Optional
from cadcnc.schemas.config import ToolItem, MaterialItem
from cadcnc.schemas.features import HoleFeature, PocketFeature, SlotFeature, PlanarFaceFeature
from cadcnc.schemas.optimization import ToolCandidate, RejectedTool

def score_tool_for_hole(
    tool: ToolItem,
    hole: HoleFeature,
    material_id: str
) -> Tuple[Optional[ToolCandidate], Optional[RejectedTool]]:
    """Evaluates and scores a tool for drilling/counterboring a hole."""
    rejection_reasons = []

    # 1. Operation compatibility
    if tool.type != "drill" and "drill" not in tool.operations:
        rejection_reasons.append(f"Tool type '{tool.type}' is not a drill")

    # 2. Material compatibility
    if material_id not in tool.compatible_materials:
        rejection_reasons.append(f"Tool not rated for material '{material_id}'")

    # 3. Reach check
    if tool.reach_mm < hole.depth_mm:
        rejection_reasons.append(f"Tool reach ({tool.reach_mm}mm) is less than hole depth ({hole.depth_mm}mm)")

    # 4. Diameter match
    target_diam = hole.diameter_mm
    diam_diff = abs(tool.diameter_mm - target_diam)
    if diam_diff > 0.05:  # For standard hole drilling, diameter must match closely
        rejection_reasons.append(f"Tool diameter ({tool.diameter_mm}mm) does not match hole diameter ({target_diam}mm)")

    if rejection_reasons:
        return None, RejectedTool(tool_id=tool.id, tool_name=tool.name, reasons=rejection_reasons)

    # Score calculation
    score = 0.50
    checks = ["operation_compatible", "material_compatible", "reach_sufficient"]
    penalties = []

    # Exact diameter bonus
    if diam_diff < 0.01:
        score += 0.30
        checks.append("exact_nominal_diameter_match")

    # Tool material efficiency
    if tool.tool_material == "carbide":
        score += 0.15
        checks.append("high_efficiency_solid_carbide")
    else:
        score += 0.05
        checks.append("standard_hss_tool")

    # Point angle suitability for blind/through
    if hole.type == "blind" and tool.point_angle_deg and tool.point_angle_deg >= 135:
        score += 0.05
        checks.append("favorable_drill_point_for_blind_hole")

    return ToolCandidate(
        tool_id=tool.id,
        tool_name=tool.name,
        tool_diameter_mm=tool.diameter_mm,
        score=round(min(1.0, score), 3),
        check_reasons=checks,
        penalty_reasons=penalties
    ), None

def score_tool_for_pocket(
    tool: ToolItem,
    pocket: PocketFeature,
    material_id: str
) -> Tuple[Optional[ToolCandidate], Optional[RejectedTool]]:
    """Evaluates and scores a flat end mill for pocket clearing."""
    rejection_reasons = []

    if tool.type != "flat_end_mill" and "pocket_roughing" not in tool.operations:
        rejection_reasons.append(f"Tool type '{tool.type}' is not suitable for pocket clearing")

    if material_id not in tool.compatible_materials:
        rejection_reasons.append(f"Tool not rated for material '{material_id}'")

    if tool.reach_mm < pocket.depth_mm:
        rejection_reasons.append(f"Tool reach ({tool.reach_mm}mm) is less than pocket depth ({pocket.depth_mm}mm)")

    # Tool diameter must fit within pocket width with clearance for clearing passes
    if tool.diameter_mm >= pocket.width_mm:
        rejection_reasons.append(f"Tool diameter ({tool.diameter_mm}mm) exceeds pocket width ({pocket.width_mm}mm)")

    if rejection_reasons:
        return None, RejectedTool(tool_id=tool.id, tool_name=tool.name, reasons=rejection_reasons)

    score = 0.50
    checks = ["operation_compatible", "material_compatible", "reach_sufficient"]
    penalties = []

    # Optimal cutter diameter ratio: ~50% to 70% of pocket width
    ratio = tool.diameter_mm / max(pocket.width_mm, 1.0)
    if 0.4 <= ratio <= 0.7:
        score += 0.30
        checks.append("optimal_pocket_width_diameter_ratio")
    elif ratio < 0.4:
        score += 0.15
        penalties.append("small_diameter_requires_many_clearing_passes")

    if tool.tool_material == "carbide":
        score += 0.15
        checks.append("high_speed_solid_carbide")

    # Corner radii match
    if pocket.corner_radii_mm:
        min_radius = min(pocket.corner_radii_mm)
        if tool.diameter_mm <= (min_radius * 2.0 + 0.1):
            score += 0.05
            checks.append("fits_internal_fillet_radii")
        else:
            penalties.append("tool_radius_exceeds_pocket_corner_fillet")

    return ToolCandidate(
        tool_id=tool.id,
        tool_name=tool.name,
        tool_diameter_mm=tool.diameter_mm,
        score=round(min(1.0, score), 3),
        check_reasons=checks,
        penalty_reasons=penalties
    ), None

def score_tool_for_slot(
    tool: ToolItem,
    slot: SlotFeature,
    material_id: str
) -> Tuple[Optional[ToolCandidate], Optional[RejectedTool]]:
    """Evaluates and scores a flat end mill for slot milling."""
    rejection_reasons = []

    if tool.type != "flat_end_mill" and "slot_milling" not in tool.operations:
        rejection_reasons.append(f"Tool type '{tool.type}' is not suitable for slot milling")

    if material_id not in tool.compatible_materials:
        rejection_reasons.append(f"Tool not rated for material '{material_id}'")

    if tool.reach_mm < slot.depth_mm:
        rejection_reasons.append(f"Tool reach ({tool.reach_mm}mm) is less than slot depth ({slot.depth_mm}mm)")

    if tool.diameter_mm > slot.width_mm:
        rejection_reasons.append(f"Tool diameter ({tool.diameter_mm}mm) exceeds slot width ({slot.width_mm}mm)")

    if rejection_reasons:
        return None, RejectedTool(tool_id=tool.id, tool_name=tool.name, reasons=rejection_reasons)

    score = 0.50
    checks = ["operation_compatible", "material_compatible", "reach_sufficient"]
    penalties = []

    # Exact slot width cutter allows single pass slotting
    if abs(tool.diameter_mm - slot.width_mm) < 0.05:
        score += 0.35
        checks.append("exact_slot_width_enables_single_pass")
    else:
        score += 0.20
        checks.append("smaller_diameter_allows_multichannel_clearing")

    if tool.tool_material == "carbide":
        score += 0.15
        checks.append("carbide_tool_efficiency")

    return ToolCandidate(
        tool_id=tool.id,
        tool_name=tool.name,
        tool_diameter_mm=tool.diameter_mm,
        score=round(min(1.0, score), 3),
        check_reasons=checks,
        penalty_reasons=penalties
    ), None

def score_tool_for_facing(
    tool: ToolItem,
    face: PlanarFaceFeature,
    material_id: str
) -> Tuple[Optional[ToolCandidate], Optional[RejectedTool]]:
    """Evaluates and scores face mills or wide end mills for top surface facing."""
    rejection_reasons = []

    if tool.type not in ("face_mill", "flat_end_mill") and "facing" not in tool.operations:
        rejection_reasons.append(f"Tool type '{tool.type}' is not suitable for facing")

    if material_id not in tool.compatible_materials:
        rejection_reasons.append(f"Tool not rated for material '{material_id}'")

    if rejection_reasons:
        return None, RejectedTool(tool_id=tool.id, tool_name=tool.name, reasons=rejection_reasons)

    score = 0.50
    checks = ["operation_compatible", "material_compatible"]
    penalties = []

    if tool.type == "face_mill":
        score += 0.40
        checks.append("dedicated_multi_insert_face_mill")
    elif tool.diameter_mm >= 12.0:
        score += 0.25
        checks.append("large_diameter_end_mill_facing")
    else:
        score += 0.10
        penalties.append("small_diameter_requires_excessive_facing_passes")

    return ToolCandidate(
        tool_id=tool.id,
        tool_name=tool.name,
        tool_diameter_mm=tool.diameter_mm,
        score=round(min(1.0, score), 3),
        check_reasons=checks,
        penalty_reasons=penalties
    ), None
