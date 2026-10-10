"""Automated test suite for Milestone M3: Pockets, Slots, Corners, and Thin Walls."""

from pathlib import Path
import pytest

from cadcnc.cad_engine.parser import load_step_model
from cadcnc.cad_engine.topology import build_topology_graph
from cadcnc.feature_detection.pocket_detector import detect_pockets
from cadcnc.feature_detection.slot_detector import detect_slots
from cadcnc.feature_detection.corner_detector import detect_internal_corners
from cadcnc.feature_detection.wall_detector import detect_thin_walls
from cadcnc.schemas.config import ThresholdsConfig
from cadcnc.schemas.common import StatusType

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_models"

@pytest.fixture
def config():
    return ThresholdsConfig()

def test_pockets_detection(config):
    cad = load_step_model(SAMPLE_DIR / "pockets_various.step")
    graph = build_topology_graph(cad.primary_solid)
    pockets = detect_pockets(graph, cad.primary_solid, config)

    assert len(pockets) == 2
    for p in pockets:
        assert p.type == "closed"
        assert p.status == StatusType.CONFIRMED
        assert pytest.approx(p.depth_mm, abs=0.2) == 10.0
        assert p.length_mm > 0
        assert p.width_mm > 0

def test_slots_detection(config):
    cad = load_step_model(SAMPLE_DIR / "slots_various.step")
    graph = build_topology_graph(cad.primary_solid)
    slots = detect_slots(graph, cad.primary_solid, config)

    assert len(slots) == 2
    types = {s.type for s in slots}
    assert "closed" in types
    assert "through" in types

    closed_s = next(s for s in slots if s.type == "closed")
    assert pytest.approx(closed_s.width_mm, abs=0.2) == 8.0
    assert pytest.approx(closed_s.length_mm, abs=0.2) == 30.0

    through_s = next(s for s in slots if s.type == "through")
    assert pytest.approx(through_s.width_mm, abs=0.2) == 6.0
    assert pytest.approx(through_s.length_mm, abs=0.2) == 25.0

def test_internal_corners_detection(config):
    cad = load_step_model(SAMPLE_DIR / "pockets_various.step")
    graph = build_topology_graph(cad.primary_solid)
    corners = detect_internal_corners(graph, cad.primary_solid, config)

    assert len(corners) >= 8  # 4 vertical corners in each of the 2 pockets
    sharp_corners = [c for c in corners if c.type == "sharp"]
    assert len(sharp_corners) >= 8
    for c in sharp_corners:
        assert c.radius_mm is None

def test_thin_wall_detection(config):
    cad = load_step_model(SAMPLE_DIR / "thin_wall.step")
    graph = build_topology_graph(cad.primary_solid)
    walls = detect_thin_walls(graph, cad.primary_solid, config)

    assert len(walls) == 1
    w = walls[0]
    assert pytest.approx(w.thickness_mm, abs=0.1) == 1.2
    assert w.status == StatusType.UNCERTAIN

def test_bracket_demo_all_features(config):
    cad = load_step_model(SAMPLE_DIR / "bracket_demo.step")
    graph = build_topology_graph(cad.primary_solid)

    pockets = detect_pockets(graph, cad.primary_solid, config)
    slots = detect_slots(graph, cad.primary_solid, config)
    corners = detect_internal_corners(graph, cad.primary_solid, config)

    assert len(pockets) == 1
    assert len(slots) == 1
    assert len(corners) >= 4
