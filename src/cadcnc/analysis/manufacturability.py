"""Manufacturability analysis and DFM evaluation engine."""

from typing import List, Optional
from cadcnc.schemas.common import FindingKind, Severity
from cadcnc.schemas.cad import ModelSummary
from cadcnc.schemas.features import FeaturesCollection
from cadcnc.schemas.config import ThresholdsConfig, MachineConfig
from cadcnc.schemas.optimization import ToolRecommendationsReport
from cadcnc.schemas.analysis import FindingItem, ManufacturabilityReport
from cadcnc.analysis.accessibility import analyze_feature_accessibility

def evaluate_manufacturability(
    summary: ModelSummary,
    features: FeaturesCollection,
    recommendations: ToolRecommendationsReport,
    thresholds_config: ThresholdsConfig,
    machine_config: MachineConfig
) -> ManufacturabilityReport:
    """Analyzes DFM manufacturability rules, compiles findings, and computes DFM score."""
    findings: List[FindingItem] = []
    finding_id = 1

    access_map = analyze_feature_accessibility(features, machine_config)
    tool_map = {rec.feature_id: rec for rec in recommendations.recommendations}

    # 1. Accessibility Checks
    for feat_id, (is_acc, setup_id, ori) in access_map.items():
        if not is_acc:
            findings.append(FindingItem(
                id=f"finding_{finding_id}",
                category="accessibility",
                severity=Severity.RED,
                kind=FindingKind.CONFIRMED_GEOMETRY,
                feature_id=feat_id,
                explanation=f"Feature '{feat_id}' cannot be accessed along any allowed machine setup orientation {machine_config.machine.allowed_setup_orientations}.",
                how_to_resolve="Reorient feature geometry or enable 3+2 indexing / multi-axis machining."
            ))
            finding_id += 1

    # 2. Tool Availability & Diameter Checks
    for rec in recommendations.recommendations:
        if rec.selected_tool_id is None:
            findings.append(FindingItem(
                id=f"finding_{finding_id}",
                category="tool_availability",
                severity=Severity.RED,
                kind=FindingKind.SUSPECTED_ISSUE,
                feature_id=rec.feature_id,
                explanation=f"No compatible cutting tool found in tool library for feature '{rec.feature_id}' ({rec.feature_type}).",
                how_to_resolve="Add a matching cutter/drill with appropriate diameter and reach to tools library JSON."
            ))
            finding_id += 1

    # 3. Hole Depth-to-Diameter (L/D) Ratio Checks
    for hole in features.holes:
        ld_ratio = hole.depth_mm / max(hole.diameter_mm, 0.001)
        if ld_ratio > 5.0:
            findings.append(FindingItem(
                id=f"finding_{finding_id}",
                category="tool_reach_limitation",
                severity=Severity.YELLOW,
                kind=FindingKind.SUSPECTED_ISSUE,
                feature_id=hole.id,
                explanation=f"Hole '{hole.id}' has depth-to-diameter ratio {ld_ratio:.1f}x > 5.0x, risking chip packing, runout, or tool breakage.",
                how_to_resolve="Implement peck drilling (G83) with through-spindle coolant or use parabolic flute drill."
            ))
            finding_id += 1

    # 4. Sharp Internal Corners
    for corner in features.internal_corners:
        if corner.type == "sharp":
            findings.append(FindingItem(
                id=f"finding_{finding_id}",
                category="sharp_internal_corner",
                severity=Severity.YELLOW,
                kind=FindingKind.CONFIRMED_GEOMETRY,
                feature_id=corner.id,
                explanation=f"Internal corner '{corner.id}' has a sharp zero-radius concave vertical edge. Rotary milling tools cannot produce a sharp inside corner.",
                how_to_resolve="Add a corner fillet radius (R >= 1.5mm) or introduce a dogbone/undercut relief feature."
            ))
            finding_id += 1

    # 5. Thin Walls
    for wall in features.thin_walls:
        findings.append(FindingItem(
            id=f"finding_{finding_id}",
            category="thin_wall",
            severity=Severity.YELLOW,
            kind=FindingKind.SUSPECTED_ISSUE,
            feature_id=wall.id,
            explanation=f"Thin wall '{wall.id}' thickness ({wall.thickness_mm}mm) is below configured minimum threshold ({wall.min_allowed_thickness_mm}mm), risking vibration chatter or deflection.",
            how_to_resolve="Increase nominal wall thickness >= 1.5mm or apply reduced depth-of-cut finishing passes."
        ))
        finding_id += 1

    # 6. B-Spline Freeform Geometry Outside MVP
    if summary.face_counts_by_surface_type.b_spline > 0:
        findings.append(FindingItem(
            id=f"finding_{finding_id}",
            category="freeform_geometry",
            severity=Severity.YELLOW,
            kind=FindingKind.CONFIRMED_GEOMETRY,
            feature_id=None,
            explanation=f"Model contains {summary.face_counts_by_surface_type.b_spline} B-Spline surface faces requiring 3D surface machining (outside 2.5D prismatic scope).",
            how_to_resolve="Use 3D ball-nose surface contouring or convert planar sections."
        ))
        finding_id += 1

    # Count findings by severity
    green_cnt = 0
    yellow_cnt = sum(1 for f in findings if f.severity == Severity.YELLOW)
    red_cnt = sum(1 for f in findings if f.severity == Severity.RED)

    # Positive findings for confirmed features that pass
    for hole in features.holes:
        if hole.id in tool_map and tool_map[hole.id].selected_tool_id and access_map.get(hole.id, (False,))[0]:
            green_cnt += 1
    for pocket in features.pockets:
        if pocket.id in tool_map and tool_map[pocket.id].selected_tool_id and access_map.get(pocket.id, (False,))[0]:
            green_cnt += 1

    # Calculate overall manufacturability score (0 to 100)
    score_penalty = (red_cnt * 25.0) + (yellow_cnt * 5.0)
    overall_score = max(0.0, min(100.0, 100.0 - score_penalty))
    formula_str = "Score = max(0.0, 100.0 - 25.0 * N_red - 5.0 * N_yellow)"

    # Count distinct setups
    accessible_setups = set(ori[1] for ori in access_map.values() if ori[0])
    setups_cnt = max(1, len(accessible_setups))

    return ManufacturabilityReport(
        schema_version="1.0.0",
        overall_score=round(overall_score, 1),
        score_formula=formula_str,
        findings=findings,
        green_count=green_cnt,
        yellow_count=yellow_cnt,
        red_count=red_cnt,
        accessible_setups_count=setups_cnt
    )
