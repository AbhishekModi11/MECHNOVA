from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.deps import get_current_user
from app.models.models import User, ToolStock, ToolChangeLog

router = APIRouter(prefix="/tools", tags=["Tools"])


@router.get("/stock")
def get_tool_stock(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns tool stock inventory with cutting life metrics and history."""
    tools = db.query(ToolStock).all()
    results = []
    for t in tools:
        life_total = float(t.life_total)
        life_used = float(t.life_used)
        usage_pct = round((life_used / life_total) * 100.0, 1) if life_total > 0 else 0.0
        remaining = max(0.0, round(life_total - life_used, 1))
        m_name = t.machine.name if t.machine else "Tool Crib (Available)"

        results.append({
            "id": t.id,
            "tool_id": t.tool_id,
            "name": t.name,
            "type": t.type,
            "diameter_mm": t.diameter_mm,
            "machine_id": t.machine_id,
            "machine_name": m_name,
            "life_total_min": t.life_total,
            "life_used_min": t.life_used,
            "usage_percent": usage_pct,
            "remaining_min": remaining,
            "status": t.status,
            "last_changed_at": t.last_changed_at.isoformat() if t.last_changed_at else None
        })

    logs = db.query(ToolChangeLog).order_by(ToolChangeLog.timestamp.desc()).limit(20).all()
    change_history = []
    for l in logs:
        change_history.append({
            "id": l.id,
            "reason": l.reason,
            "old_tool_id": l.old_tool_id,
            "new_tool_id": l.new_tool_id,
            "machine_id": l.machine_id,
            "project_id": l.project_id,
            "timestamp": l.timestamp.isoformat()
        })

    return {
        "heuristic_notice": "Tool wear life calculations are heuristic estimates based on accumulated cutting feeds and speeds.",
        "tools": results,
        "recent_changes": change_history
    }
