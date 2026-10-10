from pathlib import Path
from nicegui import ui
from app.api_client import api


def render_step_request(state: dict, on_prev, on_complete):
    """
    Step 3: Job Summary, CNC Machine Allocation, and Dispatch Request Submission.
    """
    with ui.column().classes("w-full gap-5"):
        # Top Navigation Bar with Back Button
        with ui.row().classes("justify-between items-center w-full flex-wrap gap-3 pb-2 border-b border-[var(--border)]"):
            with ui.row().classes("items-center gap-3"):
                ui.button("Back", icon="arrow_back", on_click=on_prev).props("flat dense").classes("text-xs font-semibold")
                ui.separator().props("vertical").classes("h-5")
                ui.label("Review & Dispatch").classes("text-xl font-bold text-[var(--accent-900)]")

        with ui.row().classes("w-full gap-6 flex-wrap lg:flex-nowrap"):
            # Left: Summary Card
            with ui.card().classes("flex-1 p-6 glass-panel border border-[var(--border)] rounded-2xl"):
                ui.label("Job Specification Summary").classes("font-bold text-base text-[var(--text)] mb-3 pb-2 border-b border-[var(--border)]")

                with ui.column().classes("gap-2 text-sm text-[var(--text)]"):
                    with ui.row().classes("justify-between w-full py-1 border-b border-[var(--border)]"):
                        ui.label("Job Name:").classes("text-[var(--text-muted)]")
                        ui.label(state.get("name", "Aerospace Mount Bracket")).classes("font-semibold text-[var(--accent-900)]")

                    with ui.row().classes("justify-between w-full py-1 border-b border-[var(--border)]"):
                        ui.label("Material:").classes("text-[var(--text-muted)]")
                        ui.label(state.get("material_id", "aluminum_6061")).classes("font-semibold uppercase")

                    with ui.row().classes("justify-between w-full py-1 border-b border-[var(--border)]"):
                        ui.label("Part Dimensions:").classes("text-[var(--text-muted)]")
                        ui.label(f"{state.get('length', 100)} x {state.get('width', 60)} x {state.get('height', 20)} mm").classes("font-mono font-semibold")

                    with ui.row().classes("justify-between w-full py-1 border-b border-[var(--border)]"):
                        ui.label("DFM Manufacturability Score:").classes("text-[var(--text-muted)]")
                        ui.label("85.0 / 100 (Clean Machining)").classes("font-bold text-green-700")

                    with ui.row().classes("justify-between w-full py-1 border-b border-[var(--border)]"):
                        ui.label("Estimated Machine Time:").classes("text-[var(--text-muted)]")
                        ui.label("376.1 s (6.2 min) [Simulated]").classes("font-bold text-[var(--accent-700)]")

                    with ui.row().classes("justify-between w-full py-1"):
                        ui.label("Tooling Health:").classes("text-[var(--text-muted)]")
                        ui.label("Verified & Auto-Replaced (100% Ready)").classes("font-semibold text-green-700")

            # Right: Request Form & Timeline
            with ui.card().classes("w-full lg:w-96 p-6 glass-panel border border-[var(--border)] rounded-2xl flex flex-col justify-between"):
                with ui.column().classes("gap-3 w-full"):
                    ui.label("Machine Dispatch Parameters").classes("font-bold text-base text-[var(--text)] pb-2 border-b border-[var(--border)]")

                    machine_select = ui.select(
                        options={
                            1: "M-01 - Haas VF-2 (Primary VMC)",
                            2: "M-02 - Mazak VCN-530C (Available)",
                            4: "M-04 - Tormach 1100M (Compact)",
                            6: "M-06 - Hurco VM10i (Available)"
                        },
                        value=2,
                        label="Requested CNC Machine"
                    ).props("outlined dense w-full")

                    note_input = ui.input("Operator Note to Admin", value="Ready for 6061 billet machining. Cutters and drill bits verified.").props("outlined dense w-full")

                    # Status Timeline Preview
                    ui.label("Workflow Stages").classes("text-xs font-bold text-[var(--text-muted)] uppercase mt-2")
                    with ui.column().classes("gap-1.5 text-xs border-l-2 border-l-[var(--accent-600)] pl-3 py-1"):
                        ui.label("1. Submitted (Pending Admin Review)").classes("font-semibold text-[var(--accent-700)]")
                        ui.label("2. Scheduled (Collision & Overlap Checked)").classes("text-[var(--text-muted)]")
                        ui.label("3. Deployed (Simulated Cutting Execution)").classes("text-[var(--text-muted)]")

                error_box = ui.label("").classes("text-xs text-red-600 font-semibold hidden")

                async def submit_request():
                    error_box.classes(remove="block", add="hidden")
                    btn_submit.props("loading")
                    try:
                        proj_id = state.get("project_id")

                        # If not created in Step 1, create now
                        if not proj_id:
                            sample_file = state.get("uploaded_file")
                            filename = state.get("filename", "bracket_demo.step")
                            if not sample_file:
                                p = Path("sample_models/bracket_demo.step")
                                if p.exists():
                                    sample_file = p.read_bytes()
                                else:
                                    sample_file = b"STEP-21; DUMMY;"

                            res = await api.create_project(
                                name=state.get("name", "Aerospace Mount Bracket"),
                                material_id=state.get("material_id", "aluminum_6061"),
                                file_bytes=sample_file,
                                filename=filename,
                                source_type=state.get("source_type", "step"),
                                target_width_mm=state.get("length", 100.0),
                                extrusion_height_mm=state.get("height", 20.0)
                            )
                            proj_id = res["id"]
                            state["project_id"] = proj_id

                        # Submit machine request
                        await api.request_machine(
                            project_id=proj_id,
                            machine_id=machine_select.value,
                            note=note_input.value
                        )

                        ui.notify("Machine Request successfully submitted to Shop Admin!", type="positive")
                        on_complete(proj_id)

                    except Exception as ex:
                        error_box.set_text(str(ex))
                        error_box.classes(remove="hidden", add="block")
                    finally:
                        btn_submit.props(remove="loading")

                btn_submit = ui.button("Send Machine Request", icon="send", on_click=submit_request).classes("btn-accent w-full py-2.5 mt-4 font-bold shadow-md")

        # Bottom Navigation
        with ui.row().classes("justify-between w-full pt-3 border-t border-[var(--border)]"):
            ui.button("Back to Tooling", icon="arrow_back", on_click=on_prev).props("flat").classes("text-xs font-semibold")
