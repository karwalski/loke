#!/usr/bin/env python3
"""F3.1a - throughput of loke's compiled regex PII detector.

F3.1 has carried a "10MB/s target" since it was written, and nothing had ever timed the
detector. This harness does, by the VM1.3 method: N runs per size, the first discarded as
warm-up, reported as a median and a range (and a percentile-bootstrap interval of the mean
through benchmarks/lib/result.py).

What is timed: `core.privacy.regex.detect`, the function the privacy pipeline calls, which
is pattern matching PLUS span recovery, the PL1.10 filters, placeholder assignment and
applying the placeholders to the text. That is the layer's real cost, not the regex engine's
alone. The clock is std.time's millisecond wall clock, read inside the compiled program, so
process start-up and reading the file are excluded.

Workload: the committed PII corpus (tests/fixtures/pii-corpus, seed 20260919) - every case
text in file order, each followed by FILLER_LINES lines of PII-free prose, repeated until the
target size is reached and cut at a line boundary. The labelled-entity density is computed
and printed rather than assumed, because a throughput figure without its density is not
comparable to anything.

Usage:
    python3 tests/fixtures/pii-corpus/generate.py
    TOKE_DIR=... python3 benchmarks/regex/run.py [--sizes 1,10] [--runs 6] [--record]

Needs scripts/build_loke.sh to have been run (it links build/ooke objects via the same
archives scripts/run_tests.sh builds under $BUILDDIR).
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import statistics
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
CORPUS = REPO / "tests" / "fixtures" / "pii-corpus" / "corpus.jsonl"
SRC = REPO / "benchmarks" / "regex" / "bench.tk"

FILLER = (
    "The quarterly review covered delivery timelines, the migration plan and the "
    "remaining open questions about vendor support for the reporting service.\n"
)
FILLER_LINES = 8


def build_text(target_bytes: int) -> tuple[str, int, int]:
    """The corpus text of the given size, and its labelled PII and decoy counts.

    Counted piece by piece as the text is assembled, so the counts describe exactly the
    bytes that are timed. NOT_PII labels are decoys the detector must NOT report, so they
    are counted separately rather than inflating the PII density.
    """
    cases = [json.loads(l) for l in CORPUS.read_text(encoding="utf-8").splitlines() if l.strip()]
    filler = FILLER * FILLER_LINES
    pieces = []
    for c in cases:
        pii = sum(1 for e in c["entities"] if e["type"] != "NOT_PII")
        decoys = len(c["entities"]) - pii
        pieces.append((c["text"].replace("\n", " ") + "\n", pii, decoys))
        pieces.append((filler, 0, 0))
    out, size, pii_total, decoy_total = [], 0, 0, 0
    i = 0
    while True:
        text, pii, decoys = pieces[i % len(pieces)]
        n = len(text.encode("utf-8"))
        if size + n > target_bytes:
            break
        out.append(text)
        size += n
        pii_total += pii
        decoy_total += decoys
        i += 1
    return "".join(out), pii_total, decoy_total


def compile_bench(builddir: pathlib.Path) -> pathlib.Path:
    tokedir = pathlib.Path(os.environ["TOKE_DIR"])
    ll = builddir / "bench_regex.ll"
    exe = builddir / "bench_regex"
    subprocess.run(
        [str(tokedir / "toke"), f"--config={REPO / 'tkc.toml'}", "-I", str(REPO / "build" / "interfaces"),
         "--emit-llvm", "--out", str(ll), str(SRC)],
        check=True,
    )
    stdlib = tokedir / "src" / "stdlib"
    vendor = tokedir / "stdlib" / "vendor"
    archives = [builddir / "libloke.a", builddir / "libooke.a", builddir / "libtokestd.a"]
    for a in archives:
        if not a.is_file():
            sys.exit(f"missing {a}: run scripts/run_tests.sh once with BUILDDIR={builddir}")
    subprocess.run(
        ["clang", "-std=c99", "-D_GNU_SOURCE", "-O1", "-iquote", str(stdlib), f"-I{vendor}/cmark/src",
         f"-I{vendor}/tomlc99", "-I/opt/homebrew/include", "-Wno-implicit-function-declaration",
         "-DTK_HAVE_OPENSSL", "-L/opt/homebrew/lib", "-x", "ir", str(ll), "-x", "none",
         *map(str, archives), "-o", str(exe), "-lm", "-lz", "-lsqlite3", "-lssl", "-lcrypto",
         "-framework", "Security", "-framework", "CoreFoundation", "-lobjc"],
        check=True, stderr=subprocess.DEVNULL,
    )
    return exe


def measure(exe: pathlib.Path, text: str, runs: int, workdir: pathlib.Path) -> tuple[int, list[int], list[int], list[int]]:
    """One FRESH PROCESS per run, and each run's peak RSS from wait4.

    Not N runs inside one process: the detector does not release what it allocates, so in a
    single process run k pays for the memory of runs 1..k-1 and the times climb (measured:
    1.9 s to 7.3 s across eleven 1 MB runs). Separate processes make the runs independent,
    which is what a median and a range over them assume.
    """
    path = workdir / "corpus.txt"
    path.write_text(text, encoding="utf-8")
    env = dict(os.environ, LOKE_BENCH_CORPUS=str(path), LOKE_BENCH_RUNS="1")
    nbytes = 0
    ms, found, rss = [], [], []
    for _ in range(runs):
        proc = subprocess.Popen([str(exe)], env=env, stdout=subprocess.PIPE, text=True)
        out = proc.stdout.read()
        _, status, usage = os.wait4(proc.pid, 0)
        proc.returncode = os.waitstatus_to_exitcode(status)
        if proc.returncode != 0:
            sys.exit(f"bench process exited {proc.returncode} (negative = killed by that signal); "
                     f"peak RSS {usage.ru_maxrss} bytes\n{out}")
        rss.append(usage.ru_maxrss)  # bytes on macOS
        for line in out.splitlines():
            parts = line.split()
            if parts[:1] == ["bytes"]:
                nbytes = int(parts[1])
            elif parts[:1] == ["run"]:
                ms.append(int(parts[1]))
                found.append(int(parts[2]))
    if len(ms) != runs:
        sys.exit(f"expected {runs} runs, got {len(ms)}")
    return nbytes, ms, found, rss


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sizes", default="1,10", help="corpus sizes in MB (10^6 bytes)")
    ap.add_argument("--runs", type=int, default=6, help="runs per size, INCLUDING the discarded warm-up")
    ap.add_argument("--record", action="store_true", help="append to benchmarks/results via lib/result.py")
    ap.add_argument("--toke-commit", default=None, help="toke commit actually built against")
    a = ap.parse_args()
    if not CORPUS.is_file():
        sys.exit("corpus missing: python3 tests/fixtures/pii-corpus/generate.py")
    builddir = pathlib.Path(os.environ.get("BUILDDIR", "/tmp/loke-tests"))
    exe = compile_bench(builddir)
    for mb in [float(s) for s in a.sizes.split(",")]:
        text, labelled, decoys = build_text(int(mb * 1_000_000))
        nbytes, ms, found, rss = measure(exe, text, a.runs, builddir)
        kept = ms[1:]
        if min(kept) < 20:
            sys.exit(f"{mb} MB ran in under 20 ms; the ms clock cannot resolve it - use a larger size")
        mbps = [nbytes / 1_000_000 / (x / 1000.0) for x in kept]
        print(json.dumps({
            "size_bytes": nbytes, "labelled_pii": labelled, "labelled_decoys": decoys,
            "labelled_per_kb": round(labelled / (nbytes / 1000), 3),
            "detections_per_run": sorted(set(found)),
            "runs_ms_including_warmup": ms,
            "median_ms": statistics.median(kept), "min_ms": min(kept), "max_ms": max(kept),
            "median_mb_per_s": round(statistics.median(mbps), 3),
            "range_mb_per_s": [round(min(mbps), 3), round(max(mbps), 3)],
            "n_runs_kept": len(kept),
            "peak_rss_mb_median": round(statistics.median(rss[1:] or rss) / 1_000_000, 1),
        }))
        if a.record:
            sys.path.insert(0, str(REPO))
            from benchmarks.lib.result import summarise, write
            m = summarise([float(x) for x in mbps], discard_first=False,
                          metric="regex_detect_throughput", units="MB/s (10^6 bytes)",
                          workload=f"pii-corpus-seed20260919-plus-filler-{mb:g}MB", arm="regex-layer-toke-compiled",
                          tokenizer="bytes", seed=20260919,
                          notes=f"median {statistics.median(mbps):.3f}, range {min(mbps):.3f}-{max(mbps):.3f}; warm-up run discarded before this call",
                          caveat="core.privacy.regex.detect only; one host; ms wall clock; one process per run; peak RSS median %.1f MB" % (statistics.median(rss[1:] or rss) / 1_000_000))
            if a.toke_commit:
                m.toke_commit = a.toke_commit
            write(m)
    return 0


if __name__ == "__main__":
    sys.exit(main())
