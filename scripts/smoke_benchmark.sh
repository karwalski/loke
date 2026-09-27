#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# smoke_benchmark.sh — run the built `loke benchmark` against a stand-in Ollama and judge
# the result file it writes. (VM1.6)
#
# What it proves: the CLI reaches core.eval.bench, the five default cases are dispatched
# to the local model and scored, and the summary lands as VM1.1 measurements that
# benchmarks/lib/result.py reads back and would itself accept. The stand-in answers every
# prompt with one sentence containing every expected keyword, so the only correct score is
# 1.0; an off-by-one in the scorer, a dropped case or a corrupted f64 shows up as another
# number. It also checks the three refusals: a hosted model id, a model Ollama does not
# list (no digest, so no pinned version), and a malformed --out.
#
# VM1.3: the default is five runs with the first discarded, so each figure is recorded with
# runs = 4 and a BCa interval. The stand-in delays its replies by a cycled list, so the kept
# runs' latencies differ, and the interval core.eval.interval wrote is compared with
# result.py's bca_ci over the per-run means the CLI printed. --runs 2 and --runs 9 are
# refused before anything is dispatched.
#
# What it does not prove: anything about a real model. The reply is fixed.
#
# No fixed port: the stand-in Ollama binds a port the OS hands out (or
# SMOKE_BENCH_OLLAMA_PORT), and HOME is a throwaway directory, so the real ~/.loke is never
# read or written and no lock is needed.
#
#   scripts/smoke_benchmark.sh        # uses build/trees/loke-cli/loke-cli

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN="$ROOT/build/trees/loke-cli/loke-cli"
[ -x "$BIN" ] || { echo "smoke_benchmark: $BIN not built; run scripts/build_trees.sh loke-cli" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/loke_bench_smoke.XXXXXX")
FPID=
cleanup() { [ -n "$FPID" ] && kill "$FPID" 2>/dev/null; rm -rf "$WORK"; }
trap cleanup EXIT INT TERM

PORT="${SMOKE_BENCH_OLLAMA_PORT:-$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')}"
REPLY="42. def f(s): return s[::-1]. Caching helps performance, latency and cost. Yes, Felix is a mammal. Privacy-first AI."

mkdir -p "$WORK/home/.loke"
printf '[providers]\nollama_url = "http://127.0.0.1:%s"\n' "$PORT" > "$WORK/home/.loke/config.toml"

# VM1.3: seven delays, cycled over the five cases of each run, so each run's mean latency
# differs and the latency interval is a real one rather than a single point.
FAKE_OLLAMA_COMPACT=1 FAKE_OLLAMA_PORT="$PORT" FAKE_OLLAMA_MODELS="bench-model:latest" FAKE_OLLAMA_REPLY="$REPLY" \
  FAKE_OLLAMA_DELAYS_MS="0,40,5,80,10,20,120" \
  python3 "$ROOT/scripts/lib/fake_ollama.py" "$WORK/ollama.log" &
FPID=$!
for _ in $(seq 1 50); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT/api/tags" && break
  sleep 0.1
done

FAILS=0
check() { # $1 = label, $2 = 0 if it held
  if [ "$2" -eq 0 ]; then echo "  ok    $1"; else echo "  FAIL  $1"; FAILS=$((FAILS+1)); fi
}
run() { HOME="$WORK/home" "$BIN" "$@" >"$WORK/out.txt" 2>&1; }

echo "smoke_benchmark: stand-in Ollama on 127.0.0.1:$PORT"

# ── A hosted model is refused before anything is dispatched ──────────────────
run benchmark claude-sonnet-4; rc=$?
check "a hosted model id exits non-zero" $([ "$rc" -ne 0 ]; echo $?)
check "and says it is local-only" $(grep -q "local Ollama model only" "$WORK/out.txt"; echo $?)
check "and nothing reached the model" $([ ! -s "$WORK/ollama.log" ]; echo $?)

# ── Malformed arguments are refused ──────────────────────────────────────────
run benchmark bench-model --out; rc=$?
check "--out with no path is refused" $([ "$rc" -ne 0 ] && grep -q "usage: loke benchmark" "$WORK/out.txt"; echo $?)

# ── VM1.3: too few runs to leave an interval, or more than are enumerated ─────
run benchmark bench-model --runs 2 --out "$WORK/two.jsonl"; rc=$?
check "--runs 2 is refused: one run after the warm-up is not a result" $([ "$rc" -ne 0 ] && grep -q "runs must be from 3 to 8" "$WORK/out.txt"; echo $?)
run benchmark bench-model --runs 9 --out "$WORK/nine.jsonl"; rc=$?
check "--runs 9 is refused" $([ "$rc" -ne 0 ] && grep -q "runs must be from 3 to 8" "$WORK/out.txt"; echo $?)
check "and neither dispatched anything or wrote a file" $([ ! -s "$WORK/ollama.log" ] && [ ! -e "$WORK/two.jsonl" ] && [ ! -e "$WORK/nine.jsonl" ]; echo $?)

# ── A model Ollama does not list has no digest, so nothing is recorded ───────
run benchmark not-installed --out "$WORK/none.jsonl"; rc=$?
check "an unlisted model exits non-zero" $([ "$rc" -ne 0 ]; echo $?)
check "and still prints the table" $(grep -q "AVERAGE" "$WORK/out.txt"; echo $?)
check "and says why it was not recorded" $(grep -q "no digest" "$WORK/out.txt"; echo $?)
check "and wrote no file" $([ ! -e "$WORK/none.jsonl" ]; echo $?)

# ── A model that answers nothing: the failures are not recorded as zero scores ─
# A second stand-in, with an empty reply, behind its own throwaway HOME.
PORT2="$(python3 -c 'import socket;s=socket.socket();s.bind(("127.0.0.1",0));print(s.getsockname()[1]);s.close()')"
mkdir -p "$WORK/home2/.loke"
printf '[providers]\nollama_url = "http://127.0.0.1:%s"\n' "$PORT2" > "$WORK/home2/.loke/config.toml"
FAKE_OLLAMA_COMPACT=1 FAKE_OLLAMA_PORT="$PORT2" FAKE_OLLAMA_MODELS="bench-model:latest" FAKE_OLLAMA_REPLY="" \
  python3 "$ROOT/scripts/lib/fake_ollama.py" "$WORK/ollama2.log" &
FPID2=$!
for _ in $(seq 1 50); do
  curl -s -o /dev/null "http://127.0.0.1:$PORT2/api/tags" && break
  sleep 0.1
done
HOME="$WORK/home2" "$BIN" benchmark bench-model --out "$WORK/failed.jsonl" >"$WORK/out.txt" 2>&1; rc=$?
kill "$FPID2" 2>/dev/null
check "a run whose cases all fail exits non-zero" $([ "$rc" -ne 0 ]; echo $?)
check "and says a case failed to dispatch" $(grep -q "failed to dispatch" "$WORK/out.txt"; echo $?)
check "and wrote no file" $([ ! -e "$WORK/failed.jsonl" ]; echo $?)

# ── The real run, to the default path under the throwaway HOME ───────────────
: > "$WORK/ollama.log"
run benchmark bench-model; rc=$?
cp "$WORK/out.txt" "$WORK/run.txt"
check "a local model exits 0" $([ "$rc" -eq 0 ]; echo $?)
check "the configured Ollama URL was used" $(grep -q "Ollama at http://127.0.0.1:$PORT" "$WORK/out.txt"; echo $?)
check "five runs of the five cases reached /api/chat (VM1.3 default)" $([ "$(grep -c '^/api/chat' "$WORK/ollama.log")" -eq 25 ]; echo $?)
check "carrying the case's prompt as a user message" $(grep -q '"role":"user","content":"What is 15 + 27?"' "$WORK/ollama.log"; echo $?)
check "the first run is shown as the discarded warm-up" $(grep -q "run 1 of 5 (warm-up, discarded)" "$WORK/out.txt"; echo $?)
check "every run's table shows a 1 average" $([ "$(grep -Ec "^AVERAGE +1(\.0+)? " "$WORK/out.txt")" -eq 5 ]; echo $?)

python3 - "$ROOT" "$WORK/home/.loke/benchmarks" "$WORK/run.txt" <<'EOF'
import math, pathlib, re, sys
sys.path.insert(0, sys.argv[1])
from benchmarks.lib.result import Measurement, bca_ci, read_all, validate
d = pathlib.Path(sys.argv[2])
# Each run's mean latency, as the CLI printed it, warm-up first.
printed = [int(x) for x in re.findall(r"^AVERAGE +\S+ +(\d+)ms", pathlib.Path(sys.argv[3]).read_text(), re.M)]
files = sorted(d.glob("*.jsonl"))
fails = 0
def check(label, ok):
    global fails
    print(("  ok    " if ok else "  FAIL  ") + label)
    fails += 0 if ok else 1
check("one results file under ~/.loke/benchmarks", len(files) == 1)
rows = read_all(d)
check("read_all reads two measurements", len(rows) == 2)
by = {r.get("metric"): r for r in rows}
s = by.get("keyword_score", {})
l = by.get("latency_mean", {})
check("keyword_score is 1.0 (every keyword in every reply)", s.get("value") == 1.0)
check("keyword_score is a ratio over n=20 (five cases, four kept runs)", s.get("units") == "ratio" and s.get("n") == 20)
# VM1.3: repetition and the interval.
check("both rows record four kept runs", s.get("runs") == 4 and l.get("runs") == 4)
check("identical scores give the point interval [1, 1], labelled degenerate",
      s.get("ci_low") == 1.0 and s.get("ci_high") == 1.0 and "degenerate" in (s.get("ci_method") or ""))
check("latency carries the exhaustive BCa interval of four runs",
      l.get("ci_method") == "bca-bootstrap-exhaustive-256")
check("the CLI printed five run averages", len(printed) == 5)
kept = printed[1:]
check("the kept runs' latencies differ, so the interval is a real one", len(set(kept)) > 1)
check("latency_mean is the mean of the four kept runs, not the warm-up",
      len(kept) == 4 and abs(l.get("value", -1) - sum(kept) / 4) < 1e-6)
if len(set(kept)) > 1:
    lo, hi, method = bca_ci([float(x) for x in kept])
    # core.eval.interval rounds outward to the millionth; result.py does not round.
    check(f"the toke interval is result.py's BCa interval [{lo:.6f}, {hi:.6f}]",
          abs(l.get("ci_low", 0) - math.floor(lo * 1e6) / 1e6) <= 1.5e-6
          and abs(l.get("ci_high", 0) - math.ceil(hi * 1e6) / 1e6) <= 1.5e-6
          and method == l.get("ci_method"))
check("workload is bench-default-5", s.get("workload") == "bench-default-5")
check("model and its Ollama digest are recorded", s.get("model") == "bench-model" and s.get("model_version") == "x")
check("seed is null: temperature is not forwarded", s.get("seed") is None and "temperature" in (s.get("caveat") or ""))
check("latency_mean is a non-negative number of ms", l.get("units") == "ms" and isinstance(l.get("value"), (int, float)) and l.get("value") >= 0)
# The Python sink's own guard accepts what the toke sink wrote.
for r in rows:
    fields = {k: r[k] for k in Measurement.__dataclass_fields__ if k in r}
    try:
        validate(Measurement(**fields)); ok = True
    except Exception as e:
        print(e); ok = False
    check(f"result.validate accepts the {r.get('metric')} row", ok)
check("the Python sink's keys, and no others", set(rows[0]) == set(Measurement.__dataclass_fields__))
sys.exit(fails)
EOF
FAILS=$((FAILS+$?))

if [ "$FAILS" -ne 0 ]; then
  echo "--- last CLI output ---"; cat "$WORK/run.txt"
  for f in "$WORK"/home/.loke/benchmarks/*.jsonl; do [ -f "$f" ] && { echo "--- $f ---"; cat "$f"; }; done
  echo "smoke_benchmark: $FAILS check(s) FAILED"
  exit 1
fi
echo "smoke_benchmark: all checks passed"
