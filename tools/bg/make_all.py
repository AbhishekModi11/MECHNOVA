"""
MECHNOVA Background Generator Suite Runner
Generates both intro and overview looping background videos and poster assets.
"""

import sys
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

import make_intro_bg
import make_overview_bg


def main():
    print("=" * 65)
    print("MECHNOVA Autonomous Suite - Animated Video Background Generator")
    print("=" * 65)
    t0 = time.time()

    print("\n[1/2] Generating Intro Background...")
    make_intro_bg.main()

    print("\n[2/2] Generating Overview Background...")
    make_overview_bg.main()

    elapsed = time.time() - t0
    print("\n" + "=" * 65)
    print(f"[OK] All background animations successfully generated in {elapsed:.1f}s!")
    print("  Outputs in frontend/static/bg/:")
    print("  - frontend/static/bg/intro.mp4, intro.webm & intro_poster.png")
    print("  - frontend/static/bg/overview.mp4, overview.webm & overview_poster.png")
    print("=" * 65)


if __name__ == "__main__":
    main()
