import os
import uuid
import hashlib
import numpy as np
import trimesh
import cv2
from PIL import Image
import cadquery as cq
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Body
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from features import detect_features
from recommend import recommend
from toolmatch import match_tools
from savings import savings

OUT = os.path.abspath("out")
os.makedirs(OUT, exist_ok=True)

app = FastAPI(title="Mechnova CAD Processing Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/meshes", StaticFiles(directory=OUT), name="meshes")

def vec(v):
    return np.array([v.x, v.y, v.z])

def rescale(mesh: trimesh.Trimesh, L: float, W: float, H: float) -> trimesh.Trimesh:
    mesh.apply_translation(-mesh.bounds.mean(axis=0))
    ext = mesh.extents
    sx = L / ext[0] if ext[0] > 1e-6 else 1.0
    sy = W / ext[1] if ext[1] > 1e-6 else 1.0
    sz = H / ext[2] if ext[2] > 1e-6 else 1.0
    mesh.apply_scale([sx, sy, sz])
    return mesh

def image_to_mesh(image_path: str, L: float = 100.0, W: float = 60.0, H: float = 20.0) -> trimesh.Trimesh:
    cv_img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
    if cv_img is None:
        raise ValueError(f"Could not load image at {image_path}")

    if len(cv_img.shape) == 3 and cv_img.shape[2] == 4:
        mask = (cv_img[:, :, 3] > 25).astype(np.uint8) * 255
    else:
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY) if len(cv_img.shape) == 3 else cv_img
        border = np.concatenate([gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]])
        bg_val = float(np.median(border))
        diff = cv2.absdiff(gray, int(bg_val))
        _, mask = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        plate = cq.Workplane("XY").box(L, W, H).edges("|Z").fillet(3.0)
        temp_stl = os.path.join(OUT, f"temp_{uuid.uuid4().hex[:8]}.stl")
        cq.exporters.export(plate, temp_stl, tolerance=0.05)
        m = trimesh.load(temp_stl, force="mesh")
        if os.path.exists(temp_stl): os.remove(temp_stl)
        return m

    areas = [cv2.contourArea(c) for c in contours]
    outer_idx = int(np.argmax(areas))
    outer_cnt = contours[outer_idx]
    bx, by, bw, bh = cv2.boundingRect(outer_cnt)
    peri = cv2.arcLength(outer_cnt, True)
    approx = cv2.approxPolyDP(outer_cnt, 0.0025 * peri, True)

    outer_pts = []
    for pt in approx:
        px, py = pt[0]
        nx = ((px - bx) / float(bw) - 0.5) * L
        ny = (0.5 - (py - by) / float(bh)) * W
        outer_pts.append((round(float(nx), 2), round(float(ny), 2)))
    if outer_pts[0] != outer_pts[-1]:
        outer_pts.append(outer_pts[0])

    solid = cq.Workplane("XY").polyline(outer_pts).close().extrude(H)

    if hier is not None:
        for i, h in enumerate(hier[0]):
            if h[3] == outer_idx and areas[i] > (bw * bh * 0.001):
                h_cnt = contours[i]
                h_peri = cv2.arcLength(h_cnt, True)
                h_area = areas[i]
                circularity = 4 * np.pi * h_area / max(1.0, (h_peri * h_peri))
                (hx, hy), radius = cv2.minEnclosingCircle(h_cnt)
                hnx = round(float(((hx - bx) / float(bw) - 0.5) * L), 2)
                hny = round(float((0.5 - (hy - by) / float(bh)) * W), 2)
                hradius = round(float(radius / float(bw) * L), 2)
                if circularity > 0.55 and hradius >= 1.0:
                    try:
                        solid = solid.faces(">Z").workplane().moveTo(hnx, hny).circle(hradius).cutThruAll()
                    except Exception:
                        pass

    temp_stl = os.path.join(OUT, f"temp_{uuid.uuid4().hex[:8]}.stl")
    cq.exporters.export(solid, temp_stl, tolerance=0.05)
    m = trimesh.load(temp_stl, force="mesh")
    if os.path.exists(temp_stl):
        try: os.remove(temp_stl)
        except Exception: pass

    return rescale(m, L, W, H)

def convert_to_stl(raw: str, ext: str, out_stl: str, L: float, W: float, H: float):
    if ext in (".step", ".stp"):
        shape = cq.importers.importStep(raw)
        cq.exporters.export(shape, out_stl, tolerance=0.05, angularTolerance=0.1)
    elif ext in (".png", ".jpg", ".jpeg"):
        m = image_to_mesh(raw, L=L, W=W, H=H)
        m.export(out_stl)
    elif ext == ".stl":
        if raw != out_stl:
            import shutil
            shutil.copyfile(raw, out_stl)
    else:
        raise ValueError(f"Unsupported format {ext}")

def health_and_repair(mesh):
    issues = []
    add = lambda sev, code, msg: issues.append(dict(severity=sev, code=code, message=msg))
    bodies = len(mesh.split(only_watertight=False))
    if bodies > 1: add("warning", "MULTI_BODY", f"{bodies} separate bodies found; confirm this is one part")
    if not mesh.is_winding_consistent:
        trimesh.repair.fix_normals(mesh); add("info", "NORMALS_FIXED", "Face orientation was inconsistent and was repaired")
    if not mesh.is_watertight:
        trimesh.repair.fill_holes(mesh)
        if mesh.is_watertight: add("info", "GAPS_CLOSED", "Small gaps in the mesh were closed")
        else: add("error", "NOT_WATERTIGHT", "Mesh is not watertight; hole and pocket detection may be unreliable")
    if mesh.is_watertight and mesh.volume < 0: mesh.invert(); add("info", "INVERTED", "Inside-out mesh was flipped")
    m = float(mesh.extents.max())
    if m < 5: add("warning", "UNITS_SMALL", f"Largest size is {m:.2f}; the model may be in metres or inches, not mm")
    if m > 2000: add("warning", "UNITS_LARGE", f"Largest size is {m:.0f}; the model may be in micrometres")
    return issues

def to_occupancy(mesh, max_cells=6_000_000):
    pitch = float(np.clip(mesh.extents.max() / 220, 0.25, 1.0))
    while np.prod(np.ceil(mesh.extents / pitch)) > max_cells: pitch *= 1.2
    vox = mesh.voxelized(pitch).fill()
    return np.asarray(vox.matrix, bool), pitch, np.asarray(vox.translation, float)

def analyze_stl(path, material):
    mesh = trimesh.load(path, force="mesh")
    issues = health_and_repair(mesh)
    occ, pitch, origin = to_occupancy(mesh)
    feats = detect_features(occ, pitch, tuple(origin))
    for f in feats: f["enabled"] = True
    holes = [f for f in feats if f["kind"] in ("hole", "blind_hole")]
    pockets = [f for f in feats if f["kind"] in ("pocket", "slot", "window")]
    bbox = [round(float(v), 2) for v in mesh.extents]
    part_volume_mm3 = float(abs(mesh.volume)) if mesh.is_watertight and abs(mesh.volume) > 1 else float(np.prod(bbox) * 0.45)

    if pitch > 0.5: issues.append(dict(severity="info", code="COARSE_GRID", message=f"Detection resolution is {pitch:.2f} mm; features under {2*pitch:.1f} mm may be missed"))
    if not feats: issues.append(dict(severity="warning", code="NO_FEATURES", message="No holes or pockets were found. Check the model orientation and units"))
    analysis = dict(status="READY", bbox=bbox, bounds_min=[round(float(v), 2) for v in mesh.bounds[0]],
                    part_volume_mm3=round(part_volume_mm3, 1),
                    features=feats, issues=issues, pitch_mm=round(pitch, 3),
                    summary=dict(holes=len(holes), pockets=len(pockets),
                                 through=sum(f["through"] for f in feats), issues=len(issues),
                                 blocking=sum(i["severity"] == "error" for i in issues)))
    analysis["plan"] = recommend(analysis, material, bbox)
    return analysis

@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    material: str = Form("Aluminum 6061-T6"),
    length: float = Form(100.0),
    width: float = Form(60.0),
    height: float = Form(20.0)
):
    data = await file.read()
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in (".stl", ".step", ".stp", ".png", ".jpg", ".jpeg"):
        raise HTTPException(415, "Use STL, STEP, PNG or JPG")
    
    uid = hashlib.sha256(data).hexdigest()[:16]
    raw = os.path.join(OUT, uid + ext)
    with open(raw, "wb") as f:
        f.write(data)
    
    if ext == ".stl":
        stl = raw
    elif ext in (".step", ".stp", ".png", ".jpg", ".jpeg"):
        stl = os.path.join(OUT, uid + ".stl")
        convert_to_stl(raw, ext, stl, length, width, height)
    
    res = analyze_stl(stl, material)
    res["mesh_url"] = f"/meshes/{os.path.basename(stl)}"
    res["exact"] = (ext in (".step", ".stp", ".stl"))
    return res

@app.post("/recompute_plan")
async def recompute_plan_endpoint(payload: dict = Body(...)):
    analysis = payload.get("analysis", {})
    material = payload.get("material", "Aluminum 6061-T6")
    bbox = payload.get("bbox", [100.0, 60.0, 20.0])
    plan = recommend(analysis, material, bbox)
    return {"plan": plan}

@app.post("/match-tools")
async def match_tools_endpoint(payload: dict = Body(...)):
    required = payload.get("required", [])
    inventory = payload.get("inventory", [])
    material = payload.get("material", "Aluminum 6061-T6")
    return match_tools(required, inventory, material)

@app.post("/savings")
async def savings_endpoint(payload: dict = Body(...)):
    analysis = payload.get("analysis", {})
    material = payload.get("material", "Aluminum 6061-T6")
    bbox = payload.get("bbox", analysis.get("bbox", [100.0, 60.0, 20.0]))
    part_volume_mm3 = payload.get("part_volume_mm3", analysis.get("part_volume_mm3", 0.0))
    user_stock = payload.get("user_stock", None)
    return savings(analysis, material, bbox, part_volume_mm3, user_stock)

@app.post("/process")
async def process(
    file: UploadFile = File(...),
    length: float = Form(100.0),
    width: float = Form(60.0),
    height: float = Form(20.0)
):
    data = await file.read()
    ext = os.path.splitext(file.filename.lower())[1]
    uid = hashlib.md5(data).hexdigest()[:12]
    raw = os.path.join(OUT, f"{uid}{ext}")
    with open(raw, "wb") as f:
        f.write(data)

    stl = os.path.join(OUT, f"{uid}.stl")
    if ext in (".step", ".stp"):
        convert_to_stl(raw, ext, stl, length, width, height)
    elif ext == ".stl":
        import shutil
        shutil.copyfile(raw, stl)
    elif ext in (".png", ".jpg", ".jpeg"):
        convert_to_stl(raw, ext, stl, length, width, height)
    else:
        raise HTTPException(415, f"Unsupported file type '{ext}'. Use STEP, STL, PNG or JPG.")

    res = analyze_stl(stl, "Aluminum 6061-T6")
    return {
        "meshUrl": f"/meshes/{os.path.basename(stl)}",
        "mesh_url": f"/meshes/{os.path.basename(stl)}",
        "bbox": res["bbox"],
        "part_volume_mm3": res.get("part_volume_mm3", 0.0),
        "features": res["features"],
        "holes": [f for f in res["features"] if f["kind"] in ("hole", "blind_hole")],
        "pockets": [f for f in res["features"] if f["kind"] in ("pocket", "slot", "window")],
        "issues": res["issues"],
        "summary": res["summary"],
        "plan": res["plan"],
        "source": "step" if ext in (".step", ".stp") else ("stl" if ext == ".stl" else "image"),
        "exact": ext in (".step", ".stp", ".stl")
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
