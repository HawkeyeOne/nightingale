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
5. Improve the form with course-specific preselection only if the Tally form supports a verified query/prefill mechanism.
6. Keep the sitemap `lastmod` date accurate whenever public pages materially change.

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
