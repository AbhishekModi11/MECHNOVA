"""Geometric measurement utilities for features, walls, and bounding contours."""

import math
from typing import Tuple, Optional
import numpy as np
from shapely.geometry import Polygon, MultiPolygon

from cadcnc.schemas.common import Point3D, Vector3D

def euclidean_distance_3d(p1: Point3D, p2: Point3D) -> float:
    """Computes Euclidean distance between two 3D points."""
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2 + (p1.z - p2.z)**2)

def are_vectors_parallel(v1: Vector3D, v2: Vector3D, tol_rad: float = 0.05) -> bool:
    """Checks if two 3D vectors are collinear (parallel or anti-parallel)."""
    norm1 = math.sqrt(v1.x**2 + v1.y**2 + v1.z**2)
    norm2 = math.sqrt(v2.x**2 + v2.y**2 + v2.z**2)
    if norm1 < 1e-7 or norm2 < 1e-7:
        return False
    dot = (v1.x * v2.x + v1.y * v2.y + v1.z * v2.z) / (norm1 * norm2)
    return abs(abs(dot) - 1.0) < tol_rad

def are_vectors_opposing(v1: Vector3D, v2: Vector3D, tol_rad: float = 0.05) -> bool:
    """Checks if two 3D vectors point in opposite directions (anti-parallel)."""
    norm1 = math.sqrt(v1.x**2 + v1.y**2 + v1.z**2)
    norm2 = math.sqrt(v2.x**2 + v2.y**2 + v2.z**2)
    if norm1 < 1e-7 or norm2 < 1e-7:
        return False
    dot = (v1.x * v2.x + v1.y * v2.y + v1.z * v2.z) / (norm1 * norm2)
    return (dot + 1.0) < tol_rad

def distance_between_opposing_planes(
    p1: Point3D, n1: Vector3D,
    p2: Point3D, n2: Vector3D
) -> Optional[float]:
    """Calculates perpendicular distance between two opposing parallel planes."""
    if not are_vectors_opposing(n1, n2):
        return None
    dx = p1.x - p2.x
    dy = p1.y - p2.y
    dz = p1.z - p2.z
    dist = abs(dx * n1.x + dy * n1.y + dz * n1.z)
    return float(dist)
