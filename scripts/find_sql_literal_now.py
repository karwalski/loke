#!/usr/bin/env python3
"""Find a SQL function name passed as a bound VALUE, where it is stored as text (GA5.1).

Why this exists
---------------
A bound parameter is a value and never an expression. `db.exec(sql; @(key; value; "now()"))`
stores the four characters `now()`; SQLite does not evaluate it. The same mistake was made
independently in FIVE places in this repository before it was gated:

    storage/audit.tk        every audit row carried the identical text "now()"
    storage/settings.tk     every settings row's updated_at was "now()"
    storage/dashboard.tk    a second hand-written copy of the settings upsert
    storage/backup.tk       not even SQL — a struct field assigned four characters, so a
                            backup listing sorted by createdat had every entry equal
    models/queue.tk         startedat / completedat were the literal string "now"

Each was written by someone who knew what `now()` meant in SQL and did not notice which side
of the parameter boundary they were on. It is not a typo class; it is a conceptual slip that
recurs, and the failure is silent — the write succeeds, the column is TEXT, and the value
looks plausible until somebody sorts or subtracts by it.

The two correct forms, both already in the tree:

    "... VALUES (?,?,datetime('now'))"      -- the function in the STATEMENT text
    @(key; value; str.fromi64(t.nowi64()))  -- a real timestamp from toke

What it flags
-------------
A string literal whose entire content is a SQL time function or the bare word `now`, outside
comments. Deliberately narrow: `"datetime('now')"` inside a longer SQL statement is correct
and is not flagged, because the literal is then the statement, not a value.

    python3 scripts/find_sql_literal_now.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# The whole literal is the function name — not a statement that happens to contain it.
BAD = re.compile(
    r'"\s*(now\(\)|now|current_timestamp|datetime\(\s*\'now\'\s*\)|strftime\([^"]*\))\s*"',
    re.I)


def comment_mask(src: str) -> list[bool]:
    """True at every position inside a (* ... *) comment. Comments NEST in toke (T-27).

    This is written here rather than reused from find_err_arm_first.strip_noise, and the first
    version of this script DID reuse it and was therefore unable to fail. strip_noise blanks
    string literals INCLUDING their quotes, so the test `stripped[m.start()] == '"'` was false
    for every hit and all five motivating defects were reported clean. Proving a check can fail
    is not a formality in this repository: it is the fourth time a check here could not.

    String literals must still be skipped while scanning for comment openers, because
    `"SELECT COUNT(*) ..."` contains the two characters `(*` (T-27, one level up).
    """
    mask = [False] * len(src)
    i = 0
    depth = 0
    while i < len(src):
        if depth == 0 and src[i] == '"':
            i += 1
            while i < len(src):
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if src.startswith("(*", i):
            depth += 1
            mask[i] = mask[i + 1] = True
            i += 2
            continue
        if src.startswith("*)", i) and depth > 0:
            depth -= 1
            mask[i] = mask[i + 1] = True
            i += 2
            continue
        if depth > 0:
            mask[i] = True
        i += 1
    return mask


# The second form, and the one that cost the most: a SQL string literal INSIDE the statement
# text. `VALUES (?,?,'now()')` stores five characters — the single quotes make it a string to
# SQLite, so nothing is called. It was invisible to the rule above, which only sees a toke
# literal whose whole content is the function name.
#
# core.governance.monitoring did this, and the damage was downstream: `trend` filtered
# `created_at >= datetime('now','-N days')` against a column of literal `now()`, and a string
# beginning with `n` is never >= one beginning with a digit, so every trend window returned
# nothing for every model.
SQL_QUOTED = re.compile(r"'\s*(now\(\)|current_timestamp)\s*'", re.I)


def scan(path: pathlib.Path) -> list[tuple[int, str]]:
    raw = path.read_text(errors="replace")
    incomment = comment_mask(raw)
    hits = []
    for rx in (BAD, SQL_QUOTED):
        for m in rx.finditer(raw):
            if incomment[m.start()]:
                continue
            line = raw.count("\n", 0, m.start()) + 1
            hits.append((line, m.group(0)))
    return sorted(hits)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    total = 0
    for root in args.roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.tk")):
            if any(x in f.parts for x in ("_archived-tests", "build")):
                continue
            for line, lit in scan(f):
                print(f"  {f.relative_to(REPO)}:{line}: {lit} is a VALUE here, so it is "
                      f"stored as text — a bound parameter is never evaluated as SQL")
                total += 1

    if total == 0:
        print("find_sql_literal_now: OK — no SQL time function is passed as a bound value.")
        return 0
    print(f"\n{total} site(s). Put the function in the STATEMENT text "
          f"(`VALUES (?,?,datetime('now'))`) or bind a real timestamp "
          f"(`str.fromi64(t.nowi64())`). See this script's docstring for the five that "
          f"motivated it.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
