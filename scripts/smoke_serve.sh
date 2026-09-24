#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_serve.sh — start the built loke binary and make one real HTTP request to each
# route. Fails if any request gets no response at all. (F10.36)
#
# Why this exists: on 2026-09-24 every unit test passed while /api/health, /api/models,
# /api/pipeline, /privacy, /savings and /pipeline each killed the server worker on their
# first request. The tests call handler functions directly, so none of them ever went
# through ooke's accept loop, and that was where the fault was. ooke's objects had been
# compiled by an older toke that declared tk_current_error as a plain global, and the
# first write to it zeroed the runtime's thread-local thunk. A handler test cannot see
# that class of failure. One real request per route can.
#
# It checks only that each route ANSWERS: some HTTP status comes back and not an empty
# reply. It does not judge the body. A 502 from /api/pipeline with no provider running
# is a correct answer and passes. A dropped connection fails.
#
# It serves a copy on port $SMOKE_PORT (default 11499), so it never collides with a
# loke already running on 11430.
#
#   scripts/smoke_serve.sh            # uses packages/browser/build/loke

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/packages/browser"
BIN="$SRC/build/loke"
PORT="${SMOKE_PORT:-11499}"

[ -x "$BIN" ] || { echo "smoke_serve: $BIN not built; run scripts/build_loke.sh" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_smoke.XXXXXX")
PID=
cleanup() { [ -n "$PID" ] && kill "$PID" 2>/dev/null; pkill -f "$WORK/loke" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

for d in pages templates static; do [ -d "$SRC/$d" ] && cp -R "$SRC/$d" "$WORK/"; done
cp "$BIN" "$WORK/loke"
sed -E "s/^([[:space:]]*port[[:space:]]*=).*/\1 $PORT/" "$SRC/ooke.toml" > "$WORK/ooke.toml"

( cd "$WORK" && exec ./loke > "$WORK/serve.log" 2>&1 ) &
PID=$!

up=0
for _ in $(seq 1 40); do
  if curl -s -o /dev/null -m 1 "http://127.0.0.1:$PORT/"; then up=1; break; fi
  sleep 0.25
done
if [ "$up" -ne 1 ]; then
  echo "smoke_serve: the server never answered on port $PORT" >&2
  tail -5 "$WORK/serve.log" >&2
  exit 1
fi

fail=0
probe() {  # $1 method, $2 path, $3 optional body
  local code
  if [ "$1" = POST ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 -X POST \
             -H 'Content-Type: application/json' -d "$3" "http://127.0.0.1:$PORT$2")
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "http://127.0.0.1:$PORT$2")
  fi
  if [ "$code" = "000" ]; then
    echo "  FAIL $1 $2: no response; the worker died or the connection dropped" >&2
    fail=1
  else
    echo "  ok   $1 $2 [$code]"
  fi
}

for r in health models settings savings tabs privacy; do probe GET "/api/$r"; done
probe POST /api/pipeline '{"text":"smoke test, no personal data"}'
for p in / /privacy /savings /pipeline /chat /setup; do probe GET "$p"; done

# GA2.6: a hostile page's "simple" POST (text/plain, so no preflight) must be refused
# before any handler does work. Loopback origins must still get through.
xorigin() {  # $1 path, $2 origin, $3 expect: refused|allowed
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 -X POST -H "Origin: $2" \
           -H 'Content-Type: text/plain' -d '{"text":"smoke test, no personal data"}' \
           "http://127.0.0.1:$PORT$1")
  if [ "$3" = refused ] && [ "$code" != 403 ]; then
    echo "  FAIL POST $1 from $2: got [$code], a cross-origin request must be refused (GA2.6)" >&2
    fail=1
  elif [ "$3" = allowed ] && { [ "$code" = 403 ] || [ "$code" = 000 ]; }; then
    echo "  FAIL POST $1 from $2: got [$code], a loopback origin must be let through" >&2
    fail=1
  else
    echo "  ok   POST $1 from $2 [$code]"
  fi
}
for r in pipeline settings approve privacy savings tabs; do
  xorigin "/api/$r" "https://evil.example" refused
done
xorigin /api/pipeline "http://127.0.0.1:$PORT" allowed

if [ "$fail" -ne 0 ]; then
  echo "smoke_serve: at least one route failed (F10.36, GA2.6)" >&2
  exit 1
fi
echo "smoke_serve: OK, every route answered"
