#!/usr/bin/env python3
"""AD1.3 - marginal value of each PII detection layer, measured on the PII corpus.

What runs, and what does not
----------------------------
The measurement itself is tests/integration/test_layer_marginal.tk: loke's own layer
clients (core.privacy.regex.detect, core.privacy.ner.scan, core.privacy.sidecarclient.detect)
scored by the production scorer, core.privacy.evaluation. This script only provides the
local services that test needs, runs it, and records what it prints.

  regex     in process, always.
  ner       a local Ollama started here on 127.0.0.1:11338 (OLLAMA_HOST), with the model
            named by --ner-model. loke's pipeline default is qwen2.5:7b
            (pipeline.newconfig); if that model is not installed locally, pass the one that
            is, and the result is labelled with the model actually used.
  pf        the privacy-filter sidecar (packages/privacy-filter/server.py) started here on
            127.0.0.1:11339, with HF_HUB_OFFLINE=1 so the model comes from the local Hugging
            Face cache and nothing is fetched. It is NOT a layer pipeline.run calls today;
            it is measured as a candidate.
  presidio  not run. No Presidio analyser is installed here, and installing one needs the
            network.

Nothing here contacts a remote host: both services bind loopback, the sidecar runs offline,
and loke's clients refuse a non-loopback URL.

The NER answer varies between runs (Ollama samples; loke does not pin a temperature), so the
test is run --runs times (default 4). The first run is a warm-up and is discarded; every figure
is recorded as the mean of the kept runs with their BCa bootstrap interval, through
result.summarise (VM1.3). The interval is never widened to contain the mean: a row whose mean
falls outside its interval is refused by result.validate and reported, not recorded (VM1.3b).
Ports default to 11338/11339 and can be moved with --ollama-port/--pf-port.

Usage (one command, after scripts/build_loke.sh and the moke/loke-cli trees are built):

    TOKE_DIR=... BUILDDIR=... python3 benchmarks/ad13/run.py --ner-model qwen2.5:3b --runs 4 --record

Only the services this script started are stopped, by process id.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import time
import urllib.request

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from benchmarks.lib import result  # noqa: E402

CORPUS = REPO / "tests" / "fixtures" / "pii-corpus" / "corpus.jsonl"
TEST = "tests/integration/test_layer_marginal.tk"
OLLAMA_PORT = 11338
PF_PORT = 11339
PF_SNAPSHOTS = pathlib.Path.home() / ".cache/huggingface/hub/models--openai--privacy-filter/snapshots"


def get(url: str, timeout: float = 5.0) -> str:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # loopback only
        return r.read().decode("utf-8", "replace")


def post(url: str, body: dict, timeout: float = 300.0) -> str:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # loopback only
        return r.read().decode("utf-8", "replace")


def wait_for(url: str, seconds: int) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            get(url, timeout=3)
            return True
        except Exception:
            time.sleep(2)
    return False


def start(cmd: list[str], env: dict, log: pathlib.Path) -> subprocess.Popen:
    fh = log.open("w")
    return subprocess.Popen(cmd, env=env, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)


def stop(p: subprocess.Popen | None) -> None:
    if p is None or p.poll() is not None:
        return
    try:
        os.killpg(p.pid, signal.SIGTERM)
        p.wait(timeout=20)
    except Exception:
        p.kill()


def model_digest(ollama: str, name: str) -> str | None:
    tags = json.loads(get(f"{ollama}/api/tags"))
    for m in tags.get("models", []):
        if m.get("name") == name:
            return m.get("digest", "")[:12]
    return None


def parse(out: str) -> dict:
    """AD13 lines -> {'layers': {name: {...}}, 'marginal': {name: {...}}, 'meta': {...}}."""
    res: dict = {"layers": {}, "marginal": {}, "meta": {}}
    for line in out.splitlines():
        if not line.startswith("AD13 "):
            continue
        kv = dict(re.findall(r"(\w+)=(\S*)", line[5:]))
        if "layer" in kv:
            res["layers"][kv["layer"]] = kv
        elif "marginal" in kv:
            res["marginal"][kv["marginal"]] = kv
        else:
            res["meta"] = kv
    return res


def pct(s: str) -> float:
    return float(s.rstrip("%")) / 100.0


def run_test(env: dict) -> str:
    """One run of the measurement test; its stdout."""
    return subprocess.run(["scripts/run_tests.sh", TEST], cwd=REPO, env=env,
                          capture_output=True, text=True).stdout


def _layer_model(layer: str, layer_model: dict) -> tuple[str | None, str | None]:
    model = version = None
    for part, (mname, mver) in layer_model.items():
        if part in layer.split("+") or layer == "all":
            model = (model + " + " if model else "") + mname
            version = (version + " + " if version else "") + str(mver)
    return model, version


def _write_one(values: list[float], fields: dict, written: list, refused: list) -> None:
    """Summarise one metric over the runs (warm-up discarded, BCa interval) and write it.

    The interval is the one BCa produced and is never widened to contain the mean. A BCa
    interval can in principle exclude the mean of the runs it came from, because the bias
    correction and the acceleration move both percentiles, and with three or four kept runs
    both are estimated from very little. result.validate refuses such a row; it is then
    reported with its figures and that reason, not published with an interval the bootstrap
    did not produce.
    """
    note = fields.pop("notes", "")
    m = result.summarise(values, **fields)
    m.notes = f"per-run {values}, the first discarded as warm-up" + (f"; {note}" if note else "")
    try:
        result.write(m)
        written.append(m)
    except result.ResultRejected as e:
        if m.ci_low is not None and not (m.ci_low <= m.value <= m.ci_high):
            refused.append(
                f"{m.metric} [{m.arm}]: the mean {m.value} of the kept runs {values[1:]} lies "
                f"outside its {m.ci_method} interval [{m.ci_low}, {m.ci_high}]: the bias "
                f"correction and acceleration, estimated from {m.runs} runs, moved both "
                f"percentiles past it. Not recorded; re-measure with more runs.")
        else:
            refused.append(f"{m.metric} [{m.arm}]: {e}")


def record(runs: list[dict], *, workload: str, caveat: str,
           layer_model: dict) -> tuple[list, list[str]]:
    """Write one row per layer metric and per marginal metric. Returns (written, refused).

    runs[0] is the warm-up, discarded by result.summarise; each row is the mean of the kept
    runs with their BCa interval (VM1.3, VM1.3b).
    """
    written: list = []
    refused: list[str] = []
    kept = runs[1] if len(runs) > 1 else runs[0]
    for layer in runs[0]["layers"]:
        model, version = _layer_model(layer, layer_model)
        # n is each ratio's own denominator: labelled entities, labelled direct identifiers,
        # or detection regions (which vary between NER runs; the first kept run's is
        # recorded, and the notes carry every run's value).
        for metric, key, nkey in (("pii_recall_entity", "recall", "labelled"),
                                  ("pii_recall_direct_identifiers", "direct_recall", "direct_labelled"),
                                  ("pii_precision_entity", "precision", "detections")):
            vals = [pct(r["layers"][layer][key]) for r in runs]
            _write_one(vals, dict(metric=metric, units="ratio", workload=workload,
                                  n=max(1, int(kept["layers"][layer][nkey])),
                                  arm=f"layers:{layer}", model=model, model_version=version,
                                  caveat=caveat,
                                  notes=f"scored by core.privacy.evaluation via {TEST}"),
                       written, refused)
    for name in runs[0]["marginal"]:
        mname, mver = _layer_model(name, layer_model)
        for metric, key, units in (("pii_marginal_recall_gain", "recall_gain", "entities"),
                                   ("pii_marginal_direct_gain", "direct_gain", "entities"),
                                   ("pii_marginal_false_positives_added", "fp_added", "regions")):
            vals = [float(r["marginal"][name][key]) for r in runs]
            _write_one(vals, dict(metric=metric, units=units, workload=workload,
                                  n=int(kept["marginal"][name]["labelled"]),
                                  arm=("all vs regex" if name == "all" else f"regex+{name} vs regex"),
                                  model=mname, model_version=mver, caveat=caveat),
                       written, refused)
    return written, refused


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ner-model", default="qwen2.5:3b")
    ap.add_argument("--runs", type=int, default=4,
                    help="runs of the test; the first is a warm-up and is not recorded")
    ap.add_argument("--ollama-port", type=int, default=OLLAMA_PORT)
    ap.add_argument("--pf-port", type=int, default=PF_PORT)
    ap.add_argument("--no-ner", action="store_true")
    ap.add_argument("--no-pf", action="store_true")
    ap.add_argument("--record", action="store_true", help="write through benchmarks/lib/result.py")
    args = ap.parse_args(argv)
    if args.record and args.runs < 3:
        ap.error("--record needs --runs of at least 3: the first is a warm-up, and an interval needs two more")

    subprocess.run([sys.executable, str(REPO / "tests/fixtures/pii-corpus/generate.py")], check=True, cwd=REPO)
    corpus_sha = hashlib.sha256(CORPUS.read_bytes()).hexdigest()[:12]
    ncases = sum(1 for l in CORPUS.read_text().splitlines() if l.strip())
    workload = f"pii-corpus-seed20260919-{ncases}-cases-sha256:{corpus_sha}"

    logdir = pathlib.Path(os.environ.get("BUILDDIR", "/tmp")) / "ad13"
    logdir.mkdir(parents=True, exist_ok=True)
    ollama = pf = None
    ollama_url = f"http://127.0.0.1:{args.ollama_port}"
    pf_url = f"http://127.0.0.1:{args.pf_port}"
    env = dict(os.environ)
    pf_rev = None
    digest = None
    try:
        if not args.no_ner:
            ollama = start(["ollama", "serve"], {**os.environ, "OLLAMA_HOST": f"127.0.0.1:{args.ollama_port}"}, logdir / "ollama.log")
            if not wait_for(f"{ollama_url}/api/tags", 60):
                print("ollama did not come up", file=sys.stderr)
                return 1
            digest = model_digest(ollama_url, args.ner_model)
            if not digest:
                print(f"model {args.ner_model} is not installed locally; not pulling it", file=sys.stderr)
                return 1
            # Load the model before the test's first request, so no request times out on it.
            post(f"{ollama_url}/api/chat", {"model": args.ner_model, "stream": False,
                                            "messages": [{"role": "user", "content": "ready"}]})
            env["LOKE_AD13_OLLAMA_URL"] = ollama_url
            env["LOKE_AD13_NER_MODEL"] = args.ner_model
        if not args.no_pf:
            snap = PF_SNAPSHOTS
            revs = sorted(p.name for p in snap.iterdir()) if snap.is_dir() else []
            if len(revs) != 1:
                print(f"expected one cached privacy-filter revision, found {revs}", file=sys.stderr)
                return 1
            pf_rev = revs[0]
            pf = start([sys.executable, str(REPO / "packages/privacy-filter/server.py"), str(args.pf_port)],
                       {**os.environ, "HF_HUB_OFFLINE": "1", "LOKE_PF_REVISION": pf_rev}, logdir / "pf.log")
            if not wait_for(f"{pf_url}/health", 300):
                print("privacy-filter sidecar did not come up", file=sys.stderr)
                return 1
            env["LOKE_AD13_PF_URL"] = pf_url

        runs = []
        for i in range(args.runs):
            t0 = time.time()
            out = run_test(env)
            r = parse(out)
            ok = f"PASS         {TEST}" in out
            print(f"run {i + 1}/{args.runs}: {'PASS' if ok else 'FAIL'} in {time.time() - t0:.0f}s")
            for name, kv in r["layers"].items():
                print(f"  {name:<10} recall {kv['recall']:>7} ({kv['matched']}/{kv['labelled']})  "
                      f"direct {kv['direct_recall']:>7} ({kv['direct_matched']}/{kv['direct_labelled']})  "
                      f"precision {kv['precision']:>7}  fp {kv['false_positives']}")
            for name, kv in r["marginal"].items():
                print(f"  +{name:<9} recall_gain {kv['recall_gain']}  direct_gain {kv['direct_gain']}  fp_added {kv['fp_added']}")
            if not ok:
                print(out, file=sys.stderr)
                print("the test failed; nothing is recorded from an invalid run", file=sys.stderr)
                return 1
            runs.append(r)
    finally:
        stop(ollama)
        stop(pf)

    if args.record:
        caveat = ("Synthetic 74-case corpus; entity-level, type-agnostic overlap. NER model is the one "
                  "named, which may not be loke's default (qwen2.5:7b). The privacy-filter sidecar is "
                  "an opt-in layer of pipeline.run (F3b.3), off by default. Presidio not measured.")
        layer_model = {"ner": (f"ollama:{args.ner_model}", digest), "pf": ("openai/privacy-filter", pf_rev)}
        written, refused = record(runs, workload=workload, caveat=caveat, layer_model=layer_model)
        print(f"recorded {len(written)} row(s) to {result.RESULTS_DIR}")
        if refused:
            print(f"NOT recorded, {len(refused)} row(s):", file=sys.stderr)
            for line in refused:
                print(f"  {line}", file=sys.stderr)
            return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
