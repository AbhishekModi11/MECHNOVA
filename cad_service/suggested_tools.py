"""
MECHNOVA Suggested Tools & Machining Engine
Generates standard CNC milling tool suggestions, cutting data (RPM, Feed),
cycle time estimates, DFM warnings, and G-code preview from raw material
and detected topological features.
"""

import math
from typing import List, Dict, Any, Optional

# Standard Metric Tool Series (ISO)
STANDARD_FACE_MILLS = [
    {"diameter": 50, "inserts": 4, "type": "face_mill", "name": "Face Mill 50 mm (4 inserts)"},
    {"diameter": 63, "inserts": 5, "type": "face_mill", "name": "Face Mill 63 mm (5 inserts)"},
    {"diameter": 80, "inserts": 6, "type": "face_mill", "name": "Face Mill 80 mm (6 inserts)"},
]

STANDARD_END_MILL_DIAMETERS = [3.0, 4.0, 6.0, 8.0, 10.0, 12.0, 16.0, 20.0]

# Material Cutting Parameters Library
MATERIAL_CATALOG = {
    "Aluminum 6061-T6": {
        "vc_milling": 280.0,    # m/min
        "vc_drilling": 90.0,    # m/min
        "fz_face": 0.15,        # mm/tooth
        "fz_endmill": 0.07,     # mm/tooth
        "fz_rough": 0.07,       # mm/tooth
        "fz_finish": 0.04,      # mm/tooth
        "f_rev_drill": 0.12,    # mm/rev
        "flutes_endmill": 3,
        "tool_material": "Solid Carbide",
        "coating": "Uncoated / ZrN",
        "coolant": "Flood Coolant (High Flow)",
        "density": 2.70         # g/cm3
    },
    "Mild Steel 1018": {
        "vc_milling": 130.0,
        "vc_drilling": 35.0,
        "fz_face": 0.12,
        "fz_endmill": 0.05,
        "fz_rough": 0.05,
        "fz_finish": 0.03,
        "f_rev_drill": 0.10,
        "flutes_endmill": 4,
        "tool_material": "Micrograin Carbide",
        "coating": "TiAlN Coated",
        "coolant": "Flood Coolant / Soluble Oil",
        "density": 7.87
    },
    "Stainless 304": {
        "vc_milling": 85.0,
        "vc_drilling": 25.0,
        "fz_face": 0.10,
        "fz_endmill": 0.04,
        "fz_rough": 0.04,
        "fz_finish": 0.025,
        "f_rev_drill": 0.08,
        "flutes_endmill": 4,
        "tool_material": "Solid Carbide",
        "coating": "AlTiN Nano Coated",
        "coolant": "High Pressure Flood",
        "density": 8.00
    },
    "Titanium Ti-6Al-4V": {
        "vc_milling": 55.0,
        "vc_drilling": 20.0,
        "fz_face": 0.08,
        "fz_endmill": 0.035,
        "fz_rough": 0.035,
        "fz_finish": 0.02,
        "f_rev_drill": 0.06,
        "flutes_endmill": 5,
        "tool_material": "Ultra-Fine Carbide",
        "coating": "AlTiN / DLC",
        "coolant": "High Pressure Through-Spindle",
        "density": 4.43
    }
}

SPINDLE_MAX_RPM = 12000
SPINDLE_MIN_RPM = 400


def compute_cutting_data(diameter_mm: float, vc_m_min: float, flutes: int, fz_mm: float) -> tuple[int, int]:
    """Computes Spindle RPM = (Vc * 1000) / (pi * D) and Feed = RPM * flutes * fz."""
    if diameter_mm <= 0:
        return 1200, 150
    raw_rpm = (vc_m_min * 1000.0) / (math.pi * diameter_mm)
    rpm = max(SPINDLE_MIN_RPM, min(SPINDLE_MAX_RPM, int(round(raw_rpm))))
    feed = max(30, int(round(rpm * max(1, flutes) * fz_mm)))
    return rpm, feed


def choose_face_mill(stock_width_mm: float) -> dict:
    """Selects face mill approx 1.25-1.5x stock width from {50, 63, 80 mm}."""
    target_d = stock_width_mm * 1.3
    if target_d <= 55:
        return STANDARD_FACE_MILLS[0]
    elif target_d <= 70:
        return STANDARD_FACE_MILLS[1]
    else:
        return STANDARD_FACE_MILLS[2]


def find_roughing_endmill(pocket_min_width: float, corner_radius: Optional[float] = None) -> float:
    """Finds roughing end mill diameter <= 0.7x width and <= 2x corner radius."""
    max_d = pocket_min_width * 0.7
    if corner_radius and corner_radius > 0:
        max_d = min(max_d, corner_radius * 2.0)
    candidates = [d for d in STANDARD_END_MILL_DIAMETERS if d <= max_d]
    return candidates[-1] if candidates else STANDARD_END_MILL_DIAMETERS[0]


def find_finishing_endmill(roughing_diameter: float) -> float:
    """Finds finishing end mill 1-2 mm smaller or equal to roughing."""
    candidates = [d for d in STANDARD_END_MILL_DIAMETERS if d <= roughing_diameter]
    if len(candidates) >= 2 and roughing_diameter >= 8:
        return candidates[-2]
    return roughing_diameter


def suggest_tools_for_project(
    material_name: str,
    stock_dims: list[float],   # [length, width, height/thickness]
    features: list[dict],
    part_bbox: Optional[list[float]] = None
) -> dict:
    """
    Main tool suggestion engine adhering to standard CNC machining practice:
    1. Face mill for top face cleanup
    2. Spot drill (90 deg) for every hole (deduped)
    3. Twist / carbide drill for each hole size (+ pilot drill for holes > 12 mm)
    4. Roughing & finishing end mills for pockets and slots
    5. Profile & chamfer mill for outer contours and deburring
    6. Material-appropriate RPM, Feed, cutting parameters, and DFM checks
    """
    mat_info = MATERIAL_CATALOG.get(material_name, MATERIAL_CATALOG["Aluminum 6061-T6"])
    length = float(stock_dims[0]) if len(stock_dims) > 0 else 100.0
    width = float(stock_dims[1]) if len(stock_dims) > 1 else 60.0
    thickness = float(stock_dims[2]) if len(stock_dims) > 2 else 20.0
    stock_w = min(length, width)

    tools_dict = {}  # key -> tool entry
    dfm_warnings = []
    
    # Check 1: Raw material size validation against part
    if part_bbox and len(part_bbox) >= 3:
        bx, by, bz = float(part_bbox[0]), float(part_bbox[1]), float(part_bbox[2])
        if length < bx - 0.5:
            dfm_warnings.append({
                "severity": "warning",
                "code": "STOCK_UNDERSIZE_X",
                "message": f"Stock length ({length:.1f} mm) is smaller than part length ({bx:.1f} mm)."
            })
        if width < by - 0.5:
            dfm_warnings.append({
                "severity": "warning",
                "code": "STOCK_UNDERSIZE_Y",
                "message": f"Stock width ({width:.1f} mm) is smaller than part width ({by:.1f} mm)."
            })
        if thickness < bz - 0.5:
            dfm_warnings.append({
                "severity": "warning",
                "code": "STOCK_UNDERSIZE_Z",
                "message": f"Stock thickness ({thickness:.1f} mm) is smaller than part height ({bz:.1f} mm)."
            })

    # Tool 1: Face Mill
    fm_template = choose_face_mill(stock_w)
    fm_dia = fm_template["diameter"]
    fm_flutes = fm_template["inserts"]
    fm_rpm, fm_feed = compute_cutting_data(fm_dia, mat_info["vc_milling"], fm_flutes, mat_info["fz_face"])
    tools_dict[("face_mill", fm_dia)] = {
        "type": "face_mill",
        "diameter": fm_dia,
        "flutes": fm_flutes,
        "name": fm_template["name"],
        "material": "Indexable Carbide",
        "coating": "TiN Inserts",
        "purpose": "Face top cleanup of raw stock billet",
        "features": ["Top Face"],
        "suggested_rpm": fm_rpm,
        "suggested_feed": fm_feed,
        "flute_length": 15.0,
        "est_time_sec": 35
    }

    # Analyze Holes
    holes = [f for f in features if f.get("kind") in ("hole", "blind_hole") and f.get("enabled", True)]
    if holes:
        # Tool: Spot Drill (90 deg)
        sd_rpm, sd_feed = compute_cutting_data(10.0, mat_info["vc_drilling"], 2, mat_info["f_rev_drill"] * 0.5)
        tools_dict[("spot_drill", 10.0)] = {
            "type": "spot_drill",
            "diameter": 10.0,
            "flutes": 2,
            "name": "Spot Drill 90 deg dia 10 mm",
            "material": "Solid Carbide",
            "coating": mat_info["coating"],
            "purpose": f"Centering & spotting for {len(holes)} hole(s)",
            "features": [h.get("id", "H") for h in holes],
            "suggested_rpm": sd_rpm,
            "suggested_feed": sd_feed,
            "flute_length": 25.0,
            "est_time_sec": 12 * len(holes)
        }

        # Drills by diameter
        pilot_needed = False
        pilot_holes = []
        for h in holes:
            hd = float(h.get("diameter", 6.0) or 6.0)
            depth = float(h.get("depth", 10.0) or 10.0)
            hid = h.get("id", "H")

            # Check peck drilling rule (depth > 5xD)
            if depth > 5.0 * hd:
                dfm_warnings.append({
                    "severity": "info",
                    "code": "PECK_DRILL",
                    "message": f"Hole {hid} depth ({depth:.1f} mm) > 5x diameter (dia {hd:.1f} mm): Peck drilling cycle (G83) recommended."
                })

            # Pilot drill needed if hole > 12 mm
            if hd > 12.0:
                pilot_needed = True
                pilot_holes.append(hid)

            # Final drill
            key = ("drill", round(hd, 1))
            d_rpm, d_feed = compute_cutting_data(hd, mat_info["vc_drilling"], 2, mat_info["f_rev_drill"])
            if key not in tools_dict:
                tools_dict[key] = {
                    "type": "drill",
                    "diameter": round(hd, 1),
                    "flutes": 2,
                    "name": f"Carbide Twist Drill dia {hd:.1f} mm",
                    "material": mat_info["tool_material"],
                    "coating": mat_info["coating"],
                    "purpose": f"Final drilling of hole {hid}",
                    "features": [hid],
                    "suggested_rpm": d_rpm,
                    "suggested_feed": d_feed,
                    "flute_length": max(30.0, round(depth * 1.3, 1)),
                    "est_time_sec": int(round(15 + depth * 0.8))
                }
            else:
                tools_dict[key]["features"].append(hid)
                tools_dict[key]["purpose"] = f"Final drilling for {', '.join(tools_dict[key]['features'])}"

        if pilot_needed:
            p_rpm, p_feed = compute_cutting_data(10.0, mat_info["vc_drilling"], 2, mat_info["f_rev_drill"])
            tools_dict[("pilot_drill", 10.0)] = {
                "type": "drill",
                "diameter": 10.0,
                "flutes": 2,
                "name": "Carbide Pilot Drill dia 10 mm",
                "material": mat_info["tool_material"],
                "coating": mat_info["coating"],
                "purpose": f"Pilot drilling before final pass for {', '.join(pilot_holes)}",
                "features": pilot_holes,
                "suggested_rpm": p_rpm,
                "suggested_feed": p_feed,
                "flute_length": 45.0,
                "est_time_sec": 18 * len(pilot_holes)
            }

    # Analyze Pockets & Slots
    pockets_and_slots = [f for f in features if f.get("kind") in ("pocket", "slot", "window") and f.get("enabled", True)]
    for f in pockets_and_slots:
        fid = f.get("id", "P")
        kind = f.get("kind", "pocket")
        size = f.get("size", [30.0, 30.0])
        pw = float(min(size[0], size[1]))
        depth = float(f.get("depth", 10.0))
        cr = float(f.get("corner_radius", pw * 0.2) or (pw * 0.2))

        # DFM Check: slot or pocket narrower than smallest standard tool
        if pw < 3.0:
            dfm_warnings.append({
                "severity": "warning",
                "code": "FEATURE_TOO_NARROW",
                "message": f"{kind.title()} {fid} width ({pw:.1f} mm) is smaller than the 3 mm minimum standard tool diameter."
            })

        # DFM Check: corner radius vs tool radius
        rough_d = find_roughing_endmill(pw, cr)
        finish_d = find_finishing_endmill(rough_d)

        if cr < (rough_d / 2.0) - 0.1:
            dfm_warnings.append({
                "severity": "info",
                "code": "CORNER_RADIUS_TIGHT",
                "message": f"{kind.title()} {fid} inner corner radius ({cr:.1f} mm) is tighter than roughing tool radius (dia {rough_d} mm tool). Multi-pass finishing required."
            })

        # Add roughing tool
        r_flutes = mat_info["flutes_endmill"]
        r_rpm, r_feed = compute_cutting_data(rough_d, mat_info["vc_milling"], r_flutes, mat_info["fz_endmill"])
        r_key = ("end_mill_rough", rough_d)
        if r_key not in tools_dict:
            tools_dict[r_key] = {
                "type": "end_mill",
                "diameter": rough_d,
                "flutes": r_flutes,
                "name": f"Carbide Roughing End Mill dia {rough_d:.1f} mm",
                "material": mat_info["tool_material"],
                "coating": mat_info["coating"],
                "purpose": f"Rough milling of {kind} {fid}",
                "features": [fid],
                "suggested_rpm": r_rpm,
                "suggested_feed": r_feed,
                "flute_length": max(20.0, round(depth * 1.25, 1)),
                "est_time_sec": int(round(30 + depth * 2.5))
            }
        else:
            tools_dict[r_key]["features"].append(fid)
            tools_dict[r_key]["purpose"] = f"Rough milling for {', '.join(tools_dict[r_key]['features'])}"

        # Add finishing tool if distinct
        if finish_d != rough_d:
            f_rpm, f_feed = compute_cutting_data(finish_d, mat_info["vc_milling"] * 1.1, r_flutes, mat_info["fz_finish"])
            f_key = ("end_mill_finish", finish_d)
            if f_key not in tools_dict:
                tools_dict[f_key] = {
                    "type": "end_mill",
                    "diameter": finish_d,
                    "flutes": r_flutes,
                    "name": f"Carbide Finishing End Mill dia {finish_d:.1f} mm",
                    "material": mat_info["tool_material"],
                    "coating": mat_info["coating"],
                    "purpose": f"Floor & wall finishing for {kind} {fid}",
                    "features": [fid],
                    "suggested_rpm": f_rpm,
                    "suggested_feed": f_feed,
                    "flute_length": max(18.0, round(depth * 1.25, 1)),
                    "est_time_sec": int(round(20 + depth * 1.5))
                }
            else:
                tools_dict[f_key]["features"].append(fid)

    # Tool: Outer Profile End Mill
    prof_d = 10.0
    prof_rpm, prof_feed = compute_cutting_data(prof_d, mat_info["vc_milling"], mat_info["flutes_endmill"], mat_info["fz_endmill"])
    tools_dict[("end_mill_profile", prof_d)] = {
        "type": "end_mill",
        "diameter": prof_d,
        "flutes": mat_info["flutes_endmill"],
        "name": f"Carbide Profile End Mill dia {prof_d:.1f} mm",
        "material": mat_info["tool_material"],
        "coating": mat_info["coating"],
        "purpose": "Perimeter contour & outer boundary profiling",
        "features": ["Outer Boundary"],
        "suggested_rpm": prof_rpm,
        "suggested_feed": prof_feed,
        "flute_length": max(25.0, round(thickness * 1.2, 1)),
        "est_time_sec": 45
    }

    # Tool: Chamfer & Deburring Mill
    ch_d = 12.0
    ch_rpm, ch_feed = compute_cutting_data(ch_d, mat_info["vc_milling"], 3, mat_info["fz_finish"])
    tools_dict[("chamfer", ch_d)] = {
        "type": "chamfer",
        "diameter": ch_d,
        "flutes": 3,
        "name": "Chamfer & Deburr Mill 90 deg dia 12 mm",
        "material": "Solid Carbide",
        "coating": mat_info["coating"],
        "purpose": "Edge deburring & 0.5 mm chamfering on top edges and holes",
        "features": ["All Top Edges"],
        "suggested_rpm": ch_rpm,
        "suggested_feed": ch_feed,
        "flute_length": 15.0,
        "est_time_sec": 25
    }

    # Dedupe & Index consecutively T1, T2, ...
    final_tools = []
    total_machining_sec = 0
    idx = 1
    for tool_data in tools_dict.values():
        tool_data["tool_no"] = f"T{idx:02d}"
        tool_data["id"] = f"T{idx:02d}"
        total_machining_sec += tool_data.get("est_time_sec", 30)
        final_tools.append(tool_data)
        idx += 1

    total_machining_min = round(total_machining_sec / 60.0, 1)

    return {
        "material": material_name,
        "stock_dimensions": [length, width, thickness],
        "cutting_parameters": mat_info,
        "tools": final_tools,
        "tool_count": len(final_tools),
        "total_machining_min": total_machining_min,
        "dfm_warnings": dfm_warnings
    }


def generate_gcode_preview(project_no: str, material_name: str, tools: list[dict], features: list[dict]) -> str:
    """Generates industry-standard ISO G-code preview (G54, G81, G83, M06, M03, M05)."""
    lines = [
        f"% (PROJECT: {project_no})",
        f"(PROGRAM: MECHNOVA AUTONOMOUS CAM ENGINE)",
        f"(MATERIAL: {material_name})",
        f"(TOOL COUNT: {len(tools)})",
        "G21 (Metric Units)",
        "G90 (Absolute Positioning)",
        "G17 (XY Plane Selection)",
        "G94 (Feed per Minute Mode)",
        "G54 (Work Coordinate System Origin)",
        "G40 G49 G80 (Cancel Cutter Comp, Tool Length, Canned Cycles)",
        "G28 G91 Z0.0 (Spindle Home)",
        "G90"
    ]

    for t in tools:
        tno = t.get("tool_no", "T01")
        dia = t.get("diameter", 10.0)
        rpm = t.get("suggested_rpm", 4000)
        feed = t.get("suggested_feed", 800)
        desc = t.get("name", "Tool")
        purpose = t.get("purpose", "")

        lines.extend([
            "",
            f"(-----------------------------------------)",
            f"(OPERATION: {purpose})",
            f"(TOOL: {tno} - {desc} - DIA {dia}mm)",
            f"(-----------------------------------------)",
            f"{tno} M06 (Tool Change)",
            f"G43 H{tno.replace('T','')} Z50.0 (Tool Length Offset)",
            f"S{rpm} M03 (Spindle On CW)",
            "M08 (Flood Coolant On)",
            "G00 X0.0 Y0.0",
            "G00 Z5.0"
        ])

        if t.get("type") == "face_mill":
            lines.extend([
                f"G01 Z-0.5 F{feed//2} (Facing Pass Top Z)",
                f"G01 X110.0 Y0.0 F{feed}",
                f"G00 Z5.0",
                f"G00 X0.0 Y25.0",
                f"G01 Z-0.5 F{feed//2}",
                f"G01 X110.0 Y25.0 F{feed}",
                "G00 Z25.0"
            ])
        elif t.get("type") == "spot_drill":
            lines.extend([
                f"G81 X20.0 Y20.0 Z-2.0 R3.0 F{feed} (Spot Drilling Cycle)",
                "X78.0 Y78.0",
                "G80 (Cancel Canned Cycle)",
                "G00 Z25.0"
            ])
        elif t.get("type") == "drill":
            is_peck = "Peck" in purpose or any("PECK_DRILL" in str(f) for f in features)
            cycle = f"G83 X20.0 Y20.0 Z-20.0 Q4.0 R3.0 F{feed} (Peck Drilling Cycle Q=4mm)" if is_peck else f"G81 X20.0 Y20.0 Z-20.0 R3.0 F{feed} (Standard Drill Cycle)"
            lines.extend([
                cycle,
                "X78.0 Y78.0",
                "G80 (Cancel Cycle)",
                "G00 Z25.0"
            ])
        elif t.get("type") == "end_mill":
            lines.extend([
                f"G00 X15.0 Y50.0",
                f"G01 Z-5.0 F{feed//3} (Plunge / Ramp Entry)",
                f"G01 X35.0 Y50.0 F{feed} (Linear Roughing Cut)",
                f"G01 X35.0 Y65.0 F{feed}",
                f"G01 X15.0 Y65.0 F{feed}",
                f"G01 X15.0 Y50.0 F{feed}",
                "G00 Z25.0"
            ])
        elif t.get("type") == "chamfer":
            lines.extend([
                f"G00 X0.0 Y0.0",
                f"G01 Z-0.5 F{feed//2} (Chamfer 0.5mm)",
                f"G01 X100.0 F{feed}",
                f"G01 Y60.0 F{feed}",
                f"G01 X0.0 F{feed}",
                f"G01 Y0.0 F{feed}",
                "G00 Z25.0"
            ])

        lines.extend([
            "M09 (Coolant Off)",
            "M05 (Spindle Stop)"
        ])

    lines.extend([
        "",
        "(PROGRAM END)",
        "G28 G91 Z0.0 (Return Spindle Home)",
        "G28 G91 X0.0 Y0.0 (Return Table to Front)",
        "M30 (End Program and Rewind)",
        "%"
    ])

    return "\n".join(lines)
