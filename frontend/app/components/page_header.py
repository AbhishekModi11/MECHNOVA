"""
Unified PageHeader component with standard Back button on every page.
Supports deterministic Back routing for 4-step wizard workflow and fallback for standalone pages.
"""
from typing import Optional, Callable
from nicegui import ui

WIZARD_STEPS = [
    {"num": 1, "name": "Part Design"},
    {"num": 2, "name": "Design Details"},
    {"num": 3, "name": "Tools & Equipment"},
    {"num": 4, "name": "Final Job Slip"}
]


def render_page_header(
    title: str,
    back_to: Optional[str] = None,
    subtitle: Optional[str] = None,
    current_step: Optional[int] = None,
    project_no: Optional[str] = None,
    part_name: Optional[str] = None,
    is_root: bool = False
):
    """
    Renders top-left Back button and title/stepper bar.
    - If is_root=True (e.g. Worker Dashboard), the back button is disabled/hidden.
    - If current_step (1-4) is given, renders standard step bar filled with theme color.
    """
    with ui.column().classes("w-full gap-3 pb-3 border-b border-[var(--border)] page-header"):
        # Top Row: Back button, project number badge, and title
        with ui.row().classes("justify-between items-center w-full flex-wrap gap-3"):
            with ui.row().classes("items-center gap-3"):
                if is_root:
                    ui.button("Dashboard Root", icon="home").props("flat dense size=sm").classes("back-btn opacity-50 cursor-not-allowed text-xs")
                else:
                    def handle_back():
                        if back_to:
                            ui.navigate.to(back_to)
                        else:
                            ui.navigate.to("/worker")

                    ui.button(
                        "← Back",
                        on_click=handle_back
                    ).props("outlined dense size=sm").classes(
                        "back-btn text-xs font-bold px-3 py-1 rounded-lg focus:ring-2 focus:ring-[var(--accent)] hover:bg-[var(--accent-soft)]"
                    ).tooltip(f"Return to {back_to or 'Dashboard'}")

                ui.separator().props("vertical").classes("h-5")

                with ui.column().classes("gap-0"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(title).classes("text-xl sm:text-2xl font-black text-[var(--accent-900)] tracking-tight")
                        if project_no:
                            ui.badge(project_no, color="dark").props("dense outline").classes("font-mono font-bold text-xs")
                    if subtitle:
                        ui.label(subtitle).classes("text-xs text-[var(--text-muted)]")
                    elif part_name:
                        ui.label(f"Part: {part_name}").classes("text-xs font-semibold text-[var(--text-muted)]")

        # Wizard Step Bar (1 to 4)
        if current_step:
            with ui.row().classes("w-full items-center justify-between sm:justify-start gap-2 sm:gap-4 py-2 px-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)]"):
                for step in WIZARD_STEPS:
                    s_num = step["num"]
                    s_name = step["name"]
                    is_current = s_num == current_step
                    is_done = s_num < current_step

                    with ui.row().classes("items-center gap-1.5"):
                        if is_current:
                            with ui.element("div").classes("w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs shadow-sm font-mono").style(
                                "background: var(--accent); color: var(--accent-contrast);"
                            ):
                                ui.label(str(s_num))
                            ui.label(s_name).classes("font-bold text-xs text-[var(--accent-900)]")
                        elif is_done:
                            with ui.element("div").classes("w-6 h-6 rounded-full flex items-center justify-center font-bold text-xs font-mono").style(
                                "background: var(--accent-soft); color: var(--accent); border: 1px solid var(--accent);"
                            ):
                                ui.label("✓")
                            ui.label(s_name).classes("font-semibold text-xs text-[var(--text-muted)] hidden md:block")
                        else:
                            with ui.element("div").classes("w-6 h-6 rounded-full flex items-center justify-center font-semibold text-xs bg-slate-200 text-slate-500 font-mono"):
                                ui.label(str(s_num))
                            ui.label(s_name).classes("text-xs text-[var(--text-muted)] opacity-60 hidden md:block")

                    if s_num < 4:
                        ui.label("➔").classes("text-slate-400 text-xs hidden sm:block")
