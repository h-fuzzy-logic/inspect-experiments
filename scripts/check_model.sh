#!/usr/bin/env bash
# Check that a Gemini model answers, and how long it takes.
# Runs in a codespace only. Reads the key from $GOOGLE_API_KEY and never prints it.
# See docs/github-codespace.md.
#
# Usage:
#   scripts/check_model.sh list               # list available Gemini models (free)
#   scripts/check_model.sh gemini-3.6-flash   # send one short prompt (costs a fraction of a cent)
set -u

if [ "${CODESPACES:-}" != "true" ]; then
  echo "Run this in a codespace, not locally. See CLAUDE.md." >&2
  exit 1
fi
if [ -z "${GOOGLE_API_KEY:-}" ]; then
  echo "GOOGLE_API_KEY is not set. Add it as a Codespaces secret, then restart the codespace." >&2
  exit 1
fi

API=https://generativelanguage.googleapis.com/v1beta
model=${1:-}

if [ -z "$model" ]; then
  echo "Usage: $0 list | <model-name>" >&2
  exit 1
fi

if [ "$model" = "list" ]; then
  # Printed in the form Inspect expects for --model.
  curl -sS -m 30 -H "x-goog-api-key: $GOOGLE_API_KEY" "$API/models?pageSize=200" \
    | grep -o '"name": "models/gemini[^"]*"' \
    | sed 's/"name": "models\//google\//; s/"$//'
  exit
fi

# Accept the name with or without a google/ or models/ prefix.
model=${model#google/}
model=${model#models/}

echo "Sending one short prompt to $model (waits up to 180 seconds)..."
out=$(mktemp)
curl -sS -m 180 -o "$out" -w "HTTP %{http_code} in %{time_total}s\n" \
  -H "x-goog-api-key: $GOOGLE_API_KEY" -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Say hi"}]}]}' \
  "$API/models/$model:generateContent"
echo "curl exit code: $? (0 = reply received, 28 = timed out, 6 or 7 = couldn't reach Google)"
head -c 400 "$out"
echo
rm -f "$out"
