"""B-Rep topology-based Thin Wall Feature Detector."""

from typing import Dict, List, Optional, Set, Tuple
from OCP.TopoDS import TopoDS_Solid

from cadcnc.cad_engine.topology import TopologyGraph
from cadcnc.cad_engine.geometry import compute_bounding_box, classify_point_in_solid
from cadcnc.cad_engine.measurements import distance_between_opposing_planes
from cadcnc.schemas.common import Point3D, StatusType
from cadcnc.schemas.features import ThinWallFeature
from cadcnc.schemas.config import ThresholdsConfig

def detect_thin_walls(
    graph: TopologyGraph,
    solid: TopoDS_Solid,
    config: ThresholdsConfig
) -> List[ThinWallFeature]:
    """Detects thin walls between opposing planar faces below configured threshold."""
    min_thickness = config.thresholds.min_wall_thickness_mm
    bbox = compute_bounding_box(solid)
    detected_walls: List[ThinWallFeature] = []
    wall_counter = 1
    handled_pairs: Set[Tuple[str, str]] = set()

    planar_fids = [fid for fid, node in graph.faces.items() if node.surface_type == "plane"]

    for i in range(len(planar_fids)):
        for j in range(i + 1, len(planar_fids)):
            fid1, fid2 = planar_fids[i], planar_fids[j]
            pair = (min(fid1, fid2), max(fid1, fid2))
            if pair in handled_pairs:
                continue

            node1, node2 = graph.faces[fid1], graph.faces[fid2]
            dist = distance_between_opposing_planes(
                node1.location, node1.normal_or_axis,
                node2.location, node2.normal_or_axis
            )

            # Check if opposing planes are closer than the minimum wall thickness threshold
            if dist is not None and 0.1 <= dist < min_thickness:
                # Probe at Z center of the model to avoid boundary edges
                mid_z = 0.5 * (bbox.z_min + bbox.z_max)
                mid_p = Point3D(
                    x=0.5 * (node1.location.x + node2.location.x),
                    y=0.5 * (node1.location.y + node2.location.y),
                    z=mid_z
                )
                if classify_point_in_solid(solid, mid_p) == "OUT":
                    continue  # Air void, not solid material

                handled_pairs.add(pair)
                wall = ThinWallFeature(
                    id=f"wall_{wall_counter}",
                    thickness_mm=round(float(dist), 2),
                    face_id_1=fid1,
                    face_id_2=fid2,
                    min_allowed_thickness_mm=float(min_thickness),
                    confidence=0.92,
                    confidence_basis=[
                        "opposing_parallel_planes_measured_analytically",
                        "solid_material_midpoint_confirmed",
                        f"thickness_below_configured_minimum_{min_thickness}mm"
                    ],
                    status=StatusType.UNCERTAIN  # As required by rule: label as suspected_issue / uncertain
                )
                detected_walls.append(wall)
                wall_counter += 1

    return detected_walls
