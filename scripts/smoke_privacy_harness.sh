#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_privacy_harness.sh — the privacy pipeline test harness over the REAL request path. (F3.9)
#
# It starts the BUILT loke binary and puts scripts/lib/http_recorder.py where loke expects
# Ollama, in `harness` mode: the recorder logs every request it receives and answers
# /api/generate with the prompt it was given, as a model that repeats its input would, and its
# NER answer names "Jane Citizen" only when the text holds that name. Then
# scripts/lib/privacy_harness.py sends POST /api/pipeline once for every pair of
#
#   - every built-in prompt template in core.privacy.template (read from its source), and
#   - every detector type the regex layer emits, plus a PERSON for the NER layer and a
#     control with no identifier in it,
#
# filling the template's parameters with raw data that carries the identifier. Each request is
# judged on what the RECORDER logged, never on what loke says it sent:
#
#   1. no raw identifier arrived in any request except the local NER layer's own /api/chat
#      (which is sent the text in clear, by design, to a loopback host);
#   2. the model's prompt carries a placeholder of the detector's type where the value was;
#   3. what the user is answered is the model's reply with every placeholder restored, byte
#      for byte (the echo makes the expected answer exact);
#   4. a request held for approval (RESTRICTED data) sent nothing to the model at all, and
#      after approval through POST /api/approve sends as in 1-3;
#   (and once, outside the matrix: an identifier in the caller's system_prompt did not reach
#      the model. It holds here only because nothing is sent as a system prompt; F3.9b.)
#   5. the guardian system prompt reached the model. EXPECTED TO FAIL today, recorded as XFAIL:
#      /api/pipeline sends Ollama no system prompt at all. F3.9a. An XPASS fails this script,
#      so the fix cannot land without the expectation and the backlog row being updated.
#
# loke dispatches to Ollama at the fixed address 127.0.0.1:11434, so this takes the fixed-port
# lock that smoke_e2e.sh and smoke_ui.sh hold, and refuses to start if that port is taken.
# loke itself serves on $SMOKE_PORT (default 11498). Throwaway HOME: no real key, no real
# audit trail. Nothing here contacts anything but loopback.
#
#   scripts/smoke_privacy_harness.sh                    # packages/browser/build/loke
#   LOKE_BIN=/path/to/mutant scripts/smoke_privacy_harness.sh
#   HARNESS_REPORT=cells.json HARNESS_RECORD=benchmarks/results/x.jsonl scripts/smoke_privacy_harness.sh
#
# What it does NOT cover: the Anthropic route (its endpoint is fixed to the real provider, so
# no stand-in can take its place; see tests/integration/test_system_prompt_disclosure.tk), the
# CLI paths (cli.ask, cli.proxy), the no-custody path, and detection recall, which is measured
# against the corpus in tests/integration/test_detection_recall.tk. Each detector type is
# exercised with one value the regex layer is known to detect.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/packages/browser"
BIN="${LOKE_BIN:-$SRC/build/loke}"
PORT="${SMOKE_PORT:-11498}"
OLLAMA_PORT=11434

[ -x "$BIN" ] || { echo "smoke_privacy_harness: $BIN not built; run scripts/build_loke.sh" >&2; exit 1; }

. "$ROOT/scripts/lib/fixedports_lock.sh"
acquire_fixedports || { echo "smoke_privacy_harness: could not get the fixed-port lock" >&2; exit 1; }
. "$ROOT/scripts/lib/port_owner.sh"
refuse_if_port_busy smoke_privacy_harness "$PORT" || { release_fixedports; exit 1; }
refuse_if_port_busy smoke_privacy_harness "$OLLAMA_PORT" || { release_fixedports; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_privharness.XXXXXX")
PIDS=""
cleanup() {
  for p in $PIDS; do kill "$p" 2>/dev/null; done
  pkill -f "$WORK/" 2>/dev/null
  rm -rf "$WORK"
  release_fixedports
}
trap cleanup EXIT INT TERM

for d in pages templates static; do [ -d "$SRC/$d" ] && cp -R "$SRC/$d" "$WORK/"; done
cp "$BIN" "$WORK/loke"
sed -E "s/^([[:space:]]*port[[:space:]]*=).*/\1 $PORT/" "$SRC/ooke.toml" > "$WORK/ooke.toml"
mkdir -p "$WORK/home"

# The models the router's static catalogue chooses for local text (as smoke_e2e.sh lists).
RECORDER_PORT=$OLLAMA_PORT RECORDER_MODELS="qwen2.5:7b,llama3:latest,gemma3:4b" \
  python3 "$ROOT/scripts/lib/http_recorder.py" "$WORK/model.log" "$WORK/model.port" harness \
  >/dev/null 2>&1 & PIDS="$PIDS $!"
RECPID=$!
( cd "$WORK" && HOME="$WORK/home" exec ./loke > "$WORK/serve.log" 2>&1 ) & PIDS="$PIDS $!"
LOKEPID=$!

up=0
for _ in $(seq 1 60); do
  if [ -s "$WORK/model.port" ] && curl -s -o /dev/null -m 1 "http://127.0.0.1:$PORT/api/health"; then up=1; break; fi
  sleep 0.25
done
if [ "$up" -ne 1 ]; then
  echo "smoke_privacy_harness: loke or the stand-in never came up" >&2
  tail -5 "$WORK/serve.log" >&2
  exit 1
fi
assert_port_owner smoke_privacy_harness "$PORT" "$LOKEPID" || exit 1
assert_port_owner smoke_privacy_harness "$OLLAMA_PORT" "$RECPID" || exit 1

python3 "$ROOT/scripts/lib/privacy_harness.py" \
  --loke "http://127.0.0.1:$PORT" \
  --bodies "$WORK/model.log.bodies" \
  --templates "$ROOT/packages/core/src/privacy/template.tk" \
  ${HARNESS_REPORT:+--report "$HARNESS_REPORT"} \
  ${HARNESS_RECORD:+--record "$HARNESS_RECORD"}
rc=$?
# For inspection: every request the stand-in received, kept when HARNESS_BODIES names a file.
[ -n "${HARNESS_BODIES:-}" ] && cp "$WORK/model.log.bodies" "$HARNESS_BODIES"
if [ "$rc" -ne 0 ]; then
  echo "smoke_privacy_harness: FAILED (loke log tail follows)" >&2
  tail -5 "$WORK/serve.log" >&2
fi
exit "$rc"
