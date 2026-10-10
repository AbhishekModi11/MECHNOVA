import numpy as np
import trimesh
import os
import sys

sys.path.insert(0, os.path.abspath("cad_service"))
from features import detect_features

def test_bracket_features():
    """Test feature detection on bracket.stl: finds 2 through holes + 1 open slot."""
    bracket_path = "frontend/static/uploads/bracket.stl"
    assert os.path.exists(bracket_path), f"{bracket_path} does not exist"
    
    m = trimesh.load(bracket_path, force="mesh")
    pitch = float(np.clip(m.extents.max() / 220, 0.25, 1.0))
    vox = m.voxelized(pitch).fill()
    occ = np.asarray(vox.matrix, bool)
    origin = tuple(np.asarray(vox.translation, float))
    feats = detect_features(occ, pitch, origin)

    holes = [f for f in feats if f["kind"] in ("hole", "blind_hole")]
    slots = [f for f in feats if f["kind"] in ("slot", "pocket", "window")]

    assert len(holes) == 2, f"Expected 2 holes, got {len(holes)}: {holes}"
    assert len(slots) == 1, f"Expected 1 slot, got {len(slots)}: {slots}"
    print(f"Bracket test PASSED: found {len(holes)} holes and {len(slots)} slot/pocket features.")

def test_block_with_pocket_and_blind_hole():
    """Test feature detection on block: finds 1 pocket + 1 blind hole."""
    import cadquery as cq
    wp = (
        cq.Workplane("XY")
        .box(60, 50, 30)
        .faces(">Z")
        .workplane()
        # blind pocket 20x12 depth 8
        .center(-15, 0)
        .rect(20, 12)
        .cutBlind(-8)
        # blind hole dia 8 depth 10
        .center(30, 0)
        .hole(8, depth=10)
    )
    temp_stl = "out/test_block_unit.stl"
    os.makedirs("out", exist_ok=True)
    cq.exporters.export(wp, temp_stl)

    m = trimesh.load(temp_stl, force="mesh")
    pitch = 0.5
    vox = m.voxelized(pitch).fill()
    occ = np.asarray(vox.matrix, bool)
    origin = tuple(np.asarray(vox.translation, float))
    feats = detect_features(occ, pitch, origin)

    pockets = [f for f in feats if f["kind"] == "pocket"]
    blind_holes = [f for f in feats if f["kind"] == "blind_hole"]

    assert len(pockets) >= 1, f"Expected at least 1 pocket, got {len(pockets)}"
    assert len(blind_holes) >= 1, f"Expected at least 1 blind hole, got {len(blind_holes)}"
    print(f"Block test PASSED: found {len(pockets)} pocket(s) and {len(blind_holes)} blind hole(s).")

if __name__ == "__main__":
    print("Running features unit tests...")
    test_block_with_pocket_and_blind_hole()
    test_bracket_features()
    print("ALL ACCEPTANCE UNIT TESTS PASSED SUCCESSFULLY!")
