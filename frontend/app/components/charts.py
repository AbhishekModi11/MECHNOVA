from typing import List, Dict, Any, Optional
from nicegui import ui
from app.theme import get_current_theme, THEMES


def get_theme_color() -> str:
    """Gets hex accent for currently selected UI theme."""
    t_key = get_current_theme()
    return THEMES.get(t_key, {}).get("accent", "#1D7147")


def render_attendance_chart(history_records: List[Dict[str, Any]], accent_color: Optional[str] = None):
    """Renders attendance distribution chart using ECharts."""
    present = sum(1 for r in history_records if r.get("status") == "present")
    absent = sum(1 for r in history_records if r.get("status") == "absent")
    leave = sum(1 for r in history_records if r.get("status") == "leave")

    # If no records exist, provide standard monthly baseline (e.g. 20 present, 1 absent, 1 leave)
    if present + absent + leave == 0:
        present = 20
        absent = 1
        leave = 1

    accent = accent_color or get_theme_color()

    ui.echart({
        "tooltip": {"trigger": "item"},
        "legend": {"bottom": "0%", "left": "center", "textStyle": {"fontSize": 11}},
        "color": [accent, "#D32F2F", "#F57C00"],
        "series": [
            {
                "name": "Attendance",
                "type": "pie",
                "radius": ["42%", "72%"],
                "avoidLabelOverlap": False,
                "itemStyle": {
                    "borderRadius": 6,
                    "borderColor": "#ffffff",
                    "borderWidth": 2
                },
                "label": {"show": False},
                "data": [
                    {"value": present, "name": f"Present ({present}d)"},
                    {"value": absent, "name": f"Absent ({absent}d)"},
                    {"value": leave, "name": f"Leave ({leave}d)"}
                ]
            }
        ]
    }).classes("w-full h-48")


def render_monthly_target_gauge(completed: int, target: int = 8, accent_color: Optional[str] = None):
    """Renders monthly project completion progress vs target using active theme color."""
    pct = min(100.0, round((completed / target) * 100.0, 1)) if target > 0 else 0.0
    accent = accent_color or get_theme_color()

    ui.echart({
        "series": [
            {
                "type": "gauge",
                "startAngle": 180,
                "endAngle": 0,
                "min": 0,
                "max": target,
                "splitNumber": 4,
                "itemStyle": {
                    "color": accent
                },
                "progress": {
                    "show": True,
                    "roundCap": True,
                    "width": 14
                },
                "pointer": {"show": False},
                "axisLine": {
                    "roundCap": True,
                    "lineStyle": {"width": 14, "color": [[1, "rgba(150, 150, 150, 0.2)"]]}
                },
                "axisTick": {"show": False},
                "splitLine": {"show": False},
                "axisLabel": {"show": False},
                "title": {
                    "show": True,
                    "fontSize": 12,
                    "offsetCenter": [0, "20%"],
                    "color": "#64748b"
                },
                "detail": {
                    "valueAnimation": True,
                    "offsetCenter": [0, "-20%"],
                    "fontSize": 22,
                    "fontWeight": "bolder",
                    "formatter": f"{completed}/{target}",
                    "color": accent
                },
                "data": [{"value": completed, "name": f"Progress: {pct}%"}]
            }
        ]
    }).classes("w-full h-44")
