import httpx
import time
import sys

BASE_URL = "http://127.0.0.1:8080"
CAD_URL = "http://127.0.0.1:8001"

def test_full_pipeline():
    print("=== STARTING FULL ANTIGRAVITY TASK 2 VERIFICATION ===")
    
    # 0. Reset tools inventory to pristine seed state
    import json
    with open("cad_service/seed_tools.json", "r", encoding="utf-8") as f:
        seeds = json.load(f)
    for t in seeds:
        httpx.patch(f"{BASE_URL}/api/tools/{t['id']}", json={
            "status": t.get("status", "AVAILABLE"),
            "damaged": t.get("damaged", False),
            "qty": t.get("qty", 1),
            "wear_pct": t.get("wear_pct", 0.0)
        })

    # 1. Test Tools Inventory
    r = httpx.get(f"{BASE_URL}/api/tools")
    assert r.status_code == 200, f"GET /api/tools failed: {r.text}"
    tools = r.json()
    assert len(tools) >= 15, f"Expected at least 15 tools, got {len(tools)}"
    print(f"[OK] GET /api/tools returned {len(tools)} tools.")

    # 2. Test Tool Patch
    r = httpx.patch(f"{BASE_URL}/api/tools/EM-12-3F-Z", json={"wear_pct": 35.0, "qty": 2, "damaged": False, "status": "AVAILABLE"})
    assert r.status_code == 200, f"PATCH failed: {r.text}"
    t12 = r.json()
    assert t12["qty"] == 2 and not t12["damaged"], f"Tool patch not reflected: {t12}"
    print("[OK] PATCH /api/tools/EM-12-3F-Z successful.")

    # 3. Create Project & Upload bracket.stl
    r = httpx.post(f"{BASE_URL}/api/projects", json={
        "partName": "Aerospace Mount Bracket",
        "material": "Aluminum 6061-T6",
        "length": 100.0,
        "width": 60.0,
        "height": 20.0
    })
    assert r.status_code == 200, f"Project creation failed: {r.text}"
    pid = r.json()["id"]
    print(f"[OK] Created project id: {pid}")

    with open("frontend/static/uploads/bracket.stl", "rb") as f:
        file_bytes = f.read()

    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/model", files={"file": ("bracket.stl", file_bytes, "model/stl")})
    assert r.status_code == 202, f"Model upload failed: {r.text}"
    print("[OK] Model uploaded. Waiting for analysis completion...")

    # Poll project status until READY
    for _ in range(30):
        time.sleep(0.5)
        r = httpx.get(f"{BASE_URL}/api/projects/{pid}")
        assert r.status_code == 200
        pdata = r.json()
        if pdata.get("status") == "READY":
            break
    assert pdata.get("status") == "READY", f"Project never reached READY: {pdata}"
    print(f"[OK] Project {pid} status is READY. Project No: {pdata.get('project_no')}")

    # 4. Auto-select Tools
    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/tools/auto-select")
    assert r.status_code == 200, f"Auto-select failed: {r.text}"
    match_data = r.json()
    assignments = match_data["assignments"]
    summary = match_data["summary"]
    can_proceed = match_data["can_proceed"]
    assert len(assignments) >= 7, f"Expected at least 7 assignments, got {len(assignments)}"
    assert can_proceed is True, f"can_proceed is False: {summary}"
    print(f"[OK] Auto-select completed: {summary}, can_proceed={can_proceed}")

    # Verify 85% worn tool notes contains "replace soon"
    worn_notes_found = False
    for a in assignments:
        assigned = a.get("assigned")
        if assigned and assigned.get("wear_pct") == 85:
            notes = " ".join(a.get("notes", []))
            if "replace soon" in notes:
                worn_notes_found = True
                print(f"[OK] Verified 85% worn tool note: {notes}")
    assert worn_notes_found, "Did not find expected 'replace soon' note for 85% worn tool!"

    # 5. Test Tool Missing Scenario (Crib modification test 4)
    httpx.patch(f"{BASE_URL}/api/tools/EM-12-3F-Z", json={"damaged": True, "qty": 0})
    httpx.patch(f"{BASE_URL}/api/tools/CH-12-90", json={"damaged": True, "qty": 0})
    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/tools/auto-select")
    assert r.status_code == 200
    missing_match = r.json()
    assert missing_match["summary"]["MISSING"] > 0, f"Expected MISSING tools when 12mm tools damaged: {missing_match['summary']}"
    assert missing_match["can_proceed"] is False, "can_proceed should be False when tool is MISSING"
    print(f"[OK] Damaged tool caused MISSING tool as required: {missing_match['summary']}")

    # Restore 12mm tools
    httpx.patch(f"{BASE_URL}/api/tools/EM-12-3F-Z", json={"damaged": False, "qty": 2, "wear_pct": 35.0, "status": "AVAILABLE"})
    httpx.patch(f"{BASE_URL}/api/tools/CH-12-90", json={"damaged": False, "qty": 1, "wear_pct": 70.0, "status": "AVAILABLE"})
    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/tools/auto-select")
    assert r.status_code == 200
    assert r.json()["can_proceed"] is True
    print("[OK] Restored tools and auto-select restored can_proceed=True.")

    # 6. Test Swapping an Alternative Tool
    # Find an assignment with alternatives
    swap_req = None
    alt_tool = None
    for a in r.json()["assignments"]:
        if a.get("alternatives"):
            swap_req = a["required_id"]
            alt_tool = a["alternatives"][0]["id"]
            break
    if swap_req and alt_tool:
        r = httpx.put(f"{BASE_URL}/api/projects/{pid}/tools/selection", json={"assignments": [{"required_id": swap_req, "tool_id": alt_tool}]})
        assert r.status_code == 200, f"Swap failed: {r.text}"
        swapped_sel = r.json()
        swapped_tool_id = [x["assigned"]["id"] for x in swapped_sel["assignments"] if x["required_id"] == swap_req][0]
        assert swapped_tool_id == alt_tool, f"Swap not applied: {swapped_tool_id} vs {alt_tool}"
        print(f"[OK] Swapped alternative tool {alt_tool} for {swap_req}.")

    # 7. Confirm Tools
    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/tools/confirm")
    assert r.status_code == 200, f"Confirm tools failed: {r.text}"
    print("[OK] Confirmed project tools.")

    # 8. Test Stock Updates & Savings Calculations
    bbox = pdata["analysis"]["bbox"]
    # Invalid stock (less than part + 2mm)
    bad_stock = [bbox[0] - 5, bbox[1], bbox[2]]
    r = httpx.put(f"{BASE_URL}/api/projects/{pid}/stock", json={"size": bad_stock})
    assert r.status_code == 200
    res_bad = r.json()
    assert len(res_bad["material"]["errors"]) > 0, f"Expected stock errors, got none: {res_bad}"
    print(f"[OK] Stock < part + 2mm correctly generated error: {res_bad['material']['errors'][0]}")

    # Valid recommended stock
    good_stock = [bbox[0] + 6, bbox[1] + 6, bbox[2] + 6]
    r = httpx.put(f"{BASE_URL}/api/projects/{pid}/stock", json={"size": good_stock})
    assert r.status_code == 200
    res_good = r.json()
    assert len(res_good["material"]["errors"]) == 0
    mat_saved_pct = res_good["material"]["saved_pct"]
    time_saved_pct = res_good["time"]["saved_pct"]
    print(f"[OK] Valid stock calculated savings: Time Saved {time_saved_pct}%, Material Saved {mat_saved_pct}%")
    assert 30.0 <= time_saved_pct <= 55.0, f"Time saved % unexpected: {time_saved_pct}"
    assert 20.0 <= mat_saved_pct <= 60.0, f"Material saved % unexpected: {mat_saved_pct}"

    # Bigger stock -> material saved % goes down
    bigger_stock = [bbox[0] + 30, bbox[1] + 30, bbox[2] + 30]
    r = httpx.put(f"{BASE_URL}/api/projects/{pid}/stock", json={"size": bigger_stock})
    assert r.status_code == 200
    res_bigger = r.json()
    bigger_mat_saved = res_bigger["material"]["saved_pct"]
    assert bigger_mat_saved < mat_saved_pct, f"Bigger stock should lower material saved %: {bigger_mat_saved} vs {mat_saved_pct}"
    print(f"[OK] Bigger stock lowered material saved % to {bigger_mat_saved}%.")

    # Reset back to recommended stock
    httpx.put(f"{BASE_URL}/api/projects/{pid}/stock", json={"size": good_stock})

    # 9. Test GET /api/projects/{id}/summary
    r = httpx.get(f"{BASE_URL}/api/projects/{pid}/summary")
    assert r.status_code == 200, f"Summary failed: {r.text}"
    summary = r.json()
    assert summary.get("project_no").startswith("MN-2026-"), f"Invalid project_no: {summary.get('project_no')}"
    assert summary["features"]["holes"] == 2, f"Expected 2 holes, got {summary['features']['holes']}"
    assert summary["features"]["pockets"] == 1, f"Expected 1 pocket/slot, got {summary['features']['pockets']}"
    assert len(summary["tools"]) > 0, "No tools in summary"
    assert "assumptions" in summary["savings"], "Assumptions missing in summary"
    print(f"[OK] Summary verified for {summary['project_no']}: 2 holes, 1 pocket, {len(summary['tools'])} tools, {summary['savings']['time']['saved_pct']}% time saved.")

    # 10. Machine Request & Idempotency & 409 Conflict Handling
    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/machine-request", json={"requested_by": "WRK-001"})
    assert r.status_code == 200, f"Machine request failed: {r.text}"
    req1 = r.json()
    req_no = req1["request_no"]
    assert req_no.startswith("MR-2026-"), f"Invalid request_no: {req_no}"
    print(f"[OK] Machine request created: {req_no}, status={req1['status']}")

    # Idempotent second click
    r = httpx.post(f"{BASE_URL}/api/projects/{pid}/machine-request", json={"requested_by": "WRK-001"})
    assert r.status_code == 200
    req2 = r.json()
    assert req2["request_no"] == req_no, "Second request did not return existing request"
    print("[OK] Idempotency verified: duplicate click returned existing request.")

    # Verify project status is now REQUESTED
    r = httpx.get(f"{BASE_URL}/api/projects/{pid}")
    assert r.json()["status"] == "REQUESTED"
    print("[OK] Project status updated to REQUESTED.")

    # Concurrent second browser tab conflict test:
    # Two projects select the tools at the same time. Project A reserves first.
    # Project B then tries to submit with the now-reserved tools -> 409 Conflict!
    r = httpx.post(f"{BASE_URL}/api/projects", json={
        "partName": "Concurrent Tab Part",
        "material": "Aluminum 6061-T6",
        "length": 100.0,
        "width": 60.0,
        "height": 20.0
    })
    pid_a = r.json()["id"]
    httpx.post(f"{BASE_URL}/api/projects/{pid_a}/model", files={"file": ("bracket.stl", file_bytes, "model/stl")})

    r = httpx.post(f"{BASE_URL}/api/projects", json={
        "partName": "Concurrent Tab Part 2",
        "material": "Aluminum 6061-T6",
        "length": 100.0,
        "width": 60.0,
        "height": 20.0
    })
    pid_b = r.json()["id"]
    httpx.post(f"{BASE_URL}/api/projects/{pid_b}/model", files={"file": ("bracket.stl", file_bytes, "model/stl")})

    for _ in range(30):
        time.sleep(0.5)
        st_a = httpx.get(f"{BASE_URL}/api/projects/{pid_a}").json().get("status")
        st_b = httpx.get(f"{BASE_URL}/api/projects/{pid_b}").json().get("status")
        if st_a == "READY" and st_b == "READY":
            break

    # Unreserve tools in crib for clean test
    for cid in ("FM-63-5I", "EM-20-3F-U", "EM-12-3F-Z", "SD-10-90", "CH-12-90"):
        httpx.patch(f"{BASE_URL}/api/tools/{cid}", json={"status": "AVAILABLE", "qty": 1, "damaged": False})

    # Both projects select the available tools simultaneously
    httpx.post(f"{BASE_URL}/api/projects/{pid_a}/tools/auto-select")
    httpx.post(f"{BASE_URL}/api/projects/{pid_b}/tools/auto-select")

    # Project A reserves the tools first
    r_a = httpx.post(f"{BASE_URL}/api/projects/{pid_a}/machine-request")
    assert r_a.status_code == 200, f"Project A request failed: {r_a.text}"
    print(f"[OK] Project A reserved tools successfully: {r_a.json()['request_no']}")

    # Project B tries to submit from second tab -> 409 Conflict!
    r_b = httpx.post(f"{BASE_URL}/api/projects/{pid_b}/machine-request")
    assert r_b.status_code == 409, f"Expected 409 conflict, got {r_b.status_code}: {r_b.text}"
    print(f"[OK] 409 Conflict handled correctly on second tab submission: {r_b.json()['detail']}")

    print("\n>>> ALL ACCEPTANCE CRITERIA API TESTS PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_full_pipeline()
