"""Automated test suite for Milestone M4: Tool Selection, Scoring, Accessibility, and Manufacturability."""

from pathlib import Path
import pytest

from cadcnc.cad_engine.parser import load_step_model
from cadcnc.cad_engine.topology import build_topology_graph
from cadcnc.feature_detection.hole_detector import detect_holes
from cadcnc.feature_detection.pocket_detector import detect_pockets
from cadcnc.optimization.tool_selector import load_tool_database, select_tools_for_features
from cadcnc.analysis.manufacturability import evaluate_manufacturability
from cadcnc.engine import Engine
from cadcnc.schemas.config import ThresholdsConfig, MachineConfig

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "sample_models"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"

@pytest.fixture
def tools_db():
    return load_tool_database(DATA_DIR / "tools_example.json")

def test_tool_selection_holes(tools_db):
    engine = Engine()
    features = engine.features(SAMPLE_DIR / "plate_through_holes.step", "out_test_m4")
    recs = select_tools_for_features(features, tools_db, "aluminum_6061")

    assert len(recs.recommendations) >= 3
    # Check that 5mm, 10mm, 12mm drills are matched to respective holes
    hole_recs = [r for r in recs.recommendations if "hole" in r.feature_type]
    selected_tools = [r.selected_tool_id for r in hole_recs]
    assert "DRILL-05-CARBIDE" in selected_tools
    assert "DRILL-10-CARBIDE" in selected_tools
    assert "DRILL-12-CARBIDE" in selected_tools

def test_tool_rejection_reasons(tools_db):
    engine = Engine()
    features = engine.features(SAMPLE_DIR / "plate_through_holes.step", "out_test_m4")
    recs = select_tools_for_features(features, tools_db, "aluminum_6061")

    # Pick hole_1 (5mm hole)
    h1_rec = next(r for r in recs.recommendations if r.feature_id == "hole_1")
    assert h1_rec.selected_tool_id == "DRILL-05-CARBIDE"
    assert len(h1_rec.rejected_candidates) > 0
    # A 10mm drill must be rejected for a 5mm hole due to diameter
    rej_10 = next(rj for rj in h1_rec.rejected_candidates if rj.tool_id == "DRILL-10-CARBIDE")
    assert any("does not match hole diameter" in reason for reason in rej_10.reasons)

def test_manufacturability_scoring_thin_wall(tmp_path):
    engine = Engine()
    report = engine.check(SAMPLE_DIR / "thin_wall.step", tmp_path)
    assert report.overall_score < 100.0
    assert report.yellow_count > 0
    categories = [f.category for f in report.findings]
    assert "thin_wall" in categories
    assert (tmp_path / "manufacturability.json").exists()
    assert (tmp_path / "tool_recommendations.json").exists()

def test_manufacturability_bracket_demo(tmp_path):
    engine = Engine()
    report = engine.check(SAMPLE_DIR / "bracket_demo.step", tmp_path)
    assert report.overall_score > 0.0
    assert report.accessible_setups_count >= 1
    assert report.green_count > 0
