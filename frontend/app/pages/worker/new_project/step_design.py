import asyncio
import os
from pathlib import Path
from nicegui import ui
import httpx
from app.components.model_viewer import render_model_viewer
from app.components.page_header import render_page_header
from app.components.progress_bar import render_progress_bar
from app.services.project_service import (
    create_project, get_project, update_project_status, set_active_project_id, get_active_project_id, auto_select_tools,
    update_project_raw_material
)

MATERIALS = [
    {"label": "Aluminum 6061-T6", "value": "Aluminum 6061-T6"},
    {"label": "Mild Steel 1018", "value": "Mild Steel 1018"},
    {"label": "Stainless 304", "value": "Stainless 304"},
    {"label": "Titanium Ti-6Al-4V", "value": "Titanium Ti-6Al-4V"},
]

CAD_ANALYZE_URL = "http://127.0.0.1:8001/analyze"


def render_step_design(state: dict = None, project_id: str = None):
    """
    Step 1: Part Design & CAD Specification with genuine hole/pocket detection.
    Analyzes STL, STEP, and image files, presents 3D preview with features,
    and forwards project ID directly to Step 2 Design Details.
    """
    state = state or {}
    curr_id = project_id or get_active_project_id() or state.get("project_id")

    # If loading an existing project by ID, restore state
    existing_proj = get_project(curr_id) if curr_id else None
    if existing_proj:
        state["project_id"] = existing_proj["id"]
        state["name"] = existing_proj["partName"]
        state["material_name"] = existing_proj["material"]
        state["length"] = existing_proj["length"]
        state["width"] = existing_proj["width"]
        state["height"] = existing_proj["height"]
        if existing_proj.get("mesh_url"):
            state["mesh_url"] = existing_proj["mesh_url"]
        if existing_proj.get("analysis"):
            state["analysis"] = existing_proj["analysis"]
        state["filename"] = existing_proj.get("file_name", "bracket.stl")

    if "length" not in state:
        state["length"] = 100.0
    if "width" not in state:
        state["width"] = 60.0
    if "height" not in state:
        state["height"] = 20.0
    if "material_name" not in state:
        state["material_name"] = "Aluminum 6061-T6"
    if "mesh_url" not in state:
        state["mesh_url"] = "/static/uploads/bracket.stl"

    proj_no = existing_proj.get("project_no") if existing_proj else None
    part_name = state.get("name", "Aerospace Mount Bracket")

    # Persist client-side draft key safely in browser
    if curr_id:
        ui.add_body_html(f"<script>try {{ localStorage.setItem('mechnova_active_project', '{curr_id}'); }} catch(e) {{}}</script>")

    with ui.column().classes("w-full gap-5"):
        # Unified Step 1 Header with Back to /worker (Dashboard)
        render_page_header(
            title="Step 1: Part Design & Upload",
            back_to="/worker",
            subtitle="Upload STL, STEP, or reference image for automatic 2.5D feature recognition.",
            current_step=1,
            project_no=proj_no,
            part_name=part_name
        )

        with ui.row().classes("w-full gap-6 flex-wrap lg:flex-nowrap items-start"):
            # Left: Configuration & Inputs
            with ui.card().classes("w-full lg:w-96 p-5 glass-panel rounded-2xl flex flex-col gap-3.5 border border-[var(--border)] shadow-sm"):
                name_input = ui.input("Part Name", value=state.get("name", "Aerospace Mount Bracket")).props("outlined dense w-full")

                mat_select = ui.select(
                    options={m["value"]: m["label"] for m in MATERIALS},
                    value=state.get("material_name", "Aluminum 6061-T6"),
                    label="Material"
                ).props("outlined dense w-full")

                # File upload with theme recoloring
                ui.label("Upload Model or Reference Image").classes("text-xs font-bold text-[var(--text-muted)] mt-1")
                upload_status = ui.label(state.get("filename", "bracket.stl (default sample ready)")).classes("text-[11px] text-[var(--accent-800)] font-semibold")

                async def handle_file_upload(e):
                    try:
                        if hasattr(e, "file"):
                            fname = e.file.name
                            file_bytes = await e.file.read()
                        elif hasattr(e, "content"):
                            fname = getattr(e, "name", "uploaded_file")
                            file_bytes = e.content.read()
                        else:
                            fname = getattr(e, "name", "uploaded_file")
                            file_bytes = b""

                        state["uploaded_file"] = file_bytes
                        state["filename"] = fname
                        upload_status.set_text(f"{fname} ready for analysis")
                        ui.notify(f"Selected {fname}. Click 'Analyze model' to run feature detection.", type="info", position="top")
                    except Exception as ex:
                        ui.notify(f"Upload error: {ex}", type="warning", position="top")

                ui.upload(
                    label="Select STL, STEP, or Image File",
                    on_upload=handle_file_upload,
                    auto_upload=True,
                    max_files=1
                ).props('accept=".stl,.step,.stp,.png,.jpg,.jpeg" flat bordered').classes("w-full text-xs")

                # Dimensions & Live Stock Fit Validation
                ui.label("Raw Material Stock (mm)").classes("text-xs font-bold text-[var(--text-muted)] mt-1")
                with ui.row().classes("gap-2 w-full"):
                    dim_l = ui.number("Length (X)", value=float(state.get("length", 100.0)), min=5.0, max=500.0, step=1.0).props("dense outlined flex-1")
                    dim_w = ui.number("Width (Y)", value=float(state.get("width", 60.0)), min=5.0, max=500.0, step=1.0).props("dense outlined flex-1")
                    dim_h = ui.number("Thickness (Z)", value=float(state.get("height", 20.0)), min=5.0, max=500.0, step=1.0).props("dense outlined flex-1")

                # Live inline stock warning card
                stock_warn_box = ui.column().classes("w-full gap-1 p-2.5 bg-amber-950/40 border border-amber-800 rounded-xl hidden text-xs")
                with stock_warn_box:
                    with ui.row().classes("items-center gap-1.5 text-amber-300 font-bold"):
                        ui.icon("warning", size="16px", color="warning")
                        ui.label("Stock Dimension Warning")
                    stock_warn_msg = ui.label("").classes("text-[11px] text-amber-200")

                def validate_and_sync_stock():
                    L_val = float(dim_l.value or 100.0)
                    W_val = float(dim_w.value or 60.0)
                    H_val = float(dim_h.value or 20.0)
                    state["length"] = L_val
                    state["width"] = W_val
                    state["height"] = H_val
                    state["material_name"] = mat_select.value
                    state["name"] = name_input.value

                    analysis_data = state.get("analysis")
                    if analysis_data and "bbox" in analysis_data:
                        bx, by, bz = analysis_data["bbox"]
                        errs = []
                        if L_val < bx - 0.5:
                            errs.append(f"Length ({L_val:.1f}mm < Part {bx:.1f}mm)")
                        if W_val < by - 0.5:
                            errs.append(f"Width ({W_val:.1f}mm < Part {by:.1f}mm)")
                        if H_val < bz - 0.5:
                            errs.append(f"Thickness ({H_val:.1f}mm < Part {bz:.1f}mm)")
                        if errs:
                            stock_warn_box.classes(remove="hidden")
                            stock_warn_msg.set_text(f"Stock is too small: {', '.join(errs)}. Feature envelope will exceed stock!")
                        else:
                            stock_warn_box.classes(add="hidden")

                    pid_val = state.get("project_id")
                    if pid_val:
                        try:
                            update_project_raw_material(pid_val, mat_select.value, L_val, W_val, H_val, name_input.value)
                        except Exception:
                            pass

                dim_l.on_value_change(validate_and_sync_stock)
                dim_w.on_value_change(validate_and_sync_stock)
                dim_h.on_value_change(validate_and_sync_stock)
                mat_select.on_value_change(validate_and_sync_stock)
                name_input.on_value_change(validate_and_sync_stock)

                if state.get("analysis"):
                    validate_and_sync_stock()

                # 4-stage Progress Line Container with theme styling
                progress_container = ui.column().classes("w-full gap-2 hidden p-3 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)]")
                with progress_container:
                    progress_label = ui.label("Analyzing model...").classes("text-xs font-bold text-[var(--accent-900)] font-mono")
                    progress_bar_box = ui.column().classes("w-full")

                # Analyze action
                async def handle_analyze():
                    analyze_btn.props("loading")
                    progress_container.classes(remove="hidden")

                    try:
                        L = float(dim_l.value or 100.0)
                        W = float(dim_w.value or 60.0)
                        H = float(dim_h.value or 20.0)
                        part_name = name_input.value or "Aerospace Mount Bracket"
                        material = mat_select.value or "Aluminum 6061-T6"

                        state["length"] = L
                        state["width"] = W
                        state["height"] = H
                        state["material_name"] = material
                        state["name"] = part_name

                        uploaded_bytes = state.get("uploaded_file")
                        uploaded_filename = state.get("filename")

                        if not uploaded_bytes or not uploaded_filename:
                            default_path = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "static" / "uploads" / "bracket.stl"
                            if default_path.exists():
                                with open(default_path, "rb") as f:
                                    uploaded_bytes = f.read()
                                uploaded_filename = "bracket.stl"
                                state["uploaded_file"] = uploaded_bytes
                                state["filename"] = uploaded_filename
                            else:
                                ui.notify("Please upload an STL, STEP, or image file first.", type="warning", position="top")
                                return

                        # Create Project in DB if not yet created, or update existing
                        pid = state.get("project_id")
                        if not pid:
                            pid = create_project(part_name, material, L, W, H, file_name=uploaded_filename)
                            state["project_id"] = pid
                        else:
                            update_project_raw_material(pid, material, L, W, H, part_name)
                        set_active_project_id(pid)

                        # Stage 1: Uploading
                        progress_label.set_text("1/4: Uploading model...")
                        progress_bar_box.clear()
                        with progress_bar_box:
                            render_progress_bar(25.0, "Uploading")
                        await asyncio.sleep(0.3)

                        # Stage 2: Checking mesh
                        progress_label.set_text("2/4: Checking mesh & repairing topology...")
                        progress_bar_box.clear()
                        with progress_bar_box:
                            render_progress_bar(50.0, "Checking mesh")
                        await asyncio.sleep(0.3)

                        # Call CAD analysis with resilient fallback
                        from app.services.cad_engine import analyze_cad_model
                        res_json = await analyze_cad_model(
                            uploaded_bytes,
                            uploaded_filename,
                            material=material,
                            length=L,
                            width=W,
                            height=H
                        )

                        # Stage 3: Detecting holes & pockets
                        progress_label.set_text("3/4: Detecting holes, pockets & slots...")
                        progress_bar_box.clear()
                        with progress_bar_box:
                            render_progress_bar(75.0, "Detecting features")
                        await asyncio.sleep(0.3)

                        # Stage 4: Planning tools
                        progress_label.set_text("4/4: Planning operations & recommended tooling...")
                        progress_bar_box.clear()
                        with progress_bar_box:
                            render_progress_bar(100.0, "Complete")
                        await asyncio.sleep(0.3)

                        mesh_url = res_json.get("mesh_url", "")
                        if mesh_url.startswith("/meshes/"):
                            mesh_id = mesh_url.replace("/meshes/", "")
                            mesh_url = f"/api/cad/mesh/{mesh_id}"

                        state["mesh_url"] = mesh_url
                        state["analysis"] = res_json

                        # Update DB with READY status
                        update_project_status(
                            pid, "READY",
                            mesh_url=mesh_url,
                            analysis_dict=res_json
                        )

                        # Auto-select tools in the background
                        try:
                            await auto_select_tools(pid)
                        except Exception:
                            pass

                        # Update dimensions from bbox
                        bbox = res_json.get("bbox", [L, W, H])
                        if len(bbox) >= 3:
                            dim_l.value = round(bbox[0], 1)
                            dim_w.value = round(bbox[1], 1)
                            dim_h.value = round(bbox[2], 1)
                            state["length"] = dim_l.value
                            state["width"] = dim_w.value
                            state["height"] = dim_h.value
                            dim_label.set_text(f"{bbox[0]:.1f} x {bbox[1]:.1f} x {bbox[2]:.1f} mm")

                        # Re-render cards & feature list
                        summary = res_json.get("summary", {})
                        holes_count = summary.get("holes", 0)
                        pockets_count = summary.get("pockets", 0)
                        issues_count = summary.get("issues", 0)
                        blocking_count = summary.get("blocking", 0)
                        pitch_mm = res_json.get("pitch_mm", 0.5)

                        card_holes_val.set_text(str(holes_count))
                        card_pockets_val.set_text(str(pockets_count))
                        card_issues_val.set_text(str(issues_count))
                        if blocking_count > 0:
                            card_issues_badge.props("color=negative")
                            card_issues_badge.set_text(f"{blocking_count} blocking")
                            blocking_ack_row.classes(remove="hidden")
                        else:
                            card_issues_badge.props("color=positive")
                            card_issues_badge.set_text("0 blocking")
                            blocking_ack_row.classes(add="hidden")

                        # Mesh Health Badge
                        issues = res_json.get("issues", [])
                        has_error = any(i.get("severity") == "error" for i in issues)
                        has_repair = any(i.get("code") in ("NORMALS_FIXED", "GAPS_CLOSED") for i in issues)
                        if has_error:
                            health_badge.props("color=negative")
                            health_badge.set_text("Needs attention")
                        elif has_repair:
                            health_badge.props("color=info")
                            health_badge.set_text("Repaired & Watertight")
                        else:
                            health_badge.props("color=positive")
                            health_badge.set_text("Watertight (Healthy)")

                        res_note.set_text(f"Prismatic (2.5D) detection · Grid resolution: {pitch_mm:.2f} mm · Features < {2*pitch_mm:.1f} mm may be omitted")

                        # Update features list
                        features = res_json.get("features", [])
                        feat_summary_col.clear()
                        with feat_summary_col:
                            for f in features:
                                f_kind = f.get("kind", "feature").replace("_", " ").title()
                                f_size = f"⌀{f['diameter']}mm" if f.get("diameter") else f"{f.get('size',[0,0])[0]}x{f.get('size',[0,0])[1]}mm"
                                f_through = "Through" if f.get("through") else "Blind"
                                with ui.row().classes("w-full justify-between items-center text-xs py-1.5 px-3 bg-slate-900/70 rounded-lg border border-slate-700/80 hover:border-sky-500 cursor-pointer"):
                                    with ui.row().classes("items-center gap-2"):
                                        ui.badge(f.get("id", "F"), color="primary" if "hole" in f.get("kind","") else "secondary").props("dense outline")
                                        ui.label(f"{f_kind} ({f_through})").classes("font-semibold text-white")
                                    with ui.row().classes("items-center gap-3"):
                                        ui.label(f"Size: {f_size}").classes("text-[11px] text-slate-300 font-mono")
                                        ui.label(f"Depth: {f.get('depth',0):.1f}mm").classes("text-[11px] text-slate-400 font-mono")
                                        ui.badge(f.get("setup", "+Z"), color="dark").props("dense")

                        # Re-render 3D viewer
                        viewer_col.clear()
                        with viewer_col:
                            render_model_viewer(
                                mesh_url=mesh_url,
                                features_data=res_json,
                                container_height="440px",
                                initial_mode="critical"
                            )

                        proceed_btn.props(remove="disabled")
                        ui.notify("✓ Feature analysis completed successfully!", type="positive", position="top")

                    except Exception as ex:
                        ui.notify(f"Analysis error: {ex}", type="negative", position="top")
                    finally:
                        analyze_btn.props(remove="loading")
                        progress_container.classes(add="hidden")

                analyze_btn = ui.button("Analyze model", icon="biotech", on_click=handle_analyze).classes("btn-primary w-full py-2.5 font-bold rounded-xl mt-2")

            # Right: 3D Model Preview & Feature Analysis
            with ui.card().classes("flex-1 p-5 glass-panel rounded-2xl flex flex-col justify-between min-h-[500px] border border-[var(--border)] shadow-sm"):
                with ui.row().classes("justify-between items-center w-full mb-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.label("3D Preview").classes("font-bold text-sm text-[var(--text)]")
                        health_badge = ui.badge("Ready to analyze", color="grey").props("outline").classes("text-[10px] font-bold")
                    dim_label = ui.label(f"{state.get('length', 100.0):.1f} x {state.get('width', 60.0):.1f} x {state.get('height', 20.0):.1f} mm").classes("text-xs font-mono text-[var(--text-muted)]")

                # Viewer container
                viewer_col = ui.column().classes("w-full")
                with viewer_col:
                    render_model_viewer(
                        mesh_url=state.get("mesh_url", "/static/uploads/bracket.stl"),
                        features_data=state.get("analysis", {}),
                        container_height="440px",
                        initial_mode="critical"
                    )

                # 3 Summary Cards under preview
                with ui.row().classes("w-full gap-3 mt-3 flex-wrap sm:flex-nowrap"):
                    with ui.card().classes("flex-1 p-3 bg-slate-900/60 rounded-xl border border-slate-700/80 flex flex-col gap-1"):
                        ui.label("Holes").classes("text-[11px] font-bold text-slate-400 uppercase tracking-wider")
                        with ui.row().classes("items-baseline justify-between"):
                            holes_cnt = state.get("analysis", {}).get("summary", {}).get("holes", 0)
                            card_holes_val = ui.label(str(holes_cnt)).classes("text-2xl font-black text-rose-400 font-mono")
                            ui.label("Round features").classes("text-[10px] text-slate-400")

                    with ui.card().classes("flex-1 p-3 bg-slate-900/60 rounded-xl border border-slate-700/80 flex flex-col gap-1"):
                        ui.label("Pockets / Slots").classes("text-[11px] font-bold text-slate-400 uppercase tracking-wider")
                        with ui.row().classes("items-baseline justify-between"):
                            pockets_cnt = state.get("analysis", {}).get("summary", {}).get("pockets", 0)
                            card_pockets_val = ui.label(str(pockets_cnt)).classes("text-2xl font-black text-emerald-400 font-mono")
                            ui.label("Prismatic cuts").classes("text-[10px] text-slate-400")

                    with ui.card().classes("flex-1 p-3 bg-slate-900/60 rounded-xl border border-slate-700/80 flex flex-col gap-1"):
                        ui.label("Issues").classes("text-[11px] font-bold text-slate-400 uppercase tracking-wider")
                        with ui.row().classes("items-baseline justify-between"):
                            issues_cnt = state.get("analysis", {}).get("summary", {}).get("issues", 0)
                            card_issues_val = ui.label(str(issues_cnt)).classes("text-2xl font-black text-amber-400 font-mono")
                            card_issues_badge = ui.badge("0 blocking", color="positive").props("dense outline").classes("text-[10px]")

                # Limits and resolution note
                res_note = ui.label("Prismatic (2.5D) detection · features < 2x grid pitch may be omitted · undercuts/threads not detected").classes("text-[11px] text-[var(--text-muted)] italic mt-1 px-1")

                # Detected Features List under preview
                ui.label("Detected Feature Graph").classes("text-xs font-bold text-[var(--text-muted)] mt-3")
                feat_summary_col = ui.column().classes("w-full gap-1.5 max-h-48 overflow-y-auto")
                with feat_summary_col:
                    existing_feats = state.get("analysis", {}).get("features", [])
                    if existing_feats:
                        for f in existing_feats:
                            f_kind = f.get("kind", "feature").replace("_", " ").title()
                            f_size = f"⌀{f['diameter']}mm" if f.get("diameter") else f"{f.get('size',[0,0])[0]}x{f.get('size',[0,0])[1]}mm"
                            f_through = "Through" if f.get("through") else "Blind"
                            with ui.row().classes("w-full justify-between items-center text-xs py-1.5 px-3 bg-slate-900/70 rounded-lg border border-slate-700/80 hover:border-sky-500 cursor-pointer"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.badge(f.get("id", "F"), color="primary" if "hole" in f.get("kind","") else "secondary").props("dense outline")
                                    ui.label(f"{f_kind} ({f_through})").classes("font-semibold text-white")
                                with ui.row().classes("items-center gap-3"):
                                    ui.label(f"Size: {f_size}").classes("text-[11px] text-slate-300 font-mono")
                                    ui.label(f"Depth: {f.get('depth',0):.1f}mm").classes("text-[11px] text-slate-400 font-mono")
                                    ui.badge(f.get("setup", "+Z"), color="dark").props("dense")
                    else:
                        with ui.row().classes("w-full justify-between items-center text-xs py-2 px-3 bg-slate-900/50 rounded-lg border border-slate-800"):
                            ui.label("No features analyzed yet").classes("font-semibold text-slate-300")
                            ui.label("Click 'Analyze model' to run detection").classes("text-[11px] text-slate-500 italic")

                # Blocking acknowledgment row (shown only if blocking > 0)
                with ui.row().classes("w-full items-center gap-2 mt-2 p-2.5 bg-rose-950/40 border border-rose-800 rounded-xl hidden") as blocking_ack_row:
                    ui.icon("warning", color="negative", size="20px")
                    ack_checkbox = ui.checkbox("I reviewed the critical issues and want to continue").classes("text-xs text-rose-200 font-semibold")

                # Bottom Action Bar
                with ui.row().classes("justify-between items-center w-full mt-4 pt-3 border-t border-[var(--border)]"):
                    ui.button("← Back to Dashboard", on_click=lambda: ui.navigate.to("/worker")).props("flat").classes("text-xs font-semibold")

                    def proceed_to_step_2():
                        curr_id = state.get("project_id") or get_active_project_id()
                        if not curr_id:
                            ui.notify("Please analyze the model before proceeding to Step 2.", type="warning", position="top")
                            return
                        
                        analysis = state.get("analysis", {})
                        blocking = analysis.get("summary", {}).get("blocking", 0)
                        if blocking and blocking > 0 and not ack_checkbox.value:
                            ui.notify("Please acknowledge the critical mesh issues before proceeding.", type="warning", position="top")
                            return

                        # Navigate directly to Step 2 Design Details carrying project ID
                        ui.navigate.to(f"/worker/projects/{curr_id}/design-details")

                    is_ready = bool(state.get("analysis"))
                    proceed_btn = ui.button("Proceed to Step 2 →", on_click=proceed_to_step_2).classes("btn-primary text-xs py-2.5 px-6 font-bold rounded-xl")
                    if not is_ready:
                        proceed_btn.props("disabled")
