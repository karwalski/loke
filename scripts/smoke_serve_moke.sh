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
for p in / /chat /insight /governance /dashboard /agents /connections /memory /settings /upload /mcp; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "http://127.0.0.1:$PORT$p")
  if [ "$code" = 000 ] || [ "$code" -ge 500 ]; then
    echo "  FAIL GET $p [$code]" >&2; fail=1
  else
    echo "  ok   GET $p [$code]"
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

[ "$fail" -eq 0 ] || { echo "smoke_serve_moke: failed (MK21.16)" >&2; exit 1; }
echo "smoke_serve_moke: OK, every page rendered and every dataset loaded"
