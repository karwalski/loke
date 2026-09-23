#!/bin/bash
# toke_generate.sh — Generate toke code via API, check with tkc, submit feedback
# Usage: ./scripts/toke_generate.sh "description of function" [output.tk]

set -euo pipefail

API_URL="${TOKE_API_URL:-https://api.tokelang.dev}"
API_KEY="${TOKE_API_KEY:?Set TOKE_API_KEY from console.tokelang.dev}"
TKC="${TKC_PATH:-tkc}"

DESC="$1"
OUT="${2:-/tmp/toke_gen_$$.tk}"

echo ">>> Generating: $DESC"
RESP=$(curl -s -X POST "$API_URL/v1/generate" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $API_KEY" \
  -d "{\"description\": $(echo "$DESC" | jq -Rs .), \"max_tokens\": 512, \"temperature\": 0.2}")

SOURCE=$(echo "$RESP" | jq -r '.source // empty')
if [ -z "$SOURCE" ]; then
  echo "ERROR: $(echo "$RESP" | jq -r '.error // "no source returned"')"
  exit 1
fi

echo "$SOURCE" > "$OUT"
echo ">>> Generated: $OUT"
echo ">>> Source: $SOURCE"

# Check compilation
echo ">>> Checking with tkc..."
if $TKC --check "$OUT" 2>/dev/null; then
  echo ">>> COMPILES OK"
  COMPILES="yes"
else
  echo ">>> COMPILE FAILED"
  COMPILES="no"
fi

# Submit feedback
echo ">>> Submitting feedback (compiles=$COMPILES)..."
curl -s -X POST "$API_URL/v1/feedback" \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $API_KEY" \
  -d "{\"source\": $(echo "$SOURCE" | jq -Rs .), \"prompt\": $(echo "$DESC" | jq -Rs .), \"compiles\": \"$COMPILES\"}" > /dev/null

echo ">>> Done"
