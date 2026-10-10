from nicegui import ui
from app.api_client import api
from app.session import require_auth
from app.components.layout import app_shell
from app.components.kpi_card import render_kpi_card
from app.components.charts import render_attendance_chart, render_monthly_target_gauge


def register_worker_details_page():
    @ui.page("/admin/workers")
    async def worker_details_page():
        if not require_auth(allowed_roles=["admin"]):
            return

        app_shell("Worker Details")

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            with ui.row().classes("justify-between items-center w-full"):
                with ui.column().classes("gap-1"):
                    ui.label("Shop Floor Personnel & Attendance").classes("text-2xl font-black text-[var(--accent-900)] tracking-tight")
                    ui.label("Worker shifts, today's station assignments, and 90-day attendance analytics.").classes("text-xs text-[var(--text-muted)]")

            try:
                data = await api.get_workers()
                summary = data.get("summary", {})
                workers = data.get("workers", [])
            except Exception as e:
                ui.notify(f"Could not load workers: {e}", type="negative")
                summary = {"total_workers": 6, "present_today": 6, "absent_today": 0, "on_machine_count": 2}
                workers = []

            # KPI Row
            with ui.row().classes("w-full gap-4 flex-wrap"):
                render_kpi_card("Total Staff", str(summary.get("total_workers", 0)), "Registered Operators", "groups")
                render_kpi_card("Present Today", str(summary.get("present_today", 0)), "Clocked In", "check_circle", accent=True)
                render_kpi_card("Absent / Leave", str(summary.get("absent_today", 0)), "Off Duty", "event_busy")
                render_kpi_card("Operating Spindles", str(summary.get("on_machine_count", 0)), "Active on CNC Fleet", "precision_manufacturing")

            # Workers Table
            columns = [
                {"name": "company_id", "label": "Badge ID", "field": "company_id", "sortable": True},
                {"name": "name", "label": "Full Name", "field": "name", "sortable": True},
                {"name": "status_today", "label": "Today's Status", "field": "status_today"},
                {"name": "assigned_machine", "label": "Assigned Machine", "field": "assigned_machine"},
                {"name": "actions", "label": "Actions", "field": "actions"}
            ]

            table = ui.table(columns=columns, rows=workers, row_key="id").classes("w-full glass-panel shadow-sm")
            table.add_slot('body-cell-status_today', '''
                <q-td :props="props">
                    <q-badge :color="props.value === 'present' ? 'positive' : 'negative'" :label="props.value.toUpperCase()" />
                </q-td>
            ''')
            table.add_slot('body-cell-actions', '''
                <q-td :props="props">
                    <q-btn flat dense round icon="visibility" color="primary" @click="() => $parent.$emit('view_worker', props.row)" />
                </q-td>
            ''')

            async def handle_view_worker(e):
                row = e.args
                try:
                    detail = await api.get_worker_detail(row["id"])
                    show_worker_dialog(detail)
                except Exception as ex:
                    ui.notify(f"Error fetching worker details: {ex}", type="negative")

            table.on('view_worker', handle_view_worker)

        def show_worker_dialog(detail: dict):
            w = detail.get("worker", {})
            att = detail.get("attendance", {})
            metrics = detail.get("metrics", {})

            with ui.dialog() as dialog, ui.card().classes("w-full max-w-2xl p-6 glass-panel"):
                with ui.row().classes("justify-between items-start w-full border-b border-[var(--border)] pb-3"):
                    with ui.column().classes("gap-0"):
                        ui.label(w.get("name")).classes("text-xl font-black text-[var(--accent-900)]")
                        ui.label(f"Badge ID: {w.get('company_id')} | {w.get('company_email')}").classes("text-xs text-[var(--text-muted)]")
                    ui.button(icon="close", on_click=dialog.close).props("flat round dense")

                with ui.row().classes("w-full gap-4 mt-3"):
                    with ui.column().classes("flex-1 p-3 border border-[var(--border)] rounded-xl"):
                        ui.label("Monthly Attendance (90-Day)").classes("text-xs font-bold text-[var(--text-muted)] uppercase mb-2")
                        render_attendance_chart(att.get("history", []))

                    with ui.column().classes("flex-1 p-3 border border-[var(--border)] rounded-xl"):
                        ui.label("Completed Projects vs Target").classes("text-xs font-bold text-[var(--text-muted)] uppercase mb-2")
                        render_monthly_target_gauge(
                            completed=metrics.get("month_completed", 0),
                            target=metrics.get("monthly_target", 8)
                        )

            dialog.open()
