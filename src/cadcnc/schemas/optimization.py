"""Schemas for tool selection, operation sequencing, time estimation, and before/after comparison."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class ToolCandidate(BaseModel):
    tool_id: str
    tool_name: str
    tool_diameter_mm: float
    score: float
    check_reasons: List[str]
    penalty_reasons: List[str]

class RejectedTool(BaseModel):
    tool_id: str
    tool_name: str
    reasons: List[str]

class FeatureToolRecommendation(BaseModel):
    feature_id: str
    feature_type: str
    selected_tool_id: Optional[str] = None
    ranked_candidates: List[ToolCandidate] = Field(default_factory=list)
    rejected_candidates: List[RejectedTool] = Field(default_factory=list)

class ToolRecommendationsReport(BaseModel):
    schema_version: str = "1.0.0"
    recommendations: List[FeatureToolRecommendation] = Field(default_factory=list)

class OperationItem(BaseModel):
    id: str
    operation_type: str  # facing, spot_drill, drill, peck_drill, pocket_roughing, pocket_finishing, slot_milling
    feature_id: Optional[str] = None
    setup_id: str = "setup_1"
    tool_id: str
    tool_name: str
    spindle_rpm: float
    feed_mm_min: float
    plunge_feed_mm_min: float
    cutting_depth_mm: float
    estimated_cut_time_s: float
    estimated_rapid_time_s: float
    estimated_total_time_s: float
    precedence_dependencies: List[str] = Field(default_factory=list)

class SetupPlan(BaseModel):
    setup_id: str
    orientation: List[float]  # e.g. [0, 0, 1]
    operations: List[OperationItem] = Field(default_factory=list)
    setup_time_s: float = 300.0

class PlanVariant(BaseModel):
    name: str  # baseline or optimized
    setups: List[SetupPlan] = Field(default_factory=list)
    total_operations: int
    total_tool_changes: int
    total_setup_changes: int
    estimated_machining_time_s: float
    estimated_rapid_time_s: float
    estimated_tool_change_time_s: float
    estimated_setup_change_time_s: float
    estimated_total_cycle_time_s: float
    rapid_travel_distance_mm: float

class MachiningPlan(BaseModel):
    schema_version: str = "1.0.0"
    baseline_plan: PlanVariant
    optimized_plan: PlanVariant

class ComparisonMetrics(BaseModel):
    machining_time_s: float
    rapid_travel_distance_mm: float
    rapid_travel_time_s: float
    tool_changes_count: int
    setup_changes_count: int
    total_estimated_cycle_time_s: float

class ComparisonDifference(BaseModel):
    absolute_difference: float
    percentage_difference: float
    improvement: bool

class ComparisonReport(BaseModel):
    schema_version: str = "1.0.0"
    disclaimer: str = "Estimated / simulation-based values"
    baseline: ComparisonMetrics
    optimized: ComparisonMetrics
    time_savings: ComparisonDifference
    rapid_distance_savings: ComparisonDifference
    tool_change_savings: ComparisonDifference
    stock_volume_mm3: float
    part_volume_mm3: float
    removed_volume_mm3: float
    stock_utilization_percent: float
    waste_reduction_percent: float
    formulas_and_assumptions: List[str] = Field(default_factory=list)
