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
# loke.db does keep conversation text in the clear) is printed by no report.
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
check "two requests: the answered one and the privacy refusal" $([ "$(grep -c '^17735328' "$WORK/compliance.txt")" -eq 2 ] && grep -q '"privacy_refused / browser-chat / none"' "$WORK/compliance.txt"; echo $?)

run policy generate --template policy_changes --period 2026
check "the kill-switch change is the one control change" $(grep -q "^Summary: Kill-switch changes recorded: 1\." "$WORK/policy.txt"; echo $?)

run cost generate --template cost_savings --start 2026-03-01 --end 2026-03-31 --format json
check "cost_savings in JSON exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "is one JSON object with one row counted and the outcome's cost, not the dispatch's" $(python3 -c '
import json,sys
d=json.loads(open(sys.argv[1]).read())
sys.exit(0 if d["row_count"]==1 and "total cost $1.50" in d["summary"] and d["period_start"]=="2026-03-01" else 1)' "$WORK/cost.txt"; echo $?)

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
  for f in empty routing compliance policy cost later regulatory pdf templates; do echo "--- $f ---"; cat "$WORK/$f.txt" 2>/dev/null; done
  echo "smoke_report: $FAILS check(s) FAILED"
  exit 1
fi
echo "smoke_report: all checks passed"
