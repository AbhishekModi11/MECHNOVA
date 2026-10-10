"""Automated test suite for Milestone M5: Operation Planning, 2-Opt TSP, Time Estimation, and Comparison."""

from pathlib import Path
import pytest

from cadcnc.engine import Engine
from cadcnc.optimization.time_estimator import (
    estimate_linear_move_time_s, estimate_rapid_move_time_s, estimate_tool_change_time_s
)
from cadcnc.optimization.sequencing import solve_tsp_2opt, compute_tour_length
from cadcnc.schemas.optimization import MachiningPlan, ComparisonReport

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_models"

def test_time_estimator_math():
    # 100mm move at 1000mm/min feed takes 6.0 seconds
    assert pytest.approx(estimate_linear_move_time_s(100.0, 1000.0), rel=1e-3) == 6.0
    # 500mm rapid at 10000mm/min takes 3.0 seconds
    assert pytest.approx(estimate_rapid_move_time_s(500.0, 10000.0), rel=1e-3) == 3.0
    # 3 tool changes at 8s each = 24s
    assert estimate_tool_change_time_s(3, 8.0) == 24.0

def test_2opt_tsp_reduces_distance():
    # 4 points arranged in a zig-zag that is suboptimal
    pts = [(0.0, 0.0), (100.0, 100.0), (0.0, 100.0), (100.0, 0.0)]
    initial_order = [0, 1, 2, 3]
    initial_dist = compute_tour_length(pts, initial_order)

    best_order = solve_tsp_2opt(pts)
    optimized_dist = compute_tour_length(pts, best_order)

    assert optimized_dist <= initial_dist

def test_engine_plan_and_comparison(tmp_path):
    engine = Engine()
    step_file = SAMPLE_DIR / "bracket_demo.step"
    plan, comp = engine.plan(step_file, tmp_path)

    assert isinstance(plan, MachiningPlan)
    assert isinstance(comp, ComparisonReport)

    assert plan.baseline_plan.total_operations >= 5
    assert plan.optimized_plan.total_operations >= 5

    # 2-Opt and tool grouping should yield equal or shorter rapid distance
    assert comp.optimized.rapid_travel_distance_mm <= comp.baseline.rapid_travel_distance_mm
    assert comp.rapid_distance_savings.improvement is True

    # Stock utilization must be mathematically valid between 0% and 100%
    assert 0.0 < comp.stock_utilization_percent < 100.0
    assert comp.disclaimer == "Estimated / simulation-based values"
    assert (tmp_path / "operation_plan.json").exists()
    assert (tmp_path / "comparison.json").exists()
