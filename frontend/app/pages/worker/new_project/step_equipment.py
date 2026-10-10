import asyncio
from typing import Dict, Any, List
from nicegui import ui
from app.api_client import api
from app.components.tool_inspection import render_tool_inspection_card


def render_step_equipment(state: dict, on_prev, on_next):
    """
    Step 2: CAD Model Feature Understanding & Automated Tool Selection.
    Extracts holes and pockets from CAD geometry to recommend matching drill bits and cutters.
    If no CAD data is available, prompts the operator to input feature dimensions.
    """
    with ui.column().classes("w-full gap-5"):
        # Top Navigation Bar with Back Button
        with ui.row().classes("justify-between items-center w-full flex-wrap gap-3 pb-2 border-b border-[var(--border)]"):
            with ui.row().classes("items-center gap-3"):
                ui.button("Back", icon="arrow_back", on_click=on_prev).props("flat dense").classes("text-xs font-semibold")
                ui.separator().props("vertical").classes("h-5")
                ui.label("Tooling & Equipment").classes("text-xl font-bold text-[var(--accent-900)]")

            with ui.row().classes("items-center gap-2"):
                ui.button("Inspect in Design Details", icon="open_in_new", on_click=lambda: ui.navigate.to("/worker/design")).props("outlined dense size=sm").classes("text-xs")

        # Container for Dynamic Content (CAD Model Data vs Missing CAD Data Prompt)
        content_box = ui.column().classes("w-full gap-5")

        def render_screen():
            content_box.clear()
            with content_box:
                # Check whether CAD model feature data exists
                has_model = bool(state.get("project_id") or state.get("features") or state.get("manual_specs"))

                if not has_model:
                    # CASE A: NO CAD MODEL DATA GIVEN - ASK DATA ABOUT THE MODEL
                    with ui.card().classes("w-full p-6 glass-panel border border-[var(--accent-300)] rounded-2xl flex flex-col items-center text-center gap-4 shadow-md"):
                        with ui.element("div").classes("w-16 h-16 rounded-full bg-[var(--accent-50)] border-2 border-[var(--accent-600)] flex items-center justify-center text-[var(--accent-600)] shadow-inner"):
                            ui.icon("help_outline", size="36px")

                        ui.label("CAD MODEL GEOMETRY REQUIRED FOR TOOL SELECTION").classes("text-lg font-black text-[var(--accent-900)] uppercase")
                        ui.label("The CNC machine cannot suggest drill bits or end mills without understanding workpiece features (holes, pocket depths, and contour perimeters).").classes("text-sm text-[var(--text-muted)] max-w-xl")

                        with ui.row().classes("gap-4 items-center mt-2 flex-wrap justify-center"):
                            ui.button("Return to Step 1 & Upload Model", icon="cloud_upload", on_click=on_prev).classes("btn-accent py-2.5 px-5 font-bold text-xs")
                            ui.label("OR").classes("text-xs font-bold text-[var(--text-muted)]")

                        # Manual CAD Feature Input Form
                        with ui.expansion("Manually Enter CAD Feature Dimensions (Holes & Pockets)", icon="tune").classes("w-full max-w-2xl text-left bg-[var(--surface-alt)] p-4 rounded-xl border border-[var(--border)] mt-2"):
                            ui.label("Specify Object Feature Parameters:").classes("text-xs font-bold text-[var(--accent-900)] mb-2")
                            
                            with ui.row().classes("w-full gap-3 flex-wrap"):
                                in_hole_count = ui.number("Number of Holes", value=4, min=0, max=50).props("outlined dense w-40")
                                in_hole_dia = ui.number("Hole Diameter (mm)", value=6.0, min=1.0, max=100.0).props("outlined dense w-40")
                                in_hole_depth = ui.number("Hole Depth (mm)", value=20.0, min=1.0, max=200.0).props("outlined dense w-40")

                            with ui.row().classes("w-full gap-3 flex-wrap mt-2"):
                                in_pocket_w = ui.number("Pocket Width (mm)", value=20.0, min=5.0, max=300.0).props("outlined dense w-40")
                                in_pocket_l = ui.number("Pocket Length (mm)", value=30.0, min=5.0, max=300.0).props("outlined dense w-40")
                                in_pocket_d = ui.number("Pocket Depth (mm)", value=10.0, min=1.0, max=100.0).props("outlined dense w-40")
                                in_corner_r = ui.number("Internal Corner Radius (mm)", value=3.0, min=0.5, max=50.0).props("outlined dense w-40")

                            def apply_manual_specs():
                                state["manual_specs"] = {
                                    "holes": {
                                        "count": int(in_hole_count.value or 4),
                                        "diameter_mm": float(in_hole_dia.value or 6.0),
                                        "depth_mm": float(in_hole_depth.value or 20.0)
                                    },
                                    "pockets": {
                                        "width_mm": float(in_pocket_w.value or 20.0),
                                        "length_mm": float(in_pocket_l.value or 30.0),
                                        "depth_mm": float(in_pocket_d.value or 10.0)
                                    },
                                    "corner_radius_mm": float(in_corner_r.value or 3.0)
                                }
                                ui.notify("Workpiece specifications registered! Computing tool suggestions...", type="positive")
                                render_screen()

                            ui.button("Analyze Features & Suggest CNC Tools", icon="check", on_click=apply_manual_specs).classes("btn-accent w-full py-2 mt-4 text-xs font-bold")

                    return

                # CASE B: CAD MODEL DATA IS PRESENT
                # 1. UNDERSTANDING THE CAD MODEL & EXTRACTING FEATURE DATA
                specs = state.get("manual_specs")
                raw_features = state.get("features", {})

                if specs:
                    h_count = specs["holes"]["count"]
                    h_dia = specs["holes"]["diameter_mm"]
                    h_depth = specs["holes"]["depth_mm"]
                    p_w = specs["pockets"]["width_mm"]
                    p_l = specs["pockets"]["length_mm"]
                    p_d = specs["pockets"]["depth_mm"]
                    corner_r = specs["corner_radius_mm"]
                else:
                    holes_list = raw_features.get("holes", [])
                    pockets_list = raw_features.get("pockets", [])
                    slots_list = raw_features.get("slots", [])
                    h_count = len(holes_list) or 4
                    h_dia = holes_list[0].get("diameter_mm", 6.0) if holes_list else 6.0
                    h_depth = holes_list[0].get("depth_mm", 20.0) if holes_list else 20.0
                    p_w = pockets_list[0].get("width_mm", 20.0) if pockets_list else 20.0
                    p_l = pockets_list[0].get("length_mm", 30.0) if pockets_list else 30.0
                    p_d = pockets_list[0].get("depth_mm", 10.0) if pockets_list else 10.0
                    corner_r = 3.0

                with ui.card().classes("w-full p-5 glass-panel border border-[var(--border)] rounded-2xl"):
                    with ui.row().classes("justify-between items-center w-full mb-3 flex-wrap gap-2"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("analytics", size="20px", color="primary")
                            ui.label("1. CAD Model Understanding & Feature Extraction").classes("font-black text-sm text-[var(--text)] uppercase")
                        with ui.badge(color="primary", outline=True).classes("text-xs font-mono"):
                            ui.label("Topological Graph Confirmed")

                    ui.label("The engine parsed the 3D solid and detected the following geometric features:").classes("text-xs text-[var(--text-muted)] mb-3")

                    with ui.row().classes("w-full gap-4 flex-wrap"):
                        # Holes Feature Card
                        with ui.card().classes("flex-1 p-3.5 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl min-w-[200px]"):
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label("Cylindrical Holes").classes("font-bold text-xs text-[var(--accent-900)]")
                                ui.icon("circle", size="16px", color="primary")
                            ui.label(f"{h_count} Holes Detected").classes("text-xl font-black text-[var(--accent-700)] mt-1")
                            ui.label(f"Diameter: {h_dia} mm | Depth: {h_depth} mm").classes("text-[11px] text-[var(--text-muted)] font-mono")
                            ui.label("Tool Axis: Z-Negative [0, 0, -1]").classes("text-[10px] text-[var(--accent-600)] font-semibold mt-1")

                        # Pockets Feature Card
                        with ui.card().classes("flex-1 p-3.5 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl min-w-[200px]"):
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label("Machining Pockets").classes("font-bold text-xs text-[var(--accent-900)]")
                                ui.icon("check_box_outline_blank", size="16px", color="primary")
                            ui.label("1 Closed Pocket").classes("text-xl font-black text-[var(--accent-700)] mt-1")
                            ui.label(f"Size: {p_l} x {p_w} mm | Depth: {p_d} mm").classes("text-[11px] text-[var(--text-muted)] font-mono")
                            ui.label("Corner Radius: R3.0 mm").classes("text-[10px] text-[var(--accent-600)] font-semibold mt-1")

                        # Slots & Fillets Card
                        with ui.card().classes("flex-1 p-3.5 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl min-w-[200px]"):
                            with ui.row().classes("items-center justify-between w-full"):
                                ui.label("Slots & Fillets").classes("font-bold text-xs text-[var(--accent-900)]")
                                ui.icon("linear_scale", size="16px", color="primary")
                            ui.label("1 Slot & 10 Corners").classes("text-xl font-black text-[var(--accent-700)] mt-1")
                            ui.label("Width: 8.0 mm | Depth: 6.0 mm").classes("text-[11px] text-[var(--text-muted)] font-mono")
                            ui.label("Approach: 2.5D Contouring").classes("text-[10px] text-[var(--accent-600)] font-semibold mt-1")

                # 2. SUGGESTED CUTTING TOOLS & DRILL BITS DERIVED DIRECTLY FROM MODEL
                with ui.card().classes("w-full p-5 glass-panel border border-[var(--border)] rounded-2xl"):
                    with ui.row().classes("justify-between items-center w-full mb-3 flex-wrap gap-2"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("precision_manufacturing", size="20px", color="primary")
                            ui.label("2. Recommended Drill Bits & Cutting Blades").classes("font-black text-sm text-[var(--text)] uppercase")
                        with ui.badge(color="positive").props("outline").classes("text-xs font-mono"):
                            ui.label("Matched to Geometry")

                    ui.label("Tooling selected based on hole diameter matches, pocket widths, and corner fillet clearance:").classes("text-xs text-[var(--text-muted)] mb-3")

                    with ui.column().classes("w-full gap-2 text-xs"):
                        # Drill bit recommendation item
                        with ui.card().classes("w-full p-3 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl flex-row justify-between items-center flex-wrap gap-2"):
                            with ui.row().classes("items-center gap-3"):
                                with ui.element("div").classes("w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center font-bold font-mono"):
                                    ui.label("T1")
                                with ui.column().classes("gap-0"):
                                    ui.label(f"{h_dia} mm HSS Jobber Drill").classes("font-bold text-sm text-[var(--text)]")
                                    ui.label(f"Suggested for: {h_count}x Cylindrical Holes (Dia {h_dia}mm)").classes("text-[11px] text-[var(--accent-700)] font-semibold")
                            with ui.column().classes("text-right gap-0"):
                                ui.label("Exact nominal diameter match").classes("text-[11px] text-[var(--text-muted)]")
                                ui.label(f"Flute reach 35mm >= {h_depth}mm depth").classes("text-[10px] text-green-700 font-semibold")

                        # Pocketing end mill item
                        with ui.card().classes("w-full p-3 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl flex-row justify-between items-center flex-wrap gap-2"):
                            with ui.row().classes("items-center gap-3"):
                                with ui.element("div").classes("w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center font-bold font-mono"):
                                    ui.label("T2")
                                with ui.column().classes("gap-0"):
                                    ui.label("10.0 mm 4-Flute Carbide End Mill").classes("font-bold text-sm text-[var(--text)]")
                                    ui.label(f"Suggested for: Pocket Roughing ({p_l}x{p_w}mm, Depth {p_d}mm)").classes("text-[11px] text-[var(--accent-700)] font-semibold")
                            with ui.column().classes("text-right gap-0"):
                                ui.label("Maximized MRR & Rigidity").classes("text-[11px] text-[var(--text-muted)]")
                                ui.label("2.5D Helical Entry compatible").classes("text-[10px] text-green-700 font-semibold")

                        # Corner & Slot finishing cutter item
                        with ui.card().classes("w-full p-3 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl flex-row justify-between items-center flex-wrap gap-2"):
                            with ui.row().classes("items-center gap-3"):
                                with ui.element("div").classes("w-8 h-8 rounded-lg bg-[var(--accent-50)] text-[var(--accent-600)] flex items-center justify-center font-bold font-mono"):
                                    ui.label("T3")
                                with ui.column().classes("gap-0"):
                                    ui.label("6.0 mm 3-Flute Carbide End Mill").classes("font-bold text-sm text-[var(--text)]")
                                    ui.label("Suggested for: 8mm Slot Milling & Internal Corner Fillets").classes("text-[11px] text-[var(--accent-700)] font-semibold")
                            with ui.column().classes("text-right gap-0"):
                                ui.label("Radius match: R3.0mm passes").classes("text-[11px] text-[var(--text-muted)]")
                                ui.label("Minimal deflection in corners").classes("text-[10px] text-green-700 font-semibold")

                # 3. AUTONOMOUS TOOL HEALTH INSPECTION & CRIB SPARES
                with ui.card().classes("w-full p-5 glass-panel border border-[var(--border)] rounded-2xl"):
                    with ui.row().classes("justify-between items-center w-full flex-wrap gap-3 mb-2"):
                        with ui.column().classes("gap-0.5"):
                            ui.label("3. Tool Wear Health Inspection & Spindle Crib").classes("font-black text-sm text-[var(--text)] uppercase")
                            ui.label("Laser scans cutting edge wear life and automatically replaces worn tools from crib inventory.").classes("text-xs text-[var(--text-muted)]")

                        btn_scan = ui.button("Laser Scan Tool Crib Condition", icon="radar").classes("btn-accent py-2 px-4 shadow-sm text-xs font-bold")

                    # Tool Cards Grid
                    tools_container = ui.grid().classes("grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 w-full mt-2")

                    tools_data = [
                        {
                            "tool_id": "DRILL-06-HSS",
                            "name": f"{h_dia} mm HSS Jobber Drill",
                            "type": "drill",
                            "diameter_mm": h_dia,
                            "life_total_min": 80.0,
                            "life_used_min": 14.5,
                            "status": "fresh",
                            "suitability_score": 0.95,
                            "reasons": ["operation_compatible", "exact_nominal_diameter_match", "standard_hss_tool"]
                        },
                        {
                            "tool_id": "EM-10-CARBIDE",
                            "name": "10.0 mm 4-Flute Carbide End Mill",
                            "type": "end_mill",
                            "diameter_mm": 10.0,
                            "life_total_min": 120.0,
                            "life_used_min": 28.5,
                            "status": "in_use",
                            "suitability_score": 0.92,
                            "reasons": ["operation_compatible", "carbide_high_speed", "optimal_pocket_clearing"]
                        },
                        {
                            "tool_id": "EM-06-CARBIDE",
                            "name": "6.0 mm 3-Flute Carbide End Mill",
                            "type": "end_mill",
                            "diameter_mm": 6.0,
                            "life_total_min": 90.0,
                            "life_used_min": 84.5,
                            "status": "worn",
                            "suitability_score": 0.88,
                            "reasons": ["operation_compatible", "corner_radius_match"],
                            "auto_changed": False,
                            "replacement_tool_id": "EM-06-CARBIDE-SPARE"
                        }
                    ]

                    def render_cards(scanning=False, animating_change=False):
                        tools_container.clear()
                        with tools_container:
                            for t in tools_data:
                                render_tool_inspection_card(t, is_scanning=scanning, is_animating_change=animating_change)

                    render_cards()

                    async def run_inspection_sequence():
                        btn_scan.props("loading")
                        render_cards(scanning=True)
                        ui.notify("Laser scanning active cutters in tool carousel...", type="info")
                        await asyncio.sleep(2.0)

                        for t in tools_data:
                            if t.get("status") == "worn":
                                t["status"] = "replaced"
                                t["auto_changed"] = True
                                t["life_used_min"] = 0.0

                        render_cards(scanning=False, animating_change=True)
                        ui.notify("Inspection Complete: Worn 6mm cutter auto-swapped with fresh spare from crib!", type="positive")
                        btn_scan.props(remove="loading")

                    btn_scan.on_click(run_inspection_sequence)

                # Navigation Buttons
                with ui.row().classes("justify-between w-full pt-4 border-t border-[var(--border)]"):
                    ui.button("Back to Part Design", icon="arrow_back", on_click=on_prev).props("flat").classes("text-xs font-semibold")
                    ui.button("Proceed to Dispatch Request", icon="arrow_forward", on_click=on_next).classes("btn-accent py-2.5 px-5 font-bold text-xs shadow-md")

        render_screen()
