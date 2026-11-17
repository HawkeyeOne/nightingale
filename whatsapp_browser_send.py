#!/usr/bin/env python3
"""Send one generated Nightingale post through an authenticated WhatsApp Web session.

Preview is the default. Use --send only after confirming the recipient and that
WhatsApp Web is signed in in the supplied Chrome profile.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
from pathlib import Path

from social_content import build_post, whatsapp_text


ROOT = Path(__file__).resolve().parent
DEFAULT_PROFILE = Path(os.environ.get("BROWSER_PROFILE_DIR", ROOT / ".browser-profile"))
DEFAULT_OUTPUT_DIR = ROOT / "social-posts"


def visible(locator):
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


def normalize_search_number(value: str) -> str:
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    raise ValueError("Recipient must be a US 10- or 11-digit number.")


def send_post(profile: Path, recipient: str, image: Path, message: str, expected_contact: str | None, allow_duplicate: bool = False) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for browser sending.") from exc

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
            page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=60_000)
            search = page.locator(
                'input[placeholder*="Search" i], [role="textbox"][aria-label*="Search" i]'
            ).first
            search.wait_for(state="visible", timeout=30_000)
            search.click()
            search.fill(recipient)
            page.wait_for_timeout(2_500)

            cells = page.locator('#pane-side [role="gridcell"]')
            target = None
            for index in range(cells.count()):
                candidate = cells.nth(index)
                if not candidate.is_visible():
                    continue
                if expected_contact and expected_contact.casefold() not in candidate.inner_text().casefold():
                    continue
                target = candidate
                break
            if target is None:
                raise RuntimeError(
                    "WhatsApp did not resolve the recipient. Search manually first or pass --expected-contact."
                )
            target_text = target.inner_text().replace("\n", " | ")
            target.click(force=True)
            page.wait_for_timeout(2_500)

            header = page.locator('header[data-testid="conversation-header"]')
            header.wait_for(state="visible", timeout=15_000)
            contact = header.inner_text().replace("\n", " | ")
            if expected_contact and expected_contact.casefold() not in contact.casefold():
                raise RuntimeError(f"Opened contact does not match --expected-contact: {contact}")
            if not allow_duplicate and message.splitlines()[0] in page.locator("body").inner_text():
                raise RuntimeError("This post headline is already present in the chat; refusing a duplicate send.")

            attach = visible(page.locator('footer button[aria-label="Attach"], button[aria-label="Attach"]'))
            if attach is None:
                raise RuntimeError("WhatsApp attachment button was not found.")
            attach.click(force=True)
            photos = page.locator(
                '[role="menuitem"][aria-label="Photos & videos"], [aria-label="Photos & videos"]'
            ).first
            photos.wait_for(state="visible", timeout=10_000)
            # Use the file chooser opened by Photos & videos. Selecting a
            # hidden input directly can hit WhatsApp's image-only New sticker
            # input and silently turn the upload into a sticker.
            failures_before = page.locator('[data-testid="fail-container"]').count()
            with page.expect_file_chooser(timeout=10_000) as chooser_info:
                photos.click(force=True)
            chooser_info.value.set_files(str(image))
            page.wait_for_timeout(2_000)

            # The normal footer composer is also present while media is
            # loading. WhatsApp's media caption field keeps this same test id,
            # so use it rather than a generic textbox that can create a text
            # draft alongside the upload.
            caption = visible(page.locator('[data-testid="conversation-compose-box-input"]'))
            if caption is None:
                raise RuntimeError("WhatsApp media caption field was not found.")
            caption.click(force=True)
            for index, line in enumerate(message.split("\\n")):
                page.keyboard.insert_text(line)
                if index < len(message.split("\\n")) - 1:
                    page.keyboard.down("Shift")
                    page.keyboard.press("Enter")
                    page.keyboard.up("Shift")
            page.wait_for_timeout(500)

            # A media upload uses an aria label such as "Send 1 selected".
            # The generic Send button belongs to the ordinary text composer
            # and can turn the upload into a sticker/draft.
            send = visible(page.locator(
                '[role="button"][aria-label^="Send " i], button[aria-label^="Send " i]'
            ))
            if send is None:
                raise RuntimeError("WhatsApp media Send control was not found.")
            send.click(force=True)
            page.wait_for_timeout(15_000)
            failures_after = page.locator('[data-testid="fail-container"]').count()
            if failures_after > failures_before:
                raise RuntimeError("WhatsApp reported an image send failure.")
            if message.splitlines()[0] not in page.locator("body").inner_text():
                raise RuntimeError("Send completed without the post headline appearing in the chat.")
            return f"{target_text} -> {contact}"
        finally:
            page.close()
            browser.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Post date in YYYY-MM-DD format; defaults to today")
    parser.add_argument("--to", default="+12813239428", help="US recipient phone number")
    parser.add_argument("--expected-contact", help="Expected WhatsApp contact name; recommended for safety")
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--image", type=Path, help="Image to send; defaults to the date's rendered card")
    parser.add_argument("--send", action="store_true", help="Actually send through WhatsApp Web")
    parser.add_argument("--allow-duplicate", action="store_true", help="Allow a deliberate resend, such as replacing a sticker with a media image")
    args = parser.parse_args()

    post_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    post_file = args.output_dir / f"{post_date.isoformat()}.json"
    if post_file.is_file():
        post = json.loads(post_file.read_text(encoding="utf-8"))
    else:
        post = build_post(post_date, args.output_dir)
    image = args.image or (args.output_dir / f"{post_date.isoformat()}.png")
    if not image.is_file():
        raise SystemExit(f"Missing {image}. Run render_social_post.py first.")
    message = whatsapp_text(post)
    print(message)
    if not args.send:
        print("Preview only. Add --send to submit through WhatsApp Web.")
        return 0
    if not args.profile.is_dir():
        raise SystemExit(f"Chrome profile not found: {args.profile}")
    recipient = normalize_search_number(args.to)
    print("Sending through browser session...")
    print(send_post(args.profile, recipient, image, message, args.expected_contact, args.allow_duplicate))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
