from nicegui import ui
import asyncio
import datetime
import base64
from app.session import require_auth
from app.components.layout import app_shell
from app.components.page_header import render_page_header
from app.components.model_viewer import render_model_viewer
from app.services.project_service import (
    get_project, set_active_project_id, save_job_slip_action, update_project_raw_material
)
from app.services.suggested_tools import suggest_tools_for_project, generate_gcode_preview


def render_job_slip(pid: str):
    proj = get_project(pid)
    if not proj:
        with ui.column().classes("w-full py-16 items-center justify-center text-center gap-4"):
            ui.icon("layers_clear", size="56px").classes("text-slate-400")
            ui.label("Project Not Found").classes("text-xl font-bold")
            ui.button("Dashboard", on_click=lambda: ui.navigate.to("/worker")).classes("btn-primary")
        return

    set_active_project_id(pid)
    snapshot = proj.get("slip_snapshot")
    analysis = proj.get("analysis") or {}
    features = analysis.get("features", [])
    raw_mat = proj.get("material", "Aluminum 6061-T6")
    dims = proj.get("stock") or proj.get("dims") or [100.0, 60.0, 20.0]
    bbox = analysis.get("bbox", dims)

    # Use snapshot data if available (immutable record)
    if snapshot:
        p_no = snapshot.get("project_no", proj.get("project_no"))
        op_name = snapshot.get("operator_name") or snapshot.get("operator", "Elena Rostova")
        emp_id = snapshot.get("employee_id", "WRK-001")
        if isinstance(snapshot.get("raw_material"), dict):
            mat_name = snapshot["raw_material"].get("name", raw_mat)
            stock_dims = [
                float(snapshot["raw_material"].get("length", 100.0)),
                float(snapshot["raw_material"].get("width", 60.0)),
                float(snapshot["raw_material"].get("height", 20.0))
            ]
        else:
            mat_name = snapshot.get("material", raw_mat)
            stock_dims = snapshot.get("stock_dimensions", dims)
        suggested_tools = snapshot.get("suggested_tools", proj.get("suggested_tools", []))
        gcode = snapshot.get("gcode_preview", proj.get("gcode_preview", ""))
        status = snapshot.get("status", proj.get("status", "READY"))
        record_time = snapshot.get("date_time") or snapshot.get("timestamp") or proj.get("createdAt", "")
    else:
        p_no = proj.get("project_no", f"MN-2026-{pid[:4]}")
        op_name = proj.get("operator", "Elena Rostova")
        emp_id = proj.get("employee_id", "WRK-001")
        mat_name = raw_mat
        stock_dims = dims
        suggested_tools = proj.get("suggested_tools") or []
        if not suggested_tools and features:
            st_res = suggest_tools_for_project(mat_name, stock_dims, features, bbox)
            suggested_tools = st_res.get("tools", [])
            proj["suggested_tools"] = suggested_tools
        gcode = proj.get("gcode_preview") or generate_gcode_preview(p_no, mat_name, suggested_tools, features)
        status = proj.get("status", "READY")
        record_time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")

    confirmed_time = proj.get("confirmed_at")
    requested_time = proj.get("requested_at")

    with ui.column().classes("w-full gap-5"):
        # Header (Step 4 Active, Back goes to Step 3 Tools)
        render_page_header(
            title="Step 4: Final Job Slip & Dispatch",
            back_to=f"/worker/projects/{pid}/tools",
            subtitle="Pin-to-pin manufacturing inspection ticket, standard tooling verification, and spindle dispatch.",
            current_step=4,
            project_no=p_no,
            part_name=proj.get("partName")
        )

        # Status Notification Banner if confirmed or requested
        if status in ("CONFIRMED_BY_OPERATOR", "MACHINE_REQUESTED"):
            is_req = (status == "MACHINE_REQUESTED")
            bg_col = "bg-emerald-950/40 border-emerald-500/40" if is_req else "bg-sky-950/40 border-sky-500/40"
            text_col = "text-emerald-400" if is_req else "text-sky-400"
            icon_name = "precision_manufacturing" if is_req else "verified"
            title_text = "Machine Request Dispatched & Queued" if is_req else "Job Slip Confirmed by Operator"
            time_info = requested_time if is_req else confirmed_time

            with ui.row().classes(f"w-full p-4 rounded-2xl {bg_col} border items-center justify-between"):
                with ui.row().classes("items-center gap-3"):
                    ui.icon(icon_name, size="24px").classes(text_col)
                    with ui.column().classes("gap-0"):
                        ui.label(title_text).classes(f"font-black text-sm {text_col}")
                        ui.label(f"Recorded by {op_name} ({emp_id}) at {time_info}. Immutable snapshot saved to Project History.").classes("text-xs text-slate-300")
                with ui.row().classes("gap-2"):
                    ui.button("Print Slip", icon="print", on_click=lambda: ui.run_javascript("window.print()")).props("outline dense").classes("text-xs")
                    ui.button("Project History", on_click=lambda: ui.navigate.to("/worker/history")).props("dense").classes("btn-primary text-xs")

        # PRINTABLE JOB SLIP CONTAINER
        with ui.card().classes("w-full p-6 bg-slate-900/95 rounded-2xl border border-slate-700/80 shadow-lg flex flex-col gap-6 print:p-2 print:border-none print:shadow-none print:bg-white print:text-black"):
            
            # 1. Header Information Block (Pin-to-pin specifications)
            with ui.row().classes("w-full justify-between items-start border-b border-slate-700 pb-4 flex-wrap gap-4"):
                with ui.column().classes("gap-1"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label(p_no).classes("text-2xl font-black font-mono text-sky-400 tracking-tight")
                        status_col = "positive" if status == "MACHINE_REQUESTED" else ("primary" if status == "CONFIRMED_BY_OPERATOR" else "warning")
                        ui.badge(status, color=status_col).props("dense").classes("font-mono font-bold text-xs")
                    ui.label("MECHNOVA AUTONOMOUS CNC MACHINING ROUTING SLIP").classes("text-xs font-bold text-slate-400 tracking-wider uppercase")
                
                with ui.row().classes("items-center gap-6 text-xs text-slate-300 font-mono"):
                    with ui.column().classes("gap-0.5 text-right"):
                        ui.label("OPERATOR NAME").classes("text-[10px] text-slate-400 font-sans")
                        ui.label(op_name).classes("font-bold text-white")
                    with ui.column().classes("gap-0.5 text-right"):
                        ui.label("EMPLOYEE ID").classes("text-[10px] text-slate-400 font-sans")
                        ui.label(emp_id).classes("font-bold text-sky-300")
                    with ui.column().classes("gap-0.5 text-right"):
                        ui.label("DATE & TIME").classes("text-[10px] text-slate-400 font-sans")
                        ui.label(str(record_time)[:19]).classes("font-bold text-slate-300")

            # 2. Pin-to-pin Part & Raw Material Specifications
            with ui.grid(columns=2).classes("w-full gap-4"):
                # Left: Raw Material & Billet
                with ui.card().classes("p-4 bg-slate-950/60 rounded-xl border border-slate-800 flex flex-col gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("layers", size="18px", color="primary")
                        ui.label("Raw Material Stock Specification").classes("font-bold text-sm text-white")
                    
                    with ui.grid(columns=2).classes("w-full gap-3 text-xs pt-1"):
                        with ui.column().classes("gap-0"):
                            ui.label("Material Name:").classes("text-slate-400 text-[10px]")
                            ui.label(mat_name).classes("font-bold text-white text-xs")
                        with ui.column().classes("gap-0"):
                            ui.label("Stock Billet Dimensions:").classes("text-slate-400 text-[10px]")
                            ui.label(f"{stock_dims[0]:.1f} × {stock_dims[1]:.1f} × {stock_dims[2]:.1f} mm").classes("font-mono font-bold text-sky-300 text-xs")
                        with ui.column().classes("gap-0"):
                            ui.label("Part Bounding Box:").classes("text-slate-400 text-[10px]")
                            ui.label(f"{bbox[0]:.1f} × {bbox[1]:.1f} × {bbox[2]:.1f} mm").classes("font-mono font-bold text-slate-300 text-xs")
                        with ui.column().classes("gap-0"):
                            ui.label("Part File Reference:").classes("text-slate-400 text-[10px]")
                            ui.label(proj.get("file_name", "bracket.stl")).classes("font-mono text-slate-300 text-xs truncate")

                # Right: 3D CAD Preview Thumbnail
                with ui.card().classes("p-3 bg-slate-950/60 rounded-xl border border-slate-800 flex flex-col gap-1"):
                    with ui.row().classes("justify-between items-center w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("view_in_ar", size="18px", color="primary")
                            ui.label("3D CAD Model & Geometry Snapshot").classes("font-bold text-xs text-white")
                        ui.badge("Feature Overlay", color="dark").props("dense outline").classes("text-[9px] font-mono")

                    mesh_url = proj.get("mesh_url") or f"/api/projects/{pid}/mesh"
                    render_model_viewer(
                        mesh_url=mesh_url,
                        features_data=analysis,
                        container_height="170px",
                        initial_mode="critical"
                    )

            # 3. Detected Features Breakdown (Holes, Pockets, Slots, Critical Points)
            with ui.card().classes("w-full p-4 bg-slate-950/60 rounded-xl border border-slate-800 flex flex-col gap-3"):
                with ui.row().classes("justify-between items-center w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("filter_center_focus", size="18px", color="primary")
                        ui.label("Detected Topological Features & Critical Inspection Points").classes("font-bold text-sm text-white")
                    ui.badge(f"{len(features)} Features Detected", color="primary").props("dense outline").classes("text-xs font-mono")

                if features:
                    with ui.column().classes("w-full border border-slate-800 rounded-lg overflow-hidden text-xs"):
                        with ui.row().classes("w-full p-2 bg-slate-800/80 font-bold text-slate-300 justify-between items-center font-mono text-[11px]"):
                            ui.label("Feature ID & Kind").classes("w-44")
                            ui.label("Dimensions / Diameter").classes("w-36")
                            ui.label("Depth").classes("w-24")
                            ui.label("Type").classes("w-24")
                            ui.label("Setup").classes("w-20")

                        for f in features:
                            f_kind = f.get("kind", "").replace("_", " ").title()
                            f_size = f"⌀{f['diameter']:.1f} mm" if f.get("diameter") else f"{f.get('size',[0,0])[0]:.1f} × {f.get('size',[0,0])[1]:.1f} mm"
                            f_through = "Through" if f.get("through") else "Blind"
                            f_setup = f.get("setup", "+Z")

                            with ui.row().classes("w-full p-2 border-t border-slate-800 items-center justify-between text-slate-300 font-mono text-xs hover:bg-slate-800/30"):
                                with ui.row().classes("w-44 items-center gap-1.5"):
                                    ui.badge(f.get("id", "F"), color="primary" if "hole" in f.get("kind","") else "secondary").props("dense").classes("text-[10px]")
                                    ui.label(f_kind).classes("font-sans font-semibold text-white")
                                ui.label(f_size).classes("w-36 text-sky-300")
                                ui.label(f"{f.get('depth',0):.1f} mm").classes("w-24")
                                ui.label(f_through).classes("w-24 text-slate-400 font-sans")
                                ui.label(f_setup).classes("w-20 text-emerald-400 font-bold")
                else:
                    ui.label("No topological features detected.").classes("text-xs text-slate-400 italic")

            # 4. Suggested Machining Tools (from Section 1 standard catalog)
            with ui.card().classes("w-full p-4 bg-slate-950/60 rounded-xl border border-slate-800 flex flex-col gap-3"):
                with ui.row().classes("justify-between items-center w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("precision_manufacturing", size="18px", color="primary")
                        ui.label("Suggested Machining Tools (Autonomous Tooling Selection)").classes("font-bold text-sm text-white")
                    tot_m = round(sum(t.get("est_time_sec", 30) for t in suggested_tools) / 60.0, 1)
                    ui.badge(f"{len(suggested_tools)} Tools • Est: {tot_m} min", color="secondary").props("dense outline").classes("text-xs font-mono font-bold")

                if suggested_tools:
                    with ui.column().classes("w-full border border-slate-800 rounded-lg overflow-hidden text-xs"):
                        with ui.row().classes("w-full p-2 bg-slate-800/80 font-bold text-slate-300 justify-between items-center font-mono text-[11px]"):
                            ui.label("Tool #").classes("w-14")
                            ui.label("Tool Description").classes("w-48")
                            ui.label("Diameter").classes("w-24")
                            ui.label("Flutes").classes("w-16")
                            ui.label("Purpose / Operation").classes("w-56")
                            ui.label("Spindle (RPM)").classes("w-24")
                            ui.label("Feed (mm/min)").classes("w-24")

                        for t in suggested_tools:
                            with ui.row().classes("w-full p-2 border-t border-slate-800 items-center justify-between text-slate-300 font-mono text-xs hover:bg-slate-800/30"):
                                ui.badge(t.get("tool_no", "T01"), color="primary").props("dense").classes("w-14 text-[10px]")
                                ui.label(t.get("name", "Tool")).classes("w-48 font-semibold text-white truncate")
                                ui.label(f"{t.get('diameter', 10.0):.1f} mm").classes("w-24 text-sky-300")
                                ui.label(str(t.get("flutes", 2))).classes("w-16 text-slate-400")
                                ui.label(t.get("purpose", "")).classes("w-56 text-[11px] text-slate-300 truncate")
                                ui.label(f"{t.get('suggested_rpm', 3000)}").classes("w-24 text-emerald-400 font-bold")
                                ui.label(f"{t.get('suggested_feed', 500)}").classes("w-24 text-sky-400 font-bold")

            # 5. G-Code CNC Program Preview
            if gcode:
                with ui.card().classes("w-full p-4 bg-slate-950/60 rounded-xl border border-slate-800 flex flex-col gap-2"):
                    with ui.row().classes("justify-between items-center w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("code", size="18px", color="primary")
                            ui.label("Generated CNC G-Code (ISO 6983)").classes("font-bold text-sm text-white")
                        gcode_b64 = base64.b64encode(gcode.encode('utf-8')).decode('utf-8')
                        ui.button(
                            "Download .nc",
                            icon="download",
                            on_click=lambda pno=p_no, b64=gcode_b64: ui.run_javascript(
                                f"const a = document.createElement('a'); a.href = 'data:text/plain;base64,{b64}'; a.download = '{pno}.nc'; a.click();"
                            )
                        ).props("flat dense size=sm").classes("btn-primary text-xs font-bold")

                    ui.code(gcode, language="gcode").classes("w-full max-h-48 overflow-y-auto text-[11px] font-mono bg-slate-950 rounded-lg p-2.5 border border-slate-800")

        # 6. ACTION BUTTONS (Confirm by Operator & Machine Request)
        with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex justify-between items-center sticky bottom-4 z-20 border border-[var(--border)] shadow-xl print:hidden"):
            ui.button("← Back to Tools", on_click=lambda: ui.navigate.to(f"/worker/projects/{pid}/tools")).props("outlined").classes("text-xs font-semibold")

            with ui.row().classes("items-center gap-3"):
                ui.button("Print / Save PDF", icon="print", on_click=lambda: ui.run_javascript("window.print()")).props("outlined").classes("text-xs font-semibold")

                async def handle_confirm_by_operator():
                    try:
                        res = save_job_slip_action(pid, "confirm", operator_name="Elena Rostova", employee_id="WRK-001")
                        ui.notify("Job slip confirmed by Operator Elena Rostova (WRK-001)! Saved to Project History.", type="positive", position="top")
                        ui.navigate.to("/worker/history")
                    except Exception as ex:
                        ui.notify(f"Confirmation error: {ex}", type="negative", position="top")

                async def handle_machine_request():
                    try:
                        res = save_job_slip_action(pid, "request", operator_name="Elena Rostova", employee_id="WRK-001")
                        ui.notify("Machine Request dispatched for CNC spindle queue! Saved to Project History.", type="positive", position="top")
                        ui.navigate.to("/worker/history")
                    except Exception as ex:
                        ui.notify(f"Request error: {ex}", type="negative", position="top")

                confirm_op_btn = ui.button(
                    "Confirm by Operator",
                    icon="verified",
                    on_click=handle_confirm_by_operator
                ).classes("btn-secondary text-xs py-2.5 px-5 font-bold rounded-xl border border-sky-500 text-sky-300 hover:bg-sky-950/40")

                machine_req_btn = ui.button(
                    "Machine Request",
                    icon="send_and_archive",
                    on_click=handle_machine_request
                ).classes("btn-primary text-xs py-2.5 px-6 font-bold rounded-xl shadow-lg")


def register_job_slip_page():
    @ui.page("/worker/projects/{project_id}/summary")
    def job_slip_page(project_id: str):
        if not require_auth(allowed_roles=["worker"]):
            return
        app_shell("Step 4: Final Job Slip")
        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            render_job_slip(project_id)
