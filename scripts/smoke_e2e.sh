#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_e2e.sh — the whole request path, end to end: moke -> loke -> a model -> back.
#
# It runs a fake Ollama (scripts/lib/fake_ollama.py) that records every request, then loke,
# then moke, each from a scratch copy with a throwaway HOME, so no real provider key and no
# real audit trail is touched. It POSTs a prompt containing a synthetic email address to
# moke's /api/pipeline and asserts three things:
#
#   1. the request succeeds end to end;
#   2. the MODEL never received the email address, only a placeholder;
#   3. the USER got the email address back, restored by loke.
#
# The first time this path ran at all was 2026-09-25. Before that, moke called `http.post`,
# which registers a server route rather than making a request, and moke believed loke was
# down whenever it was up (SO_REUSEPORT fooled the port probe, and process.wait read exit
# code 0 as failure).
#
# The components talk to each other on fixed ports (loke 11430, moke 11432, Ollama 11434).
# If any is taken, this script says so and exits 0 without running: it does not touch
# something you have running. It reports that as SKIPPED, loudly, and not as a pass.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOKE_BIN="$ROOT/packages/browser/build/loke"
MOKE_BIN="$ROOT/build/trees/moke/moke"
for b in "$LOKE_BIN" "$MOKE_BIN"; do
  [ -x "$b" ] || { echo "smoke_e2e: $b not built" >&2; exit 1; }
done
for port in 11430 11432 11434; do
  if nc -z -G 1 127.0.0.1 "$port" 2>/dev/null; then
    echo "smoke_e2e: SKIPPED — port $port is in use, and this test must own it. Nothing was run." >&2
    exit 0
  fi
done

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_e2e.XXXXXX")
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

EMAIL="e2e.probe.$$@example.com"
OUT=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"prompt\":\"summarise: contact $EMAIL\",\"session_id\":\"e2e\",\"dataset_name\":\"demo\"}" \
        http://127.0.0.1:11432/api/pipeline)

fail=0
ok=$(printf '%s' "$OUT" | python3 -c 'import json,sys
try: d=json.load(sys.stdin); print("true" if d.get("ok") else "false"); print(d.get("response") or d.get("error") or "", file=sys.stderr)
except Exception: print("unparseable")' 2>"$WORK/resp.txt")
resp=$(cat "$WORK/resp.txt")

if [ "$ok" = "true" ]; then echo "  ok   moke -> loke -> model -> moke succeeded"
else echo "  FAIL the request did not succeed end to end: $resp" >&2; fail=1; fi

if [ ! -s "$SEEN" ]; then
  echo "  FAIL the model received no request at all" >&2; fail=1
elif grep -q "$EMAIL" "$SEEN"; then
  echo "  FAIL the MODEL received the email address in clear — the privacy filter did not run" >&2; fail=1
else
  echo "  ok   the model saw only: $(grep -o '\[EMAIL_[0-9a-f]*_[0-9]*\]' "$SEEN" | head -1)"
fi

case "$resp" in
  *"$EMAIL"*) echo "  ok   the user got the email address back, restored" ;;
  *) echo "  FAIL the response did not restore the placeholder: $resp" >&2; fail=1 ;;
esac

# DA1.7: one disclosure_log row for the dispatch, completed, whose bytes_body is the exact
# octet count of the body the model received (spec acceptance A7), and which holds the
# address in no column (A10).
DB="$WORK/lk/home/.loke/loke.db"
dl() { sqlite3 "$DB" "$1" 2>/dev/null; }
sent_bytes=$(python3 -c 'import sys
for line in open(sys.argv[1],encoding="utf-8"):
    if line.startswith("/api/generate "): print(len(line[len("/api/generate "):].rstrip("\n").encode("utf-8"))); break' "$SEEN")
rows=$(dl "SELECT COUNT() FROM disclosure_log")
if [ "$rows" = "1" ]; then echo "  ok   the dispatch wrote one disclosure record"
else echo "  FAIL expected one disclosure_log row, found '${rows}'" >&2; fail=1; fi
rec=$(dl "SELECT state||' '||bytes_body||' '||custody||' '||custody_check FROM disclosure_log")
if [ -n "$sent_bytes" ] && [ "$rec" = "completed $sent_bytes redacted-data not_run" ]; then
  echo "  ok   its bytes_body ($sent_bytes) is what the model received, and it is completed"
else echo "  FAIL disclosure record '$rec' does not match the $sent_bytes octets the model received" >&2; fail=1; fi
# DA1.5: the savings view reads the same record. One local dispatch, and its bytes.
sv=$(curl -s -m 20 http://127.0.0.1:11430/api/savings)
case "$sv" in
  *"\"dispatches\":1,"*"\"local_dispatches\":1,"*"\"bytes_sent_local\":$sent_bytes,"*)
    echo "  ok   /api/savings reports the dispatch and its $sent_bytes bytes" ;;
  *) echo "  FAIL /api/savings does not report the recorded dispatch: $(printf '%s' "$sv" | head -c 300)" >&2; fail=1 ;;
esac
leaked=$(dl "SELECT COUNT() FROM disclosure_log WHERE instr(record_id||correlation_id||request_id||session_id||provider||model_id||endpoint_host||custody||entity_types||detection_layers||fields_disclosed, '$EMAIL')>0")
if [ "$leaked" = "0" ]; then echo "  ok   and it holds the address in no column"
else echo "  FAIL the disclosure record holds the address" >&2; fail=1; fi

# F5.12: when the routed model is not installed, loke must refuse and name what IS installed,
# rather than send a request Ollama will reject. Restart the fake with a list that does
# not contain the routed model.
pkill -f "scripts/lib/fake_ollama.py $SEEN" 2>/dev/null; sleep 0.5
: > "$SEEN"
FAKE_OLLAMA_MODELS="llama3:latest" python3 "$ROOT/scripts/lib/fake_ollama.py" "$SEEN" >/dev/null 2>&1 & PIDS="$PIDS $!"
for _ in $(seq 1 20); do nc -z -G 1 127.0.0.1 11434 2>/dev/null && break; sleep 0.25; done
OUT2=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"text\":\"summarise: contact $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUT2" in
  *model_not_installed*llama3:latest*|*llama3:latest*model_not_installed*)
    echo "  ok   a routed model that is not installed is refused, naming what is installed" ;;
  *) echo "  FAIL uninstalled routed model was not refused clearly: $(printf '%s' "$OUT2" | head -c 200)" >&2; fail=1 ;;
esac
if [ -s "$SEEN" ]; then echo "  FAIL a request was sent for a model that is not installed" >&2; fail=1; fi
rows_after=$(dl "SELECT COUNT() FROM disclosure_log")

# F5.12: when an installed catalogue model fits, the router chooses IT rather than a
# catalogue default that is not installed. A chat request has two local candidates,
# qwen2.5:7b (the default) and gemma3:4b; only gemma3:4b is listed.
pkill -f "scripts/lib/fake_ollama.py $SEEN" 2>/dev/null; sleep 0.5
: > "$SEEN"
FAKE_OLLAMA_MODELS="gemma3:4b" python3 "$ROOT/scripts/lib/fake_ollama.py" "$SEEN" >/dev/null 2>&1 & PIDS="$PIDS $!"
for _ in $(seq 1 20); do nc -z -G 1 127.0.0.1 11434 2>/dev/null && break; sleep 0.25; done
OUT3=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"text\":\"hello there, please write to $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUT3" in
  *'"ok":true'*'"model":"gemma3:4b"'*) echo "  ok   the router chose the installed gemma3:4b, and the request was answered" ;;
  *) echo "  FAIL the installed model was not chosen: $(printf '%s' "$OUT3" | head -c 200)" >&2; fail=1 ;;
esac
if grep -q '^/api/generate .*"model": *"gemma3:4b"' "$SEEN"; then echo "  ok   and the model received the request under that name"
else echo "  FAIL the model did not receive a request for gemma3:4b" >&2; fail=1; fi
# DA1.5: the answer carries its own disclosure, and its bytes are what the model received.
g_bytes=$(python3 -c 'import sys
for line in open(sys.argv[1],encoding="utf-8"):
    if line.startswith("/api/generate "): print(len(line[len("/api/generate "):].rstrip("\n").encode("utf-8"))); break' "$SEEN")
case "$OUT3" in
  *"\"disclosure\":{\"bytes_body\":$g_bytes,\"destination\":\"local\""*) echo "  ok   and the answer reports its own disclosure: $g_bytes bytes to a local model" ;;
  *) echo "  FAIL the answer does not report its disclosure ($g_bytes bytes sent): $(printf '%s' "$OUT3" | head -c 300)" >&2; fail=1 ;;
esac

# T10.1: with the per-provider kill switch engaged for ollama, the same request is refused
# with the fallback message and nothing reaches the model. The row is written as
# killswitch.engageprovider writes it.
: > "$SEEN"
sqlite3 "$DB" "INSERT OR REPLACE INTO settings (key,value,value_type,namespace,updated_at) VALUES ('governance.kill_switch.provider.ollama','true','bool','governance',datetime('now'))"
OUT4=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"text\":\"hello there, please write to $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUT4" in
  *'"provider_blocked":true'*) echo "  ok   with ollama switched off, the request is refused with the fallback message" ;;
  *) echo "  FAIL a switched-off provider was not refused: $(printf '%s' "$OUT4" | head -c 200)" >&2; fail=1 ;;
esac
if grep -q '^/api/generate' "$SEEN"; then echo "  FAIL a request reached the switched-off provider" >&2; fail=1
else echo "  ok   and nothing reached the model"; fi
if [ -n "$rows" ] && [ "$rows_after" = "$rows" ]; then
  echo "  ok   and the refusal, which sent nothing, wrote no disclosure record"
else echo "  FAIL disclosure_log went from '${rows}' to '${rows_after}' rows across a refused request" >&2; fail=1; fi

[ "$fail" -eq 0 ] || { echo "smoke_e2e: FAILED" >&2; exit 1; }
echo "smoke_e2e: OK — anonymised on the way out, restored on the way back"
