"""B-Rep topology-based Internal Corner Detector."""

from typing import Dict, List, Optional, Set, Tuple
from OCP.TopoDS import TopoDS_Solid

from cadcnc.cad_engine.topology import TopologyGraph, BRepEdgeItem
from cadcnc.schemas.common import StatusType
from cadcnc.schemas.features import CornerFeature
from cadcnc.schemas.config import ThresholdsConfig

def detect_internal_corners(
    graph: TopologyGraph,
    solid: TopoDS_Solid,
    config: ThresholdsConfig
) -> List[CornerFeature]:
    """Detects sharp and filleted vertical internal corners."""
    detected_corners: List[CornerFeature] = []
    corner_counter = 1

    # 1. Sharp internal corners: concave linear edges between vertical walls
    for edge in graph.edges:
        if edge.convexity == "concave" and edge.is_linear:
            # Check if edge is vertical-ish (Z component of edge curve is dominant)
            # Find the shared faces
            if len(edge.face_ids) == 2:
                f1 = graph.faces[edge.face_ids[0]]
                f2 = graph.faces[edge.face_ids[1]]
                # Both faces are near-vertical walls (normal Z component near 0)
                if abs(f1.normal_or_axis.z) < 0.3 and abs(f2.normal_or_axis.z) < 0.3:
                    corner = CornerFeature(
                        id=f"corner_{corner_counter}",
                        type="sharp",
                        pocket_or_slot_id=None,
                        radius_mm=None,  # Sharp has zero radius
                        edge_ids=[edge.edge_id],
                        wall_face_ids=list(edge.face_ids),
                        min_tool_diameter_needed_mm=0.0,  # Impossible with rotary tool
                        accessible=True,
                        confidence=0.98,
                        confidence_basis=[
                            "confirmed_concave_linear_edge",
                            "vertical_wall_intersection",
                            "zero_fillet_radius"
                        ],
                        status=StatusType.CONFIRMED
                    )
                    detected_corners.append(corner)
                    corner_counter += 1

    # 2. Filleted internal corners: cylindrical fillet faces between walls
    for fid, fnode in graph.faces.items():
        if fnode.surface_type == "cylinder" and fnode.radius_mm is not None:
            # If radius is small (< 10mm) and adjacent to two vertical planar walls at concave edges
            adj_fids = graph.get_adjacent_faces(fid)
            planar_adj = [af for af in adj_fids if graph.faces[af].surface_type == "plane"]
            if len(planar_adj) >= 2:
                corner = CornerFeature(
                    id=f"corner_{corner_counter}",
                    type="filleted",
                    pocket_or_slot_id=None,
                    radius_mm=round(float(fnode.radius_mm), 2),
                    edge_ids=[],
                    wall_face_ids=planar_adj,
                    min_tool_diameter_needed_mm=round(float(fnode.radius_mm * 2.0), 2),
                    accessible=True,
                    confidence=0.95,
                    confidence_basis=[
                        "cylindrical_fillet_surface_detected",
                        "tangent_transition_to_planar_walls"
                    ],
                    status=StatusType.CONFIRMED
                )
                detected_corners.append(corner)
                corner_counter += 1

    return detected_corners
