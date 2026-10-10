"""CAD Engine module for STEP parsing, B-Rep topology, measurements, and tessellation."""

from cadcnc.cad_engine.parser import load_step_model, STEPParseError, CADModel
from cadcnc.cad_engine.geometry import (
    compute_bounding_box, compute_volume_and_area, compute_face_area,
    classify_surface, extract_plane_info, extract_cylinder_info,
    extract_cone_info, classify_point_in_solid, is_internal_cylindrical_surface
)
from cadcnc.cad_engine.topology import (
    BRepFaceNode, BRepEdgeItem, TopologyGraph, build_topology_graph, compute_edge_convexity
)
from cadcnc.cad_engine.measurements import (
    euclidean_distance_3d, are_vectors_parallel, are_vectors_opposing,
    distance_between_opposing_planes
)
from cadcnc.cad_engine.tessellate import export_model_preview, export_feature_map

__all__ = [
    "load_step_model", "STEPParseError", "CADModel",
    "compute_bounding_box", "compute_volume_and_area", "compute_face_area",
    "classify_surface", "extract_plane_info", "extract_cylinder_info",
    "extract_cone_info", "classify_point_in_solid", "is_internal_cylindrical_surface",
    "BRepFaceNode", "BRepEdgeItem", "TopologyGraph", "build_topology_graph", "compute_edge_convexity",
    "euclidean_distance_3d", "are_vectors_parallel", "are_vectors_opposing",
    "distance_between_opposing_planes",
    "export_model_preview", "export_feature_map"
]
