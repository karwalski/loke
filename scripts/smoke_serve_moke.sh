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

# It serves on its own port, but what it serves is a CLIENT of the fixed ports: moke's /api/pipeline, /api/routing and /api/ml/propose call loke at 127.0.0.1:11430,
# and this script asserts loke is NOT there. So
# it takes the fixed-port lock that smoke_e2e.sh and smoke_ui.sh hold. Without it, a run
# overlapping another worktree's smoke_e2e sent that smoke's servers requests it had not made:
# measured on 2026-09-27, an extra disclosure row ("hello") and a proposal request reaching
# the fake model, which failed smoke_e2e's counts. Found by the DA1.9 follow-up.
. "$ROOT/scripts/lib/fixedports_lock.sh"
acquire_fixedports || { echo "smoke_serve_moke: could not get the fixed-port lock" >&2; exit 1; }

# F10.38: refuse to start on a port something already holds. Another worker's fake Ollama
# once held this port; the server failed to bind and the probes below were answered by the
# fake. Checked after taking the lock, so the holder is not one of our own smokes.
. "$ROOT/scripts/lib/port_owner.sh"
refuse_if_port_busy smoke_serve_moke "$PORT" || { release_fixedports; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/moke_smoke.XXXXXX")
PID=
cleanup() { [ -n "$PID" ] && kill "$PID" 2>/dev/null; rm -rf "$WORK"; release_fixedports; }
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
# F10.38: something answered; confirm it is the moke this script started.
assert_port_owner smoke_serve_moke "$PORT" "$PID" || { tail -5 "$WORK/serve.log" >&2; exit 1; }

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

# GA1.5c: the savings surfaces take their figures from static/js/moke-savings.js. Both pages
# must load it, and it must be served, or the ledger is not written and the view is blank.
for p in /chat /governance; do
  if curl -s -m 20 "http://127.0.0.1:$PORT$p" | grep -qF '<script src="/static/js/moke-savings.js"></script>'; then
    echo "  ok   GET $p loads the measured savings ledger"
  else
    echo "  FAIL GET $p does not load /static/js/moke-savings.js" >&2; fail=1
  fi
done
if curl -s -m 20 "http://127.0.0.1:$PORT/static/js/moke-savings.js" | grep -qF "var NOT_MEASURED = 'not measured';"; then
  echo "  ok   GET /static/js/moke-savings.js serves the ledger"
else
  echo "  FAIL GET /static/js/moke-savings.js is not served" >&2; fail=1
fi

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
# MK6.6: ?name= reaches the handler (http.reqparam never saw a query string), and the preview
# holds the cells, not their addresses.
api POST '/api/upload?name=sales_q3.csv' $'region,amount\nnorth,10\n' 200 '"filename":"sales_q3.csv"' "an upload takes its name from ?name="
api POST '/api/upload?name=sales_q3.csv' $'region,amount\nnorth,10\n' 200 '"preview_rows":[["north","10"]]' "and previews the rows it parsed"
# MK6.9: the name is percent-decoded (moke.query.value); it was stored as sent.
api POST '/api/upload?name=sales%20q3%2B.csv' $'region,amount\nnorth,10\n' 200 '"filename":"sales q3+.csv"' "a percent-encoded ?name= is decoded"
api POST /api/routing   '{"prompt":"hello"}'            200 '"routing":{'           "routing explains a decision"
# GA1.5c: the cost it answered was priced over a fixed 500 tokens in and 200 out, whatever the
# prompt. No token is counted before dispatch, so it must say the cost is not measured.
api POST /api/routing   '{"prompt":"hello"}'            200 '"cost":{"measured":false,"reason":"not measured' "and says its cost is not measured, not priced over invented tokens"
api GET  /api/agents    ""                              200 '"agents":['            "agents lists the agents"
# NC1.3 / MK6.5: the proposal route exists, takes column names only, and with loke down says
# its suggestions are heuristic rather than presenting them as a model's.
api POST /api/ml/propose '{}'                            400 'at least one of'       "a proposal needs column names"
api POST /api/ml/propose '{"num_cols":["revenue","orders","ltv"],"cat_cols":["region","plan"]}' 200 '"source":"heuristic"' "and proposes analyses from names alone, labelled heuristic"
# MK6.5: the seven handlers that compiled with no route. Each check judges what the handler
# computed, so a route that answers 404, or a handler that answers but ignores its input, fails.
# MK6.6: the panels' histories are shared by every worker, which the repeated reads below check.
api GET  /api/mcp/tools  ""                              200 '"name":"anonymise"'    "the MCP panel lists mcp-toke's tools"
api POST /api/mcp/invoke '{}'                            400 'tool_name is required' "invoking needs a tool name"
api POST /api/mcp/invoke '{"tool_name":"nosuchtool","args":{}}' 200 'unknown tool: nosuchtool' "and an unknown tool is reported as one"
# MK6.7: compress answered {"toon":"~","savings_pct":94} for this input. It must carry both rows
# as TOON's table and measure the saving from the two lengths (17 characters to 15, 11%).
api POST /api/mcp/invoke '{"tool_name":"compress","args":{"json":"[{\"a\":1},{\"a\":2}]"}}' 200 '[2]{a}:' "compress writes the two rows as a TOON table, not ~"
api POST /api/mcp/invoke '{"tool_name":"compress","args":{"json":"[{\"a\":1},{\"a\":2}]"}}' 200 'toon_chars\\\":15,\\\"savings_pct\\\":11,' "and measures the saving from the lengths, 17 characters to 15"
# MK6.10: anonymise answered with an "original" field holding the text as sent, and analyse
# listed each entity's value. The POST echoes the caller's own arguments back in args_json, so
# the scan is of the tool's answer, result_json, every layer of which is decoded strictly; the
# positive control is that the same scan finds every value in args_json. Then the files the calls
# could have written: the shared panel log and loke.log. The detection layers other than regex
# are unreachable here.
PII_TEXT='{"text":"Dear team,\nplease contact alice@example.com or ring 0412 345 678.\n\tCard: 4111 1111 1111 1111"}'
PII_ROWS='{"json":"[{\"email\":\"alice@example.com\"},{\"email\":\"bob@example.com\"}]","name":"q3"}'
tool_answer() {  # tool args-json label python-condition-on-answer
  local out
  out=$(curl -s -m 20 -X POST -H 'Content-Type: application/json' \
    -d "{\"tool_name\":\"$1\",\"args\":$2}" "http://127.0.0.1:$PORT/api/mcp/invoke")
  if printf '%s' "$out" | python3 -c '
import json, sys
pii = ["alice@example.com", "alice@", "bob@", "0412 345 678", "4111 1111 1111 1111", "4111"]
inv = json.loads(sys.stdin.read())
sent = [v for v in pii if v in inv["args_json"]]
assert sent, "control: the scan finds no value in args_json"
assert inv["success"] is True, "the tool failed: %s" % inv["error"][:160]
answer = json.loads(json.loads(inv["result_json"])["content"][0]["text"])
leaked = [v for v in sent if v in inv["result_json"]]
assert not leaked, "the answer holds %s" % leaked
assert eval(sys.argv[1]), "the answer is %s" % json.dumps(answer)[:200]
' "$4"; then
    echo "  ok   POST /api/mcp/invoke $1: $3"
  else
    echo "  FAIL POST /api/mcp/invoke $1: $3: $(printf '%s' "$out" | head -c 200)" >&2; fail=1
  fi
}
tool_answer anonymise "$PII_TEXT" "the answer is the anonymised text, with no personal value in it" \
  'answer["entities_found"] == 3 and answer["anonymised"].startswith("Dear team,\nplease contact [EMAIL") and "original" not in answer'
tool_answer analyse "$PII_TEXT" "the answer counts the entities and names none of their values" \
  'answer["entity_count"] == 3 and answer["safe_to_send"] is False and {"type": "email", "start": 26, "end": 43} in answer["entities"]'
tool_answer profile "$PII_ROWS" "the schema describes the column and holds none of its values" \
  'answer["schema"] == "SCHEMA:q3 rows:2 cols:1\nemail:str nulls:0% uniq:2 [PII]" and answer["rows"] == 2'
if grep -rqsF -e 'alice@' -e 'bob@' -e '0412 345 678' -e '4111 1111' "$WORK/home/.loke"; then
  echo "  FAIL a personal value reached a file under ~/.loke: $(grep -rlsF -e 'alice@' -e 'bob@' -e '0412 345 678' -e '4111 1111' "$WORK/home/.loke")" >&2; fail=1
elif ! grep -qsF 'anonymise: 3 entities found' "$WORK/home/.loke/loke.log"; then
  echo "  FAIL control: loke.log does not hold anonymise's line, so the scan above proves nothing" >&2; fail=1
else
  echo "  ok   no personal value was written under ~/.loke, and loke.log holds the calls' lines"
fi
api GET  /api/mcp/broker ""                              200 '"name":"loke-memory"'  "the broker panel lists its servers"
api GET  /api/mcp/memory ""                              200 '"available_tools":["memory.search"' "the memory panel lists its tools"
api POST /api/mcp/memory '{"tool_name":"memory.diary_write","args":{"agent_id":"smoke","entry":"hello"}}' 200 '"success":true,"result_preview":"{\"ok\":true}"' "a memory tool runs and succeeds"
# MK6.6: store, status and context used to kill the worker (no response at all).
api POST /api/mcp/memory '{"tool_name":"memory.store","args":{"content":"a note about the project","role":"user"}}' 200 '"success":true,"result_preview":"{\"ok\":true,\"drawer_id\":\"' "memory.store writes a drawer and names it"
api POST /api/mcp/memory '{"tool_name":"memory.status","args":{}}' 200 '"success":true,"result_preview":"{\"total_drawers\":2,\"total_closets\":0,\"total_wings\":2}"' "memory.status counts the diary entry and the note"
api POST /api/mcp/memory '{"tool_name":"memory.search","args":{"query":"project","limit":5}}' 200 'a note about the project' "memory.search finds the stored note"
api POST /api/mcp/memory '{"tool_name":"memory.context","args":{"task":"project","token_budget":2000}}' 200 'PALACE: ' "memory.context answers with the palace map"
api POST /api/agents/scan '{"dataset_id":"smoke","headers":["amount"],"rows_json":"[[\"10\"],[\"11\"],[\"10\"],[\"12\"],[\"9\"],[\"10\"],[\"11\"],[\"10\"],[\"9\"],[\"10\"],[\"11\"],[\"10\"],[\"1000\"]]"}' 200 '"column":"amount","kind":"iqr"' "the quality scan finds the planted outlier"
api POST /api/agents/schema '{}'                         400 'old_csv and new_csv are required' "a schema comparison needs two files"
api POST /api/agents/schema '{"dataset_id":"smoke","old_csv":"a,b\n1,2\n","new_csv":"a,c\n1,x\n"}' 200 '"summary":"2 changes: 1 added, 1 removed' "and reports the column that went and the one that came"
api GET  '/api/agents/diary?agent_id=schema-change-detector' "" 200 '"agent_id":"schema-change-detector"' "the diary answers for the agent it is asked about"
api GET  '/api/agents/diary?agent_id=nosuchagent' ""    404 'agent not found: nosuchagent' "and 404s an agent that does not exist"

# MK6.6: state shared across moke's pre-forked workers. Each worker used to keep its own copy,
# and eight reads after six invocations reported 0,0,0,1,0,0,1,1. Every read must now see all of
# them: the nosuchtool and two compress invocations above and five more here (MK6.7 added the
# compress pair, MK6.10 the anonymise, analyse and profile calls); the five memory calls above.
for i in 1 2 3 4 5; do
  curl -s -o /dev/null -m 20 -X POST -H 'Content-Type: application/json' \
    -d '{"tool_name":"nosuchtool","args":{}}' "http://127.0.0.1:$PORT/api/mcp/invoke"
done
for i in 1 2 3 4 5 6 7 8; do
  api GET /api/mcp/tools  "" 200 '"total_invocations":11}' "read $i of the tool log sees all eleven invocations"
  api GET /api/mcp/memory "" 200 '"total_invocations":5}' "read $i of the memory log sees all five calls"
  api GET '/api/agents/diary?agent_id=data-quality-scanner' "" 200 '"total_runs":1,' "read $i of the scanner sees its run"
  api GET /api/agents     "" 200 '"output_summary":"2 changes: 1 added, 1 removed' "read $i of the agents panel sees the schema run"
done
# The shared log is a file that outlives the request, so it keeps no arguments or results.
api GET /api/mcp/memory "" 200 '"tool_name":"memory.store","args_json":"",' "the memory log does not keep what was stored"

# F10.38: and it still is, so no answer above came from a server that took the port later.
assert_port_owner smoke_serve_moke "$PORT" "$PID" || fail=1

# GA2.5: and it listens on loopback only. lsof names each listening socket's address; `*:$PORT`
# (every interface) or any address but 127.0.0.1 / ::1 fails. The served ooke.toml is the
# tree's own with only the port changed, so this checks the [server] host moke ships with.
if assert_loopback_only smoke_serve_moke "$PORT"; then
  echo "  ok   listening on loopback only: $(port_bind_addresses "$PORT" | tr '\n' ' ')(GA2.5)"
else
  fail=1
fi

[ "$fail" -eq 0 ] || { echo "smoke_serve_moke: failed (MK21.16)" >&2; exit 1; }
echo "smoke_serve_moke: OK, every page rendered and every dataset loaded"
