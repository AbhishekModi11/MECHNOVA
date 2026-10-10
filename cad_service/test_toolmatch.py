import json
import os
import sys

sys.path.insert(0, os.path.abspath("cad_service"))
from toolmatch import match_tools, condition_of, usable
from savings import savings, plan_time

def load_seed_tools():
    p = os.path.join(os.path.dirname(__file__), "seed_tools.json")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)

def test_toolmatch_bracket():
    # Required tools typical for bracket
    required = [
        {"id": "T1", "name": "Face mill 63 mm, 5 inserts", "diameter": 63, "type": "face_mill"},
        {"id": "T2", "name": "Carbide end mill 20 mm, 3 flute", "diameter": 20, "type": "end_mill", "flute_length": 23},
        {"id": "T3", "name": "Spot drill 90 deg, 10 mm", "diameter": 10, "type": "spot_drill"},
        {"id": "T4", "name": "Carbide drill 10 mm (pilot)", "diameter": 10, "type": "drill"},
        {"id": "T5", "name": "Carbide end mill 10 mm", "diameter": 10, "type": "end_mill"},
        {"id": "T6", "name": "Chamfer mill 90 deg, 12 mm", "diameter": 12, "type": "chamfer"},
        {"id": "T7", "name": "Carbide end mill 10 mm (profile finish)", "diameter": 10, "type": "end_mill"}
    ]
    inventory = load_seed_tools()
    res = match_tools(required, inventory, "Aluminum 6061-T6")
    
    print("Match results summary:", res["summary"])
    assert res["summary"]["MISSING"] == 0, f"Expected 0 missing tools, got {res['summary']['MISSING']}"
    assert res["can_proceed"] is True
    
    # Check that profile end mill gets the 85% worn tool with caution note
    worn_match = next((a for a in res["assignments"] if a["assigned"] and a["assigned"]["id"] == "EM-10-3F-U"), None)
    assert worn_match is not None, "Expected EM-10-3F-U to be assigned"
    assert worn_match["assigned"]["wear_pct"] == 85
    assert worn_match["status"] == "CAUTION"
    print("[OK] Bracket toolmatch test passed.")

def test_damaged_tool_never_selected():
    inventory = load_seed_tools()
    # CH-8-90 is marked damaged=True in seed_tools.json
    damaged = next(t for t in inventory if t["id"] == "CH-8-90")
    assert condition_of(damaged) == "DAMAGED"
    assert usable(damaged) is False
    
    required = [{"id": "T1", "name": "Chamfer mill 8 mm", "diameter": 8, "type": "chamfer"}]
    res = match_tools(required, inventory, "Aluminum 6061-T6")
    # Should be MISSING because the only 8mm chamfer tool is damaged
    assert res["assignments"][0]["status"] == "MISSING"
    print("[OK] Damaged tool rejection test passed.")

def test_same_tool_not_given_to_two_roles():
    inventory = load_seed_tools()
    # FM-63-5I has qty 1
    required = [
        {"id": "T1", "name": "Face mill 63 mm", "diameter": 63, "type": "face_mill"},
        {"id": "T2", "name": "Face mill 63 mm (second op)", "diameter": 63, "type": "face_mill"}
    ]
    res = match_tools(required, inventory, "Aluminum 6061-T6")
    # First gets FM-63-5I, second must get alternative (FM-50-4I substitute) or missing
    a1 = res["assignments"][0]["assigned"]["id"]
    a2 = res["assignments"][1]["assigned"]
    assert a1 == "FM-63-5I"
    if a2:
        assert a2["id"] != "FM-63-5I", "Same physical tool with qty 1 assigned twice!"
    print("[OK] Single tool duplicate prevention test passed.")

def test_stock_below_part_plus_2mm_errors():
    analysis = {"features": [{"kind": "hole", "enabled": True, "setup": "+Z", "diameter": 10, "depth": 15}]}
    bbox = [100.0, 100.0, 80.0]
    # user stock smaller than part + 2 mm
    user_stock = [101.0, 106.0, 86.0] # 101 < 100 + 2
    res = savings(analysis, "Aluminum 6061-T6", bbox, 300000.0, user_stock)
    assert len(res["material"]["errors"]) > 0
    assert "smaller than part + 2 mm" in res["material"]["errors"][0]
    print("[OK] Stock boundary validation test passed.")

def test_savings_never_negative():
    analysis = {"features": [{"kind": "hole", "enabled": True, "setup": "+Z", "diameter": 10, "depth": 15}]}
    bbox = [100.0, 100.0, 80.0]
    res = savings(analysis, "Aluminum 6061-T6", bbox, 300000.0, [200.0, 200.0, 200.0])
    assert res["time"]["saved_pct"] >= 0.0
    assert res["material"]["saved_pct"] >= 0.0
    print("[OK] Non-negative savings guarantee test passed.")

if __name__ == "__main__":
    print("Running Tool Match & Savings Acceptance Tests...")
    test_toolmatch_bracket()
    test_damaged_tool_never_selected()
    test_same_tool_not_given_to_two_roles()
    test_stock_below_part_plus_2mm_errors()
    test_savings_never_negative()
    print("ALL TOOL MATCH & SAVINGS TESTS PASSED!")
