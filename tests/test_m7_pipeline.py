"""Tests for Milestone M7: Full end-to-end pipeline execution and artifact delivery."""

import json
import shutil
from pathlib import Path
import pytest

from cadcnc.engine import Engine, EngineRunRequest
from cadcnc.cad_engine.parser import STEPParseError
from cadcnc.schemas.cad import ModelSummary
from cadcnc.schemas.features import FeaturesCollection
from cadcnc.schemas.analysis import ManufacturabilityReport
from cadcnc.schemas.optimization import ToolRecommendationsReport, MachiningPlan, ComparisonReport
from cadcnc.schemas.cam import ToolpathsCollection, ValidationReport
from cadcnc.schemas.run_log import RunLog

DEMO_STEP = Path("sample_models/bracket_demo.step")
BROKEN_STEP = Path("sample_models/broken_corrupt.step")
OUT_DIR = Path("runs/test_m7_full_pipeline")

@pytest.fixture(autouse=True)
def cleanup_test_dir():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR, ignore_errors=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR, ignore_errors=True)

def test_full_pipeline_run_bracket_demo():
    """Validates complete Engine.run() pipeline generating all required deliverables."""
    assert DEMO_STEP.exists()

    engine = Engine()
    req = EngineRunRequest(
        model_path=DEMO_STEP,
        out_dir=OUT_DIR,
        material_id="aluminum_6061"
    )

    result = engine.run(req)

    assert result.success is True

    # Check that all 12 core deliverables exist
    expected_files = [
        "model_summary.json",
        "features.json",
        "manufacturability.json",
        "tool_recommendations.json",
        "operation_plan.json",
        "toolpaths.json",
        "validation_report.json",
        "comparison.json",
        "program_setup1.nc",
        "model_preview.glb",
        "feature_map.json",
        "report.md",
        "report.html",
        "run_log.json"
    ]

    for fn in expected_files:
        p = OUT_DIR / fn
        assert p.exists(), f"Mandatory artifact missing: {fn}"
        assert p.stat().st_size > 0, f"Artifact is empty: {fn}"

    # Validate JSON schemas against Pydantic models
    with open(OUT_DIR / "model_summary.json", "r", encoding="utf-8") as f:
        ModelSummary.model_validate_json(f.read())

    with open(OUT_DIR / "features.json", "r", encoding="utf-8") as f:
        FeaturesCollection.model_validate_json(f.read())

    with open(OUT_DIR / "manufacturability.json", "r", encoding="utf-8") as f:
        ManufacturabilityReport.model_validate_json(f.read())

    with open(OUT_DIR / "tool_recommendations.json", "r", encoding="utf-8") as f:
        ToolRecommendationsReport.model_validate_json(f.read())

    with open(OUT_DIR / "operation_plan.json", "r", encoding="utf-8") as f:
        MachiningPlan.model_validate_json(f.read())

    with open(OUT_DIR / "comparison.json", "r", encoding="utf-8") as f:
        ComparisonReport.model_validate_json(f.read())

    with open(OUT_DIR / "toolpaths.json", "r", encoding="utf-8") as f:
        ToolpathsCollection.model_validate_json(f.read())

    with open(OUT_DIR / "validation_report.json", "r", encoding="utf-8") as f:
        val_rep = ValidationReport.model_validate_json(f.read())
        assert val_rep.all_mandatory_checks_passed is True

    with open(OUT_DIR / "run_log.json", "r", encoding="utf-8") as f:
        log = RunLog.model_validate_json(f.read())
        assert log.total_duration_s > 0.0
        assert len(log.stage_timings) >= 6

    # Verify G-code prototype banner
    nc_text = (OUT_DIR / "program_setup1.nc").read_text(encoding="utf-8")
    assert "PROTOTYPE - NOT VERIFIED ON A MACHINE" in nc_text

    # Verify Report content
    report_md = (OUT_DIR / "report.md").read_text(encoding="utf-8")
    assert "CAD-to-CNC Optimization Report" in report_md
    assert "Executive Summary" in report_md

    report_html = (OUT_DIR / "report.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in report_html
    assert "CAD-to-CNC Optimization Engine" in report_html

def test_broken_step_fails_gracefully():
    """Validates that a corrupted STEP file halts with STEPParseError without crash."""
    assert BROKEN_STEP.exists()

    engine = Engine()
    req = EngineRunRequest(
        model_path=BROKEN_STEP,
        out_dir=OUT_DIR
    )

    with pytest.raises(STEPParseError):
        engine.run(req)
