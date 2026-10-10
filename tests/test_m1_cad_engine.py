"""Tests for Milestone M1: CAD Engine, STEP Parser, Topology, and Tessellation."""

import json
from pathlib import Path
import pytest

from cadcnc.cad_engine.parser import load_step_model, STEPParseError
from cadcnc.cad_engine.geometry import compute_bounding_box, compute_volume_and_area
from cadcnc.cad_engine.topology import build_topology_graph
from cadcnc.cad_engine.tessellate import export_model_preview
from cadcnc.engine import Engine

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_models"

def test_load_step_success():
    step_file = SAMPLE_DIR / "plate_through_holes.step"
    cad_model = load_step_model(step_file)
    assert cad_model is not None
    assert len(cad_model.solids) == 1
    assert cad_model.unit in ("mm", "in")
    assert cad_model.load_time_s > 0

def test_load_corrupt_file_raises():
    corrupt_file = SAMPLE_DIR / "broken_corrupt.step"
    with pytest.raises(STEPParseError):
        load_step_model(corrupt_file)

def test_geometry_measurements():
    step_file = SAMPLE_DIR / "plate_through_holes.step"
    cad_model = load_step_model(step_file)
    solid = cad_model.primary_solid

    bbox = compute_bounding_box(solid)
    assert pytest.approx(bbox.dx, abs=0.1) == 80.0
    assert pytest.approx(bbox.dy, abs=0.1) == 60.0
    assert pytest.approx(bbox.dz, abs=0.1) == 20.0

    vol, area = compute_volume_and_area(solid)
    # Box 80x60x20 = 96000. Less 3 holes:
    # V_holes = pi*(2.5^2 + 5^2 + 6^2)*20 = pi*(6.25 + 25 + 36)*20 = pi*67.25*20 = 4225.44
    # Expected volume ~ 91774.56 mm3
    expected_vol = 96000.0 - 4225.44
    assert pytest.approx(vol, rel=1e-3) == expected_vol
    assert area > 0

def test_topology_graph():
    step_file = SAMPLE_DIR / "plate_through_holes.step"
    cad_model = load_step_model(step_file)
    solid = cad_model.primary_solid

    graph = build_topology_graph(solid)
    assert len(graph.faces) == 9  # 6 planar faces + 3 cylindrical hole faces
    assert len(graph.edges) == 21
    
    # Check adjacency
    for fid, neighbors in graph.face_adjacency.items():
        assert len(neighbors) > 0

def test_tessellation_glb(tmp_path):
    step_file = SAMPLE_DIR / "plate_through_holes.step"
    cad_model = load_step_model(step_file)
    solid = cad_model.primary_solid

    out_glb = tmp_path / "preview.glb"
    path, verts, faces = export_model_preview(solid, out_glb)
    assert path.exists()
    assert path.stat().st_size > 0
    assert verts > 0
    assert faces > 0

def test_engine_analyze(tmp_path):
    engine = Engine()
    step_file = SAMPLE_DIR / "bracket_demo.step"
    summary = engine.analyze(step_file, tmp_path)
    assert summary.filename == "bracket_demo.step"
    assert summary.solids_count == 1
    assert summary.faces_count == 19
    assert (tmp_path / "model_summary.json").exists()
    assert (tmp_path / "model_preview.glb").exists()
    assert (tmp_path / "feature_map.json").exists()
