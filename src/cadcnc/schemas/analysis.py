"""Schemas for manufacturability analysis, DFM findings, and accessibility."""

from typing import List, Optional
from pydantic import BaseModel, Field
from cadcnc.schemas.common import FindingKind, Severity

class FindingItem(BaseModel):
    id: str
    category: str
    severity: Severity  # green, yellow, red
    kind: FindingKind   # confirmed_geometry, suspected_issue
    feature_id: Optional[str] = None
    explanation: str
    how_to_resolve: str

class ManufacturabilityReport(BaseModel):
    schema_version: str = "1.0.0"
    overall_score: float  # 0 to 100
    score_formula: str
    findings: List[FindingItem] = Field(default_factory=list)
    green_count: int = 0
    yellow_count: int = 0
    red_count: int = 0
    accessible_setups_count: int = 1
