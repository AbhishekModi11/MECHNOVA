"""CAD analysis integration module with resilient in-process fallback.
Tries the standalone CAD service on port 8001 first; if unreachable,
seamlessly performs analysis directly in-process without failing connections.
"""
import os
import sys
import hashlib
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
OUT_DIR = WORKSPACE_ROOT / "out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
CAD_SERVICE_URL = "http://127.0.0.1:8001"

# Ensure cad_service is importable
CAD_SERVICE_DIR = WORKSPACE_ROOT / "cad_service"
if str(CAD_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(CAD_SERVICE_DIR))


def _run_inprocess_analyze(
    file_bytes: bytes,
    filename: str,
    material: str = "Aluminum 6061-T6",
    length: float = 100.0,
    width: float = 60.0,
    height: float = 20.0
) -> Dict[str, Any]:
    """Execute CAD feature recognition and mesh analysis directly in-process."""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in (".stl", ".step", ".stp", ".png", ".jpg", ".jpeg"):
        raise ValueError(f"Unsupported file type '{ext}'. Use STL, STEP, PNG or JPG.")

    uid = hashlib.sha256(file_bytes).hexdigest()[:16]
    raw_path = str(OUT_DIR / f"{uid}{ext}")
    with open(raw_path, "wb") as f:
        f.write(file_bytes)

    from main import analyze_stl, convert_to_stl  # cad_service.main

    if ext == ".stl":
        stl_path = raw_path
    else:
        stl_path = str(OUT_DIR / f"{uid}.stl")
        convert_to_stl(raw_path, ext, stl_path, length, width, height)

    res = analyze_stl(stl_path, material)
    mesh_filename = os.path.basename(stl_path)
    res["mesh_url"] = f"/meshes/{mesh_filename}"
    res["exact"] = (ext in (".step", ".stp", ".stl"))
    return res


def _run_inprocess_process(
    file_bytes: bytes,
    filename: str,
    length: float = 100.0,
    width: float = 60.0,
    height: float = 20.0
) -> Dict[str, Any]:
    """Execute CAD process endpoint directly in-process."""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in (".stl", ".step", ".stp", ".png", ".jpg", ".jpeg"):
        raise ValueError(f"Unsupported file type '{ext}'. Use STL, STEP, PNG or JPG.")

    uid = hashlib.md5(file_bytes).hexdigest()[:12]
    raw_path = str(OUT_DIR / f"{uid}{ext}")
    with open(raw_path, "wb") as f:
        f.write(file_bytes)

    from main import analyze_stl, convert_to_stl

    stl_path = str(OUT_DIR / f"{uid}.stl")
    if ext in (".step", ".stp"):
        convert_to_stl(raw_path, ext, stl_path, length, width, height)
    elif ext == ".stl":
        import shutil
        if raw_path != stl_path:
            shutil.copyfile(raw_path, stl_path)
    elif ext in (".png", ".jpg", ".jpeg"):
        convert_to_stl(raw_path, ext, stl_path, length, width, height)

    res = analyze_stl(stl_path, "Aluminum 6061-T6")
    mesh_filename = os.path.basename(stl_path)
    return {
        "meshUrl": f"/meshes/{mesh_filename}",
        "mesh_url": f"/meshes/{mesh_filename}",
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


def _is_cad_service_alive(host: str = "127.0.0.1", port: int = 8001) -> bool:
    """Quick probe to check if CAD service port is listening."""
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            return s.connect_ex((host, port)) == 0
    except Exception:
        return False


async def analyze_cad_model(
    file_bytes: bytes,
    filename: str,
    material: str = "Aluminum 6061-T6",
    length: float = 100.0,
    width: float = 60.0,
    height: float = 20.0
) -> Dict[str, Any]:
    """Analyze CAD model, trying CAD service on port 8001 first, falling back to in-process."""
    if _is_cad_service_alive():
        try:
            timeout = httpx.Timeout(connect=2.0, read=90.0, write=30.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                files = {"file": (filename, file_bytes, "application/octet-stream")}
                data = {
                    "material": material,
                    "length": str(length),
                    "width": str(width),
                    "height": str(height)
                }
                resp = await client.post(f"{CAD_SERVICE_URL}/analyze", files=files, data=data)
                if resp.status_code == 200:
                    return resp.json()
                elif resp.status_code == 415:
                    raise ValueError("Unsupported file type. Use STL, STEP, PNG or JPG.")
        except ValueError:
            raise
        except Exception as e:
            logger.info("CAD service call failed (%s); falling back to in-process.", e)

    # In-process execution in thread pool to prevent blocking UI event loop
    return await asyncio.to_thread(
        _run_inprocess_analyze,
        file_bytes,
        filename,
        material,
        length,
        width,
        height
    )


async def process_cad_model(
    file_bytes: bytes,
    filename: str,
    length: float = 100.0,
    width: float = 60.0,
    height: float = 20.0
) -> Dict[str, Any]:
    """Process CAD model, trying CAD service first, falling back to in-process."""
    if _is_cad_service_alive():
        try:
            timeout = httpx.Timeout(connect=2.0, read=90.0, write=30.0, pool=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                files = {"file": (filename, file_bytes, "application/octet-stream")}
                data = {"length": str(length), "width": str(width), "height": str(height)}
                resp = await client.post(f"{CAD_SERVICE_URL}/process", files=files, data=data)
                if resp.status_code == 200:
                    return resp.json()
        except Exception:
            pass

    return await asyncio.to_thread(
        _run_inprocess_process,
        file_bytes,
        filename,
        length,
        width,
        height
    )
