#!/usr/bin/env python3
"""Generate and download a real image from the Nightingale ChatGPT session."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import time
from pathlib import Path

from social_content import BRAND, DEFAULT_OUTPUT_DIR

DEFAULT_CHATGPT_URL = "https://chatgpt.com/c/6afbe414-b624-83ea-8f24-7480abe6dc21"


def _visible(page, selector: str):
    locator = page.locator(selector)
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


def _image_candidates(page) -> list[dict]:
    locator = page.locator("main img")
    if not locator.count():
        locator = page.locator("img")
    values = locator.evaluate_all(
        """els => els.map((image, index) => {
            const rect = image.getBoundingClientRect();
            return {
              index,
              src: image.currentSrc || image.src || '',
              width: image.naturalWidth || Math.round(rect.width),
              height: image.naturalHeight || Math.round(rect.height),
              visible: !!(rect.width && rect.height)
            };
        })"""
    )
    return [
        value for value in values
        if value.get("src") and value.get("visible")
        and int(value.get("width") or 0) >= 256
        and int(value.get("height") or 0) >= 256
    ]


def _download_image(page, src: str) -> tuple[bytes, str]:
    result = page.evaluate(
        """async src => {
          const response = await fetch(src, {credentials: 'include'});
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const bytes = new Uint8Array(await response.arrayBuffer());
          let binary = '';
          const chunkSize = 0x8000;
          for (let i = 0; i < bytes.length; i += chunkSize) {
            binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
          }
          return {base64: btoa(binary), contentType: response.headers.get('content-type') || 'image/png'};
        }""",
        src,
    )
    return base64.b64decode(result["base64"]), result["contentType"]


def _extension(content_type: str, data: bytes) -> str:
    content_type = content_type.split(";", 1)[0].lower()
    if content_type == "image/jpeg" or data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content_type == "image/webp" or (data.startswith(b"RIFF") and b"WEBP" in data[:16]):
        return ".webp"
    return ".png"


def _image_prompt(headline: str) -> str:
    return f"""Generate the actual finished square Instagram image now for {BRAND['name']}. Do not return an image prompt, JSON, a plan, or a caption-only response. Use the image generation tool and render the image in this chat.

Use the official {BRAND['name']} shield logo already shown in this conversation and preserve its original proportions and recognizable colors. Create a polished 1080x1080 social graphic for this exact campaign: “{headline}”. Use the website brand system: deep navy {BRAND['navy']}, blue {BRAND['blue']}, gold {BRAND['gold']}, and white text, with an elegant healthcare education style and generous safe margins. Include the exact headline “{headline.upper()}” and a restrained footer: “Missouri City, TX | {BRAND['phone']} | nightingalernacademy.com”. Visually support NCLEX-RN preparation, BLS, ACLS, and PALS without inventing dates, prices, reviews, credentials, or outcomes. The logo and all text must be legible. Generate the actual image now; after rendering, give only a short confirmation."""


def generate_image(
    post_date: dt.date,
    profile: Path,
    output_dir: Path,
    headline: str,
    *,
    chatgpt_url: str = DEFAULT_CHATGPT_URL,
    timeout_seconds: int = 240,
    force: bool = False,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{post_date.isoformat()}-chatgpt.png"
    if output.is_file() and not force:
        print(f"Using existing ChatGPT image: {output}")
        return output
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for ChatGPT image generation") from exc

    prompt = _image_prompt(headline)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            str(profile),
            executable_path=os.environ.get("BROWSER_EXECUTABLE_PATH", "/usr/bin/google-chrome"),
            headless=False,
            viewport={"width": 1440, "height": 1000},
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled", "--window-position=-10000,-10000"],
        )
        page = browser.new_page()
        try:
            page.goto(chatgpt_url, wait_until="domcontentloaded", timeout=60_000)
            page.wait_for_timeout(10_000)
            before = {item["src"] for item in _image_candidates(page)}
            composer = None
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline and composer is None:
                composer = _visible(
                    page,
                    '[contenteditable="true"][role="textbox"], textarea[data-testid="prompt-textarea"], textarea',
                )
                if composer is None:
                    page.wait_for_timeout(500)
            if composer is None:
                raise RuntimeError("ChatGPT composer was not available; check browser sign-in")
            composer.fill(prompt)
            send = None
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and send is None:
                send = _visible(page, 'button[data-testid="send-button"], button[aria-label="Send" i], button[aria-label="Send prompt" i]')
                if send is None:
                    page.wait_for_timeout(200)
            if send is None:
                raise RuntimeError("ChatGPT send button was not available")
            send.click()

            deadline = time.monotonic() + timeout_seconds
            fresh = None
            while time.monotonic() < deadline:
                candidates = [item for item in _image_candidates(page) if item["src"] not in before]
                if candidates:
                    fresh = candidates[-1]
                    break
                page.wait_for_timeout(1_000)
            if fresh is None:
                raise RuntimeError("ChatGPT did not expose a newly generated image")
            data, content_type = _download_image(page, fresh["src"])
            if len(data) < 10_000:
                raise RuntimeError("Downloaded ChatGPT image was unexpectedly small")
            output = output.with_suffix(_extension(content_type, data))
            output.write_bytes(data)
            print(f"Downloaded ChatGPT image: {output} ({len(data)} bytes)")
            return output
        finally:
            page.close()
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Post date in YYYY-MM-DD format; defaults to today")
    parser.add_argument("--profile", type=Path, default=Path(os.environ.get("BROWSER_PROFILE_DIR", ".browser-profile")))
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--chatgpt-url", default=os.environ.get("CHATGPT_URL", DEFAULT_CHATGPT_URL))
    parser.add_argument("--headline")
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    post_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    json_path = args.output_dir / f"{post_date.isoformat()}.json"
    headline = args.headline
    if not headline and json_path.is_file():
        headline = str(json.loads(json_path.read_text(encoding="utf-8"))["headline"])
    if not headline:
        raise SystemExit(f"Missing {json_path}; generate the caption first or pass --headline")
    generate_image(post_date, args.profile, args.output_dir, headline, chatgpt_url=args.chatgpt_url, timeout_seconds=args.timeout, force=args.force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
