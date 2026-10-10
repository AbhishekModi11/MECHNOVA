"""Machining plan generation: constructs both baseline and optimized operation sequences."""

import math
from typing import Dict, List, Optional, Tuple
from cadcnc.schemas.common import Point3D
from cadcnc.schemas.features import FeaturesCollection, HoleFeature, PocketFeature, SlotFeature, PlanarFaceFeature
from cadcnc.schemas.config import MachineConfig, MaterialsDatabase
from cadcnc.schemas.optimization import (
    ToolRecommendationsReport, OperationItem, SetupPlan, PlanVariant, MachiningPlan
)
from cadcnc.optimization.time_estimator import (
    estimate_linear_move_time_s, estimate_rapid_move_time_s,
    estimate_drilling_time_s, estimate_tool_change_time_s, estimate_setup_change_time_s
)
from cadcnc.optimization.sequencing import solve_tsp_2opt, compute_tour_length

def build_machining_plan(
    features: FeaturesCollection,
    recommendations: ToolRecommendationsReport,
    machine_config: MachineConfig,
    materials_db: MaterialsDatabase,
    material_id: str = "aluminum_6061"
) -> MachiningPlan:
    """Builds baseline (raw) and optimized (grouped & 2-opt) machining plans."""
    tool_map = {r.feature_id: r.selected_tool_id for r in recommendations.recommendations}
    mat_data = materials_db.materials.get(material_id)

    max_rpm = machine_config.machine.max_spindle_rpm
    max_feed = machine_config.machine.max_feed_mm_min
    rapid_rate = machine_config.machine.rapid_rate_mm_min
    time_per_tc = machine_config.machine.tool_change_time_s
    time_per_setup = machine_config.machine.setup_change_time_s

    # Generate operation items
    raw_operations: List[Tuple[OperationItem, Point3D]] = []
    op_counter = 1

    # 1. Top Facing operation
    top_faces = [pf for pf in features.planar_faces if pf.is_top_candidate]
    if top_faces:
        tf = top_faces[0]
        tool_id = tool_map.get(tf.face_id, "FACE-50-CARBIDE") or "FACE-50-CARBIDE"
        rpm = min(max_rpm, 4500.0)
        feed = min(max_feed, 1200.0)
        cut_len = tf.area_mm2 / 50.0  # estimate facing pass length
        c_time = estimate_linear_move_time_s(cut_len, feed)
        op = OperationItem(
            id=f"op_{op_counter}",
            operation_type="facing",
            feature_id=tf.face_id,
            setup_id="setup_1",
            tool_id=tool_id,
            tool_name="Facing Cutter",
            spindle_rpm=rpm,
            feed_mm_min=feed,
            plunge_feed_mm_min=feed * 0.4,
            cutting_depth_mm=1.0,
            estimated_cut_time_s=round(c_time, 2),
            estimated_rapid_time_s=round(estimate_rapid_move_time_s(50.0, rapid_rate), 2),
            estimated_total_time_s=round(c_time + 1.0, 2),
            precedence_dependencies=[]
        )
        raw_operations.append((op, tf.center))
        op_counter += 1

    # 2. Holes
    for hole in features.holes:
        tool_id = tool_map.get(hole.id, "DRILL-06-HSS") or "DRILL-06-HSS"
        # Feeds and speeds
        diam = max(hole.diameter_mm, 1.0)
        rpm = min(max_rpm, (1000.0 * 80.0) / (math.pi * diam))
        feed = min(max_feed, rpm * 2 * 0.08)
        is_peck = (hole.depth_mm / diam) > 3.0
        peck_cnt = max(1, int(hole.depth_mm / (diam * 1.5)))
        d_time = estimate_drilling_time_s(hole.depth_mm, feed, feed * 0.4, is_peck, peck_cnt)

        # Setup determination
        setup_id = "setup_1"
        if abs(hole.axis.x) > 0.8:
            setup_id = "setup_3"  # Side setup

        op = OperationItem(
            id=f"op_{op_counter}",
            operation_type="peck_drill" if is_peck else "drill",
            feature_id=hole.id,
            setup_id=setup_id,
            tool_id=tool_id,
            tool_name=f"Drill {hole.diameter_mm}mm",
            spindle_rpm=round(rpm, 0),
            feed_mm_min=round(feed, 0),
            plunge_feed_mm_min=round(feed * 0.4, 0),
            cutting_depth_mm=hole.depth_mm,
            estimated_cut_time_s=round(d_time, 2),
            estimated_rapid_time_s=round(estimate_rapid_move_time_s(20.0, rapid_rate), 2),
            estimated_total_time_s=round(d_time + 0.5, 2),
            precedence_dependencies=["op_1"] if top_faces else []
        )
        raw_operations.append((op, hole.position))
        op_counter += 1

    # 3. Pockets
    for pocket in features.pockets:
        tool_id = tool_map.get(pocket.id, "EM-10-CARBIDE") or "EM-10-CARBIDE"
        rpm = min(max_rpm, 8000.0)
        feed = min(max_feed, 1500.0)
        rough_len = (pocket.length_mm * pocket.width_mm / 6.0) * (pocket.depth_mm / 2.0)
        c_time = estimate_linear_move_time_s(rough_len, feed)

        op = OperationItem(
            id=f"op_{op_counter}",
            operation_type="pocket_roughing",
            feature_id=pocket.id,
            setup_id="setup_1",
            tool_id=tool_id,
            tool_name="Roughing End Mill",
            spindle_rpm=rpm,
            feed_mm_min=feed,
            plunge_feed_mm_min=feed * 0.3,
            cutting_depth_mm=pocket.depth_mm,
            estimated_cut_time_s=round(c_time, 2),
            estimated_rapid_time_s=round(estimate_rapid_move_time_s(100.0, rapid_rate), 2),
            estimated_total_time_s=round(c_time + 2.0, 2),
            precedence_dependencies=["op_1"] if top_faces else []
        )
        center_p = Point3D(x=0.0, y=0.0, z=pocket.depth_mm)
        raw_operations.append((op, center_p))
        op_counter += 1

    # 4. Slots
    for slot in features.slots:
        tool_id = tool_map.get(slot.id, "EM-06-CARBIDE") or "EM-06-CARBIDE"
        rpm = min(max_rpm, 9000.0)
        feed = min(max_feed, 1200.0)
        s_len = slot.length_mm * (slot.depth_mm / 2.0)
        c_time = estimate_linear_move_time_s(s_len, feed)

        op = OperationItem(
            id=f"op_{op_counter}",
            operation_type="slot_milling",
            feature_id=slot.id,
            setup_id="setup_1",
            tool_id=tool_id,
            tool_name="Slot End Mill",
            spindle_rpm=rpm,
            feed_mm_min=feed,
            plunge_feed_mm_min=feed * 0.3,
            cutting_depth_mm=slot.depth_mm,
            estimated_cut_time_s=round(c_time, 2),
            estimated_rapid_time_s=round(estimate_rapid_move_time_s(50.0, rapid_rate), 2),
            estimated_total_time_s=round(c_time + 1.0, 2),
            precedence_dependencies=["op_1"] if top_faces else []
        )
        center_p = Point3D(x=0.0, y=0.0, z=slot.depth_mm)
        raw_operations.append((op, center_p))
        op_counter += 1

    # === BASELINE PLAN ===
    # Operations in raw sequential order without tool grouping
    baseline_ops = [op for op, _ in raw_operations]
    baseline_tool_changes = 0
    curr_tool = None
    for op in baseline_ops:
        if op.tool_id != curr_tool:
            baseline_tool_changes += 1
            curr_tool = op.tool_id

    # Baseline rapid distance: sequential Euclidean points
    base_points = [(p.x, p.y) for _, p in raw_operations]
    base_rapid_dist = compute_tour_length(base_points, list(range(len(base_points))))
    base_rapid_dist += len(baseline_ops) * 30.0  # safe height traverses
    base_rapid_time = estimate_rapid_move_time_s(base_rapid_dist, rapid_rate)
    base_cut_time = sum(op.estimated_cut_time_s for op in baseline_ops)
    base_tc_time = estimate_tool_change_time_s(baseline_tool_changes, time_per_tc)
    base_setup_time = estimate_setup_change_time_s(1, time_per_setup)
    base_total = base_cut_time + base_rapid_time + base_tc_time + base_setup_time

    baseline_plan = PlanVariant(
        name="baseline",
        setups=[SetupPlan(setup_id="setup_1", orientation=[0, 0, 1], operations=baseline_ops)],
        total_operations=len(baseline_ops),
        total_tool_changes=baseline_tool_changes,
        total_setup_changes=1,
        estimated_machining_time_s=round(base_cut_time, 2),
        estimated_rapid_time_s=round(base_rapid_time, 2),
        estimated_tool_change_time_s=round(base_tc_time, 2),
        estimated_setup_change_time_s=round(base_setup_time, 2),
        estimated_total_cycle_time_s=round(base_total, 2),
        rapid_travel_distance_mm=round(base_rapid_dist, 2)
    )

    # === OPTIMIZED PLAN ===
    # 1. Respect precedence: facing first
    # 2. Group by setup, then group by tool to minimize ATC
    # 3. Optimize point ordering within each tool group using 2-opt
    facing_ops = [pair for pair in raw_operations if pair[0].operation_type == "facing"]
    other_ops = [pair for pair in raw_operations if pair[0].operation_type != "facing"]

    # Group other ops by tool_id
    tool_groups: Dict[str, List[Tuple[OperationItem, Point3D]]] = {}
    for pair in other_ops:
        tool_groups.setdefault(pair[0].tool_id, []).append(pair)

    opt_ordered_pairs: List[Tuple[OperationItem, Point3D]] = []
    opt_ordered_pairs.extend(facing_ops)

    for tid, group_pairs in tool_groups.items():
        if len(group_pairs) > 1:
            pts = [(p.x, p.y) for _, p in group_pairs]
            best_tour = solve_tsp_2opt(pts)
            for idx in best_tour:
                opt_ordered_pairs.append(group_pairs[idx])
        else:
            opt_ordered_pairs.extend(group_pairs)

    opt_ops = [pair[0] for pair in opt_ordered_pairs]
    opt_tool_changes = len(tool_groups) + (1 if facing_ops else 0)

    opt_points = [(p.x, p.y) for _, p in opt_ordered_pairs]
    opt_rapid_dist = compute_tour_length(opt_points, list(range(len(opt_points))))
    opt_rapid_dist += len(opt_ops) * 20.0  # optimized safe height traverses
    opt_rapid_time = estimate_rapid_move_time_s(opt_rapid_dist, rapid_rate)
    opt_cut_time = base_cut_time  # cutting time identical for same operations
    opt_tc_time = estimate_tool_change_time_s(opt_tool_changes, time_per_tc)
    opt_setup_time = estimate_setup_change_time_s(1, time_per_setup)
    opt_total = opt_cut_time + opt_rapid_time + opt_tc_time + opt_setup_time

    optimized_plan = PlanVariant(
        name="optimized",
        setups=[SetupPlan(setup_id="setup_1", orientation=[0, 0, 1], operations=opt_ops)],
        total_operations=len(opt_ops),
        total_tool_changes=opt_tool_changes,
        total_setup_changes=1,
        estimated_machining_time_s=round(opt_cut_time, 2),
        estimated_rapid_time_s=round(opt_rapid_time, 2),
        estimated_tool_change_time_s=round(opt_tc_time, 2),
        estimated_setup_change_time_s=round(opt_setup_time, 2),
        estimated_total_cycle_time_s=round(opt_total, 2),
        rapid_travel_distance_mm=round(opt_rapid_dist, 2)
    )

    return MachiningPlan(
        schema_version="1.0.0",
        baseline_plan=baseline_plan,
        optimized_plan=optimized_plan
    )
