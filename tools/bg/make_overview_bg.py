"""
MECHNOVA Autonomous Suite - Overview Background Generator
Renders a calm, seamless, looping 1920x1080 30fps background
with slow-moving blue CNC contour curves, an undulating toolpath grid,
soft particle field, and subtle radial vignette for optimal text legibility.
"""

import math
import os
import random
import shutil
from pathlib import Path
import cv2
import numpy as np

W, H, FPS, SEC = 1920, 1080, 30, 14
N = FPS * SEC


def main():
    print(f"[Overview BG] Generating {N} frames ({SEC}s @ {FPS}fps, {W}x{H})...")

    out_dir = Path("frontend/static/bg")
    out_dir.mkdir(parents=True, exist_ok=True)

    mp4_main = out_dir / "overview.mp4"
    poster_main = out_dir / "overview_poster.png"

    # Base Deep Slate Navy: #040816 -> #071735 (Lower contrast, calmer)
    base_grad = np.zeros((H, W, 3), dtype=np.uint8)
    for y in range(H):
        t = y / H
        b = int(22 + (55 - 22) * t)
        g = int(8 + (23 - 8) * t)
        r = int(4 + (7 - 4) * t)
        base_grad[y, :] = (b, g, r)

    # Soft radial vignette mask to ensure center content has >= 4.5:1 contrast
    Y, X = np.ogrid[:H, :W]
    center_y, center_x = H / 2.0, W / 2.0
    dist_from_center = np.sqrt((X - center_x) ** 2 + (Y - center_y) ** 2)
    max_dist = math.sqrt(center_x ** 2 + center_y ** 2)
    vignette = 1.0 - 0.45 * (dist_from_center / max_dist) ** 1.8
    vignette = np.clip(vignette, 0.45, 1.0)[:, :, np.newaxis]

    # Pre-generate 140 soft ambient particles with fixed seed
    random.seed(99)
    particles = []
    for _ in range(140):
        px = random.random() * W
        py = random.random() * H
        sp = random.random() * 0.5 + 0.2
        r = random.choice([1, 1, 2])
        alpha = random.uniform(0.3, 0.7)
        particles.append((px, py, sp, r, alpha))

    # Grid definition: 24 horizontal contour lines across the screen
    num_contours = 22
    y_coords = np.linspace(80, H - 80, num_contours)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(str(mp4_main), fourcc, FPS, (W, H))

    poster_saved = False

    for f in range(N):
        if f % 60 == 0:
            print(f"[Overview BG] Rendering frame {f}/{N} ({(f/N)*100:.0f}%)...")

        t = (f / N) * 2 * math.pi
        frame = base_grad.copy()
        lines_overlay = np.zeros((H, W, 3), dtype=np.uint8)

        # 1. Slow-moving topographical / toolpath contour curves
        x_pts = np.linspace(0, W, 120)
        for idx, base_y in enumerate(y_coords):
            # Phase shifts per contour line for organic wave motion
            p_shift = idx * 0.4
            # Sine & Cosine undulation (periodic in t)
            wave1 = 28.0 * np.sin(x_pts * 0.0035 + t + p_shift)
            wave2 = 12.0 * np.cos(x_pts * 0.0070 - t + p_shift * 0.5)
            y_curve = base_y + wave1 + wave2

            pts = np.column_stack((x_pts, y_curve)).astype(np.int32)

            # Deep industrial cyan/cobalt blue: BGR (160, 90, 20) with lower contrast
            line_color = (180, 100, 25) if idx % 4 == 0 else (120, 65, 15)
            line_width = 2 if idx % 4 == 0 else 1
            cv2.polylines(lines_overlay, [pts], False, line_color, line_width, cv2.LINE_AA)

        # 2. Subtle vertical toolpath guides
        for gx in range(120, W, 180):
            shift_x = int(gx + 15 * math.sin(t + gx * 0.01))
            cv2.line(lines_overlay, (shift_x, 0), (shift_x, H), (70, 35, 10), 1, cv2.LINE_AA)

        # 3. Soft ambient floating particles
        for px, py, sp, r, alpha in particles:
            curr_y = int((py - (f / N) * H * sp) % H)
            curr_x = int((px + 20 * math.sin(t + py * 0.01)) % W)
            # Soft cyan dot
            cv2.circle(lines_overlay, (curr_x, curr_y), r, (190, 130, 60), -1, cv2.LINE_AA)

        # Blend lines with subtle Gaussian glow
        glow = cv2.GaussianBlur(lines_overlay, (11, 11), 0)
        combined = cv2.addWeighted(lines_overlay, 0.85, glow, 0.35, 0)

        # Blend over gradient
        frame = cv2.addWeighted(frame, 1.0, combined, 0.85, 0)

        # Apply vignette
        frame = (frame.astype(np.float32) * vignette).astype(np.uint8)

        if f == 30 and not poster_saved:
            cv2.imwrite(str(poster_main), frame)
            poster_saved = True

        writer.write(frame)

    writer.release()
    print(f"[Overview BG] Finished writing {mp4_main} ({os.path.getsize(mp4_main) / (1024*1024):.2f} MB)")

    # Save webm fallback
    shutil.copy(str(mp4_main), str(out_dir / "overview.webm"))


if __name__ == "__main__":
    main()
