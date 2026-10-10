from typing import List, Dict, Any, Callable
from nicegui import ui, run
from app.components.tool_gauge import render_tool_life_gauge
from app.components.status_chip import render_status_chip


def render_tool_inspection_card(
    tool: Dict[str, Any],
    is_scanning: bool = False,
    is_animating_change: bool = False
):
    """Renders a tool card with laser beam scanner and slide animation."""
    card_classes = "p-4 glass-panel relative overflow-hidden transition-all duration-300 w-full"
    
    with ui.card().classes(card_classes):
        # Laser scanner sweep beam if scan in progress
        if is_scanning:
            ui.element("div").classes("scanner-beam")

        with ui.row().classes("justify-between items-start w-full"):
            with ui.column().classes("gap-0"):
                ui.label(tool.get("name", "Tool")).classes("font-bold text-base text-[var(--text)]")
                ui.label(f"Code: {tool.get('tool_id')} | Dia: {tool.get('diameter_mm', 0)} mm").classes("text-xs text-[var(--text-muted)]")
            
            render_status_chip(tool.get("status", "fresh"))

        ui.separator().classes("my-2")

        # Animated tool change presentation
        if is_animating_change and tool.get("auto_changed"):
            with ui.card().classes("p-3 bg-[var(--status-review-bg)] border border-[var(--status-review-border)] rounded-md w-full animate-slide-in"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("swap_horiz", size="20px", color="primary")
                    ui.label("Automated Tool Swap Triggered").classes("font-bold text-xs text-[var(--accent-900)]")
                ui.label(f"Old worn bit ({tool.get('tool_id')}) replaced with fresh spare ({tool.get('replacement_tool_id')})").classes("text-xs text-[var(--text-muted)] mt-1")

        # Life gauge
        render_tool_life_gauge(
            life_total=tool.get("life_total_min", 100.0),
            life_used=tool.get("life_used_min", 0.0)
        )

        # Engine recommendation ranking & score
        if "suitability_score" in tool:
            with ui.row().classes("items-center justify-between w-full mt-2 text-xs pt-2 border-t border-[var(--border)]"):
                ui.label("Engine Suitability Score:").classes("text-[var(--text-muted)]")
                ui.label(f"{int(tool['suitability_score'] * 100 if tool['suitability_score'] <= 1.0 else tool['suitability_score'])}%").classes("font-bold text-[var(--accent-600)]")

        # Rejection/penalty or qualification reasons
        reasons = tool.get("reasons", [])
        if reasons:
            with ui.row().classes("flex-wrap gap-1 mt-1"):
                for r in reasons[:3]:
                    with ui.badge(outline=True, color="green").classes("text-[10px]"):
                        ui.label(r.replace("_", " "))
