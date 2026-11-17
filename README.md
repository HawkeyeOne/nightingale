# Nightingale RN Academy website

Static marketing site for **Nightingale RN Academy LLC**, based in Missouri City, Texas and serving healthcare learners across Greater Houston.

## Business goals

- Attract local searches for NCLEX-RN preparation, BLS, ACLS, and PALS training.
- Turn visitors into course inquiries through the scheduling form, phone, and email.
- Explain which course fits a learner’s school, employer, clinical, or exam-preparation need.
- Build trust with useful, accurate nursing and course information without promising outcomes the academy cannot guarantee.

## Site structure

- `index.html` — primary landing page and course overview.
- `bls-course.html`, `acls-course.html`, `pals-course.html` — course detail and inquiry pages.
- `nclex-prep.html` — NCLEX-RN preparation page.
- `schedule.html` — Tally scheduling form and primary lead-conversion page.
- `houston-area.html` — Missouri City/Greater Houston local landing page.
- `nursing-career.html` — Texas RN pathway and official Houston-area program resources.
- `faq.html` — course, eligibility, prerequisite, and scheduling questions.
- `site-pages.css` — shared styles for detail pages; the home page has its own inline styles.
- `assets/` — logo and course photography.
- `google-apps-script/LeadNotifier.gs` — optional Google Sheets lead-notification automation.
- `social_content.py` — daily branded post generator with ChatGPT-browser, API, and safe fallback modes.
- `chatgpt_browser_content.py` — uses Playwright and a signed-in ChatGPT website session to generate fresh JSON content.
- `chatgpt_browser_image.py` — asks that same ChatGPT session to generate and download the actual image asset.
- `render_social_post.py` — fallback renderer for a branded HTML card when ChatGPT image generation is disabled.
- `whatsapp_browser_send.py` — preview-first WhatsApp Web sender for the generated image and caption.
- `run_daily_social_post.sh` — daily generate/render/send wrapper; sending requires explicit `SEND=1`.
- `MEMORY.md` — maintained project context, business facts, guardrails, and next-step priorities.
- `robots.txt`, `sitemap.xml` — crawl guidance and indexable URLs.

## Conversion and SEO work included

- Intent-focused home-page title, description, H1, local wording, and social metadata.
- Clear above-the-fold availability and phone CTAs, course-detail links, and a lower-page conversion band.
- Course cards now link directly to detailed pages instead of relying on title links alone.
- Educational-organization structured data includes public contact details and service area.
- Detail pages include breadcrumb, robots, theme-color, Open Graph, and Twitter metadata.
- Shared keyboard focus styles improve accessibility for links, buttons, and FAQ controls.
- Sitemap `lastmod` values reflect the latest site update.

## Run locally

This is a static site. From the project directory, use any static server, for example:

```bash
python3 -m http.server 8000
```

Then open <http://localhost:8000/>.

`main.py` is only the scaffold for the Python project and is not required to serve the website.

## Daily WhatsApp content

Generate a date-specific post, render its branded card, and preview the WhatsApp message:

```bash
python3 social_content.py --date 2026-11-17 --chatgpt-browser --profile /path/to/signed-in-profile --force
python3 chatgpt_browser_image.py --date 2026-11-17 --profile /path/to/signed-in-profile
python3 whatsapp_browser_send.py --date 2026-11-17 --image social-posts/2026-11-17-chatgpt.png --to +12813239428 --expected-contact "Contact Name"
```

For a daily runner (ChatGPT website generation is the default; still preview-only unless `SEND=1`):

```bash
CHATGPT_BROWSER=1 WHATSAPP_EXPECTED_CONTACT="Contact Name" BROWSER_PROFILE_DIR=/path/to/signed-in-profile ./run_daily_social_post.sh
```

The preferred workflow uses `--chatgpt-browser`, `chatgpt_browser_image.py`, Playwright, and a signed-in ChatGPT website profile. The default Nightingale session is `https://chatgpt.com/c/6afbe414-b624-83ea-8f24-7480abe6dc21`; override it with `CHATGPT_URL` if needed. This downloads a real ChatGPT-generated image, not a sticker and not only an HTML screenshot. The API mode uses `OPENAI_API_KEY`/`OPENAI_MODEL`; if neither is available, the brand-safe fallback topics are used. Rendering and browser sending require Playwright in the Python environment. It writes JSON, Markdown, HTML, and PNG files under `social-posts/`; rerunning a date reuses the existing post unless `--force` is passed. The HTML card uses the website logo and navy/blue/gold palette. The song is a suggestion only; verify commercial audio availability and rights before posting.

For an actual browser send, WhatsApp Web must already be signed in to a Chrome profile. Use `--send` only after checking the preview and recipient:

```bash
python3 whatsapp_browser_send.py --date 2026-11-17 --to +12813239428 --expected-contact "Contact Name" --profile /path/to/signed-in-profile --send
```

Set `CHATGPT_BROWSER=0` only if you intentionally want the API/fallback generator instead. The sender refuses duplicate headlines in the chat and never sends by default. Do not commit browser profiles, cookies, tokens, private messages, or generated worktrees.

## Lead form setup

The scheduling page embeds a Tally form. Follow `google-apps-script/README.md` to configure the optional Google Sheets notifier. Do not commit credentials, private form data, or generated worktrees.

## Launch checklist

1. Verify the production domain, phone number, email address, Tally embed, and course requirements.
2. Submit a test inquiry and confirm that the owner receives it once.
3. Check every primary CTA on mobile and desktop.
4. Submit `sitemap.xml` in Google Search Console and verify indexing.
5. Create/optimize the Google Business Profile with the same public business details.
6. Add only real reviews, credentials, class dates, pricing, policies, and social links when available.
7. Track form submissions, phone clicks, email clicks, landing-page traffic, and search queries.

## Content guardrails

The site intentionally avoids invented testimonials, pass rates, prices, class dates, street addresses, provider affiliations, or guaranteed exam/licensure/employment outcomes. Confirm current requirements with the relevant school, employer, credentialing body, or Texas Board of Nursing before publishing specifics.
