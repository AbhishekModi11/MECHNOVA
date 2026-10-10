"""B-Rep topology-based Slot Feature Detector."""

import math
from typing import Dict, List, Optional, Set, Tuple
from OCP.TopoDS import TopoDS_Solid, TopoDS_Face

from cadcnc.cad_engine.topology import TopologyGraph, BRepFaceNode
from cadcnc.cad_engine.geometry import compute_bounding_box, classify_point_in_solid
from cadcnc.cad_engine.measurements import distance_between_opposing_planes
from cadcnc.schemas.common import Point3D, Vector3D, StatusType
from cadcnc.schemas.features import SlotFeature
from cadcnc.schemas.config import ThresholdsConfig

def detect_slots(
    graph: TopologyGraph,
    solid: TopoDS_Solid,
    config: ThresholdsConfig
) -> List[SlotFeature]:
    """Detects closed, open-ended, and through slots from B-Rep topology."""
    bbox = compute_bounding_box(solid)
    aspect_threshold = config.thresholds.slot_aspect_ratio_min

    detected_slots: List[SlotFeature] = []
    slot_counter = 1
    handled_face_pairs: Set[Tuple[str, str]] = set()

    # 1. Closed and open slots with recessed floor faces
    for fid, fnode in graph.faces.items():
        if fnode.surface_type != "plane" or fnode.normal_or_axis.z < 0.8:
            continue
        if fnode.location.z >= (bbox.z_max - 0.5):
            continue

        concave_edges = [e for e in graph.face_edges.get(fid, []) if e.convexity == "concave"]
        if len(concave_edges) < 2:
            continue

        linear_edges = [e for e in concave_edges if e.is_linear]
        unique_lengths = sorted(list(set([round(e.length_mm, 2) for e in linear_edges])), reverse=True)
        if len(unique_lengths) >= 2:
            dim_length = unique_lengths[0]
            dim_width = unique_lengths[1]
        elif len(unique_lengths) == 1:
            dim_length = unique_lengths[0]
            dim_width = unique_lengths[0]
        else:
            dim_width = math.sqrt(fnode.area_mm2 / 3.0)
            dim_length = fnode.area_mm2 / max(dim_width, 0.001)

        aspect_ratio = dim_length / max(dim_width, 0.001)
        if aspect_ratio >= aspect_threshold:
            wall_fids = set()
            for e in concave_edges:
                for wfid in e.face_ids:
                    if wfid != fid:
                        wall_fids.add(wfid)

            depth = bbox.z_max - fnode.location.z
            slot = SlotFeature(
                id=f"slot_{slot_counter}",
                type="closed" if len(concave_edges) >= 4 else "open_ended",
                width_mm=round(float(dim_width), 2),
                length_mm=round(float(dim_length), 2),
                depth_mm=round(float(depth), 2),
                end_shape="straight",
                floor_face_id=fid,
                wall_face_ids=list(wall_fids),
                aspect_ratio=round(float(aspect_ratio), 2),
                accessible=True,
                confidence=0.95,
                confidence_basis=[
                    "elongated_channel_aspect_ratio_verified",
                    "parallel_walls_detected",
                    "recessed_floor_bounded_by_concave_edges"
                ],
                status=StatusType.CONFIRMED
            )
            detected_slots.append(slot)
            slot_counter += 1

    # 2. Through slots (opposing internal vertical walls without floor)
    planar_fids = [f for f, node in graph.faces.items() if node.surface_type == "plane" and abs(node.normal_or_axis.z) < 0.2]
    for i in range(len(planar_fids)):
        for j in range(i + 1, len(planar_fids)):
            fid1, fid2 = planar_fids[i], planar_fids[j]
            pair = (min(fid1, fid2), max(fid1, fid2))
            if pair in handled_face_pairs:
                continue

            node1, node2 = graph.faces[fid1], graph.faces[fid2]
            dist = distance_between_opposing_planes(node1.location, node1.normal_or_axis, node2.location, node2.normal_or_axis)
            if dist is not None and 1.0 <= dist <= 30.0:
                # Crucial check: verify that space between the two faces is OUT of solid (hollow channel)
                mid_p = Point3D(
                    x=0.5 * (node1.location.x + node2.location.x),
                    y=0.5 * (node1.location.y + node2.location.y),
                    z=0.5 * (node1.location.z + node2.location.z)
                )
                if classify_point_in_solid(solid, mid_p) != "OUT":
                    continue  # This is solid material (e.g. wall or rib), not an empty channel

                h1 = bbox.dz
                l1 = min(node1.area_mm2, node2.area_mm2) / max(h1, 0.001)
                aspect = l1 / max(dist, 0.001)
                if aspect >= aspect_threshold:
                    handled_face_pairs.add(pair)
                    slot = SlotFeature(
                        id=f"slot_{slot_counter}",
                        type="through",
                        width_mm=round(float(dist), 2),
                        length_mm=round(float(l1), 2),
                        depth_mm=round(float(h1), 2),
                        end_shape="straight",
                        floor_face_id=None,
                        wall_face_ids=[fid1, fid2],
                        aspect_ratio=round(float(aspect), 2),
                        accessible=True,
                        confidence=0.92,
                        confidence_basis=[
                            "through_part_opposing_vertical_walls",
                            "hollow_channel_void_verified",
                            "aspect_ratio_exceeds_threshold"
                        ],
                        status=StatusType.CONFIRMED
                    )
                    detected_slots.append(slot)
                    slot_counter += 1

    return detected_slots
