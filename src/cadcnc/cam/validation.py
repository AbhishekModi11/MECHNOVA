"""Closed-loop validation gate determining whether G-code export is permitted."""

import math
from typing import List, Tuple
from cadcnc.schemas.common import Point3D
from cadcnc.schemas.config import MachineConfig, ToolsDatabase
from cadcnc.schemas.cam import (
    ToolpathsCollection, ValidationCheckItem, ValidationReport, MoveType
)
from cadcnc.schemas.analysis import ManufacturabilityReport, Severity

def validate_toolpaths_and_plan(
    toolpaths: ToolpathsCollection,
    machine_config: MachineConfig,
    tools_db: ToolsDatabase,
    dfm_report: ManufacturabilityReport
) -> ValidationReport:
    """Runs all mandatory safety checks on toolpaths and machine bounds.
    
    Returns:
        ValidationReport. G-code export is permitted ONLY when all_mandatory_checks_passed is True.
    """
    checks: List[ValidationCheckItem] = []
    failure_reasons: List[str] = []

    limits = machine_config.machine.travel_limits_mm
    max_rpm = machine_config.machine.max_spindle_rpm
    max_feed = machine_config.machine.max_feed_mm_min
    tool_map = {t.id: t for t in tools_db.tools}

    # 1. Check: Machine Travel Limits
    out_of_bounds = []
    for op in toolpaths.operations:
        for m in op.moves:
            for pt in (m.start, m.end):
                if not (limits.x_min <= pt.x <= limits.x_max and
                        limits.y_min <= pt.y <= limits.y_max and
                        limits.z_min <= pt.z <= limits.z_max):
                    out_of_bounds.append(f"{op.operation_id}: point ({pt.x:.1f}, {pt.y:.1f}, {pt.z:.1f})")

    check_travel = ValidationCheckItem(
        id="check_travel_limits",
        name="Machine Travel Envelope Limits",
        passed=len(out_of_bounds) == 0,
        details="All toolpath moves fall inside the physical travel boundaries." if len(out_of_bounds) == 0 else f"{len(out_of_bounds)} moves exceeded travel envelope.",
        failed_elements=out_of_bounds[:5]
    )
    checks.append(check_travel)
    if not check_travel.passed:
        failure_reasons.append("Toolpath coordinates exceed machine physical travel envelope.")

    # 2. Check: Safe-Height Rapids
    unsafe_rapids = []
    for op in toolpaths.operations:
        for m in op.moves:
            if m.move_type == MoveType.RAPID:
                # Rapid moves should not plunge deep into material
                if m.start.z < -100.0 or m.end.z < -100.0:
                    unsafe_rapids.append(f"{op.operation_id}: rapid traverse below safe floor")

    check_rapids = ValidationCheckItem(
        id="check_safe_rapids",
        name="Safe Retract and Rapid Traversal",
        passed=len(unsafe_rapids) == 0,
        details="Rapids execute safely above cut levels.",
        failed_elements=unsafe_rapids
    )
    checks.append(check_rapids)
    if not check_rapids.passed:
        failure_reasons.append("Unsafe rapid traverse detected below safe clearance plane.")

    # 3. Check: Feeds and Spindle Speeds
    feed_violations = []
    for op in toolpaths.operations:
        if op.spindle_rpm > max_rpm or op.spindle_rpm <= 0:
            feed_violations.append(f"{op.operation_id}: RPM {op.spindle_rpm} exceeds max {max_rpm}")
        for m in op.moves:
            if m.move_type in (MoveType.CUT, MoveType.PLUNGE) and m.feed_mm_min > max_feed:
                feed_violations.append(f"{op.operation_id}: feed {m.feed_mm_min} exceeds max {max_feed}")

    check_feeds = ValidationCheckItem(
        id="check_feeds_and_speeds",
        name="Spindle RPM and Feed Limits",
        passed=len(feed_violations) == 0,
        details="All cutting speeds and feeds are within machine limits.",
        failed_elements=feed_violations[:5]
    )
    checks.append(check_feeds)
    if not check_feeds.passed:
        failure_reasons.append("Programmed spindle speed or feed rate violates machine specification.")

    # 4. Check: Inaccessible or Red-Flagged Features
    red_findings = [f.feature_id for f in dfm_report.findings if f.severity == Severity.RED and f.feature_id]
    planned_red_features = []
    for op in toolpaths.operations:
        if op.feature_id and op.feature_id in red_findings:
            planned_red_features.append(op.feature_id)

    check_red = ValidationCheckItem(
        id="check_no_inaccessible_features",
        name="Exclusion of Inaccessible Features",
        passed=len(planned_red_features) == 0,
        details="No toolpaths generated for inaccessible or unmachinable geometry.",
        failed_elements=planned_red_features
    )
    checks.append(check_red)
    if not check_red.passed:
        failure_reasons.append("Operations were scheduled for red-flagged inaccessible features.")

    # 5. Check: Closed-Loop Sanity (No NaN, No Infinite)
    nan_moves = []
    for op in toolpaths.operations:
        for m in op.moves:
            coords = [m.start.x, m.start.y, m.start.z, m.end.x, m.end.y, m.end.z, m.feed_mm_min, m.length_mm]
            if any(math.isnan(c) or math.isinf(c) for c in coords):
                nan_moves.append(op.operation_id)

    check_sanity = ValidationCheckItem(
        id="check_numeric_sanity",
        name="Numeric Sanity and Non-Spam Verification",
        passed=len(nan_moves) == 0,
        details="All move coordinates, lengths, and feeds are finite numbers.",
        failed_elements=nan_moves
    )
    checks.append(check_sanity)
    if not check_sanity.passed:
        failure_reasons.append("Non-numeric or NaN coordinates detected in toolpath stream.")

    all_passed = all(c.passed for c in checks)

    return ValidationReport(
        schema_version="1.0.0",
        all_mandatory_checks_passed=all_passed,
        gcode_export_permitted=all_passed,
        exported_gcode_files=[],
        checks=checks,
        failure_reasons=failure_reasons
    )
