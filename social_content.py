#!/usr/bin/env python3
"""Generate a branded daily social post and optionally send it through WhatsApp.

The generator is dependency-free. With OPENAI_API_KEY configured it asks the
OpenAI chat-completions endpoint for a fresh post; without a key it uses the
curated, brand-safe fallback library so a post can still be produced.
Sending is opt-in and requires WhatsApp Cloud API credentials.
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = ROOT / "social-posts"
BRAND = {
    "name": "Nightingale RN Academy",
    "legal_name": "Nightingale RN Academy LLC",
    "website": "https://www.nightingalernacademy.com/",
    "phone": "713-281-7770",
    "email": "nightingale.rn.academy@gmail.com",
    "location": "Missouri City, Texas",
    "service_area": "Greater Houston",
    "navy": "#061a3a",
    "blue": "#0b2a5c",
    "gold": "#e7b551",
    "text": "#cfd8ea",
    "logo": "../assets/nightingale-logo.png",
}

FALLBACK_POSTS = [
    {
        "topic": "BLS readiness",
        "headline": "Confidence starts before the emergency.",
        "caption": (
            "Your next clinical opportunity can depend on being ready before the call for help. "
            "Nightingale RN Academy provides BLS training in Missouri City for nursing and healthcare "
            "students and professionals across Greater Houston. Need training for school, work, or renewal? "
            "Tell us what you need and your preferred timing—we’ll follow up with current availability. "
            "Call 713-281-7770 or visit nightingalernacademy.com to get started."
        ),
        "song": "Good Day — Nappy Roots",
        "hashtags": ["#BLS", "#NursingStudents", "#HealthcareTraining", "#MissouriCityTX", "#GreaterHouston"],
        "image_prompt": "A focused healthcare student practicing CPR on a training manikin in a clean simulation classroom, navy and gold lighting, supportive professional mood.",
    },
    {
        "topic": "NCLEX clinical judgment",
        "headline": "Study with a plan. Test with purpose.",
        "caption": (
            "NCLEX-RN preparation is more than memorizing facts. Build a deliberate approach to clinical "
            "judgment, prioritization, question analysis, and safe nursing decisions with focused preparation "
            "from Nightingale RN Academy. Based in Missouri City and serving Greater Houston nursing graduates. "
            "Call 713-281-7770 or request course availability at nightingalernacademy.com."
        ),
        "song": "Unstoppable — Sia",
        "hashtags": ["#NCLEXPrep", "#FutureRN", "#NursingGraduate", "#NursingSchool", "#HoustonNurses"],
        "image_prompt": "Nursing graduates reviewing NCLEX-style questions together around a table, warm gold accents against a deep navy academic environment, confident and encouraging.",
    },
    {
        "topic": "ACLS teamwork",
        "headline": "Strong teams make every second count.",
        "caption": (
            "ACLS learning brings assessment, communication, decision-making, and team roles together. "
            "Nightingale RN Academy helps healthcare professionals prepare for structured cardiovascular "
            "emergency response in a focused learning environment in Missouri City. Ask about current ACLS "
            "availability for your school, employer, or renewal need. Call 713-281-7770 or visit our website."
        ),
        "song": "The Climb — Miley Cyrus",
        "hashtags": ["#ACLS", "#HealthcareProfessionals", "#ResuscitationTeam", "#ClinicalSkills", "#MissouriCity"],
        "image_prompt": "A diverse healthcare team practicing coordinated emergency response in a modern simulation lab, navy uniforms with subtle gold accents, energetic but professional.",
    },
    {
        "topic": "PALS preparation",
        "headline": "Be ready to respond when little patients need you most.",
        "caption": (
            "PALS preparation centers on a clear, systematic approach to pediatric assessment, respiratory "
            "emergencies, shock, and resuscitation teamwork. Nightingale RN Academy serves healthcare learners "
            "in Missouri City and across Greater Houston. Confirm the course your school or employer requires, "
            "then call 713-281-7770 or request PALS availability online."
        ),
        "song": "Brave — Sara Bareilles",
        "hashtags": ["#PALS", "#PediatricCare", "#NursingSkills", "#HealthcareEducation", "#GreaterHouston"],
        "image_prompt": "Healthcare learners practicing pediatric emergency assessment beside an infant training manikin, clean simulation classroom, navy and gold brand palette, calm and focused.",
    },
    {
        "topic": "local training",
        "headline": "Your next credential starts with one clear step.",
        "caption": (
            "Searching for healthcare training close to home? Nightingale RN Academy is based in Missouri City "
            "and serves learners from Sugar Land, Stafford, southwest Houston, Pearland, Richmond, and nearby "
            "communities. Explore NCLEX-RN prep, BLS, ACLS, and PALS training, then tell us your preferred timing. "
            "We’ll follow up with current availability. Call 713-281-7770 or visit nightingalernacademy.com."
        ),
        "song": "On Top of the World — Imagine Dragons",
        "hashtags": ["#MissouriCityTX", "#HealthcareTraining", "#NursingCareer", "#BLS", "#NCLEXPrep"],
        "image_prompt": "Professional healthcare education scene in a welcoming Missouri City training center, nursing student with notebook and CPR equipment, deep navy background and warm gold highlights.",
    },
]


def normalize_phone(value: str) -> str:
    """Return a US 10-digit number as WhatsApp Cloud API E.164 digits."""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 10:
        return "1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return digits
    raise ValueError("WhatsApp recipient must be a US 10- or 11-digit number.")


def previous_headlines(output_dir: Path) -> list[str]:
    headlines: list[str] = []
    if not output_dir.exists():
        return headlines
    for path in sorted(output_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        headline = data.get("headline")
        if isinstance(headline, str) and headline:
            headlines.append(headline)
    return headlines[-30:]


def fallback_post(post_date: dt.date, output_dir: Path) -> dict[str, Any]:
    used = set(previous_headlines(output_dir))
    start = post_date.toordinal() % len(FALLBACK_POSTS)
    candidates = FALLBACK_POSTS[start:] + FALLBACK_POSTS[:start]
    selected = next((post for post in candidates if post["headline"] not in used), candidates[0])
    return {**selected, "generated_by": "curated fallback"}


def ai_prompt(post_date: dt.date, used: list[str]) -> str:
    history = "\n".join(f"- {headline}" for headline in used) or "- None yet"
    return f"""Create one original social-media post for {BRAND['name']} for {post_date.isoformat()}.

Brand facts (use only these facts):
- Based in {BRAND['location']}; serves {BRAND['service_area']}.
- Offers NCLEX-RN preparation, BLS, ACLS, and PALS training.
- Public phone: {BRAND['phone']}.
- Website: {BRAND['website']}
- Brand colors: navy {BRAND['navy']}, blue {BRAND['blue']}, gold {BRAND['gold']}.

Audience: nursing graduates, nursing students, healthcare students, and healthcare professionals.
Goal: earn a genuine course-availability inquiry without hype.
Do not invent prices, class dates, reviews, pass rates, credentials, provider affiliations, addresses, or guaranteed outcomes. Remind readers to confirm exact requirements with their school or employer when relevant. Keep the tone warm, concise, and professional. Make the post distinctly different from these recent headlines:
{history}

Return JSON only with exactly these keys:
headline (short), caption (80-130 words), song (song title and artist only), hashtags (array of 4-7 hashtags), image_prompt (one sentence for a square branded visual).
"""


def call_openai(prompt: str) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    body = {
        "model": model,
        "temperature": 0.9,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": "You write accurate, conversion-focused social content for a local healthcare education business."},
            {"role": "user", "content": prompt},
        ],
    }
    request = Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"AI request failed: {exc}") from exc
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise RuntimeError("AI response did not contain text")
    content = content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE | re.DOTALL).strip()
    result = json.loads(content)
    required = {"headline", "caption", "song", "hashtags", "image_prompt"}
    if not required.issubset(result):
        raise RuntimeError("AI response is missing required post fields")
    if not isinstance(result["hashtags"], list):
        raise RuntimeError("AI hashtags must be an array")
    result["generated_by"] = f"OpenAI ({model})"
    return result


def build_post(post_date: dt.date, output_dir: Path) -> dict[str, Any]:
    try:
        post = call_openai(ai_prompt(post_date, previous_headlines(output_dir)))
    except (RuntimeError, KeyError, json.JSONDecodeError) as exc:
        print(f"AI generation unavailable; using brand-safe fallback: {exc}", file=sys.stderr)
        post = fallback_post(post_date, output_dir)
    post["date"] = post_date.isoformat()
    post["brand"] = BRAND
    post["hashtags"] = [str(tag) for tag in post["hashtags"]]
    return post


def whatsapp_text(post: dict[str, Any]) -> str:
    hashtags = " ".join(post["hashtags"])
    return "\n\n".join(
        [
            f"{post['headline']}\n\n{post['caption']}",
            f"Song suggestion: {post['song']}",
            hashtags,
        ]
    )


def render_markdown(post: dict[str, Any]) -> str:
    return f"""# {post['headline']}

**Date:** {post['date']}  
**Topic:** {post.get('topic', 'daily brand post')}  
**Generated by:** {post['generated_by']}

## Caption

{post['caption']}

## Song suggestion

{post['song']}

> Check the platform’s commercial audio library and usage rights before using a song for business content.

## Hashtags

{' '.join(post['hashtags'])}

## Visual direction

{post['image_prompt']}

## WhatsApp-ready message

```text
{whatsapp_text(post)}
```
"""


def render_html(post: dict[str, Any]) -> str:
    e = html.escape
    hashtags = " ".join(post["hashtags"])
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(post['headline'])} | {e(BRAND['name'])}</title>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
<style>
* {{ box-sizing:border-box; }}
body {{ margin:0; min-height:100vh; display:grid; place-items:center; background:#e8edf5; font-family:Inter,Arial,sans-serif; }}
.post {{ width:min(100vw,1080px); aspect-ratio:1; padding:7.5%; display:flex; flex-direction:column; justify-content:space-between; color:#fff; overflow:hidden; background:radial-gradient(circle at 88% 10%,rgba(231,181,81,.3),transparent 25%),linear-gradient(145deg,{BRAND['navy']},{BRAND['blue']}); }}
.topline {{ color:{BRAND['gold']}; font-size:clamp(12px,1.5vw,18px); font-weight:700; letter-spacing:.16em; text-transform:uppercase; }}
.logo {{ width:clamp(76px,12vw,135px); height:auto; filter:drop-shadow(0 12px 20px rgba(0,0,0,.24)); }}
h1 {{ max-width:850px; margin:10% 0 3%; font:700 clamp(44px,7.2vw,88px)/.95 'Cormorant Garamond',Georgia,serif; }}
.caption {{ max-width:750px; color:{BRAND['text']}; font-size:clamp(14px,1.7vw,21px); line-height:1.5; }}
.bottom {{ display:flex; justify-content:space-between; align-items:end; gap:24px; color:{BRAND['text']}; font-size:clamp(12px,1.4vw,17px); }}
.cta {{ color:{BRAND['gold']}; font-weight:700; }}
.hashtags {{ max-width:48%; text-align:right; }}
@media(max-width:600px) {{ .post {{ width:100vw; }} .bottom {{ display:block; }} .hashtags {{ max-width:none; margin-top:12px; text-align:left; }} }}
</style>
</head>
<body>
<main class="post">
  <div>
    <div class="topline">{e(BRAND['location'])} · {e(BRAND['service_area'])}</div>
    <img class="logo" src="{e(BRAND['logo'])}" alt="{e(BRAND['name'])} logo">
    <h1>{e(post['headline'])}</h1>
    <p class="caption">{e(post['caption'])}</p>
  </div>
  <footer class="bottom">
    <div><div class="cta">Request course availability</div><div>{e(BRAND['phone'])} · nightingalernacademy.com</div></div>
    <div class="hashtags">{e(hashtags)}</div>
  </footer>
</main>
</body>
</html>
"""


def send_whatsapp(message: str, to: str) -> dict[str, Any]:
    token = os.environ.get("WHATSAPP_ACCESS_TOKEN")
    phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID")
    if not token or not phone_number_id:
        raise RuntimeError("Set WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID before using --send")
    recipient = normalize_phone(to)
    graph_version = os.environ.get("WHATSAPP_GRAPH_VERSION", "v20.0")
    endpoint = f"https://graph.facebook.com/{graph_version}/{phone_number_id}/messages"
    body = {
        "messaging_product": "whatsapp",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": True, "body": message},
    }
    request = Request(
        endpoint,
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"WhatsApp API returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"WhatsApp request failed: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", help="Post date in YYYY-MM-DD format; defaults to today")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force", action="store_true", help="Regenerate even if this date already has a post")
    parser.add_argument("--send", action="store_true", help="Send the generated text through WhatsApp Cloud API")
    parser.add_argument("--to", default=os.environ.get("WHATSAPP_TO", "+12813239428"), help="US recipient number")
    args = parser.parse_args()

    post_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    stem = args.output_dir / post_date.isoformat()
    post_file = stem.with_suffix(".json")
    if post_file.is_file() and not args.force:
        post = json.loads(post_file.read_text(encoding="utf-8"))
        print(f"Using existing post for {post_date.isoformat()}; pass --force to regenerate.", file=sys.stderr)
    else:
        post = build_post(post_date, args.output_dir)
    post_file.write_text(json.dumps(post, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (stem.with_suffix(".md")).write_text(render_markdown(post), encoding="utf-8")
    (stem.with_suffix(".html")).write_text(render_html(post), encoding="utf-8")

    message = whatsapp_text(post)
    print(message)
    print(f"\nSaved: {stem}.json, {stem}.md, {stem}.html")
    if args.send:
        result = send_whatsapp(message, args.to)
        print(f"WhatsApp sent to {normalize_phone(args.to)}. Message id: {result.get('messages', [{}])[0].get('id', 'unknown')}")
    else:
        print("Not sent. Add WhatsApp Cloud API credentials and rerun with --send when ready.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
