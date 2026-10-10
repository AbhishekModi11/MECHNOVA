from datetime import datetime, timedelta
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.models import Schedule, Machine


class SchedulingConflictError(Exception):
    def __init__(self, message: str, suggested_slot: Optional[Tuple[datetime, datetime]] = None):
        super().__init__(message)
        self.suggested_slot = suggested_slot


def check_schedule_conflict(
    machine_id: int,
    start: datetime,
    end: datetime,
    db: Session,
    exclude_project_id: Optional[int] = None
) -> None:
    """Checks if requested machine window overlaps with existing schedules.
    
    Raises SchedulingConflictError with next suggested free slot if conflict detected.
    """
    if end <= start:
        raise SchedulingConflictError("Scheduled end time must be after start time.")

    query = db.query(Schedule).filter(
        Schedule.machine_id == machine_id,
        and_(
            Schedule.start < end,
            Schedule.end > start
        )
    )
    if exclude_project_id:
        query = query.filter(Schedule.project_id != exclude_project_id)

    conflicting = query.order_by(Schedule.end.asc()).first()
    if conflicting:
        # Find next free slot after the latest overlapping schedule
        all_schedules = db.query(Schedule).filter(
            Schedule.machine_id == machine_id,
            Schedule.end >= start
        ).order_by(Schedule.start.asc()).all()

        duration = end - start
        suggested_start = conflicting.end + timedelta(minutes=15)  # 15-minute turnaround buffer
        suggested_end = suggested_start + duration

        # Verify suggested slot is clear
        slot_conflict = True
        while slot_conflict:
            slot_conflict = False
            for s in all_schedules:
                if s.start < suggested_end and s.end > suggested_start:
                    suggested_start = s.end + timedelta(minutes=15)
                    suggested_end = suggested_start + duration
                    slot_conflict = True
                    break

        machine = db.query(Machine).filter(Machine.id == machine_id).first()
        m_name = machine.name if machine else f"Machine #{machine_id}"

        msg = (
            f"Scheduling Conflict: {m_name} is already reserved between "
            f"{conflicting.start.strftime('%Y-%m-%d %H:%M')} and {conflicting.end.strftime('%Y-%m-%d %H:%M')}. "
            f"Next suggested free slot: {suggested_start.strftime('%Y-%m-%d %H:%M')} to {suggested_end.strftime('%Y-%m-%d %H:%M')}."
        )
        raise SchedulingConflictError(msg, suggested_slot=(suggested_start, suggested_end))


def create_schedule(
    machine_id: int,
    project_id: int,
    start: datetime,
    end: datetime,
    db: Session
) -> Schedule:
    """Verifies no overlap and creates a committed machine schedule."""
    check_schedule_conflict(machine_id, start, end, db, exclude_project_id=project_id)
    
    # Remove any existing schedule for this project
    db.query(Schedule).filter(Schedule.project_id == project_id).delete()

    schedule = Schedule(
        machine_id=machine_id,
        project_id=project_id,
        start=start,
        end=end
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule
