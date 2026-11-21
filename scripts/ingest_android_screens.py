#!/usr/bin/env python3
"""Build Android v6 site assets from ghofi design/target-v6 PNGs.

Reads 860×1864 screens from design/target-v6/png/{dark,light}/android/{id}.png
and writes the same trio the iOS screens already use:

  assets/screens/v6/{dark,light}/android/{id}.png        860×1864
  assets/screens/v6/{dark,light}/android/{id}.webp       860×1864
  assets/screens/v6/{dark,light}/android/{id}-430.webp   430×932

Only ids passed on the command line are written. Source commit used for the
site: MuratPod/ghofi main 84399121b3cdc98c8ecb6920c6da2889e4b46192
(the squash of assistant/design-device-frames; frame and PNG bytes match
9554c891907874dd3cf9de93e9a953d9f14edfcd).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEBP_QUALITY = "82"


def used_ids() -> list[str]:
    ids: set[str] = set()
    for html in ROOT.glob("*/index.html"):
        text = html.read_text(encoding="utf-8")
        ids.update(_ids_in(text))
    ids.update(_ids_in((ROOT / "index.html").read_text(encoding="utf-8")))
    return sorted(ids)


def _ids_in(text: str) -> set[str]:
    import re

    return set(re.findall(r"assets/screens/v6/dark/([a-z0-9-]+)\.png", text))


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def convert_one(src: Path, dest_dir: Path, sid: str) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    png = dest_dir / f"{sid}.png"
    webp = dest_dir / f"{sid}.webp"
    webp430 = dest_dir / f"{sid}-430.webp"
    # Palette PNG, same approach as the committed iOS 860px screens.
    run(
        [
            "pngquant",
            "--quality=75-95",
            "--speed",
            "1",
            "--force",
            "--output",
            str(png),
            str(src),
        ]
    )
    run(["cwebp", "-quiet", "-q", WEBP_QUALITY, "-m", "6", str(src), "-o", str(webp)])
    run(
        [
            "cwebp",
            "-quiet",
            "-q",
            WEBP_QUALITY,
            "-m",
            "6",
            "-resize",
            "430",
            "932",
            str(src),
            "-o",
            str(webp430),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="design/target-v6 directory from ghofi",
    )
    parser.add_argument("ids", nargs="*", help="Screen ids. Default: ids already used on the site.")
    args = parser.parse_args()
    source: Path = args.source
    ids = args.ids or used_ids()
    if not ids:
        raise SystemExit("No screen ids")
    jobs: list[tuple[Path, Path, str, str]] = []
    for theme in ("dark", "light"):
        folder = source / "png" / theme / "android"
        dest = ROOT / "assets" / "screens" / "v6" / theme / "android"
        for sid in ids:
            src = folder / f"{sid}.png"
            if not src.is_file():
                raise SystemExit(f"Missing {src}")
            jobs.append((src, dest, sid, theme))
    written = 0
    with ProcessPoolExecutor(max_workers=8) as pool:
        futures = {
            pool.submit(convert_one, src, dest, sid): (theme, sid)
            for src, dest, sid, theme in jobs
        }
        for future in as_completed(futures):
            theme, sid = futures[future]
            future.result()
            written += 1
            print(f"ok {theme}/{sid}", flush=True)
    print(f"done: {written} screens")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit(exc.returncode or 1)
