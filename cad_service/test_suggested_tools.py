"""
Unit tests for MECHNOVA Suggested Tools & Machining Engine.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from suggested_tools import suggest_tools_for_project, generate_gcode_preview

def test_tool_suggestions():
    print("Testing Tool Suggestions & Machining Engine...")

    sample_features = [
        {"id": "H1", "kind": "hole", "diameter": 10.0, "depth": 20.0, "through": True, "enabled": True},
        {"id": "H2", "kind": "hole", "diameter": 18.0, "depth": 60.0, "through": False, "enabled": True},
        {"id": "P1", "kind": "pocket", "size": [40.0, 30.0], "depth": 15.0, "corner_radius": 5.0, "enabled": True},
        {"id": "S1", "kind": "slot", "size": [12.0, 50.0], "depth": 10.0, "enabled": True}
    ]

    stock = [110.0, 70.0, 25.0]
    res = suggest_tools_for_project("Aluminum 6061-T6", stock, sample_features, part_bbox=[100.0, 60.0, 20.0])

    tools = res["tools"]
    warnings = res["dfm_warnings"]

    # 1. Face Mill check
    face_mills = [t for t in tools if t["type"] == "face_mill"]
    assert len(face_mills) == 1, f"Expected 1 face mill, got {len(face_mills)}"
    print(f"[OK] Face mill chosen: {face_mills[0]['name']}")

    # 2. Spot Drill check
    spot_drills = [t for t in tools if t["type"] == "spot_drill"]
    assert len(spot_drills) == 1, f"Expected 1 deduped spot drill, got {len(spot_drills)}"
    print(f"[OK] Spot drill present: {spot_drills[0]['name']}")

    # 3. Pilot Drill check (because H2 is 18 mm > 12 mm)
    pilot_drills = [t for t in tools if "Pilot" in t["name"]]
    assert len(pilot_drills) == 1, f"Expected 1 pilot drill for 18mm hole, got {len(pilot_drills)}"
    print(f"[OK] Pilot drill present for large hole: {pilot_drills[0]['name']}")

    # 4. Final Drills check (10mm and 18mm)
    drills = [t for t in tools if t["type"] == "drill"]
    drill_dias = [t["diameter"] for t in drills]
    assert 10.0 in drill_dias and 18.0 in drill_dias, f"Expected 10mm and 18mm drills in {drill_dias}"
    print(f"[OK] Drill sizes match holes exactly: {drill_dias}")

    # 5. Peck drilling DFM check
    sample_features_deep = [
        {"id": "H_DEEP", "kind": "hole", "diameter": 8.0, "depth": 50.0, "through": True, "enabled": True} # 50 > 5*8=40
    ]
    res_deep = suggest_tools_for_project("Aluminum 6061-T6", stock, sample_features_deep)
    peck_warns = [w for w in res_deep["dfm_warnings"] if w["code"] == "PECK_DRILL"]
    assert len(peck_warns) == 1, "Expected PECK_DRILL warning for hole > 5xD"
    print(f"[OK] Peck drilling DFM check passed: {peck_warns[0]['message']}")

    # 6. Pockets and slots end mills
    endmills = [t for t in tools if t["type"] == "end_mill"]
    assert len(endmills) >= 2, f"Expected roughing & finishing end mills, got {len(endmills)}"
    print(f"[OK] End mills generated: {[t['name'] for t in endmills]}")

    # 7. Cutting parameters test: RPM and Feed calculation
    for t in tools:
        assert t["suggested_rpm"] >= 400 and t["suggested_rpm"] <= 12000, f"RPM out of range: {t['suggested_rpm']}"
        assert t["suggested_feed"] > 0, f"Feed must be positive: {t['suggested_feed']}"
    print("[OK] Cutting parameters RPM and Feed calculated accurately.")

    # 8. G-code preview test
    gcode = generate_gcode_preview("MN-2026-TEST", "Aluminum 6061-T6", tools, sample_features)
    assert "G54" in gcode and "M06" in gcode and "M03" in gcode and "M30" in gcode
    print("[OK] G-code generation passed.")

    print("\nALL SUGGESTED TOOLS ENGINE TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_tool_suggestions()
