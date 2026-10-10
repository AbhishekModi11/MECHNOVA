"""Estimated time and material savings: recommended plan vs a conservative manual baseline.
All numbers are ESTIMATES from the stated assumptions, shown to the user as such."""
import math
from recommend import MATERIALS

SPINDLE_MAX, TOOL_CHANGE_MIN, SETUP_MIN = 12000, 0.15, 10.0
DENSITY = {"Aluminum 6061-T6": 2.70, "Mild Steel 1018": 7.87, "Stainless 304": 8.00, "Titanium Ti-6Al-4V": 4.43}  # g/cm3
OPT_ALLOW, BASE_ALLOW = 3.0, 10.0       # stock added per side (mm)

ASSUMPTIONS = [
    "Recommended: stock = part size + 3 mm per side; baseline: part size + 10 mm per side rounded up to 10 mm.",
    "Recommended: largest end mill that fits each pocket (up to 0.5x width), full-depth roughing, face mill for facing.",
    "Baseline: one 6 mm end mill for every milling job, half-depth cuts, 60% of the feed, a 20 mm end mill for facing.",
    "Baseline drills run at 60% of the recommended feed and speed, with no spot drilling or chamfer pass.",
    "Both plans include the same setup time (10 min per setup) and 9 s per tool change; spindle limit 12 000 rpm.",
    "These are planning estimates, not measured results.",
]

def _rpm(vc, d): return min(vc*1000/(math.pi*d), SPINDLE_MAX)

def _mill(vol, d, m, ap_r, ae_r, fz_k):
    rpm = _rpm(m["vc"], d); f = rpm*m["flutes"]*m["fz"]*fz_k
    return vol / max(ae_r*d*ap_r*d*f, 1e-6)

def _drill(depth, d, m, k):
    rpm = _rpm(m["vc"], d)*k; f = rpm*0.02*d
    return depth/max(f, 1e-6)*(1.6 if depth > 3*d else 1.0) + 0.05

def plan_time(analysis, material, bbox, mode):
    m = MATERIALS.get(material, MATERIALS["Aluminum 6061-T6"])
    feats = [f for f in analysis["features"] if f.get("enabled", True)]
    opt = mode == "opt"; bx, by, bz = bbox
    allow = OPT_ALLOW if opt else BASE_ALLOW
    ph = {k: [] for k in ("face", "pocket", "spot", "drill", "bore", "chamfer", "profile")}; t = 0.0
    # facing
    if opt: t += _mill(bx*by*allow, 50, m, 0.06, 0.7, 1.0); ph["face"].append("face_mill")
    else:   t += _mill(bx*by*allow, 20, m, 0.10, 0.6, 0.6); ph["face"].append("em20")
    for f in feats:
        if f["kind"] in ("pocket", "slot", "window"):
            if opt:
                d = max([x for x in (3, 4, 6, 8, 10, 12, 16, 20) if x <= min(f["size"])*(0.8 if f["kind"] == "slot" else 0.5)] or [3])
                t += _mill(f["size"][0]*f["size"][1]*f["depth"], d, m, 1.0, 0.5, 1.0); ph["pocket"].append(f"em{d}")
            else:
                t += _mill(f["size"][0]*f["size"][1]*f["depth"], 6, m, 0.5, 0.3, 0.6); ph["pocket"].append("em6")
        else:
            d = f["diameter"] or 6
            if opt: ph["spot"].append("spot"); ph["chamfer"].append("chamfer"); t += 0.18
            if d <= 16:
                t += _drill(f["depth"], d, m, 1.0 if opt else 0.6); ph["drill"].append(f"dr{d}")
            else:
                t += _drill(f["depth"], 10, m, 1.0 if opt else 0.6) + _mill(math.pi*d*d/4*f["depth"], 12 if opt else 6, m, 1.0 if opt else 0.5, 0.5 if opt else 0.3, 1.0 if opt else 0.6)
                ph["drill"].append("dr10"); ph["bore"].append("em12" if opt else "em6")
    # profile: perimeter x passes
    d = 10 if opt else 6; rpm = _rpm(m["vc"], d); feed = rpm*m["flutes"]*m["fz"]*(1.0 if opt else 0.6)
    passes = math.ceil(bz/((1.0 if opt else 0.5)*d)) + 1
    t += 2*(bx+by)*passes/feed; ph["profile"].append(f"em{d}")
    seq = [x for k in ph for x in sorted(ph[k])]          # grouped by phase, identical tools adjacent
    changes = sum(1 for a, b in zip(seq, seq[1:]) if a != b) + 1
    setups = len({f["setup"] for f in feats} | {"+Z"})
    return dict(machining_min=round(t, 2), tool_changes=changes, setups=setups,
                total_min=round(t + changes*TOOL_CHANGE_MIN + setups*SETUP_MIN, 2))

def savings(analysis, material, bbox, part_volume_mm3, user_stock=None):
    a, b = plan_time(analysis, material, bbox, "opt"), plan_time(analysis, material, bbox, "base")
    time_saved = max(0.0, (b["total_min"]-a["total_min"])/b["total_min"]*100)
    rec = [math.ceil(v+2*OPT_ALLOW) for v in bbox]
    base = [math.ceil((v+2*BASE_ALLOW)/10)*10 for v in bbox]
    chosen = list(user_stock) if user_stock else rec
    errors = [f"Stock axis {i+1} ({c} mm) is smaller than part + 2 mm" for i, (c, v) in enumerate(zip(chosen, bbox)) if c < v+2]
    vol = lambda s: s[0]*s[1]*s[2]
    kg = lambda s: vol(s)/1000*DENSITY.get(material, 2.7)/1000
    mat_saved = max(0.0, (vol(base)-vol(chosen))/vol(base)*100)
    return dict(
        time=dict(recommended=a, baseline=b, saved_pct=round(time_saved, 1), saved_min=round(b["total_min"]-a["total_min"], 1)),
        material=dict(recommended_stock=rec, baseline_stock=base, chosen_stock=chosen, saved_pct=round(mat_saved, 1),
                      saved_kg=round(kg(base)-kg(chosen), 2), chosen_kg=round(kg(chosen), 2),
                      utilisation_pct=round(part_volume_mm3/vol(chosen)*100, 1) if part_volume_mm3 else None, errors=errors),
        assumptions=ASSUMPTIONS, estimated=True)
