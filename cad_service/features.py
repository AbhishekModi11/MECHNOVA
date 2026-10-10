"""Feature detection on a voxel occupancy grid (2.5D / prismatic CNC parts).
Finds through-holes, blind holes, closed pockets and open slots from the 6 tool-approach directions."""
import numpy as np
from scipy import ndimage as ndi

def _disk(r):
    y, x = np.ogrid[-r:r+1, -r:r+1]
    return (x*x + y*y) <= r*r

def _shape_of(mask):
    ii, jj = np.nonzero(mask)
    w = (ii.max()-ii.min()+1); h = (jj.max()-jj.min()+1)
    area = mask.sum()
    circular = abs(w-h) <= 0.12*max(w, h) and 0.70 <= area/(w*h) <= 0.85 and min(w, h) >= 3
    return w, h, area, circular, ((ii.min()+ii.max())/2, (jj.min()+jj.max())/2)

def _setup_features(occ, pitch, min_area_mm2=4.0):
    nz = occ.shape[2]
    any_ = occ.any(2)
    cnt = occ.sum(2)
    top = np.where(any_, nz-1-np.argmax(occ[:, :, ::-1], axis=2), -1)
    ztop = top.max()
    tol = max(1, int(round(0.5/pitch)))
    out = []
    min_cells = max(4, int(min_area_mm2/(pitch*pitch)))

    def ring(mask):
        return ndi.binary_dilation(mask) & ~mask

    # (a) enclosed through-holes: empty columns not connected to the outside
    empty = ~any_
    lab, n = ndi.label(empty)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    enclosed = np.zeros_like(empty)
    for i in range(1, n+1):
        if i in border: continue
        m = lab == i
        if m.sum() < min_cells: continue
        enclosed |= m
        w, h, area, circ, c = _shape_of(m)
        depth = float(np.median(cnt[ring(m) & any_])) * pitch
        out.append(dict(kind="hole" if circ else "window", through=True, plan=c,
                        diameter=round(2*np.sqrt(area/np.pi)*pitch, 2) if circ else None,
                        size=[round(w*pitch, 2), round(h*pitch, 2)], depth=round(depth, 2),
                        floor=int(np.median(top[ring(m) & any_]))))

    # (b) open through-slots / notches: empty areas that a big disk cannot enter
    fx = np.nonzero(any_.any(1))[0]; fy = np.nonzero(any_.any(0))[0]
    r = int(0.25*min(np.ptp(fx)+1, np.ptp(fy)+1))
    if r >= 2:
        pad = r+2
        closed = ndi.binary_closing(np.pad(any_, pad), structure=_disk(r))[pad:-pad, pad:-pad]
        notch = closed & empty & ~enclosed
        nl, nn = ndi.label(notch)
        for i in range(1, nn+1):
            m = nl == i
            if m.sum() < max(min_cells, 0.01*any_.sum()): continue
            sides = sum(bool((np.roll(m, sh, ax) & ~m & any_).any()) for ax in (0, 1) for sh in (1, -1))
            if sides < 3: continue                      # inner corner of the part, not a slot
            w, h, area, circ, c = _shape_of(m)
            depth = float(np.median(cnt[ring(m) & any_])) * pitch
            out.append(dict(kind="slot", through=True, plan=c, diameter=None,
                            size=[round(w*pitch, 2), round(h*pitch, 2)], depth=round(depth, 2),
                            floor=int(np.median(top[ring(m) & any_]))))

    # (c) closed blind features: flat floors lower than the part top, fully walled by higher material
    low = (top >= 0) & (top < ztop - tol)
    for lvl in np.unique(top[low]):
        ll, nl = ndi.label(top == lvl)
        for i in range(1, nl+1):
            m = ll == i
            if m.sum() < min_cells: continue
            nb = ring(m)
            if not nb.any(): continue
            if not np.all(top[nb] > lvl + tol): continue        # touches outside / lower area -> open step, not a pocket
            w, h, area, circ, c = _shape_of(m)
            depth = (float(np.median(top[nb])) - lvl) * pitch
            out.append(dict(kind="blind_hole" if circ else "pocket", through=False, plan=c,
                            diameter=round(2*np.sqrt(area/np.pi)*pitch, 2) if circ else None,
                            size=[round(w*pitch, 2), round(h*pitch, 2)], depth=round(depth, 2),
                            floor=int(lvl)))
    return out

def detect_features(occ, pitch, origin=(0, 0, 0)):
    """occ[x,y,z] bool; pitch in mm; origin = world position (mm) of voxel [0,0,0]."""
    feats = []
    for axis in range(3):
        others = [a for a in range(3) if a != axis]
        for sign in (+1, -1):
            o = np.transpose(occ, others+[axis])
            if sign < 0: o = o[:, :, ::-1]
            nz = o.shape[2]
            for f in _setup_features(o, pitch):
                i, j = f.pop("plan")
                world = [0.0, 0.0, 0.0]
                world[others[0]] = origin[others[0]] + i*pitch
                world[others[1]] = origin[others[1]] + j*pitch
                axis_pos = None
                if f["floor"] is not None:
                    k = f["floor"] if sign > 0 else nz-1-f["floor"]
                    world[axis] = origin[axis] + k*pitch
                f.pop("floor")
                vec = [0, 0, 0]; vec[axis] = sign
                f.update(center=[round(v, 2) for v in world], axis=vec, setup=("+" if sign > 0 else "-")+"XYZ"[axis])
                feats.append(f)
    return _py(_dedupe(feats))

def _dedupe(feats, tol=2.0):
    keep = []
    for f in feats:
        dup = False
        for g in keep:
            if f["through"] and g["through"] and f["kind"] == g["kind"] and abs(np.array(f["axis"])).tolist() == abs(np.array(g["axis"])).tolist():
                ax = int(np.argmax(np.abs(f["axis"])))
                pl = [a for a in range(3) if a != ax]
                if all(abs(f["center"][a]-g["center"][a]) <= tol for a in pl) and \
                   abs((f["diameter"] or 0)-(g["diameter"] or 0)) <= tol:
                    dup = True; break
        if not dup: keep.append(f)
    # ids
    cnt = {}
    for f in keep:
        p = {"hole": "H", "blind_hole": "B", "pocket": "P", "slot": "S", "window": "W"}[f["kind"]]
        cnt[p] = cnt.get(p, 0)+1; f["id"] = f"{p}{cnt[p]}"
    return keep

def _py(o):
    if isinstance(o, dict): return {k: _py(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)): return [_py(v) for v in o]
    if isinstance(o, np.generic): return o.item()
    return o
