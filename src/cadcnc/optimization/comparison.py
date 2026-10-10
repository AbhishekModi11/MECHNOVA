"""Plan comparison and savings calculation engine."""

from typing import List
from cadcnc.schemas.optimization import (
    MachiningPlan, ComparisonMetrics, ComparisonDifference, ComparisonReport
)
from cadcnc.optimization.waste_estimator import StockEstimationResult

def generate_comparison_report(
    plan: MachiningPlan,
    stock_res: StockEstimationResult
) -> ComparisonReport:
    """Calculates before-and-after savings percentages and formats comparison.json."""
    base = plan.baseline_plan
    opt = plan.optimized_plan

    base_metrics = ComparisonMetrics(
        machining_time_s=base.estimated_machining_time_s,
        rapid_travel_distance_mm=base.rapid_travel_distance_mm,
        rapid_travel_time_s=base.estimated_rapid_time_s,
        tool_changes_count=base.total_tool_changes,
        setup_changes_count=base.total_setup_changes,
        total_estimated_cycle_time_s=base.estimated_total_cycle_time_s
    )

    opt_metrics = ComparisonMetrics(
        machining_time_s=opt.estimated_machining_time_s,
        rapid_travel_distance_mm=opt.rapid_travel_distance_mm,
        rapid_travel_time_s=opt.estimated_rapid_time_s,
        tool_changes_count=opt.total_tool_changes,
        setup_changes_count=opt.total_setup_changes,
        total_estimated_cycle_time_s=opt.estimated_total_cycle_time_s
    )

    # Time savings
    time_abs = max(0.0, base.estimated_total_cycle_time_s - opt.estimated_total_cycle_time_s)
    time_pct = (time_abs / max(base.estimated_total_cycle_time_s, 0.001)) * 100.0

    # Rapid distance savings
    dist_abs = max(0.0, base.rapid_travel_distance_mm - opt.rapid_travel_distance_mm)
    dist_pct = (dist_abs / max(base.rapid_travel_distance_mm, 0.001)) * 100.0

    # Tool changes savings
    tc_abs = max(0, base.total_tool_changes - opt.total_tool_changes)
    tc_pct = (tc_abs / max(base.total_tool_changes, 1)) * 100.0

    assumptions = [
        "Cutting time = sum(move_distance / cutting_feed * 60)",
        "Rapid traverse time = rapid_distance / machine_rapid_rate * 60",
        "Automatic Tool Change (ATC) time = tool_changes * machine_tc_time_s (8.0s)",
        "Setup fixture time = setup_changes * machine_setup_time_s (300.0s)",
        "2-Opt TSP optimization applied to XY feature coordinates within identical tool operations",
        "Raw stock bounding box based on part bounding box plus configured allowances"
    ]

    return ComparisonReport(
        schema_version="1.0.0",
        disclaimer="Estimated / simulation-based values",
        baseline=base_metrics,
        optimized=opt_metrics,
        time_savings=ComparisonDifference(
            absolute_difference=round(time_abs, 2),
            percentage_difference=round(time_pct, 1),
            improvement=time_abs > 0.0
        ),
        rapid_distance_savings=ComparisonDifference(
            absolute_difference=round(dist_abs, 2),
            percentage_difference=round(dist_pct, 1),
            improvement=dist_abs > 0.0
        ),
        tool_change_savings=ComparisonDifference(
            absolute_difference=float(tc_abs),
            percentage_difference=round(tc_pct, 1),
            improvement=tc_abs > 0
        ),
        stock_volume_mm3=stock_res.stock_volume_mm3,
        part_volume_mm3=stock_res.part_volume_mm3,
        removed_volume_mm3=stock_res.removed_volume_mm3,
        stock_utilization_percent=stock_res.stock_utilization_percent,
        waste_reduction_percent=stock_res.waste_reduction_percent,
        formulas_and_assumptions=assumptions
    )
