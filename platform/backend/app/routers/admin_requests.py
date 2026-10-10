from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.deps import require_admin
from app.models.models import User, MachineRequest, Project, Machine, Schedule, Notification
from app.services.scheduling_service import create_schedule, SchedulingConflictError

router = APIRouter(prefix="/admin", tags=["Admin Requests & Scheduling"])


class ApproveRequestPayload(BaseModel):
    machine_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    note: Optional[str] = None


class RejectRequestPayload(BaseModel):
    reason: str


@router.get("/requests")
def list_machine_requests(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists machine requests with estimated cycle times from the core engine."""
    requests = db.query(MachineRequest).order_by(MachineRequest.created_at.desc()).all()
    results = []

    for req in requests:
        proj = req.project
        worker = req.worker

        # Read estimated machining time from engine comparison.json
        est_time_seconds = 0.0
        if proj and proj.run_id:
            comp_path = Path(settings.RUNS_DIR) / proj.run_id / "comparison.json"
            if comp_path.exists():
                try:
                    with open(comp_path, "r", encoding="utf-8") as f:
                        c_data = json.load(f)
                        est_time_seconds = c_data.get("optimized_time_s", 0.0)
                except Exception:
                    pass

        # Machine code/name if specified
        m_name = None
        if req.requested_machine_id:
            m = db.query(Machine).filter(Machine.id == req.requested_machine_id).first()
            if m:
                m_name = f"{m.code} - {m.name}"

        results.append({
            "id": req.id,
            "project_id": req.project_id,
            "project_name": proj.name if proj else "Unknown",
            "material_id": proj.material_id if proj else "aluminum_6061",
            "worker_id": req.worker_id,
            "worker_name": worker.name if worker else "Unknown",
            "requested_machine_id": req.requested_machine_id,
            "requested_machine_name": m_name,
            "status": req.status,
            "estimated_time_seconds": est_time_seconds,
            "note": req.note,
            "scheduled_start": req.scheduled_start.isoformat() if req.scheduled_start else None,
            "scheduled_end": req.scheduled_end.isoformat() if req.scheduled_end else None,
            "decided_at": req.decided_at.isoformat() if req.decided_at else None,
            "created_at": req.created_at.isoformat()
        })

    return results


@router.post("/requests/{request_id}/approve")
def approve_request(
    request_id: int,
    payload: ApproveRequestPayload,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Approves a machine request, validates conflict-free schedule, and notifies worker."""
    req = db.query(MachineRequest).filter(MachineRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Machine request not found")

    machine = db.query(Machine).filter(Machine.id == payload.machine_id).first()
    if not machine:
        raise HTTPException(status_code=404, detail="Selected machine does not exist")

    # Enforce conflict check & schedule creation
    try:
        schedule = create_schedule(
            machine_id=payload.machine_id,
            project_id=int(req.project_id),
            start=payload.scheduled_start,
            end=payload.scheduled_end,
            db=db
        )
    except SchedulingConflictError as ce:
        suggested = None
        if ce.suggested_slot:
            suggested = {
                "start": ce.suggested_slot[0].isoformat(),
                "end": ce.suggested_slot[1].isoformat()
            }
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "message": str(ce),
                "suggested_slot": suggested
            }
        )

    # Update request and project
    req.status = "approved"
    req.admin_id = admin.id
    req.requested_machine_id = payload.machine_id
    req.scheduled_start = payload.scheduled_start
    req.scheduled_end = payload.scheduled_end
    req.note = payload.note
    req.decided_at = datetime.now(timezone.utc)

    if req.project:
        setattr(req.project, "status", "approved")

    # Send Notification to Worker
    notif = Notification(
        user_id=req.worker_id,
        type="request_approved",
        message=f"Your machine request for '{req.project.name}' on {machine.name} was APPROVED for {payload.scheduled_start.strftime('%Y-%m-%d %H:%M')}.",
        read=False,
        link=f"/projects/{req.project_id}"
    )
    db.add(notif)
    db.commit()

    return {
        "message": f"Request approved. Schedule confirmed on {machine.name}.",
        "schedule_id": schedule.id,
        "machine_id": machine.id,
        "scheduled_start": schedule.start.isoformat(),
        "scheduled_end": schedule.end.isoformat()
    }


@router.post("/requests/{request_id}/reject")
def reject_request(
    request_id: int,
    payload: RejectRequestPayload,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Rejects a machine request with an explanation note and notifies worker."""
    req = db.query(MachineRequest).filter(MachineRequest.id == request_id).first()
    if not req:
        raise HTTPException(status_code=404, detail="Machine request not found")

    req.status = "rejected"
    req.admin_id = admin.id
    req.note = payload.reason
    req.decided_at = datetime.now(timezone.utc)

    if req.project:
        setattr(req.project, "status", "rejected")

    notif = Notification(
        user_id=req.worker_id,
        type="request_rejected",
        message=f"Machine request for '{req.project.name}' was rejected: {payload.reason}",
        read=False,
        link=f"/projects/{req.project_id}"
    )
    db.add(notif)
    db.commit()

    return {"message": "Request rejected", "reason": payload.reason}


@router.get("/schedule")
def get_schedule_timeline(
    machine_id: Optional[int] = None,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Returns calendar/timeline reservations for shop CNC machines."""
    query = db.query(Schedule)
    if machine_id:
        query = query.filter(Schedule.machine_id == machine_id)
    
    schedules = query.order_by(Schedule.start.asc()).all()
    results = []
    for s in schedules:
        results.append({
            "id": s.id,
            "machine_id": s.machine_id,
            "machine_name": s.machine.name if s.machine else f"Machine #{s.machine_id}",
            "project_id": s.project_id,
            "project_name": s.project.name if s.project else f"Project #{s.project_id}",
            "worker_name": s.project.owner.name if (s.project and s.project.owner) else "Unknown",
            "start": s.start.isoformat(),
            "end": s.end.isoformat()
        })
    return results
