"""Tests for Milestone M6: CAM toolpath generation, validation gating, and G-code export."""

import shutil
from pathlib import Path
import pytest
from cadcnc.engine import Engine
from cadcnc.schemas.config import MachineConfig, TravelLimits

DEMO_STEP = Path("sample_models/bracket_demo.step")
OUT_DIR = Path("runs/test_m6_output")

@pytest.fixture(autouse=True)
def cleanup_test_dir():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    yield
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)

def test_toolpaths_generation_and_export():
    """Validates full toolpath generation and G-code export on demo bracket."""
    assert DEMO_STEP.exists(), f"Demo STEP file not found: {DEMO_STEP}"

    engine = Engine()
    tp_coll, val_report = engine.toolpaths(
        model_path=DEMO_STEP,
        out_dir=OUT_DIR,
        material_id="aluminum_6061"
    )

    # 1. Toolpaths verify
    assert tp_coll.total_operations > 0
    assert tp_coll.total_moves > 0
    assert (OUT_DIR / "toolpaths.json").exists()

    # 2. Validation report verify
    assert (OUT_DIR / "validation_report.json").exists()
    assert val_report.all_mandatory_checks_passed is True
    assert val_report.gcode_export_permitted is True

    # 3. G-code file verification
    gcode_path = OUT_DIR / "program_setup1.nc"
    assert gcode_path.exists(), "program_setup1.nc must be created when validation passes"

    gcode_text = gcode_path.read_text(encoding="utf-8")
    assert "PROTOTYPE - NOT VERIFIED ON A MACHINE" in gcode_text, "Mandatory prototype safety warning banner must be in G-code header"
    assert "M06" in gcode_text, "Tool change commands must be present"
    assert "M30" in gcode_text, "Program rewind/end must be present"
    assert "%" in gcode_text, "ISO framing percent signs must be present"

def test_validation_gating_blocks_gcode():
    """Validates that G-code export is strictly blocked when validation fails."""
    assert DEMO_STEP.exists()

    engine = Engine()
    # Create an artificially constrained machine configuration where part exceeds travel limits
    restricted_machine = MachineConfig()
    restricted_machine.machine.travel_limits_mm = TravelLimits(
        x_min=-5.0, x_max=5.0,
        y_min=-5.0, y_max=5.0,
        z_min=-5.0, z_max=5.0
    )

    machine_yaml = OUT_DIR / "restricted_machine.yaml"
    import yaml
    with open(machine_yaml, "w", encoding="utf-8") as f:
        yaml.dump(restricted_machine.model_dump(), f)

    tp_coll, val_report = engine.toolpaths(
        model_path=DEMO_STEP,
        out_dir=OUT_DIR,
        material_id="aluminum_6061",
        machine_path=machine_yaml
    )

    # Validation must FAIL
    assert val_report.all_mandatory_checks_passed is False
    assert val_report.gcode_export_permitted is False
    assert len(val_report.failure_reasons) > 0
    assert any("travel envelope" in r.lower() for r in val_report.failure_reasons)

    # G-code file MUST NOT exist!
    gcode_path = OUT_DIR / "program_setup1.nc"
    assert not gcode_path.exists(), "Safety violation: G-code must NOT be written when validation fails!"
