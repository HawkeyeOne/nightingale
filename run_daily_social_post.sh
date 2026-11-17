#!/usr/bin/env bash
# Generate one branded post every day. Sending is opt-in: set SEND=1.
set -Eeuo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${PYTHON:-python3}"
POST_DATE="${POST_DATE:-$(date +%F)}"
RECIPIENT="${WHATSAPP_TO:-+12813239428}"
PROFILE="${BROWSER_PROFILE_DIR:-$ROOT/.browser-profile}"
EXPECTED_CONTACT="${WHATSAPP_EXPECTED_CONTACT:-}"

cd "$ROOT"
GEN_ARGS=(--date "$POST_DATE")
if [[ "${CHATGPT_BROWSER:-1}" == "1" ]]; then
  GEN_ARGS+=(--chatgpt-browser --profile "$PROFILE")
fi
"$PYTHON" social_content.py "${GEN_ARGS[@]}"
"$PYTHON" render_social_post.py --date "$POST_DATE"

SEND_ARGS=(
  --date "$POST_DATE"
  --to "$RECIPIENT"
  --profile "$PROFILE"
)
if [[ -n "$EXPECTED_CONTACT" ]]; then
  SEND_ARGS+=(--expected-contact "$EXPECTED_CONTACT")
fi
if [[ "${SEND:-0}" == "1" ]]; then
  SEND_ARGS+=(--send)
fi
"$PYTHON" whatsapp_browser_send.py "${SEND_ARGS[@]}"
