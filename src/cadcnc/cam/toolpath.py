"""Toolpath generator compiling operations into ordered polylines and toolpaths.json."""

from typing import Dict, List, Optional
from cadcnc.schemas.common import Point3D, BoundingBox3D
from cadcnc.schemas.features import FeaturesCollection
from cadcnc.schemas.optimization import MachiningPlan, ToolRecommendationsReport
from cadcnc.schemas.cam import (
    ToolpathOperation, ToolpathMove, ToolpathsCollection, MoveType
)
from cadcnc.schemas.config import ToolsDatabase, ThresholdsConfig
from cadcnc.cam.operations import (
    generate_facing_toolpath_moves, generate_drilling_toolpath_moves, generate_pocket_clearing_moves
)

def generate_full_toolpaths(
    plan: MachiningPlan,
    features: FeaturesCollection,
    part_bbox: BoundingBox3D,
    tools_db: ToolsDatabase,
    config: ThresholdsConfig
) -> ToolpathsCollection:
    """Generates continuous geometric toolpaths for all operations in the plan."""
    tool_map = {t.id: t for t in tools_db.tools}
    feat_holes = {h.id: h for h in features.holes}
    feat_pockets = {p.id: p for p in features.pockets}
    feat_slots = {s.id: s for s in features.slots}

    toolpath_ops: List[ToolpathOperation] = []
    total_move_count = 0

    clearance_z = config.thresholds.safe_clearance_z_mm
    z_top = part_bbox.z_max

    for setup in plan.optimized_plan.setups:
        for op in setup.operations:
            tool = tool_map.get(op.tool_id)
            tool_diam = tool.diameter_mm if tool else 10.0
            moves: List[ToolpathMove] = []

            if op.operation_type == "facing":
                moves = generate_facing_toolpath_moves(
                    x_min=part_bbox.x_min, x_max=part_bbox.x_max,
                    y_min=part_bbox.y_min, y_max=part_bbox.y_max,
                    z_cut=z_top,
                    tool_diameter_mm=tool_diam,
                    feed_mm_min=op.feed_mm_min,
                    clearance_z=clearance_z
                )

            elif op.operation_type in ("drill", "peck_drill"):
                hole = feat_holes.get(op.feature_id) if op.feature_id else None
                center = hole.position if hole else Point3D(x=0.0, y=0.0, z=z_top)
                depth = hole.depth_mm if hole else op.cutting_depth_mm
                is_peck = (op.operation_type == "peck_drill")
                moves = generate_drilling_toolpath_moves(
                    center=center,
                    depth_mm=depth,
                    z_top=z_top,
                    feed_mm_min=op.feed_mm_min,
                    clearance_z=clearance_z,
                    is_peck=is_peck
                )

            elif op.operation_type in ("pocket_roughing", "pocket_finishing"):
                pocket = feat_pockets.get(op.feature_id) if op.feature_id else None
                if pocket:
                    # Approximate 2D bounding outline centered at origin or floor
                    half_l = pocket.length_mm * 0.5
                    half_w = pocket.width_mm * 0.5
                    corners = [
                        (-half_l, -half_w),
                        (half_l, -half_w),
                        (half_l, half_w),
                        (-half_l, half_w),
                        (-half_l, -half_w)
                    ]
                    moves = generate_pocket_clearing_moves(
                        corners_2d=corners,
                        z_top=z_top,
                        depth_mm=pocket.depth_mm,
                        tool_diameter_mm=tool_diam,
                        feed_mm_min=op.feed_mm_min,
                        stepdown_mm=config.thresholds.default_stepdown_fraction * tool_diam,
                        stepover_frac=config.thresholds.default_stepover_fraction,
                        clearance_z=clearance_z
                    )

            elif op.operation_type == "slot_milling":
                slot = feat_slots.get(op.feature_id) if op.feature_id else None
                if slot:
                    half_l = slot.length_mm * 0.5
                    # Centerline pass along X
                    p_start = Point3D(x=-half_l, y=0.0, z=z_top - slot.depth_mm)
                    p_end = Point3D(x=half_l, y=0.0, z=z_top - slot.depth_mm)
                    p_safe = Point3D(x=-half_l, y=0.0, z=z_top + clearance_z)
                    p_safe_end = Point3D(x=half_l, y=0.0, z=z_top + clearance_z)

                    moves.append(ToolpathMove(
                        move_type=MoveType.PLUNGE,
                        start=p_safe, end=p_start,
                        feed_mm_min=op.plunge_feed_mm_min,
                        length_mm=round(slot.depth_mm + clearance_z, 2)
                    ))
                    moves.append(ToolpathMove(
                        move_type=MoveType.CUT,
                        start=p_start, end=p_end,
                        feed_mm_min=op.feed_mm_min,
                        length_mm=round(slot.length_mm, 2)
                    ))
                    moves.append(ToolpathMove(
                        move_type=MoveType.RETRACT,
                        start=p_end, end=p_safe_end,
                        feed_mm_min=10000.0,
                        length_mm=round(slot.depth_mm + clearance_z, 2)
                    ))

            total_len = sum(m.length_mm for m in moves)
            total_move_count += len(moves)

            toolpath_ops.append(ToolpathOperation(
                operation_id=op.id,
                feature_id=op.feature_id,
                setup_id=op.setup_id,
                tool_id=op.tool_id,
                tool_name=op.tool_name,
                spindle_rpm=op.spindle_rpm,
                total_length_mm=round(total_len, 2),
                moves=moves
            ))

    return ToolpathsCollection(
        schema_version="1.0.0",
        total_operations=len(toolpath_ops),
        total_moves=total_move_count,
        operations=toolpath_ops
    )
