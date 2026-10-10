from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal
from app.models.models import User, Project, MachineRequest, Machine, Schedule
from app.services.engine_service import run_engine_for_project_sync

client = TestClient(app)

DEMO_STEP = Path("sample_models/bracket_demo.step")


@pytest.fixture(autouse=True)
def cleanup_test_schedules():
    db = SessionLocal()
    try:
        db.query(Schedule).delete()
        db.commit()
    finally:
        db.close()
    yield
    db = SessionLocal()
    try:
        db.query(Schedule).delete()
        db.commit()
    finally:
        db.close()


def get_auth_token(email: str, password: str, role_tab: str) -> str:
    resp = client.post("/api/auth/login", json={
        "email": email,
        "password": password,
        "role_tab": role_tab
    })
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_admin_machines_summary():
    admin_token = get_auth_token("admin@mechnova.com", "admin123", "admin")
    resp = client.get("/api/admin/machines/summary", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_machines"] == 8
    assert "working_count" in data
    assert len(data["machines"]) == 8


def test_admin_workers_list():
    admin_token = get_auth_token("admin@mechnova.com", "admin123", "admin")
    resp = client.get("/api/admin/workers", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["summary"]["total_workers"] >= 6
    assert len(data["workers"]) >= 6


def test_tool_stock_inventory():
    worker_token = get_auth_token("elena@mechnova.com", "worker123", "worker")
    resp = client.get("/api/tools/stock", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["tools"]) >= 8
    assert "heuristic_notice" in data


def test_notifications_endpoint():
    worker_token = get_auth_token("elena@mechnova.com", "worker123", "worker")
    resp = client.get("/api/notifications", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "unread_count" in data
    assert len(data["notifications"]) >= 1


def test_scheduling_conflict_rejection():
    admin_token = get_auth_token("admin@mechnova.com", "admin123", "admin")
    db = SessionLocal()
    try:
        # Create a dummy project and schedule
        admin = db.query(User).filter(User.role == "admin").first()
        machine = db.query(Machine).first()
        assert admin is not None
        assert machine is not None
        
        proj1 = Project(
            owner_id=admin.id,
            name="Conflict Test Job 1",
            source_file_path=str(DEMO_STEP),
            status="approved"
        )
        proj2 = Project(
            owner_id=admin.id,
            name="Conflict Test Job 2",
            source_file_path=str(DEMO_STEP),
            status="requested"
        )
        db.add_all([proj1, proj2])
        db.commit()

        req2 = MachineRequest(
            project_id=proj2.id,
            worker_id=admin.id,
            requested_machine_id=machine.id,
            status="pending"
        )
        db.add(req2)
        db.commit()

        start_time = datetime.now(timezone.utc) + timedelta(days=2)
        end_time = start_time + timedelta(hours=2)

        # Existing reservation
        s1 = Schedule(
            machine_id=machine.id,
            project_id=proj1.id,
            start=start_time,
            end=end_time
        )
        db.add(s1)
        db.commit()

        # Attempt overlapping reservation on the same machine
        overlap_start = start_time + timedelta(minutes=30)
        overlap_end = overlap_start + timedelta(hours=1)

        resp = client.post(
            f"/api/admin/requests/{req2.id}/approve",
            json={
                "machine_id": machine.id,
                "scheduled_start": overlap_start.isoformat(),
                "scheduled_end": overlap_end.isoformat(),
                "note": "Testing conflict detection"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert resp.status_code == 409  # Conflict!
        err = resp.json()["detail"]
        assert "Scheduling Conflict" in err["message"]
        assert err["suggested_slot"] is not None

    finally:
        db.close()


def test_full_project_engine_integration_and_artifacts():
    worker_token = get_auth_token("elena@mechnova.com", "worker123", "worker")
    admin_token = get_auth_token("admin@mechnova.com", "admin123", "admin")

    assert DEMO_STEP.exists()

    # 1. Upload STEP project
    with open(DEMO_STEP, "rb") as f:
        resp = client.post(
            "/api/projects",
            data={"name": "Bracket Demo API Project", "material_id": "aluminum_6061"},
            files={"file": ("bracket_demo.step", f, "application/octet-stream")},
            headers={"Authorization": f"Bearer {worker_token}"}
        )
    assert resp.status_code == 201
    proj_id = resp.json()["id"]

    # 2. Synchronously run the engine for this project to produce real deliverables
    res = run_engine_for_project_sync(proj_id)
    assert res["success"] is True

    # 3. Verify deliverables via API
    # 3a. Model GLB preview
    resp_glb = client.get(f"/api/projects/{proj_id}/model", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp_glb.status_code == 200
    assert len(resp_glb.content) > 1000

    # 3b. Features JSON
    resp_feat = client.get(f"/api/projects/{proj_id}/features", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp_feat.status_code == 200
    feat_data = resp_feat.json()
    assert len(feat_data["features"]["holes"]) == 4

    # 3c. Tool recommendations
    resp_tools = client.get(f"/api/projects/{proj_id}/tools", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp_tools.status_code == 200
    tools_data = resp_tools.json()
    recs = tools_data.get("recommendations", tools_data.get("tool_recommendations", []))
    assert len(recs) > 0

    # 3d. Machining plan & comparison
    resp_plan = client.get(f"/api/projects/{proj_id}/plan", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp_plan.status_code == 200
    plan_data = resp_plan.json()
    assert "operation_plan" in plan_data
    assert "comparison" in plan_data

    # 3e. G-code prototype
    resp_nc = client.get(f"/api/projects/{proj_id}/gcode", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp_nc.status_code == 200
    assert "PROTOTYPE - NOT VERIFIED ON A MACHINE" in resp_nc.text

    # 3f. Tool check & auto-change
    resp_tc = client.post(f"/api/projects/{proj_id}/check-tools", headers={"Authorization": f"Bearer {worker_token}"})
    assert resp_tc.status_code == 200
    assert "inspected_tools" in resp_tc.json()

    # 4. Request Machine
    resp_req = client.post(
        f"/api/projects/{proj_id}/request-machine",
        json={"requested_machine_id": 1, "note": "Priority Bracket Job"},
        headers={"Authorization": f"Bearer {worker_token}"}
    )
    assert resp_req.status_code == 200

    # 5. Admin Approves Request
    # Find request id
    reqs_resp = client.get("/api/admin/requests", headers={"Authorization": f"Bearer {admin_token}"})
    match_req = [r for r in reqs_resp.json() if r["project_id"] == proj_id][0]
    
    appr_resp = client.post(
        f"/api/admin/requests/{match_req['id']}/approve",
        json={
            "machine_id": 2,  # Machine 2 is idle
            "scheduled_start": (datetime.now(timezone.utc) + timedelta(days=5)).isoformat(),
            "scheduled_end": (datetime.now(timezone.utc) + timedelta(days=5, hours=1)).isoformat()
        },
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert appr_resp.status_code == 200

    # 6. Worker Deploys Job
    deploy_resp = client.post(f"/api/projects/{proj_id}/deploy", headers={"Authorization": f"Bearer {worker_token}"})
    assert deploy_resp.status_code == 200
    assert deploy_resp.json()["simulated"] is True
