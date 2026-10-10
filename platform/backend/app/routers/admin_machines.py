from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import require_admin
from app.models.models import User, Machine, Project

router = APIRouter(prefix="/admin/machines", tags=["Admin Machines"])


@router.get("/summary")
def get_machines_summary(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Provides KPI cards and machine fleet status summary for Admin dashboard."""
    machines = db.query(Machine).all()
    total = len(machines)
    working_count = sum(1 for m in machines if m.status == "working")
    not_working_count = total - working_count

    machine_cards = []
    for m in machines:
        worker_name = None
        proj_name = None
        prog = 0.0

        if m.current_worker_id:
            w = db.query(User).filter(User.id == m.current_worker_id).first()
            if w:
                worker_name = w.name

        if m.current_project_id:
            p = db.query(Project).filter(Project.id == m.current_project_id).first()
            if p:
                proj_name = p.name
                prog = p.progress_percent

        machine_cards.append({
            "id": m.id,
            "code": m.code,
            "name": m.name,
            "type": m.type,
            "status": m.status,
            "worker_name": worker_name,
            "project_name": proj_name,
            "progress_percent": prog,
            "travel_limits": m.travel_limits,
            "controller_type": m.controller_type
        })

    return {
        "total_machines": total,
        "working_count": working_count,
        "not_working_count": not_working_count,
        "machines": machine_cards
    }


@router.get("")
def list_machines(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists all shop CNC machines."""
    machines = db.query(Machine).all()
    return machines
