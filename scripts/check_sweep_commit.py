#!/usr/bin/env python3
"""Refuse a commit that deletes a lot of a file without saying so (story X4.6).

Why this exists
---------------
On 2026-09-22, commit `09b0a67` — *"fix(F10.18): ooke.template.renderfile ->
tplrenderfile"*, a mechanical 24-site sweep — cut
`packages/browser/pages/api/pipeline.tk` from **240 lines to 79**, net -161. It kept
the imports and deleted every call: response restoration, governance policy
evaluation and audit logging all left the request path. Its commit message does not
mention the file, and it was the **only** one of that commit's 24 files to shrink by
more than thirty lines.

Three stories (GA1.2, GA1.4, GA1.8) were then recorded as "never implemented" for a
day, when in fact they had been implemented, committed, and silently removed. They
were recovered from `2b8942e` under GA1.10.

The part that makes this worth a gate rather than a lesson: **the hazard was already
written down.** `scripts/verify_held_changes.py` names that exact file and says *"Its
working-tree copy drops all nine core imports … The committed version is the good
one. It must never be committed from the working tree."* It was committed anyway,
because that script guards the WORKING TREE and only reports — its own docstring says
"reported rather than enforced". Once a change is committed it has nothing to compare
against, and nothing at all checked that a commit *described* as a mechanical sweep
actually was one.

So this runs over commits, not over the working tree, and it fails.

What it checks, and what it deliberately does not
-------------------------------------------------
A large deletion is not a defect. Deleting a dead module, replacing a file wholesale,
or splitting one file into three are all normal. What cost us was a large deletion
**nobody mentioned** — so the rule is not "do not delete" but "say what you deleted".

For each commit in the range, any file whose net line delta is at or beyond
`--threshold` deletions must have its name (or its basename) appear somewhere in the
commit message. That is a low bar on purpose: it is satisfied by one honest sentence,
and it cannot be satisfied by accident.

It does **not** try to judge whether a deletion was correct. It cannot, and a check
that claimed to would be the fourth thing in this repository that cannot fail.

Usage
-----
    python3 scripts/check_sweep_commit.py --range origin/main..HEAD
    python3 scripts/check_sweep_commit.py --staged
    python3 scripts/check_sweep_commit.py --range HEAD~1..HEAD --threshold 50
"""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# Files whose shrinkage must be named in the message however small it is, because
# losing part of them is not a style question. Keep this list short and specific:
# a long list becomes noise and stops being read.
PROTECTED = {
    # The only path in browser mode that reaches an external provider. Losing a call
    # here is a disclosure change, and it has happened once.
    "packages/browser/pages/api/pipeline.tk",
    # The privacy pipeline and the placeholder map it depends on.
    "packages/core/src/privacy/pipeline.tk",
    "packages/core/src/privacy/placeholder.tk",
    # The tamper-evident trail and its verifier.
    "packages/core/src/storage/audit.tk",
}

PROTECTED_THRESHOLD = 5

# Commits before this one are not checked, and the reason is not laziness.
#
# Nine unexplained deletions exist in history before this point — in d14e0bd, 4894533
# and 4d6e0ec — all of them legitimate work whose messages simply did not enumerate
# files. They cannot be amended: rewriting commits that may already have been fetched
# is a worse problem than the one this script solves, and a check that demands the
# impossible gets disabled.
#
# So the rule applies from here forward, and the nine are audited separately under
# X4.7 rather than grandfathered silently. Do NOT move this marker forward to make a
# failure go away: that is the one use of this constant that defeats its purpose.
CUTOVER = "531708a"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(REPO), *args],
        capture_output=True, text=True, check=False,
    ).stdout


def commits_in(rng: str) -> list[str]:
    out = git("rev-list", "--no-merges", rng).split()
    return out


def numstat(commit: str) -> list[tuple[int, int, str]]:
    """(added, removed, path) per file, skipping binary entries."""
    rows = []
    for line in git("show", "--numstat", "--format=", commit).splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, r, path = parts
        if not a.isdigit() or not r.isdigit():
            continue  # binary
        rows.append((int(a), int(r), path))
    return rows


def staged() -> list[tuple[int, int, str]]:
    rows = []
    for line in git("diff", "--cached", "--numstat").splitlines():
        parts = line.split("\t")
        if len(parts) != 3:
            continue
        a, r, path = parts
        if not a.isdigit() or not r.isdigit():
            continue
        rows.append((int(a), int(r), path))
    return rows


def mentions(message: str, path: str) -> bool:
    """Does the message name this file? Path or basename, either is enough."""
    base = pathlib.PurePosixPath(path).name
    if path in message:
        return True
    # A basename alone is acceptable — messages wrap, and full paths rarely survive it.
    return bool(re.search(rf"(?<![\w/]){re.escape(base)}(?![\w])", message))


def threshold_for(path: str, default: int) -> int:
    return PROTECTED_THRESHOLD if path in PROTECTED else default


def check(rows: list[tuple[int, int, str]], message: str, label: str,
          default_threshold: int, verbose: bool) -> list[str]:
    problems = []
    for added, removed, path in rows:
        net = added - removed
        limit = threshold_for(path, default_threshold)
        if net > -limit:
            continue
        if mentions(message, path):
            if verbose:
                print(f"  ok   {label}: {path} net {net:+d}, named in the message")
            continue
        extra = ""
        if path in PROTECTED:
            extra = (f"\n      This file is PROTECTED: any net loss of {PROTECTED_THRESHOLD}"
                     f" lines or more must be named. See PROTECTED in this script for why.")
        problems.append(
            f"{label}: {path} loses {-net} lines net (+{added} -{removed}) and the commit "
            f"message never mentions it.{extra}\n"
            f"      If the deletion is intended, say so in the message — one sentence is "
            f"enough. If it is not, this is the check working."
        )
    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--range", help="commit range, e.g. origin/main..HEAD")
    g.add_argument("--staged", action="store_true", help="check the staged diff")
    ap.add_argument("--threshold", type=int, default=30,
                    help="net deletions that require a mention (default 30)")
    ap.add_argument("--all-history", action="store_true",
                    help="ignore CUTOVER and check every commit in the range. This is how "
                         "the script demonstrates its own evidence: "
                         "--range 09b0a67~1..09b0a67 --all-history reproduces the deletion "
                         "that motivated it. Not for the gate — pre-cutover commits cannot "
                         "be amended.")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    problems: list[str] = []

    if args.staged:
        message = ""
        msg_file = REPO / ".git" / "COMMIT_EDITMSG"
        if msg_file.exists():
            message = msg_file.read_text(errors="replace")
        problems += check(staged(), message, "staged", args.threshold, args.verbose)
    else:
        cs = commits_in(args.range)
        if not cs:
            print(f"check_sweep_commit: no commits in {args.range}; nothing to check.")
            return 0
        # Drop anything at or before the cutover. `merge-base --is-ancestor X c` is true
        # when c is a descendant of X, i.e. when c is in scope.
        in_scope = []
        for c in cs:
            if args.all_history:
                in_scope.append(c)
                continue
            r = subprocess.run(
                ["git", "-C", str(REPO), "merge-base", "--is-ancestor", CUTOVER, c],
                capture_output=True, check=False)
            if r.returncode == 0 and c != git("rev-parse", CUTOVER).strip():
                in_scope.append(c)
        skipped = len(cs) - len(in_scope)
        if skipped and args.verbose:
            print(f"  {skipped} commit(s) at or before the {CUTOVER} cutover, not checked "
                  f"(see CUTOVER in this script, and story X4.7)")
        cs = in_scope
        for c in cs:
            message = git("show", "-s", "--format=%B", c)
            short = git("show", "-s", "--format=%h %s", c).strip()
            problems += check(numstat(c), message, short, args.threshold, args.verbose)

    if problems:
        print(f"check_sweep_commit: FAIL — {len(problems)} unexplained deletion(s).\n",
              file=sys.stderr)
        for p in problems:
            print("  " + p + "\n", file=sys.stderr)
        print("A large deletion is not a defect; an unmentioned one is a defect waiting to "
              "be found months later. 09b0a67 cost this project three stories that way.",
              file=sys.stderr)
        return 1

    scope = "the staged diff" if args.staged else args.range
    print(f"check_sweep_commit: OK — every net deletion beyond {args.threshold} lines in "
          f"{scope} is named in its commit message.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
