"""Auto-select tools from the crib (inventory) for the tools the plan needs."""
GOOD_COAT = {"Al": {"uncoated", "ZrN", "DLC"}, "Steel": {"TiAlN", "AlTiN", "TiCN", "TiN"},
             "SS": {"TiAlN", "AlTiN"}, "Ti": {"AlTiN", "TiAlN"}}
BAD_COAT = {"Al": {"TiAlN", "AlTiN", "TiN", "TiCN"}, "Steel": set(), "SS": {"uncoated"}, "Ti": {"uncoated", "ZrN"}}

def mat_group(material):
    m = material.lower()
    return "Al" if "alum" in m else "Ti" if "titan" in m else "SS" if "stainless" in m else "Steel"

def condition_of(t):
    if t.get("damaged"): return "DAMAGED"
    w = t.get("wear_pct", 0)
    return "GOOD" if w < 50 else "FAIR" if w <= 80 else "WORN"

def usable(t):
    return t.get("qty", 0) > 0 and t.get("status", "AVAILABLE") == "AVAILABLE" and condition_of(t) != "DAMAGED"

def _fits(r, t):
    dd = t["diameter"] - r["diameter"]
    if abs(dd) <= 0.05: return True, True
    if r["type"] == "drill": return False, False                       # hole size must match exactly
    if r["type"] == "end_mill": return (-0.4*r["diameter"] <= dd < 0), False   # may be smaller, never larger
    return abs(dd) <= 0.25*r["diameter"], False

def match_tools(required, inventory, material):
    g = mat_group(material)
    left = {t["id"]: t.get("qty", 1) for t in inventory}
    results = []
    for r in required:
        cands = []
        for t in inventory:
            if t["type"] != r["type"] or not usable(t) or left[t["id"]] <= 0: continue
            ok, exact = _fits(r, t)
            if not ok: continue
            if r.get("flute_length") and t.get("flute_length", 0) < r["flute_length"]: continue
            coat_bad = t.get("coating", "uncoated") in BAD_COAT[g]
            coat_good = t.get("coating", "uncoated") in GOOD_COAT[g]
            score = abs(t["diameter"]-r["diameter"])*10 + (3 if coat_bad else 0 if coat_good else 1) + t.get("wear_pct", 0)/10
            cands.append(dict(tool=t, exact=exact, coat_bad=coat_bad, score=score))
        cands.sort(key=lambda c: c["score"])
        if not cands:
            results.append(dict(required_id=r["id"], required=r["name"], assigned=None, status="MISSING",
                                notes=[f"No usable {r['type'].replace('_',' ')} of about {r['diameter']} mm in the crib. Order or borrow one."],
                                alternatives=[])); continue
        best = cands[0]; t = best["tool"]; left[t["id"]] -= 1
        cond = condition_of(t); notes = []
        if not best["exact"]: notes.append(f"Diameter {t['diameter']} mm instead of {r['diameter']} mm: expect slower cycle")
        if best["coat_bad"]: notes.append(f"Coating {t['coating']} is not ideal for this material")
        if cond == "FAIR": notes.append(f"Wear {t['wear_pct']}%: inspect before use")
        if cond == "WORN": notes.append(f"Wear {t['wear_pct']}%: replace soon, only available option")
        status = "SUBSTITUTE" if not best["exact"] else "CAUTION" if (cond != "GOOD" or best["coat_bad"]) else "READY"
        results.append(dict(required_id=r["id"], required=r["name"], assigned=dict(t, condition=cond), status=status,
                            notes=notes, alternatives=[dict(c["tool"], condition=condition_of(c["tool"])) for c in cands[1:4]]))
    summary = {s: sum(x["status"] == s for x in results) for s in ("READY", "CAUTION", "SUBSTITUTE", "MISSING")}
    return dict(assignments=results, summary=summary, can_proceed=summary["MISSING"] == 0)
