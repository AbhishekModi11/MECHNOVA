"""Schemas for CAD summary and B-Rep metadata."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from cadcnc.schemas.common import BoundingBox3D, Point3D, Vector3D

class SurfaceCounts(BaseModel):
    plane: int = 0
    cylinder: int = 0
    cone: int = 0
    sphere: int = 0
    torus: int = 0
    b_spline: int = 0
    other: int = 0

class ModelSummary(BaseModel):
    schema_version: str = "1.0.0"
    filename: str
    size_bytes: int
    unit: str = "mm"
    solids_count: int
    shells_count: int
    faces_count: int
    edges_count: int
    vertices_count: int
    bounding_box: BoundingBox3D
    volume_mm3: float
    surface_area_mm2: float
    face_counts_by_surface_type: SurfaceCounts
    load_time_s: float
    analysis_time_s: float
