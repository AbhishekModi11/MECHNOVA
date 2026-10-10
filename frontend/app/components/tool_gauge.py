from nicegui import ui


def render_tool_life_gauge(life_total: float, life_used: float):
    """Renders a tool wear condition gauge."""
    usage_pct = min(100.0, round((life_used / life_total) * 100.0, 1)) if life_total > 0 else 0.0
    remaining_pct = max(0.0, round(100.0 - usage_pct, 1))
    
    # Heuristic color mapping
    if usage_pct < 65.0:
        bar_color = "positive"
        status_text = "Optimal Condition"
        text_color = "text-green-700"
    elif usage_pct < 85.0:
        bar_color = "warning"
        status_text = "Fair / Moderate Wear"
        text_color = "text-amber-700"
    else:
        bar_color = "negative"
        status_text = "Worn - Replacement Required"
        text_color = "text-red-700"

    with ui.column().classes("w-full gap-1"):
        with ui.row().classes("justify-between w-full text-xs"):
            ui.label("Remaining Cutting Life:").classes("text-[var(--text-muted)] font-medium")
            ui.label(f"{remaining_pct}% ({round(life_total - life_used, 1)} min)").classes(f"font-bold {text_color}")
            
        ui.linear_progress(value=(1.0 - usage_pct / 100.0), color=bar_color, size="10px", show_value=False).classes("rounded-full")
        
        with ui.row().classes("justify-between w-full text-[10px] text-[var(--text-muted)]"):
            ui.label(f"Used: {round(life_used, 1)} / {round(life_total, 1)} min")
            ui.label(status_text).classes(f"font-semibold {text_color}")
