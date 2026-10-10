from nicegui import ui
from app.session import require_auth
from app.components.layout import app_shell
from app.components.page_header import render_page_header
from app.components.progress_bar import render_progress_bar
from app.services.project_service import get_tools, update_tool


def register_equipment_details_page():
    @ui.page("/worker/equipment")
    def equipment_details_page():
        if not require_auth(allowed_roles=["worker"]):
            return

        app_shell("Equipment & Tool Crib")

        with ui.column().classes("w-full p-6 max-w-7xl mx-auto gap-6"):
            # Header with standard Back button
            render_page_header(
                title="Equipment & Spindle Tool Crib",
                back_to="/worker",
                subtitle="Live inventory tracking, spindle magazine allocation, and wear life management."
            )

            all_tools = get_tools()

            # Filter Controls
            with ui.card().classes("w-full p-4 glass-panel rounded-2xl flex flex-wrap items-center justify-between gap-4 border border-[var(--border)] shadow-sm"):
                with ui.row().classes("items-center gap-3 flex-1 flex-wrap"):
                    search_input = ui.input(placeholder="Search by ID or name...").props("dense outlined").classes("w-64 text-xs")
                    type_select = ui.select(
                        options=["All Types", "face_mill", "end_mill", "drill", "spot_drill", "chamfer"],
                        value="All Types",
                        label="Tool Type"
                    ).props("dense outlined").classes("w-40 text-xs")
                    filter_status = ui.select(
                        options=["All Statuses", "AVAILABLE", "RESERVED", "MAINTENANCE"],
                        value="All Statuses",
                        label="Status"
                    ).props("dense outlined").classes("w-36 text-xs")
                    usable_only = ui.checkbox("Usable only", value=False).classes("text-xs font-semibold")

                ui.badge(f"{len(all_tools)} Total Tools in Crib", color="primary").props("dense outline").classes("text-xs font-mono font-bold")

            # Tools Table Container
            table_container = ui.column().classes("w-full gap-3")

            def refresh_tools_list():
                table_container.clear()
                q = (search_input.value or "").lower()
                t_filter = type_select.value
                s_filter = filter_status.value
                u_only = usable_only.value

                tools = get_tools()

                with table_container:
                    # Table Header
                    with ui.card().classes("w-full p-3 bg-slate-900 border border-slate-700 rounded-xl hidden md:flex flex-row justify-between items-center text-xs font-bold text-slate-300 font-mono"):
                        ui.label("ID & Name").classes("w-52")
                        ui.label("Geometry / Coating").classes("w-44")
                        ui.label("Qty & Mag").classes("w-28")
                        ui.label("Wear & Condition").classes("w-44")
                        ui.label("Status & Flags").classes("w-32")
                        ui.label("Actions").classes("w-24 text-right")

                    for tool in tools:
                        if q and (q not in tool["name"].lower() and q not in tool["id"].lower()):
                            continue
                        if t_filter != "All Types" and tool["type"] != t_filter:
                            continue
                        if s_filter != "All Statuses" and tool["status"] != s_filter:
                            continue

                        is_usable = tool.get("qty", 0) > 0 and tool.get("status") == "AVAILABLE" and not tool.get("damaged")
                        if u_only and not is_usable:
                            continue

                        cond = tool.get("condition", "GOOD")
                        cond_color = "positive" if cond == "GOOD" else ("warning" if cond == "FAIR" else "negative")
                        wear_val = float(tool.get("wear_pct", 0.0))
                        tool_id = tool["id"]

                        with ui.card().classes("w-full p-4 glass-panel rounded-xl border border-[var(--border)] flex flex-col md:flex-row justify-between items-start md:items-center gap-3"):
                            # ID & Name
                            with ui.column().classes("w-full md:w-52 gap-0.5"):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.badge(tool_id, color="secondary").props("dense").classes("font-mono font-bold text-xs")
                                    ui.label(tool["type"].replace("_", " ").title()).classes("text-[10px] text-slate-400 uppercase font-mono")
                                ui.label(tool["name"]).classes("font-bold text-xs text-white truncate")

                            # Geometry / Coating
                            with ui.column().classes("w-full md:w-44 gap-0.5 text-xs text-slate-300 font-mono"):
                                ui.label(f"⌀{tool.get('diameter', 0)} mm • {tool.get('flutes', 2)}F • FL {tool.get('flute_length', 0)}mm")
                                ui.label(f"Coating: {tool.get('coating', 'uncoated')}").classes("text-[11px] text-slate-400 font-sans")

                            # Qty & Mag
                            with ui.column().classes("w-full md:w-28 gap-0.5 text-xs font-mono"):
                                ui.label(f"Qty: {tool.get('qty', 0)}").classes("font-bold text-white")
                                ui.label(f"Slot: {tool.get('location', 'T01')}").classes("text-slate-400 text-[11px]")

                            # Wear & Condition
                            with ui.column().classes("w-full md:w-44 gap-1 text-xs"):
                                with ui.row().classes("items-center gap-1.5"):
                                    ui.badge(cond, color=cond_color).props("dense").classes("text-[9px] font-bold")
                                    ui.label(f"{wear_val:.1f}% wear").classes("text-slate-300 font-mono text-[11px]")
                                render_progress_bar(wear_val, height="12px")

                            # Status & Flags
                            with ui.column().classes("w-full md:w-32 gap-1"):
                                status_color = "positive" if tool.get("status") == "AVAILABLE" else ("warning" if tool.get("status") == "RESERVED" else "negative")
                                ui.badge(tool.get("status", "AVAILABLE"), color=status_color).props("dense outline").classes("text-[10px] font-mono font-bold")
                                if tool.get("damaged"):
                                    ui.badge("DAMAGED", color="negative").props("dense").classes("text-[9px] font-bold")

                            # Actions / Quick Edit Modal
                            with ui.row().classes("w-full md:w-24 justify-end"):
                                def make_edit_dialog(t_data=tool):
                                    with ui.dialog() as edit_dialog, ui.card().classes("p-5 max-w-md w-full bg-slate-900 border border-slate-700 rounded-2xl flex flex-col gap-4"):
                                        with ui.row().classes("justify-between items-center w-full"):
                                            ui.label(f"Edit Tool: {t_data['id']}").classes("font-black text-sm text-white font-mono")
                                            ui.badge(t_data['type'], color="primary").props("dense")
                                        
                                        ui.label(t_data['name']).classes("text-xs text-slate-300 font-bold")

                                        w_input = ui.number(label="Wear % (0-100)", value=t_data.get("wear_pct", 0), min=0, max=100).props("dense outlined dark")
                                        q_input = ui.number(label="Quantity", value=t_data.get("qty", 1), min=0).props("dense outlined dark")
                                        d_check = ui.checkbox("Flag Damaged", value=bool(t_data.get("damaged"))).classes("text-xs font-semibold text-rose-400")
                                        s_select = ui.select(
                                            options=["AVAILABLE", "RESERVED", "MAINTENANCE"],
                                            value=t_data.get("status", "AVAILABLE"),
                                            label="Status"
                                        ).props("dense outlined dark").classes("text-xs")

                                        with ui.row().classes("w-full justify-end gap-2 pt-2"):
                                            ui.button("Cancel", on_click=edit_dialog.close).props("flat").classes("text-xs")
                                            
                                            def on_save_tool():
                                                try:
                                                    update_tool(t_data["id"], {
                                                        "wear_pct": float(w_input.value or 0.0),
                                                        "qty": int(q_input.value or 0),
                                                        "damaged": bool(d_check.value),
                                                        "status": str(s_select.value)
                                                    })
                                                    ui.notify(f"Tool {t_data['id']} updated.", type="positive", position="top")
                                                    edit_dialog.close()
                                                    refresh_tools_list()
                                                except Exception as ex:
                                                    ui.notify(f"Error saving tool: {ex}", type="negative", position="top")

                                            ui.button("Save Changes", on_click=on_save_tool).classes("btn-primary text-xs py-1.5 px-4 rounded-xl")
                                    return edit_dialog

                                dlg = make_edit_dialog(tool)
                                ui.button("Edit", icon="edit", on_click=dlg.open).props("flat dense").classes("text-xs text-sky-400")

            search_input.on("update:model-value", refresh_tools_list)
            type_select.on("update:model-value", refresh_tools_list)
            filter_status.on("update:model-value", refresh_tools_list)
            usable_only.on("update:model-value", refresh_tools_list)

            refresh_tools_list()
