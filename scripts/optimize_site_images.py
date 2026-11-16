#!/usr/bin/env python3
"""Compress assets/screens/*.png (prototype frames) to max width 860 + WebP sibling."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SCREENS = ROOT / "assets" / "screens"
MAX_WIDTH = 430
WEBP_QUALITY = 82
SKIP_DIRS = {"ios"}


def optimize_in_place(path: Path) -> None:
    webp = path.with_suffix(".webp")
    with Image.open(path) as im:
        if im.mode in ("RGBA", "LA", "P"):
            im = im.convert("RGBA")
        else:
            im = im.convert("RGB")
        w, h = im.size
        if w > MAX_WIDTH:
            nh = max(1, int(h * MAX_WIDTH / w))
            im = im.resize((MAX_WIDTH, nh), Image.Resampling.LANCZOS)
        if im.mode == "RGBA":
            im.save(path, optimize=True, compress_level=9)
        else:
            im.save(path, optimize=True)
        im.save(webp, format="WEBP", quality=WEBP_QUALITY, method=6)


def main() -> None:
    count = 0
    for path in sorted(SCREENS.glob("*.png")):
        if path.name == "placeholder.svg":
            continue
        optimize_in_place(path)
        count += 1
        print(f"ok {path.name}")
    print(f"done: {count} prototype PNGs")


if __name__ == "__main__":
    main()