#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""check_figure_evidence.py — every figure in docs/metrics-baseline.md cites a recorded row.

Story VM1.3a. Python 3, standard library plus benchmarks/lib.

`result.validate` refuses a single run of anything that varies, but a figure reaches
docs/metrics-baseline.md by hand. This check closes that gap. Every section of the page (each
`##` or `###` heading and the text under it) that prints a figure must carry one marker:

    **Evidence: verified.** <optional note>
    **Evidence: legacy, unverified.** <why it cannot be verified>
    **Evidence: withdrawn.** <reason>                  (outside "## Measured" only)
    **Evidence: not a measurement.** <reason>          (outside "## Measured" only)

The marker opens a paragraph, and the reason is the rest of that paragraph. It is printed, not
hidden in a comment, so a reader sees the status the check sees.

In a **verified** section, every figure — each numeric table cell after the first column, and
each percentage, multiplier, time budget or rate in the prose — must be followed by a citation

    1.80x <sub>[ev:98f805d6d5a6 n=2]</sub>         the row's value
    1.77–1.88 <sub>[ev:… /ci n=5]</sub>            the row's interval, both bounds
    26% <sub>[ev:… /saving n=2]</sub>              a ratio r shown as a saving, (1 − 1/r)

and the citation must resolve to exactly one row of the committed ledger
(benchmarks/evidence/ledger.jsonl), that row must pass `result.validate` today, the printed
number must equal the row's at the precision printed, `n=` must equal the row's N, the row's
toke and loke commits must be named in the section, and the row must have been recorded on
the date in the section's heading. A row recorded over repeated runs must also be cited with
`/ci` in the same section, so its BCa interval is printed with it.

A **legacy, unverified** section is one published before this check existed whose rows were
never recorded, or whose recorded rows do not match what the page prints. It must say why, and
it is allowed only for a heading dated on or before LEGACY_CUTOFF, so a new measurement can
never be published under it. Every citation anywhere on the page is resolved, whatever its
section's marker.

The ledger is checked too: every row validates, no digest repeats, and the ledger at HEAD is a
prefix of the working copy (append-only).

Usage:
    python3 scripts/check_figure_evidence.py [--root DIR] [--verbose]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from benchmarks.lib import evidence, result  # noqa: E402

BASELINE = "docs/metrics-baseline.md"
LEGACY_CUTOFF = "2026-09-28"
MEASURED = "## Measured"

STATUSES = ("verified", "legacy, unverified", "withdrawn", "not a measurement")
MARKER = re.compile(r"^\*\*Evidence:\s*([^*]+?)\.?\*\*\s*(.*)$")
CITE = re.compile(r"<sub>\[ev:([0-9a-f]{12})(?:\s*/(ci|saving))?\s+n=(\d+)\]</sub>")
# What may sit between a figure and its citation: closing emphasis and spaces.
CITE_AFTER = re.compile(r"^[*_]*\s*" + CITE.pattern)

HEADING = re.compile(r"^(#{2,3})\s+(.*)$")
DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
FENCE = re.compile(r"^\s*(?:```|~~~)")

NUM = r"\d+(?:\.\d+)?"
# A numeric table cell: a number or a range, with an optional unit.
CELL_FIGURE = re.compile(rf"(?<![\w.]){NUM}(?:\s*[–-]\s*{NUM})?(?:\s*(?:%|x|MB/s|ms|MB|s)\b|%)?")
# A figure in prose. Kept to the shapes check_claims.py treats as published figures, plus rates.
PROSE_FIGURES = [
    re.compile(rf"{NUM}\s*(?:[–-]\s*{NUM})?\s*%"),
    re.compile(rf"\b{NUM}\s*(?:[–-]\s*{NUM})?\s*[xX]\b"),
    re.compile(rf"(?:[<>]\s*|under\s+|over\s+|within\s+){NUM}\s*(?:ms|s\b|seconds?)"),
    re.compile(rf"\b{NUM}\s*(?:MB/s|tok/s|tokens/s)"),
]
# Not figures, wherever they appear: story ids, versions, dates, commits.
NOT_FIGURE = [
    re.compile(r"\b[A-Z]{1,3}\d+[a-z]?\.\d+[a-z]?\b"),
    re.compile(r"\bv?\d+\.\d+\.\d+\b"),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"`[^`]*`"),
    CITE,
]


class Section:
    def __init__(self, level, title, start):
        self.level, self.title, self.start = level, title, start
        self.lines: list[tuple[int, str]] = []
        self.under_measured = False

    @property
    def text(self):
        return "\n".join(l for _, l in self.lines)

    @property
    def date(self):
        m = DATE.search(self.title)
        return m.group(1) if m else None


def split_sections(text):
    sections = [Section(1, "(preamble)", 1)]
    in_measured = False
    for i, line in enumerate(text.splitlines(), 1):
        m = HEADING.match(line)
        if m:
            level = len(m.group(1))
            if level == 2:
                in_measured = line.strip() == MEASURED
            s = Section(level, m.group(2).strip(), i)
            s.under_measured = in_measured and level == 3
            sections.append(s)
            continue
        sections[-1].lines.append((i, line))
    return sections


def markers_in(section):
    """(status, reason) for each evidence marker paragraph in the section."""
    out = []
    lines = section.lines
    for i, (_, line) in enumerate(lines):
        m = MARKER.match(line.strip())
        if not m:
            continue
        reason = [m.group(2)]
        for _, nxt in lines[i + 1:]:
            if not nxt.strip():
                break
            reason.append(nxt.strip())
        out.append((m.group(1).strip().lower(), " ".join(reason).strip()))
    return out


def marker_lines(section):
    """Line numbers of the marker paragraphs: their text is a reason, not a figure."""
    out, inside = set(), False
    for lineno, line in section.lines:
        if MARKER.match(line.strip()):
            inside = True
        elif not line.strip():
            inside = False
        if inside:
            out.add(lineno)
    return out


def _masked(line):
    """Spans in `line` that are not figures (ids, versions, dates, code, citations)."""
    spans = []
    for pat in NOT_FIGURE:
        spans += [(m.start(), m.end()) for m in pat.finditer(line)]
    return spans


def _overlaps(spans, a, b):
    return any(s < b and a < e for s, e in spans)


def figures_in(section):
    """(lineno, line, start, end, token) for every figure the section prints."""
    out = []
    in_fence = False
    skip = marker_lines(section)
    for lineno, line in section.lines:
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence or lineno in skip:
            continue
        masked = _masked(line)
        stripped = line.strip()
        if stripped.startswith("|"):
            if re.fullmatch(r"\|[\s:|-]+\|?", stripped):
                continue
            # Cell boundaries, from the pipes. The first cell is the row's label.
            pipes = [m.start() for m in re.finditer(r"\|", line)]
            if len(pipes) < 3:
                continue
            for a, b in zip(pipes[1:-1], pipes[2:]):
                for m in CELL_FIGURE.finditer(line, a + 1, b):
                    if not _overlaps(masked, m.start(), m.end()):
                        out.append((lineno, line, m.start(), m.end(), m.group(0)))
            continue
        seen = []
        for pat in PROSE_FIGURES:
            for m in pat.finditer(line):
                if _overlaps(masked, m.start(), m.end()) or _overlaps(seen, m.start(), m.end()):
                    continue
                seen.append((m.start(), m.end()))
                out.append((lineno, line, m.start(), m.end(), m.group(0)))
    return out


def _is_header_row(section, lineno):
    """A table's first row is its header: the line after it is the |---| separator."""
    nums = [n for n, _ in section.lines]
    idx = nums.index(lineno)
    if idx + 1 < len(section.lines):
        nxt = section.lines[idx + 1][1].strip()
        return bool(re.fullmatch(r"\|[\s:|-]+\|?", nxt))
    return False


def _decimals(s):
    return len(s.split(".")[1]) if "." in s else 0


def _matches(shown, true):
    """`shown` (text) is `true` rounded to the precision printed."""
    return abs(float(shown) - true) <= 0.5 * 10 ** -_decimals(shown) + 1e-9


def check_citation(token, kind, row):
    """Problems with printing `token` as this row's `kind`, or []."""
    nums = re.findall(NUM, token)
    um = re.search(r"(%|[xX]|MB/s|ms|MB|s)\s*$", token)
    unit = um.group(1) if um else ""
    v = row["value"]
    if kind == "ci":
        if row.get("ci_low") is None:
            return ["cited as an interval, but the row has none"]
        if len(nums) != 2:
            return [f"an interval citation needs a range 'low–high', found {token!r}"]
        out = []
        if not _matches(nums[0], row["ci_low"]):
            out.append(f"interval low {nums[0]} ≠ recorded {row['ci_low']}")
        if not _matches(nums[1], row["ci_high"]):
            out.append(f"interval high {nums[1]} ≠ recorded {row['ci_high']}")
        return out
    if len(nums) != 1:
        return [f"a value citation needs one number, found {token!r}"]
    if kind == "saving":
        if row["units"] != "ratio" or v <= 0:
            return ["a saving is computed from a ratio, and this row is not one"]
        true = (1 - 1 / v) * 100
    elif unit == "%":
        true = v * 100 if row["units"] == "ratio" else v
    else:
        true = v
    if unit.lower() == "x" and row["units"] != "ratio":
        return [f"printed as a multiplier, but the row's units are {row['units']!r}"]
    if not _matches(nums[0], true):
        return [f"printed {nums[0]}, but the row records {true:g}"]
    return []


def git_head_ledger(root):
    try:
        out = subprocess.run(
            ["git", "-C", root, "show", f"HEAD:{evidence.LEDGER_REL}"],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout if out.returncode == 0 else None


def check(doc_text, ledger_text, head_ledger_text=None, today_cutoff=LEGACY_CUTOFF):
    """Return (errors, summary). Pure: the tests drive it with altered text."""
    errors: list[str] = []
    summary = {s: 0 for s in STATUSES}
    summary["cited"] = 0
    summary["legacy_figures"] = 0

    # The ledger.
    rows = {}
    try:
        parsed = evidence.parse_ledger(ledger_text)
    except ValueError as e:
        return [f"{evidence.LEDGER_REL}: not JSON Lines ({e})"], summary
    for i, row in enumerate(parsed, 1):
        d = evidence.digest(row)
        if d in rows:
            errors.append(f"{evidence.LEDGER_REL}:{i}: duplicate row ev:{d}")
        rows[d] = row
        try:
            evidence.validate_row(row)
        except result.ResultRejected as e:
            errors.append(f"{evidence.LEDGER_REL}:{i}: ev:{d} no longer validates: {e}")
    if head_ledger_text is not None:
        if not ledger_text.startswith(head_ledger_text):
            errors.append(
                f"{evidence.LEDGER_REL}: the ledger at HEAD is not a prefix of the working copy. "
                "It is append-only: a recorded row is never edited or removed, because published "
                "figures cite it by digest.")

    for sec in split_sections(doc_text):
        where = f"{BASELINE}:{sec.start} ({sec.title[:60]})"
        markers = markers_in(sec)
        figs = figures_in(sec)
        figs = [f for f in figs if not (f[1].strip().startswith("|") and _is_header_row(sec, f[0]))]

        # Resolve every citation on the page, whatever the section's marker.
        cited_ci = set()
        for lineno, line in sec.lines:
            for m in CITE.finditer(line):
                d, kind, n = m.group(1), m.group(2), int(m.group(3))
                row = rows.get(d)
                if row is None:
                    errors.append(f"{BASELINE}:{lineno}: ev:{d} is not in {evidence.LEDGER_REL}")
                    continue
                if n != row["n"]:
                    errors.append(f"{BASELINE}:{lineno}: ev:{d} printed n={n}, the row's N is {row['n']}")
                if kind == "ci":
                    cited_ci.add(d)

        if not figs and not markers:
            continue
        if len(markers) != 1:
            errors.append(
                f"{where}: prints {len(figs)} figure(s) and carries {len(markers)} evidence "
                f"marker(s); it needs one paragraph opening **Evidence: <status>.**, the "
                f"status one of: {'; '.join(STATUSES)}.")
            continue
        status, reason = markers[0]
        if status not in STATUSES:
            errors.append(f"{where}: unknown evidence status {status!r}")
            continue
        summary[status] += 1

        if status != "verified":
            if len(reason) < 20:
                errors.append(f"{where}: '{status}' must say why (at least a sentence).")
            if sec.under_measured and status != "legacy, unverified":
                errors.append(
                    f"{where}: a section under '{MEASURED}' is either verified or, if it predates "
                    f"VM1.3a, legacy, unverified; '{status}' is not allowed there.")
            if status == "legacy, unverified":
                if sec.date is None or sec.date > today_cutoff:
                    errors.append(
                        f"{where}: 'legacy, unverified' is only for figures published on or before "
                        f"{today_cutoff}. A new figure cites its recorded row.")
                summary["legacy_figures"] += len(figs)
            continue

        cited_here = set()
        for lineno, line, a, b, token in figs:
            m = CITE_AFTER.match(line[b:])
            if not m:
                errors.append(
                    f"{BASELINE}:{lineno}: figure {token!r} in a verified section cites no "
                    f"recorded row. Follow it with <sub>[ev:<digest> n=<N>]</sub> "
                    f"(python3 -m benchmarks.lib.evidence list).")
                continue
            d, kind = m.group(1), m.group(2)
            row = rows.get(d)
            if row is None:
                continue  # already reported above
            summary["cited"] += 1
            cited_here.add(d)
            for p in check_citation(token.strip(), kind, row):
                errors.append(f"{BASELINE}:{lineno}: {token!r} cites ev:{d}: {p}")

        for d in sorted(cited_here):
            row = rows[d]
            for key in ("toke_commit", "loke_commit"):
                val = row.get(key)
                if not val:
                    errors.append(f"{where}: ev:{d} records no {key}, so its provenance is unknown")
                elif val not in sec.text:
                    errors.append(f"{where}: ev:{d} was measured at {key} {val}, which the section does not name")
            if sec.date and not str(row.get("recorded_at", "")).startswith(sec.date):
                errors.append(
                    f"{where}: ev:{d} was recorded {str(row.get('recorded_at'))[:10]}, "
                    f"not on the heading's date {sec.date}")
            if (row.get("runs") or 0) >= 2 and d not in cited_ci:
                errors.append(
                    f"{where}: ev:{d} is a repeated measurement ({row['runs']} runs); print its "
                    f"BCa interval with a /ci citation in the same section")

    if summary["verified"] == 0:
        errors.append(f"{BASELINE}: no section is verified, so nothing on the page is tied to a row")
    return errors, summary


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=ROOT)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)

    doc = open(os.path.join(args.root, BASELINE), encoding="utf-8").read()
    lpath = os.path.join(args.root, evidence.LEDGER_REL)
    ledger = open(lpath, encoding="utf-8").read() if os.path.exists(lpath) else ""
    errors, s = check(doc, ledger, git_head_ledger(args.root))
    if errors:
        print(f"check_figure_evidence: FAIL — {len(errors)} problem(s).")
        for e in errors:
            print(f"  {e}")
        return 1
    print(f"check_figure_evidence: OK — {s['cited']} figure(s) in {s['verified']} verified "
          f"section(s) resolve to recorded rows; {s['legacy_figures']} figure(s) in "
          f"{s['legacy, unverified']} section(s) are marked legacy, unverified; "
          f"{s['withdrawn']} withdrawn and {s['not a measurement']} not-a-measurement section(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
