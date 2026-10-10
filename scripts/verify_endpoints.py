import httpx
import json

BASE = "http://localhost:8080"

def test_routes():
    with httpx.Client(base_url=BASE, timeout=15.0) as client:
        # 1. Login page
        r = client.get("/login")
        assert r.status_code == 200, f"/login status {r.status_code}"
        print(f"[OK] GET /login -> {r.status_code}")

        # 2. Themes CSS
        r = client.get("/static/css/themes.css")
        assert r.status_code == 200, f"themes.css status {r.status_code}"
        assert "--accent" in r.text, "CSS vars missing in themes.css"
        print(f"[OK] GET /static/css/themes.css -> {r.status_code} (Contains --accent tokens)")

        # 3. Step 1 New Project
        r = client.get("/worker/new-project")
        assert r.status_code == 200, f"/worker/new-project status {r.status_code}"
        print(f"[OK] GET /worker/new-project -> {r.status_code}")

        # 4. Step 2 Design Details
        r = client.get("/worker/projects/c6805c0f/design-details")
        assert r.status_code == 200, f"/worker/projects/c6805c0f/design-details status {r.status_code}"
        print(f"[OK] GET /worker/projects/c6805c0f/design-details -> {r.status_code}")

        # 5. Step 3 Tools
        r = client.get("/worker/projects/c6805c0f/tools")
        assert r.status_code == 200, f"/worker/projects/c6805c0f/tools status {r.status_code}"
        print(f"[OK] GET /worker/projects/c6805c0f/tools -> {r.status_code}")

        # 6. Step 4 Job Slip Summary
        r = client.get("/worker/projects/c6805c0f/summary")
        assert r.status_code == 200, f"/worker/projects/c6805c0f/summary status {r.status_code}"
        print(f"[OK] GET /worker/projects/c6805c0f/summary -> {r.status_code}")

        # 7. Project History
        r = client.get("/worker/history")
        assert r.status_code == 200, f"/worker/history status {r.status_code}"
        print(f"[OK] GET /worker/history -> {r.status_code}")

        # 8. REST API: raw-material update
        r = client.put("/api/projects/c6805c0f/raw-material", json={
            "material": "Aluminum 6061-T6",
            "length": 120.0,
            "width": 110.0,
            "height": 90.0,
            "part_name": "Precision Aerospace Bracket"
        })
        assert r.status_code == 200, f"raw-material PUT status {r.status_code}: {r.text}"
        res = r.json()
        print(f"[OK] PUT /api/projects/c6805c0f/raw-material -> {r.status_code} ({len(res.get('tools', []))} suggested tools generated, DFM warnings: {len(res.get('dfm_warnings', []))})")

        # 9. REST API: slip-action confirm
        r = client.post("/api/projects/c6805c0f/slip-action", json={
            "action": "confirm",
            "operator": "Elena Rostova",
            "employee_id": "WRK-001"
        })
        assert r.status_code == 200, f"slip-action POST status {r.status_code}: {r.text}"
        snap = r.json()
        print(f"[OK] POST /api/projects/c6805c0f/slip-action (confirm) -> {r.status_code} (Status: {snap.get('status')}, Tools: {len(snap.get('suggested_tools', []))})")

        # 10. REST API: slip-action request
        r = client.post("/api/projects/c6805c0f/slip-action", json={
            "action": "request",
            "operator": "Elena Rostova",
            "employee_id": "WRK-001"
        })
        assert r.status_code == 200, f"slip-action POST status {r.status_code}: {r.text}"
        snap2 = r.json()
        print(f"[OK] POST /api/projects/c6805c0f/slip-action (request) -> {r.status_code} (Status: {snap2.get('status')})")

        print("\n>>> ALL 10 END-TO-END VERIFICATION CHECKS PASSED PERFECTLY! <<<")

if __name__ == "__main__":
    test_routes()
