"""Schemas for detected CAD manufacturing features."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from cadcnc.schemas.common import Point3D, Vector3D, StatusType

class HoleFeature(BaseModel):
    id: str
    type: str  # through, blind, counterbore, countersink
    diameter_mm: float
    depth_mm: float
    axis: Vector3D
    position: Point3D
    opening_face_id: Optional[str] = None
    face_ids: List[str]
    point_angle_deg: Optional[float] = None
    counterbore_diameter_mm: Optional[float] = None
    counterbore_depth_mm: Optional[float] = None
    countersink_angle_deg: Optional[float] = None
    accessible: bool = True
    confidence: float
    confidence_basis: List[str]
    status: StatusType

class PocketFeature(BaseModel):
    id: str
    type: str  # closed, open, through
    length_mm: float
    width_mm: float
    depth_mm: float
    floor_face_id: str
    wall_face_ids: List[str]
    corner_radii_mm: List[float] = Field(default_factory=list)
    islands_count: int = 0
    floor_normal: Vector3D
    accessible: bool = True
    confidence: float
    confidence_basis: List[str]
    status: StatusType

class SlotFeature(BaseModel):
    id: str
    type: str  # closed, open_ended, through
    width_mm: float
    length_mm: float
    depth_mm: float
    end_shape: str = "straight"  # straight, rounded
    floor_face_id: Optional[str] = None
    wall_face_ids: List[str] = Field(default_factory=list)
    aspect_ratio: float
    accessible: bool = True
    confidence: float
    confidence_basis: List[str]
    status: StatusType

class CornerFeature(BaseModel):
    id: str
    type: str  # sharp, filleted
    pocket_or_slot_id: Optional[str] = None
    radius_mm: Optional[float] = None  # None for sharp
    edge_ids: List[str] = Field(default_factory=list)
    wall_face_ids: List[str] = Field(default_factory=list)
    min_tool_diameter_needed_mm: float
    accessible: bool = True
    confidence: float
    confidence_basis: List[str]
    status: StatusType

class ThinWallFeature(BaseModel):
    id: str
    thickness_mm: float
    face_id_1: str
    face_id_2: str
    min_allowed_thickness_mm: float
    confidence: float
    confidence_basis: List[str]
    status: StatusType

class PlanarFaceFeature(BaseModel):
    face_id: str
    normal: Vector3D
    area_mm2: float
    is_top_candidate: bool = False
    center: Point3D

class FeaturesCollection(BaseModel):
    schema_version: str = "1.0.0"
    holes: List[HoleFeature] = Field(default_factory=list)
    pockets: List[PocketFeature] = Field(default_factory=list)
    slots: List[SlotFeature] = Field(default_factory=list)
    internal_corners: List[CornerFeature] = Field(default_factory=list)
    thin_walls: List[ThinWallFeature] = Field(default_factory=list)
    planar_faces: List[PlanarFaceFeature] = Field(default_factory=list)

class FeatureMap(BaseModel):
    schema_version: str = "1.0.0"
    face_to_features: Dict[str, List[str]] = Field(default_factory=dict)
