#!/usr/bin/env python3
"""Generate one Nightingale social post through the ChatGPT website UI."""

from __future__ import annotations

import datetime as dt
import json
import re
import time
from pathlib import Path
from typing import Any

from social_content import BRAND, ai_prompt, previous_headlines


ASSISTANT_SELECTORS = (
    '[data-message-author-role="assistant"]',
    '[data-testid^="conversation-turn-"][data-message-author-role="assistant"]',
    'main [data-markdown-text-style="assistant-message"]',
)


def _visible(locator):
    for index in range(locator.count()):
        candidate = locator.nth(index)
        try:
            if candidate.is_visible():
                return candidate
        except Exception:
            continue
    return None


def _assistant_texts(page) -> list[str]:
    for selector in ASSISTANT_SELECTORS:
        locator = page.locator(selector)
        if locator.count():
            values = []
            for index in range(locator.count()):
                text = locator.nth(index).inner_text().strip()
                if text:
                    values.append(text)
            if values:
                return values
    return []


def _composer(page):
    return _visible(page.locator(
        'textarea[data-testid="prompt-textarea"], '
        'textarea[placeholder*="ask chatgpt" i], '
        '[contenteditable="true"][role="textbox"], '
        '[contenteditable="true"]'
    ))


def _send_button(page):
    return _visible(page.locator(
        'button[data-testid="send-button"], '
        'button[aria-label="Send" i], '
        'button[aria-label="Send prompt" i]'
    ))


def _wait_for_response(page, before: list[str], timeout_seconds: int) -> str:
    before_latest = before[-1] if before else ""
    deadline = time.monotonic() + timeout_seconds
    stable_polls = 0
    last = ""
    while time.monotonic() < deadline:
        messages = _assistant_texts(page)
        latest = messages[-1] if messages else ""
        stop = _visible(page.locator(
            'button[aria-label*="stop" i], button:has-text("Stop generating"), '
            'button:has-text("Stop response")'
        ))
        if latest and latest != before_latest and len(latest) >= 80:
            if latest == last:
                stable_polls += 1
            else:
                stable_polls = 0
            # A response that stays unchanged while the Stop control is gone is
            # complete. Two one-second stable polls avoid parsing streamed JSON.
            if stop is None and stable_polls >= 2:
                return latest
        last = latest
        page.wait_for_timeout(1_000)
    raise RuntimeError("ChatGPT did not return a stable social post before the timeout")


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned, flags=re.I | re.S).strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, re.S)
        if not match:
            raise RuntimeError("ChatGPT response did not contain a JSON object")
        value = json.loads(match.group(0))
    required = {"headline", "caption", "song", "hashtags", "image_prompt"}
    if not isinstance(value, dict) or not required.issubset(value):
        raise RuntimeError("ChatGPT response is missing a required post field")
    if not isinstance(value["hashtags"], list):
        raise RuntimeError("ChatGPT hashtags must be an array")
    return value


def generate_chatgpt_post(
    post_date: dt.date,
    output_dir: Path,
    profile: Path,
    *,
    chatgpt_url: str = "https://chatgpt.com/c/6afbe414-b624-83ea-8f24-7480abe6dc21",
    timeout_seconds: int = 180,
) -> dict[str, Any]:
    """Open ChatGPT in a saved browser profile, ask for JSON, and parse it."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("Playwright is required for ChatGPT website generation") from exc

    prompt = ai_prompt(post_date, previous_headlines(output_dir))
    prompt += "\nReturn JSON only. Do not use markdown fences or extra commentary."

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch_persistent_context(
            str(profile),
            executable_path="/usr/bin/google-chrome",
            headless=False,
            viewport={"width": 1440, "height": 1000},
            ignore_default_args=["--enable-automation"],
            args=["--disable-blink-features=AutomationControlled", "--window-position=-10000,-10000"],
        )
        page = browser.new_page()
        try:
            page.goto(chatgpt_url, wait_until="domcontentloaded", timeout=60_000)
            composer = None
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline and composer is None:
                composer = _composer(page)
                if composer is None:
                    page.wait_for_timeout(500)
            if composer is None:
                body = page.locator("body").inner_text()[:500]
                raise RuntimeError(f"ChatGPT composer was not available; check browser sign-in. Page says: {body}")
            before = _assistant_texts(page)
            composer.fill(prompt)
            send = None
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline and send is None:
                send = _send_button(page)
                if send is None:
                    page.wait_for_timeout(200)
            if send is None:
                raise RuntimeError("ChatGPT send button was not available")
            send.click()
            result = _parse_json(_wait_for_response(page, before, timeout_seconds))
            result["date"] = post_date.isoformat()
            result["brand"] = BRAND
            result["generated_by"] = "ChatGPT website via Playwright"
            result["hashtags"] = [str(tag) for tag in result["hashtags"]]
            return result
        finally:
            page.close()
            browser.close()
