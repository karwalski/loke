#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_doctor.sh — run the built `loke doctor` against a recording stand-in for Ollama,
# Presidio and LLMLingua, and judge what it prints AND what reached the stand-in. (VM1.6e)
#
# Why: `loke doctor` printed "down — Ollama not running" while a stand-in Ollama answered
# on the configured URL. Every health check it runs was `http.get(http.client(url);path)`,
# which toke compiles as server ROUTE REGISTRATION (T-57), so no request was ever sent.
# This smoke fails if the report says an answering service is down, or if the report is
# right but the request did not arrive (a report that is right by accident is not a check).
#
# One stand-in (scripts/lib/http_recorder.py) answers all three, on a port the OS hands
# out; HOME is a throwaway directory, so the real ~/.loke is never read and no lock is
# needed. About a second.
#
#   scripts/smoke_doctor.sh        # uses build/trees/loke-cli/loke-cli

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/build/trees/loke-cli/loke-cli"
[ -x "$BIN" ] || { echo "smoke_doctor: $BIN not built; run scripts/build_trees.sh loke-cli" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_doctor_smoke.XXXXXX")
RPID=
cleanup() { [ -n "$RPID" ] && kill "$RPID" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

python3 "$ROOT/scripts/lib/http_recorder.py" "$WORK/rec.log" "$WORK/rec.port" &
RPID=$!
for _ in $(seq 1 50); do [ -s "$WORK/rec.port" ] && break; sleep 0.1; done
PORT=$(cat "$WORK/rec.port" 2>/dev/null)
[ -n "$PORT" ] || { echo "smoke_doctor: the recorder did not start" >&2; exit 1; }
URL="http://127.0.0.1:$PORT"

mkdir -p "$WORK/home/.loke"
printf '[providers]\nollama_url = "%s"\n\n[privacy]\npresidio_url = "%s"\nllmlingua_url = "%s"\n' \
  "$URL" "$URL" "$URL" > "$WORK/home/.loke/config.toml"

FAILS=0
check() { # $1 = label, $2 = 0 if it held
  if [ "$2" -eq 0 ]; then echo "  ok    $1"; else echo "  FAIL  $1"; FAILS=$((FAILS+1)); fi
}

echo "smoke_doctor: stand-in on $URL"

HOME="$WORK/home" "$BIN" doctor >"$WORK/up.txt" 2>&1; rc=$?
check "doctor exits 0 with every service answering" $([ "$rc" -eq 0 ]; echo $?)
check "the overall status is ok" $(grep -q "overall: ok" "$WORK/up.txt"; echo $?)
# Each subsystem's name is on one line and its status on the next.
status_of() { grep -A1 "^$1" "$WORK/up.txt" | tail -1 | sed 's/^ *//'; }
check "Ollama is reported ok, not down" $([ "$(status_of Ollama)" = "ok" ]; echo $?)
check "Presidio is reported ok" $([ "$(status_of Presidio)" = "ok" ]; echo $?)
check "LLMLingua is reported ok" $([ "$(status_of LLMLingua)" = "ok" ]; echo $?)
check "GET /api/tags reached the stand-in" $(grep -qs "^GET /api/tags" "$WORK/rec.log"; echo $?)
check "GET /health reached it twice (Presidio and LLMLingua)" $([ "$(grep -cs '^GET /health' "$WORK/rec.log" || true)" = 2 ]; echo $?)

# With nothing listening, the same config must report Ollama down and exit non-zero.
kill "$RPID" 2>/dev/null; wait "$RPID" 2>/dev/null; RPID=
HOME="$WORK/home" "$BIN" doctor >"$WORK/down.txt" 2>&1; rc=$?
check "with nothing listening, doctor exits non-zero" $([ "$rc" -ne 0 ]; echo $?)
check "and says Ollama is not running" $(grep -q "Ollama not running" "$WORK/down.txt"; echo $?)

if [ "$FAILS" -ne 0 ]; then
  echo "--- doctor, services up ---"; cat "$WORK/up.txt"
  echo "--- doctor, services down ---"; cat "$WORK/down.txt"
  echo "--- recorder log ---"; cat "$WORK/rec.log" 2>/dev/null
  echo "smoke_doctor: $FAILS check(s) FAILED"
  exit 1
fi
echo "smoke_doctor: all checks passed"
