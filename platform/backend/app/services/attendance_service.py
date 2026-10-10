from datetime import date
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.models.models import Attendance, Project


def get_monthly_attendance_summary(user_id: int, year: int, month: int, db: Session) -> Dict[str, Any]:
    """Computes monthly attendance metrics (present, absent, leave) dynamically via query."""
    records = db.query(Attendance).filter(
        Attendance.user_id == user_id,
        extract("year", Attendance.date) == year,
        extract("month", Attendance.date) == month
    ).order_by(Attendance.date.asc()).all()

    present_count = sum(1 for r in records if r.status == "present")
    absent_count = sum(1 for r in records if r.status == "absent")
    leave_count = sum(1 for r in records if r.status == "leave")
    total_days = len(records)
    
    rate = round((present_count / total_days * 100.0), 1) if total_days > 0 else 100.0

    return {
        "year": year,
        "month": month,
        "total_days": total_days,
        "present_days": present_count,
        "absent_days": absent_count,
        "leave_days": leave_count,
        "attendance_rate_percent": rate,
        "history": [{"date": r.date.isoformat(), "status": r.status} for r in records]
    }


def get_worker_project_metrics(worker_id: int, year: int, month: int, db: Session) -> Dict[str, Any]:
    """Computes worker completed projects vs monthly target dynamically."""
    completed_projects = db.query(Project).filter(
        Project.owner_id == worker_id,
        Project.status == "completed"
    ).all()

    # Monthly completed count
    month_completed = 0
    for p in completed_projects:
        if p.completed_at and p.completed_at.year == year and p.completed_at.month == month:
            month_completed += 1

    # Standard shop target: 8 projects per month
    monthly_target = 8
    target_progress_percent = min(100.0, round((month_completed / monthly_target) * 100.0, 1))

    return {
        "total_completed_all_time": len(completed_projects),
        "month_completed": month_completed,
        "monthly_target": monthly_target,
        "target_progress_percent": target_progress_percent
    }
