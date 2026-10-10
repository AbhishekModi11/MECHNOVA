from datetime import datetime, timedelta, timezone
from nicegui import ui
from app.api_client import api
from app.session import require_auth
from app.components.layout import app_shell
from app.components.status_chip import render_status_chip


def register_machine_requests_page():
    @ui.page("/admin/requests")
    async def machine_requests_page():
        if not require_auth(allowed_roles=["admin"]):
            return

        app_shell("Machine Requests")

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            with ui.row().classes("justify-between items-center w-full"):
                with ui.column().classes("gap-1"):
                    ui.label("Machine Dispatch Requests & Approvals").classes("text-2xl font-black text-[var(--accent-900)] tracking-tight")
                    ui.label("Review worker job proposals, assign spindle slots, and prevent machine schedule overlaps.").classes("text-xs text-[var(--text-muted)]")

            # Load requests and machines
            try:
                requests_data = await api.get_machine_requests()
                mach_summary = await api.get_machines_summary()
                machines = mach_summary.get("machines", [])
                schedules = await api.get_schedule()
            except Exception as e:
                ui.notify(f"Could not load requests: {e}", type="negative")
                requests_data = []
                machines = []
                schedules = []

            # 1. PENDING REQUESTS SECTION
            with ui.card().classes("w-full p-5 glass-panel"):
                ui.label("Incoming Dispatch Queue").classes("font-bold text-base text-[var(--text)] mb-3")

                if not requests_data:
                    ui.label("No pending or handled machine requests at this time.").classes("text-xs text-[var(--text-muted)] italic")
                else:
                    for req in requests_data:
                        with ui.card().classes("p-4 border border-[var(--border)] rounded-xl w-full mb-3"):
                            with ui.row().classes("justify-between items-start w-full"):
                                with ui.column().classes("gap-1"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.label(req.get("project_name", "Job")).classes("font-bold text-base text-[var(--text)]")
                                        render_status_chip(req.get("status", "pending"))
                                    ui.label(f"Operator: {req.get('worker_name')} | Material: {req.get('material_id')}").classes("text-xs text-[var(--text-muted)]")

                                # Estimated Machining Time Badge
                                with ui.card().classes("p-2 bg-[var(--surface-alt)] border border-[var(--border)] text-right"):
                                    est_s = req.get("estimated_time_seconds", 0.0)
                                    mins = round(est_s / 60.0, 1)
                                    ui.label("Engine Estimated Cycle:").classes("text-[10px] text-[var(--text-muted)] font-bold uppercase")
                                    ui.label(f"{mins} min ({int(est_s)} s)").classes("text-sm font-extrabold text-[var(--accent-700)]")

                            if req.get("note"):
                                ui.label(f"Worker Note: \"{req['note']}\"").classes("text-xs italic text-[var(--text)] mt-2 bg-[var(--surface-alt)] p-2 rounded")

                            # Actions Row
                            if req.get("status") == "pending":
                                ui.separator().classes("my-3")
                                with ui.row().classes("justify-end items-center gap-3 w-full"):
                                    # Reject button & dialog
                                    ui.button("Reject", color="red", icon="close", on_click=lambda *_, r=req: open_reject_dialog(r)).props("flat dense")

                                    # Approve button & dialog
                                    ui.button("Approve & Schedule Slot", icon="check_circle", on_click=lambda *_, r=req: open_approve_dialog(r)).classes("btn-accent text-xs")

            # 2. SCHEDULE TIMELINE VIEW
            with ui.card().classes("w-full p-5 glass-panel mt-2"):
                ui.label("Shop Fleet Schedule Timeline").classes("font-bold text-base text-[var(--text)] mb-3")
                if not schedules:
                    ui.label("No active machine reservations scheduled.").classes("text-xs text-[var(--text-muted)] italic")
                else:
                    for s in schedules:
                        with ui.row().classes("justify-between items-center w-full p-2.5 border-b border-[var(--border)] text-xs"):
                            with ui.row().classes("items-center gap-3"):
                                ui.icon("precision_manufacturing", color="primary")
                                with ui.column().classes("gap-0"):
                                    ui.label(str(s.get("machine_name") or "Machine")).classes("font-bold text-[var(--text)]")
                                    ui.label(f"Job: {s.get('project_name')} (Worker: {s.get('worker_name')})").classes("text-[var(--text-muted)]")
                            with ui.row().classes("items-center gap-2"):
                                start_str = str(s.get("start") or "")[:16].replace("T", " ")
                                end_str = str(s.get("end") or "")[:16].replace("T", " ")
                                ui.label(f"{start_str}  ➔  {end_str}").classes("font-mono font-semibold text-[var(--accent-700)]")

        # Dialog: Approve Request with Conflict Gating
        def open_approve_dialog(req: dict):
            with ui.dialog() as dlg, ui.card().classes("w-full max-w-md p-6 glass-panel"):
                ui.label(f"Approve Job: {req.get('project_name')}").classes("text-lg font-bold text-[var(--text)] mb-2")
                
                # Machine dropdown
                m_opts = {m["id"]: f"{m['code']} - {m['name']} ({m['status']})" for m in machines}
                sel_m = ui.select(m_opts, label="Assign CNC Machine", value=req.get("requested_machine_id") or list(m_opts.keys())[0]).props("outlined dense w-full")

                # Date & Time Pickers
                now = datetime.now(timezone.utc) + timedelta(minutes=10)
                start_inp = ui.input("Scheduled Start (YYYY-MM-DD HH:MM)", value=now.strftime("%Y-%m-%d %H:%M")).props("outlined dense w-full")
                end_inp = ui.input("Scheduled End (YYYY-MM-DD HH:MM)", value=(now + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")).props("outlined dense w-full")
                note_inp = ui.input("Admin Dispatch Note", value="Approved for production.").props("outlined dense w-full")

                err_label = ui.label("").classes("text-xs text-red-600 font-semibold hidden")

                async def confirm_approve():
                    err_label.classes(remove="block", add="hidden")
                    if not start_inp.value or not end_inp.value or not sel_m.value:
                        err_label.set_text("Please fill in machine and scheduled time range.")
                        err_label.classes(remove="hidden", add="block")
                        return
                    try:
                        t_start = datetime.strptime(str(start_inp.value), "%Y-%m-%d %H:%M").isoformat()
                        t_end = datetime.strptime(str(end_inp.value), "%Y-%m-%d %H:%M").isoformat()
                        await api.approve_request(
                            request_id=req["id"],
                            machine_id=sel_m.value,
                            start=t_start,
                            end=t_end,
                            note=str(note_inp.value or "")
                        )
                        ui.notify("Job Approved and Scheduled successfully!", type="positive")
                        dlg.close()
                        ui.navigate.reload()
                    except Exception as ex:
                        err_label.set_text(str(ex))
                        err_label.classes(remove="hidden", add="block")

                with ui.row().classes("justify-end gap-2 w-full mt-4"):
                    ui.button("Cancel", on_click=dlg.close).props("flat")
                    ui.button("Confirm Approval", on_click=confirm_approve).classes("btn-accent text-xs")

            dlg.open()

        # Dialog: Reject Request
        def open_reject_dialog(req: dict):
            with ui.dialog() as dlg, ui.card().classes("w-full max-w-md p-6 glass-panel"):
                ui.label(f"Reject Job: {req.get('project_name')}").classes("text-lg font-bold text-red-700 mb-2")
                reason_inp = ui.input("Rejection Reason", value="Tool envelope or stock material conflict.").props("outlined dense w-full")

                async def confirm_reject():
                    try:
                        await api.reject_request(req["id"], str(reason_inp.value or "Rejected by admin"))
                        ui.notify("Job request rejected.", type="warning")
                        dlg.close()
                        ui.navigate.reload()
                    except Exception as ex:
                        ui.notify(f"Error: {ex}", type="negative")

                with ui.row().classes("justify-end gap-2 w-full mt-4"):
                    ui.button("Cancel", on_click=dlg.close).props("flat")
                    ui.button("Confirm Rejection", color="red", on_click=confirm_reject)

            dlg.open()
