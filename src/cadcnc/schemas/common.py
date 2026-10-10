"""Common geometric, status, and identifier schemas for cadcnc."""

from enum import Enum
from typing import List, Tuple
from pydantic import BaseModel, Field

class SchemaBase(BaseModel):
    """Base schema enforcing strict validation and serializability."""
    pass

class Point3D(BaseModel):
    x: float
    y: float
    z: float

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

class Vector3D(BaseModel):
    x: float
    y: float
    z: float

    def to_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

class BoundingBox3D(BaseModel):
    x_min: float
    x_max: float
    y_min: float
    y_max: float
    z_min: float
    z_max: float
    dx: float
    dy: float
    dz: float

class StatusType(str, Enum):
    CONFIRMED = "confirmed"
    UNCERTAIN = "uncertain"

class FindingKind(str, Enum):
    CONFIRMED_GEOMETRY = "confirmed_geometry"
    SUSPECTED_ISSUE = "suspected_issue"

class Severity(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"
