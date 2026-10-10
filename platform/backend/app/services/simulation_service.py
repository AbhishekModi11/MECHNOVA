import asyncio
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.db import SessionLocal
from app.models.models import Project, Machine, Notification
from app.routers.ws import ws_manager
from app.services.tool_wear_service import deduct_tool_wear_after_job


async def run_machine_simulation_async(project_id: int, speed_factor: Optional[float] = None) -> None:
    """Simulates real-time CNC machining progression through planned operations."""
    if speed_factor is None:
        speed_factor = max(1.0, float(settings.DEMO_SPEED_FACTOR))

    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project or not project.run_id:
            return

        run_dir = Path(settings.RUNS_DIR) / project.run_id
        plan_path = run_dir / "operation_plan.json"
        
        operations: List[Dict[str, Any]] = []
        if plan_path.exists():
            try:
                with open(plan_path, "r", encoding="utf-8") as f:
                    plan_data = json.load(f)
                    operations = plan_data.get("operations", [])
            except Exception:
                pass

        if not operations:
            # Fallback operations if plan file was empty
            operations = [
                {"operation_name": "Rough Facing", "estimated_time_seconds": 30.0},
                {"operation_name": "Feature Pocketing", "estimated_time_seconds": 60.0},
                {"operation_name": "Drilling & Chamfering", "estimated_time_seconds": 40.0},
                {"operation_name": "Contour Finishing", "estimated_time_seconds": 30.0}
            ]

        total_sim_seconds = sum(op.get("estimated_time_seconds", 30.0) for op in operations)
        # Scaled duration for demo
        scaled_total_seconds = max(5.0, total_sim_seconds / speed_factor)

        # Mark machine working
        machine = None
        if project.machine_request and project.machine_request.requested_machine_id:
            machine = db.query(Machine).filter(Machine.id == project.machine_request.requested_machine_id).first()
            if machine:
                machine.status = "working"
                machine.current_project_id = project.id
                machine.current_worker_id = project.owner_id
        
        project.status = "deployed"
        project.started_at = datetime.now(timezone.utc)
        project.progress_percent = 0.0
        db.commit()

        # Step through operations
        elapsed = 0.0
        step_dt = 0.5  # updates every 500ms
        
        while elapsed < scaled_total_seconds:
            await asyncio.sleep(step_dt)
            elapsed += step_dt
            
            progress_ratio = min(0.99, elapsed / scaled_total_seconds)
            pct = round(progress_ratio * 100.0, 1)

            # Determine which operation is active
            cum_time = 0.0
            active_op_name = operations[-1].get("operation_name", "Machining")
            for op in operations:
                op_dur_scaled = (op.get("estimated_time_seconds", 30.0) / total_sim_seconds) * scaled_total_seconds
                cum_time += op_dur_scaled
                if elapsed <= cum_time:
                    active_op_name = op.get("operation_name", "Cutting")
                    break

            project.progress_percent = pct
            project.current_operation = active_op_name
            db.commit()

            # Push live update over WebSocket
            await ws_manager.broadcast_progress(
                project_id=project_id,
                stage="machining_simulation",
                percent=progress_ratio,
                message=f"[Simulated] {active_op_name} in progress ({pct}%)",
                extra={
                    "current_operation": active_op_name,
                    "simulated": True,
                    "speed_factor": speed_factor
                }
            )

        # Finalize 100% completion
        project.progress_percent = 100.0
        project.current_operation = "Machining Complete"
        project.status = "completed"
        project.completed_at = datetime.now(timezone.utc)

        # Free the machine
        if machine:
            machine.status = "idle"
            machine.current_project_id = None
            machine.current_worker_id = None

        # Deduct tool wear
        deduct_tool_wear_after_job(project, db)

        # Create Completion Notification
        notif = Notification(
            user_id=project.owner_id,
            type="job_completed",
            message=f"Job '{project.name}' successfully completed machining simulation! Final deliverables ready.",
            read=False,
            link=f"/projects/{project.id}"
        )
        db.add(notif)
        db.commit()

        await ws_manager.broadcast_progress(
            project_id=project_id,
            stage="machining_completed",
            percent=1.0,
            message=f"[Simulated] Machining 100% Complete for '{project.name}'.",
            extra={"completed": True, "simulated": True}
        )

    finally:
        db.close()
