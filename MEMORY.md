# Project memory

## Identity and audience

- Business: Nightingale RN Academy LLC.
- Public website: `https://www.nightingalernacademy.com/`.
- Location language: based in Missouri City, Texas; serves Greater Houston and nearby communities including Sugar Land, Stafford, southwest Houston, Pearland, and Richmond.
- Public contact: `713-281-7770` and `nightingale.rn.academy@gmail.com`.
- Primary audiences: nursing graduates preparing for the NCLEX-RN, nursing/healthcare students, and healthcare professionals who need life-support training.

## Offers

- NCLEX-RN preparation: content review, clinical judgment, question analysis, and test-taking strategy.
- BLS: foundational CPR, ventilations, AED, recognition, and team response.
- ACLS: advanced cardiovascular emergency response, assessment, communication, and teamwork.
- PALS: pediatric assessment and response for respiratory emergencies, shock, and cardiac arrest.

## Current site architecture

- Static HTML with shared `site-pages.css` for detail pages.
- `index.html` is the main landing page and keeps its own inline CSS.
- `schedule.html` embeds the Tally scheduling form.
- `google-apps-script/LeadNotifier.gs` polls a connected Google Sheet and emails new leads to the public owner email.
- `social_content.py` generates date-specific caption/song/hashtag content and brand-safe HTML/JSON/Markdown output.
- `chatgpt_browser_content.py` uses Playwright with the Nightingale ChatGPT session `https://chatgpt.com/c/6afbe414-b624-83ea-8f24-7480abe6dc21`.
- `render_social_post.py` renders the HTML card with the website logo to a square PNG.
- `whatsapp_browser_send.py` can send the generated image and caption through a signed-in WhatsApp Web browser profile; preview is the default and `--send` is explicit.
- `run_daily_social_post.sh` chains generation, rendering, and preview/send for daily use; `SEND=1` is required for delivery.
- `robots.txt` allows crawling and points to `sitemap.xml`.
- All public HTML pages are listed in `sitemap.xml`.

## Product and marketing decisions

- Main conversion is a course-availability request; secondary conversions are phone and email clicks.
- The home page now uses the intent-led H1 `NCLEX Prep & Life Support Training in Missouri City, TX` and prominent schedule/phone actions.
- Course cards link to dedicated detail pages, and a lower-page CTA sends visitors to the short scheduling form.
- Pages use local, course-specific titles/descriptions, social metadata, and breadcrumb structured data.
- Homepage organization markup uses `EducationalOrganization` with public contact and service-area data.
- Site copy must remain accurate and should not invent prices, dates, reviews, pass rates, credentials, street address, provider affiliations, or outcome guarantees.

## Safe next improvements

1. Connect Google Search Console and Google Business Profile; keep name, phone, email, and location wording consistent.
2. Add real course dates, pricing, prerequisites, accepted provider details, policies, reviews, and instructor credentials only after verification.
3. Measure Tally submissions, phone clicks, email clicks, organic landing pages, and course-specific conversion rates.
4. Add real testimonials or outcomes with permission and attribution.
5. Use `social_content.py` plus `render_social_post.py` for the daily branded post; configure `OPENAI_API_KEY` for fresh AI copy, otherwise review the fallback copy.
6. Use `whatsapp_browser_send.py --send` only with a signed-in browser profile and an explicitly checked recipient.
7. Improve the form with course-specific preselection only if the Tally form supports a verified query/prefill mechanism.
8. Keep the sitemap `lastmod` date accurate whenever public pages materially change.

## Validation commands

```bash
python -m http.server 8000
python - <<'PY'
from pathlib import Path
from html.parser import HTMLParser
for path in sorted(Path('.').glob('*.html')):
    HTMLParser().feed(path.read_text())
    print('OK', path)
PY
```

The project has no JavaScript build pipeline or automated browser test suite. Use a browser and a real test submission before deploying.
