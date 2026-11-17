#!/usr/bin/env python3
"""Render a generated social-post HTML card to a square PNG."""

from __future__ import annotations

import argparse
import datetime as dt
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Post date in YYYY-MM-DD format; defaults to today")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "social-posts")
    args = parser.parse_args()
    post_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    html_path = args.output_dir / f"{post_date.isoformat()}.html"
    png_path = args.output_dir / f"{post_date.isoformat()}.png"
    if not html_path.is_file():
        raise SystemExit(f"Missing {html_path}. Run social_content.py first.")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise SystemExit(
            "Playwright is required to render a PNG. Install it with the project's browser tooling."
        ) from exc

    executable = os.environ.get("BROWSER_EXECUTABLE_PATH", "/usr/bin/google-chrome")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            executable_path=executable if Path(executable).exists() else None,
            args=["--no-sandbox"],
        )
        page = browser.new_page(viewport={"width": 1080, "height": 1080}, device_scale_factor=1)
        page.goto(html_path.resolve().as_uri(), wait_until="networkidle", timeout=60_000)
        page.screenshot(path=str(png_path), full_page=False)
        browser.close()
    print(png_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
