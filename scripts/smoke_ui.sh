#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_ui.sh — moke's chat page in headless Chrome, against the whole stack (GA3, RV1.4).
#
# Starts the same stack as smoke_e2e.sh (a recording fake Ollama, loke and moke, each with a
# throwaway HOME) and runs tests/ui/chat_ga3.json through scripts/lib/ui_check.mjs. Those
# checks exercise the GA3 behaviours in a real browser: the warning levels (with the timers
# actually run), the simple/advanced view, the pre-send estimate, cancelling a live request,
# thumbs-down on a real reply, and the sensitivity tooltip. The GA3 rows had been Done
# without ever being run in a browser.
#
# Needs node and Google Chrome. If either is missing, or one of the ports is taken, it says
# SKIPPED and exits 0, loudly, and does not count as a pass.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOKE_BIN="$ROOT/packages/browser/build/loke"
MOKE_BIN="$ROOT/build/trees/moke/moke"
command -v node >/dev/null || { echo "smoke_ui: SKIPPED — node is not installed" >&2; exit 0; }
[ -x "${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}" ] || { echo "smoke_ui: SKIPPED — Google Chrome not found" >&2; exit 0; }
for b in "$LOKE_BIN" "$MOKE_BIN"; do
  [ -x "$b" ] || { echo "smoke_ui: $b not built" >&2; exit 1; }
done
. "$ROOT/scripts/lib/fixedports_lock.sh"
trap release_fixedports EXIT INT TERM
acquire_fixedports || { echo "smoke_ui: could not get the fixed-port lock" >&2; exit 1; }
for port in 11430 11432 11434; do
  if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
    echo "smoke_ui: SKIPPED — port $port is in use, and this test must own it. Nothing was run." >&2
    exit 0
  fi
done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_ui.XXXXXX")
PIDS=""
cleanup() {
  for p in $PIDS; do kill "$p" 2>/dev/null; done
  pkill -9 -f "$WORK/" 2>/dev/null
  rm -rf "$WORK"
  release_fixedports
}
trap cleanup EXIT INT TERM

mkdir -p "$WORK/lk/home" "$WORK/mk/home"
( cd "$ROOT/packages/browser" && cp -R pages templates static ooke.toml "$WORK/lk/" )
cp "$LOKE_BIN" "$WORK/lk/loke"
( cd "$ROOT/packages/moke" && cp -R pages templates static ooke.toml "$WORK/mk/" )
cp "$MOKE_BIN" "$WORK/mk/moke"

SEEN="$WORK/model_saw.log"; : > "$SEEN"
python3 "$ROOT/scripts/lib/fake_ollama.py" "$SEEN" >/dev/null 2>&1 & PIDS="$PIDS $!"
( cd "$WORK/lk" && HOME="$WORK/lk/home" exec "$WORK/lk/loke" > "$WORK/lk.log" 2>&1 ) & PIDS="$PIDS $!"
( cd "$WORK/mk" && HOME="$WORK/mk/home" exec "$WORK/mk/moke" > "$WORK/mk.log" 2>&1 ) & PIDS="$PIDS $!"

for _ in $(seq 1 40); do
  nc -z -G 1 127.0.0.1 11430 2>/dev/null && nc -z -G 1 127.0.0.1 11432 2>/dev/null \
    && nc -z -G 1 127.0.0.1 11434 2>/dev/null && break
  sleep 0.25
done
# The loop above gives up silently after ten seconds. On a loaded machine (the gate runs this
# straight after a full build) a server could still be starting, and then Chrome loaded its own
# connection-error page and every GA3 check ran against that: "showWarning is not defined",
# "setViewMode is not defined", null elements. So wait for the pages themselves to answer 200,
# for up to a minute, and fail naming the one that did not rather than judge an error page.
for url in http://127.0.0.1:11432/chat http://127.0.0.1:11430/savings http://127.0.0.1:11430/chat; do
  up=0
  for _ in $(seq 1 120); do
    [ "$(curl -s -o /dev/null -m 5 -w '%{http_code}' "$url")" = "200" ] && { up=1; break; }
    sleep 0.5
  done
  [ "$up" -eq 1 ] || { echo "smoke_ui: FAILED — $url never answered 200, so no check was run against it" >&2; exit 1; }
done


node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11432/chat" "${UI_CHECKS:-$ROOT/tests/ui/chat_ga3.json}"
rc=$?
# GA1.5c: moke's savings ledger and view, judged against loke's own reply to a real request.
if [ "$rc" -eq 0 ] && [ -z "${UI_CHECKS:-}" ]; then
  node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11432/chat" "$ROOT/tests/ui/savings_ga15c.json"
  rc=$?
fi
# DA1.5: loke's savings page, after the chat checks above have sent requests through it.
if [ "$rc" -eq 0 ] && [ -z "${UI_CHECKS:-}" ]; then
  node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11430/savings" "$ROOT/tests/ui/savings_da15.json"
  rc=$?
fi
# GA5.26: loke's own chat, a restricted prompt, the approval page, and back.
if [ "$rc" -eq 0 ] && [ -z "${UI_CHECKS:-}" ]; then
  node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11430/chat" "$ROOT/tests/ui/approve_ga526.json"
  rc=$?
fi
# MK19.1: moke's dataset pages read the one store (static/data) in a real browser — the
# landing page's cards and the upload page's list, and a Load from each.
if [ "$rc" -eq 0 ] && [ -z "${UI_CHECKS:-}" ]; then
  node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11432/upload" "$ROOT/tests/ui/datasets_mk191.json"
  rc=$?
fi
[ "$rc" -eq 0 ] && echo "smoke_ui: OK — every GA3 check passed in a real browser" || echo "smoke_ui: FAILED" >&2
exit $rc
