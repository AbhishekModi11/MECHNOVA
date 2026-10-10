"""B-Rep Topology Adjacency Graph and Edge Convexity Classifier."""

from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field

from OCP.TopoDS import TopoDS, TopoDS_Shape, TopoDS_Solid, TopoDS_Face, TopoDS_Edge
from OCP.TopExp import TopExp, TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE, TopAbs_EDGE, TopAbs_SOLID, TopAbs_REVERSED, TopAbs_FORWARD
from OCP.TopTools import TopTools_IndexedDataMapOfShapeListOfShape
from OCP.BRepAdaptor import BRepAdaptor_Surface, BRepAdaptor_Curve
from OCP.BRep import BRep_Tool
from OCP.GeomAbs import (
    GeomAbs_Plane, GeomAbs_Cylinder, GeomAbs_Cone, GeomAbs_Line, GeomAbs_Circle
)
from OCP.ShapeAnalysis import ShapeAnalysis_Surface
from OCP.gp import gp_Pnt, gp_Vec

from cadcnc.schemas.common import Point3D, Vector3D
from cadcnc.cad_engine.geometry import (
    classify_surface, extract_plane_info, extract_cylinder_info,
    extract_cone_info, compute_face_area
)

@dataclass
class BRepFaceNode:
    face_id: str
    occt_face: TopoDS_Face
    surface_type: str
    area_mm2: float
    normal_or_axis: Vector3D
    location: Point3D
    radius_mm: Optional[float] = None
    cone_angle_deg: Optional[float] = None
    orientation: str = "FORWARD"

@dataclass
class BRepEdgeItem:
    edge_id: str
    occt_edge: TopoDS_Edge
    face_ids: Tuple[str, ...]
    convexity: str  # "concave", "convex", "smooth"
    length_mm: float
    midpoint: Point3D
    is_linear: bool = False
    is_circular: bool = False

@dataclass
class TopologyGraph:
    faces: Dict[str, BRepFaceNode] = field(default_factory=dict)
    edges: List[BRepEdgeItem] = field(default_factory=list)
    face_adjacency: Dict[str, Set[str]] = field(default_factory=dict)
    face_edges: Dict[str, List[BRepEdgeItem]] = field(default_factory=dict)

    def get_adjacent_faces(self, face_id: str) -> List[str]:
        return list(self.face_adjacency.get(face_id, set()))

    def get_edges_between(self, face_id_1: str, face_id_2: str) -> List[BRepEdgeItem]:
        matches = []
        for e in self.edges:
            if face_id_1 in e.face_ids and face_id_2 in e.face_ids:
                matches.append(e)
        return matches

def compute_edge_convexity(
    edge: TopoDS_Edge,
    f1: TopoDS_Face,
    f2: TopoDS_Face
) -> str:
    """Computes whether an edge shared by two faces is concave, convex, or smooth."""
    c_adapt = BRepAdaptor_Curve(edge)
    first_p = c_adapt.FirstParameter()
    last_p = c_adapt.LastParameter()
    if last_p <= first_p:
        return "smooth"

    u_mid = 0.5 * (first_p + last_p)
    p_edge = c_adapt.Value(u_mid)

    t_vec = gp_Vec()
    p = gp_Pnt()
    c_adapt.D1(u_mid, p, t_vec)
    if t_vec.Magnitude() < 1e-7:
        return "smooth"
    t_vec.Normalize()

    # Find edge orientation in f1
    exp_e = TopExp_Explorer(f1, TopAbs_EDGE)
    e_in_f1 = None
    while exp_e.More():
        if exp_e.Current().IsSame(edge):
            e_in_f1 = exp_e.Current()
            break
        exp_e.Next()

    if e_in_f1 and e_in_f1.Orientation() == TopAbs_REVERSED:
        t_vec.Reverse()

    s1 = BRepAdaptor_Surface(f1)
    s2 = BRepAdaptor_Surface(f2)

    try:
        sas1 = ShapeAnalysis_Surface(s1.Surface().Surface())
        uv1 = sas1.ValueOfUV(p_edge, 1e-3)
        d1u1, d1v1 = gp_Vec(), gp_Vec()
        s1.D1(uv1.X(), uv1.Y(), p, d1u1, d1v1)
        n1 = d1u1.Crossed(d1v1)
        if n1.Magnitude() < 1e-7:
            return "smooth"
        n1.Normalize()
        if f1.Orientation() == TopAbs_REVERSED:
            n1.Reverse()

        sas2 = ShapeAnalysis_Surface(s2.Surface().Surface())
        uv2 = sas2.ValueOfUV(p_edge, 1e-3)
        d1u2, d1v2 = gp_Vec(), gp_Vec()
        s2.D1(uv2.X(), uv2.Y(), p, d1u2, d1v2)
        n2 = d1u2.Crossed(d1v2)
        if n2.Magnitude() < 1e-7:
            return "smooth"
        n2.Normalize()
        if f2.Orientation() == TopAbs_REVERSED:
            n2.Reverse()
    except Exception:
        return "smooth"

    # Smooth/tangent check (normals nearly identical)
    dot_n = n1.Dot(n2)
    if dot_n > 0.998:
        return "smooth"

    # Cross tangent with normal to obtain vector pointing into f1
    v_in = n1.Crossed(t_vec)
    dot_convexity = v_in.Dot(n2)

    if dot_convexity > 0.05:
        return "concave"
    elif dot_convexity < -0.05:
        return "convex"
    else:
        return "smooth"

def build_topology_graph(solid: TopoDS_Solid) -> TopologyGraph:
    """Constructs the face adjacency graph with edge convexities."""
    graph = TopologyGraph()
    face_map: Dict[TopoDS_Face, str] = {}
    
    # 1. Register face nodes
    exp_face = TopExp_Explorer(solid, TopAbs_FACE)
    idx = 1
    while exp_face.More():
        face = TopoDS.Face_s(exp_face.Current())
        face_id = f"face_{idx}"
        idx += 1
        face_map[face] = face_id

        stype = classify_surface(face)
        area = compute_face_area(face)
        radius = None
        cone_angle = None

        if stype == "plane":
            loc, norm_vec = extract_plane_info(face)
        elif stype == "cylinder":
            loc, norm_vec, radius = extract_cylinder_info(face)
        elif stype == "cone":
            loc, norm_vec, _, cone_angle = extract_cone_info(face)
        else:
            loc = Point3D(x=0.0, y=0.0, z=0.0)
            norm_vec = Vector3D(x=0.0, y=0.0, z=1.0)

        orientation_str = "REVERSED" if face.Orientation() == TopAbs_REVERSED else "FORWARD"

        graph.faces[face_id] = BRepFaceNode(
            face_id=face_id,
            occt_face=face,
            surface_type=stype,
            area_mm2=area,
            normal_or_axis=norm_vec,
            location=loc,
            radius_mm=radius,
            cone_angle_deg=cone_angle,
            orientation=orientation_str
        )
        graph.face_adjacency[face_id] = set()
        graph.face_edges[face_id] = []
        exp_face.Next()

    # 2. Map edges to faces to build adjacency
    edge_map = TopTools_IndexedDataMapOfShapeListOfShape()
    TopExp.MapShapesAndAncestors_s(solid, TopAbs_EDGE, TopAbs_FACE, edge_map)

    for i in range(1, edge_map.Extent() + 1):
        edge = TopoDS.Edge_s(edge_map.FindKey(i))
        face_list = edge_map.FindFromIndex(i)
        
        shared_face_ids = []
        faces_for_edge: List[TopoDS_Face] = []
        for shp in face_list:
            f = TopoDS.Face_s(shp)
            faces_for_edge.append(f)
            # Find face_id in face_map
            for k, fid in face_map.items():
                if k.IsSame(f):
                    shared_face_ids.append(fid)
                    break

        c_adapt = BRepAdaptor_Curve(edge)
        first_p = c_adapt.FirstParameter()
        last_p = c_adapt.LastParameter()
        length = 0.0
        midpoint = Point3D(x=0.0, y=0.0, z=0.0)

        if last_p > first_p:
            p_mid = c_adapt.Value(0.5 * (first_p + last_p))
            midpoint = Point3D(x=float(p_mid.X()), y=float(p_mid.Y()), z=float(p_mid.Z()))
            p_start = c_adapt.Value(first_p)
            p_end = c_adapt.Value(last_p)
            length = float(p_start.Distance(p_end)) if c_adapt.GetType() == GeomAbs_Line else float(last_p - first_p)

        is_linear = (c_adapt.GetType() == GeomAbs_Line)
        is_circular = (c_adapt.GetType() == GeomAbs_Circle)

        convexity = "smooth"
        if len(faces_for_edge) == 2:
            convexity = compute_edge_convexity(edge, faces_for_edge[0], faces_for_edge[1])
            f_id1, f_id2 = shared_face_ids[0], shared_face_ids[1]
            graph.face_adjacency[f_id1].add(f_id2)
            graph.face_adjacency[f_id2].add(f_id1)

        edge_item = BRepEdgeItem(
            edge_id=f"edge_{i}",
            occt_edge=edge,
            face_ids=tuple(shared_face_ids),
            convexity=convexity,
            length_mm=max(0.0, length),
            midpoint=midpoint,
            is_linear=is_linear,
            is_circular=is_circular
        )
        graph.edges.append(edge_item)

        for fid in shared_face_ids:
            if fid in graph.face_edges:
                graph.face_edges[fid].append(edge_item)

    return graph
