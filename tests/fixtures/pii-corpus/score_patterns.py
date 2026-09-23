#!/usr/bin/env python3
"""Score loke's regex layer against the PII corpus (story AD1.2, partial).

What this measures, and what it does not
----------------------------------------
It reads the ten pattern strings **directly from
`packages/core/src/privacy/patterns.tk`** and evaluates them against the corpus
with Python's `re`. It does not reimplement them, so it is not the stub-test
antipattern this project is trying to get away from.

**It is nonetheless not a measurement of loke.** Two limits, both material:

1. Python's regex engine is not toke's. Character-class handling, anchoring and
   greediness can differ, so a discrepancy here may be an engine difference
   rather than a pattern defect.
2. The regex layer is one of several. loke also runs NER and, optionally, a
   sidecar model. A recall figure for the regex layer alone is a floor, not
   loke's recall.

So the output is labelled `regex-layer-python-re` and must not be quoted as
loke's detection accuracy. The real figure requires the compiled detector and is
blocked on the toolchain migration. This exists to make the corpus useful now, to
prove the corpus discriminates, and to size the problem.

Scoring
-------
Entity-level, not token-level, and **recall-weighted**: a false negative leaks,
whereas a false positive only costs utility. Precision is reported as the utility
cost, never as the headline.

A detection counts as a true positive if it overlaps a labelled span at all. Exact
span matching is stricter and arguably more correct, so both are reported —
`docs/specifications/artifact-contract.md`-style precision about which rule is in
force matters, because the numbers differ.

Usage
-----
    python3 tests/fixtures/pii-corpus/generate.py            # write corpus.jsonl
    python3 tests/fixtures/pii-corpus/score_patterns.py
    python3 tests/fixtures/pii-corpus/score_patterns.py --record   # to results
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
PATTERNS_TK = REPO / "packages" / "core" / "src" / "privacy" / "patterns.tk"
CORPUS = HERE / "corpus.jsonl"

# Entity types the regex layer is actually responsible for. PERSON and the
# Australian identifiers with no pattern are NER's job or nobody's, so scoring
# the regex layer against them understates it; scoring loke as a whole without
# them overstates it. Both figures are therefore reported.
REGEX_ADDRESSABLE = {
    "EMAIL", "PHONE_AU", "PHONE_US", "CREDIT_CARD", "IP_V4",
    "AU_TFN", "AU_ABN", "SSN_US", "URL", "API_KEY",
}

# Pattern function name in patterns.tk -> corpus entity type.
PATTERN_TO_TYPE = {
    "patemail": "EMAIL",
    "patphoneau": "PHONE_AU",
    "patphoneus": "PHONE_US",
    "patcreditcard": "CREDIT_CARD",
    "patipv4": "IP_V4",
    "patautfn": "AU_TFN",
    "patauabn": "AU_ABN",
    "patssnus": "SSN_US",
    "paturl": "URL",
    "patapikey": "API_KEY",
}


def load_patterns() -> dict[str, str]:
    """Extract the pattern strings from the toke source, unmodified."""
    src = PATTERNS_TK.read_text(encoding="utf-8")
    found: dict[str, str] = {}
    for fn in PATTERN_TO_TYPE:
        m = re.search(rf'f={re.escape(fn)}\(\):str\{{\s*<"((?:[^"\\]|\\.)*)"', src)
        if not m:
            print(f"WARNING: could not extract {fn} from {PATTERNS_TK.name}", file=sys.stderr)
            continue
        raw = m.group(1)
        # toke source escapes backslashes for its own string literal; unescape
        # one level to recover the regex the engine actually receives.
        found[fn] = raw.replace("\\\\", "\\")
    return found


# ── The two post-match filters the shipped detector applies (PL1.10) ──────────
#
# IMPORTANT, and a genuine weakening of this instrument: the pattern strings above
# are READ from patterns.tk, so they are not reimplemented. These two predicates
# ARE reimplemented, from `packages/core/src/privacy/regex.tk`
# (`digitrunpattern`, `boundaryclear`, `tfnchecksumvalid`). That is the stub-test
# antipattern this file's header warns about, applied knowingly and for one reason:
# without them this script scores a detector that no longer exists, and a figure
# describing code that does not ship is worse than a figure with a stated caveat.
#
# So both are reported — unfiltered and filtered — and the delta is the filters'
# contribution. If the toke predicates change, these must be changed with them, and
# the only real fix is AD1.2's harness driving the compiled detector.

# Patterns whose whole match is a bare digit run, so an adjacent digit means the
# match is a fragment of a longer number. Mirrors regex.digitrunpattern.
# Keyed by the toke FUNCTION name, which is what load_patterns returns — the toke
# side keys the same set by pdef.name (au_tfn, au_abn, …). Getting this wrong is
# silent: the filter simply never fires and the figures come out unchanged, which is
# how the first version of this looked like it worked.
DIGIT_RUN_PATTERNS = {
    "patautfn", "patauabn", "patssnus", "patcreditcard", "patphoneau",
    "patphoneus", "patipv4",
}

TFN_WEIGHTS = [1, 4, 3, 7, 5, 8, 6, 9, 10]


def boundary_clear(text: str, start: int, end: int) -> bool:
    """Mirrors regex.boundaryclear: no digit immediately either side of the match."""
    if start > 0 and text[start - 1].isdigit():
        return False
    if end < len(text) and text[end].isdigit():
        return False
    return True


def tfn_checksum_valid(value: str) -> bool:
    """Mirrors regex.tfnchecksumvalid: weighted sum mod 11."""
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 9:
        return False
    return sum(w * d for w, d in zip(TFN_WEIGHTS, digits)) % 11 == 0


def detect(text: str, patterns: dict[str, str], filters: bool = True) -> list[dict]:
    """Run every pattern, as the detector does, and collect spans.

    With `filters=False` this is the pre-PL1.10 detector, which is what the
    2026-09-19 figures in docs/metrics-baseline.md describe.
    """
    out = []
    for fn, pat in patterns.items():
        try:
            # No IGNORECASE: the patterns do not request it, and whether the
            # detector applies it is exactly one of the things under test.
            for m in re.finditer(pat, text):
                if filters and fn in DIGIT_RUN_PATTERNS:
                    if not boundary_clear(text, m.start(), m.end()):
                        continue
                if filters and fn == "patautfn":
                    if not tfn_checksum_valid(m.group(0)):
                        continue
                out.append({
                    "type": PATTERN_TO_TYPE[fn],
                    "pattern": fn,
                    "value": m.group(0),
                    "start": m.start(),
                    "end": m.end(),
                })
        except re.error as e:
            print(f"WARNING: {fn} is not valid in Python re: {e}", file=sys.stderr)
    return out


def overlaps(a: dict, b: dict) -> bool:
    return a["start"] < b["end"] and b["start"] < a["end"]


def score(corpus: list[dict], patterns: dict[str, str], filters: bool = True) -> dict:
    # Recall is computed only over entities loke claims to detect. Entities with
    # expected_detected false are counted separately, because scoring loke
    # against types it has no detector for would conflate two different problems.
    tp_overlap = tp_exact = fn_missed = 0
    tp_addressable = fn_addressable = 0
    fp = 0
    undetectable_total = undetectable_found = 0
    per_type: dict[str, dict[str, int]] = {}
    fp_by_pattern: dict[str, int] = {}

    for case in corpus:
        text = case["text"]
        dets = detect(text, patterns, filters)
        labelled = case["entities"]

        claimed = [e for e in labelled if e["expected_detected"] and e["type"] != "NOT_PII"]
        unclaimed = [e for e in labelled if not e["expected_detected"] and e["type"] != "NOT_PII"]
        must_not = [e for e in labelled if e["type"] == "NOT_PII"]

        for e in claimed:
            t = per_type.setdefault(e["type"], {"tp": 0, "fn": 0})
            hit = [d for d in dets if overlaps(d, e)]
            addressable = e["type"] in REGEX_ADDRESSABLE
            if hit:
                tp_overlap += 1
                t["tp"] += 1
                if addressable:
                    tp_addressable += 1
                if any(d["start"] == e["start"] and d["end"] == e["end"] for d in hit):
                    tp_exact += 1
            else:
                fn_missed += 1
                t["fn"] += 1
                if addressable:
                    fn_addressable += 1

        for e in unclaimed:
            undetectable_total += 1
            if any(overlaps(d, e) for d in dets):
                undetectable_found += 1

        # A detection is a false positive if it overlaps nothing that should be
        # detected. Overlapping a NOT_PII span is the clearest case.
        for d in dets:
            if any(overlaps(d, e) for e in claimed + unclaimed):
                continue
            fp += 1
            fp_by_pattern[d["pattern"]] = fp_by_pattern.get(d["pattern"], 0) + 1

    recall = tp_overlap / (tp_overlap + fn_missed) if (tp_overlap + fn_missed) else 0.0
    recall_exact = tp_exact / (tp_overlap + fn_missed) if (tp_overlap + fn_missed) else 0.0
    precision = tp_overlap / (tp_overlap + fp) if (tp_overlap + fp) else 0.0

    denom_addr = tp_addressable + fn_addressable
    return {
        "recall_regex_addressable": (tp_addressable / denom_addr) if denom_addr else 0.0,
        "regex_addressable_total": denom_addr,
        "regex_addressable_missed": fn_addressable,
        "recall_overlap": recall,
        "recall_exact_span": recall_exact,
        "precision_overlap": precision,
        "true_positives": tp_overlap,
        "false_negatives": fn_missed,
        "false_positives": fp,
        "per_type": per_type,
        "false_positives_by_pattern": fp_by_pattern,
        "undetectable_entities": undetectable_total,
        "undetectable_incidentally_matched": undetectable_found,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", type=pathlib.Path, default=CORPUS)
    ap.add_argument("--record", action="store_true",
                    help="write the result through benchmarks/lib/result.py")
    args = ap.parse_args()

    if not args.corpus.is_file():
        print(f"corpus not found at {args.corpus} — run generate.py first", file=sys.stderr)
        return 1

    corpus = [json.loads(l) for l in args.corpus.read_text().splitlines() if l.strip()]
    patterns = load_patterns()
    print(f"extracted {len(patterns)} of {len(PATTERN_TO_TYPE)} patterns from {PATTERNS_TK.name}\n")

    r = score(corpus, patterns)

    print("Regex layer only, Python re engine — NOT loke's detection accuracy")
    print("-" * 66)
    print(f"  recall, regex-addressable types only   {r['recall_regex_addressable']:.3f}   "
          f"({r['regex_addressable_total'] - r['regex_addressable_missed']}"
          f"/{r['regex_addressable_total']})")
    print(f"    ^ the fair figure for this layer: excludes PERSON and the")
    print(f"      identifiers with no pattern at all")
    print()
    print(f"  recall, all claimed types              {r['recall_overlap']:.3f}   "
          f"({r['true_positives']} found, {r['false_negatives']} missed)")
    print(f"    ^ the floor for loke as a whole: the layers that would cover")
    print(f"      the remainder are not running here")
    print(f"  recall (exact span)     {r['recall_exact_span']:.3f}")
    print(f"  precision (overlap)     {r['precision_overlap']:.3f}   "
          f"({r['false_positives']} false positives)")
    print()
    print("  Per type (of the types loke claims to detect):")
    for t, c in sorted(r["per_type"].items()):
        tot = c["tp"] + c["fn"]
        print(f"    {t:<14} recall {c['tp']}/{tot}")
    print()
    if r["false_positives_by_pattern"]:
        print("  False positives by pattern — these cost precision:")
        for p, n in sorted(r["false_positives_by_pattern"].items(), key=lambda kv: -kv[1]):
            print(f"    {p:<14} {n}")
        print()
    print(f"  Entities of types with no detector: {r['undetectable_entities']} "
          f"({r['undetectable_incidentally_matched']} matched incidentally by "
          f"another pattern)")
    print()
    print("Interpretation: recall is the metric that matters here, because a missed")
    print("entity leaves the device. Precision is the utility cost of achieving it.")

    if args.record:
        sys.path.insert(0, str(REPO))
        from benchmarks.lib.result import Measurement, write
        for metric, value in (("pii_recall_regex_addressable", r["recall_regex_addressable"]),
                              ("pii_recall_all_claimed_types", r["recall_overlap"]),
                              ("pii_precision_overlap", r["precision_overlap"])):
            write(Measurement(
                metric=metric, value=round(value, 4), units="ratio",
                workload=f"pii-corpus-{len(corpus)}-cases", n=r["true_positives"] + r["false_negatives"],
                arm="regex-layer-python-re",
                caveat="Regex layer only, evaluated with Python's re engine rather than "
                       "toke's. Not loke's detection accuracy: other layers are not "
                       "included and engine behaviour may differ.",
            ))
        print("\nrecorded to benchmarks/results/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
