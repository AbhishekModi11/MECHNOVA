"""Geometric evaluation utilities for B-Rep shapes and surfaces."""

import math
from typing import Tuple, Optional
from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Solid, TopoDS_Face
from OCP.TopAbs import TopAbs_IN, TopAbs_OUT, TopAbs_ON, TopAbs_REVERSED, TopAbs_FORWARD
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import (
    GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone,
    GeomAbs_Sphere, GeomAbs_Torus, GeomAbs_BSplineSurface, GeomAbs_BezierSurface
)
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt, gp_Vec, gp_Dir

from cadcnc.schemas.common import Point3D, Vector3D, BoundingBox3D

def compute_bounding_box(shape: TopoDS_Shape) -> BoundingBox3D:
    """Calculates axis-aligned bounding box for any shape."""
    bbox = Bnd_Box()
    BRepBndLib.Add_s(shape, bbox)
    x_min, y_min, z_min, x_max, y_max, z_max = bbox.Get()
    return BoundingBox3D(
        x_min=float(x_min),
        x_max=float(x_max),
        y_min=float(y_min),
        y_max=float(y_max),
        z_min=float(z_min),
        z_max=float(z_max),
        dx=float(x_max - x_min),
        dy=float(y_max - y_min),
        dz=float(z_max - z_min)
    )

def compute_volume_and_area(shape: TopoDS_Shape) -> Tuple[float, float]:
    """Calculates exact analytical volume (mm3) and surface area (mm2)."""
    v_props = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, v_props)
    volume = float(v_props.Mass())

    s_props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(shape, s_props)
    area = float(s_props.Mass())

    return max(0.0, volume), max(0.0, area)

def compute_face_area(face: TopoDS_Face) -> float:
    """Calculates surface area of a single face."""
    s_props = GProp_GProps()
    BRepGProp.SurfaceProperties_s(face, s_props)
    return max(0.0, float(s_props.Mass()))

def classify_surface(face: TopoDS_Face) -> str:
    """Returns canonical surface category for a face."""
    adaptor = BRepAdaptor_Surface(face)
    stype = adaptor.GetType()
    if stype == GeomAbs_Plane:
        return "plane"
    elif stype == GeomAbs_Cylinder:
        return "cylinder"
    elif stype == GeomAbs_Cone:
        return "cone"
    elif stype == GeomAbs_Sphere:
        return "sphere"
    elif stype == GeomAbs_Torus:
        return "torus"
    elif stype in (GeomAbs_BSplineSurface, GeomAbs_BezierSurface):
        return "b_spline"
    else:
        return "other"

def extract_plane_info(face: TopoDS_Face) -> Tuple[Point3D, Vector3D]:
    """Extracts reference point and outward unit normal vector of a planar face."""
    adaptor = BRepAdaptor_Surface(face)
    pln = adaptor.Plane()
    loc = pln.Location()
    axis = pln.Axis()
    direction = axis.Direction()

    dx, dy, dz = direction.X(), direction.Y(), direction.Z()
    # If face orientation is REVERSED, normal points opposite to geometric surface normal
    if face.Orientation() == TopAbs_REVERSED:
        dx, dy, dz = -dx, -dy, -dz

    return (
        Point3D(x=float(loc.X()), y=float(loc.Y()), z=float(loc.Z())),
        Vector3D(x=float(dx), y=float(dy), z=float(dz))
    )

def extract_cylinder_info(face: TopoDS_Face) -> Tuple[Point3D, Vector3D, float]:
    """Extracts axis position, unit axis direction, and radius of a cylindrical face."""
    adaptor = BRepAdaptor_Surface(face)
    cyl = adaptor.Cylinder()
    axis = cyl.Axis()
    loc = axis.Location()
    direction = axis.Direction()
    radius = float(cyl.Radius())

    return (
        Point3D(x=float(loc.X()), y=float(loc.Y()), z=float(loc.Z())),
        Vector3D(x=float(direction.X()), y=float(direction.Y()), z=float(direction.Z())),
        radius
    )

def extract_cone_info(face: TopoDS_Face) -> Tuple[Point3D, Vector3D, float, float]:
    """Extracts apex point, axis direction, semi-angle (deg), and full angle (deg)."""
    adaptor = BRepAdaptor_Surface(face)
    cone = adaptor.Cone()
    apex = cone.Apex()
    axis = cone.Axis()
    direction = axis.Direction()
    semi_angle_rad = cone.SemiAngle()
    semi_angle_deg = abs(math.degrees(semi_angle_rad))
    full_angle_deg = semi_angle_deg * 2.0

    return (
        Point3D(x=float(apex.X()), y=float(apex.Y()), z=float(apex.Z())),
        Vector3D(x=float(direction.X()), y=float(direction.Y()), z=float(direction.Z())),
        float(semi_angle_deg),
        float(full_angle_deg)
    )

def classify_point_in_solid(solid: TopoDS_Solid, point: Point3D, tolerance: float = 1e-4) -> str:
    """Uses OCCT BRepClass3d_SolidClassifier to determine if point is IN, OUT, or ON the solid."""
    classifier = BRepClass3d_SolidClassifier(solid)
    pnt = gp_Pnt(point.x, point.y, point.z)
    classifier.Perform(pnt, tolerance)
    state = classifier.State()
    if state == TopAbs_IN:
        return "IN"
    elif state == TopAbs_OUT:
        return "OUT"
    else:
        return "ON"

def is_internal_cylindrical_surface(solid: TopoDS_Solid, face: TopoDS_Face) -> bool:
    """Determines whether a cylindrical face is internal (a hole) or external (a shaft/boss).
    
    Combines surface normal orientation check with 3D solid classifier probing:
    - For an internal cylinder (hole), material is OUTSIDE the cylinder; interior of cylinder is void.
    - For an external cylinder (boss/shaft), material is INSIDE the cylinder.
    """
    adaptor = BRepAdaptor_Surface(face)
    if adaptor.GetType() != GeomAbs_Cylinder:
        return False

    u_mid = 0.5 * (adaptor.FirstUParameter() + adaptor.LastUParameter())
    v_mid = 0.5 * (adaptor.FirstVParameter() + adaptor.LastVParameter())

    pnt = gp_Pnt()
    d1u = gp_Vec()
    d1v = gp_Vec()
    adaptor.D1(u_mid, v_mid, pnt, d1u, d1v)

    # Surface geometric normal is cross product of partial derivatives
    normal_vec = d1u.Crossed(d1v)
    if normal_vec.Magnitude() < 1e-7:
        return False
    normal_vec.Normalize()

    # Respect face topological orientation
    if face.Orientation() == TopAbs_REVERSED:
        normal_vec.Reverse()

    # Inward vector towards cylinder axis
    cyl = adaptor.Cylinder()
    axis_pnt = cyl.Axis().Location()
    to_axis = gp_Vec(pnt, axis_pnt)
    
    # Check if normal points towards cylinder axis
    dot_axis = normal_vec.Dot(to_axis)
    is_normal_towards_axis = dot_axis > 0.0

    # Probe slightly into the cylinder interior (towards axis)
    probe_step = min(0.5, cyl.Radius() * 0.2)
    probe_pnt = Point3D(
        x=pnt.X() + normal_vec.X() * probe_step,
        y=pnt.Y() + normal_vec.Y() * probe_step,
        z=pnt.Z() + normal_vec.Z() * probe_step
    )
    probe_state = classify_point_in_solid(solid, probe_pnt)

    # For a hole, probing along normal (into void) is OUT of solid material
    if probe_state == "OUT" and is_normal_towards_axis:
        return True
    elif probe_state == "IN":
        return False
    
    return is_normal_towards_axis
