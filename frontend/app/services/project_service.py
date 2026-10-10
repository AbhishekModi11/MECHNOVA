"""Project service and SQLite persistence for MECHNOVA projects, tool crib inventory,
and machine requests.
"""
import os
import json
import sqlite3
import hashlib
import uuid
import datetime
from pathlib import Path
import httpx
import asyncio

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = WORKSPACE_ROOT / "projects.db"
CAD_SERVICE_URL = "http://127.0.0.1:8001"
SEED_TOOLS_PATH = WORKSPACE_ROOT / "cad_service" / "seed_tools.json"
if not SEED_TOOLS_PATH.exists():
    SEED_TOOLS_PATH = Path("cad_service/seed_tools.json").resolve()


def init_db():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
            project_no TEXT,
            part_name TEXT,
            material TEXT,
            length REAL,
            width REAL,
            height REAL,
            status TEXT,
            mesh_path TEXT,
            mesh_url TEXT,
            file_name TEXT,
            file_sha TEXT,
            thumbnail TEXT,
            analysis_json TEXT,
            tool_selection_json TEXT,
            tools_confirmed INTEGER DEFAULT 0,
            stock_json TEXT,
            savings_json TEXT,
            created_at TEXT
        )
    """)

    # Tools Crib Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tools (
            id TEXT PRIMARY KEY,
            name TEXT,
            type TEXT,
            diameter REAL,
            flutes INTEGER,
            coating TEXT,
            flute_length REAL,
            qty INTEGER,
            wear_pct REAL,
            damaged INTEGER DEFAULT 0,
            location TEXT,
            status TEXT DEFAULT 'AVAILABLE'
        )
    """)

    # Machine Requests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS machine_requests (
            id TEXT PRIMARY KEY,
            request_no TEXT,
            project_id TEXT,
            requested_by TEXT,
            status TEXT DEFAULT 'PENDING',
            snapshot_json TEXT,
            created_at TEXT
        )
    """)

    # Migrations for suggested tools, DFM, G-code and Job Slip snapshots
    for col_def in [
        ("suggested_tools_json", "TEXT"),
        ("dfm_warnings_json", "TEXT"),
        ("gcode_preview", "TEXT"),
        ("operator", "TEXT DEFAULT 'Elena Rostova'"),
        ("employee_id", "TEXT DEFAULT 'WRK-001'"),
        ("confirmed_at", "TEXT"),
        ("requested_at", "TEXT"),
        ("slip_snapshot_json", "TEXT")
    ]:
        try:
            cursor.execute(f"ALTER TABLE projects ADD COLUMN {col_def[0]} {col_def[1]}")
        except Exception:
            pass

    # Seed tools if table is empty
    cursor.execute("SELECT COUNT(*) FROM tools")
    count = cursor.fetchone()[0]
    if count == 0 and SEED_TOOLS_PATH.exists():
        with open(SEED_TOOLS_PATH, "r", encoding="utf-8") as f:
            seed_tools = json.load(f)
        for t in seed_tools:
            cursor.execute("""
                INSERT OR REPLACE INTO tools (id, name, type, diameter, flutes, coating, flute_length, qty, wear_pct, damaged, location, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                t["id"], t["name"], t["type"], float(t.get("diameter", 0.0)),
                int(t.get("flutes", 1)), t.get("coating", "uncoated"),
                float(t.get("flute_length", 0.0)), int(t.get("qty", 1)),
                float(t.get("wear_pct", 0.0)), 1 if t.get("damaged") else 0,
                t.get("location", "T01"), t.get("status", "AVAILABLE")
            ))

    conn.commit()
    conn.close()


init_db()

_ACTIVE_PROJECT_ID: str | None = None


def get_active_project_id() -> str | None:
    global _ACTIVE_PROJECT_ID
    return _ACTIVE_PROJECT_ID


def set_active_project_id(pid: str | None):
    global _ACTIVE_PROJECT_ID
    _ACTIVE_PROJECT_ID = pid


def next_project_no(cursor) -> str:
    year = datetime.datetime.utcnow().year
    cursor.execute("SELECT COUNT(*) FROM projects")
    seq = cursor.fetchone()[0] + 1
    return f"MN-{year}-{seq:04d}"


def create_project(part_name: str, material: str, length: float, width: float, height: float, file_name: str = None) -> str:
    pid = str(uuid.uuid4())[:8]
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()
    p_no = next_project_no(cursor)
    cursor.execute("""
        INSERT INTO projects (id, project_no, part_name, material, length, width, height, status, file_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'DRAFT', ?, ?)
    """, (pid, p_no, part_name, material, length, width, height, file_name or "bracket.stl", now))
    conn.commit()
    conn.close()
    return pid


from cad_service.suggested_tools import suggest_tools_for_project, generate_gcode_preview


def get_project(pid: str) -> dict | None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (pid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    d = dict(row)
    analysis = json.loads(d["analysis_json"]) if d.get("analysis_json") else None
    tool_sel = json.loads(d["tool_selection_json"]) if d.get("tool_selection_json") else None
    stock = json.loads(d["stock_json"]) if d.get("stock_json") else None
    savings_data = json.loads(d["savings_json"]) if d.get("savings_json") else None
    suggested_tools_data = json.loads(d["suggested_tools_json"]) if d.get("suggested_tools_json") else None
    dfm_warnings = json.loads(d["dfm_warnings_json"]) if d.get("dfm_warnings_json") else []
    gcode = d.get("gcode_preview") or ""
    slip_snapshot = json.loads(d["slip_snapshot_json"]) if d.get("slip_snapshot_json") else None

    # Compute suggested tools on-the-fly if missing and analysis exists
    if not suggested_tools_data and analysis:
        try:
            feats = analysis.get("features", [])
            bbox = analysis.get("bbox", [d["length"], d["width"], d["height"]])
            stock_dims = stock or [d["length"], d["width"], d["height"]]
            st_res = suggest_tools_for_project(d["material"], stock_dims, feats, bbox)
            suggested_tools_data = st_res.get("tools", [])
            dfm_warnings = st_res.get("dfm_warnings", [])
            gcode = generate_gcode_preview(d.get("project_no") or f"MN-2026-{d['id'][:4]}", d["material"], suggested_tools_data, feats)
            cursor.execute("""
                UPDATE projects SET suggested_tools_json = ?, dfm_warnings_json = ?, gcode_preview = ? WHERE id = ?
            """, (json.dumps(suggested_tools_data), json.dumps(dfm_warnings), gcode, pid))
            conn.commit()
        except Exception:
            pass

    conn.close()

    return {
        "id": d["id"],
        "project_no": d.get("project_no") or f"MN-2026-{d['id'][:4]}",
        "partName": d["part_name"],
        "material": d["material"],
        "dims": [d["length"], d["width"], d["height"]],
        "length": d["length"],
        "width": d["width"],
        "height": d["height"],
        "status": d["status"],
        "mesh_url": d["mesh_url"],
        "meshPath": d["mesh_path"],
        "file_name": d.get("file_name") or "bracket.stl",
        "thumbnail": d.get("thumbnail"),
        "analysis": analysis,
        "tool_selection": tool_sel,
        "suggested_tools": suggested_tools_data or [],
        "dfm_warnings": dfm_warnings or [],
        "gcode_preview": gcode,
        "operator": d.get("operator") or "Elena Rostova",
        "employee_id": d.get("employee_id") or "WRK-001",
        "confirmed_at": d.get("confirmed_at"),
        "requested_at": d.get("requested_at"),
        "slip_snapshot": slip_snapshot,
        "tools_confirmed": bool(d.get("tools_confirmed", 0)),
        "stock": stock or [d["length"], d["width"], d["height"]],
        "savings": savings_data,
        "createdAt": d["created_at"]
    }


def list_projects() -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, mr.status AS request_status, mr.request_no AS mr_no
        FROM projects p
        LEFT JOIN machine_requests mr ON p.id = mr.project_id
        ORDER BY p.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    result = []
    for row in rows:
        d = dict(row)
        analysis = json.loads(d["analysis_json"]) if d.get("analysis_json") else None
        tool_sel = json.loads(d["tool_selection_json"]) if d.get("tool_selection_json") else None
        result.append({
            "id": d["id"],
            "project_no": d.get("project_no") or f"MN-2026-{d['id'][:4]}",
            "partName": d["part_name"],
            "material": d["material"],
            "dims": [d["length"], d["width"], d["height"]],
            "status": d["status"],
            "request_status": d.get("request_status"),
            "request_no": d.get("mr_no"),
            "mesh_url": d["mesh_url"],
            "analysis": analysis,
            "tools_confirmed": bool(d.get("tools_confirmed", 0)),
            "createdAt": d["created_at"]
        })
    return result


def update_project_status(pid: str, status: str, mesh_path: str = None, mesh_url: str = None, analysis_dict: dict = None, file_sha: str = None, thumbnail: str = None):
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    analysis_json = json.dumps(analysis_dict) if analysis_dict is not None else None
    
    updates = ["status = ?"]
    params = [status]
    if mesh_path is not None:
        updates.append("mesh_path = ?")
        params.append(mesh_path)
    if mesh_url is not None:
        updates.append("mesh_url = ?")
        params.append(mesh_url)
    if analysis_json is not None:
        updates.append("analysis_json = ?")
        params.append(analysis_json)
    if file_sha is not None:
        updates.append("file_sha = ?")
        params.append(file_sha)
    if thumbnail is not None:
        updates.append("thumbnail = ?")
        params.append(thumbnail)
    params.append(pid)
    
    cursor.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()


def update_project_raw_material(pid: str, material: str, length: float, width: float, height: float, part_name: str = None) -> dict:
    """Updates project raw material dimensions, validates fit against part bounding box,
    and automatically re-computes suggested tools and G-code preview."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (pid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Project not found")
    
    d = dict(row)
    analysis = json.loads(d["analysis_json"]) if d.get("analysis_json") else {}
    feats = analysis.get("features", [])
    bbox = analysis.get("bbox", [length, width, height])
    stock_dims = [float(length), float(width), float(height)]

    # Compute tool suggestions and DFM warnings
    st_res = suggest_tools_for_project(material, stock_dims, feats, bbox)
    suggested_tools = st_res.get("tools", [])
    dfm_warnings = st_res.get("dfm_warnings", [])
    p_no = d.get("project_no") or f"MN-2026-{pid[:4]}"
    gcode = generate_gcode_preview(p_no, material, suggested_tools, feats)

    updates = [
        "material = ?", "length = ?", "width = ?", "height = ?",
        "suggested_tools_json = ?", "dfm_warnings_json = ?", "gcode_preview = ?"
    ]
    params = [
        material, float(length), float(width), float(height),
        json.dumps(suggested_tools), json.dumps(dfm_warnings), gcode
    ]
    if part_name:
        updates.append("part_name = ?")
        params.append(part_name)
    params.append(pid)

    cursor.execute(f"UPDATE projects SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()
    conn.close()

    return get_project(pid)


def save_job_slip_action(pid: str, action: str, operator_name: str = "Elena Rostova", employee_id: str = "WRK-001") -> dict:
    """Saves operator confirmation or machine request, transitions status,
    and stores an immutable complete snapshot of the Job Slip."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (pid,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError("Project not found")
    
    d = dict(row)
    now = datetime.datetime.utcnow().isoformat()
    status = "CONFIRMED_BY_OPERATOR" if action == "confirm" else "MACHINE_REQUESTED"

    proj = get_project(pid)
    # Build immutable snapshot
    snapshot = {
        "project_no": proj.get("project_no"),
        "project_id": pid,
        "operator_name": operator_name,
        "employee_id": employee_id,
        "date_time": now,
        "confirmed_at": now if action == "confirm" else None,
        "requested_at": now if action == "request" else None,
        "action": action,
        "status": status,
        "part_name": proj.get("partName"),
        "model_file": proj.get("file_name"),
        "thumbnail": proj.get("thumbnail"),
        "bbox": proj.get("analysis", {}).get("bbox", proj.get("dims")),
        "raw_material": {
            "name": proj.get("material"),
            "length": proj.get("length"),
            "width": proj.get("width"),
            "height": proj.get("height"),
            "thickness": proj.get("height")
        },
        "features": proj.get("analysis", {}).get("features", []),
        "features_summary": proj.get("analysis", {}).get("summary", {}),
        "suggested_tools": proj.get("suggested_tools", []),
        "dfm_warnings": proj.get("dfm_warnings", []),
        "gcode_preview": proj.get("gcode_preview", ""),
        "total_machining_min": round(sum(t.get("est_time_sec", 30) for t in proj.get("suggested_tools", [])) / 60.0, 1)
    }

    snap_json = json.dumps(snapshot)
    if action == "confirm":
        cursor.execute("""
            UPDATE projects SET status = ?, operator = ?, employee_id = ?, confirmed_at = ?, slip_snapshot_json = ?
            WHERE id = ?
        """, (status, operator_name, employee_id, now, snap_json, pid))
    else:
        # Machine Request
        year = datetime.datetime.utcnow().year
        cursor.execute("SELECT COUNT(*) FROM machine_requests")
        seq = cursor.fetchone()[0] + 1
        req_no = f"MR-{year}-{seq:04d}"
        cursor.execute("""
            INSERT INTO machine_requests (id, request_no, project_id, requested_by, status, snapshot_json, created_at)
            VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
        """, (str(uuid.uuid4())[:8], req_no, pid, operator_name, snap_json, now))
        cursor.execute("""
            UPDATE projects SET status = ?, operator = ?, employee_id = ?, requested_at = ?, slip_snapshot_json = ?
            WHERE id = ?
        """, (status, operator_name, employee_id, now, snap_json, pid))

    conn.commit()
    conn.close()
    return snapshot


def find_cached_analysis(file_sha: str, material: str):
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE file_sha = ? AND material = ? AND status = 'READY' LIMIT 1", (file_sha, material))
    row = cursor.fetchone()
    conn.close()
    if row:
        d = dict(row)
        if d.get("analysis_json"):
            return {
                "mesh_path": d["mesh_path"],
                "mesh_url": d["mesh_url"],
                "analysis": json.loads(d["analysis_json"])
            }
    return None


async def run_analysis_background(pid: str, file_bytes: bytes, filename: str):
    try:
        update_project_status(pid, "ANALYZING")
        proj = get_project(pid)
        if not proj:
            return
        
        file_sha = hashlib.sha256(file_bytes).hexdigest()
        material = proj.get("material", "Aluminum 6061-T6")
        
        # Check cache
        cached = find_cached_analysis(file_sha, material)
        if cached:
            update_project_status(
                pid, "READY",
                mesh_path=cached["mesh_path"],
                mesh_url=cached["mesh_url"],
                analysis_dict=cached["analysis"],
                file_sha=file_sha
            )
            # Auto-select tools immediately
            await auto_select_tools(pid)
            return

        from app.services.cad_engine import analyze_cad_model
        try:
            analysis = await analyze_cad_model(
                file_bytes=file_bytes,
                filename=filename,
                material=material,
                length=float(proj.get("length", 100.0)),
                width=float(proj.get("width", 60.0)),
                height=float(proj.get("height", 20.0))
            )
        except Exception as e:
            update_project_status(pid, "FAILED", analysis_dict={"error": str(e)})
            return

        mesh_url = analysis.get("mesh_url", "")
        if mesh_url.startswith("/meshes/"):
            mesh_id = mesh_url.replace("/meshes/", "")
            mesh_url = f"/api/cad/mesh/{mesh_id}"

        analysis["mesh_url"] = mesh_url
        mesh_path = os.path.join(str(Path(__file__).resolve().parent.parent.parent / "out"), os.path.basename(analysis.get("mesh_url", "")))
        update_project_status(
            pid, "READY",
            mesh_path=mesh_path,
            mesh_url=mesh_url,
            analysis_dict=analysis,
            file_sha=file_sha
        )
        # Auto-select tools immediately
        await auto_select_tools(pid)
    except Exception as ex:
        update_project_status(pid, "FAILED", analysis_dict={"error": str(ex)})


# =========================================================================
# TOOL CRIB CRUD
# =========================================================================

def get_tools() -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["damaged"] = bool(d.get("damaged", 0))
        w = d.get("wear_pct", 0)
        cond = "DAMAGED" if d["damaged"] else ("GOOD" if w < 50 else ("FAIR" if w <= 80 else "WORN"))
        d["condition"] = cond
        result.append(d)
    return result


def get_tool(tool_id: str) -> dict | None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tools WHERE id = ?", (tool_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    d = dict(row)
    d["damaged"] = bool(d.get("damaged", 0))
    w = d.get("wear_pct", 0)
    cond = "DAMAGED" if d["damaged"] else ("GOOD" if w < 50 else ("FAIR" if w <= 80 else "WORN"))
    d["condition"] = cond
    return d


def update_tool(tool_id: str, updates: dict) -> dict | None:
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    fields = []
    vals = []
    for k, v in updates.items():
        if k in ("wear_pct", "damaged", "status", "qty", "location"):
            fields.append(f"{k} = ?")
            vals.append(1 if (k == "damaged" and v) else (0 if k == "damaged" else v))
    if not fields:
        conn.close()
        return get_tool(tool_id)
    vals.append(tool_id)
    cursor.execute(f"UPDATE tools SET {', '.join(fields)} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    return get_tool(tool_id)


# =========================================================================
# AUTO-SELECT TOOLS & CONFIRMATION
# =========================================================================

async def auto_select_tools(pid: str) -> dict | None:
    proj = get_project(pid)
    if not proj or not proj.get("analysis"):
        return None
    
    plan = proj["analysis"].get("plan", {})
    required = plan.get("tools", [])
    inventory = get_tools()
    material = proj.get("material", "Aluminum 6061-T6")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{CAD_SERVICE_URL}/match-tools", json={
            "required": required,
            "inventory": inventory,
            "material": material
        })
        if resp.status_code != 200:
            return None
        match_data = resp.json()

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET tool_selection_json = ? WHERE id = ?", (json.dumps(match_data), pid))
    conn.commit()
    conn.close()

    # Also compute initial savings with default stock
    bbox = proj["analysis"].get("bbox", proj.get("dims", [100, 60, 20]))
    vol = proj["analysis"].get("part_volume_mm3", 0.0)
    await update_project_stock(pid, [round(b + 6, 1) for b in bbox])

    return match_data


def update_tool_selection(pid: str, assignments: list[dict]) -> dict | None:
    proj = get_project(pid)
    if not proj or not proj.get("tool_selection"):
        return None
    
    current_sel = proj["tool_selection"]
    # Check that tools are not duplicated and exist
    inventory = {t["id"]: t for t in get_tools()}
    used_ids = set()

    for item in assignments:
        req_id = item.get("required_id")
        tool_id = item.get("tool_id")
        if not tool_id:
            continue
        if tool_id in used_ids:
            raise ValueError(f"Tool {tool_id} cannot be assigned twice (quantity exceeded)!")
        used_ids.add(tool_id)
        
        tool = inventory.get(tool_id)
        if not tool or tool.get("damaged") or tool.get("qty", 0) <= 0:
            raise ValueError(f"Tool {tool_id} is unavailable or damaged!")

        for a in current_sel.get("assignments", []):
            if a["required_id"] == req_id:
                a["assigned"] = tool
                a["status"] = "READY" if tool["condition"] == "GOOD" else "CAUTION"
                a["notes"] = [f"Operator manually selected {tool['name']}"]

    # Recompute summary
    summary = {s: sum(x["status"] == s for x in current_sel["assignments"]) for s in ("READY", "CAUTION", "SUBSTITUTE", "MISSING")}
    current_sel["summary"] = summary
    current_sel["can_proceed"] = (summary.get("MISSING", 0) == 0)

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET tool_selection_json = ? WHERE id = ?", (json.dumps(current_sel), pid))
    conn.commit()
    conn.close()

    return current_sel


def confirm_project_tools(pid: str) -> dict:
    proj = get_project(pid)
    if not proj:
        raise ValueError("Project not found")
    tool_sel = proj.get("tool_selection", {})
    if tool_sel.get("summary", {}).get("MISSING", 0) > 0:
        raise ValueError("Cannot confirm tools while tools are MISSING from inventory!")
    
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("UPDATE projects SET tools_confirmed = 1 WHERE id = ?", (pid,))
    conn.commit()
    conn.close()
    return {"status": "CONFIRMED", "tools_confirmed": True}


async def update_project_stock(pid: str, stock: list[float]) -> dict | None:
    proj = get_project(pid)
    if not proj or not proj.get("analysis"):
        return None
    
    analysis = proj["analysis"]
    bbox = analysis.get("bbox", proj.get("dims", [100, 60, 20]))
    vol = analysis.get("part_volume_mm3", 0.0)
    material = proj.get("material", "Aluminum 6061-T6")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{CAD_SERVICE_URL}/savings", json={
            "analysis": analysis,
            "material": material,
            "bbox": bbox,
            "part_volume_mm3": vol,
            "user_stock": stock
        })
        if resp.status_code != 200:
            return None
        savings_data = resp.json()

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE projects SET stock_json = ?, savings_json = ? WHERE id = ?
    """, (json.dumps(stock), json.dumps(savings_data), pid))
    conn.commit()
    conn.close()

    return savings_data


def update_feature_enabled(pid: str, fid: str, enabled: bool) -> dict | None:
    proj = get_project(pid)
    if not proj or not proj.get("analysis"):
        return None
    analysis = proj["analysis"]
    feats = analysis.get("features", [])
    found = False
    for f in feats:
        if f.get("id") == fid:
            f["enabled"] = enabled
            found = True
            break
    if not found:
        return None
    
    holes = [f for f in feats if f["kind"] in ("hole", "blind_hole") and f.get("enabled", True)]
    pockets = [f for f in feats if f["kind"] in ("pocket", "slot", "window") and f.get("enabled", True)]
    analysis["summary"]["holes"] = len(holes)
    analysis["summary"]["pockets"] = len(pockets)
    analysis["summary"]["through"] = sum(f["through"] for f in feats if f.get("enabled", True))
    
    # Recompute plan
    try:
        import httpx as sync_httpx
        resp = sync_httpx.post(f"{CAD_SERVICE_URL}/recompute_plan", json={
            "analysis": analysis,
            "material": proj.get("material", "Aluminum 6061-T6"),
            "bbox": analysis.get("bbox", proj.get("dims", [100, 60, 20]))
        }, timeout=10.0)
        if resp.status_code == 200:
            analysis["plan"] = resp.json().get("plan", analysis.get("plan"))
    except Exception:
        pass
    
    update_project_status(pid, "READY", analysis_dict=analysis)
    return analysis


# =========================================================================
# SUMMARY & MACHINE REQUEST
# =========================================================================

def get_project_summary(pid: str) -> dict | None:
    proj = get_project(pid)
    if not proj:
        return None

    analysis = proj.get("analysis") or {}
    tool_sel = proj.get("tool_selection") or {}
    savings_data = proj.get("savings") or {}
    bbox = analysis.get("bbox", proj.get("dims", [100, 60, 20]))
    stock = proj.get("stock") or savings_data.get("material", {}).get("chosen_stock", [round(b+6, 1) for b in bbox])
    
    # Tools used list
    tools_used = []
    for a in tool_sel.get("assignments", []):
        t = a.get("assigned")
        if t:
            tools_used.append({
                "required": a.get("required"),
                "crib_id": t.get("id"),
                "name": t.get("name"),
                "location": t.get("location", "T01"),
                "condition": t.get("condition", "GOOD"),
                "wear_pct": t.get("wear_pct", 0),
                "status": a.get("status", "READY")
            })

    return {
        "project_no": proj.get("project_no"),
        "id": pid,
        "created_at": proj.get("createdAt"),
        "operator": "WRK-001",
        "status": proj.get("status"),
        "part": {
            "name": proj.get("partName"),
            "file": proj.get("file_name", "bracket.stl"),
            "source": "stl",
            "exact": analysis.get("exact", True),
            "bbox": bbox,
            "entered_dims": proj.get("dims", [100, 60, 20]),
            "volume_mm3": analysis.get("part_volume_mm3", 330000.0),
            "thumbnail": proj.get("thumbnail")
        },
        "material": {
            "name": proj.get("material", "Aluminum 6061-T6"),
            "stock": stock,
            "stock_kg": savings_data.get("material", {}).get("chosen_kg", 2.61),
            "utilisation_pct": savings_data.get("material", {}).get("utilisation_pct", 34.2)
        },
        "features": {
            "holes": analysis.get("summary", {}).get("holes", 0),
            "pockets": analysis.get("summary", {}).get("pockets", 0),
            "setups": analysis.get("plan", {}).get("equipment", {}).get("setups", 1),
            "list": analysis.get("features", []),
            "issues": analysis.get("issues", [])
        },
        "plan": {
            "operations": analysis.get("plan", {}).get("operations", []),
            "equipment": analysis.get("plan", {}).get("equipment", {})
        },
        "tools": tools_used,
        "savings": savings_data
    }


def create_machine_request(pid: str, requested_by: str = "WRK-001") -> dict:
    """
    Submits a machine dispatch request in ONE database transaction.
    Idempotent: returns existing request if already created.
    Validates tool availability, reserves tools, and creates snapshot.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # 1. Check if request already exists for this project (Idempotent)
    cursor.execute("SELECT * FROM machine_requests WHERE project_id = ?", (pid,))
    existing = cursor.fetchone()
    if existing:
        d = dict(existing)
        d["snapshot"] = json.loads(d["snapshot_json"])
        conn.close()
        return d

    summary = get_project_summary(pid)
    if not summary:
        conn.close()
        raise ValueError("Project not found")

    # 2. Check every selected tool is still usable
    tools_used = summary.get("tools", [])
    unavailable = []
    for t in tools_used:
        cid = t.get("crib_id")
        cursor.execute("SELECT * FROM tools WHERE id = ?", (cid,))
        row = cursor.fetchone()
        if not row:
            unavailable.append(cid)
            continue
        tool = dict(row)
        if tool.get("qty", 0) <= 0 or tool.get("status") != "AVAILABLE" or tool.get("damaged"):
            unavailable.append(f"{cid} ({tool.get('name')})")

    if unavailable:
        conn.close()
        raise ValueError(f"Tools no longer available: {', '.join(unavailable)}")

    # 3. Generate Request Number
    year = datetime.datetime.utcnow().year
    cursor.execute("SELECT COUNT(*) FROM machine_requests")
    seq = cursor.fetchone()[0] + 1
    req_no = f"MR-{year}-{seq:04d}"
    req_id = str(uuid.uuid4())[:8]
    now = datetime.datetime.utcnow().isoformat()

    # 4. Reserve Tools (set status = RESERVED or reduce qty)
    for t in tools_used:
        cid = t.get("crib_id")
        cursor.execute("UPDATE tools SET status = 'RESERVED' WHERE id = ?", (cid,))

    # 5. Insert Machine Request & Set Project Status = REQUESTED
    snapshot_json = json.dumps(summary)
    cursor.execute("""
        INSERT INTO machine_requests (id, request_no, project_id, requested_by, status, snapshot_json, created_at)
        VALUES (?, ?, ?, ?, 'PENDING', ?, ?)
    """, (req_id, req_no, pid, requested_by, snapshot_json, now))

    cursor.execute("UPDATE projects SET status = 'REQUESTED' WHERE id = ?", (pid,))

    conn.commit()
    conn.close()

    return {
        "id": req_id,
        "request_no": req_no,
        "project_id": pid,
        "requested_by": requested_by,
        "status": "PENDING",
        "created_at": now,
        "snapshot": summary
    }
