from datetime import datetime, timezone
from pathlib import Path
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.models import ToolStock, ToolChangeLog, Project, Notification
from app.config import settings

WEAR_THRESHOLD_PERCENT = 85.0  # If life_used / life_total >= 85%, mark worn


def inspect_tool_conditions_for_project(project: Project, db: Session) -> Dict[str, Any]:
    """Inspects tool conditions (remaining life, status) and executes automatic tool changes if worn.
    
    Returns structured results for Step 2 UI with heuristic labels.
    """
    run_dir = Path(settings.RUNS_DIR) / (project.run_id or "")
    recs_path = run_dir / "tool_recommendations.json"
    
    recommended_tools: List[Dict[str, Any]] = []
    if recs_path.exists():
        try:
            with open(recs_path, "r", encoding="utf-8") as f:
                recs_data = json.load(f)
                recommended_tools = recs_data.get("recommendations", recs_data.get("tool_recommendations", []))
        except Exception:
            pass

    inspected_tools: List[Dict[str, Any]] = []
    auto_changes: List[Dict[str, Any]] = []

    # Get all active tool stock
    for rec in recommended_tools:
        tid = rec.get("selected_tool_id") or rec.get("tool_id")
        ts = db.query(ToolStock).filter(ToolStock.tool_id == tid).first()
        if not ts:
            # Fallback by type
            t_type = rec.get("feature_type", "end_mill")
            if "hole" in t_type or "drill" in t_type:
                ts = db.query(ToolStock).filter(ToolStock.type == "drill").first()
            else:
                ts = db.query(ToolStock).filter(ToolStock.type == "end_mill").first()
        
        if not ts:
            continue

        usage_pct = round((ts.life_used / ts.life_total) * 100.0, 1) if ts.life_total > 0 else 0.0
        remaining_min = max(0.0, round(ts.life_total - ts.life_used, 1))

        # Check if worn or needs change
        is_worn = usage_pct >= WEAR_THRESHOLD_PERCENT or ts.status == "worn"
        auto_changed = False
        replacement_tool_id = None

        if is_worn:
            # Attempt to find fresh spare in tool stock
            spare = db.query(ToolStock).filter(
                ToolStock.type == ts.type,
                ToolStock.status == "fresh",
                ToolStock.id != ts.id
            ).first()

            if spare:
                # Execute auto replacement
                ts.status = "worn"
                spare.status = "in_use"
                spare.machine_id = ts.machine_id
                ts.machine_id = None
                spare.last_changed_at = datetime.now(timezone.utc)

                # Log tool change
                change_log = ToolChangeLog(
                    tool_stock_id=ts.id,
                    machine_id=spare.machine_id,
                    project_id=project.id,
                    reason="Automated replacement: Heuristic cutting wear exceeded 85% safe threshold",
                    old_tool_id=ts.tool_id,
                    new_tool_id=spare.tool_id
                )
                db.add(change_log)
                auto_changes.append({
                    "old_tool_id": ts.tool_id,
                    "old_tool_name": ts.name,
                    "new_tool_id": spare.tool_id,
                    "new_tool_name": spare.name,
                    "reason": "Wear threshold exceeded"
                })
                auto_changed = True
                replacement_tool_id = spare.tool_id

        db.commit()

        inspected_tools.append({
            "tool_id": ts.tool_id,
            "name": ts.name,
            "type": ts.type,
            "diameter_mm": ts.diameter_mm,
            "life_total_min": ts.life_total,
            "life_used_min": ts.life_used,
            "usage_percent": usage_pct,
            "remaining_min": remaining_min,
            "status": "worn" if (is_worn and not auto_changed) else ("replaced" if auto_changed else ts.status),
            "suitability_score": rec.get("suitability_score", 90.0),
            "reasons": rec.get("reasons", []),
            "auto_changed": auto_changed,
            "replacement_tool_id": replacement_tool_id
        })

    return {
        "heuristic_notice": "Tool wear estimates are computed via cutting physics heuristics and historical tool life logs.",
        "inspected_tools": inspected_tools,
        "auto_changes": auto_changes
    }


def deduct_tool_wear_after_job(project: Project, db: Session) -> None:
    """Calculates tool cutting time from engine operation_plan.json and deducts wear.
    
    If remaining life < threshold, flags worn and swaps with fresh spare if available.
    """
    run_dir = Path(settings.RUNS_DIR) / (project.run_id or "")
    plan_path = run_dir / "operation_plan.json"
    if not plan_path.exists():
        return

    try:
        with open(plan_path, "r", encoding="utf-8") as f:
            plan_data = json.load(f)
    except Exception:
        return

    operations = plan_data.get("operations", [])
    # Group estimated cutting minutes by tool_id
    tool_cutting_seconds: Dict[str, float] = {}
    for op in operations:
        tid = op.get("tool_id")
        t_cut = op.get("cutting_time_seconds", op.get("estimated_time_seconds", 30.0))
        if tid:
            tool_cutting_seconds[tid] = tool_cutting_seconds.get(tid, 0.0) + t_cut

    for tid, secs in tool_cutting_seconds.items():
        mins_used = round(secs / 60.0, 2)
        ts = db.query(ToolStock).filter(ToolStock.tool_id == tid).first()
        if not ts:
            continue

        ts.life_used += mins_used
        usage_pct = (ts.life_used / ts.life_total) * 100.0 if ts.life_total > 0 else 100.0

        if usage_pct >= WEAR_THRESHOLD_PERCENT and ts.status != "worn":
            ts.status = "worn"
            # Find fresh spare
            spare = db.query(ToolStock).filter(
                ToolStock.type == ts.type,
                ToolStock.status == "fresh",
                ToolStock.id != ts.id
            ).first()

            if spare:
                spare.status = "in_use"
                spare.machine_id = ts.machine_id
                ts.machine_id = None
                log = ToolChangeLog(
                    tool_stock_id=ts.id,
                    machine_id=spare.machine_id,
                    project_id=project.id,
                    reason=f"Post-job wear deduction: tool exceeded {WEAR_THRESHOLD_PERCENT}% life limit (heuristic)",
                    old_tool_id=ts.tool_id,
                    new_tool_id=spare.tool_id
                )
                db.add(log)
                # Notify worker
                notif = Notification(
                    user_id=project.owner_id,
                    type="tool_worn",
                    message=f"Tool {ts.name} ({ts.tool_id}) exceeded wear limit after job completion. Auto-replaced by fresh spare {spare.name}.",
                    read=False,
                    link=f"/projects/{project.id}"
                )
                db.add(notif)

    db.commit()
