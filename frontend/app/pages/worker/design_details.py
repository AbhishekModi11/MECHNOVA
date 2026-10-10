from nicegui import ui
import asyncio
import base64
from app.session import require_auth
from app.components.layout import app_shell
from app.components.model_viewer import render_model_viewer
from app.components.page_header import render_page_header
from app.services.project_service import (
    get_project, get_active_project_id, set_active_project_id, update_feature_enabled,
    confirm_project_tools
)
from app.services.suggested_tools import suggest_tools_for_project, generate_gcode_preview


def render_empty_state():
    """Empty state rendered when no project is loaded. NEVER calls navigate()."""
    with ui.column().classes("w-full py-16 items-center justify-center text-center gap-4"):
        ui.icon("layers_clear", size="64px").classes("text-[var(--text-muted)] opacity-60")
        ui.label("No Active CAD Project Selected").classes("text-2xl font-bold text-[var(--accent-900)]")
        ui.label("Upload an STL, STEP, or reference image in Step 1 to inspect geometry, detect holes/pockets, and generate CNC tooling.").classes("text-sm text-[var(--text-muted)] max-w-md")
        ui.button("Start a new project", icon="add_circle", on_click=lambda: ui.navigate.to("/worker/new-project")).classes("btn-primary py-2.5 px-6 font-bold rounded-xl mt-2")


def render_project_view(pid: str):
    proj = get_project(pid)
    if not proj or not proj.get("analysis"):
        with ui.column().classes("w-full py-16 items-center justify-center text-center gap-4"):
            ui.icon("error_outline", size="56px").classes("text-amber-500")
            ui.label(f"Project #{pid} is not ready").classes("text-xl font-bold text-[var(--accent-900)]")
            status = proj.get("status", "NOT_FOUND") if proj else "NOT_FOUND"
            ui.label(f"Current project status is {status}. Please retry or create a new project.").classes("text-sm text-[var(--text-muted)]")
            with ui.row().classes("gap-3 mt-2"):
                ui.button("Start new project", icon="add", on_click=lambda: ui.navigate.to("/worker/new-project")).classes("btn-primary py-2 px-4 rounded-xl text-xs")
                ui.button("Back to Step 1", icon="arrow_back", on_click=lambda: ui.navigate.to(f"/worker/projects/{pid}/upload")).props("outlined").classes("text-xs")
        return

    # Update global active project
    set_active_project_id(pid)

    analysis = proj.get("analysis", {})
    summary = analysis.get("summary", {})
    bbox = analysis.get("bbox", proj.get("dims", [100, 60, 20]))
    features = analysis.get("features", [])
    issues = analysis.get("issues", [])
    plan = analysis.get("plan", {})
    operations = plan.get("operations", [])
    equipment = plan.get("equipment", {})

    # Suggested Tools from Autonomous Engine
    suggested_tools = proj.get("suggested_tools") or []
    dfm_warnings = proj.get("dfm_warnings") or []
    gcode_preview = proj.get("gcode_preview") or ""
    raw_mat = proj.get("material", "Aluminum 6061-T6")
    stock_dims = proj.get("stock") or proj.get("dims") or [100.0, 60.0, 20.0]

    if not suggested_tools and features:
        st_res = suggest_tools_for_project(raw_mat, stock_dims, features, bbox)
        suggested_tools = st_res.get("tools", [])
        dfm_warnings = st_res.get("dfm_warnings", [])
        gcode_preview = generate_gcode_preview(proj.get("project_no", f"MN-2026-{pid[:4]}"), raw_mat, suggested_tools, features)

    with ui.column().classes("w-full gap-5"):
        # Unified Header with Step Bar (Step 2 active, Back to Step 1 upload)
        render_page_header(
            title="Step 2: Design Details & Auto Tooling",
            back_to=f"/worker/projects/{pid}/upload",
            subtitle="Topological feature inspection and autonomous tooling suggestions from standard catalog.",
            current_step=2,
            project_no=proj.get("project_no"),
            part_name=proj.get("partName")
        )

        # Suggested Tools Panel
        with ui.card().classes("w-full p-4 rounded-2xl border border-[var(--border)] glass-panel shadow-sm flex flex-col gap-3"):
            with ui.row().classes("justify-between items-center w-full flex-wrap gap-2"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("precision_manufacturing", size="22px").classes("text-[var(--accent)]")
                    with ui.column().classes("gap-0"):
                        ui.label("Suggested Machining Tools (Standard Tool Catalog)").classes("font-black text-sm text-[var(--text)]")
                        ui.label(f"Calculated for {raw_mat} • Stock {stock_dims[0]:.1f} × {stock_dims[1]:.1f} × {stock_dims[2]:.1f} mm").classes("text-[11px] text-[var(--text-muted)]")

                with ui.row().classes("items-center gap-2"):
                    ui.badge(f"{len(suggested_tools)} Tools Planned", color="primary").props("dense outline").classes("text-xs font-bold font-mono px-2 py-0.5")
                    tot_m = round(sum(t.get("est_time_sec", 30) for t in suggested_tools) / 60.0, 1)
                    ui.badge(f"Est: {tot_m} min", color="secondary").props("dense outline").classes("text-xs font-bold font-mono px-2 py-0.5")

            # Suggested Tool Cards
            with ui.row().classes("w-full gap-2.5 overflow-x-auto py-1"):
                for t in suggested_tools:
                    t_no = t.get("tool_no", "T01")
                    t_name = t.get("name", "Tool")
                    dia = float(t.get("diameter", 10.0))
                    flutes = t.get("flutes", 2)
                    rpm = t.get("suggested_rpm", 3000)
                    feed = t.get("suggested_feed", 500)
                    purpose = t.get("purpose", "Machining")
                    mat_coat = f"{t.get('material', 'Carbide')} • {t.get('coating', 'Uncoated')}"

                    with ui.card().classes("p-3 bg-slate-900/80 rounded-xl border border-slate-700 min-w-[230px] max-w-[270px] flex flex-col gap-1.5 flex-shrink-0 hover:border-sky-500 transition-all"):
                        with ui.row().classes("justify-between items-center w-full"):
                            ui.badge(t_no, color="primary").props("dense").classes("text-[11px] font-mono font-bold")
                            ui.badge(f"dia {dia:.1f} mm", color="dark").props("dense outline").classes("text-[10px] font-mono font-bold text-sky-300")

                        ui.label(t_name).classes("text-xs font-bold text-white truncate")
                        ui.label(purpose).classes("text-[10px] text-slate-300 line-clamp-2 h-7")

                        ui.separator().classes("bg-slate-800")

                        with ui.column().classes("gap-0.5 text-[10px] text-slate-300"):
                            with ui.row().classes("justify-between w-full"):
                                ui.label("Specs:").classes("text-slate-400")
                                ui.label(f"{flutes} flutes | {mat_coat}").classes("font-mono text-slate-200")
                            with ui.row().classes("justify-between w-full"):
                                ui.label("Spindle:").classes("text-slate-400")
                                ui.label(f"{rpm} RPM (suggested)").classes("font-mono font-bold text-emerald-400")
                            with ui.row().classes("justify-between w-full"):
                                ui.label("Feed:").classes("text-slate-400")
                                ui.label(f"{feed} mm/min (suggested)").classes("font-mono font-bold text-sky-400")

            # DFM Notices if any
            if dfm_warnings:
                with ui.column().classes("w-full gap-1 p-2.5 rounded-xl bg-amber-950/40 border border-amber-800"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("warning", size="16px", color="warning")
                        ui.label("Design for Manufacturability (DFM) Notices").classes("text-xs font-bold text-amber-300")
                    for w in dfm_warnings:
                        with ui.row().classes("items-start gap-2 text-xs text-amber-100"):
                            ui.badge(w.get("code", "DFM"), color="warning").props("dense outline").classes("text-[9px] font-mono")
                            ui.label(w.get("message", "")).classes("text-[11px] flex-1")

            # G-code Preview Expander
            if gcode_preview:
                with ui.expansion("G-Code CNC Preview (ISO 6983)", icon="code").classes("w-full text-xs font-semibold text-slate-200 bg-slate-950/40 rounded-xl border border-slate-800"):
                    with ui.column().classes("w-full p-3 gap-2"):
                        with ui.row().classes("w-full justify-between items-center"):
                            ui.label(f"CNC Program: {proj.get('project_no', 'MN-2026-0001')}.nc").classes("text-xs font-mono text-sky-400")
                            gcode_b64 = base64.b64encode(gcode_preview.encode('utf-8')).decode('utf-8')
                            pno = proj.get('project_no', 'job_program')
                            ui.button(
                                "Download .nc",
                                icon="download",
                                on_click=lambda pno=pno, b64=gcode_b64: ui.run_javascript(
                                    f"const a = document.createElement('a'); a.href = 'data:text/plain;base64,{b64}'; a.download = '{pno}.nc'; a.click();"
                                )
                            ).props("flat dense size=sm").classes("btn-primary text-xs font-bold")

                        ui.code(gcode_preview, language="gcode").classes("w-full max-h-52 overflow-y-auto text-[11px] font-mono bg-slate-950 rounded-lg p-2.5 border border-slate-800")

        # Split Layout: Left 55% 3D Viewer, Right 45% Scrolling Cards
        with ui.row().classes("w-full gap-6 items-start flex-wrap lg:flex-nowrap"):
            # LEFT (55%): 3D Viewer with feature markers
            with ui.card().classes("w-full lg:w-[55%] p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm sticky top-4"):
                with ui.row().classes("justify-between items-center w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("view_in_ar", size="20px", color="primary")
                        ui.label("Interactive CAD Feature Viewer").classes("font-bold text-sm text-[var(--text)]")
                    ui.badge("360° Free Orbit", color="dark").props("dense outline").classes("text-[10px] font-mono")

                mesh_url = proj.get("mesh_url") or f"/api/projects/{pid}/mesh"
                render_model_viewer(
                    mesh_url=mesh_url,
                    features_data=analysis,
                    container_height="520px",
                    initial_mode="critical"
                )

                with ui.row().classes("w-full justify-between items-center text-[11px] text-[var(--text-muted)] px-1"):
                    ui.label("Tip: Critical mode displays through-holes (Red), blind holes (Orange), pockets (Green), and slots (Blue) with ID badges.")
                    ui.button("Fit View", icon="fit_screen", on_click=lambda: ui.run_javascript("if(window[Object.keys(window).find(k=>k.startsWith('viewer3d_'))]) window[Object.keys(window).find(k=>k.startsWith('viewer3d_'))].fit();")).props("flat dense size=sm").classes("text-xs")

            # RIGHT (45%): Scrolling Cards
            with ui.column().classes("w-full lg:w-[45%] gap-5"):
                # 1. Design Overview Card
                with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("dashboard", size="20px", color="primary")
                            ui.label("1. Design Overview").classes("font-bold text-sm text-[var(--text)]")
                        ui.badge(f"{len(features)} Features Detected", color="primary").props("dense outline").classes("text-xs font-mono")

                    with ui.grid(columns=3).classes("w-full gap-2 text-center"):
                        with ui.card().classes("p-2 bg-slate-900/50 rounded-xl border border-slate-800"):
                            ui.label("Holes").classes("text-[10px] text-slate-400 font-bold uppercase")
                            ui.label(str(summary.get("holes", 0))).classes("text-xl font-black text-rose-400 font-mono")
                        with ui.card().classes("p-2 bg-slate-900/50 rounded-xl border border-slate-800"):
                            ui.label("Pockets / Slots").classes("text-[10px] text-slate-400 font-bold uppercase")
                            ui.label(str(summary.get("pockets", 0))).classes("text-xl font-black text-emerald-400 font-mono")
                        with ui.card().classes("p-2 bg-slate-900/50 rounded-xl border border-slate-800"):
                            ui.label("Setups").classes("text-[10px] text-slate-400 font-bold uppercase")
                            ui.label(str(equipment.get("setups", 1))).classes("text-xl font-black text-sky-400 font-mono")

                    with ui.row().classes("w-full justify-between items-center text-xs py-1 px-2 bg-slate-900/30 rounded-lg"):
                        ui.label("Mesh Health Status:").classes("text-slate-400")
                        has_error = any(i.get("severity") == "error" for i in issues)
                        ui.badge("Needs Attention" if has_error else "Watertight Solid", color="negative" if has_error else "positive").props("dense")

                # 2. Features Table Card with Enabled Toggle
                with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("table_rows", size="20px", color="primary")
                            ui.label("2. Topological Features").classes("font-bold text-sm text-[var(--text)]")
                        ui.label("Operator verification").classes("text-[11px] text-[var(--text-muted)] italic")

                    with ui.column().classes("w-full gap-1.5 max-h-64 overflow-y-auto"):
                        for f in features:
                            fid = f.get("id", "F")
                            f_kind = f.get("kind", "").replace("_", " ").title()
                            f_size = f"⌀{f['diameter']:.1f}mm" if f.get("diameter") else f"{f.get('size',[0,0])[0]:.1f}×{f.get('size',[0,0])[1]:.1f}mm"
                            f_through = "Through" if f.get("through") else "Blind"
                            f_setup = f.get("setup", "+Z")

                            with ui.row().classes("w-full justify-between items-center text-xs p-2 bg-slate-900/60 rounded-xl border border-slate-700 hover:border-sky-500"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.badge(fid, color="primary" if "hole" in f.get("kind","") else "secondary").props("dense outline").classes("font-bold font-mono")
                                    with ui.column().classes("gap-0"):
                                        ui.label(f"{f_kind} ({f_through})").classes("font-semibold text-white")
                                        ui.label(f"{f_size} • Depth: {f.get('depth',0):.1f}mm • Setup {f_setup}").classes("text-[10px] text-slate-400 font-mono")

                                async def handle_toggle(e, feature_id=fid):
                                    await update_feature_enabled(pid, feature_id, e.value)
                                    ui.notify(f"Updated feature {feature_id} (Enabled: {e.value}). Plan refreshed.", type="info", position="top")

                                ui.switch(value=f.get("enabled", True), on_change=handle_toggle).props("dense size=sm")

                # 3. Issues & Health Card
                with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("health_and_safety", size="20px", color="warning" if issues else "positive")
                            ui.label("3. Mesh Health & Manufacturing Checks").classes("font-bold text-sm text-[var(--text)]")
                        ui.badge(f"{len(issues)} Checked", color="dark").props("dense outline").classes("text-xs font-mono")

                    if issues:
                        with ui.column().classes("w-full gap-1.5"):
                            for issue in issues:
                                sev = issue.get("severity", "info")
                                col = "negative" if sev == "error" else ("warning" if sev == "warning" else "info")
                                with ui.row().classes(f"w-full items-start gap-2 p-2 rounded-lg bg-slate-900/50 border border-slate-800 text-xs"):
                                    ui.badge(sev.upper(), color=col).props("dense").classes("text-[10px] font-bold")
                                    with ui.column().classes("gap-0 flex-1"):
                                        ui.label(issue.get("code", "CHECK")).classes("font-mono font-bold text-slate-200 text-[11px]")
                                        ui.label(issue.get("message", "")).classes("text-slate-400 text-[11px]")
                    else:
                        ui.label("✓ No topology or boundary issues detected in this model.").classes("text-xs text-emerald-400 font-semibold p-2 bg-emerald-950/20 rounded-lg")

                # 4. Machining Plan Operations Card
                with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
                    with ui.row().classes("items-center justify-between w-full"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("format_list_numbered", size="20px", color="primary")
                            ui.label("4. Operation Plan").classes("font-bold text-sm text-[var(--text)]")
                        ui.badge(f"{len(operations)} Operations", color="primary").props("dense outline").classes("text-xs font-mono")

                    with ui.column().classes("w-full gap-1.5 max-h-56 overflow-y-auto"):
                        for op in operations:
                            with ui.row().classes("w-full justify-between items-center text-xs p-2 bg-slate-900/50 rounded-xl border border-slate-800"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.badge(str(op.get("order", 1)), color="dark").props("dense").classes("font-mono text-[10px]")
                                    ui.label(op.get("name", "Operation")).classes("font-semibold text-slate-200")
                                with ui.row().classes("items-center gap-2"):
                                    ui.badge(f"Tool: {op.get('tool', 'T1')}", color="secondary").props("dense outline").classes("text-[10px]")
                                    ui.badge(f"Setup {op.get('setup', '+Z')}", color="dark").props("dense").classes("text-[10px]")

        # Footer Actions
        with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm mt-2"):
            with ui.row().classes("w-full justify-between items-center flex-wrap gap-3"):
                ui.button("← Back to Step 1", icon="arrow_back", on_click=lambda: ui.navigate.to(f"/worker/projects/{pid}/upload")).props("outlined").classes("text-xs font-semibold")

                def handle_confirm_tools():
                    try:
                        confirm_project_tools(pid)
                        ui.notify("Tool set confirmed. Navigating to Step 3 Tools & Equipment...", type="positive", position="top")
                        ui.navigate.to(f"/worker/projects/{pid}/tools")
                    except Exception as ex:
                        ui.notify(f"Confirmation note: {ex}", type="info", position="top")
                        ui.navigate.to(f"/worker/projects/{pid}/tools")

                ui.button(
                    "Confirm tools & continue →",
                    on_click=handle_confirm_tools
                ).classes("btn-primary text-xs py-2.5 px-6 font-bold rounded-xl")


def register_design_details_page():
    @ui.page("/worker/projects/{project_id}/design-details")
    def design_details_by_id_page(project_id: str):
        if not require_auth(allowed_roles=["worker"]):
            return
        app_shell("Design Details")
        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            render_project_view(project_id)

    @ui.page("/worker/design")
    def design_details_entry_page():
        """Resolves active project id. If none, renders clean empty state. NEVER calls navigate()."""
        if not require_auth(allowed_roles=["worker"]):
            return
        app_shell("Design Details")
        active_id = get_active_project_id()
        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            if active_id:
                render_project_view(active_id)
            else:
                render_empty_state()
