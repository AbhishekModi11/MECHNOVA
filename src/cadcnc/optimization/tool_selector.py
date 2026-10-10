"""Tool selection orchestrator querying the tool database and producing ranked recommendations."""

import json
from pathlib import Path
from typing import Dict, List, Optional

from cadcnc.schemas.config import ToolsDatabase, ToolItem
from cadcnc.schemas.features import FeaturesCollection
from cadcnc.schemas.optimization import (
    ToolRecommendationsReport, FeatureToolRecommendation, ToolCandidate, RejectedTool
)
from cadcnc.optimization.scoring import (
    score_tool_for_hole, score_tool_for_pocket, score_tool_for_slot, score_tool_for_facing
)

def load_tool_database(tools_path: Path | str) -> ToolsDatabase:
    """Loads and validates tool database JSON."""
    p = Path(tools_path).resolve()
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return ToolsDatabase.model_validate(data)

def select_tools_for_features(
    features: FeaturesCollection,
    tools_db: ToolsDatabase,
    material_id: str = "aluminum_6061"
) -> ToolRecommendationsReport:
    """Queries tool library, evaluates all candidates, and ranks tools per feature."""
    recommendations: List[FeatureToolRecommendation] = []

    # 1. Holes
    for hole in features.holes:
        candidates: List[ToolCandidate] = []
        rejected: List[RejectedTool] = []
        for tool in tools_db.tools:
            cand, rej = score_tool_for_hole(tool, hole, material_id)
            if cand:
                candidates.append(cand)
            if rej:
                rejected.append(rej)

        candidates.sort(key=lambda c: c.score, reverse=True)
        selected_id = candidates[0].tool_id if candidates else None

        recommendations.append(FeatureToolRecommendation(
            feature_id=hole.id,
            feature_type=f"hole_{hole.type}",
            selected_tool_id=selected_id,
            ranked_candidates=candidates,
            rejected_candidates=rejected
        ))

    # 2. Pockets
    for pocket in features.pockets:
        candidates: List[ToolCandidate] = []
        rejected: List[RejectedTool] = []
        for tool in tools_db.tools:
            cand, rej = score_tool_for_pocket(tool, pocket, material_id)
            if cand:
                candidates.append(cand)
            if rej:
                rejected.append(rej)

        candidates.sort(key=lambda c: c.score, reverse=True)
        selected_id = candidates[0].tool_id if candidates else None

        recommendations.append(FeatureToolRecommendation(
            feature_id=pocket.id,
            feature_type=f"pocket_{pocket.type}",
            selected_tool_id=selected_id,
            ranked_candidates=candidates,
            rejected_candidates=rejected
        ))

    # 3. Slots
    for slot in features.slots:
        candidates: List[ToolCandidate] = []
        rejected: List[RejectedTool] = []
        for tool in tools_db.tools:
            cand, rej = score_tool_for_slot(tool, slot, material_id)
            if cand:
                candidates.append(cand)
            if rej:
                rejected.append(rej)

        candidates.sort(key=lambda c: c.score, reverse=True)
        selected_id = candidates[0].tool_id if candidates else None

        recommendations.append(FeatureToolRecommendation(
            feature_id=slot.id,
            feature_type=f"slot_{slot.type}",
            selected_tool_id=selected_id,
            ranked_candidates=candidates,
            rejected_candidates=rejected
        ))

    # 4. Top planar face for facing
    top_faces = [pf for pf in features.planar_faces if pf.is_top_candidate]
    if top_faces:
        top_face = top_faces[0]
        candidates = []
        rejected = []
        for tool in tools_db.tools:
            cand, rej = score_tool_for_facing(tool, top_face, material_id)
            if cand:
                candidates.append(cand)
            if rej:
                rejected.append(rej)

        candidates.sort(key=lambda c: c.score, reverse=True)
        selected_id = candidates[0].tool_id if candidates else None

        recommendations.append(FeatureToolRecommendation(
            feature_id=top_face.face_id,
            feature_type="planar_top_facing",
            selected_tool_id=selected_id,
            ranked_candidates=candidates,
            rejected_candidates=rejected
        ))

    return ToolRecommendationsReport(
        schema_version="1.0.0",
        recommendations=recommendations
    )
