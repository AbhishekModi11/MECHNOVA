"""Rule-based CNC plan: operations, tools, equipment. Cutting data = carbide starting values; operator must verify."""
import math

MATERIALS = {   # vc = surface speed m/min, fz = feed per tooth mm, coolant
    "Aluminum 6061-T6": dict(vc=300, fz=0.06, coolant="Flood or mist", flutes=3),
    "Mild Steel 1018":  dict(vc=120, fz=0.04, coolant="Flood",         flutes=4),
    "Stainless 304":    dict(vc=80,  fz=0.03, coolant="Flood (high pressure)", flutes=4),
    "Titanium Ti-6Al-4V": dict(vc=45, fz=0.03, coolant="Flood (high pressure)", flutes=4),
}
STD_EM = [3, 4, 6, 8, 10, 12, 16, 20]

def _cut(d, mat):
    m = MATERIALS.get(mat, MATERIALS["Aluminum 6061-T6"])
    rpm = int(m["vc"]*1000/(math.pi*d))
    return dict(rpm=rpm, feed_mm_min=int(rpm*m["flutes"]*m["fz"]))

def _em_for(limit):
    ok = [d for d in STD_EM if d <= limit]
    return ok[-1] if ok else None

def recommend(analysis, material, bbox):
    feats = [f for f in analysis["features"] if f.get("enabled", True)]
    holes = [f for f in feats if f["kind"] in ("hole", "blind_hole")]
    pockets = [f for f in feats if f["kind"] in ("pocket", "slot", "window")]
    tools, ops, warn = [], [], []
    def tool(name, dia, kind, **kw):
        for t in tools:
            if t["name"] == name: return t
        t = dict(id=f"T{len(tools)+1}", name=name, diameter=dia, type=kind, **_cut(dia, material), **kw); tools.append(t); return t

    setups = ["+Z"] + sorted({f["setup"] for f in feats} - {"+Z"})

    fm = tool("Face mill 50 mm, 5 inserts" if min(bbox[:2]) < 90 else "Face mill 63 mm, 5 inserts", 50 if min(bbox[:2]) < 90 else 63, "face_mill")
    ops.append(dict(name="Face top", tool=fm["id"], setup="+Z", features=[]))

    for f in pockets:
        short = min(f["size"]); lim = short*(0.8 if f["kind"] == "slot" else 0.5)
        d = _em_for(lim)
        if d is None: warn.append(f"{f['id']}: opening {short} mm is too small for a standard end mill"); continue
        t = next((x for x in tools if x["type"] == "end_mill" and x["diameter"] == d), None) or \
            tool(f"Carbide end mill {d} mm, {MATERIALS.get(material, MATERIALS['Aluminum 6061-T6'])['flutes']} flute", d, "end_mill", flute_length=round(f["depth"]*1.2, 1))
        t["flute_length"] = max(t.get("flute_length", 0), round(f["depth"]*1.2, 1))
        ops.append(dict(name=f"Mill {f['kind']} {f['id']}", tool=t["id"], setup=f["setup"], features=[f["id"]],
                        depth=f["depth"], step_down=round(min(d*0.5, f["depth"]), 1)))
        if f["depth"] > 3*d: warn.append(f"{f['id']}: depth {f['depth']} mm > 3x tool diameter, use a long-reach tool and light cuts")

    if holes:
        sp = tool("Spot drill 90 deg, 10 mm", 10, "spot_drill")
        for f in holes:
            ops.append(dict(name=f"Spot {f['id']}", tool=sp["id"], setup=f["setup"], features=[f["id"]], depth=1.5))
        by_dia = {}
        for f in holes: by_dia.setdefault(f["diameter"], []).append(f)
        for dia, fl in sorted(by_dia.items()):
            if dia <= 16:
                t = tool(f"Carbide drill {dia:.1f} mm", dia, "drill")
                for f in fl:
                    ops.append(dict(name=f"Drill {f['id']}", tool=t["id"], setup=f["setup"], features=[f["id"]], depth=f["depth"], peck=f["depth"] > 3*dia))
                    if f["depth"] > 5*dia: warn.append(f"{f['id']}: depth/diameter = {f['depth']/dia:.1f}, use peck drilling with through-coolant")
            else:
                pil = tool("Carbide drill 10 mm (pilot)", 10, "drill")
                e = 12 if dia >= 18 else (_em_for(dia*0.6) or 8)
                t = next((x for x in tools if x["type"] == "end_mill" and x["diameter"] == e), None) or tool(f"Carbide end mill {e} mm", e, "end_mill")
                for f in fl:
                    ops.append(dict(name=f"Pilot {f['id']}", tool=pil["id"], setup=f["setup"], features=[f["id"]], depth=f["depth"]))
                    ops.append(dict(name=f"Helical-bore {f['id']} to {dia} mm", tool=t["id"], setup=f["setup"], features=[f["id"]], depth=f["depth"]))
        ch = tool("Chamfer mill 90 deg, 12 mm", 12, "chamfer")
        ops.append(dict(name="Chamfer / deburr hole edges", tool=ch["id"], setup="+Z", features=[f["id"] for f in holes]))
        for f in holes:
            if f["diameter"] < 1.5: warn.append(f"{f['id']}: micro-hole {f['diameter']} mm, check tool availability")

    prof = tool("Carbide end mill 10 mm (profile finish)", 10, "end_mill")
    ops.append(dict(name="Profile / contour finish", tool=prof["id"], setup="+Z", features=[]))

    ops.sort(key=lambda o: setups.index(o["setup"]) if o["setup"] in setups else 9)
    for i, o in enumerate(ops, 1): o["order"] = i

    stock = [round(b + 6, 1) for b in bbox]
    m = MATERIALS.get(material, MATERIALS["Aluminum 6061-T6"])
    equipment = dict(
        machine="3-axis vertical machining centre" if len(setups) <= 2 else "3-axis VMC with 4th-axis indexer or modular fixture plate",
        setups=len(setups), setup_list=setups,
        workholding="Precision vise, 150 mm, with soft jaws" if len(setups) <= 2 else "Fixture plate + soft jaws (re-clamp between setups)",
        coolant=m["coolant"], tool_changer_slots_needed=len(tools),
        stock_suggestion_mm=stock, probe="Touch probe recommended for multi-setup work",
        notes=["Stock = part size + 3 mm per side (preview only; raw material is set later).",
               "Cutting data are carbide starting values; confirm with the tool maker."])
    return dict(operations=ops, tools=tools, equipment=equipment, warnings=warn)
