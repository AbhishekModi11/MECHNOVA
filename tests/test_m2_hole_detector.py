"""Automated test suite for Milestone M2: Hole Detection and Boss Rejection."""

from pathlib import Path
import pytest

from cadcnc.cad_engine.parser import load_step_model
from cadcnc.cad_engine.topology import build_topology_graph
from cadcnc.feature_detection.hole_detector import detect_holes
from cadcnc.schemas.config import ThresholdsConfig
from cadcnc.schemas.common import StatusType

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_models"

@pytest.fixture
def config():
    return ThresholdsConfig()

def test_through_holes_detection(config):
    cad = load_step_model(SAMPLE_DIR / "plate_through_holes.step")
    graph = build_topology_graph(cad.primary_solid)
    holes = detect_holes(graph, cad.primary_solid, config)

    assert len(holes) == 3
    for h in holes:
        assert h.type == "through"
        assert h.status == StatusType.CONFIRMED
        assert pytest.approx(h.depth_mm, abs=0.2) == 20.0
        assert h.accessible is True

    diameters = sorted([round(h.diameter_mm, 1) for h in holes])
    assert diameters == [5.0, 10.0, 12.0]

def test_blind_holes_detection(config):
    cad = load_step_model(SAMPLE_DIR / "plate_blind_holes.step")
    graph = build_topology_graph(cad.primary_solid)
    holes = detect_holes(graph, cad.primary_solid, config)

    assert len(holes) == 2
    for h in holes:
        assert h.type == "blind"
        assert h.status == StatusType.CONFIRMED

    diameters = sorted([round(h.diameter_mm, 1) for h in holes])
    assert diameters == [8.0, 10.0]

def test_counterbore_countersink_detection(config):
    cad = load_step_model(SAMPLE_DIR / "counterbore_countersink.step")
    graph = build_topology_graph(cad.primary_solid)
    holes = detect_holes(graph, cad.primary_solid, config)

    assert len(holes) == 2
    types = {h.type for h in holes}
    assert "counterbore" in types
    assert "countersink" in types

    cbore = next(h for h in holes if h.type == "counterbore")
    assert pytest.approx(cbore.diameter_mm, abs=0.2) == 6.0
    assert pytest.approx(cbore.counterbore_diameter_mm, abs=0.2) == 12.0

    csk = next(h for h in holes if h.type == "countersink")
    assert pytest.approx(csk.diameter_mm, abs=0.2) == 5.0
    assert csk.countersink_angle_deg is not None

def test_shaft_boss_negative_case(config):
    """Critical negative test: external cylinder MUST NOT be classified as a hole."""
    cad = load_step_model(SAMPLE_DIR / "shaft_boss_negative.step")
    graph = build_topology_graph(cad.primary_solid)
    holes = detect_holes(graph, cad.primary_solid, config)

    assert len(holes) == 0, f"Expected 0 holes on shaft/boss part, but found {len(holes)}"

def test_side_holes_detection(config):
    cad = load_step_model(SAMPLE_DIR / "side_holes.step")
    graph = build_topology_graph(cad.primary_solid)
    holes = detect_holes(graph, cad.primary_solid, config)

    assert len(holes) == 1
    h = holes[0]
    assert h.type == "through"
    assert pytest.approx(h.diameter_mm, abs=0.2) == 8.0
    # Axis should be aligned with X axis (abs(x) close to 1)
    assert abs(h.axis.x) > 0.9

def test_bracket_demo_holes(config):
    cad = load_step_model(SAMPLE_DIR / "bracket_demo.step")
    graph = build_topology_graph(cad.primary_solid)
    holes = detect_holes(graph, cad.primary_solid, config)

    assert len(holes) == 4
    for h in holes:
        assert h.type == "through"
        assert pytest.approx(h.diameter_mm, abs=0.2) == 6.0
        assert pytest.approx(h.depth_mm, abs=0.2) == 20.0
