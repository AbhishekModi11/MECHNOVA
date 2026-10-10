from typing import Optional
from nicegui import ui


def render_kpi_card(
    title: str,
    value: str,
    subtitle: Optional[str] = None,
    icon: str = "precision_manufacturing",
    accent: bool = False
):
    """Renders a modern elevated KPI card."""
    border_style = "border-l-4 border-l-[var(--accent-600)]" if accent else ""
    
    with ui.card().classes(
        f"p-4 glass-panel flex-1 min-w-[200px] {border_style} transition-transform hover:-translate-y-0.5"
    ):
        with ui.row().classes("items-center justify-between w-full mb-1"):
            ui.label(title).classes("text-xs uppercase tracking-wider font-semibold text-[var(--text-muted)]")
            ui.icon(icon, size="20px").classes("text-[var(--accent-600)] opacity-80")
        
        ui.label(value).classes("text-2xl font-bold text-[var(--text)] tracking-tight")
        
        if subtitle:
            ui.label(subtitle).classes("text-xs text-[var(--text-muted)] mt-1")
