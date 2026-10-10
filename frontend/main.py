import os
import sys
import asyncio
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))
sys.path.insert(0, str(ROOT_DIR / "frontend"))

from nicegui import app, ui

from app.config import settings
from app.session import is_authenticated, get_current_user
from app.pages.public.intro import register_intro_page
from app.pages.public.overview import register_overview_page
from app.pages.login import register_login_page
from app.pages.admin.dashboard import register_admin_dashboard
from app.pages.admin.machine_details import register_machine_details_page
from app.pages.admin.worker_details import register_worker_details_page
from app.pages.admin.machine_requests import register_machine_requests_page
from app.pages.worker.dashboard import register_worker_dashboard
from app.pages.worker.design_details import register_design_details_page
from app.pages.worker.equipment_details import register_equipment_details_page
from app.pages.worker.project_history import register_project_history_page
from app.pages.worker.project_progress import register_project_progress_page
from app.pages.worker.new_project.wizard import register_new_project_wizard
from app.pages.worker.tools_step import register_tools_step_page
from app.pages.worker.job_slip import register_job_slip_page

# Serve static directory
static_dir = Path(__file__).resolve().parent / "static"
app.add_static_files("/static", str(static_dir))

out_dir = Path(__file__).resolve().parent.parent / "out"
out_dir.mkdir(parents=True, exist_ok=True)
app.add_static_files("/meshes", str(out_dir))

@app.get("/manifest.json")
async def get_manifest():
    manifest_path = Path(__file__).resolve().parent / "static" / "manifest.json"
    if manifest_path.exists():
        return FileResponse(manifest_path, media_type="application/manifest+json")
    return {"name": "MECHNOVA"}


import httpx
from fastapi import UploadFile, File, Form, Response, HTTPException, Body
from fastapi.responses import FileResponse

CAD_SERVICE_URL = "http://localhost:8001"

@app.post("/api/cad/process")
async def proxy_cad_process(
    file: UploadFile = File(...),
    length: float = Form(100.0),
    width: float = Form(60.0),
    height: float = Form(20.0)
):
    try:
        content = await file.read()
        from app.services.cad_engine import process_cad_model
        res_json = await process_cad_model(
            content,
            file.filename,
            length=length,
            width=width,
            height=height
        )
        mesh_url = res_json.get("meshUrl", "")
        if mesh_url.startswith("/meshes/"):
            mesh_id = mesh_url.replace("/meshes/", "")
            res_json["meshUrl"] = f"/api/cad/mesh/{mesh_id}"
        return res_json
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cad/mesh/{mesh_id}")
async def proxy_cad_mesh(mesh_id: str):
    root_out = Path(__file__).resolve().parent.parent / "out" / mesh_id
    if root_out.exists():
        return FileResponse(root_out, media_type="model/stl", filename=mesh_id)
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{CAD_SERVICE_URL}/meshes/{mesh_id}")
        if resp.status_code == 200:
            return Response(content=resp.content, media_type="model/stl")
    raise HTTPException(status_code=404, detail="Mesh not found")

from app.services.project_service import (
    create_project, get_project, list_projects, update_project_status,
    run_analysis_background, update_feature_enabled
)
from pydantic import BaseModel
from typing import Optional

class ProjectCreateRequest(BaseModel):
    partName: str = "Aerospace Mount Bracket"
    material: str = "Aluminum 6061-T6"
    length: float = 100.0
    width: float = 60.0
    height: float = 20.0

@app.post("/api/projects")
async def api_create_project(req: ProjectCreateRequest):
    pid = create_project(req.partName, req.material, req.length, req.width, req.height)
    return {"id": pid}

@app.get("/api/projects")
async def api_list_projects():
    return list_projects()

@app.post("/api/projects/{id}/model", status_code=202)
async def api_upload_project_model(id: str, file: UploadFile = File(...)):
    proj = get_project(id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    content = await file.read()
    # Trigger background analysis
    asyncio.create_task(run_analysis_background(id, content, file.filename))
    return {"status": "ANALYZING", "id": id}

@app.get("/api/projects/{id}")
async def api_get_project(id: str):
    proj = get_project(id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

class FeaturePatchRequest(BaseModel):
    enabled: bool

@app.patch("/api/projects/{id}/features/{fid}")
async def api_patch_project_feature(id: str, fid: str, req: FeaturePatchRequest):
    updated = await update_feature_enabled(id, fid, req.enabled)
    if not updated:
        raise HTTPException(status_code=404, detail="Project or feature not found")
    return updated

@app.get("/api/projects/{id}/mesh")
async def api_get_project_mesh(id: str):
    proj = get_project(id)
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    mesh_path = proj.get("meshPath")
    if mesh_path and os.path.exists(mesh_path):
        return FileResponse(mesh_path, media_type="model/stl", filename=f"{id}.stl")
    mesh_url = proj.get("mesh_url")
    if mesh_url:
        mesh_filename = os.path.basename(mesh_url)
        local_path = Path(__file__).resolve().parent.parent / "out" / mesh_filename
        if local_path.exists():
            return FileResponse(local_path, media_type="model/stl", filename=f"{id}.stl")
    raise HTTPException(status_code=404, detail="Mesh file not found for project")

# Tool Crib Endpoints
from app.services.project_service import (
    get_tools, get_tool, update_tool, auto_select_tools, update_tool_selection,
    confirm_project_tools, update_project_stock, get_project_summary, create_machine_request
)

@app.get("/api/tools")
async def api_get_tools():
    return get_tools()

@app.patch("/api/tools/{id}")
async def api_patch_tool(id: str, updates: dict = Body(...)):
    t = update_tool(id, updates)
    if not t:
        raise HTTPException(status_code=404, detail="Tool not found")
    return t

@app.post("/api/projects/{id}/tools/auto-select")
async def api_project_auto_select_tools(id: str):
    res = await auto_select_tools(id)
    if not res:
        raise HTTPException(status_code=400, detail="Could not auto-select tools")
    return res

class ToolSelectionRequest(BaseModel):
    assignments: list[dict]

@app.put("/api/projects/{id}/tools/selection")
async def api_project_update_tool_selection(id: str, req: ToolSelectionRequest):
    try:
        updated = update_tool_selection(id, req.assignments)
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{id}/tools/confirm")
async def api_project_confirm_tools(id: str):
    try:
        res = confirm_project_tools(id)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

class StockUpdateRequest(BaseModel):
    size: list[float]

@app.put("/api/projects/{id}/stock")
async def api_project_update_stock(id: str, req: StockUpdateRequest):
    res = await update_project_stock(id, req.size)
    if not res:
        raise HTTPException(status_code=400, detail="Could not update stock")
    return res

@app.get("/api/projects/{id}/summary")
async def api_project_summary(id: str):
    s = get_project_summary(id)
    if not s:
        raise HTTPException(status_code=404, detail="Project not found")
    return s

@app.post("/api/projects/{id}/machine-request")
async def api_project_machine_request(id: str, payload: dict = Body(default={})):
    try:
        req = create_machine_request(id, payload.get("requested_by", "WRK-001"))
        return req
    except ValueError as e:
        err_msg = str(e)
        if "no longer available" in err_msg.lower():
            raise HTTPException(status_code=409, detail=err_msg)
        raise HTTPException(status_code=400, detail=err_msg)

class RawMaterialUpdateRequest(BaseModel):
    material: str = "Aluminum 6061-T6"
    length: float = 100.0
    width: float = 60.0
    height: float = 20.0
    part_name: Optional[str] = None

@app.put("/api/projects/{id}/raw-material")
async def api_update_project_raw_material(id: str, req: RawMaterialUpdateRequest):
    try:
        from app.services.project_service import update_project_raw_material
        return update_project_raw_material(id, req.material, req.length, req.width, req.height, req.part_name)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

class SlipActionRequest(BaseModel):
    action: str = "confirm"
    operator: str = "Elena Rostova"
    employee_id: str = "WRK-001"

@app.post("/api/projects/{id}/slip-action")
async def api_project_slip_action(id: str, req: SlipActionRequest):
    try:
        from app.services.project_service import save_job_slip_action
        return save_job_slip_action(id, req.action, req.operator, req.employee_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))



# Register Pages
register_intro_page()
register_overview_page()
register_login_page()
register_admin_dashboard()
register_machine_details_page()
register_worker_details_page()
register_machine_requests_page()
register_worker_dashboard()
register_design_details_page()
register_equipment_details_page()
register_project_history_page()
register_project_progress_page()
register_new_project_wizard()
register_tools_step_page()
register_job_slip_page()


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        port=settings.PORT,
        storage_secret=settings.STORAGE_SECRET,
        title="Mechnova CAD-to-CNC Platform",
        favicon="🛠️",
        reload=True
    )
