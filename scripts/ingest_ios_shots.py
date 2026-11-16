#!/usr/bin/env python3
"""Copy iOS audit PNGs into assets/screens/ios/ with web-optimized PNG + WebP."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("/cursor/stores/bot/site-shots")
OUT_DIR = ROOT / "assets" / "screens" / "ios"
MAX_WIDTH = 430
WEBP_QUALITY = 82


def optimize_pair(src: Path, base_name: str) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_png = OUT_DIR / f"{base_name}.png"
    out_webp = OUT_DIR / f"{base_name}.webp"
    with Image.open(src) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")
        w, h = im.size
        if w > MAX_WIDTH:
            nh = max(1, int(h * MAX_WIDTH / w))
            im = im.resize((MAX_WIDTH, nh), Image.Resampling.LANCZOS)
        if im.mode == "RGBA":
            im.save(out_png, optimize=True, compress_level=9)
        else:
            im.save(out_png, optimize=True)
        im.save(out_webp, format="WEBP", quality=WEBP_QUALITY, method=6)


def main() -> None:
    if not SOURCE.is_dir():
        raise SystemExit(f"Source not found: {SOURCE}")
    ios_files = sorted(SOURCE.glob("ios-*.png"))
    if len(ios_files) != 19:
        print(f"warning: expected 19 ios-*.png, found {len(ios_files)}")
    for src in ios_files:
        base = src.stem  # ios-home-es-dark
        optimize_pair(src, base)
        print(f"ok {base}")
    print(f"done: {len(ios_files)} files -> {OUT_DIR}")


if __name__ == "__main__":
    main()