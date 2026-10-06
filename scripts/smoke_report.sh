#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_report.sh — run the built `loke report` against a throwaway HOME whose loke.db is
# seeded with audit rows, and judge what it prints. (GA5.31, GA5.30)
#
# Checks: one forwarded request (its llm_dispatch and llm_request rows) is one routing
# decision and one provider call, a kill-switch change is a control change and not a
# routing decision, a refused request is in the compliance summary, the cost total is the
# outcome's, each format renders, a window that holds nothing reports nothing, an unknown
# template and PDF are refused with exit 1, and a raw value planted in memory_drawers (where
# loke.db does keep conversation text in the clear) is printed by no report. GA5.32: a refused
# kill-switch change through the CLI is audited as kill_switch_change_refused and counted by no
# template, and the JSON and CSV exports of a row holding a quote, a comma, a newline and a
# backslash parse with Python's json and csv and give each field back exactly.
#
# HOME is a throwaway directory, so the real ~/.loke is never read; no port, no lock, no
# network. The first run creates and migrates loke.db; the rows are then inserted with
# sqlite3, since audit_log takes INSERT and the point is rows dated in March 2026.
#
#   scripts/smoke_report.sh        # uses build/trees/loke-cli/loke-cli

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/build/trees/loke-cli/loke-cli"
[ -x "$BIN" ] || { echo "smoke_report: $BIN not built; run scripts/build_trees.sh loke-cli" >&2; exit 1; }
command -v sqlite3 >/dev/null || { echo "smoke_report: sqlite3 not found" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_report_smoke.XXXXXX")
trap 'rm -rf "$WORK"' EXIT INT TERM
mkdir -p "$WORK/home/.loke"
DB="$WORK/home/.loke/loke.db"

FAILS=0
check() { # $1 = label, $2 = 0 if it held
  if [ "$2" -eq 0 ]; then echo "  ok    $1"; else echo "  FAIL  $1"; FAILS=$((FAILS+1)); fi
}
run() { # $1 = output name, rest = report arguments; sets rc
  HOME="$WORK/home" "$BIN" report "${@:2}" >"$WORK/$1.txt" 2>&1; rc=$?
}

run empty generate --period Q1-2026
check "an empty store reports and exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "and says it holds no requests" $(grep -q "^Summary: Requests audited, one row per request: 0" "$WORK/empty.txt"; echo $?)
[ -s "$DB" ] || { echo "smoke_report: $DB was not created" >&2; exit 1; }

PLANTED="jane.planted@example.com"
row() { # event_type correlation_id model sensitivity cents created_ms
  echo "INSERT INTO audit_log (id,event_type,use_case,model_id,provider,sensitivity,risk_tier,tokens_in,tokens_out,cost_usd_cents,duration_ms,correlation_id,prev_hash,hash,created_at) VALUES ('$(openssl rand -hex 8)','$1','browser-chat','$3','anthropic','$4','MEDIUM',10,20,$5,100,'$2','','placeholder','$6');"
}
{
  row llm_dispatch     rq1 claude-3.5-sonnet confidential 999 1773532801000
  row llm_request      rq1 claude-3.5-sonnet confidential 150 1773532802000
  row privacy_refused  rq2 none              restricted   0   1773532803000
  row kill_switch_engaged global:all ""      ""           0   1773532804000
  echo "INSERT INTO memory_drawers (id,wing,hall,room,role,content,session_id,model_id,sensitivity,created_at) VALUES ('md-1','work','finance','invoices','user','Email $PLANTED about the invoice','rq1','claude-3.5-sonnet','CONFIDENTIAL','1773532801000');"
} | sqlite3 "$DB" || { echo "smoke_report: seeding $DB failed" >&2; exit 1; }

run routing generate --template routing_decisions --period Q1-2026
check "routing_decisions exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "one forwarded request is one routing decision" $(grep -q "^Summary: Provider calls, one row per call: 1$" "$WORK/routing.txt"; echo $?)
check "reported as its outcome, with provider and model" $(grep -q "| routing: llm_request / browser-chat / claude-3.5-sonnet" "$WORK/routing.txt"; echo $?)
check "and no dispatch or kill-switch row" $(! grep -qE "llm_dispatch|kill_switch" "$WORK/routing.txt"; echo $?)

run compliance generate --period 2026-03 --format csv
check "compliance_summary in CSV exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "its header is the CSV header" $(grep -q "^timestamp,category,detail,severity,value$" "$WORK/compliance.txt"; echo $?)
check "two requests: the answered one and the privacy refusal" $(python3 -c '
import csv,sys
rows=[r for r in csv.reader(open(sys.argv[1],newline="")) if r]  # the CLI ends its output with a newline of its own
details=sorted(r[2] for r in rows[1:])
sys.exit(0 if rows[0]==["timestamp","category","detail","severity","value"] and details==["llm_request / browser-chat / claude-3.5-sonnet","privacy_refused / browser-chat / none"] else 1)' "$WORK/compliance.txt"; echo $?)

# GA5.32: a refused kill-switch change, made through the real CLI, is audited under its
# own event type, never the target typed, and is no control change and no request.
HOME="$WORK/home" "$BIN" kill-switch on --use-case no-such-use-case >"$WORK/ksbad.txt" 2>&1; rc=$?
check "a kill-switch change to an unknown use case is refused with exit 1" $([ "$rc" -eq 1 ]; echo $?)
check "and audited as kill_switch_change_refused under its scope alone" $([ "$(sqlite3 "$DB" "SELECT COUNT() FROM audit_log WHERE event_type='kill_switch_change_refused' AND correlation_id='use_case:unrecognised'")" = 1 ] && [ "$(sqlite3 "$DB" "SELECT COUNT() FROM audit_log WHERE correlation_id LIKE '%no-such%' OR use_case LIKE '%no-such%' OR event_type='kill_switch_refused'")" = 0 ]; echo $?)

run policy generate --template policy_changes --period 2026
check "the kill-switch change is the one control change, the refused one not counted" $(grep -q "^Summary: Kill-switch changes recorded: 1\." "$WORK/policy.txt"; echo $?)
run compliance2026 generate --period 2026
check "and the refused change is no request either" $(grep -q "^Summary: Requests audited, one row per request: 2$" "$WORK/compliance2026.txt" && ! grep -q "kill_switch" "$WORK/compliance2026.txt"; echo $?)

run cost generate --template cost_savings --start 2026-03-01 --end 2026-03-31 --format json
check "cost_savings in JSON exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "is one JSON object with one row counted and the outcome's cost, not the dispatch's" $(python3 -c '
import json,sys
d=json.loads(open(sys.argv[1]).read())
sys.exit(0 if d["row_count"]==1 and len(d["rows"])==1 and d["rows"][0]["value"]=="$1.50" and "total cost $1.50" in d["summary"] and d["period_start"]=="2026-03-01" else 1)' "$WORK/cost.txt"; echo $?)

# GA5.31's Not-done: a row whose model and provider hold a double quote, a comma, a newline
# and a backslash, alone in November 2025. The exports are parsed with Python's json and csv and
# each field must come back exactly as stored.
TRICKY_MODEL="evil \"model\", with"$'\n'"newline \\ back"
TRICKY_PROVIDER='prov,"x"\y'
{
  echo "INSERT INTO audit_log (id,event_type,use_case,model_id,provider,sensitivity,risk_tier,tokens_in,tokens_out,cost_usd_cents,duration_ms,correlation_id,prev_hash,hash,created_at) VALUES ('$(openssl rand -hex 8)','llm_request','browser-chat','evil \"model\", with' || char(10) || 'newline \\ back','prov,\"x\"\\y','internal','MEDIUM',10,20,0,100,'rq9','','placeholder','1762732800000');"
} | sqlite3 "$DB" || { echo "smoke_report: seeding the escaping row failed" >&2; exit 1; }
[ "$(sqlite3 "$DB" "SELECT COUNT() FROM audit_log WHERE model_id LIKE '%\"model\"%' AND instr(model_id,char(10))>0 AND instr(model_id,'\\')>0")" = 1 ] \
  || { echo "smoke_report: the escaping row was not stored as intended" >&2; exit 1; }

run trickyjson generate --template routing_decisions --period 2025-11 --format json
check "JSON with a quote, comma, newline and backslash in its fields parses, and each comes back exact" $(python3 -c '
import json,sys
d=json.loads(open(sys.argv[1]).read())
r=d["rows"]
sys.exit(0 if d["row_count"]==1 and len(r)==1 and r[0]["detail"]=="llm_request / browser-chat / "+sys.argv[2] and r[0]["value"]==sys.argv[3]+" / "+sys.argv[2] else 1)' "$WORK/trickyjson.txt" "$TRICKY_MODEL" "$TRICKY_PROVIDER"; echo $?)

run trickycsv generate --template routing_decisions --period 2025-11 --format csv
check "CSV with the same row parses as RFC 4180: one record of five fields, each exact" $(python3 -c '
import csv,sys
rows=[r for r in csv.reader(open(sys.argv[1],newline="")) if r]  # the CLI ends its output with a newline of its own
ok=len(rows)==2 and len(rows[1])==5 and rows[1][2]=="llm_request / browser-chat / "+sys.argv[2] and rows[1][4]==sys.argv[3]+" / "+sys.argv[2]
sys.exit(0 if ok else 1)' "$WORK/trickycsv.txt" "$TRICKY_MODEL" "$TRICKY_PROVIDER"; echo $?)

run later generate --template routing_decisions --period Q2-2026
check "a quarter that holds nothing reports nothing" $(grep -q "^Summary: Provider calls, one row per call: 0$" "$WORK/later.txt"; echo $?)

run regulatory generate --template eu-ai-act --period Q1-2026
check "an unbuilt template exits 1" $([ "$rc" -eq 1 ]; echo $?)
check "and names the templates there are" $(grep -q "unknown report template: eu-ai-act. Available: compliance_summary" "$WORK/regulatory.txt"; echo $?)

run pdf generate --period Q1-2026 --format pdf
check "PDF exits 1 and says it is not built" $([ "$rc" -eq 1 ] && grep -q "PDF output is not built" "$WORK/pdf.txt"; echo $?)

run templates templates
check "report templates lists the five" $(grep -q "^Report templates: compliance_summary, pii_detection_log, routing_decisions, policy_changes, cost_savings$" "$WORK/templates.txt"; echo $?)

for t in compliance_summary pii_detection_log routing_decisions policy_changes cost_savings; do
  for f in text csv json; do
    run "pii-$t-$f" generate --template "$t" --period Q1-2026 --format "$f"
  done
done
check "the value planted in memory_drawers is printed by no template in any format" $(! cat "$WORK"/*.txt | grep -q "jane.planted"; echo $?)

if [ "$FAILS" -ne 0 ]; then
  for f in empty routing compliance ksbad policy compliance2026 cost trickyjson trickycsv later regulatory pdf templates; do echo "--- $f ---"; cat "$WORK/$f.txt" 2>/dev/null; done
  echo "smoke_report: $FAILS check(s) FAILED"
  exit 1
fi
echo "smoke_report: all checks passed"
