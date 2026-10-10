"""Schemas for CAM toolpaths and validation reports."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from cadcnc.schemas.common import Point3D

class MoveType(str, Enum):
    RAPID = "rapid"
    CUT = "cut"
    PLUNGE = "plunge"
    RETRACT = "retract"

class ToolpathMove(BaseModel):
    move_type: MoveType
    start: Point3D
    end: Point3D
    feed_mm_min: float
    length_mm: float

class ToolpathOperation(BaseModel):
    operation_id: str
    feature_id: Optional[str] = None
    setup_id: str
    tool_id: str
    tool_name: str
    spindle_rpm: float
    total_length_mm: float
    moves: List[ToolpathMove] = Field(default_factory=list)

class ToolpathsCollection(BaseModel):
    schema_version: str = "1.0.0"
    total_operations: int
    total_moves: int
    operations: List[ToolpathOperation] = Field(default_factory=list)

class ValidationCheckItem(BaseModel):
    id: str
    name: str
    passed: bool
    details: str
    failed_elements: List[str] = Field(default_factory=list)

class ValidationReport(BaseModel):
    schema_version: str = "1.0.0"
    all_mandatory_checks_passed: bool
    gcode_export_permitted: bool
    exported_gcode_files: List[str] = Field(default_factory=list)
    checks: List[ValidationCheckItem] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)
