#!/usr/bin/env python3
"""check_backlog.py — CI gate for the backlog's schema, its SUMMARY, and its figures.

Story RV1.7b. Python 3, standard library only.

`docs/epics-and-stories.md` is the project's only backlog, and it is the input to
`docs/claims.md`, which is the input to everything this project says publicly. That
makes it a parsed artefact, not a notebook, and until RV1.7a it could not be parsed:
eight epics used a three-column table with no status column at all and carried status
as a trailing `**[Done]**` inside the Summary cell, one row had unescaped `|`
characters that silently added fields, two rows were missing their closing `|`, and
status was written seven different ways for the same state. Two careful parses of the
file disagreed on its own row count — 598/477 against 594/485 — and the reason was
structural, not arithmetic.

The SUMMARY table was worse, because it was hand-maintained. Measured 2026-09-23, its
Total row did not sum its own column (Stories summed to 280 against a stated 268, Done
to 255 against a stated 193), it was wrong per layer in both directions, and it covered
55 of ~96 epics and ~279 of ~598 rows — thirty-odd epics were absent from it entirely.
Every hand-edit produced a new set of numbers that disagreed with the rows. So this
script generates that table and fails when the document's copy has drifted; `--fix`
rewrites it. A generated table cannot omit an epic.

Seven checks:

  1. Schema. Four cells per row and a closing `|`; no unescaped `|`; status drawn from
     the closed vocabulary in the legend; IDs well-formed and unique; size in
     {S,M,L,XL}; every ID's epic prefix has a heading in the document.
  2. The SUMMARY is derived, never hand-maintained. Generated from the rows and diffed
     against the text between the sentinel comments.
  3. Legend closure, both ways. Every status used appears in the legend, and every
     legend status is used by at least one row unless the legend marks it reserved.
  4. One live census per denominator. `N of M modules` and friends, grouped by unit and
     by denominator. This is what let "58 of 199 modules" survive in four places
     against the real 218 of 218, and four different denominators for the same file
     count (562, 532, 629; the true count is 535).
  5. Stale holds. A `Blocked — <ID>` or `⏸ … until <ID>` whose blocker is Done. Caught
     in review as X8.5 held on NC1.9 after NC1.9 landed; this stops the next one.
  6. Cross-reference liveness. Every ID named by a Blocked / Queued behind / Superseded
     by status exists, is not the row itself, and is not part of a cycle.
  7. Figures answerable to the build. Error and module ladders must not fork, and the
     error total in `build/census-baseline*.json` must be accounted for by a story row.
     A ladder that arrives in disconnected pieces warns rather than fails, because a
     reset and a wrong figure look identical to a script, and only a human knows which
     it is. The F10 ladders warned this way until 2026-11-09, when they were settled from
     git history: the 88-to-90 module step was F10.19/F10.20's commit, not F10.24's, and
     F10.7's 308-to-0 is a summary over the whole ladder, not a rung in it.

What this script deliberately does NOT do: judge whether a `**Done**` marker is *true*.
That is RV1's human work — exercising the code and writing a verdict — and a script
claiming to do it would be the fourth thing in this repository that cannot fail, after
the `2>/dev/null || true` build, the `grep … || echo` licence-check job and the
`command -v ooke` gate that passed on a tree where 294 of 532 files did not compile.
This script checks the shape of the document and the arithmetic over it. Nothing here
is evidence that any row is done.

Matching is deliberately conservative, in the same spirit as check_claims.py: a false
positive that blocks the build is worse than a miss, so every exemption is a named
entry in a table below that can be argued with rather than guessed at.

Usage:
    python3 scripts/check_backlog.py             # report, exit non-zero on failure
    python3 scripts/check_backlog.py --check     # same, for CI (explicit)
    python3 scripts/check_backlog.py --verbose   # also list what was skipped and why
    python3 scripts/check_backlog.py --fix       # rewrite the generated SUMMARY
    python3 scripts/check_backlog.py --root DIR  # run against a different tree
"""

import argparse
import collections
import glob
import json
import os
import re
import sys

BACKLOG = "docs/epics-and-stories.md"
BASELINE_GLOB = "build/census-baseline*.json"

SUMMARY_BEGIN = "<!-- SUMMARY:BEGIN -->"
SUMMARY_END = "<!-- SUMMARY:END -->"

HEADER_CELLS = ["Story", "Size", "Status", "Summary"]
SIZES = ("S", "M", "L", "XL")

# A story ID. The document also carries three-part IDs — X4a.5.1, MK4.6.1 — and those
# are not a defect: `## Epic X4a.5` and `## Epic MK4.6` are real headings with their own
# story tables, so the middle group is an epic number, not a story number. Renaming 49
# rows to fit a two-part pattern would be a content change, so the pattern admits them.
ID_RE = re.compile(r"^[A-Z]+[0-9]+[a-z]?(?:\.[0-9]+)?\.[0-9]+[a-z]?$")

# One epic — `## Epic RS: Research Spikes` — carries no number of its own, so it numbers
# its stories directly: RS1..RS4. Accepted only when a heading vouches for the letters.
FLAT_ID_RE = re.compile(r"^([A-Z]{2,})([0-9]+)$")

# A reference to a story or an epic, as a Status cell names one.
REF_RE = re.compile(r"\b[A-Z]{1,3}[0-9]+[a-z]?(?:\.[0-9]+[a-z]?){0,2}\b")

# Split a table row on unescaped pipes only. `\|` is a literal pipe in a cell.
SPLIT = re.compile(r"(?<!\\)\|")
SEP_CELL = re.compile(r"^[-: ]+$")
FENCE = re.compile(r"^\s*(?:```|~~~)")

# ---------------------------------------------------------------------------
# The closed status vocabulary.
#
# Each entry is (head, needs_note). `head` is matched literally at the start of the
# cell; anything after it must be introduced by " — ", except for the two heads that
# read as a sentence and take a bare reference. The whole cell is capped, because an
# uncapped Status cell is how rationale got in there in the first place.
# ---------------------------------------------------------------------------
STATUSES = [
    ("**Done**", False),
    ("**Reopened**", False),
    ("**Partial**", False),
    ("⏸ On hold", True),
    ("Blocked", True),
    ("Queued behind", True),
    ("Superseded by", True),
]
BARE_REF_HEADS = ("Queued behind", "Superseded by")
STATUS_CAP = 120

# Heads whose note is expected to name another story, and which check 6 follows.
REFERRING_HEADS = ("Blocked", "Queued behind", "Superseded by", "⏸ On hold")

# Heads that mean the row is open. Used only for the generated SUMMARY's columns.
DONE_HEADS = ("**Done**",)

# ---------------------------------------------------------------------------
# Check 4 — census claims
# ---------------------------------------------------------------------------

# "218 of 218 modules", "26 of 122 test files", "52 of 179 interfaces".
CENSUS_RE = re.compile(
    r"\b([0-9][0-9,]*)\s*(?:of|/)\s*([0-9][0-9,]*)\s*"
    r"(non-test\s+|non-archived\s+|source\s+|test\s+)?"
    r"(modules?|interfaces?|tests?|test files?|files?|errors?)\b",
    re.I,
)

# A census claim is live unless the text immediately around it says it is not the
# current figure. Every phrase here is a form this document actually uses; none is a
# guess. The window matters more than the list: an earlier version of this check tested
# the whole line, and because nearly every preamble paragraph in this document carries a
# date, it exempted "58 of 199" and "218 of 218" alike and found nothing at all.
SUPERSEDED_MARKS = [
    ("superseded", re.compile(r"\bsupersede[ds]?\b", re.I)),
    ("corrected", re.compile(r"\bre-?corrected\b|\bcorrected\b|\bcorrection\b", re.I)),
    ("withdrawn", re.compile(r"\bwithdraw(?:n|s|ing)?\b", re.I)),
    ("stated false", re.compile(
        r"\bwas false\b|\bwas wrong\b|\bnot true\b|\bthis was wrong\b|\bfalse\b", re.I)),
    ("historical", re.compile(
        r"\bused to carry\b|\bhistorical\b|\bno longer\b|\bnot reinstated\b|"
        r"\bpreviously\b|\bat the time\b|"
        # Past perfect is this document's way of quoting a conclusion it has since
        # overturned: "had concluded a hard ceiling of 209 of 217 modules".
        r"\bhad (?:concluded|reported|assumed|said|claimed)\b", re.I)),
    ("dated", re.compile(r"\b20\d\d-\d\d-\d\d\b")),
]
# How far either side of the figure a superseding mark counts. A mark further away than
# this is about some other sentence.
MARK_WINDOW_BEFORE = 90
MARK_WINDOW_AFTER = 45

# A figure whose scope is qualified is not comparable with the built-set census. These
# are the qualifiers this document actually uses — and only the ones that really do
# change the denominator. `packages/` and `src` were in this list and matched almost
# every F10 cell, which exempted the whole ladder.
SCOPE_QUALIFIERS = re.compile(
    r"\brepo-wide\b|\bmoke\b|\bexcluding\b|\b_archived-tests\b|\bE\d{4}\b|"
    r"\bper-tree\b|\bnon-test\b|\bnon-archived\b|\bin six trees\b",
    re.I,
)


def window(text, start, end, before=MARK_WINDOW_BEFORE, after=MARK_WINDOW_AFTER):
    return text[max(0, start - before):end + after]

# ---------------------------------------------------------------------------
# Check 7 — figure ladders
# ---------------------------------------------------------------------------

# Both orders occur: "284 → 257 errors" and "308 errors → 0".
UNITS = r"errors?|modules?|interfaces?|compiling|files?"
TRANSITION_RES = [
    re.compile(r"\b([0-9][0-9,]*)\s*(?:→|->)\s*([0-9][0-9,]*)\s*(" + UNITS + r")\b", re.I),
    re.compile(r"\b([0-9][0-9,]*)\s+(" + UNITS + r")\s*(?:→|->)\s*([0-9][0-9,]*)\b", re.I),
]
# Units that should fall over a ladder, and the direction each must move.
DECREASING = ("error", "errors")
INCREASING = ("module", "modules", "interface", "interfaces", "compiling")


def norm_unit(u):
    if not u:
        return None
    u = u.strip().lower()
    if u == "compiling":
        return "modules"
    if u.endswith("s"):
        return u
    return u + "s"


# ---------------------------------------------------------------------------

Row = collections.namedtuple(
    "Row", "lineno sid epic size status summary layer heading cells trailing"
)


def split_row(line):
    """Split a markdown table row on unescaped pipes.

    Returns (cells, had_closing_pipe). A row that does not end in `|` still renders
    in GFM, which is why two such rows survived in this document unnoticed.
    """
    s = line.strip()
    parts = SPLIT.split(s)
    if parts and parts[0].strip() == "":
        parts = parts[1:]
    trailing = bool(parts) and parts[-1].strip() == ""
    if trailing:
        parts = parts[:-1]
    return [c.strip() for c in parts], trailing


def epic_of(sid):
    """F10.23 -> F10;  X4a.5.1 -> X4a;  MK4.6.1 -> MK4;  RS1 -> RS."""
    if "." not in sid:
        m = FLAT_ID_RE.match(sid)
        if m:
            return m.group(1)
    return re.match(r"^[A-Z]+[0-9]+[a-z]?", sid).group(0)


def parse(path, errors, notes):
    """Return (rows, layers, headings, lines, legend_heads, raw_pipe_rows)."""
    lines = open(path, encoding="utf-8").read().split("\n")
    rows = []
    headings = {}          # epic id -> heading line number
    layer = None
    heading = None
    in_table = None        # column count of the story table currently open
    in_fence = False
    raw_pipe_rows = []

    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue

        if line.startswith("# "):
            layer = line[2:].strip()
            in_table = None
            continue
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
            m = re.match(r"^(?:Epic\s+)?([A-Z]+[0-9]+[a-z]?(?:\.[0-9]+)?)\b", heading)
            if m:
                headings.setdefault(m.group(1), i)
                # `## Epic MK4.6: …` also vouches for the MK4 prefix.
                headings.setdefault(epic_of(m.group(1) + ".0"), i)
            else:
                # `## Epic RS: Research Spikes` — an epic with no number of its own.
                m = re.match(r"^Epic\s+([A-Z]{2,})\b", heading)
                if m:
                    headings.setdefault(m.group(1), i)
            in_table = None
            continue

        s = line.strip()
        if not s.startswith("|"):
            if s:
                in_table = None
            continue

        cells, trailing = split_row(line)
        if not cells:
            continue
        if cells[0] == "Story":
            if cells != HEADER_CELLS:
                errors.append(
                    f"{BACKLOG}:{i}: story table header is {cells} — it must be exactly "
                    f"{HEADER_CELLS}. A three-column table has nowhere to put a status, "
                    f"which is the defect RV1.7a existed to remove."
                )
            in_table = len(cells)
            continue
        if SEP_CELL.match(cells[0]):
            continue
        if not re.match(r"^\*{0,2}[A-Z]", cells[0]) or in_table is None:
            in_table = None if cells[0] != "Story" else in_table
            continue

        sid = cells[0].strip("*")
        flat = FLAT_ID_RE.match(sid)
        if flat and flat.group(1) in headings:
            pass  # RS1 under `## Epic RS`
        elif not ID_RE.match(sid):
            # Not a story row — some tables inside the document are prose tables whose
            # first cell happens to start with a capital. Only complain when the cell
            # looks like an ID that is nearly right.
            if re.match(r"^[A-Z]+[0-9]", sid):
                errors.append(
                    f"{BACKLOG}:{i}: {sid!r} is not a well-formed story ID. Expected "
                    f"EPIC.N, e.g. F10.23 (a sub-epic may add one group: MK4.6.1)."
                )
            continue

        if SPLIT.split(line.strip()) and len(cells) != 4:
            errors.append(
                f"{BACKLOG}:{i}: row {sid} has {len(cells)} cells, not 4. An unescaped "
                f"`|` inside a cell adds a field silently — write it as `\\|`."
            )
            raw_pipe_rows.append(i)
            continue
        if not trailing:
            errors.append(
                f"{BACKLOG}:{i}: row {sid} has no closing `|`. GFM renders it anyway, "
                f"which is how two such rows survived here unnoticed."
            )

        rows.append(Row(i, sid, epic_of(sid), cells[1], cells[2], cells[3],
                        layer, heading, cells, trailing))

    return rows, headings, lines


def parse_legend(lines):
    """Return {head: reserved_bool} from the status vocabulary table in the legend."""
    legend = {}
    inside = False
    for line in lines:
        if line.startswith("**Status vocabulary"):
            inside = True
            continue
        if inside:
            if line.startswith("#") or line.startswith("`Spec done`"):
                break
            cells, _ = split_row(line)
            if len(cells) != 2 or SEP_CELL.match(cells[0]):
                continue
            head = cells[0].strip()
            if head == "Status":
                continue
            if head == "*(blank)*":
                legend[""] = False
                continue
            head = head.strip("`")
            head = re.sub(r"\s*—.*$", "", head).strip()
            head = re.sub(r"\s*<ID>.*$", "", head).strip()
            legend[head] = "reserved" in cells[1].lower()
    return legend


# ---------------------------------------------------------------------------
# Check 1 — schema
# ---------------------------------------------------------------------------

def status_head(status):
    """Return the vocabulary head a status cell uses, or None."""
    if status.strip() == "":
        return ""
    for head, _ in STATUSES:
        if status.startswith(head):
            return head
    return None


def check_schema(rows, headings, legend, errors, notes):
    seen = {}
    for r in rows:
        if r.sid in seen:
            errors.append(
                f"{BACKLOG}:{r.lineno}: duplicate story ID {r.sid} "
                f"(first seen at line {seen[r.sid]}). Two rows with one ID means every "
                f"count over this document is ambiguous."
            )
        seen[r.sid] = r.lineno

        if r.size not in SIZES:
            errors.append(
                f"{BACKLOG}:{r.lineno}: row {r.sid} has size {r.size!r}; expected one "
                f"of {SIZES}."
            )

        head = status_head(r.status)
        if head is None:
            errors.append(
                f"{BACKLOG}:{r.lineno}: row {r.sid} has status {r.status[:60]!r}, which "
                f"is not in the closed vocabulary. Use one of "
                f"{[h for h, _ in STATUSES]} and put the reasoning in the Summary."
            )
        else:
            if len(r.status) > STATUS_CAP:
                errors.append(
                    f"{BACKLOG}:{r.lineno}: row {r.sid} has a {len(r.status)}-character "
                    f"status cell (cap {STATUS_CAP}). Move the rationale to the Summary "
                    f"after `**Status detail:**` and leave the state behind."
                )
            note = r.status[len(head):].strip()
            if head and note:
                if head in BARE_REF_HEADS:
                    pass  # `Queued behind X7.2` — no dash
                elif not re.match(r"^[—–-]\s+\S", note):
                    errors.append(
                        f"{BACKLOG}:{r.lineno}: row {r.sid} status {r.status[:60]!r} — a "
                        f"note after {head!r} must be introduced by ' — '."
                    )
            if head and not note and head in dict(STATUSES) and dict(STATUSES)[head]:
                errors.append(
                    f"{BACKLOG}:{r.lineno}: row {r.sid} status is a bare {head!r}. That "
                    f"head is meaningless without what it is waiting on."
                )
            if head not in legend:
                errors.append(
                    f"{BACKLOG}:{r.lineno}: row {r.sid} uses status head {head!r}, which "
                    f"is not in the legend's vocabulary table. Add it there or stop "
                    f"using it — the legend is the definition, not a summary of it."
                )

        if r.epic not in headings:
            errors.append(
                f"{BACKLOG}:{r.lineno}: row {r.sid} belongs to epic {r.epic}, which has "
                f"no heading in this document. A story under no epic is invisible to "
                f"every count."
            )

    for r in rows:
        if "|" in r.summary.replace("\\|", ""):
            errors.append(
                f"{BACKLOG}:{r.lineno}: row {r.sid} has an unescaped `|` in its Summary."
            )


# ---------------------------------------------------------------------------
# Check 2 — the generated SUMMARY
# ---------------------------------------------------------------------------

def summarise(rows):
    """Build the SUMMARY block. Every epic appears, so none can be absent."""
    def bucket(rs):
        c = collections.Counter()
        for r in rs:
            h = status_head(r.status)
            c[h if h is not None else "?"] += 1
        return c

    cols = ["**Done**", "**Partial**", "**Reopened**", "Blocked", "Queued behind",
            "Superseded by", "⏸ On hold", ""]
    labels = ["Done", "Partial", "Reopened", "Blocked", "Queued", "Superseded",
              "On hold", "Not started"]

    out = [SUMMARY_BEGIN, "",
           "*Generated by `scripts/check_backlog.py --fix` from the story rows. Do not",
           "hand-edit: the gate fails when this drifts from the rows, and every previous",
           "hand-edit produced a set of numbers that disagreed with them.*",
           ""]

    def table(title, groups, keyname):
        out.append(f"**{title}**")
        out.append("")
        out.append("| " + keyname + " | Epics | Stories | " + " | ".join(labels) + " |")
        out.append("|" + "---|" * (3 + len(labels)))
        tot = collections.Counter()
        tot_epics = set()
        tot_rows = 0
        for key, rs in groups:
            c = bucket(rs)
            epics = {r.epic for r in rs}
            tot.update(c)
            tot_epics |= epics
            tot_rows += len(rs)
            cellvals = [str(c[k]) if c[k] else "—" for k in cols]
            out.append(f"| {key} | {len(epics)} | {len(rs)} | " + " | ".join(cellvals) + " |")
        cellvals = [f"**{tot[k]}**" if tot[k] else "—" for k in cols]
        out.append(f"| **Total** | **{len(tot_epics)}** | **{tot_rows}** | "
                   + " | ".join(cellvals) + " |")
        out.append("")

    by_layer = collections.OrderedDict()
    for r in rows:
        by_layer.setdefault(r.layer or "(no layer heading)", []).append(r)
    table("By layer — the level-1 heading each row sits under", list(by_layer.items()), "Layer")

    by_epic = collections.OrderedDict()
    for r in rows:
        by_epic.setdefault(r.epic, []).append(r)
    table("By epic — every epic in the document, so none can be absent",
          list(by_epic.items()), "Epic")

    out.append(f"Rows parsed: **{len(rows)}**, across **{len(by_epic)}** epics and "
               f"**{len(by_layer)}** level-1 headings.")
    odd = sorted({r.epic for r in rows if (r.layer or "").upper() == "SUMMARY"})
    if odd:
        out.append("")
        out.append(f"Filed under the `# SUMMARY` heading rather than a layer: "
                   f"{', '.join(odd)}. That is where those epics physically sit in the "
                   f"document; the grouping above reports it rather than hiding it.")
    out.append("")
    out.append(SUMMARY_END)
    return out


def check_summary(path, lines, rows, errors, notes, fix):
    try:
        b = lines.index(SUMMARY_BEGIN)
        e = lines.index(SUMMARY_END)
    except ValueError:
        errors.append(
            f"{BACKLOG}: the sentinels {SUMMARY_BEGIN} / {SUMMARY_END} are missing. The "
            f"SUMMARY is generated between them; without them there is nothing to "
            f"regenerate and the table goes back to being hand-maintained."
        )
        return
    want = summarise(rows)
    have = lines[b:e + 1]
    if have == want:
        return
    if fix:
        lines[b:e + 1] = want
        open(path, "w", encoding="utf-8").write("\n".join(lines))
        print(f"check_backlog: rewrote the generated SUMMARY in {BACKLOG}.")
        return
    first = next((n for n, (h, w) in enumerate(zip(have, want)) if h != w),
                 min(len(have), len(want)))
    detail = ""
    if first < len(have) or first < len(want):
        got = have[first] if first < len(have) else "(nothing)"
        exp = want[first] if first < len(want) else "(nothing)"
        detail = (f"\n    first difference at line {b + 1 + first}:"
                  f"\n      document:  {got[:110]}"
                  f"\n      generated: {exp[:110]}")
    errors.append(
        f"{BACKLOG}:{b + 1}: the generated SUMMARY has drifted from the story rows "
        f"({len(have)} lines present, {len(want)} generated). Run "
        f"`python3 scripts/check_backlog.py --fix`. Do not hand-edit it: that is what "
        f"produced a Total row which did not sum its own column.{detail}"
    )


# ---------------------------------------------------------------------------
# Check 3 — legend closure
# ---------------------------------------------------------------------------

def check_legend(rows, legend, errors, notes):
    if not legend:
        errors.append(
            f"{BACKLOG}: no status vocabulary table found in the legend. It is parsed "
            f"from the table under '**Status vocabulary'."
        )
        return
    used = collections.Counter()
    for r in rows:
        h = status_head(r.status)
        if h is not None:
            used[h] += 1
    for head, reserved in sorted(legend.items()):
        if used[head]:
            continue
        if reserved:
            notes.append(
                f"legend: {head!r} is declared but unused, and the legend marks it "
                f"reserved. Drop the '(reserved)' note when a row starts using it."
            )
            continue
        errors.append(
            f"{BACKLOG}: the legend declares status {head!r} and no row uses it. Either "
            f"use it, mark it '(reserved …)' in the legend, or remove it — an unused "
            f"status value is how `Spec done` sat in this legend on zero rows."
        )
    for head in used:
        if head not in legend:
            errors.append(
                f"{BACKLOG}: status {head!r} is used by {used[head]} row(s) and is not "
                f"in the legend."
            )


# ---------------------------------------------------------------------------
# Check 4 — one live census per denominator
# ---------------------------------------------------------------------------

def mark_of(text):
    for label, pat in SUPERSEDED_MARKS:
        if pat.search(text):
            return label
    return None


def check_census(lines, errors, notes, verbose):
    live = collections.defaultdict(list)     # unit -> [(denom, num, lineno)]
    in_fence = False
    for i, line in enumerate(lines, 1):
        if FENCE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for m in CENSUS_RE.finditer(line):
            num, denom = m.group(1).replace(",", ""), m.group(2).replace(",", "")
            unit = norm_unit(m.group(4))
            qual = (m.group(3) or "").strip().lower()
            if qual:
                unit = f"{qual} {unit}"
            near = window(line, m.start(), m.end())
            # A story row is one physical line, and this document's convention is that
            # "every figure changed carries the date". So a dated Status cell dates every
            # figure in its row, however far along the line the figure sits.
            cells, _ = split_row(line) if line.strip().startswith("|") else ([], False)
            if len(cells) == 4 and re.search(r"\b20\d\d-\d\d-\d\d\b", cells[2]):
                near += " " + cells[2]
            mark = mark_of(near)
            if mark:
                notes.append(f"{BACKLOG}:{i}: census {num} of {denom} {unit} — "
                             f"not counted as live ({mark})")
                continue
            if SCOPE_QUALIFIERS.search(near):
                notes.append(f"{BACKLOG}:{i}: census {num} of {denom} {unit} — "
                             f"not counted as live (scope-qualified)")
                continue
            live[unit].append((denom, num, i))

    for unit, claims in sorted(live.items()):
        denoms = {d for d, _, _ in claims}
        if len(denoms) > 1:
            where = ", ".join(f"{n} of {d} at line {ln}" for d, n, ln in claims)
            errors.append(
                f"{BACKLOG}: {len(denoms)} live denominators for '{unit}': "
                f"{sorted(denoms)} — {where}.\n"
                f"    One live census per denominator. A second denominator for the same "
                f"unit means one of them is stale; date it, mark it superseded, or delete "
                f"it. This is how four different file counts (562, 532, 629) coexisted "
                f"with the true 535."
            )
            continue
        for denom in denoms:
            nums = {n for d, n, _ in claims if d == denom}
            if len(nums) > 1:
                where = ", ".join(f"{n} at line {ln}" for d, n, ln in claims if d == denom)
                errors.append(
                    f"{BACKLOG}: {len(nums)} live numerators against {denom} {unit}: "
                    f"{where}. Only one can be current."
                )
    return sum(len(v) for v in live.values())


# ---------------------------------------------------------------------------
# Checks 5 and 6 — holds and cross-references
# ---------------------------------------------------------------------------

def refs_of(row):
    head = status_head(row.status)
    if head not in REFERRING_HEADS:
        return []
    note = row.status[len(head):]
    return [m.group(0) for m in REF_RE.finditer(note)]


def check_refs(rows, headings, errors, notes, verbose):
    by_id = {r.sid: r for r in rows}
    epics = set(headings)
    graph = {}
    checked = 0

    for r in rows:
        head = status_head(r.status)
        rs = refs_of(r)
        if head in REFERRING_HEADS and not rs:
            notes.append(
                f"{BACKLOG}:{r.lineno}: row {r.sid} is {head!r} on a reason rather than "
                f"a story ID ({r.status[:60]!r}). Not cross-checkable; that is allowed "
                f"for a genuinely non-story blocker such as hardware."
            )
        for ref in rs:
            checked += 1
            if ref == r.sid:
                errors.append(
                    f"{BACKLOG}:{r.lineno}: row {r.sid} names itself in its status."
                )
                continue
            if ref not in by_id and ref not in epics:
                errors.append(
                    f"{BACKLOG}:{r.lineno}: row {r.sid} is {head!r} {ref}, which is "
                    f"neither a story row nor an epic heading in this document."
                )
                continue
            # Check 5 — a hold on something already done is stale.
            if head in ("Blocked", "⏸ On hold"):
                target = by_id.get(ref)
                if target is not None and status_head(target.status) in DONE_HEADS:
                    errors.append(
                        f"{BACKLOG}:{r.lineno}: row {r.sid} is {head!r} {ref}, but {ref} "
                        f"is marked {target.status[:40]!r} at line {target.lineno}. "
                        f"Release the hold or correct one of the two rows. X8.5 sat held "
                        f"on NC1.9 for exactly this reason."
                    )
            elif head == "Queued behind":
                target = by_id.get(ref)
                if target is not None and status_head(target.status) in DONE_HEADS:
                    notes.append(
                        f"{BACKLOG}:{r.lineno}: row {r.sid} is queued behind {ref}, which "
                        f"is Done. The queue has moved on; this row is startable."
                    )
            if ref in by_id:
                graph.setdefault(r.sid, set()).add(ref)

    # Cycles.
    state = {}

    def walk(node, stack):
        if state.get(node) == "done":
            return
        if node in stack:
            cyc = " → ".join(stack[stack.index(node):] + [node])
            errors.append(
                f"{BACKLOG}: cross-reference cycle among story statuses: {cyc}. "
                f"Nothing in a cycle can ever start."
            )
            return
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            walk(nxt, stack)
        stack.pop()
        state[node] = "done"

    for node in sorted(graph):
        walk(node, [])
    return checked


# ---------------------------------------------------------------------------
# Check 7 — figures answerable to the build
# ---------------------------------------------------------------------------

def check_ladders(rows, root, errors, warnings, notes, verbose):
    """Errors on contradictions; warnings on discontinuities.

    A row saying `284 → 257 errors` is a step in a ladder, and the ladder for an epic has
    to be readable. Two kinds of problem are distinguishable, and only one of them is a
    script's business:

      * A **fork** — one source value with two different targets, or one target with two
        different sources — is a contradiction whatever the history was. That fails.
      * A **discontinuity** — a chain that ends at 88 while another starts at 90, or
        errors that reach 0 and then reappear at 284 — may be a real reset (a toolchain
        bump re-broke the build) or a wrong figure, and the difference is a question about
        this project's history that no script can answer. That warns, loudly, and names
        the two rows so a human can settle it.

    Document order is deliberately not used. F10.18 sits above F10.19 and its figures run
    after it, which is why an order-based version of this check reported the F10 ladder as
    running backwards when it is only listed out of sequence.
    """
    ladders = collections.defaultdict(list)   # (epic, unit) -> [(a, b, lineno, sid)]
    for r in rows:
        cell = r.status + " " + r.summary
        seen_spans = set()
        for which, pat in enumerate(TRANSITION_RES):
          for m in pat.finditer(cell):
            if which == 0:
                a_s, b_s, unit = m.group(1), m.group(2), norm_unit(m.group(3))
            else:
                a_s, unit, b_s = m.group(1), norm_unit(m.group(2)), m.group(3)
            if unit not in ("errors", "modules", "interfaces"):
                continue
            if any(s <= m.start() < e for s, e in seen_spans):
                continue
            seen_spans.add((m.start(), m.end()))
            near = window(cell, m.start(), m.end(), before=70, after=40)
            if SCOPE_QUALIFIERS.search(near):
                notes.append(
                    f"{BACKLOG}:{r.lineno}: {r.sid} transition "
                    f"{a_s} → {b_s} {unit} — not laddered "
                    f"(scope-qualified, so not the built-set census)"
                )
                continue
            a = int(a_s.replace(",", ""))
            b = int(b_s.replace(",", ""))
            ladders[(r.epic, unit)].append((a, b, r.lineno, r.sid))

    checked = 0
    for (epic, unit), steps in sorted(ladders.items()):
        checked += len(steps)
        if len(steps) < 2:
            continue

        # Forks — a contradiction regardless of order or history.
        for key, idx in (("source", 0), ("target", 1)):
            groups = collections.defaultdict(set)
            for st in steps:
                groups[st[idx]].add((st[0], st[1]))
            for value, pairs in sorted(groups.items()):
                if len(pairs) > 1:
                    where = ", ".join(
                        f"{s[3]} ({s[0]} → {s[1]}) at line {s[2]}"
                        for s in steps if s[idx] == value
                    )
                    errors.append(
                        f"{BACKLOG}: the {epic} {unit} ladder forks at {value} — the same "
                        f"{key} has two different partners: {where}. One of those figures "
                        f"is wrong; the ladder cannot be read as written."
                    )

        # Chains. Link end-to-end wherever a target meets a source.
        by_source = {s[0]: s for s in steps}
        chains = []
        for s in sorted(steps, key=lambda s: -s[0]):
            if any(o[1] == s[0] for o in steps):
                continue   # not the head of a chain
            chain = [s]
            while chain[-1][1] in by_source and by_source[chain[-1][1]] not in chain:
                chain.append(by_source[chain[-1][1]])
            chains.append(chain)
        if len(chains) > 1:
            ends = " and ".join(
                f"{c[0][3]}..{c[-1][3]} ({c[0][0]} → {c[-1][1]})" for c in chains
            )
            rowlist = ", ".join(sorted({f"{s[3]}:{s[2]}" for c in chains for s in c}))
            warnings.append(
                f"{BACKLOG}: the {epic} {unit} ladder is in {len(chains)} disconnected "
                f"pieces — {ends}. Either a figure is wrong or something reset the count; "
                f"whichever it is, the document does not say. Rows: {rowlist}.\n"
                f"    A script cannot tell a real reset from a wrong number, so this warns "
                f"rather than failing. Settle it by hand and say what moved the figure."
            )

    # The recorded census baseline, if one has been taken.
    for bl in sorted(glob.glob(os.path.join(root, BASELINE_GLOB))):
        try:
            data = json.load(open(bl, encoding="utf-8"))
        except (OSError, ValueError) as exc:
            errors.append(f"{bl}: unreadable ({exc}). A census baseline that cannot be "
                          f"parsed cannot answer for any figure.")
            continue
        total = data.get("total")
        rel = os.path.relpath(bl, root)
        if total is None:
            notes.append(f"{rel}: no 'total' key; nothing to compare figures against.")
            continue
        if not total:
            # A clean build has no error figure for the backlog to answer for. Say so
            # rather than letting `"0" in text` pass by accident, which it always would.
            notes.append(
                f"{rel}: records a clean build (total 0), so there is no error figure to "
                f"reconcile against the rows."
            )
            checked += 1
            continue
        body = "\n".join(r.status + " " + r.summary for r in rows)
        if not re.search(rf"(?<![\d,]){total}(?![\d,])", body):
            errors.append(
                f"{rel}: records {total} errors and no story row mentions that figure. "
                f"The baseline is the build's own account of itself; a backlog that does "
                f"not reference it is not answerable to the build."
            )
        else:
            notes.append(f"{rel}: baseline total {total} is referenced by a story row.")
        checked += 1
    return checked


# ---------------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true",
                    help="CI mode: identical behaviour, stated explicitly.")
    ap.add_argument("--verbose", action="store_true",
                    help="List what was skipped or allowed, and why.")
    ap.add_argument("--fix", action="store_true",
                    help="Rewrite the generated SUMMARY between its sentinels.")
    ap.add_argument("--root", default=None,
                    help="Repository root (default: the parent of this script).")
    args = ap.parse_args(argv)

    root = args.root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(root, BACKLOG)

    errors, warnings, notes = [], [], []
    if not os.path.exists(path):
        print(f"check_backlog: FAIL — {BACKLOG} is missing. It is the project's only "
              f"backlog and the input to docs/claims.md.")
        return 1

    rows, headings, lines = parse(path, errors, notes)
    if not rows:
        print(f"check_backlog: FAIL — no story rows parsed from {BACKLOG}. Expected "
              f"tables headed {HEADER_CELLS}.")
        return 1

    legend = parse_legend(lines)
    check_schema(rows, headings, legend, errors, notes)
    check_summary(path, lines, rows, errors, notes, args.fix)
    check_legend(rows, legend, errors, notes)
    census = check_census(lines, errors, notes, args.verbose)
    refs = check_refs(rows, headings, errors, notes, args.verbose)
    ladders = check_ladders(rows, root, errors, warnings, notes, args.verbose)

    if args.verbose:
        for n in notes:
            print(f"note: {n}")
        print()

    for w in warnings:
        print(f"warning: {w}")
    if warnings:
        print()

    if errors:
        print(f"check_backlog: FAIL — {len(errors)} problem(s).\n")
        for e in errors:
            print(f"  {e}")
        print(f"\nParsed {len(rows)} story rows over {len({r.epic for r in rows})} epics; "
              f"{census} live census claim(s), {refs} cross-reference(s), "
              f"{ladders} ladder step(s).\n"
              f"This script checks the document's shape and the arithmetic over it. It "
              f"does not and cannot check whether a Done marker is true — that is RV1.")
        return 1

    print(f"check_backlog: OK — {len(rows)} story rows over "
          f"{len({r.epic for r in rows})} epics all carry a 4-cell schema and a status "
          f"from the legend's closed vocabulary; the generated SUMMARY matches the rows; "
          f"{census} live census claim(s), {refs} cross-reference(s) and {ladders} ladder "
          f"step(s) are consistent.\n"
          f"Nothing here is evidence that any row is done; that is RV1's work.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
