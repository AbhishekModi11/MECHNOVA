import asyncio
import os
import uuid
from pathlib import Path
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.config import settings
from app.db import SessionLocal
from app.models.models import Project
from app.routers.ws import ws_manager
from cadcnc.engine import Engine, EngineRunRequest


def run_engine_for_project_sync(project_id: int, loop: Optional[asyncio.AbstractEventLoop] = None) -> Dict[str, Any]:
    """Synchronous worker function that executes Engine.run() and persists deliverables to runs/<run_id>/."""
    db: Session = SessionLocal()
    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return {"success": False, "error": f"Project {project_id} not found."}

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        project.run_id = run_id
        project.engine_status = "running"
        project.error_message = None
        db.commit()

        out_dir = Path(settings.RUNS_DIR) / run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        def progress_callback(stage_msg: str, progress_ratio: float):
            # Update DB progress
            pct = round(progress_ratio * 100.0, 1)
            project.progress_percent = pct
            db.commit()

            # Push live progress over WebSocket if loop is active
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_progress(
                        project_id=project_id,
                        stage="analysis",
                        percent=progress_ratio,
                        message=stage_msg
                    ),
                    loop
                )

        engine = Engine()
        req = EngineRunRequest(
            model_path=Path(project.source_file_path),
            out_dir=out_dir,
            material_id=project.material_id or "aluminum_6061"
        )

        try:
            result = engine.run(req, progress_cb=progress_callback)
            
            # Read generated summary for dimensions
            sum_path = out_dir / "model_summary.json"
            if sum_path.exists():
                import json
                with open(sum_path, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                    bb = s_data.get("bounding_box", {})
                    project.dimensions = {
                        "length": bb.get("x_length_mm", 0.0),
                        "width": bb.get("y_length_mm", 0.0),
                        "height": bb.get("z_length_mm", 0.0),
                        "volume_mm3": s_data.get("volume_mm3", 0.0)
                    }

            project.engine_status = "done"
            project.status = "analysed"
            project.progress_percent = 100.0
            db.commit()

            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_progress(
                        project_id=project_id,
                        stage="analysis_complete",
                        percent=1.0,
                        message="CAD-to-CNC Optimization Engine pipeline complete.",
                        extra={"run_id": run_id, "success": True}
                    ),
                    loop
                )

            return {"success": True, "run_id": run_id}

        except Exception as e:
            err_str = str(e)
            project.engine_status = "failed"
            project.status = "draft"
            project.error_message = err_str
            db.commit()

            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    ws_manager.broadcast_progress(
                        project_id=project_id,
                        stage="analysis_failed",
                        percent=1.0,
                        message=f"Engine analysis halted: {err_str}",
                        extra={"error": err_str}
                    ),
                    loop
                )

            return {"success": False, "error": err_str}

    finally:
        db.close()


async def trigger_project_analysis_async(project_id: int) -> None:
    """Dispatches engine execution to an async thread pool worker."""
    loop = asyncio.get_running_loop()
    await asyncio.to_thread(run_engine_for_project_sync, project_id, loop)
