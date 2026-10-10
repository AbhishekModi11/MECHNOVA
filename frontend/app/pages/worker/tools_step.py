from nicegui import ui
import asyncio
from app.session import require_auth
from app.components.layout import app_shell
from app.components.page_header import render_page_header
from app.services.project_service import (
    get_project, get_tools, get_active_project_id, set_active_project_id
)
from app.services.suggested_tools import (
    suggest_tools_for_project, STANDARD_FACE_MILLS, STANDARD_END_MILL_DIAMETERS, MATERIAL_CATALOG
)


def render_tools_step(pid: str):
    proj = get_project(pid)
    if not proj or not proj.get("analysis"):
        with ui.column().classes("w-full py-16 items-center justify-center text-center gap-4"):
            ui.icon("layers_clear", size="56px").classes("text-slate-400")
            ui.label("Project Not Found").classes("text-xl font-bold")
            ui.button("Start New Project", on_click=lambda: ui.navigate.to("/worker/new-project")).classes("btn-primary")
        return

    set_active_project_id(pid)
    analysis = proj.get("analysis", {})
    features = analysis.get("features", [])
    plan = analysis.get("plan", {})
    equipment = plan.get("equipment", {})
    raw_mat = proj.get("material", "Aluminum 6061-T6")
    stock_dims = proj.get("stock") or proj.get("dims") or [100.0, 60.0, 20.0]

    # Get suggested tools or compute from standard catalog
    suggested_tools = proj.get("suggested_tools") or []
    if not suggested_tools:
        st_res = suggest_tools_for_project(raw_mat, stock_dims, features, analysis.get("bbox"))
        suggested_tools = st_res.get("tools", [])

    mat_info = MATERIAL_CATALOG.get(raw_mat, MATERIAL_CATALOG["Aluminum 6061-T6"])

    with ui.column().classes("w-full gap-5"):
        # Header with Step 3 Active, Back to Step 2 Design Details
        render_page_header(
            title="Step 3: Tools & Equipment Setup",
            back_to=f"/worker/projects/{pid}/design-details",
            subtitle="Verify planned tooling carousel, inspect cutting speeds, and confirm machine setup.",
            current_step=3,
            project_no=proj.get("project_no"),
            part_name=proj.get("partName")
        )

        # Main Split Content: Two Panels Side by Side
        with ui.row().classes("w-full gap-6 items-start flex-wrap lg:flex-nowrap"):
            # LEFT PANEL: Suggested Tools Planned for This Job
            with ui.card().classes("w-full lg:w-1/2 p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
                with ui.row().classes("justify-between items-center w-full"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("precision_manufacturing", size="20px", color="primary")
                        ui.label("Planned Tooling (Standard Tool Catalog)").classes("font-black text-sm text-[var(--text)]")
                    ui.badge(f"{len(suggested_tools)} Tools Planned", color="primary").props("dense outline").classes("text-xs font-mono font-bold")

                with ui.column().classes("w-full gap-2.5"):
                    for t in suggested_tools:
                        t_no = t.get("tool_no", "T01")
                        t_name = t.get("name", "Tool")
                        dia = float(t.get("diameter", 10.0))
                        flutes = int(t.get("flutes", 2))
                        rpm = t.get("suggested_rpm", 3000)
                        feed = t.get("suggested_feed", 500)
                        purpose = t.get("purpose", "Machining operation")
                        mat_coat = f"{t.get('material', 'Carbide')} • {t.get('coating', 'Uncoated')}"
                        flute_len = t.get("flute_length", 30.0)

                        with ui.card().classes("w-full p-3 bg-slate-900/70 rounded-xl border border-slate-700/80 flex flex-col gap-2 hover:border-sky-500 transition-all"):
                            with ui.row().classes("justify-between items-center w-full"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.badge(t_no, color="primary").props("dense").classes("font-mono font-bold text-xs")
                                    ui.label(t_name).classes("font-bold text-xs text-white")
                                ui.badge(f"dia {dia:.1f} mm", color="dark").props("dense outline").classes("text-[10px] font-mono text-sky-300 font-bold")

                            ui.label(purpose).classes("text-[11px] text-slate-300")

                            with ui.row().classes("justify-between items-center w-full text-[10px] text-slate-300 pt-1 border-t border-slate-800"):
                                ui.label(f"Flutes: {flutes} | Length: {flute_len:.0f}mm").classes("font-mono text-slate-400")
                                ui.label(mat_coat).classes("text-slate-400")

                            with ui.row().classes("justify-between items-center w-full text-xs bg-slate-950/60 p-2 rounded-lg"):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.label("Spindle:").classes("text-[10px] text-slate-400")
                                    ui.label(f"{rpm} RPM").classes("font-mono font-bold text-emerald-400 text-xs")
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.label("Feed Rate:").classes("text-[10px] text-slate-400")
                                    ui.label(f"{feed} mm/min").classes("font-mono font-bold text-sky-400 text-xs")

            # RIGHT PANEL: Standard Tool Catalog & Machining Parameters
            with ui.card().classes("w-full lg:w-1/2 p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
                with ui.row().classes("justify-between items-center w-full flex-wrap gap-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("menu_book", size="20px", color="primary")
                        ui.label("Machining Library & Cutting Speeds").classes("font-black text-sm text-[var(--text)]")
                    ui.badge(raw_mat, color="secondary").props("dense").classes("text-xs font-mono font-bold")

                # Cutting speed parameters card
                with ui.card().classes("w-full p-3 bg-slate-950/70 rounded-xl border border-slate-800 text-xs flex flex-col gap-2"):
                    ui.label("Material Cutting Coefficients (ISO 513 Standards)").classes("font-bold text-white text-xs")
                    with ui.grid(columns=3).classes("w-full gap-2 text-center text-xs"):
                        with ui.card().classes("p-2 bg-slate-900 rounded-lg border border-slate-800"):
                            ui.label("Vc Milling").classes("text-[10px] text-slate-400 font-bold")
                            ui.label(f"{mat_info.get('vc_milling', 280.0)} m/min").classes("text-sm font-mono font-bold text-emerald-400")
                        with ui.card().classes("p-2 bg-slate-900 rounded-lg border border-slate-800"):
                            ui.label("Vc Drilling").classes("text-[10px] text-slate-400 font-bold")
                            ui.label(f"{mat_info.get('vc_drilling', 90.0)} m/min").classes("text-sm font-mono font-bold text-sky-400")
                        with ui.card().classes("p-2 bg-slate-900 rounded-lg border border-slate-800"):
                            ui.label("Feed per Tooth (fz)").classes("text-[10px] text-slate-400 font-bold")
                            ui.label(f"{mat_info.get('fz_rough', mat_info.get('fz_endmill', 0.07))} mm/z").classes("text-sm font-mono font-bold text-amber-400")

                    with ui.row().classes("justify-between items-center text-[11px] text-slate-300 pt-1"):
                        ui.label(f"Recommended Tool Substrate: {mat_info.get('tool_material', 'Solid Carbide')}")
                        ui.badge(mat_info.get('coating', 'Uncoated / ZrN'), color="dark").props("dense")

                # Standard Series Catalog Reference
                ui.label("Standard Series Metric Tools").classes("text-xs font-bold text-[var(--text-muted)] mt-1")
                with ui.column().classes("w-full gap-1.5 max-h-[340px] overflow-y-auto"):
                    # Face Mills
                    with ui.card().classes("p-2.5 bg-slate-900/50 rounded-xl border border-slate-800 flex flex-col gap-1"):
                        ui.label("Standard Face Mills").classes("text-xs font-bold text-sky-300")
                        with ui.row().classes("gap-2 flex-wrap text-[11px]"):
                            for fm in STANDARD_FACE_MILLS:
                                ui.badge(f"dia {fm['diameter']}mm ({fm['inserts']} inserts)", color="dark").props("dense outline")

                    # End Mills
                    with ui.card().classes("p-2.5 bg-slate-900/50 rounded-xl border border-slate-800 flex flex-col gap-1"):
                        ui.label("Standard End Mill Series (Roughing & Finishing)").classes("text-xs font-bold text-emerald-300")
                        with ui.row().classes("gap-1.5 flex-wrap text-[11px]"):
                            for em_d in STANDARD_END_MILL_DIAMETERS:
                                ui.badge(f"dia {em_d}mm", color="dark").props("dense outline")

                    # Center / Spot & Chamfer
                    with ui.card().classes("p-2.5 bg-slate-900/50 rounded-xl border border-slate-800 flex flex-col gap-1"):
                        ui.label("Drilling & Edge Preparation").classes("text-xs font-bold text-amber-300")
                        with ui.row().classes("gap-2 flex-wrap text-[11px]"):
                            ui.badge("Spot Drill 90 deg dia 10mm", color="dark").props("dense outline")
                            ui.badge("Chamfer Mill 90 deg dia 12mm", color="dark").props("dense outline")
                            ui.badge("Peck Drilling Cycle: G83 (>5xD)", color="dark").props("dense outline")

        # Under Both Panels: Equipment & Workholding Card
        with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-col gap-3 border border-[var(--border)] shadow-sm"):
            with ui.row().classes("items-center justify-between w-full"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("precision_manufacturing", size="20px", color="primary")
                    ui.label("Equipment & Workholding Specification").classes("font-black text-sm text-[var(--text)]")
                ui.badge(f"Magazine Slots Needed: {len(suggested_tools)}", color="dark").props("dense outline").classes("text-xs font-mono")

            with ui.grid(columns=3).classes("w-full gap-3 text-xs"):
                with ui.card().classes("p-3 bg-slate-900/50 rounded-xl border border-slate-800 flex flex-col gap-0.5"):
                    ui.label("Assigned CNC Machine").classes("text-slate-400 text-[10px] uppercase font-bold")
                    ui.label(equipment.get("machine", "3-axis vertical machining centre")).classes("font-bold text-white text-xs")
                with ui.card().classes("p-3 bg-slate-900/50 rounded-xl border border-slate-800 flex flex-col gap-0.5"):
                    ui.label("Workholding Fixture").classes("text-slate-400 text-[10px] uppercase font-bold")
                    ui.label(equipment.get("workholding", "Precision vise, 150 mm, with soft jaws")).classes("font-bold text-white text-xs")
                with ui.card().classes("p-3 bg-slate-900/50 rounded-xl border border-slate-800 flex flex-col gap-0.5"):
                    ui.label("Coolant & Work Probe").classes("text-slate-400 text-[10px] uppercase font-bold")
                    ui.label(f"{equipment.get('coolant', 'Flood')} • {equipment.get('probe', 'Touch probe')}").classes("font-bold text-white text-xs")

        # Bottom Actions Bar
        with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex justify-between items-center border border-[var(--border)] shadow-sm"):
            ui.button("← Back to Design Details", on_click=lambda: ui.navigate.to(f"/worker/projects/{pid}/design-details")).props("outlined").classes("text-xs font-semibold")

            def handle_proceed_to_summary():
                ui.notify("Tool set verified! Generating final job slip...", type="positive", position="top")
                ui.navigate.to(f"/worker/projects/{pid}/summary")

            ui.button(
                "Confirm tool set & go to final slip →",
                on_click=handle_proceed_to_summary
            ).classes("btn-primary text-xs py-2.5 px-6 font-bold rounded-xl")


def register_tools_step_page():
    @ui.page("/worker/projects/{project_id}/tools")
    def tools_step_page(project_id: str):
        if not require_auth(allowed_roles=["worker"]):
            return
        app_shell("Step 3: Tools & Equipment")
        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            render_tools_step(project_id)
