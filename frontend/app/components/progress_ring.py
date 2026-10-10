from nicegui import ui


def render_progress_ring(progress_percent: float, current_operation: str = "Cutting"):
    """Renders real-time simulated build progress overlay."""
    pct = max(0.0, min(100.0, float(progress_percent)))

    with ui.card().classes("p-5 glass-panel w-full text-center flex flex-col items-center"):
        with ui.row().classes("items-center gap-2 mb-2"):
            ui.icon("precision_manufacturing", size="22px").classes("text-[var(--accent-600)]")
            ui.label("Live Machine Execution").classes("font-bold text-base text-[var(--text)]")
            with ui.badge(color="orange").classes("text-[10px] uppercase font-bold tracking-wider"):
                ui.label("Simulated")

        # Circular progress
        with ui.circular_progress(
            value=pct / 100.0,
            size="110px",
            show_value=True,
            color="primary"
        ).classes("my-3 text-lg font-bold"):
            ui.label(f"{int(pct)}%").classes("font-black text-xl")

        ui.label(current_operation).classes("text-sm font-semibold text-[var(--accent-700)]")
        ui.label("Time calculations derived from Open CASCADE cutting physics heuristics.").classes("text-[11px] text-[var(--text-muted)] mt-1")
