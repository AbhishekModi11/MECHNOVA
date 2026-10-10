from nicegui import ui
import json
import base64
from app.api_client import api
from app.session import require_auth
from app.components.layout import app_shell
from app.components.page_header import render_page_header
from app.services.project_service import list_projects, get_project


def register_project_history_page():
    @ui.page("/worker/history")
    async def project_history_page():
        if not require_auth(allowed_roles=["worker"]):
            return

        app_shell("Project History")

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            render_page_header(
                title="Project Lifecycle Archive",
                back_to="/worker",
                subtitle="Track DFM analysis, immutable job slip records, and shop routing history."
            )

            try:
                db_projects = list_projects()
            except Exception:
                db_projects = []

            with ui.card().classes("w-full p-5 glass-panel rounded-2xl border border-[var(--border)] flex flex-col gap-4"):
                with ui.row().classes("justify-between items-center w-full flex-wrap gap-3"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("history_edu", size="24px").classes("text-[var(--accent)]")
                        ui.label("Job Lifecycle Records & Immutable Slips").classes("font-black text-base text-[var(--text)]")
                    
                    ui.button("New Project", icon="add", on_click=lambda: ui.navigate.to("/worker/new-project")).classes("btn-primary py-1.5 px-4 shadow-sm text-xs font-bold rounded-xl")

                # Search and filter bar
                with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                    search_input = ui.input(placeholder="Search by project no or part name...").props("dense outlined").classes("flex-1 min-w-[240px] text-xs")
                    status_filter = ui.select(
                        options=["All Statuses", "CONFIRMED_BY_OPERATOR", "MACHINE_REQUESTED", "READY"],
                        value="All Statuses",
                        label="Status"
                    ).props("dense outlined").classes("w-48 text-xs")

                # Project Cards Container
                cards_container = ui.column().classes("w-full gap-3")

                def render_cards():
                    cards_container.clear()
                    q = (search_input.value or "").strip().lower()
                    sf = status_filter.value

                    filtered = []
                    for p in db_projects:
                        p_no = str(p.get("project_no", "")).lower()
                        p_name = str(p.get("partName", "")).lower()
                        p_stat = str(p.get("status", ""))
                        p_req_stat = str(p.get("request_status", ""))

                        if q and q not in p_no and q not in p_name:
                            continue
                        if sf != "All Statuses":
                            if sf == "MACHINE_REQUESTED" and p_stat != "MACHINE_REQUESTED" and p_req_stat not in ("PENDING", "DONE"):
                                continue
                            elif sf == "CONFIRMED_BY_OPERATOR" and p_stat != "CONFIRMED_BY_OPERATOR":
                                continue
                            elif sf == "READY" and p_stat != "READY":
                                continue
                        filtered.append(p)

                    if not filtered:
                        with cards_container:
                            ui.label("No project records match the current filter.").classes("text-xs text-[var(--text-muted)] italic py-4")
                        return

                    with cards_container:
                        for p in filtered:
                            pid = p["id"]
                            p_no = p.get("project_no", f"MN-2026-{pid[:4]}")
                            p_name = p.get("partName", "Bracket")
                            status = p.get("status", "READY")
                            req_status = p.get("request_status")
                            created_str = str(p.get("createdAt") or "")[:19].replace("T", " ")
                            
                            # Status Badge Styling
                            if status == "MACHINE_REQUESTED" or req_status in ("PENDING", "DONE"):
                                stat_badge_col = "positive"
                                stat_badge_text = "MACHINE REQUESTED"
                            elif status == "CONFIRMED_BY_OPERATOR":
                                stat_badge_col = "primary"
                                stat_badge_text = "CONFIRMED BY OPERATOR"
                            elif status == "READY":
                                stat_badge_col = "info"
                                stat_badge_text = "DESIGN READY"
                            else:
                                stat_badge_col = "secondary"
                                stat_badge_text = status

                            with ui.card().classes("p-4 border border-[var(--border)] rounded-xl w-full flex-col justify-between glass-panel hover:border-[var(--accent)] transition-all"):
                                with ui.row().classes("justify-between items-start w-full flex-wrap gap-2"):
                                    with ui.column().classes("gap-1"):
                                        with ui.row().classes("items-center gap-2 flex-wrap"):
                                            ui.badge(p_no, color="secondary").props("dense").classes("font-mono font-bold text-xs")
                                            ui.label(p_name).classes("font-bold text-base text-[var(--text)]")
                                            ui.badge(stat_badge_text, color=stat_badge_col).props("dense").classes("font-mono font-bold text-[10px]")

                                        ui.label(f"Material: {p.get('material', 'Aluminum')} • Created: {created_str}").classes("text-xs text-[var(--text-muted)]")

                                    with ui.row().classes("items-center gap-2"):
                                        ui.button(
                                            "View Job Slip",
                                            icon="description",
                                            on_click=lambda pid=pid: ui.navigate.to(f"/worker/projects/{pid}/summary")
                                        ).props("dense size=sm").classes("btn-primary text-xs font-bold py-1 px-3")

                                        ui.button(
                                            "Design Details",
                                            icon="tune",
                                            on_click=lambda pid=pid: ui.navigate.to(f"/worker/projects/{pid}/design-details")
                                        ).props("flat dense size=sm").classes("text-xs text-slate-300 hover:text-white")

                                        ui.button(
                                            "Tools",
                                            icon="construction",
                                            on_click=lambda pid=pid: ui.navigate.to(f"/worker/projects/{pid}/tools")
                                        ).props("flat dense size=sm").classes("text-xs text-slate-300 hover:text-white")

                search_input.on("update:model-value", render_cards)
                status_filter.on("update:model-value", render_cards)
                render_cards()
