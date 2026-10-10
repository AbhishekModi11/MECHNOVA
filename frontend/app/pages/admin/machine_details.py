from nicegui import ui
from app.api_client import api
from app.session import require_auth
from app.components.layout import app_shell
from app.components.status_chip import render_status_chip


def register_machine_details_page():
    @ui.page("/admin/machines")
    async def machine_details_page():
        if not require_auth(allowed_roles=["admin"]):
            return

        app_shell("Machine Details")

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            with ui.row().classes("justify-between items-center w-full"):
                with ui.column().classes("gap-1"):
                    ui.label("CNC Machine Fleet & Specifications").classes("text-2xl font-black text-[var(--accent-900)] tracking-tight")
                    ui.label("Shop floor equipment parameters, axis envelopes, and active assignments.").classes("text-xs text-[var(--text-muted)]")

            try:
                summary = await api.get_machines_summary()
                machines = summary.get("machines", [])
            except Exception as e:
                ui.notify(f"Could not load machines: {e}", type="negative")
                machines = []

            # Status Filter Tabs
            with ui.row().classes("gap-2 items-center"):
                ui.label("Filter Status:").classes("text-xs font-bold text-[var(--text-muted)]")
                status_filter = ui.select(
                    options=["All", "working", "idle", "maintenance", "offline"],
                    value="All"
                ).props("dense outlined").classes("w-40 text-xs")

            container = ui.grid().classes("grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 w-full")

            def refresh_grid():
                container.clear()
                val = status_filter.value
                filtered = [m for m in machines if val == "All" or m["status"] == val]

                with container:
                    for m in filtered:
                        with ui.card().classes("p-5 glass-panel border border-[var(--border)] rounded-2xl flex flex-col justify-between"):
                            with ui.row().classes("justify-between items-start w-full"):
                                with ui.column().classes("gap-0"):
                                    ui.label(m["code"]).classes("font-black text-base text-[var(--accent-600)]")
                                    ui.label(m["name"]).classes("font-bold text-sm text-[var(--text)]")
                                    ui.label(m["type"]).classes("text-xs text-[var(--text-muted)]")
                                render_status_chip(m["status"])

                            ui.separator().classes("my-3")

                            # Specs
                            with ui.column().classes("gap-1 text-xs text-[var(--text)]"):
                                with ui.row().classes("justify-between w-full"):
                                    ui.label("Controller:").classes("text-[var(--text-muted)]")
                                    ui.label(m.get("controller_type", "Standard")).classes("font-semibold")

                                limits = m.get("travel_limits", {})
                                with ui.row().classes("justify-between w-full"):
                                    ui.label("Travel (X x Y x Z):").classes("text-[var(--text-muted)]")
                                    ui.label(f"{limits.get('x', 0)} x {limits.get('y', 0)} x {limits.get('z', 0)} mm").classes("font-mono")

                            # Active Operator / Job
                            ui.separator().classes("my-2")
                            if m.get("worker_name"):
                                with ui.column().classes("w-full gap-1"):
                                    with ui.row().classes("items-center justify-between text-xs"):
                                        ui.label(f"Operator: {m['worker_name']}").classes("font-semibold text-[var(--accent-900)]")
                                        ui.label(f"{m.get('progress_percent', 0)}%").classes("font-bold text-[var(--accent-600)]")
                                    if m.get("project_name"):
                                        ui.label(f"Job: {m['project_name']}").classes("text-[11px] text-[var(--text-muted)] truncate")
                                    ui.linear_progress(value=m.get("progress_percent", 0.0) / 100.0, color="primary", size="6px").classes("rounded-full")
                            else:
                                ui.label("Station Ready for Job Allocation").classes("text-xs text-green-700 italic")

            status_filter.on_value_change(refresh_grid)
            refresh_grid()
