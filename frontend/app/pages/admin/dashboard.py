from typing import Dict, Any, List
from nicegui import ui
from app.api_client import api
from app.session import require_auth
from app.components.layout import app_shell
from app.components.kpi_card import render_kpi_card
from app.components.status_chip import render_status_chip


def register_admin_dashboard():
    @ui.page("/admin")
    async def admin_dashboard():
        if not require_auth(allowed_roles=["admin"]):
            return

        app_shell("Admin Overview")

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            with ui.row().classes("justify-between items-center w-full"):
                with ui.column().classes("gap-1"):
                    ui.label("Shop Floor Administration").classes("text-2xl font-black text-[var(--accent-900)] tracking-tight")
                    ui.label("Real-time monitoring of CNC fleet, staff attendance, and job dispatches.").classes("text-xs text-[var(--text-muted)]")

            # Load data from backend
            mach_summary: Dict[str, Any] = {}
            workers_data: Dict[str, Any] = {}
            requests_list: List[Dict[str, Any]] = []
            try:
                mach_summary = await api.get_machines_summary()
                workers_data = await api.get_workers()
                requests_list = await api.get_machine_requests()
            except Exception as e:
                ui.notify(f"Failed to fetch fleet data: {e}", type="negative")
                mach_summary = {"total_machines": 8, "working_count": 2, "not_working_count": 6, "machines": []}
                workers_data = {"summary": {"total_workers": 6, "present_today": 6, "on_machine_count": 2}}
                requests_list = []

            # KPI Grid
            with ui.row().classes("w-full gap-4 flex-wrap"):
                render_kpi_card("Fleet Total", str(mach_summary.get("total_machines", 8)), "Configured CNC Stations", "precision_manufacturing", accent=True)
                render_kpi_card("Active Spindles", str(mach_summary.get("working_count", 0)), "Running Operations", "play_circle")
                render_kpi_card("Available / Idle", str(mach_summary.get("not_working_count", 0)), "Ready for Allocation", "check_circle")
                render_kpi_card("Staff Present", f"{workers_data.get('summary', {}).get('present_today', 6)} / {workers_data.get('summary', {}).get('total_workers', 6)}", "Today's Attendance", "people")
                render_kpi_card("Pending Requests", str(len([r for r in requests_list if r.get('status') == 'pending'])), "Awaiting Approval", "pending_actions")

            # Active Machines Overview
            with ui.card().classes("w-full p-5 glass-panel"):
                with ui.row().classes("justify-between items-center w-full mb-3"):
                    ui.label("CNC Machine Fleet Status").classes("font-bold text-base text-[var(--text)]")
                    ui.button("Manage Machines", icon="settings", on_click=lambda: ui.navigate.to("/admin/machines")).props("flat dense size=sm")

                with ui.grid().classes("grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full"):
                    for m in mach_summary.get("machines", []):
                        with ui.card().classes("p-3 border border-[var(--border)] rounded-xl flex flex-col justify-between"):
                            with ui.row().classes("justify-between items-start w-full"):
                                with ui.column().classes("gap-0"):
                                    ui.label(m["code"]).classes("font-black text-sm text-[var(--accent-700)]")
                                    ui.label(m["name"]).classes("text-xs font-semibold text-[var(--text)]")
                                render_status_chip(m["status"])

                            ui.label(f"Type: {m['type']}").classes("text-[11px] text-[var(--text-muted)] mt-2")
                            
                            if m.get("worker_name"):
                                with ui.row().classes("items-center gap-1 mt-2 text-xs"):
                                    ui.icon("person", size="14px", color="primary")
                                    ui.label(f"Operator: {m['worker_name']}").classes("font-medium")
                                if m.get("project_name"):
                                    ui.label(f"Job: {m['project_name']}").classes("text-[11px] text-[var(--accent-600)] font-semibold truncate")
                                    ui.linear_progress(value=m.get("progress_percent", 0.0) / 100.0, size="6px", color="primary").classes("rounded-full mt-1")
                            else:
                                ui.label("No active operator assigned").classes("text-[11px] text-[var(--text-muted)] italic mt-2")
