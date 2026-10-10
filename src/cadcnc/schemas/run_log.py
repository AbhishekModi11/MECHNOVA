"""Schemas for run logs, execution timings, and environment provenance."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field

class StageTiming(BaseModel):
    stage_name: str
    duration_s: float

class RunLog(BaseModel):
    schema_version: str = "1.0.0"
    model_path: str
    material_id: str
    machine_id: str
    total_duration_s: float
    stage_timings: List[StageTiming] = Field(default_factory=list)
    feature_counts: Dict[str, int] = Field(default_factory=dict)
    library_versions: Dict[str, str] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    success: bool = True
