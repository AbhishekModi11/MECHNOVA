from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import require_admin, get_current_user
from app.models.models import User, Attendance, Machine, Project
from app.services.attendance_service import get_monthly_attendance_summary, get_worker_project_metrics

router = APIRouter(prefix="/admin/workers", tags=["Admin Workers"])


@router.get("")
def list_workers(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Lists all shop floor workers, their attendance status today, and assigned machine."""
    workers = db.query(User).filter(User.role == "worker").all()
    today = date.today()

    results = []
    present_today = 0
    absent_today = 0
    on_machine_count = 0

    for w in workers:
        att = db.query(Attendance).filter(
            Attendance.user_id == w.id,
            Attendance.date == today
        ).first()
        status_today = att.status if att else "present"  # fallback default

        if status_today == "present":
            present_today += 1
        else:
            absent_today += 1

        # Check assigned machine
        m = db.query(Machine).filter(Machine.current_worker_id == w.id).first()
        machine_info = f"{m.code} - {m.name}" if m else "None (Available)"
        if m:
            on_machine_count += 1

        results.append({
            "id": w.id,
            "name": w.name,
            "company_id": w.company_id,
            "company_email": w.company_email,
            "status_today": status_today,
            "assigned_machine": machine_info,
            "active": w.active
        })

    return {
        "summary": {
            "total_workers": len(workers),
            "present_today": present_today,
            "absent_today": absent_today,
            "on_machine_count": on_machine_count
        },
        "workers": results
    }


@router.get("/{worker_id}")
def get_worker_detail(
    worker_id: int,
    year: int = date.today().year,
    month: int = date.today().month,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieves worker profile, 90-day attendance metrics, and completed projects."""
    if current_user.role != "admin" and current_user.id != worker_id:
        raise HTTPException(status_code=403, detail="Forbidden: You can only view your own worker record")

    worker = db.query(User).filter(User.id == worker_id, User.role == "worker").first()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    att_summary = get_monthly_attendance_summary(worker.id, year, month, db)
    metrics = get_worker_project_metrics(worker.id, year, month, db)

    projects = db.query(Project).filter(Project.owner_id == worker.id).all()

    return {
        "worker": {
            "id": worker.id,
            "name": worker.name,
            "company_id": worker.company_id,
            "company_email": worker.company_email
        },
        "attendance": att_summary,
        "metrics": metrics,
        "projects_count": len(projects)
    }
