#!/usr/bin/env python3
"""check_claims.py — CI gate for the claims register and published figures.

Story X6.3. Python 3, standard library only.

Three checks:

  1. Every row in docs/claims.md marked `verified` must carry an evidence pointer
     in its "Implementing code" column — a file path, with a line reference where
     the claim is about specific code.

  3. (GA1.11) Every `page.md:line` pointer in the "Where" column of a row that quotes
     its claim must land on lines that hold the quote's distinctive words.

  2. Every numeric figure appearing in README.md or docs/features-*.md must have a
     corresponding entry in docs/metrics-baseline.md, which is the only place this
     project publishes figures from.

Check 2 is deliberately conservative. A false positive that blocks the build on a
port number or a version string is worse than a miss, so the matcher looks only for
the shapes a *performance or capability figure* takes — percentages, multipliers,
latency and throughput budgets — and drops anything that looks like a port, a
version, a year, a file size, a story ID, an entity count, a row count or a
threshold declared in code. Every exclusion is listed in EXCLUSIONS below so the
rule set can be argued with rather than guessed at.

Usage:
    python3 scripts/check_claims.py            # report, exit non-zero on failure
    python3 scripts/check_claims.py --check     # same, for CI (explicit)
    python3 scripts/check_claims.py --verbose   # also list what was skipped and why
    python3 scripts/check_claims.py --root DIR  # run against a different tree
"""

import argparse
import os
import re
import sys

CLAIMS = "docs/claims.md"
BASELINE = "docs/metrics-baseline.md"
FIGURE_SOURCES = ["README.md", "docs/features-loke.md", "docs/features-moke.md"]

VERDICTS = ("verified", "partial", "stub", "absent")

# ---------------------------------------------------------------------------
# Check 1 — verified rows need an evidence pointer
# ---------------------------------------------------------------------------

# A row id looks like A1, B10, L6 — section letter plus number.
ROW_ID = re.compile(r"^[A-Z]\d+$")

# An evidence pointer is a path with a source extension, optionally :line or
# :line-line or :line,line. Backticks are stripped before matching.
EVIDENCE = re.compile(
    r"[\w./-]+\.(?:tk|tkt|tki|py|sh|json|toml|yml|yaml|js|md)"
    r"(?::\d+(?:[-,]\d+)*)?"
)

# Phrases that explicitly say no code was found. A verified row must not use one.
NO_CODE_PHRASES = (
    "none",
    "no implementing code",
    "not found",
    "zero matches",
    "n/a",
)


def split_row(line):
    """Split a markdown table row into stripped cells, or return None."""
    if not line.lstrip().startswith("|"):
        return None
    return [c.strip() for c in line.strip().strip("|").split("|")]


def parse_claims(path):
    """Yield (lineno, row_id, verdict, evidence_cell) for each register row."""
    rows = []
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            cells = split_row(line)
            if not cells or len(cells) < 7:
                continue
            if not ROW_ID.match(cells[0]):
                continue
            verdict = cells[3].strip("`").strip().lower()
            if verdict not in VERDICTS:
                continue
            rows.append((lineno, cells[0], verdict, cells[4]))
    return rows


def check_evidence(root, errors, warnings, verbose_notes):
    path = os.path.join(root, CLAIMS)
    if not os.path.exists(path):
        errors.append(f"{CLAIMS}: missing. The claims register is required (story X6.1).")
        return 0

    rows = parse_claims(path)
    if not rows:
        errors.append(
            f"{CLAIMS}: no claim rows parsed. Expected tables whose first column is a "
            f"row id such as A1 and whose fourth column is a verdict in {VERDICTS}."
        )
        return 0

    seen = {}
    verified = 0
    for lineno, row_id, verdict, evidence in rows:
        if row_id in seen:
            errors.append(
                f"{CLAIMS}:{lineno}: duplicate row id {row_id} "
                f"(first seen at line {seen[row_id]})."
            )
        seen[row_id] = lineno

        if verdict != "verified":
            continue
        verified += 1

        bare = evidence.replace("`", "").replace("*", "").strip()
        lowered = bare.lower()

        if not bare or bare in {"-", "—", "–"}:
            errors.append(
                f"{CLAIMS}:{lineno}: row {row_id} is marked `verified` but its "
                f"implementing-code column is empty. Name the file and line, or "
                f"change the verdict."
            )
            continue

        if any(lowered.startswith(p) for p in NO_CODE_PHRASES):
            errors.append(
                f"{CLAIMS}:{lineno}: row {row_id} is marked `verified` but its "
                f"implementing-code column says {bare[:40]!r}. A verified claim needs "
                f"code behind it."
            )
            continue

        if not EVIDENCE.search(bare):
            errors.append(
                f"{CLAIMS}:{lineno}: row {row_id} is marked `verified` but no file path "
                f"was found in its implementing-code column. Give a path such as "
                f"packages/core/src/privacy/regex.tk:20-31."
            )
            continue

        # A path with no line reference is allowed (a whole-module claim) but noted.
        if not re.search(r"\.\w+:\d", bare):
            verbose_notes.append(
                f"{CLAIMS}:{lineno}: row {row_id} cites a file with no line reference. "
                f"Acceptable for a whole-module claim; add a line for anything narrower."
            )

    return verified


# ---------------------------------------------------------------------------
# Check 3 — a "Where" pointer must still point at the claim (GA1.11)
# ---------------------------------------------------------------------------
#
# The Where column cites the line of a public page that makes the claim, e.g.
# `docs/features-loke.md:44`. Those pages are edited all the time, and in October
# 2026 about a hundred such pointers were found aimed at unrelated lines. For a row
# whose claim quotes the page ("..." or “...”), each `.md` pointer in its Where
# cell must land on lines holding at least two of the quote's distinctive tokens
# (one, if the quote has only one): a word of four letters or more that is not
# in STOPWORDS, or a number such as 0.92 or 35.5%. Matching ignores case, `**`
# and backticks. A row with no quotation is not checked (its Where cell names a
# page that says something in its own words), and nor is a pointer to a file
# that is not markdown.

POINTER = re.compile(r"`([\w./-]+\.md):(\d+(?:[-,]\d+)*)`")
QUOTED = re.compile(r'"([^"]+)"|“([^”]+)”')
TOKEN = re.compile(r"\d+(?:\.\d+)?%?|[a-z][a-z-]{3,}")
STOPWORDS = frozenset(
    "about after again also been being does each every from have into just loke more "
    "must only other over should some such than that their them then there these they "
    "this those under were what when where which while whose will with without would "
    "could your".split()
)


def quote_tokens(claim):
    text = " ".join(a or b for a, b in QUOTED.findall(claim))
    text = text.replace("`", "").replace("*", "").lower()
    return {t for t in TOKEN.findall(text) if t not in STOPWORDS}


def cited_lines(spec):
    """'44' -> [44]; '89-90' -> [89, 90]; '42,157' -> [42, 157]; '177-179,201' too."""
    out = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(part))
    return out


def check_pointers(root, errors, warnings, verbose_notes):
    path = os.path.join(root, CLAIMS)
    if not os.path.exists(path):
        return 0
    cache = {}
    checked = 0
    with open(path, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            cells = split_row(line)
            if not cells or len(cells) < 7 or not ROW_ID.match(cells[0]):
                continue
            tokens = quote_tokens(cells[1])
            if not tokens:
                continue
            need = min(2, len(tokens))
            for m in POINTER.finditer(cells[2]):
                rel, spec = m.group(1), m.group(2)
                target = os.path.join(root, rel)
                if rel not in cache:
                    if not os.path.exists(target):
                        errors.append(f"{CLAIMS}:{lineno}: row {cells[0]} cites {rel}, which does not exist.")
                        cache[rel] = None
                        continue
                    cache[rel] = open(target, encoding="utf-8").read().split("\n")
                page = cache[rel]
                if page is None:
                    continue
                nums = cited_lines(spec)
                if any(n < 1 or n > len(page) for n in nums):
                    errors.append(
                        f"{CLAIMS}:{lineno}: row {cells[0]} cites {rel}:{spec}, past the end "
                        f"of that file ({len(page)} lines)."
                    )
                    continue
                checked += 1
                text = " ".join(page[n - 1] for n in nums).replace("`", "").replace("*", "").lower()
                found = sorted(t for t in tokens if t in text)
                if len(found) >= need:
                    verbose_notes.append(f"{CLAIMS}:{lineno}: {cells[0]} {rel}:{spec} holds {found[:4]}")
                    continue
                errors.append(
                    f"{CLAIMS}:{lineno}: row {cells[0]} cites {rel}:{spec}, but that line holds "
                    f"{'only ' + repr(found) if found else 'none'} of the quoted claim's words "
                    f"{sorted(tokens)[:6]}. The page has moved: point at the line that makes the claim now, "
                    f"or say the page no longer makes it."
                )
    return checked


# ---------------------------------------------------------------------------
# Check 2 — figures must be traceable to metrics-baseline.md
# ---------------------------------------------------------------------------

# Shapes that count as a published figure. Kept narrow on purpose.
FIGURE_PATTERNS = [
    # 60%, 60-80%, 30–60 %, 98.5%
    re.compile(r"\d+(?:\.\d+)?\s*(?:[-–]\s*\d+(?:\.\d+)?)?\s*%"),
    # 20x, 5–30x, 1.5x   (multipliers)
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:[-–]\s*\d+(?:\.\d+)?)?\s*[xX]\b"),
    # < 500ms, under 10 ms, <1 second, < 2 seconds
    re.compile(
        r"(?:[<>]\s*|under\s+|over\s+|within\s+)"
        r"\d+(?:\.\d+)?\s*(?:ms|milliseconds?|s\b|secs?\b|seconds?|min\b|minutes?|hours?)"
    ),
    # 25-55 tok/s, 30 tokens/sec
    re.compile(r"\b\d+(?:\.\d+)?\s*(?:[-–]\s*\d+(?:\.\d+)?)?\s*(?:tok|tokens)\s*/\s*s"),
]

# Anything matching one of these, at the match site, is not a published figure.
# (label, pattern) — label is shown by --verbose.
EXCLUSIONS = [
    ("story id", re.compile(r"\b(?:[A-Z]{1,3}\d+[a-z]?)\.\d+\b")),
    ("port", re.compile(r"\b(?:port|:)\s*1\d{4}\b|\b114\d\d\b|\b5000\b|\b5002\b")),
    ("version string", re.compile(r"\bv?\d+\.\d+\.\d+\b")),
    ("year", re.compile(r"\b(?:19|20)\d{2}\b")),
    ("file size", re.compile(r"\b\d+(?:\.\d+)?\s*(?:[KMGT]i?B|bytes?)\b", re.I)),
    ("http status", re.compile(r"\b(?:200|201|400|404|409|500)\b")),
    ("iso date", re.compile(r"\b\d{4}-\d{2}-\d{2}\b")),
    ("arxiv id", re.compile(r"arXiv:\d+")),
]

# Contexts in which a figure is not a claim about loke's performance.
CONTEXT_EXEMPT = [
    # A line that already defers to the baseline, or says the figure is withdrawn,
    # a target, an estimate, a third-party result, or not measured.
    ("defers to baseline", re.compile(r"metrics-baseline", re.I)),
    ("withdrawn", re.compile(r"\bwithdraw(?:n|ing)?\b", re.I)),
    ("explicit non-measurement", re.compile(
        r"\b(?:not measured|never measured|no(?:t)? benchmark|unmeasured|never\b|"
        r"design target|target, not|targets, not|illustrative|worked example|estimate[ds]?|"
        r"estimated|hypothes(?:is|ised|es)|expected)\b", re.I)),
    # Third-party results are attributed, not published by loke.
    ("third-party attribution", re.compile(
        r"\b(?:published work|prior art|SurrogateShield|InferLink|MaskSQL|Staab|Sweeney|"
        r"de Montjoye|RouteLLM|LLMLingua|Presidio|BIRD|Spider|Anonymeter|third-party)\b")),
    # A demo-dataset descriptor row. These carry a sensitivity label and describe
    # patterns seeded into synthetic data ("3x rollback rate"), not loke's behaviour.
    ("demo dataset row", re.compile(
        r"\|\s*(?:PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED)\s*\|")),
    # Structural counts about the repository or a dataset, not performance.
    ("repo or dataset count", re.compile(
        r"\b(?:test files?|modules?|patterns?|detectors?|datasets?|rows?|columns?|"
        r"servers?|customers?|claims?|entit(?:y|ies)|strategies|layers?|tiers?|"
        r"importers?|files?|lines?|stories)\b", re.I)),
]

# A fenced code block is code or sample output, not a published figure.
FENCE = re.compile(r"^\s*(?:```|~~~)")


def baseline_figures(root):
    """Return the normalised set of figure tokens that appear in metrics-baseline.md.

    Includes withdrawn figures: naming a figure as withdrawn is an entry, and a page
    that cites the withdrawal rather than restating the number is compliant.
    """
    path = os.path.join(root, BASELINE)
    if not os.path.exists(path):
        return None
    text = open(path, encoding="utf-8").read()
    found = set()
    for pat in FIGURE_PATTERNS:
        for m in pat.finditer(text):
            found.add(normalise(m.group(0)))
    return found


def normalise(token):
    """Collapse whitespace and unify dash forms so 30–60% == 30-60 %."""
    t = token.strip().lower().replace("–", "-").replace("—", "-")
    return re.sub(r"\s+", "", t)


def line_is_exempt(line):
    for label, pat in CONTEXT_EXEMPT:
        if pat.search(line):
            return label
    return None


def match_is_excluded(line, start, end):
    """True if the figure match overlaps an excluded token (port, version, …)."""
    for label, pat in EXCLUSIONS:
        for m in pat.finditer(line):
            if m.start() < end and start < m.end():
                return label
    return None


def check_figures(root, errors, warnings, verbose_notes):
    known = baseline_figures(root)
    if known is None:
        errors.append(
            f"{BASELINE}: missing. It is the only source of published figures and must exist."
        )
        return 0

    checked = 0
    for rel in FIGURE_SOURCES:
        path = os.path.join(root, rel)
        if not os.path.exists(path):
            warnings.append(f"{rel}: not found, skipped.")
            continue

        in_fence = False
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            if FENCE.match(line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue

            exempt = line_is_exempt(line)

            for pat in FIGURE_PATTERNS:
                for m in pat.finditer(line):
                    token = m.group(0)
                    excl = match_is_excluded(line, m.start(), m.end())
                    if excl:
                        verbose_notes.append(
                            f"{rel}:{lineno}: skipped {token!r} ({excl})"
                        )
                        continue
                    checked += 1
                    if normalise(token) in known:
                        continue
                    if exempt:
                        verbose_notes.append(
                            f"{rel}:{lineno}: allowed {token!r} ({exempt})"
                        )
                        continue
                    errors.append(
                        f"{rel}:{lineno}: figure {token!r} has no entry in {BASELINE} "
                        f"and the line does not mark it as a target, an estimate, a "
                        f"third-party result or withdrawn.\n"
                        f"    {line.strip()[:120]}\n"
                        f"    Fix: add the measurement to {BASELINE}, cite that file, or "
                        f"state on this line that the figure is not a measurement."
                    )
    return checked


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="CI mode: identical behaviour, stated explicitly.")
    ap.add_argument("--verbose", action="store_true",
                    help="List figures that were skipped or allowed, and why.")
    ap.add_argument("--root", default=None,
                    help="Repository root (default: the parent of this script).")
    args = ap.parse_args(argv)

    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    errors, warnings, notes = [], [], []
    verified = check_evidence(root, errors, warnings, notes)
    pointers = check_pointers(root, errors, warnings, notes)
    figures = check_figures(root, errors, warnings, notes)

    if args.verbose:
        for n in notes:
            print(f"note: {n}")
        print()

    for w in warnings:
        print(f"warning: {w}")

    if errors:
        print(f"check_claims: FAIL — {len(errors)} problem(s).\n")
        for e in errors:
            print(f"  {e}")
        print(
            f"\nChecked {verified} verified claim(s), {pointers} page pointer(s) and {figures} figure(s).\n"
            f"The claims register is {CLAIMS}; figures come only from {BASELINE}."
        )
        return 1

    print(
        f"check_claims: OK — {verified} verified claim(s) all carry an evidence "
        f"pointer; {pointers} page pointer(s) land on the claim they cite; {figures} "
        f"figure(s) all traceable to {BASELINE}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
