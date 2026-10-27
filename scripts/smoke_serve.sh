#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_serve.sh — start the built loke binary and make one real HTTP request to each
# route. Fails if any request gets no response at all. (F10.36)
#
# Why this exists: on 2026-09-24 every unit test passed while /api/health, /api/models,
# /api/pipeline, /privacy, /savings and /pipeline each killed the server worker on their
# first request. The tests call handler functions directly, so none of them ever went
# through ooke's accept loop, and that was where the fault was. ooke's objects had been
# compiled by an older toke that declared tk_current_error as a plain global, and the
# first write to it zeroed the runtime's thread-local thunk. A handler test cannot see
# that class of failure. One real request per route can.
#
# It checks only that each route ANSWERS: some HTTP status comes back and not an empty
# reply. It does not judge the body. A 502 from /api/pipeline with no provider running
# is a correct answer and passes. A dropped connection fails.
#
# It serves a copy on port $SMOKE_PORT (default 11499), so it never collides with a
# loke already running on 11430.
#
#   scripts/smoke_serve.sh            # uses packages/browser/build/loke

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/packages/browser"
BIN="$SRC/build/loke"
PORT="${SMOKE_PORT:-11499}"

[ -x "$BIN" ] || { echo "smoke_serve: $BIN not built; run scripts/build_loke.sh" >&2; exit 1; }

# It serves on its own port, but what it serves is a CLIENT of the fixed ports: its /api/pipeline dispatches to Ollama at 127.0.0.1:11434. So
# it takes the fixed-port lock that smoke_e2e.sh and smoke_ui.sh hold. Without it, a run
# overlapping another worktree's smoke_e2e sent that smoke's servers requests it had not made:
# measured on 2026-09-27, an extra disclosure row ("hello") and a proposal request reaching
# the fake model, which failed smoke_e2e's counts. Found by the DA1.9 follow-up.
. "$ROOT/scripts/lib/fixedports_lock.sh"
acquire_fixedports || { echo "smoke_serve: could not get the fixed-port lock" >&2; exit 1; }

# F10.38: refuse to start on a port something already holds. Another worker's fake Ollama
# once held this port; the server failed to bind and the probes below were answered by the
# fake. Checked after taking the lock, so the holder is not one of our own smokes.
. "$ROOT/scripts/lib/port_owner.sh"
refuse_if_port_busy smoke_serve "$PORT" || { release_fixedports; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_smoke.XXXXXX")
PID=
cleanup() { [ -n "$PID" ] && kill "$PID" 2>/dev/null; pkill -f "$WORK/loke" 2>/dev/null; rm -rf "$WORK"; release_fixedports; }
trap cleanup EXIT INT TERM

for d in pages templates static; do [ -d "$SRC/$d" ] && cp -R "$SRC/$d" "$WORK/"; done
cp "$BIN" "$WORK/loke"
sed -E "s/^([[:space:]]*port[[:space:]]*=).*/\1 $PORT/" "$SRC/ooke.toml" > "$WORK/ooke.toml"

# A throwaway HOME. loke reads ~/.loke/settings.json for provider keys, so with the real
# HOME a smoke POST to /api/pipeline could be routed to a cloud provider on the
# developer's account. It also keeps the smoke run out of the real audit trail and log.
mkdir -p "$WORK/home"
( cd "$WORK" && HOME="$WORK/home" exec ./loke > "$WORK/serve.log" 2>&1 ) &
PID=$!

up=0
for _ in $(seq 1 40); do
  if curl -s -o /dev/null -m 1 "http://127.0.0.1:$PORT/"; then up=1; break; fi
  sleep 0.25
done
if [ "$up" -ne 1 ]; then
  echo "smoke_serve: the server never answered on port $PORT" >&2
  tail -5 "$WORK/serve.log" >&2
  exit 1
fi
# F10.38: something answered; confirm it is the loke this script started.
assert_port_owner smoke_serve "$PORT" "$PID" || { tail -5 "$WORK/serve.log" >&2; exit 1; }

fail=0
probe() {  # $1 method, $2 path, $3 optional body
  local code
  if [ "$1" = POST ]; then
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 -X POST \
             -H 'Content-Type: application/json' -d "$3" "http://127.0.0.1:$PORT$2")
  else
    code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 "http://127.0.0.1:$PORT$2")
  fi
  if [ "$code" = "000" ]; then
    echo "  FAIL $1 $2: no response; the worker died or the connection dropped" >&2
    fail=1
  else
    echo "  ok   $1 $2 [$code]"
  fi
}

for r in health models settings savings tabs privacy layermetrics privacylayers privacymodels; do probe GET "/api/$r"; done
probe POST /api/pipeline '{"text":"smoke test, no personal data","fallback_reason":"user_choice","fallback_selected_by":"user"}'
for p in / /privacy /savings /pipeline /chat /setup /installer /approve /tabs /sysmon /evaluate; do probe GET "$p"; done

# F10.8: ooke rc.2's template engine ignores a directive it does not know. /tabs and /privacy
# closed their blocks with `endblock` and `/block`, so each answered 200 with the base layout
# alone; /installer's `raw` rendered nothing. A status says none of that, so judge the body.
page() {  # $1 path, $2 substring the body must contain, $3 label
  local body
  body=$(curl -s -m 20 "http://127.0.0.1:$PORT$1")
  if [[ "$body" != *"$2"* ]] || [[ "$body" == *"<title></title>"* ]]; then
    echo "  FAIL GET $1: $3 (no '$2', or an empty title)" >&2; fail=1
  else
    echo "  ok   GET $1: $3"
  fi
}
page /tabs '.tabs-layout' 'renders its content block and title'
page /privacy '.privacy-hero' 'renders its content block and title'
page /installer 'data-hardware="{&quot;chip&quot;:' 'hands the measured hardware JSON to the page'
page /evaluate 'id="ev-layers"' 'renders the layer comparison panel (F3b.9)'

# BG1.2: /sysmon answered 200 with an empty body (the snapshot went to a template that never
# printed it), and the snapshot itself read 0 MB used and 0% CPU on every machine. Each figure
# is judged against the machine's own readings; the tolerances are explained in the script.
python3 "$ROOT/scripts/lib/sysmon_check.py" "http://127.0.0.1:$PORT/sysmon" --loke-parent "$PID" || fail=1

# NC1.7: /api/artifact runs a returned artifact locally. Unlike the probes above, these judge
# the body, because "it answered" says nothing about whether the value was bound or the
# column was checked.
artifact() {  # $1 label, $2 body, $3 expected status, $4 substring the body must contain
  local out code body
  out=$(curl -s -m 20 -w '\n%{http_code}' -X POST -H 'Content-Type: application/json' \
          -d "$2" "http://127.0.0.1:$PORT/api/artifact")
  code=${out##*$'\n'}; body=${out%$'\n'*}
  if [ "$code" != "$3" ] || [[ "$body" != *"$4"* ]]; then
    echo "  FAIL POST /api/artifact ($1): got [$code] $body, expected [$3] containing $4" >&2
    fail=1
  else
    echo "  ok   POST /api/artifact ($1) [$code]"
  fi
}
# NC1.13: loke issues the session. Every artifact below runs under an id POST /api/session
# handed out; a caller-chosen one is refused.
issue_session() {
  curl -s -m 20 -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:$PORT/api/session" \
    | python3 -c 'import json,sys
try:
  d=json.load(sys.stdin); s=d.get("session_id","")
  print(s if d.get("ok") and s.startswith("nc-") and len(s)==35 and d.get("expires_in_s")==86400 else "")
except Exception: print("")'
}
S1=$(issue_session)
S2=$(issue_session)
if [ -n "$S1" ] && [ -n "$S2" ] && [ "$S1" != "$S2" ]; then
  echo "  ok   POST /api/session issues distinct nc- ids with a 24 hour lifetime"
else
  echo "  FAIL POST /api/session did not issue two distinct session ids: '$S1' '$S2'" >&2; fail=1
fi
DS='"headers":["region","amount","note"],"rows":[["north","10","a"],["south","2.5","b"],["north","5","c"]]'
SID="\"session_id\":\"$S1\""
artifact "sum where region = north" \
  "{$SID,\"artifact\":{\"op\":\"sum\",\"column\":\"amount\",\"filter_col\":\"region\",\"filter_val\":\"north\"},$DS}" \
  200 '"values":["15.0"]'
artifact "a quote in the value is data" \
  "{$SID,\"artifact\":{\"op\":\"count\",\"filter_col\":\"region\",\"filter_val\":\"x' OR '1'='1\"},$DS}" \
  200 '"values":["0"]'
artifact "a column the dataset lacks" \
  "{$SID,\"artifact\":{\"op\":\"sum\",\"column\":\"salary\"},$DS}" \
  422 'not in the dataset'
artifact "no artifact" "{$SID,$DS}" 400 'missing required field: artifact'
artifact "an answer carries the session cumulative" \
  "{$SID,\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DS}" \
  200 '"session_rows_released":3,"session_cells_released":3'

# NC1.10: no session, no run; and a sequence guessing one column's values is refused at the
# bound (SESSION_PREDICATE_REPEAT_LIMIT, core.nocustody.bound) while a different column in the same session is not.
artifact "no session_id" \
  "{\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DS}" \
  400 '"refusal":"no_session"'
PID2="\"session_id\":\"$S2\""
for g in $(seq 1 20); do
  artifact "probe $g of 20 on note" \
    "{$PID2,\"artifact\":{\"op\":\"count\",\"filter_col\":\"note\",\"filter_val\":\"guess-$g\"},$DS}" \
    200 '"values":["0"]'
done
artifact "probe 21 on note is refused as value probing" \
  "{$PID2,\"artifact\":{\"op\":\"sum\",\"column\":\"amount\",\"filter_col\":\"note\",\"filter_val\":\"a\"},$DS}" \
  429 '"refusal":"value_probing","error":"refused as value probing: this session has already filtered on this column 20 times, the limit is 20'
artifact "the same session filtering another column still runs" \
  "{$PID2,\"artifact\":{\"op\":\"count\",\"filter_col\":\"amount\",\"filter_val\":\"10\"},$DS}" \
  200 '"values":["1"]'

# NC1.13: a new session does not reset the count. The next probe on note, from a freshly
# issued id, is refused across sessions; a caller-chosen, forged or empty-shaped id is refused
# before anything runs.
S3=$(issue_session)
artifact "a new issued session probing note is refused across sessions" \
  "{\"session_id\":\"$S3\",\"artifact\":{\"op\":\"count\",\"filter_col\":\"note\",\"filter_val\":\"c\"},$DS}" \
  429 '"refusal":"cross_session_probing","error":"refused as value probing across sessions: this column has been filtered on 20 times in the last 24 hours across all sessions, the limit is 20 (NC1.13); a new session does not reset it'
artifact "while that session's ordinary question runs" \
  "{\"session_id\":\"$S3\",\"artifact\":{\"op\":\"count_by\",\"column\":\"region\"},$DS}" \
  200 '"labels":["north","south"],"values":["2","1"]'
artifact "a caller-chosen session id is refused" \
  "{\"session_id\":\"smoke-1\",\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DS}" \
  400 '"refusal":"session_unissued","error":"session_id was not issued by loke; POST /api/session issues one (NC1.13)"'
artifact "an id shaped like an issued one is refused" \
  "{\"session_id\":\"nc-0123456789abcdef0123456789abcdef\",\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DS}" \
  400 '"refusal":"session_unissued"'
pl=$(curl -s -m 20 -w '\n%{http_code}' -X POST -H 'Content-Type: application/json' \
       -d '{"text":"smoke test, no personal data","fallback_reason":"user_choice","fallback_selected_by":"user","session_id":"smoke-1"}' \
       "http://127.0.0.1:$PORT/api/pipeline")
case "${pl##*$'\n'} ${pl%$'\n'*}" in
  '400 {"ok":false,"refusal":"session_unissued"'*) echo "  ok   POST /api/pipeline refuses a session id loke did not issue [400]" ;;
  *) echo "  FAIL POST /api/pipeline with a caller-chosen session id: $pl" >&2; fail=1 ;;
esac

# NC1.10 (d): config.toml's [nocustody] limits are read on every run, and may only tighten.
# Written into the smoke's throwaway HOME, never the real one. A column no check above has
# filtered (zone), so the installation count starts at 0.
mkdir -p "$WORK/home/.loke"
DSZ='"headers":["zone","amount"],"rows":[["east","1"],["west","2"]]'
printf '[nocustody]\nsession_predicate_repeat_limit = 30\n' > "$WORK/home/.loke/config.toml"
artifact "a looser repeat limit in config.toml refuses every run" \
  "{\"session_id\":\"$S3\",\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DSZ}" \
  503 '"refusal":"limits_unusable","error":"the no-custody limits in config.toml cannot be applied, so nothing is released: nocustody.session_predicate_repeat_limit = 30 is above'
printf '[nocustody]\nsession_predicate_repeat_limit = 2\n' > "$WORK/home/.loke/config.toml"
S4=$(issue_session)
for g in 1 2; do
  artifact "probe $g of 2 on zone under a configured limit of 2" \
    "{\"session_id\":\"$S4\",\"artifact\":{\"op\":\"count\",\"filter_col\":\"zone\",\"filter_val\":\"g$g\"},$DSZ}" \
    200 '"values":["0"]'
done
artifact "probe 3 on zone is refused at the configured limit" \
  "{\"session_id\":\"$S4\",\"artifact\":{\"op\":\"count\",\"filter_col\":\"zone\",\"filter_val\":\"east\"},$DSZ}" \
  429 '"refusal":"value_probing","error":"refused as value probing: this session has already filtered on this column 2 times, the limit is 2 (NC1.10)'
rm -f "$WORK/home/.loke/config.toml"

# NC1.14: loke.policy.json can set a ceiling on those limits, read on every run. A ceiling is
# enforced at the ceiling, a config.toml value above it and a policy looser than the contract are
# refused (503 org_policy_violation), and each is a governance alert in loke.log and a row in
# nc_artifact_runs. A fresh column (area), so no count above carries over.
POL="$WORK/home/.loke/loke.policy.json"
DSA='"headers":["area","amount"],"rows":[["up","1"],["down","2"]]'
printf '{"max_session_predicate_repeat_limit":1}' > "$POL"
S5=$(issue_session)
artifact "probe 1 on area under a policy ceiling of 1" \
  "{\"session_id\":\"$S5\",\"artifact\":{\"op\":\"count\",\"filter_col\":\"area\",\"filter_val\":\"g1\"},$DSA}" \
  200 '"values":["0"]'
artifact "probe 2 on area is refused at the policy's ceiling" \
  "{\"session_id\":\"$S5\",\"artifact\":{\"op\":\"count\",\"filter_col\":\"area\",\"filter_val\":\"up\"},$DSA}" \
  429 '"refusal":"value_probing","error":"refused as value probing: this session has already filtered on this column 1 times, the limit is 1 (NC1.10)'
printf '[nocustody]\nsession_predicate_repeat_limit = 5\n' > "$WORK/home/.loke/config.toml"
artifact "config.toml above the policy's ceiling refuses every run" \
  "{\"session_id\":\"$S5\",\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DSA}" \
  503 '"refusal":"org_policy_violation","error":"the no-custody limits cannot be applied under the organisation policy, so nothing is released: nocustody.session_predicate_repeat_limit = 5 in config.toml is above the ceiling of 1 that organisation policy loke.policy.json sets (max_session_predicate_repeat_limit)'
rm -f "$WORK/home/.loke/config.toml"
printf '{"max_session_cell_budget":60000}' > "$POL"
artifact "a policy looser than the contract refuses every run" \
  "{\"session_id\":\"$S5\",\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DSA}" \
  503 '"refusal":"org_policy_violation","error":"the no-custody limits cannot be applied under the organisation policy, so nothing is released: organisation policy loke.policy.json cannot be applied: max_session_cell_budget = 60000 is above the artifact contract'"'"'s default, 50000'
rm -f "$POL"
artifact "with the policy removed, the same run is released" \
  "{\"session_id\":\"$S5\",\"artifact\":{\"op\":\"sum\",\"column\":\"amount\"},$DSA}" \
  200 '"values":["3.0"]'
LOG="$WORK/home/.loke/loke.log"
for want in 'governance alert: privacy organisation policy: organisation policy loke.policy.json overrode the no-custody limits in config.toml: nocustody.session_predicate_repeat_limit is lowered from 20 to 1 by max_session_predicate_repeat_limit' \
            'governance alert: privacy organisation policy: nocustody.session_predicate_repeat_limit = 5 in config.toml is above the ceiling of 1' \
            'governance alert: privacy organisation policy: organisation policy loke.policy.json cannot be applied: max_session_cell_budget = 60000'; do
  if grep -qF "$want" "$LOG" 2>/dev/null; then echo "  ok   loke.log has: ${want:0:90}..."
  else echo "  FAIL loke.log lacks the alert: $want" >&2; fail=1; fi
done
if command -v sqlite3 >/dev/null; then
  got=$(sqlite3 "$WORK/home/.loke/loke.db" "SELECT verdict||':'||COALESCE(refusal_code,'') FROM nc_artifact_runs WHERE session_id='$S5' AND op='' ORDER BY run_id" 2>&1 | tr '\n' ' ')
  if [ "$got" = "org_policy_override: org_policy_override: refused:org_policy_violation refused:org_policy_violation " ]; then
    echo "  ok   nc_artifact_runs has the two override rows and the two org_policy_violation rows"
  else echo "  FAIL nc_artifact_runs policy rows for the session: [$got]" >&2; fail=1; fi
else
  echo "  FAIL sqlite3 is not installed, so the policy rows cannot be checked" >&2; fail=1
fi

# LS1.4a: POST /api/settings merges one key into ~/.loke/settings.json. It wrote {key:value}
# over the whole file, so saving one setting lost every other. Judged on the response body
# and on the file the server wrote. No API key is posted: the keychain the server would write
# to is the user's, whatever HOME is.
SETF="$WORK/home/.loke/settings.json"
mkdir -p "$WORK/home/.loke"
printf '%s' '{"port":11430,"theme":"dark"}' > "$SETF"
setting() {  # $1 label, $2 body, $3 expected status, $4 substring the body must contain
  local out code body
  out=$(curl -s -m 20 -w '\n%{http_code}' -X POST -H 'Content-Type: application/json' \
          -d "$2" "http://127.0.0.1:$PORT/api/settings")
  code=${out##*$'\n'}; body=${out%$'\n'*}
  if [ "$code" != "$3" ] || [[ "$body" != *"$4"* ]] || [[ "$body" == *secretvalue* ]]; then
    echo "  FAIL POST /api/settings ($1): got [$code] $body, expected [$3] containing $4 and no secret" >&2
    fail=1
  else
    echo "  ok   POST /api/settings ($1) [$code]"
  fi
}
setting "key A is saved" '{"key":"locale","value":"en-AU"}' 200 '{"ok":true}'
setting "key B is saved" '{"key":"default_model","value":"llama3.2:3b"}' 200 '{"ok":true}'
setting "a body that is not JSON is refused" 'not json' 400 'needs a string key'
setting "a secret-looking key is refused, not echoed" '{"key":"mistral_api_key","value":"sk-smoke-secretvalue"}' 400 'not stored in the settings file'
if python3 -c 'import json,sys
t=open(sys.argv[1]).read(); d=json.loads(t)
sys.exit(0 if d=={"port":11430,"theme":"dark","locale":"en-AU","default_model":"llama3.2:3b"} and "secretvalue" not in t else 1)' "$SETF"; then
  echo "  ok   settings.json holds keys A and B and the two settings it started with, and no secret"
else
  echo "  FAIL settings.json after the posts: $(cat "$SETF")" >&2; fail=1
fi

# F3b.9: POST /api/evaluate runs every configured detection layer on a text, side by side,
# and answers types, spans, confidences and placeholders, never a value. Here regex scans and
# the sidecars are not running, so they must read unavailable with detections null, never 0.
python3 "$ROOT/scripts/lib/evaluate_check.py" evaluate "http://127.0.0.1:$PORT" || fail=1
# F3b.10: GET /api/layermetrics, judged against the database file itself.
python3 "$ROOT/scripts/lib/evaluate_check.py" layermetrics "http://127.0.0.1:$PORT" "$WORK/home/.loke/loke.db" || fail=1

# F3b.2 (b), F3b.7 (1), F3b.8 (3): the settings UI's privacy routes and /api/health's
# policy-applied layers, judged on the bodies and on the files the server wrote. The check owns
# config.toml, loke.policy.json and privacy-models.json while it runs and removes them after;
# the NC1.14 checks above leave a config.toml, so it is removed first.
rm -f "$WORK/home/.loke/config.toml"
python3 "$ROOT/scripts/lib/privacy_settings_check.py" "http://127.0.0.1:$PORT" "$WORK/home" || fail=1

# GA2.6: a hostile page's "simple" POST (text/plain, so no preflight) must be refused
# before any handler does work. Loopback origins must still get through.
xorigin() {  # $1 path, $2 origin, $3 expect: refused|allowed
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 20 -X POST -H "Origin: $2" \
           -H 'Content-Type: text/plain' -d '{"text":"smoke test, no personal data","fallback_reason":"user_choice","fallback_selected_by":"user"}' \
           "http://127.0.0.1:$PORT$1")
  if [ "$3" = refused ] && [ "$code" != 403 ]; then
    echo "  FAIL POST $1 from $2: got [$code], a cross-origin request must be refused (GA2.6)" >&2
    fail=1
  elif [ "$3" = allowed ] && { [ "$code" = 403 ] || [ "$code" = 000 ]; }; then
    echo "  FAIL POST $1 from $2: got [$code], a loopback origin must be let through" >&2
    fail=1
  else
    echo "  ok   POST $1 from $2 [$code]"
  fi
}
for r in pipeline settings approve privacy savings tabs artifact evaluate privacylayers privacymodels; do
  xorigin "/api/$r" "https://evil.example" refused
done
xorigin /api/pipeline "http://127.0.0.1:$PORT" allowed

# GA2.7: a DNS-rebound page reads GET routes as same-origin; its Host still names it.
for r in settings health layermetrics privacylayers privacymodels; do
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Host: rebind.example:$PORT" \
           "http://127.0.0.1:$PORT/api/$r")
  if [ "$code" != 403 ]; then
    echo "  FAIL GET /api/$r with Host rebind.example: got [$code], must be refused (GA2.7)" >&2
    fail=1
  else
    echo "  ok   GET /api/$r with Host rebind.example [$code]"
  fi
done

# F3b.10: GET /api/layermetrics reads loke's state, so a foreign Origin is refused too.
code=$(curl -s -o /dev/null -w '%{http_code}' -m 10 -H "Origin: https://evil.example" "http://127.0.0.1:$PORT/api/layermetrics")
if [ "$code" != 403 ]; then
  echo "  FAIL GET /api/layermetrics from https://evil.example: got [$code], must be refused (GA2.6)" >&2; fail=1
else
  echo "  ok   GET /api/layermetrics from https://evil.example [$code]"
fi

# F10.38: and it still is, so no answer above came from a server that took the port later.
assert_port_owner smoke_serve "$PORT" "$PID" || fail=1

# GA2.5: and it listens on loopback only. lsof names each listening socket's address; `*:$PORT`
# (every interface) or any address but 127.0.0.1 / ::1 fails. The served ooke.toml is the
# tree's own with only the port changed, so this checks the [server] host loke ships with.
if assert_loopback_only smoke_serve "$PORT"; then
  echo "  ok   listening on loopback only: $(port_bind_addresses "$PORT" | tr '\n' ' ')(GA2.5)"
else
  fail=1
fi

if [ "$fail" -ne 0 ]; then
  echo "smoke_serve: at least one route failed (F10.36, GA2.6)" >&2
  exit 1
fi
echo "smoke_serve: OK, every route answered"
