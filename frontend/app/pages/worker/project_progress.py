from nicegui import ui
from app.api_client import api
from app.session import require_auth
from app.components.layout import app_shell
from app.components.status_chip import render_status_chip
from app.components.model_viewer import render_model_viewer
from app.components.progress_ring import render_progress_ring


def register_project_progress_page():
    @ui.page("/worker/projects/{project_id}")
    async def project_progress_page(project_id: int):
        if not require_auth(allowed_roles=["worker"]):
            return

        app_shell("Job Execution Console")

        try:
            project = await api.get_project(project_id)
        except Exception as e:
            ui.notify(f"Could not load project: {e}", type="negative")
            project = None

        if not project:
            ui.label("Project not found.").classes("p-8 text-center text-red-600 font-bold")
            return

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            with ui.row().classes("justify-between items-center w-full"):
                with ui.column().classes("gap-1"):
                    with ui.row().classes("items-center gap-3"):
                        ui.label(project["name"]).classes("text-2xl font-black text-[var(--accent-900)] tracking-tight")
                        render_status_chip(project.get("status", "draft"))

                    ui.label(f"Material: {project.get('material_id')} | Source: {project.get('source_type', 'step').upper()}").classes("text-xs text-[var(--text-muted)]")

                with ui.row().classes("gap-2 items-center"):
                    ui.button("Back to History", icon="arrow_back", on_click=lambda: ui.navigate.to("/worker/history")).props("flat dense")
                    ui.button("Dashboard", icon="dashboard", on_click=lambda: ui.navigate.to("/worker")).props("flat dense")

            # Main Grid: Left 3D Viewer, Right Progress & G-Code
            with ui.row().classes("w-full gap-6 flex-wrap lg:flex-nowrap"):
                # Left: 3D Model
                with ui.card().classes("flex-1 p-5 glass-panel min-h-[460px]"):
                    with ui.row().classes("justify-between items-center w-full mb-2"):
                        ui.label("3D CAD Solid Preview").classes("font-bold text-sm text-[var(--text)]")
                        with ui.badge(color="primary", outline=True).classes("text-[10px]"):
                            ui.label("WebGL Tessellation")

                    glb_url = f"/api/projects/{project_id}/model"
                    render_model_viewer(glb_url=glb_url, container_height="380px")

                # Right: Dynamic Progress & Deliverables
                right_card = ui.card().classes("w-full lg:w-96 p-5 glass-panel flex flex-col justify-between min-h-[460px]")

            def refresh_right_panel(proj_data: dict):
                right_card.clear()
                with right_card:
                    cur_status = proj_data.get("status", "draft")

                    if cur_status == "completed":
                        # Completion Celebration
                        with ui.card().classes("w-full p-4 bg-green-50 border border-green-200 rounded-xl text-center"):
                            ui.icon("check_circle", size="36px", color="positive").classes("mx-auto")
                            ui.label("Machining Simulation 100% Complete!").classes("font-black text-sm text-green-900 mt-1")
                            ui.label("Part successfully milled in virtual environment. Tool wear life deducted.").classes("text-[11px] text-green-700 mt-1")

                        # G-Code Prototype Viewer & Download
                        with ui.column().classes("w-full gap-2 mt-4"):
                            ui.label("Validated G-Code Program").classes("font-bold text-xs text-[var(--text)] uppercase")
                            
                            # Non-negotiable safety banner
                            with ui.card().classes("p-2 bg-amber-50 border border-amber-300 rounded text-amber-900 font-mono text-[10px]"):
                                ui.label("(*** PROTOTYPE - NOT VERIFIED ON A MACHINE ***)")
                                ui.label("(DO NOT RUN IN PRODUCTION WITHOUT DRY-RUN & CAM VERIFICATION)")

                            async def download_gcode():
                                try:
                                    txt = await api.get_gcode(project_id)
                                    ui.download(txt.encode("utf-8"), filename=f"{proj_data['name']}_setup1.nc")
                                except Exception as ex:
                                    ui.notify(f"Could not load G-code: {ex}", type="negative")

                            ui.button("Download .NC G-Code", icon="download", on_click=download_gcode).classes("btn-accent text-xs w-full py-2")

                    elif cur_status in ("deployed", "working"):
                        # Live Simulation in progress
                        render_progress_ring(
                            progress_percent=proj_data.get("progress_percent", 0.0),
                            current_operation=proj_data.get("current_operation", "Cutting")
                        )

                    elif cur_status == "approved":
                        # Deploy ready
                        with ui.column().classes("w-full items-center justify-center p-6 text-center gap-3"):
                            ui.icon("verified", size="42px", color="positive")
                            ui.label("Job Approved by Shop Admin!").classes("font-bold text-base text-[var(--text)]")
                            ui.label("Spindle slot is reserved and ready for automated execution.").classes("text-xs text-[var(--text-muted)]")
                            
                            async def start_deploy():
                                try:
                                    await api.deploy_project(project_id)
                                    ui.notify("Deployment started!", type="positive")
                                    updated = await api.get_project(project_id)
                                    if updated:
                                        refresh_right_panel(updated)
                                except Exception as ex:
                                    ui.notify(f"Deploy error: {ex}", type="negative")

                            ui.button("Deploy to Machine Now", icon="play_arrow", on_click=start_deploy).classes("btn-accent py-2.5 px-6 animate-pulse")

                    else:
                        with ui.column().classes("w-full items-center justify-center p-6 text-center gap-2"):
                            ui.icon("schedule", size="36px", color="grey")
                            ui.label(f"Status: {cur_status.title()}").classes("font-bold text-sm text-[var(--text)]")
                            ui.label("Awaiting admin review and spindle scheduling.").classes("text-xs text-[var(--text-muted)]")

            refresh_right_panel(project)

            # Polling Timer for live progress while deployed
            poll_timer = None

            async def poll_progress() -> None:
                p = await api.get_project(project_id)
                if p and p.get("status") in ("deployed", "completed"):
                    refresh_right_panel(p)
                    if p.get("status") == "completed" and poll_timer is not None:
                        poll_timer.deactivate()

            poll_timer = ui.timer(1.5, poll_progress)
            if project.get("status") != "deployed":
                poll_timer.deactivate()
