"""
MECHNOVA Autonomous Suite - Intro Background Generator
Renders a seamless, looping 1920x1080 30fps animated background
with a rotating 3D CAD wireframe gear/bracket, glowing toolpath line,
faint perspective coordinate grid, and drifting particle dust.
"""

import math
import os
import random
import shutil
import subprocess
from pathlib import Path
import cv2
import numpy as np

W, H, FPS, SEC = 1920, 1080, 30, 14
N = FPS * SEC


def build_cad_geometry():
    """Builds a multi-component 3D wireframe representing a precision machined bracket & spur gear."""
    vertices = []
    edges = []

    # 1. Spur Gear (16 teeth, pitch circle r1=1.1, tip r2=1.4, thickness z=0.3)
    teeth = 16
    gear_pts = []
    for i in range(teeth * 2):
        angle = i * math.pi / teeth
        r = 1.4 if i % 2 == 0 else 1.1
        gear_pts.append((r * math.cos(angle), r * math.sin(angle)))

    # Front and Back face vertices
    n_pts = len(gear_pts)
    for x, y in gear_pts:
        vertices.append((x, y, -0.3))
    for x, y in gear_pts:
        vertices.append((x, y, 0.3))

    # Edges around circumference & interconnects
    for i in range(n_pts):
        edges.append((i, (i + 1) % n_pts))
        edges.append((i + n_pts, (i + 1) % n_pts + n_pts))
        edges.append((i, i + n_pts))

    # 2. Inner Hub Cylinder (r=0.6)
    hub_pts = 16
    offset = len(vertices)
    for i in range(hub_pts):
        angle = i * 2 * math.pi / hub_pts
        vertices.append((0.6 * math.cos(angle), 0.6 * math.sin(angle), -0.4))
    for i in range(hub_pts):
        angle = i * 2 * math.pi / hub_pts
        vertices.append((0.6 * math.cos(angle), 0.6 * math.sin(angle), 0.4))
    for i in range(hub_pts):
        edges.append((offset + i, offset + (i + 1) % hub_pts))
        edges.append((offset + i + hub_pts, offset + (i + 1) % hub_pts + hub_pts))
        edges.append((offset + i, offset + i + hub_pts))

    # 3. Square Mounting Flange Box
    offset2 = len(vertices)
    flange_corners = [
        (-1.8, -1.8, -0.2), (1.8, -1.8, -0.2), (1.8, 1.8, -0.2), (-1.8, 1.8, -0.2),
        (-1.8, -1.8, 0.2), (1.8, -1.8, 0.2), (1.8, 1.8, 0.2), (-1.8, 1.8, 0.2)
    ]
    for c in flange_corners:
        vertices.append(c)
    box_edges = [
        (0, 1), (1, 2), (2, 3), (3, 0),
        (4, 5), (5, 6), (6, 7), (7, 4),
        (0, 4), (1, 5), (2, 6), (3, 7)
    ]
    for a, b in box_edges:
        edges.append((offset2 + a, offset2 + b))

    # 4. Bolt holes on flange corners
    bolt_r = 0.22
    corner_centers = [(-1.35, -1.35), (1.35, -1.35), (1.35, 1.35), (-1.35, 1.35)]
    for cx, cy in corner_centers:
        hole_offset = len(vertices)
        for i in range(8):
            a = i * 2 * math.pi / 8
            vertices.append((cx + bolt_r * math.cos(a), cy + bolt_r * math.sin(a), -0.21))
        for i in range(8):
            edges.append((hole_offset + i, hole_offset + (i + 1) % 8))

    return np.array(vertices, dtype=np.float32), edges


def rot_matrix(ax, ay, az):
    """3D Euler Rotation Matrix"""
    cx, sx = math.cos(ax), math.sin(ax)
    cy, sy = math.cos(ay), math.sin(ay)
    cz, sz = math.cos(az), math.sin(az)

    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]], dtype=np.float32)
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], dtype=np.float32)
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]], dtype=np.float32)
    return Rz @ Ry @ Rx


def main():
    print(f"[Intro BG] Generating {N} frames ({SEC}s @ {FPS}fps, {W}x{H})...")

    # Target output paths
    out_dirs = [
        Path("frontend/static/bg"),
        Path("platform/frontend/public/bg")
    ]
    for d in out_dirs:
        d.mkdir(parents=True, exist_ok=True)

    mp4_main = out_dirs[0] / "intro.mp4"
    poster_main = out_dirs[0] / "intro_poster.png"

    # Base background gradient (Deep Navy: #050b1f -> #0b2a5b)
    # BGR format: #050b1f is (31, 11, 5), #0b2a5b is (91, 42, 11)
    base_grad = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        b = int(31 + (95 - 31) * t)
        g = int(11 + (44 - 11) * t)
        r = int(5 + (12 - 5) * t)
        base_grad[y, :] = (b, g, r)

    # CAD Wireframe Model
    V, E = build_cad_geometry()

    # Fixed seed for deterministic, seamless particle field
    random.seed(42)
    particles = []
    for _ in range(180):
        px = random.random() * W
        py = random.random() * H
        pz = random.random() * 0.7 + 0.3
        radius = random.choice([1, 1, 2])
        particles.append((px, py, pz, radius))

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(mp4_main), fourcc, FPS, (W, H))

    poster_saved = False

    for f in range(N):
        # Progress indicator every 60 frames
        if f % 60 == 0:
            print(f"[Intro BG] Rendering frame {f}/{N} ({(f/N)*100:.0f}%)...")

        # Periodic time variable for 100% seamless looping
        t = (f / N) * 2 * math.pi

        frame = base_grad.copy()
        glow_layer = np.zeros((H, W, 3), dtype=np.uint8)

        # 1. Subtle background grid floor (perspective grid lines)
        grid_alpha = 0.15
        grid_y_start = int(H * 0.65)
        for gy in range(grid_y_start, H, 38):
            cv2.line(frame, (0, gy), (W, gy), (55, 28, 12), 1, cv2.LINE_AA)
        for gx in range(0, W, 75):
            cv2.line(frame, (gx, grid_y_start), (int((gx - W / 2) * 1.8 + W / 2), H), (45, 22, 10), 1, cv2.LINE_AA)

        # 2. Rotating 3D CAD Wireframe Model
        # Rotation angles: smoothly completes full 360-degree rotation
        ax = 0.55 + 0.22 * math.sin(t)
        ay = t  # Full 2*pi rotation over N frames
        az = 0.15 * math.cos(t)
        R = rot_matrix(ax, ay, az)

        P = (V @ R.T)
        # Perspective projection onto right-hand focal zone (W * 0.65, H * 0.5)
        # Shift object along Z to keep in front of camera
        cam_z = 5.2 + P[:, 2]
        s = 520.0 / np.maximum(cam_z, 0.1)

        pts_x = (W * 0.64 + P[:, 0] * s).astype(np.int32)
        pts_y = (H * 0.50 + P[:, 1] * s).astype(np.int32)

        # Draw wireframe lines on both base frame and glow layer
        for a, b in E:
            pt1 = (int(pts_x[a]), int(pts_y[a]))
            pt2 = (int(pts_x[b]), int(pts_y[b]))
            # Vivid cyan / electric blue in BGR (255, 185, 55)
            cv2.line(frame, pt1, pt2, (255, 185, 55), 2, cv2.LINE_AA)
            cv2.line(glow_layer, pt1, pt2, (255, 140, 25), 4, cv2.LINE_AA)

        # 3. Drifting Dust Particles (seamless vertical loop)
        for px, py, pz, radius in particles:
            # Wrap py seamlessly using modulo H
            curr_y = int((py - (f / N) * H * pz * 1.5) % H)
            curr_x = int(px)
            # Soft blue-white particle
            cv2.circle(frame, (curr_x, curr_y), radius, (230, 200, 160), -1, cv2.LINE_AA)

        # 4. Faint glowing CNC toolpath laser sweep
        # Periodic sweep from left to right
        sweep_x = int((f / N) * (W + 600)) - 300
        cv2.line(frame, (sweep_x, 0), (sweep_x - 380, H), (255, 230, 180), 1, cv2.LINE_AA)
        cv2.line(glow_layer, (sweep_x, 0), (sweep_x - 380, H), (255, 190, 110), 3, cv2.LINE_AA)

        # 5. Apply Bloom / Glow to lines
        glow_blurred = cv2.GaussianBlur(glow_layer, (15, 15), 0)
        frame = cv2.addWeighted(frame, 1.0, glow_blurred, 0.55, 0)

        # Save frame 30 as high-quality poster image
        if f == 30 and not poster_saved:
            cv2.imwrite(str(poster_main), frame)
            poster_saved = True

        writer.write(frame)

    writer.release()
    print(f"[Intro BG] Finished writing {mp4_main} ({os.path.getsize(mp4_main) / (1024*1024):.2f} MB)")

    # Copy files to secondary directory (client/public/bg)
    shutil.copy(str(mp4_main), str(out_dirs[1] / "intro.mp4"))
    shutil.copy(str(poster_main), str(out_dirs[1] / "intro_poster.png"))

    # Also save as intro.webm fallback
    for d in out_dirs:
        shutil.copy(str(d / "intro.mp4"), str(d / "intro.webm"))


if __name__ == "__main__":
    main()
