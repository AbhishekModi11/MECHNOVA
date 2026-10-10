from datetime import datetime, timezone
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.deps import get_current_user, require_worker
from app.models.models import User, Project, MachineRequest, Machine
from app.services.engine_service import trigger_project_analysis_async
from app.services.simulation_service import run_machine_simulation_async
from app.services.tool_wear_service import inspect_tool_conditions_for_project
from app.services.image_to_step import process_reference_image, extrude_contour_to_step

router = APIRouter(prefix="/projects", tags=["Projects"])


class DimensionsPatchRequest(BaseModel):
    length: float
    width: float
    height: float


class MaterialPatchRequest(BaseModel):
    material_id: str


class MachineRequestPayload(BaseModel):
    requested_machine_id: Optional[int] = None
    note: Optional[str] = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_project(
    background_tasks: BackgroundTasks,
    name: str = Form(...),
    material_id: str = Form("aluminum_6061"),
    source_type: str = Form("step"),  # "step" | "image_extrusion"
    extrusion_height_mm: float = Form(20.0),
    target_width_mm: float = Form(100.0),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads a CAD model (STEP) or reference image, initializes project record."""
    filename = file.filename or "upload.step"
    ext = Path(filename).suffix.lower()

    # Validate file extension
    allowed_exts = [".step", ".stp", ".png", ".jpg", ".jpeg"]
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '{ext}'. Allowed: {allowed_exts}"
        )

    upload_dir = Path(settings.UPLOAD_DIR) / f"user_{current_user.id}"
    upload_dir.mkdir(parents=True, exist_ok=True)
    saved_path = upload_dir / f"{uuid.uuid4().hex[:8]}_{filename}"

    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    actual_step_path = saved_path

    # If reference image, generate 2.5D extrusion
    if ext in [".png", ".jpg", ".jpeg"] or source_type == "image_extrusion":
        overlay_path = upload_dir / f"overlay_{saved_path.stem}.png"
        step_out_path = upload_dir / f"extruded_{saved_path.stem}.step"
        try:
            process_reference_image(saved_path, overlay_path)
            extrude_contour_to_step(saved_path, target_width_mm, extrusion_height_mm, step_out_path)
            actual_step_path = step_out_path
            source_type = "image_extrusion"
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"2.5D Image Extrusion failed: {str(e)}"
            )

    project = Project(
        owner_id=current_user.id,
        name=name,
        material_id=material_id,
        source_type=source_type,
        source_file_path=str(actual_step_path),
        dimensions={"length": target_width_mm, "width": 60.0, "height": extrusion_height_mm},
        status="draft",
        engine_status="queued",
        progress_percent=0.0
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Immediately queue engine analysis
    background_tasks.add_task(trigger_project_analysis_async, project.id)

    return {
        "id": project.id,
        "name": project.name,
        "status": project.status,
        "engine_status": project.engine_status,
        "material_id": project.material_id,
        "source_type": project.source_type,
        "created_at": project.created_at.isoformat()
    }


@router.get("")
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List projects belonging to the current user, or all projects if admin."""
    query = db.query(Project)
    if current_user.role != "admin":
        query = query.filter(Project.owner_id == current_user.id)
    
    projects = query.order_by(Project.created_at.desc()).all()
    results = []
    for p in projects:
        results.append({
            "id": p.id,
            "name": p.name,
            "material_id": p.material_id,
            "source_type": p.source_type,
            "status": p.status,
            "engine_status": p.engine_status,
            "progress_percent": p.progress_percent,
            "current_operation": p.current_operation,
            "run_id": p.run_id,
            "created_at": p.created_at.isoformat(),
            "completed_at": p.completed_at.isoformat() if p.completed_at else None
        })
    return results


@router.get("/{project_id}")
def get_project_detail(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full project details and status."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if current_user.role != "admin" and project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied to this project")

    req_data = None
    if project.machine_request:
        mr = project.machine_request
        req_data = {
            "id": mr.id,
            "status": mr.status,
            "requested_machine_id": mr.requested_machine_id,
            "scheduled_start": mr.scheduled_start.isoformat() if mr.scheduled_start else None,
            "scheduled_end": mr.scheduled_end.isoformat() if mr.scheduled_end else None,
            "note": mr.note,
            "decided_at": mr.decided_at.isoformat() if mr.decided_at else None
        }

    return {
        "id": project.id,
        "name": project.name,
        "material_id": project.material_id,
        "source_type": project.source_type,
        "dimensions": project.dimensions,
        "status": project.status,
        "engine_status": project.engine_status,
        "progress_percent": project.progress_percent,
        "current_operation": project.current_operation,
        "run_id": project.run_id,
        "error_message": project.error_message,
        "created_at": project.created_at.isoformat(),
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "machine_request": req_data
    }


@router.post("/{project_id}/analyse")
async def trigger_analysis(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually triggers or re-runs the CAD-to-CNC Optimization Engine."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    background_tasks.add_task(trigger_project_analysis_async, project.id)
    return {"message": "Engine analysis dispatched", "project_id": project.id}


@router.get("/{project_id}/model")
def get_model_glb(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Serves the generated GLB 3D tessellation file for Three.js rendering."""
    project = db.query(Project).filter(Project.id == project_id).first()
    root_dir = Path(__file__).resolve().parents[4]
    active_glb = root_dir / "frontend" / "static" / "models" / "active_model.glb"
    fallback_glb = root_dir / "out" / "model_preview.glb"

    if project and project.run_id:
        glb_path = Path(settings.RUNS_DIR) / project.run_id / "model_preview.glb"
        if glb_path.exists():
            return FileResponse(glb_path, media_type="model/gltf-binary", filename="model_preview.glb")

    if active_glb.exists():
        return FileResponse(active_glb, media_type="model/gltf-binary", filename="model_preview.glb")

    if fallback_glb.exists():
        return FileResponse(fallback_glb, media_type="model/gltf-binary", filename="model_preview.glb")

    raise HTTPException(status_code=404, detail="3D model preview not generated yet")


@router.get("/{project_id}/features")
def get_features_json(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns detected manufacturing features JSON and feature map."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.run_id:
        raise HTTPException(status_code=404, detail="Features not available")

    run_dir = Path(settings.RUNS_DIR) / project.run_id
    f_path = run_dir / "features.json"
    fm_path = run_dir / "feature_map.json"
    
    if not f_path.exists():
        raise HTTPException(status_code=404, detail="features.json not generated")

    with open(f_path, "r", encoding="utf-8") as f:
        features = json.load(f)

    feature_map = {}
    if fm_path.exists():
        with open(fm_path, "r", encoding="utf-8") as f:
            feature_map = json.load(f)

    return {"features": features, "feature_map": feature_map}


@router.get("/{project_id}/tools")
def get_tools_json(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns tool recommendations and scoring JSON."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.run_id:
        raise HTTPException(status_code=404, detail="Tool recommendations not available")

    t_path = Path(settings.RUNS_DIR) / project.run_id / "tool_recommendations.json"
    if not t_path.exists():
        raise HTTPException(status_code=404, detail="tool_recommendations.json not found")

    with open(t_path, "r", encoding="utf-8") as f:
        return json.load(f)


@router.get("/{project_id}/plan")
def get_plan_json(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns operation plan and comparison JSON."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.run_id:
        raise HTTPException(status_code=404, detail="Plan not available")

    run_dir = Path(settings.RUNS_DIR) / project.run_id
    plan_path = run_dir / "operation_plan.json"
    comp_path = run_dir / "comparison.json"

    if not plan_path.exists():
        raise HTTPException(status_code=404, detail="operation_plan.json not found")

    with open(plan_path, "r", encoding="utf-8") as f:
        plan_data = json.load(f)

    comp_data = {}
    if comp_path.exists():
        with open(comp_path, "r", encoding="utf-8") as f:
            comp_data = json.load(f)

    return {"operation_plan": plan_data, "comparison": comp_data}


@router.get("/{project_id}/report")
def get_report(
    project_id: int,
    format: str = "html",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns HTML or Markdown engineering optimization report."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.run_id:
        raise HTTPException(status_code=404, detail="Report not generated")

    run_dir = Path(settings.RUNS_DIR) / project.run_id
    fn = "report.html" if format.lower() == "html" else "report.md"
    rep_path = run_dir / fn
    
    if not rep_path.exists():
        raise HTTPException(status_code=404, detail=f"{fn} not found")

    media_type = "text/html" if format.lower() == "html" else "text/markdown"
    return FileResponse(rep_path, media_type=media_type, filename=fn)


@router.get("/{project_id}/gcode")
def get_gcode(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serves validated prototype G-code program with mandatory non-production disclaimer."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or not project.run_id:
        raise HTTPException(status_code=404, detail="Deliverables not generated")

    nc_path = Path(settings.RUNS_DIR) / project.run_id / "program_setup1.nc"
    if not nc_path.exists():
        raise HTTPException(
            status_code=404,
            detail="G-code not available (either validation failed or not generated)"
        )

    return FileResponse(nc_path, media_type="text/plain", filename=f"program_{project.name}.nc")


@router.patch("/{project_id}/dimensions")
def update_dimensions(
    project_id: int,
    payload: DimensionsPatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates physical stock / part dimensions."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.dimensions = {
        "length": payload.length,
        "width": payload.width,
        "height": payload.height
    }
    db.commit()
    return {"message": "Dimensions updated", "dimensions": project.dimensions}


@router.patch("/{project_id}/material")
def update_material(
    project_id: int,
    payload: MaterialPatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates target material and flags if material is unsupported."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    supported_materials = ["aluminum_6061", "steel_1018", "stainless_304", "abs", "nylon"]
    if payload.material_id.lower() not in supported_materials:
        raise HTTPException(
            status_code=400,
            detail=f"Material '{payload.material_id}' is not supported yet. Supported: {supported_materials}"
        )

    project.material_id = payload.material_id
    db.commit()
    return {"message": "Material updated", "material_id": project.material_id}


@router.post("/{project_id}/check-tools")
def check_tools(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Executes tool inspection sequence, wear evaluation, and automatic replacement of worn tools."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    inspection_results = inspect_tool_conditions_for_project(project, db)
    return inspection_results


@router.post("/{project_id}/request-machine")
def request_machine(
    project_id: int,
    payload: MachineRequestPayload,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submits a formal job dispatch request to shop administrators."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check if request already exists
    existing = db.query(MachineRequest).filter(MachineRequest.project_id == project_id).first()
    if existing:
        existing.status = "pending"
        existing.requested_machine_id = payload.requested_machine_id
        existing.note = payload.note
    else:
        req = MachineRequest(
            project_id=project.id,
            worker_id=current_user.id,
            requested_machine_id=payload.requested_machine_id,
            status="pending",
            note=payload.note
        )
        db.add(req)

    project.status = "requested"
    db.commit()

    return {"message": "Machine request submitted to Admin", "project_status": project.status}


@router.post("/{project_id}/deploy")
async def deploy_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deploys approved job and initiates simulated CNC machining execution."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in ["approved", "deployed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot deploy project with status '{project.status}'. Must be 'approved' by Admin."
        )

    # Launch simulation in background
    background_tasks.add_task(run_machine_simulation_async, project.id)

    return {
        "message": "Project deployed to machine. Simulated machining running.",
        "simulated": True,
        "project_id": project.id
    }


@router.get("/{project_id}/progress")
def get_project_progress(
    project_id: int,
    db: Session = Depends(get_db)
):
    """Returns real-time simulated production progress."""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project_id": project.id,
        "status": project.status,
        "progress_percent": project.progress_percent,
        "current_operation": project.current_operation,
        "simulated": True
    }
