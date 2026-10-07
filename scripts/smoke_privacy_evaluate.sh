#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_privacy_evaluate.sh — run the built `loke privacy evaluate` against a recording
# stand-in for NER (Ollama) and Presidio, and judge what it prints AND what reached the
# stand-in. (F3b.9)
#
# Checks: every layer is reported with its own detections by type and span, no detected value
# is printed without --show-values, the stand-ins really were asked (a report right by
# accident is not a check), a labelled file is scored per layer, and with the stand-in gone
# NER and Presidio are reported unavailable rather than as finding nothing.
#
# The stand-in (scripts/lib/http_recorder.py) takes a port from the OS and HOME is a
# throwaway directory, so the real ~/.loke is never read and no lock is needed. A second
# or two.
#
#   scripts/smoke_privacy_evaluate.sh        # uses build/trees/loke-cli/loke-cli

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/build/trees/loke-cli/loke-cli"
[ -x "$BIN" ] || { echo "smoke_privacy_evaluate: $BIN not built; run scripts/build_trees.sh loke-cli" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_privacy_eval_smoke.XXXXXX")
RPID=
cleanup() { [ -n "$RPID" ] && kill "$RPID" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

python3 "$ROOT/scripts/lib/http_recorder.py" "$WORK/rec.log" "$WORK/rec.port" &
RPID=$!
for _ in $(seq 1 50); do [ -s "$WORK/rec.port" ] && break; sleep 0.1; done
PORT=$(cat "$WORK/rec.port" 2>/dev/null)
[ -n "$PORT" ] || { echo "smoke_privacy_evaluate: the recorder did not start" >&2; exit 1; }
URL="http://127.0.0.1:$PORT"

mkdir -p "$WORK/home/.loke"
printf '[providers]\nollama_url = "%s"\n\n[privacy]\npresidio_url = "%s"\n' "$URL" "$URL" > "$WORK/home/.loke/config.toml"

TEXT="Jane Citizen called Tuesday, mail jane@example.com"
printf '%s\n%s\n' \
  '{"text":"Jane Citizen called Tuesday, mail jane@example.com","entities":[{"type":"PERSON","value":"Jane Citizen","start":0,"end":12,"expected_detected":true},{"type":"EMAIL","value":"jane@example.com","start":34,"end":50,"expected_detected":true}]}' \
  '{"text":"The weather is fine today, thanks.","entities":[]}' > "$WORK/labelled.jsonl"

FAILS=0
check() { # $1 = label, $2 = 0 if it held
  if [ "$2" -eq 0 ]; then echo "  ok    $1"; else echo "  FAIL  $1"; FAILS=$((FAILS+1)); fi
}

echo "smoke_privacy_evaluate: stand-in on $URL"

HOME="$WORK/home" "$BIN" privacy evaluate "$TEXT" >"$WORK/up.txt" 2>&1; rc=$?
check "evaluate exits 0 with every layer answering" $([ "$rc" -eq 0 ]; echo $?)
check "NER completed with its detection at 0-12" $(grep -A1 "^  ner (detect-and-mask): completed, 1 detection" "$WORK/up.txt" | grep -q "\[PERSON\] 0-12"; echo $?)
check "Presidio completed with its detection at 0-12" $(grep -A1 "^  presidio (detect-and-mask): completed, 1 detection" "$WORK/up.txt" | grep -q "\[PERSON\] 0-12"; echo $?)
check "regex completed with the email's span 34-50" $(grep -A1 "^  regex (detect-and-mask): completed, 1 detection" "$WORK/up.txt" | grep -q " 34-50 "; echo $?)
check "the name's disagreement is shown (regex missed it)" $(grep -q "not found by regex -> mask" "$WORK/up.txt"; echo $?)
check "no detected value is printed" $(! grep -qiE "jane|citizen|example\.com" "$WORK/up.txt"; echo $?)
check "POST /analyze reached the Presidio stand-in" $(grep -qs "^POST /analyze" "$WORK/rec.log"; echo $?)
check "POST /api/chat reached the NER stand-in" $(grep -qs "^POST /api/chat" "$WORK/rec.log"; echo $?)

HOME="$WORK/home" "$BIN" privacy evaluate --show-values "$TEXT" >"$WORK/shown.txt" 2>&1
check "--show-values prints the values" $(grep -q '"Jane Citizen"' "$WORK/shown.txt" && grep -q '"jane@example.com"' "$WORK/shown.txt"; echo $?)

HOME="$WORK/home" "$BIN" privacy evaluate --file "$WORK/labelled.jsonl" >"$WORK/file.txt" 2>&1; rc=$?
check "evaluate --file exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "regex is scored tp=1 fp=0 fn=1" $(grep "^layer=regex recall=" "$WORK/file.txt" | grep -q "tp=1 fp=0 fn=1 texts=2/2"; echo $?)
check "Presidio is scored with its false positive" $(grep "^layer=presidio recall=" "$WORK/file.txt" | grep -q "tp=1 fp=1 fn=1 texts=2/2"; echo $?)
check "the labelled report prints no value or text" $(! grep -qiE "jane|citizen|weather" "$WORK/file.txt"; echo $?)

# With nothing listening, NER and Presidio are unavailable; the regex layer still scans.
kill "$RPID" 2>/dev/null; wait "$RPID" 2>/dev/null; RPID=
HOME="$WORK/home" "$BIN" privacy evaluate "$TEXT" >"$WORK/down.txt" 2>&1; rc=$?
check "with the stand-in gone, evaluate still exits 0 (regex scanned)" $([ "$rc" -eq 0 ]; echo $?)
check "NER is reported unavailable" $(grep -q "^  ner: unavailable -- Ollama unreachable" "$WORK/down.txt"; echo $?)
check "Presidio is reported unavailable" $(grep -q "^  presidio: unavailable -- Presidio sidecar unreachable" "$WORK/down.txt"; echo $?)
check "neither is reported as completing with nothing found" $(! grep -qE "^  (ner|presidio) \(" "$WORK/down.txt"; echo $?)
HOME="$WORK/home" "$BIN" privacy evaluate --file "$WORK/labelled.jsonl" >"$WORK/filedown.txt" 2>&1
check "and in the labelled report they are not scored, not scored zero" $(grep -q "^layer=ner not scored" "$WORK/filedown.txt" && ! grep -q "^layer=ner recall=" "$WORK/filedown.txt"; echo $?)

# F3b.7: a token classifier registered with `loke privacy add-model` is a layer evaluate
# reports. The recorder's `tokenmodel` mode stands in for the sidecar serving it.
python3 "$ROOT/scripts/lib/http_recorder.py" "$WORK/tok.log" "$WORK/tok.port" tokenmodel &
RPID=$!
for _ in $(seq 1 50); do [ -s "$WORK/tok.port" ] && break; sleep 0.1; done
TURL="http://127.0.0.1:$(cat "$WORK/tok.port" 2>/dev/null)"
HOME="$WORK/home" "$BIN" privacy add-model recorder/token-model --url "$TURL" --label MISC=MISCELLANEOUS >"$WORK/addbad.txt" 2>&1; rc=$?
check "add-model refuses a label mapped to a type loke does not know" $([ "$rc" -eq 1 ] && grep -q "maps MISC to MISCELLANEOUS, which is not an entity type loke knows" "$WORK/addbad.txt" && [ ! -e "$WORK/home/.loke/privacy-models.json" ]; echo $?)
HOME="$WORK/home" "$BIN" privacy add-model recorder/token-model --url "$TURL" --label PER=PERSON --label LOC=LOCATION --threshold 0.5 >"$WORK/add.txt" 2>&1; rc=$?
check "add-model registers the model" $([ "$rc" -eq 0 ] && grep -q '"id":"recorder/token-model"' "$WORK/home/.loke/privacy-models.json"; echo $?)
HOME="$WORK/home" "$BIN" privacy list-models >"$WORK/list.txt" 2>&1
check "list-models lists it with its mapping" $(grep -q "^model:recorder/token-model  $TURL  labels=PER=PERSON,LOC=LOCATION  confidence_threshold=0.5  priority=5  enabled" "$WORK/list.txt"; echo $?)
HOME="$WORK/home" "$BIN" privacy evaluate "Jane Citizen from Brisbane, mail jane@example.com" >"$WORK/model.txt" 2>&1; rc=$?
check "evaluate reports the registered model as a layer with its two detections" $([ "$rc" -eq 0 ] && grep -A1 "^  model:recorder/token-model (detect-and-mask): completed, 2 detections" "$WORK/model.txt" | grep -q "\[PERSON\] 0-12"; echo $?)
check "the model was probed before it was sent the text" $(head -1 "$WORK/tok.log" | grep -q "^GET /health" && grep -q "^POST /detect" "$WORK/tok.log"; echo $?)
check "and no value is printed" $(! grep -qiE "jane|citizen|brisbane" "$WORK/model.txt"; echo $?)
HOME="$WORK/home" "$BIN" privacy remove-model recorder/token-model >/dev/null 2>&1; rc=$?
HOME="$WORK/home" "$BIN" privacy evaluate "Jane Citizen" >"$WORK/removed.txt" 2>&1
check "remove-model removes the layer" $([ "$rc" -eq 0 ] && ! grep -q "model:recorder/token-model" "$WORK/removed.txt"; echo $?)

if [ "$FAILS" -ne 0 ]; then
  for f in up shown file down filedown addbad add list model removed; do echo "--- $f ---"; cat "$WORK/$f.txt" 2>/dev/null; done
  echo "smoke_privacy_evaluate: $FAILS check(s) FAILED"
  exit 1
fi
echo "smoke_privacy_evaluate: all checks passed"
