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
}
trap cleanup EXIT INT TERM

mkdir -p "$WORK/lk/home" "$WORK/mk/home" "$WORK/mk/data"
( cd "$ROOT/packages/browser" && cp -R pages templates static ooke.toml "$WORK/lk/" )
cp "$LOKE_BIN" "$WORK/lk/loke"
( cd "$ROOT/packages/moke" && cp -R pages templates static ooke.toml "$WORK/mk/" && cp -R data/csv "$WORK/mk/data/" )
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


node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11432/chat" "${UI_CHECKS:-$ROOT/tests/ui/chat_ga3.json}"
rc=$?
# DA1.5: loke's savings page, after the chat checks above have sent requests through it.
if [ "$rc" -eq 0 ] && [ -z "${UI_CHECKS:-}" ]; then
  node "$ROOT/scripts/lib/ui_check.mjs" "http://127.0.0.1:11430/savings" "$ROOT/tests/ui/savings_da15.json"
  rc=$?
fi
[ "$rc" -eq 0 ] && echo "smoke_ui: OK — every GA3 check passed in a real browser" || echo "smoke_ui: FAILED" >&2
exit $rc
