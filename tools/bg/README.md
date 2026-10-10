# MECHNOVA Animated Video Backgrounds Generator

Python-only, open-source procedural background animation engine for MECHNOVA.
Generates seamless looping video files (1920×1080 @ 30fps) for the public **Intro (`/`)** and **Overview (`/overview`)** pages.

---

## 1. Prerequisites & Dependencies

All dependencies are 100% open-source:
```bash
pip install numpy opencv-python pillow
```

---

## 2. Generate Video Assets

Run the all-in-one generator script:
```bash
python tools/bg/make_all.py
```

Or run individual scripts:
```bash
python tools/bg/make_intro_bg.py
python tools/bg/make_overview_bg.py
```

### Outputs Generated:
- `frontend/static/bg/intro.mp4` & `intro.webm`
- `frontend/static/bg/intro_poster.png`
- `frontend/static/bg/overview.mp4` & `overview.webm`
- `frontend/static/bg/overview_poster.png`

---

## 3. Codec & FFmpeg Notes

- **Default / No FFmpeg:** When `ffmpeg` is not present on the system PATH, OpenCV uses the built-in `mp4v` codec which writes valid `.mp4` video files directly.
- **Optional WebM / VP9 Optimization:** If `ffmpeg` is installed, convert for minimal bundle size (< 5 MB) and maximum cross-browser streaming performance:
  ```bash
  # Convert Intro to VP9 WebM with CRF 30
  ffmpeg -y -i frontend/static/bg/intro.mp4 -c:v libvpx-vp9 -b:v 0 -crf 30 -an frontend/static/bg/intro.webm

  # Convert Overview to VP9 WebM with CRF 30
  ffmpeg -y -i frontend/static/bg/overview.mp4 -c:v libvpx-vp9 -b:v 0 -crf 30 -an frontend/static/bg/overview.webm
  ```

---

## 4. Visual Design Specifications

- **Intro Look:**
  - Deep Navy gradient (`#050b1f` → `#0b2a5b`).
  - Rotating 3D CAD wireframe gear and flange bracket model projected mathematically via NumPy perspective projection.
  - Antialiased lines with dual-layer Gaussian bloom glow (`cv2.addWeighted`).
  - Drifting dust particles and a faint glowing CNC toolpath laser sweep.
  - Seamless period loop ($t \in [0, 2\pi)$).

- **Overview Look:**
  - Deep, calm navy backdrop designed for high readability (text contrast $\ge 4.5:1$).
  - Undulating topographical toolpath contour lines.
  - Soft floating particle field and radial vignette.
