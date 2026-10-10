"""Tessellation and 3D preview asset exporter (GLB & STL)."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import trimesh
import trimesh.exchange.gltf

from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Face
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRep import BRep_Tool
from OCP.TopLoc import TopLoc_Location

def export_model_preview(
    shape: TopoDS_Shape,
    out_glb_path: Path,
    linear_deflection: float = 0.1,
    angular_deflection: float = 0.5
) -> Tuple[Path, int, int]:
    """Tessellates OCCT shape and exports binary glTF (.glb) and .stl.
    
    Returns:
        Tuple of (out_path, vertices_count, faces_count)
    """
    out_glb_path = Path(out_glb_path).resolve()
    out_glb_path.parent.mkdir(parents=True, exist_ok=True)

    # Perform BRep incremental mesh
    mesh = BRepMesh_IncrementalMesh(shape, linear_deflection, False, angular_deflection, True)
    mesh.Perform()

    all_verts = []
    all_tris = []
    v_offset = 0

    exp_face = TopExp_Explorer(shape, TopAbs_FACE)
    while exp_face.More():
        face = TopoDS.Face_s(exp_face.Current())
        loc = TopLoc_Location()
        tri = BRep_Tool.Triangulation_s(face, loc)
        if tri:
            trsf = loc.Transformation()
            nb_nodes = tri.NbNodes()
            nb_triangles = tri.NbTriangles()

            for i in range(1, nb_nodes + 1):
                p = tri.Node(i).Transformed(trsf)
                all_verts.append([float(p.X()), float(p.Y()), float(p.Z())])

            for i in range(1, nb_triangles + 1):
                t = tri.Triangle(i)
                n1, n2, n3 = t.Get()
                all_tris.append([n1 - 1 + v_offset, n2 - 1 + v_offset, n3 - 1 + v_offset])

            v_offset += nb_nodes
        exp_face.Next()

    if not all_verts or not all_tris:
        raise RuntimeError("Tessellation produced 0 vertices or 0 faces")

    tm = trimesh.Trimesh(vertices=all_verts, faces=all_tris)
    glb_data = trimesh.exchange.gltf.export_glb(tm)
    with open(out_glb_path, "wb") as f:
        f.write(glb_data)

    # Also export STL as fallback
    stl_path = out_glb_path.with_suffix(".stl")
    tm.export(str(stl_path))

    return out_glb_path, len(tm.vertices), len(tm.faces)

def export_feature_map(
    face_to_features: Dict[str, List[str]],
    out_json_path: Path
) -> Path:
    """Exports face_id to feature_ids mapping for Phase 2 3D viewer highlighting."""
    out_json_path = Path(out_json_path).resolve()
    payload = {
        "schema_version": "1.0.0",
        "face_to_features": face_to_features
    }
    with open(out_json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return out_json_path
