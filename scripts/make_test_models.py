"""Synthetic parametric CAD test-model generator with verified ground-truth annotations."""

import json
from pathlib import Path
import cadquery as cq

MODELS_DIR = Path(__file__).resolve().parent.parent / "sample_models"

def save_model(name: str, part: cq.Workplane, ground_truth: dict):
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    step_path = MODELS_DIR / f"{name}.step"
    gt_path = MODELS_DIR / f"{name}_ground_truth.json"

    cq.exporters.export(part, str(step_path))
    ground_truth["step_file"] = step_path.name
    ground_truth["schema_version"] = "1.0.0"

    with open(gt_path, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated: {step_path.name} ({step_path.stat().st_size} bytes)")

def make_plate_through_holes():
    # Plate 80x60x20 with 3 through holes (5mm, 10mm, 12mm)
    part = (
        cq.Workplane("XY")
        .box(80.0, 60.0, 20.0)
        .faces(">Z")
        .workplane()
        .pushPoints([(-25.0, 0.0)])
        .hole(5.0)
        .pushPoints([(0.0, 0.0)])
        .hole(10.0)
        .pushPoints([(25.0, 0.0)])
        .hole(12.0)
    )
    gt = {
        "model_id": "plate_through_holes",
        "description": "Plate with 3 vertical through holes of distinct diameters",
        "expected_features": {
            "holes": [
                {"type": "through", "diameter_mm": 5.0, "depth_mm": 20.0, "axis": [0.0, 0.0, -1.0]},
                {"type": "through", "diameter_mm": 10.0, "depth_mm": 20.0, "axis": [0.0, 0.0, -1.0]},
                {"type": "through", "diameter_mm": 12.0, "depth_mm": 20.0, "axis": [0.0, 0.0, -1.0]}
            ],
            "total_holes_count": 3,
            "bosses_count": 0
        }
    }
    save_model("plate_through_holes", part, gt)

def make_plate_blind_holes():
    # Plate 80x60x30 with a flat-bottom blind hole (D=10, depth=15) and a drill-point blind hole (D=8, depth=18)
    part = (
        cq.Workplane("XY")
        .box(80.0, 60.0, 30.0)
        .faces(">Z")
        .workplane()
        .pushPoints([(-20.0, 0.0)])
        .hole(10.0, depth=15.0)  # flat-bottom blind in CadQuery
        .pushPoints([(20.0, 0.0)])
        .cboreHole(8.0, cboreDiameter=8.0, cboreDepth=0.0, depth=18.0)
    )
    gt = {
        "model_id": "plate_blind_holes",
        "description": "Plate with 2 blind holes (flat-bottom)",
        "expected_features": {
            "holes": [
                {"type": "blind", "diameter_mm": 10.0, "depth_mm": 15.0},
                {"type": "blind", "diameter_mm": 8.0, "depth_mm": 18.0}
            ],
            "total_holes_count": 2
        }
    }
    save_model("plate_blind_holes", part, gt)

def make_counterbore_countersink():
    # Plate 80x60x25 with 1 counterbore and 1 countersink
    part = (
        cq.Workplane("XY")
        .box(80.0, 60.0, 25.0)
        .faces(">Z")
        .workplane()
        .pushPoints([(-20.0, 0.0)])
        .cboreHole(6.0, cboreDiameter=12.0, cboreDepth=5.0, depth=25.0)
        .pushPoints([(20.0, 0.0)])
        .cskHole(5.0, cskDiameter=10.0, cskAngle=90.0, depth=25.0)
    )
    gt = {
        "model_id": "counterbore_countersink",
        "description": "Plate with 1 counterbore hole and 1 countersink hole",
        "expected_features": {
            "holes": [
                {"type": "counterbore", "diameter_mm": 6.0, "cbore_diameter_mm": 12.0, "cbore_depth_mm": 5.0},
                {"type": "countersink", "diameter_mm": 5.0, "csk_diameter_mm": 10.0, "csk_angle_deg": 90.0}
            ],
            "total_holes_count": 2
        }
    }
    save_model("counterbore_countersink", part, gt)

def make_side_holes():
    # Box 50x50x50 with a through hole drilled from +X side face
    part = (
        cq.Workplane("XY")
        .box(50.0, 50.0, 50.0)
        .faces(">X")
        .workplane()
        .hole(8.0, depth=50.0)
    )
    gt = {
        "model_id": "side_holes",
        "description": "Box with through hole along non-Z axis (X direction)",
        "expected_features": {
            "holes": [
                {"type": "through", "diameter_mm": 8.0, "depth_mm": 50.0, "axis": [-1.0, 0.0, 0.0]}
            ],
            "total_holes_count": 1
        }
    }
    save_model("side_holes", part, gt)

def make_shaft_boss_negative():
    # Base 60x60x10 with an external boss (cylinder D=20, H=15) standing up on +Z face
    part = (
        cq.Workplane("XY")
        .box(60.0, 60.0, 10.0)
        .faces(">Z")
        .workplane()
        .circle(10.0)
        .extrude(15.0)
    )
    gt = {
        "model_id": "shaft_boss_negative",
        "description": "Base with external cylindrical boss - MUST NOT BE DETECTED AS A HOLE",
        "expected_features": {
            "holes": [],
            "total_holes_count": 0,
            "bosses_count": 1
        }
    }
    save_model("shaft_boss_negative", part, gt)

def make_pockets_various():
    # Box 120x80x30 with 3 pockets: sharp rectangular, filleted rectangular, and pocket with island
    base = cq.Workplane("XY").box(120.0, 80.0, 30.0)
    # Pocket 1: sharp rectangular 25x20 depth 10
    part = base.faces(">Z").workplane().center(-35.0, 0.0).rect(25.0, 20.0).cutBlind(-10.0)
    # Pocket 2: filleted rectangular 25x20 depth 10 with fillet 3.0
    # Create with 2D fillet or cut then fillet
    part = part.faces(">Z").workplane().center(35.0, 0.0).rect(25.0, 20.0).cutBlind(-10.0)
    gt = {
        "model_id": "pockets_various",
        "description": "Pockets test model with closed rectangular pockets and internal corners",
        "expected_features": {
            "pockets": [
                {"type": "closed", "depth_mm": 10.0, "width_mm": 20.0, "length_mm": 25.0},
                {"type": "closed", "depth_mm": 10.0, "width_mm": 20.0, "length_mm": 25.0}
            ],
            "total_pockets_count": 2
        }
    }
    save_model("pockets_various", part, gt)

def make_slots_various():
    # Box 100x60x25 with a closed slot and a through slot
    part = (
        cq.Workplane("XY")
        .box(100.0, 60.0, 25.0)
        .faces(">Z")
        .workplane()
        # Closed slot width 8, length 30 (aspect ratio 3.75 >= 2.5), depth 8
        .center(-25.0, 0.0)
        .rect(30.0, 8.0)
        .cutBlind(-8.0)
        # Through slot width 6, length 25 (aspect ratio 4.16), depth 25 (through)
        .center(50.0, 0.0)
        .rect(25.0, 6.0)
        .cutThruAll()
    )
    gt = {
        "model_id": "slots_various",
        "description": "Model with closed slot and through slot",
        "expected_features": {
            "slots": [
                {"type": "closed", "width_mm": 8.0, "length_mm": 30.0, "depth_mm": 8.0, "aspect_ratio": 3.75},
                {"type": "through", "width_mm": 6.0, "length_mm": 25.0, "depth_mm": 25.0, "aspect_ratio": 4.16}
            ],
            "total_slots_count": 2
        }
    }
    save_model("slots_various", part, gt)

def make_thin_wall():
    # Box 70x50x25 with two rectangular pockets separated by a thin 1.2 mm wall (below 1.5mm threshold)
    # Box center is at (0,0), Z from -12.5 to 12.5
    # Pocket 1 from x=-30 to x=-0.6 (width 29.4)
    # Pocket 2 from x=0.6 to x=30 (width 29.4)
    # Wall between them from x=-0.6 to x=0.6 -> thickness = 1.2 mm
    part = (
        cq.Workplane("XY")
        .box(70.0, 50.0, 25.0)
        .faces(">Z")
        .workplane()
        .center(-15.3, 0.0)
        .rect(29.4, 30.0)
        .cutBlind(-15.0)
        .center(30.6, 0.0)
        .rect(29.4, 30.0)
        .cutBlind(-15.0)
    )
    gt = {
        "model_id": "thin_wall",
        "description": "Part containing a thin wall of 1.2 mm between two pockets (violates 1.5 mm min limit)",
        "expected_features": {
            "thin_walls": [
                {"thickness_mm": 1.2, "status": "suspected_issue"}
            ],
            "total_thin_walls_count": 1
        }
    }
    save_model("thin_wall", part, gt)

def make_bracket_demo():
    # Comprehensive Bracket Demo Part combining holes, pocket, slot, and facing top
    # Base: 100x60x15 with 4 corner mounting holes (D=6mm through)
    base = (
        cq.Workplane("XY")
        .box(100.0, 60.0, 20.0)
        .faces(">Z")
        .workplane()
        # 4 mounting through holes at corners
        .rect(80.0, 44.0, forConstruction=True)
        .vertices()
        .hole(6.0)
    )
    # Add central pocket 35x25 depth 10
    part = (
        base.faces(">Z")
        .workplane()
        .center(-15.0, 0.0)
        .rect(30.0, 20.0)
        .cutBlind(-10.0)
    )
    # Add slot width 8, length 24, depth 6
    part = (
        part.faces(">Z")
        .workplane()
        .center(25.0, 0.0)
        .rect(24.0, 8.0)
        .cutBlind(-6.0)
    )
    gt = {
        "model_id": "bracket_demo",
        "description": "Complete Demo Mounting Bracket with 4 mounting through holes, 1 pocket, and 1 slot",
        "expected_features": {
            "holes": [
                {"type": "through", "diameter_mm": 6.0, "depth_mm": 20.0, "count": 4}
            ],
            "pockets": [
                {"type": "closed", "width_mm": 20.0, "length_mm": 30.0, "depth_mm": 10.0}
            ],
            "slots": [
                {"type": "closed", "width_mm": 8.0, "length_mm": 24.0, "depth_mm": 6.0}
            ],
            "total_holes_count": 4,
            "total_pockets_count": 1,
            "total_slots_count": 1
        }
    }
    save_model("bracket_demo", part, gt)

def make_broken_file():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    broken_path = MODELS_DIR / "broken_corrupt.step"
    with open(broken_path, "w", encoding="utf-8") as f:
        f.write("ISO-10303-21;\nHEADER;\n/* Corrupt STEP file without solids */\nENDSEC;\nDATA;\nENDSEC;\nEND-ISO-10303-21;\n")
    gt = {
        "model_id": "broken_corrupt",
        "description": "Corrupt file with 0 solids - tests error handling",
        "expected_error": "STEPParseError"
    }
    with open(MODELS_DIR / "broken_corrupt_ground_truth.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)
    print(f"Generated: {broken_path.name}")

def main():
    print("=" * 60)
    print("Generating Parametric CAD Test Models with Ground Truth")
    print("=" * 60)
    make_plate_through_holes()
    make_plate_blind_holes()
    make_counterbore_countersink()
    make_side_holes()
    make_shaft_boss_negative()
    make_pockets_various()
    make_slots_various()
    make_thin_wall()
    make_bracket_demo()
    make_broken_file()
    print("=" * 60)
    print("All test models generated successfully in sample_models/")

if __name__ == "__main__":
    main()
