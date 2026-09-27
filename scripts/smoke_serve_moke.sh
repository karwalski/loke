#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_serve_moke.sh — start the built moke binary and check that every page renders and
# every demo dataset loads (MK21.16).
#
# moke never linked before 2026-09-24, so nothing about it had ever run. The first time it
# was served, / and /chat answered 500 "Handler returned null": each `get` ended in a `mt`
# with no `<`, so the rendered page was computed and thrown away. The datasets had just
# moved from source literals to CSV files, and a dataset that fails to load comes back empty
# rather than erroring. So this script checks row counts, not only that a request answered.
#
# Pages must answer below 500. /api/health proxies to loke and answers 503 when loke is
# not running, which is correct, so it is not probed here. Runs a copy on port
# $SMOKE_MOKE_PORT (default 11497) with a throwaway HOME.

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/packages/moke"
BIN="$ROOT/build/trees/moke/moke"
PORT="${SMOKE_MOKE_PORT:-11497}"

[ -x "$BIN" ] || { echo "smoke_serve_moke: $BIN not built; run scripts/build_trees.sh moke" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/moke_smoke.XXXXXX")
PID=
cleanup() { [ -n "$PID" ] && kill "$PID" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

for d in pages templates static; do [ -d "$SRC/$d" ] && cp -R "$SRC/$d" "$WORK/"; done
mkdir -p "$WORK/data" "$WORK/home"
cp -R "$SRC/data/csv" "$WORK/data/"
cp "$BIN" "$WORK/moke"
sed -E "s/^([[:space:]]*port[[:space:]]*=).*/\1 $PORT/" "$SRC/ooke.toml" > "$WORK/ooke.toml"

( cd "$WORK" && HOME="$WORK/home" exec ./moke > "$WORK/serve.log" 2>&1 ) &
PID=$!

up=0
for _ in $(seq 1 40); do
  if curl -s -o /dev/null -m 1 "http://127.0.0.1:$PORT/insight"; then up=1; break; fi
  sleep 0.25
done
[ "$up" -eq 1 ] || { echo "smoke_serve_moke: moke never answered on $PORT" >&2; tail -5 "$WORK/serve.log" >&2; exit 1; }

fail=0
# X7.2: each page must answer 200 with a whole rendered document. This replaced twelve
# packages/moke/tests/test_*_handler.tk files that asserted literals they declared
# themselves ("the template path is templates/chat.tkt") and so could never fail.
for p in / /chat /insight /governance /dashboard /agents /connections /memory /settings /upload /mcp /presentation; do
  code=$(curl -s -o "$WORK/page.html" -w '%{http_code}' -m 20 "http://127.0.0.1:$PORT$p")
  if [ "$code" != 200 ]; then
    echo "  FAIL GET $p [$code]" >&2; fail=1
  elif ! grep -qi '</html>' "$WORK/page.html"; then
    echo "  FAIL GET $p [200] but not a whole HTML document ($(wc -c < "$WORK/page.html") bytes)" >&2; fail=1
  else
    echo "  ok   GET $p [200, $(wc -c < "$WORK/page.html") bytes]"
  fi
done

# Every dataset id the registry answers to must load with at least one row.
ids=$(grep -o 'str.eq(id;"[^"]*")' "$SRC/data/registry.tk" | sed 's/.*"\(.*\)")/\1/' | sort -u)
for id in $ids; do
  out=$(curl -s -m 20 -X POST -H 'Content-Type: application/json' -d "{\"id\":\"$id\"}" \
          "http://127.0.0.1:$PORT/api/datasets")
  rows=$(printf '%s' "$out" | sed -n 's/.*"row_count":\([0-9]*\).*/\1/p')
  if [ -z "$rows" ] || [ "$rows" -eq 0 ]; then
    echo "  FAIL dataset $id did not load: $(printf '%s' "$out" | head -c 120)" >&2; fail=1
  else
    echo "  ok   dataset $id [$rows rows]"
  fi
done

# X7.2: the API endpoints, each against the behaviour its old packages/moke/tests stub only
# described. loke is not running here, so the loke-backed endpoints are checked for how they
# fail. Every body must be valid JSON: /api/routing and /api/agents were not (every string
# was doubly quoted) until this check existed.
api() {  # method path body expected-code must-contain label
  local out code
  out=$(curl -s -m 20 -X "$1" -H 'Content-Type: application/json' ${3:+-d "$3"} -w '\n%{http_code}' "http://127.0.0.1:$PORT$2")
  code=$(printf '%s' "$out" | tail -1); out=$(printf '%s' "$out" | sed '$d')
  if [ "$code" != "$4" ]; then
    echo "  FAIL $1 $2 [$code, wanted $4]: $(printf '%s' "$out" | head -c 150)" >&2; fail=1; return
  fi
  if ! printf '%s' "$out" | python3 -c 'import json,sys; json.loads(sys.stdin.read())' 2>/dev/null; then
    echo "  FAIL $1 $2 [$code] is not valid JSON: $(printf '%s' "$out" | head -c 150)" >&2; fail=1; return
  fi
  case "$out" in
    *"$5"*) echo "  ok   $1 $2 [$code] $6" ;;
    *) echo "  FAIL $1 $2 [$code] lacks $5: $(printf '%s' "$out" | head -c 150)" >&2; fail=1 ;;
  esac
}
api GET  /api/health    ""                              503 '"loke":"unreachable"'  "reports loke unreachable, with a 503"
api POST /api/datasets  '{}'                            400 'missing required field: id' "requires an id"
api POST /api/feedback  '{"rating":"meh"}'              400 'thumbs_up or thumbs_down' "accepts only thumbs_up or thumbs_down"
api POST /api/feedback  '{"rating":"thumbs_down"}'      200 '"rating":"thumbs_down"' "and records a valid rating"
api GET  /api/memory    ""                              200 '"ok":true'             "memory API answers"
api POST /api/memory    '{"action":"store"}'            400 'missing required field: content' "storing requires content"
api POST /api/pipeline  '{}'                            400 'missing required field: prompt' "the pipeline requires a prompt"
api POST /api/pipeline  '{"prompt":"hello"}'            502 'upstream error'        "and says so when loke is down"
api POST /api/stream    '{}'                            400 'missing required field: prompt' "streaming requires a prompt"
api POST /api/upload    ''                              400 'empty body'            "upload refuses an empty body"
api POST /api/routing   '{"prompt":"hello"}'            200 '"routing":{'           "routing explains a decision"
api GET  /api/agents    ""                              200 '"agents":['            "agents lists the agents"
# NC1.3 / MK6.5: the proposal route exists, takes column names only, and with loke down says
# its suggestions are heuristic rather than presenting them as a model's.
api POST /api/ml/propose '{}'                            400 'at least one of'       "a proposal needs column names"
api POST /api/ml/propose '{"num_cols":["revenue","orders","ltv"],"cat_cols":["region","plan"]}' 200 '"source":"heuristic"' "and proposes analyses from names alone, labelled heuristic"

[ "$fail" -eq 0 ] || { echo "smoke_serve_moke: failed (MK21.16)" >&2; exit 1; }
echo "smoke_serve_moke: OK, every page rendered and every dataset loaded"
