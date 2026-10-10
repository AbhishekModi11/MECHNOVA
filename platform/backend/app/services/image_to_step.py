import os
from pathlib import Path
from typing import Tuple, Dict, Any, List
import cv2
import numpy as np
import cadquery as cq


def process_reference_image(
    image_path: Path | str,
    overlay_out_path: Path | str
) -> Dict[str, Any]:
    """Detects contours in a reference image using Canny edges and generates an edge overlay image."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError("Could not read image file.")

    h, w = img.shape[:2]
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        raise ValueError("No contours detected in reference image.")

    # Sort by area and select largest contour
    largest_contour = max(contours, key=cv2.contourArea)

    # Draw overlay for UI verification
    overlay = img.copy()
    cv2.drawContours(overlay, [largest_contour], -1, (0, 255, 0), 2)
    cv2.imwrite(str(overlay_out_path), overlay)

    # Bounding rect
    bx, by, bw, bh = cv2.boundingRect(largest_contour)

    return {
        "image_width_px": w,
        "image_height_px": h,
        "contour_bbox_px": {"x": bx, "y": by, "width": bw, "height": bh},
        "points_count": len(largest_contour),
        "overlay_path": str(overlay_out_path),
        "method_label": "2.5D extrusion from reference image (Canny contour detection, not true 3D scan)"
    }


def extrude_contour_to_step(
    image_path: Path | str,
    target_width_mm: float,
    extrusion_height_mm: float,
    out_step_path: Path | str
) -> Path:
    """Takes the largest contour, scales to target_width_mm, extrudes in CadQuery, and exports STEP."""
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError(f"Unable to read image at {image_path}")
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        raise ValueError("No contour detected for 2.5D extrusion.")

    largest = max(contours, key=cv2.contourArea)
    
    # Approximate polygon to reduce point count for clean CAD b-spline / polyline
    epsilon = 0.005 * cv2.arcLength(largest, True)
    approx = cv2.approxPolyDP(largest, epsilon, True)
    
    pts = approx.reshape(-1, 2)
    if len(pts) < 3:
        raise ValueError("Contour approximation has fewer than 3 points.")

    # Normalize and scale
    min_x, min_y = np.min(pts, axis=0)
    max_x, max_y = np.max(pts, axis=0)
    orig_w = max(1e-3, max_x - min_x)
    
    scale = target_width_mm / orig_w
    
    # Center points in mm
    pts_mm: List[Tuple[float, float]] = []
    center_x = (min_x + max_x) / 2.0
    center_y = (min_y + max_y) / 2.0
    
    for px, py in pts:
        x_mm = float((px - center_x) * scale)
        # Invert Y to match Cartesian CAD orientation
        y_mm = float(-(py - center_y) * scale)
        pts_mm.append((x_mm, y_mm))

    # CadQuery extrusion
    poly = cq.Workplane("XY").polyline(pts_mm).close()
    solid = poly.extrude(extrusion_height_mm)
    
    out_p = Path(out_step_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    cq.exporters.export(solid, str(out_p))
    
    return out_p
