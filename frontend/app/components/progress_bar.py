"""
Theme-coloured percentage visual components.
Rule: Every PERCENTAGE visual uses the theme accent (--accent, --accent-soft, --accent-contrast).
Condition indicators (tool wear, READY / CAUTION / MISSING chips) keep fixed green / amber / red
because those colours carry industrial safety meaning.
"""
from nicegui import ui


def render_progress_bar(pct: float, label: str = None, height: str = "24px"):
    """
    Renders a percentage progress bar strictly styled with theme accent.
    Theme accent automatically updates when header color dots are selected.
    """
    v = max(0.0, min(100.0, float(pct or 0.0)))
    lbl = f"{label} " if label else ""
    text = f"{lbl}{v:.1f}%"

    with ui.element("div").classes("w-full rounded-lg overflow-hidden relative shadow-inner theme-progress-track").style(
        f"background: var(--accent-soft); height: {height};"
    ):
        with ui.element("div").classes("h-full flex items-center justify-end px-2.5 transition-all duration-300 theme-progress-fill font-mono font-bold text-xs whitespace-nowrap").style(
            f"width: {v}%; background: var(--accent); color: var(--accent-contrast);"
        ):
            if v > 12:
                ui.label(text).classes("text-[11px] font-bold")
        if v <= 12:
            ui.label(text).classes("absolute left-2.5 top-1/2 -translate-y-1/2 text-[11px] font-bold text-[var(--text)] font-mono")


def render_percent_badge(pct: float):
    """Renders a rounded pill badge with theme accent coloring."""
    v = float(pct or 0.0)
    with ui.element("span").classes("theme-pct-badge font-mono font-bold text-xs shadow-sm").style(
        "background: var(--accent); color: var(--accent-contrast); border-radius: 9999px; padding: 2px 10px;"
    ):
        ui.label(f"{v:.1f}%")
