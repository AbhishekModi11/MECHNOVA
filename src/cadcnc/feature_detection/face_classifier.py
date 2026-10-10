"""Face role classification for manufacturing feature recognition."""

import math
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field

from OCP.TopoDS import TopoDS_Solid, TopoDS_Face
from OCP.BRepAdaptor import BRepAdaptor_Surface
from OCP.GeomAbs import GeomAbs_Cylinder, GeomAbs_Plane, GeomAbs_Cone

from cadcnc.cad_engine.topology import TopologyGraph, BRepFaceNode
from cadcnc.cad_engine.geometry import is_internal_cylindrical_surface

@dataclass
class ClassifiedFaces:
    internal_cylinders: List[str] = field(default_factory=list)
    external_cylinders: List[str] = field(default_factory=list)
    planar_faces: List[str] = field(default_factory=list)
    conical_faces: List[str] = field(default_factory=list)
    top_face_candidates: List[str] = field(default_factory=list)
    angular_spans: Dict[str, float] = field(default_factory=dict)
    axial_lengths: Dict[str, float] = field(default_factory=dict)

def classify_all_faces(graph: TopologyGraph, solid: TopoDS_Solid) -> ClassifiedFaces:
    """Classifies each B-Rep face by geometry and role in manufacturing."""
    result = ClassifiedFaces()

    max_z = -float("inf")
    top_candidate_id = None

    for fid, node in graph.faces.items():
        if node.surface_type == "cylinder":
            adapt = BRepAdaptor_Surface(node.occt_face)
            u_span_rad = abs(adapt.LastUParameter() - adapt.FirstUParameter())
            v_span_mm = abs(adapt.LastVParameter() - adapt.FirstVParameter())
            u_span_deg = math.degrees(u_span_rad)

            result.angular_spans[fid] = u_span_deg
            result.axial_lengths[fid] = float(v_span_mm)

            if is_internal_cylindrical_surface(solid, node.occt_face):
                result.internal_cylinders.append(fid)
            else:
                result.external_cylinders.append(fid)

        elif node.surface_type == "plane":
            result.planar_faces.append(fid)
            # Check for top face candidate (+Z normal and highest Z location)
            norm = node.normal_or_axis
            if norm.z > 0.95 and node.location.z > max_z:
                max_z = node.location.z
                top_candidate_id = fid

        elif node.surface_type == "cone":
            result.conical_faces.append(fid)

    if top_candidate_id:
        result.top_face_candidates.append(top_candidate_id)

    return result
