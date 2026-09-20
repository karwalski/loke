#!/usr/bin/env python3
"""Measure input tokens per serialisation format (story VM1.7).

What this measures, and what it does not
----------------------------------------
It measures **input token counts** for the same data in three formats, with real
provider tokenisers, and records each figure through `benchmarks/lib/result.py` so
it cannot be published without its tokeniser, workload and sample size.

It does **not** measure accuracy, latency or cost, and it makes no model calls. The
accuracy half of the methodology needs an LLM-as-judge and repeated frontier-model
calls across every configuration, which is real recurring spend and is a decision
that has not been taken. So this half runs for free, produces a defensible number
today, and the expensive half stays unstarted rather than half-started.

A token-count-only result is still worth having, and is also the easiest thing to
overclaim with. Two rules hold it in place:

  1. A compression ratio is not an accuracy claim. A format that halves the tokens
     and halves the accuracy is worse, not twice as good, and this harness cannot
     tell you which happened. Every result carries that caveat.
  2. The minified-JSON baseline is reported next to every other format, because a
     format that only matches B2 has achieved whitespace removal.

Usage
-----
    python3 benchmarks/toon/run.py            # measure and print
    python3 benchmarks/toon/run.py --record   # also write to benchmarks/results/
    python3 benchmarks/toon/run.py --self-test
"""

from __future__ import annotations

import argparse
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from benchmarks.lib import result as result_sink  # noqa: E402
from benchmarks.toon.lib import datasets, serialisers, tokenisers  # noqa: E402

WORKLOAD = "toon-baselines-v1"

CAVEAT = (
    "Input token count only. No model was called, so this says nothing about "
    "accuracy: a format that halves the tokens and halves the accuracy is worse, "
    "not better. Compare every format against b2_json_min — a format that only "
    "matches minified JSON has achieved whitespace removal, not compression."
)


def collect() -> tuple[dict, list[str], dict]:
    """Measure every (payload, format, tokeniser). Returns rows, problems, digests."""
    toks = tokenisers.available()
    problems: list[str] = []
    if not toks:
        problems.append(
            "no tokeniser is available offline. Install tiktoken, or cache a "
            "HuggingFace tokeniser locally. Character counts are not a substitute — "
            "that is the defect this story exists to fix.")
        return {}, problems, {}

    rows: dict = {}
    digests: dict[str, str] = {}

    for spec in datasets.SPECS:
        try:
            payload = datasets.build(spec)
        except FileNotFoundError as e:
            problems.append(f"{spec.name}: {e}")
            continue
        except datasets.LicenceError as e:
            problems.append(f"{spec.name}: {e}")
            continue

        digests[spec.name] = datasets.digest(payload)

        for fmt in serialisers.FORMATS:
            if not serialisers.roundtrips(fmt, payload):
                # Not a warning. A lossy format shows the model different data, so
                # its token count is not comparable and the pairing is dropped.
                problems.append(
                    f"{spec.name}/{fmt}: does not round-trip, so its token count "
                    "describes different data than the baseline. Excluded.")
                continue
            text = serialisers.serialise(fmt, payload)
            for tok in toks:
                n = tok.count(text)
                rows[(spec.name, fmt, tok.name)] = {
                    "tokens": n,
                    "chars": len(text),
                    "shape": spec.shape,
                    "licence": spec.licence,
                    "provider": tok.provider,
                }
    return rows, problems, digests


def report(rows: dict, problems: list[str], digests: dict, record: bool) -> int:
    if problems:
        print("PROBLEMS")
        for p in problems:
            print("  - " + p)
        print()
    if not rows:
        print("Nothing measured.")
        return 1

    tok_names = sorted({k[2] for k in rows})
    payloads = [s.name for s in datasets.SPECS if any(k[0] == s.name for k in rows)]

    print(f"workload {WORKLOAD}")
    print(f"tokenisers: {', '.join(tok_names)}")
    for provider, why in tokenisers.UNAVAILABLE.items():
        print(f"  {provider}: NOT MEASURED — {why.split('.')[0]}.")
    print(f"formats implemented: {', '.join(serialisers.FORMATS)}")
    for fmt, why in serialisers.UNIMPLEMENTED.items():
        print(f"  {fmt}: NOT IMPLEMENTED — {why.split('.')[0]}.")
    print()

    written = 0
    for payload in payloads:
        base_key = lambda t: (payload, "b1_json", t)  # noqa: E731
        print(f"{payload}")
        for fmt in serialisers.FORMATS:
            ratios = []
            counts = []
            for t in tok_names:
                k = (payload, fmt, t)
                b = base_key(t)
                if k not in rows or b not in rows:
                    continue
                counts.append(rows[k]["tokens"])
                ratios.append(tokenisers.compression_ratio(
                    rows[b]["tokens"], rows[k]["tokens"]))
            if not ratios:
                continue
            gm_ratio = tokenisers.geometric_mean(ratios)
            gm_tokens = tokenisers.geometric_mean([float(c) for c in counts])
            per_tok = "  ".join(
                f"{t}={rows[(payload, fmt, t)]['tokens']}"
                for t in tok_names if (payload, fmt, t) in rows)
            print(f"  {fmt:<14} ratio {gm_ratio:5.3f}  tokens(gm) {gm_tokens:9.1f}   {per_tok}")

            if record and fmt != "b1_json":
                m = result_sink.Measurement(
                    metric="input_token_compression_ratio",
                    value=round(gm_ratio, 4),
                    units="ratio",
                    workload=f"{WORKLOAD}/{payload}",
                    n=len(ratios),
                    arm=fmt,
                    tokenizer="geometric-mean:" + ",".join(tok_names),
                    notes=(f"tokens(b1_json)/tokens({fmt}), geometric mean over "
                           f"{len(ratios)} tokenisers. Payload sha256 "
                           f"{digests.get(payload, '?')[:16]}."),
                    caveat=CAVEAT,
                )
                result_sink.validate(m)
                result_sink.write(m)
                written += 1
        print()

    chk_problems = datasets.verify_checksums(digests)
    if chk_problems:
        print("CHECKSUM MISMATCH")
        for p in chk_problems:
            print("  - " + p)
        return 1
    if not datasets.CHECKSUMS.exists():
        datasets.write_checksums(digests)
        print(f"wrote {datasets.CHECKSUMS.relative_to(REPO)} ({len(digests)} payloads)")

    if record:
        print(f"recorded {written} measurement(s) through benchmarks/lib/result.py")
    else:
        print("not recorded — pass --record to write to benchmarks/results/")
    return 0


def self_test() -> int:
    """Guards on the instrument, before any figure from it is quoted."""
    failures = []

    def check(cond, msg):
        if not cond:
            failures.append(msg)

    # 1. Minified JSON must beat indented JSON on tokens. If it does not, the
    #    tokeniser or the serialiser is wrong and every ratio is suspect.
    data = datasets._uniform_tabular(50)
    toks = tokenisers.available()
    check(bool(toks), "no tokeniser available; the harness cannot measure anything")
    if toks:
        t = toks[0]
        b1 = t.count(serialisers.b1_json(data))
        b2 = t.count(serialisers.b2_json_min(data))
        check(b2 < b1, f"minified JSON should use fewer tokens than indented ({b2} vs {b1})")
        check(tokenisers.compression_ratio(b1, b2) > 1.0,
              "a smaller candidate must give a ratio above 1.0")

    # 2. Every format must round-trip every shape. A lossy format's token count is
    #    not comparable, and YAML type coercion is a real hazard here.
    for spec in datasets.SPECS:
        if spec.licence != "generated":
            continue
        payload = datasets.build(spec)
        for fmt in serialisers.FORMATS:
            check(serialisers.roundtrips(fmt, payload),
                  f"{spec.name}/{fmt} does not round-trip")

    # 3. Determinism: the same spec built twice must be byte-identical, or the
    #    checksum is meaningless.
    a = datasets.digest(datasets._uniform_tabular(100))
    b = datasets.digest(datasets._uniform_tabular(100))
    check(a == b, "payload generation is not deterministic")

    # 4. The geometric mean must refuse a zero count rather than returning 0.0.
    try:
        tokenisers.geometric_mean([10, 0, 5])
        check(False, "geometric_mean accepted a zero token count")
    except ValueError:
        pass

    # 5. A licence outside the allowed set must be refused.
    bad = datasets.PayloadSpec("x", "s", "all-rights-reserved", "nowhere",
                               lambda n: [], 0)
    try:
        datasets.build(bad)
        check(False, "a non-redistributable licence was accepted")
    except datasets.LicenceError:
        pass

    # 6. An unimplemented format must raise, never fall back to something else.
    try:
        serialisers.serialise("f4_toon", {"a": 1})
        check(False, "serialise() accepted an unimplemented format")
    except KeyError:
        pass

    # 7. The caveat must say what the number cannot tell you.
    check("accuracy" in CAVEAT.lower(), "the caveat must mention accuracy")
    check("b2_json_min" in CAVEAT, "the caveat must point at the whitespace control")

    if failures:
        print(f"SELF-TEST FAILED — {len(failures)} guard(s):", file=sys.stderr)
        for f in failures:
            print("  - " + f, file=sys.stderr)
        return 1
    print("self-test passed: 7 guard groups")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--record", action="store_true",
                    help="write measurements through benchmarks/lib/result.py")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    rows, problems, digests = collect()
    return report(rows, problems, digests, args.record)


if __name__ == "__main__":
    sys.exit(main())
