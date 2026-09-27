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
. "$ROOT/scripts/lib/fixedports_lock.sh"
trap release_fixedports EXIT INT TERM
acquire_fixedports || { echo "smoke_e2e: could not get the fixed-port lock" >&2; exit 1; }
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
  release_fixedports
}
trap cleanup EXIT INT TERM

mkdir -p "$WORK/lk/home" "$WORK/mk/home" "$WORK/mk/data"
( cd "$ROOT/packages/browser" && cp -R pages templates static ooke.toml "$WORK/lk/" )
cp "$LOKE_BIN" "$WORK/lk/loke"
( cd "$ROOT/packages/moke" && cp -R pages templates static ooke.toml "$WORK/mk/" && cp -R data/csv "$WORK/mk/data/" )
cp "$MOKE_BIN" "$WORK/mk/moke"

SEEN="$WORK/model_saw.log"; : > "$SEEN"
QWEN_DIGEST=2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730
LLAMA_DIGEST=365c0bd3c000a25d28ddbf732fe1c6add414de7275464c4e4d1c3b5fcb5d8ad1
FAKE_OLLAMA_DIGESTS="qwen2.5:7b=$QWEN_DIGEST,llama3:latest=$LLAMA_DIGEST" \
  python3 "$ROOT/scripts/lib/fake_ollama.py" "$SEEN" >/dev/null 2>&1 & PIDS="$PIDS $!"
( cd "$WORK/lk" && HOME="$WORK/lk/home" exec "$WORK/lk/loke" > "$WORK/lk.log" 2>&1 ) & PIDS="$PIDS $!"
( cd "$WORK/mk" && HOME="$WORK/mk/home" exec "$WORK/mk/moke" > "$WORK/mk.log" 2>&1 ) & PIDS="$PIDS $!"

for _ in $(seq 1 40); do
  nc -z -G 1 127.0.0.1 11430 2>/dev/null && nc -z -G 1 127.0.0.1 11432 2>/dev/null \
    && nc -z -G 1 127.0.0.1 11434 2>/dev/null && break
  sleep 0.25
done

fail=0
# NC1.13: loke issues the session. moke's pages cannot ask loke directly (a foreign Origin is
# refused), so moke's POST /api/session asks on their behalf and hands back loke's id.
E2ESID=$(curl -s -m 20 -X POST -H 'Content-Type: application/json' -d '{}' http://127.0.0.1:11432/api/session \
  | python3 -c 'import json,sys
try:
  d=json.load(sys.stdin); s=d.get("session_id","")
  print(s if d.get("ok") and s.startswith("nc-") and len(s)==35 else "")
except Exception: print("")')
if [ -n "$E2ESID" ] && [ "$(sqlite3 "$WORK/lk/home/.loke/loke.db" "SELECT COUNT() FROM nc_sessions WHERE session_id='$E2ESID'" 2>/dev/null)" = "1" ]; then
  echo "  ok   moke's POST /api/session returned a session loke issued and recorded"
else echo "  FAIL moke did not obtain a session loke issued: '$E2ESID'" >&2; fail=1; fi

EMAIL="e2e.probe.$$@example.com"
OUT=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"prompt\":\"summarise: contact $EMAIL\",\"session_id\":\"$E2ESID\",\"dataset_name\":\"demo\"}" \
        http://127.0.0.1:11432/api/pipeline)

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

# VM1.6e: the NER layer asks the local model to find entities before anything is forwarded.
# fake_ollama.py logs that request apart ($SEEN.ner): it carries the prompt in clear, by
# design, to a loopback host. Before VM1.6e it was never sent at all.
if grep -qs '^/api/chat ' "$SEEN.ner"; then echo "  ok   the NER layer consulted the local model before the forward"
else echo "  FAIL the NER layer never reached the local model" >&2; fail=1; fi

case "$resp" in
  *"$EMAIL"*) echo "  ok   the user got the email address back, restored" ;;
  *) echo "  FAIL the response did not restore the placeholder: $resp" >&2; fail=1 ;;
esac
# GA1.5: no LLMLingua sidecar is configured here, and this prompt is prose, so nothing is
# optimised; the answer says so and why, and moke's pipeline console carries the same line.
case "$OUT" in
  *'"optimisation":{"method":"none","applied":false,"reason":"llmlingua_not_configured"'*)
    echo "  ok   the answer reports that the prompt was not optimised, and why" ;;
  *) echo "  FAIL the answer does not report the optimiser's outcome: $(printf '%s' "$OUT" | head -c 300)" >&2; fail=1 ;;
esac
case "$OUT" in
  *'"stage":"optimise","status":"skip","detail":"not optimised: llmlingua_not_configured"'*)
    echo "  ok   and moke's pipeline console records it" ;;
  *) echo "  FAIL moke's pipeline console has no optimiser line" >&2; fail=1 ;;
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
# DA1.9 (4): the session moke's caller named reaches the record. (3): the model version is the
# digest Ollama listed for the model the row names, measured before transport; header octets,
# jurisdiction and retention are not measured, so NULL, NULL and unknown rather than a guess.
ver=$(dl "SELECT session_id||' '||model_id||' '||model_version||' '||COALESCE(bytes_headers,'NULL')||' '||COALESCE(jurisdiction,'NULL')||' '||retention_class FROM disclosure_log")
case "$ver" in
  "$E2ESID qwen2.5:7b $QWEN_DIGEST NULL NULL unknown"|"$E2ESID llama3:latest $LLAMA_DIGEST NULL NULL unknown")
    echo "  ok   it carries the caller's session and the digest Ollama reported for its model: $ver" ;;
  *) echo "  FAIL the record's session, model version or unmeasured fields are '$ver'" >&2; fail=1 ;;
esac
# DA1.9 (2), spec P2 and G1: the dispatch has exactly one llm_dispatch audit row on its
# correlation id, written with the reserve, and one outcome row after the response.
cid=$(dl "SELECT correlation_id FROM disclosure_log")
pair=$(dl "SELECT (SELECT COUNT() FROM audit_log WHERE correlation_id='$cid' AND event_type='llm_dispatch')||' '||(SELECT COUNT() FROM audit_log WHERE correlation_id='$cid' AND event_type='llm_request')")
if [ -n "$cid" ] && [ "$pair" = "1 1" ]; then echo "  ok   and it joins one llm_dispatch audit row and one outcome row"
else echo "  FAIL the dispatch's audit rows are '$pair' (llm_dispatch, llm_request) for '$cid'" >&2; fail=1; fi
leaked=$(dl "SELECT COUNT() FROM disclosure_log WHERE instr(record_id||correlation_id||request_id||session_id||provider||model_id||endpoint_host||custody||entity_types||detection_layers||fields_disclosed, '$EMAIL')>0")
if [ "$leaked" = "0" ]; then echo "  ok   and it holds the address in no column"
else echo "  FAIL the disclosure record holds the address" >&2; fail=1; fi

# NC1.3: the Insight Lab's proposal path end to end. moke sends loke column NAMES only. The
# prompt is a data-analysis task, which the catalogue can only route to a cloud model at this
# tolerance, and no key is configured here (this test never calls a real provider), so loke
# refuses and moke answers with its heuristic, labelled as such. What is asserted is that the
# request reached loke's router, that no model received anything, and the label.
: > "$SEEN"
refused_before=$(dl "SELECT COUNT() FROM audit_log WHERE event_type='llm_request_refused'")
OUTP=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d '{"num_cols":["revenue","orders","ltv"],"cat_cols":["region"]}' http://127.0.0.1:11432/api/ml/propose)
refused_after=$(dl "SELECT COUNT() FROM audit_log WHERE event_type='llm_request_refused'")
if [ "$refused_after" -gt "$refused_before" ]; then echo "  ok   the Insight Lab's proposal request reaches loke's router"
else echo "  FAIL the proposal request never reached loke ($refused_before -> $refused_after refusals)" >&2; fail=1; fi
case "$OUTP" in
  *'"source":"heuristic"'*'"kind":"kmeans"'*) echo "  ok   and with no model available the proposals are labelled heuristic, not passed off as a model's" ;;
  *) echo "  FAIL unexpected proposal response: $(printf '%s' "$OUTP" | head -c 200)" >&2; fail=1 ;;
esac
if [ -s "$SEEN" ]; then echo "  FAIL a model received a proposal request that should have been refused" >&2; fail=1
else echo "  ok   and no model received anything"; fi
# VM1.6f: the router's intent classifier now reaches the local model when its keywords are
# unsure (it sent nothing before, T-48). fake_ollama.py logs that apart ($SEEN.intent).
if grep -qs '^/api/chat ' "$SEEN.intent"; then echo "  ok   the router's intent classifier consulted the local model, apart from any forward"
else echo "  FAIL the intent classifier never reached the local model" >&2; fail=1; fi

# F5.12: when the routed model is not installed, loke must refuse and name what IS installed,
# rather than send a request Ollama will reject. Restart the fake with a list that does
# not contain the routed model.
pkill -f "scripts/lib/fake_ollama.py $SEEN" 2>/dev/null; sleep 0.5
: > "$SEEN"
FAKE_OLLAMA_MODELS="llama3:latest" python3 "$ROOT/scripts/lib/fake_ollama.py" "$SEEN" >/dev/null 2>&1 & PIDS="$PIDS $!"
for _ in $(seq 1 20); do nc -z -G 1 127.0.0.1 11434 2>/dev/null && break; sleep 0.25; done
OUT2=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"fallback_reason\":\"task_requires_prose\",\"fallback_selected_by\":\"user\",\"text\":\"summarise: contact $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
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
        -d "{\"fallback_reason\":\"task_requires_prose\",\"fallback_selected_by\":\"user\",\"text\":\"hello there, please write to $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
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

# NC1.8: the answer names its custody and what the fallback does not protect, and the
# disclosure record carries the selection.
case "$OUT3" in
  *'"custody":"redacted-data","fallback_reason":"task_requires_prose","fallback_selected_by":"user","residual_risk":"'*)
    echo "  ok   and it names its custody, the fallback selection and the residual risk" ;;
  *) echo "  FAIL the answer does not state its custody and residual risk: $(printf '%s' "$OUT3" | head -c 300)" >&2; fail=1 ;;
esac
sel=$(dl "SELECT fallback_reason||'/'||fallback_selected_by FROM disclosure_log ORDER BY occurred_at DESC, rowid DESC LIMIT 1")
if [ "$sel" = "task_requires_prose/user" ]; then echo "  ok   and the disclosure record carries the fallback selection"
else echo "  FAIL the disclosure record's fallback selection is '$sel'" >&2; fail=1; fi
# A request that does not select the fallback is refused before anything is scanned or sent.
: > "$SEEN"
rows_unsel=$(dl "SELECT COUNT() FROM disclosure_log")
OUTU=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"text\":\"hello there, please write to $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUTU" in
  *'"fallback_unselected":true'*'"no_custody":"/api/artifact"'*) echo "  ok   an unselected fallback is refused and pointed at the no-custody path" ;;
  *) echo "  FAIL an unselected fallback was not refused: $(printf '%s' "$OUTU" | head -c 200)" >&2; fail=1 ;;
esac
if [ -s "$SEEN" ]; then echo "  FAIL the model received an unselected fallback request" >&2; fail=1; fi
if [ "$(dl "SELECT COUNT() FROM disclosure_log")" = "$rows_unsel" ]; then echo "  ok   and it wrote no disclosure record"
else echo "  FAIL an unselected fallback wrote a disclosure record" >&2; fail=1; fi
# DA1.9 (4): a session id that is not a plain identifier is refused before anything is sent,
# so an address cannot reach the record through it.
OUTS=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"fallback_reason\":\"task_requires_prose\",\"fallback_selected_by\":\"user\",\"session_id\":\"$EMAIL\",\"text\":\"hello there\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUTS" in
  *'"session_invalid":true'*) echo "  ok   a session id that is not a plain identifier is refused" ;;
  *) echo "  FAIL an address as session id was not refused: $(printf '%s' "$OUTS" | head -c 200)" >&2; fail=1 ;;
esac
if [ -s "$SEEN" ] || [ "$(dl "SELECT COUNT() FROM disclosure_log")" != "$rows_unsel" ]; then
  echo "  FAIL a request with an invalid session id reached the model or wrote a record" >&2; fail=1
else echo "  ok   and nothing was sent or recorded"; fi
# NC1.13: a well-formed id loke did not issue is refused too, directly and through moke, and
# nothing is sent or recorded under it.
CODEF=$(curl -s -m 40 -o "$WORK/forged" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d '{"fallback_reason":"task_requires_prose","fallback_selected_by":"user","session_id":"e2e","text":"hello there"}' http://127.0.0.1:11430/api/pipeline)
case "$CODEF $(cat "$WORK/forged")" in
  '400 {"ok":false,"refusal":"session_unissued","error":"session_id was not issued by loke; POST /api/session issues one (NC1.13)"}') echo "  ok   a caller-chosen session id (as DA1.9 accepted) is refused as unissued" ;;
  *) echo "  FAIL a caller-chosen session id was not refused: $CODEF $(head -c 200 "$WORK/forged")" >&2; fail=1 ;;
esac
OUTM=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d '{"prompt":"hello there","session_id":"nc-0123456789abcdef0123456789abcdef"}' http://127.0.0.1:11432/api/pipeline)
case "$OUTM" in
  '{"ok":false,"refusal":"session_unissued"'*) echo "  ok   moke's pipeline passes loke's refusal back for a session loke never issued" ;;
  *) echo "  FAIL moke's pipeline with a session loke never issued: $(printf '%s' "$OUTM" | head -c 200)" >&2; fail=1 ;;
esac
if [ -s "$SEEN" ] || [ "$(dl "SELECT COUNT() FROM disclosure_log")" != "$rows_unsel" ]; then
  echo "  FAIL a request with an unissued session id reached the model or wrote a record" >&2; fail=1
else echo "  ok   and nothing was sent or recorded under either"; fi

# GA5.26: a request carrying restricted data is HELD for approval, not forwarded. The input is
# a card number: core.privacy.pipeline.maxsensitivity classifies CREDIT_CARD as RESTRICTED,
# core.governance.policy.classifyrisk makes RESTRICTED high risk, and evaluate answers
# require-approval for high risk over RESTRICTED. The request is re-sent with the approval id
# before approval, forged, after approval, for another text, and a second time; only the
# approved re-send of the same request reaches the model, once.
: > "$SEEN"
CARD="4111 1111 1111 1111"
CARDTEXT="please check card $CARD against the order"
rows_ap=$(dl "SELECT COUNT() FROM disclosure_log")
pipe_post() {  # $1 text, $2 approval id or ""; sets CODE and BODY
  local out aidf=""
  [ -n "$2" ] && aidf=",\"approval_id\":\"$2\""
  out=$(curl -s -m 40 -w '\n%{http_code}' -X POST -H 'Content-Type: application/json' \
          -d "{\"fallback_reason\":\"user_choice\",\"fallback_selected_by\":\"user\",\"text\":\"$1\"$aidf}" \
          http://127.0.0.1:11430/api/pipeline)
  CODE=${out##*$'\n'}; BODY=${out%$'\n'*}
}
approve_post() {  # $1 approval id, $2 decision; sets CODE and BODY
  local out
  out=$(curl -s -m 20 -w '\n%{http_code}' -X POST -H 'Content-Type: application/json' \
          -d "{\"approval_id\":\"$1\",\"decision\":\"$2\"}" http://127.0.0.1:11430/api/approve)
  CODE=${out##*$'\n'}; BODY=${out%$'\n'*}
}
judge() {  # $1 label, $2 expected status, $3 substring the body must contain
  if [ "$CODE" = "$2" ] && [[ "$BODY" == *"$3"* ]]; then echo "  ok   $1 [$CODE]"
  else echo "  FAIL $1: got [$CODE] $(printf '%s' "$BODY" | head -c 300), expected [$2] containing $3" >&2; fail=1; fi
}
pipe_post "$CARDTEXT" ""
judge "a restricted request is held for approval, not forwarded" 409 '"approval_required":true'
AID=$(printf '%s' "$BODY" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("approval_id",""))
except Exception: print("")')
if [[ "$AID" =~ ^[0-9a-f]{32}$ ]]; then echo "  ok   and it carries a 32-hex approval id"
else echo "  FAIL the held response carries no usable approval id: '$AID'" >&2; fail=1; fi
if [[ "$BODY" == *'"sensitivity":"restricted"'* ]] && [[ "$BODY" == *'"entity_types":"'*credit_card* || "$BODY" == *'"entity_types":"'*CREDIT_CARD* ]]; then
  echo "  ok   and it names the sensitivity and the entity type"
else echo "  FAIL the held response does not name the sensitivity and entity type: $(printf '%s' "$BODY" | head -c 300)" >&2; fail=1; fi
case "$BODY" in *"$CARD"*|*4111*) echo "  FAIL the held response echoes the card number" >&2; fail=1 ;; esac
if [ -s "$SEEN" ]; then echo "  FAIL the model received a request that was held for approval" >&2; fail=1
else echo "  ok   and nothing reached the model"; fi
if [ "$(dl "SELECT COUNT() FROM disclosure_log")" = "$rows_ap" ]; then echo "  ok   and it wrote no disclosure record"
else echo "  FAIL a held request wrote a disclosure record" >&2; fail=1; fi
if [ "$(dl "SELECT COUNT() FROM audit_log WHERE event_type='policy_require_approval'")" -ge 1 ] \
   && [ "$(dl "SELECT approval_outcome FROM decision_trace WHERE outcome='policy_require_approval' ORDER BY created_at_ms DESC, rowid DESC LIMIT 1")" = "held_pending" ]; then
  echo "  ok   the hold is audited as policy_require_approval and traced as held_pending"
else echo "  FAIL the hold is not in the audit trail and decision trace" >&2; fail=1; fi
if [ "$(dl "SELECT state FROM approval_requests WHERE approval_id='$AID'")" = "pending" ] \
   && [ "$(dl "SELECT COUNT() FROM approval_requests WHERE instr(approval_id||binding||state, '4111')>0 OR instr(approval_id||binding||state, 'check')>0")" = "0" ]; then
  echo "  ok   the approval is stored pending, with no text and no card number"
else echo "  FAIL the stored approval is not pending, or holds text" >&2; fail=1; fi

pipe_post "$CARDTEXT" "$AID"
judge "re-sent before approval, it is refused" 403 '"approval_refusal":"not_approved"'
pipe_post "$CARDTEXT" "0123456789abcdef0123456789abcdef"
judge "re-sent with a forged id, it is refused" 403 '"approval_refusal":"unknown"'
approve_post "$AID" approve
judge "the user approves it through /api/approve" 200 '"action":"approved"'
approve_post "$AID" approve
judge "approving it twice changes nothing" 409 '"reason":"already_approved"'
pipe_post "please check card $CARD against the invoice" "$AID"
judge "the approval does not let a different request through" 403 '"approval_refusal":"mismatch"'
if [ -s "$SEEN" ]; then echo "  FAIL the model received a request before a valid approval was spent" >&2; fail=1
else echo "  ok   and none of those reached the model"; fi

pipe_post "$CARDTEXT" "$AID"
judge "the approved request, re-sent with its id, is answered" 200 '"ok":true'
case "$BODY" in
  *"$CARD"*) echo "  ok   and the user gets the card number back, restored" ;;
  *) echo "  FAIL the approved answer was not restored: $(printf '%s' "$BODY" | head -c 300)" >&2; fail=1 ;;
esac
if grep -q '^/api/generate .*\[CREDIT_CARD_[0-9a-f]*_1\]' "$SEEN" && ! grep -q "$CARD" "$SEEN"; then
  echo "  ok   the model received it once, anonymised"
else echo "  FAIL the model did not receive the approved request anonymised" >&2; fail=1; fi
if [ "$(dl "SELECT approval_outcome FROM decision_trace WHERE outcome='llm_request' ORDER BY created_at_ms DESC, rowid DESC LIMIT 1")" = "approved" ]; then
  echo "  ok   and it is traced as approved"
else echo "  FAIL the forwarded request is not traced as approved" >&2; fail=1; fi
: > "$SEEN"
pipe_post "$CARDTEXT" "$AID"
judge "the same approval used a second time is refused" 403 '"approval_refusal":"already_used"'
if [ -s "$SEEN" ]; then echo "  FAIL a reused approval reached the model" >&2; fail=1; fi

pipe_post "$CARDTEXT" ""
AID2=$(printf '%s' "$BODY" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("approval_id",""))
except Exception: print("")')
approve_post "$AID2" approve
sqlite3 "$DB" "UPDATE approval_requests SET expires_at_ms=1 WHERE approval_id='$AID2'"
pipe_post "$CARDTEXT" "$AID2"
judge "an expired approval is refused" 403 '"approval_refusal":"expired"'
pipe_post "$CARDTEXT" ""
AID3=$(printf '%s' "$BODY" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("approval_id",""))
except Exception: print("")')
approve_post "$AID3" decline
judge "the user can decline instead" 200 '"action":"declined"'
pipe_post "$CARDTEXT" "$AID3"
judge "and a declined approval is refused" 403 '"approval_refusal":"declined"'
if [ -s "$SEEN" ]; then echo "  FAIL an expired or declined approval reached the model" >&2; fail=1; fi

# DA1.9 follow-up: overlapping requests. Each server worker has its own connection to loke.db,
# and without a busy timeout a reserve that met another worker's lock failed at once, so the
# request was refused with 503 ("the disclosure record could not be written"). Measured: four
# of eight concurrent requests. smoke_ui's cancel-then-send checks overlap two requests, which
# is why it failed intermittently. Every request here carries an address, so none can be a
# cache hit, and all must be dispatched and recorded in both tables. With the timeout set
# only after openstore's liveness check, the check itself still failed now and then (a
# completion went missing in 1 of 6); that shows as "could not be opened" in loke's log.
CONC=12
disp_before=$(dl "SELECT COUNT() FROM disclosure_log WHERE state='completed'")
aud_before=$(dl "SELECT COUNT() FROM audit_log WHERE event_type='llm_dispatch'")
for i in $(seq 1 $CONC); do
  curl -s -m 60 -o "$WORK/conc$i" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
    -d "{\"fallback_reason\":\"task_requires_prose\",\"fallback_selected_by\":\"user\",\"text\":\"hello there, please write to $EMAIL about item $i\"}" \
    http://127.0.0.1:11430/api/pipeline > "$WORK/conccode$i" & CPIDS="${CPIDS:-} $!"
done
for p in $CPIDS; do wait "$p"; done
codes=$(cat "$WORK"/conccode* | tr -d '\n')
if [ "$codes" = "$(printf '200%.0s' $(seq 1 $CONC))" ]; then echo "  ok   $CONC overlapping requests are all answered"
else echo "  FAIL overlapping requests answered $codes: $(grep -h -o '"error":"[^"]*"' "$WORK"/conc[0-9]* | sort | uniq -c | head -3)" >&2; fail=1; fi
disp_after=$(dl "SELECT COUNT() FROM disclosure_log WHERE state='completed'")
aud_after=$(dl "SELECT COUNT() FROM audit_log WHERE event_type='llm_dispatch'")
if [ $((disp_after - disp_before)) -eq $CONC ] && [ $((aud_after - aud_before)) -eq $CONC ]; then
  echo "  ok   and each wrote its completed disclosure record and its llm_dispatch audit row"
else echo "  FAIL overlapping requests wrote $((disp_after - disp_before)) completed records and $((aud_after - aud_before)) llm_dispatch rows, not $CONC" >&2; fail=1; fi
opened=$(grep -c "the database could not be opened" "$WORK/lk/home/.loke/loke.log" 2>/dev/null)
if [ "${opened:-0}" = "0" ]; then echo "  ok   and no request found the database locked when it opened it"
else echo "  FAIL loke logged 'the database could not be opened' $opened time(s): a connection met a lock with no busy timeout" >&2; fail=1; fi

# NC1.12: the no-custody dispatch, over real HTTP. A request that carries its dataset
# (headers and rows, which stay on this machine) is tried no-custody first. loke checks the
# exact body it would send against every cell (spec C2), and only a body holding none is sent
# and recorded no-custody with custody_check sentinel_pass. The dataset has a planted sentinel.
NCSENT="ZQ-SENTINEL-$$"
NCDATA="\"dataset_name\":\"accounts\",\"headers\":[\"customer\",\"region\",\"plan\"],\"rows\":[[\"$NCSENT\",\"northern\",\"gold\"],[\"Harriet Oyelaran\",\"southern\",\"silver\"]]"
NCPROF="DATASET: accounts | ROWS: 2 | COLS: 3\\nCOLS: customer(text,nulls=0%,distinct=2,unique) region(text,nulls=0%,distinct=2,low) plan(text,nulls=0%,distinct=2,low)"
nc_seen_clean() {  # every cell of at least 4 bytes is absent from what the model received
  for v in "$NCSENT" "Harriet Oyelaran" northern southern gold silver; do
    grep -qi -- "$v" "$SEEN" && return 1
  done
  return 0
}
nc_last() { dl "SELECT $1 FROM disclosure_log WHERE correlation_id LIKE '%-nc' ORDER BY rowid DESC LIMIT 1"; }
: > "$SEEN"
rows_nc=$(dl "SELECT COUNT() FROM disclosure_log")
NCSID=$(curl -s -m 20 -X POST -d '{}' http://127.0.0.1:11430/api/session | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("session_id",""))
except Exception: print("")')
OUTN=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{$NCDATA,\"profile\":\"$NCPROF\",\"text\":\"$NCPROF\\n\\nWhich region has the most customers?\",\"session_id\":\"$NCSID\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUTN" in
  *'"ok":true,"custody":"no-custody","custody_check":"sentinel_pass"'*) echo "  ok   a profile and a question with the dataset attached are answered no-custody, with no fallback selected" ;;
  *) echo "  FAIL the no-custody request was not answered no-custody: $(printf '%s' "$OUTN" | head -c 300)" >&2; fail=1 ;;
esac
if grep -q '^/api/generate .*Which region has the most customers' "$SEEN" && nc_seen_clean; then
  echo "  ok   the model received the profile and question, and no cell of the dataset (the sentinel included)"
else echo "  FAIL the model did not receive the question, or received a value from the dataset" >&2; fail=1; fi
nc_bytes=$(python3 -c 'import sys
for line in open(sys.argv[1],encoding="utf-8"):
    if line.startswith("/api/generate "): print(len(line[len("/api/generate "):].rstrip("\n").encode("utf-8"))); break' "$SEEN")
ncrec=$(nc_last "custody||' '||custody_check||' '||state||' '||provider_class||' '||bytes_body||' '||session_id||' '||real_values_included")
if [ -n "$nc_bytes" ] && [ -n "$NCSID" ] && [ "$ncrec" = "no-custody sentinel_pass completed local $nc_bytes $NCSID 0" ]; then
  echo "  ok   its disclosure row: $ncrec (bytes_body is what the model received)"
else echo "  FAIL the no-custody disclosure row is '$ncrec' for $nc_bytes octets received" >&2; fail=1; fi
if [ "$(dl "SELECT COUNT() FROM disclosure_log")" = "$((rows_nc + 1))" ]; then echo "  ok   and it is the only row the request wrote: the fallback was not taken"
else echo "  FAIL the no-custody request wrote $(( $(dl "SELECT COUNT() FROM disclosure_log") - rows_nc )) rows" >&2; fail=1; fi

# A value from the dataset in the question: refused as sentinel_fail, recorded raw, nothing sent.
: > "$SEEN"
CODE=$(curl -s -m 40 -o "$WORK/ncfail" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d "{$NCDATA,\"profile\":\"$NCPROF\",\"text\":\"$NCPROF\\n\\nWhy is $NCSENT on the gold plan?\"}" http://127.0.0.1:11430/api/pipeline)
BODY=$(cat "$WORK/ncfail")
case "$CODE $BODY" in
  "422 "*'"refusal":"sentinel_fail"'*'"fallback_unselected":true'*) echo "  ok   a body holding a dataset value is refused as sentinel_fail (422), and no fallback is taken unselected" ;;
  *) echo "  FAIL a body holding a dataset value was not refused: $CODE $(printf '%s' "$BODY" | head -c 300)" >&2; fail=1 ;;
esac
if grep -q '^/api/generate' "$SEEN"; then echo "  FAIL the refused body reached the model" >&2; fail=1
else echo "  ok   and nothing reached the model"; fi
ncrec=$(nc_last "custody||' '||custody_check||' '||state||' '||outcome||' '||bytes_body")
if [ "$ncrec" = "raw sentinel_fail failed rejected_locally 0" ]; then echo "  ok   its disclosure row: $ncrec"
else echo "  FAIL the refused dispatch's row is '$ncrec'" >&2; fail=1; fi

# The same with the fallback selected: no-custody is refused first, then the fallback runs,
# and each is recorded as what it was.
: > "$SEEN"
OUTF=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{$NCDATA,\"profile\":\"$NCPROF\",\"text\":\"$NCPROF\\n\\nWhy is $NCSENT on the gold plan?\",\"fallback_reason\":\"task_requires_prose\",\"fallback_selected_by\":\"user\"}" http://127.0.0.1:11430/api/pipeline)
fbrec=$(dl "SELECT custody||' '||fallback_reason FROM disclosure_log ORDER BY rowid DESC LIMIT 1")
ncrec=$(nc_last "custody_check")
case "$OUTF" in
  *'"ok":true'*'"custody":"redacted-data"'*)
    if [ "$fbrec" = "redacted-data task_requires_prose" ] && [ "$ncrec" = "sentinel_fail" ]; then
      echo "  ok   with the fallback selected, the no-custody refusal is recorded and then the fallback is taken, recorded as redacted-data"
    else echo "  FAIL the fallback's records are '$fbrec' after a no-custody check of '$ncrec'" >&2; fail=1; fi ;;
  *) echo "  FAIL the selected fallback did not run after the no-custody refusal: $(printf '%s' "$OUTF" | head -c 300)" >&2; fail=1 ;;
esac

# A cloud route is refused citing T-58, and nothing is sent.
: > "$SEEN"
CODE=$(curl -s -m 40 -o "$WORK/nccloud" -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
        -d "{$NCDATA,\"provider\":\"anthropic\",\"text\":\"Which region has the most customers?\"}" http://127.0.0.1:11430/api/pipeline)
case "$CODE $(cat "$WORK/nccloud")" in
  "403 "*'"refusal":"cloud_route_refused"'*T-58*) echo "  ok   a no-custody request for a cloud provider is refused (403), citing T-58" ;;
  *) echo "  FAIL a cloud no-custody route was not refused: $CODE $(head -c 300 "$WORK/nccloud")" >&2; fail=1 ;;
esac
if grep -q '^/api/generate' "$SEEN"; then echo "  FAIL the cloud-routed request reached a model" >&2; fail=1
else echo "  ok   and nothing was sent"; fi

# moke's Insight Lab proposal, with the loaded dataset: moke sends column names only, and loke
# dispatches it no-custody rather than to the fallback.
: > "$SEEN"
nc_before=$(dl "SELECT COUNT() FROM disclosure_log WHERE custody='no-custody'")
OUTP2=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"num_cols\":[],\"cat_cols\":[\"region\",\"plan\"],$NCDATA}" http://127.0.0.1:11432/api/ml/propose)
nc_after=$(dl "SELECT COUNT() FROM disclosure_log WHERE custody='no-custody'")
if [ "$nc_after" = "$((nc_before + 1))" ] && grep -q '^/api/generate' "$SEEN" && nc_seen_clean; then
  echo "  ok   the Insight Lab's proposal request is dispatched no-custody, and the model received no cell"
else echo "  FAIL the proposal request was not dispatched no-custody ($nc_before -> $nc_after rows): $(printf '%s' "$OUTP2" | head -c 200)" >&2; fail=1; fi

# T10.1: with the per-provider kill switch engaged for ollama, the same request is refused
# with the fallback message and nothing reaches the model. The row is written as
# killswitch.engageprovider writes it.
: > "$SEEN"
sqlite3 "$DB" "INSERT OR REPLACE INTO settings (key,value,value_type,namespace,updated_at) VALUES ('governance.kill_switch.provider.ollama','true','bool','governance',datetime('now'))"
OUT4=$(curl -s -m 40 -X POST -H 'Content-Type: application/json' \
        -d "{\"fallback_reason\":\"task_requires_prose\",\"fallback_selected_by\":\"user\",\"text\":\"hello there, please write to $EMAIL\"}" http://127.0.0.1:11430/api/pipeline)
case "$OUT4" in
  *'"provider_blocked":true'*) echo "  ok   with ollama switched off, the request is refused with the fallback message" ;;
  *) echo "  FAIL a switched-off provider was not refused: $(printf '%s' "$OUT4" | head -c 200)" >&2; fail=1 ;;
esac
if grep -q '^/api/generate' "$SEEN"; then echo "  FAIL a request reached the switched-off provider" >&2; fail=1
else echo "  ok   and nothing reached the model"; fi
if [ -n "$rows" ] && [ "$rows_after" = "$rows" ]; then
  echo "  ok   and the refusal, which sent nothing, wrote no disclosure record"
else echo "  FAIL disclosure_log went from '${rows}' to '${rows_after}' rows across a refused request" >&2; fail=1; fi

# G1.6: the per-use-case switch, engaged through the real CLI against the running server's
# database. ollama is switched back on first, so only the use-case switch can refuse. The
# request is refused before it is scanned: neither the model nor the NER layer is asked.
sqlite3 "$DB" "UPDATE settings SET value='false' WHERE key='governance.kill_switch.provider.ollama'"
CLI_BIN="$ROOT/build/trees/loke-cli/loke-cli"
if [ ! -x "$CLI_BIN" ]; then echo "  FAIL $CLI_BIN not built (scripts/build_trees.sh loke-cli)" >&2; fail=1
else
  if HOME="$WORK/lk/home" "$CLI_BIN" kill-switch on --use-case browser-chat >/dev/null 2>&1; then
    echo "  ok   loke kill-switch on --use-case browser-chat succeeds"
  else echo "  FAIL loke kill-switch on --use-case browser-chat exited non-zero" >&2; fail=1; fi
  : > "$SEEN"; : > "$SEEN.ner"
  pipe_post "hello there, please write to $EMAIL" ""
  judge "with the browser-chat use case switched off, the request is refused" 403 '"kill_switch_scope":"use_case"'
  judge "with a message that names the use case" 403 'The browser-chat use case is switched off by the kill switch'
  if [ -s "$SEEN" ] || grep -qs . "$SEEN.ner"; then echo "  FAIL a request for a switched-off use case reached a model" >&2; fail=1
  else echo "  ok   and nothing reached the model, not even the NER layer"; fi
  ucaud=$(dl "SELECT COUNT() FROM audit_log WHERE event_type='kill_switch_refused' AND correlation_id='use_case:browser-chat'")
  ucset=$(dl "SELECT COUNT() FROM audit_log WHERE event_type='kill_switch_engaged' AND use_case='browser-chat'")
  if [ "$ucaud" = "1" ] && [ "$ucset" = "1" ]; then echo "  ok   the switch and the refusal are each in the audit trail"
  else echo "  FAIL audit rows for the use-case switch: engaged '$ucset', refused '$ucaud', expected 1 and 1" >&2; fail=1; fi
  HOME="$WORK/lk/home" "$CLI_BIN" kill-switch off --use-case browser-chat >/dev/null 2>&1
  pipe_post "hello there, please write to $EMAIL" ""
  judge "released, the same request is answered again" 200 '"ok":true'
fi

# F3b.3: the privacy-filter sidecar as a detection layer of the pipeline. http_recorder.py
# stands in for packages/privacy-filter/server.py (OS-assigned loopback port): it answers
# /health, and /detect with "Jane Citizen" (private_person, 0.95) and "Tuesday" (0.4),
# applying the request's threshold. Regex does not find a name and the fake NER model answers
# [], so if the model does not receive the name it is because this layer found it. The layer
# is switched on the way an operator would, in config.toml, which the /api/pipeline handler
# reads per request; nothing before this point ran with it.
PF_LOG="$WORK/pf.log"
# The Ollama stand-in back to its starting model list (F5.12 above left it listing only
# gemma3:4b), so the router's default choice is installed and the request is dispatched.
pkill -f "scripts/lib/fake_ollama.py $SEEN" 2>/dev/null; sleep 0.5
FAKE_OLLAMA_DIGESTS="qwen2.5:7b=$QWEN_DIGEST,llama3:latest=$LLAMA_DIGEST" \
  python3 "$ROOT/scripts/lib/fake_ollama.py" "$SEEN" >/dev/null 2>&1 & PIDS="$PIDS $!"
for _ in $(seq 1 20); do nc -z -G 1 127.0.0.1 11434 2>/dev/null && break; sleep 0.25; done
python3 "$ROOT/scripts/lib/http_recorder.py" "$PF_LOG" "$WORK/pf.port" >/dev/null 2>&1 & PF_PID=$!; PIDS="$PIDS $PF_PID"
for _ in $(seq 1 40); do [ -s "$WORK/pf.port" ] && break; sleep 0.25; done
PF_PORT=$(cat "$WORK/pf.port" 2>/dev/null)
mkdir -p "$WORK/lk/home/.loke"
if [ -z "$PF_PORT" ]; then echo "  FAIL the privacy-filter stand-in did not start" >&2; fail=1
elif [ -e "$WORK/lk/home/.loke/config.toml" ]; then echo "  FAIL a config.toml already exists in the throwaway HOME; this check would not own it" >&2; fail=1
else
  printf '[privacy]\nprivacy_filter = true\nprivacy_filter_url = "http://127.0.0.1:%s"\nprivacy_filter_threshold = "0.5"\n' "$PF_PORT" > "$WORK/lk/home/.loke/config.toml"
  PFNAME="Jane Citizen"
  : > "$SEEN"; : > "$SEEN.ner"
  pipe_post "summarise what $PFNAME asked about the invoice" ""
  judge "with the privacy filter configured, the request is answered" 200 '"ok":true'
  if grep -q '^GET /health' "$PF_LOG" && grep -q "^POST /detect .*$PFNAME.*\"threshold\":0.5" "$PF_LOG"; then
    echo "  ok   the pipeline asked the privacy filter, at the configured operating point"
  else echo "  FAIL the privacy filter was not asked: $(head -c 300 "$PF_LOG" 2>/dev/null)" >&2; fail=1; fi
  if [ ! -s "$SEEN" ]; then echo "  FAIL the model received no request with the privacy filter on" >&2; fail=1
  elif grep -q "$PFNAME" "$SEEN"; then echo "  FAIL the MODEL received the name the privacy filter found, in clear" >&2; fail=1
  else echo "  ok   the model did not receive the name; it saw: $(grep -o '\[PERSON_[0-9a-f]*_[0-9]*\]' "$SEEN" | head -1)"; fi
  if grep -q '\[PERSON_[0-9a-f]*_[0-9]*\]' "$SEEN"; then echo "  ok   in its place a PERSON placeholder, the pipeline's own type for the sidecar's private_person"
  else echo "  FAIL no PERSON placeholder reached the model" >&2; fail=1; fi
  case "$BODY" in
    *"$PFNAME"*) echo "  ok   and the user got the name back, restored" ;;
    *) echo "  FAIL the response did not restore the name: $(printf '%s' "$BODY" | head -c 300)" >&2; fail=1 ;;
  esac
  pflayers=$(dl "SELECT detection_layers FROM disclosure_log ORDER BY rowid DESC LIMIT 1")
  case "$pflayers" in
    scanned=*privacy_filter*\;skipped=*) echo "  ok   the disclosure record names privacy_filter among the layers that scanned: $pflayers" ;;
    *) echo "  FAIL the disclosure record's detection layers are '$pflayers'" >&2; fail=1 ;;
  esac
  # The sidecar down: the layer is degraded, recorded as skipped, and nothing claims it scanned.
  kill "$PF_PID" 2>/dev/null; wait "$PF_PID" 2>/dev/null
  pipe_post "summarise what $PFNAME asked about the invoice" ""
  judge "with the privacy filter down and other layers completing, the request is still answered (degraded)" 200 '"layers_degraded":'
  pflayers=$(dl "SELECT detection_layers FROM disclosure_log ORDER BY rowid DESC LIMIT 1")
  case "$pflayers" in
    *skipped=*privacy_filter*) echo "  ok   and the record lists privacy_filter as skipped: $pflayers" ;;
    *) echo "  FAIL with the sidecar down the detection layers are '$pflayers'" >&2; fail=1 ;;
  esac
  rm -f "$WORK/lk/home/.loke/config.toml"
fi
# GA1.5: the token optimiser, between the privacy filter and dispatch. scripts/lib/http_recorder.py
# stands in for the LLMLingua sidecar: in `echo` mode it keeps every placeholder and every other
# word; in `answer` mode it answers "short", dropping the placeholder. It is configured the way a
# user would, by the settings rows the handler reads. Judged: what the sidecar was sent (never
# the address), what the model received (compressed, or not), the restored answer, the answer's
# own report, and that the disclosure record's bytes are the octets the model received.
ll_start() {  # $1 mode; sets LLPORT and LLLOG
  LLLOG="$WORK/lingua_$1.log"; rm -f "$WORK/lingua_$1.port"
  python3 "$ROOT/scripts/lib/http_recorder.py" "$LLLOG" "$WORK/lingua_$1.port" "$1" >/dev/null 2>&1 & PIDS="$PIDS $!"
  for _ in $(seq 1 40); do [ -s "$WORK/lingua_$1.port" ] && break; sleep 0.25; done
  LLPORT=$(cat "$WORK/lingua_$1.port" 2>/dev/null)
  sqlite3 "$DB" "INSERT OR REPLACE INTO settings (key,value,value_type,namespace,updated_at) VALUES ('optimiser.llmlingua_url','http://127.0.0.1:$LLPORT','str','optimiser',datetime('now'))"
}
model_body() {  # the body of the last /api/generate the model received
  python3 -c 'import sys
b=""
for line in open(sys.argv[1],encoding="utf-8"):
    if line.startswith("/api/generate "): b=line[len("/api/generate "):].rstrip("\n")
print(b)' "$SEEN"
}
sqlite3 "$DB" "INSERT OR REPLACE INTO settings (key,value,value_type,namespace,updated_at) VALUES ('optimiser.llmlingua_min_chars','40','int','optimiser',datetime('now'))"
LONGTEXT="please write to $EMAIL about the overdue invoice from last month and ask them to confirm the payment date"
ll_start echo
: > "$SEEN"
pipe_post "$LONGTEXT" ""
judge "GA1.5: with an LLMLingua sidecar configured, a long prompt is answered" 200 '"ok":true'
judge "and the answer reports the compression it measured" 200 '"optimisation":{"method":"llmlingua","applied":true,"reason":"","bytes_before":'
judge "and restores the address the model was given as a placeholder" 200 "$EMAIL"
mb=$(model_body)
if grep -q 'POST /compress .*invoice' "$LLLOG" && ! grep -q "$EMAIL" "$LLLOG"; then
  echo "  ok   the sidecar was sent the anonymised prompt, never the address"
else echo "  FAIL the sidecar was not sent the anonymised prompt, or was sent the address" >&2; fail=1; fi
if [ -n "$mb" ] && [[ "$mb" != *invoice* ]] && [[ "$mb" != *payment* ]] && [[ "$mb" == *'[EMAIL_'* ]] && [[ "$mb" != *"$EMAIL"* ]]; then
  echo "  ok   the model received the compressed prompt, placeholder intact"
else echo "  FAIL the model did not receive the compressed prompt: $(printf '%s' "$mb" | head -c 200)" >&2; fail=1; fi
mbytes=$(printf '%s' "$mb" | python3 -c 'import sys; print(len(sys.stdin.buffer.read()))')
lastbytes=$(dl "SELECT bytes_body FROM disclosure_log ORDER BY occurred_at DESC, rowid DESC LIMIT 1")
if [ "$lastbytes" = "$mbytes" ] && [[ "$BODY" == *"\"disclosure\":{\"bytes_body\":$mbytes,"* ]]; then
  echo "  ok   its disclosure record and its answer both say $mbytes bytes, the octets the model received"
else echo "  FAIL disclosure bytes '$lastbytes' do not match the $mbytes octets the model received" >&2; fail=1; fi
stages=$(dl "SELECT savings_by_stage FROM metrics_raw ORDER BY rowid DESC LIMIT 1")
case "$stages" in
  optimiser=llmlingua\;bytes=*) echo "  ok   and its metrics row records the compression: $stages" ;;
  *) echo "  FAIL the metrics row does not record the compression: '$stages'" >&2; fail=1 ;;
esac
ll_start answer
: > "$SEEN"
pipe_post "$LONGTEXT" ""
judge "a sidecar that drops the placeholder is refused, and the request still answered" 200 '"optimisation":{"method":"none","applied":false,"reason":"placeholder_lost'
judge "with the address restored" 200 "$EMAIL"
mb=$(model_body)
if [[ "$mb" == *invoice* ]] && [[ "$mb" == *'[EMAIL_'* ]] && [[ "$mb" != *'"prompt":"short"'* ]]; then
  echo "  ok   and the model received the whole anonymised prompt, not the compression"
else echo "  FAIL the model did not receive the uncompressed prompt: $(printf '%s' "$mb" | head -c 200)" >&2; fail=1; fi
sqlite3 "$DB" "DELETE FROM settings WHERE key IN ('optimiser.llmlingua_url','optimiser.llmlingua_min_chars')"

[ "$fail" -eq 0 ] || { echo "smoke_e2e: FAILED" >&2; exit 1; }
echo "smoke_e2e: OK — anonymised on the way out, restored on the way back"
