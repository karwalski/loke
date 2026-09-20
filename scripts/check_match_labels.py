#!/usr/bin/env python3
"""Find modules whose emitted IR has duplicate match labels (toke bug T-2).

Why this is checked in the IR and not the source
------------------------------------------------
toke emits one `rm_ok<n>` / `rm_err<n>` label pair per match. When it does not know
the match subject's sum type, arms 2..n all reuse the same `rm_err<n>` label, and
clang rejects the whole module with

    error: invalid LLVM IR input: Terminator found in the middle of a basic block!
    label %rm_err11

The error names an LLVM label. It does not name the module, the function, the source
file or the line, so a red link says nothing about where to look. This scan reads the
emitted IR, where the label is still next to the module it came from.

The trigger, measured (docs/upstream/toke-issues.md T-2): a match of three or more
arms whose subject type toke cannot see — an `i64` parameter carrying a sum, an
untyped local, a struct field, a match nested in another match's arm. Two arms is
always safe, which is why every `$ok`/`$err` match in the codebase is unaffected.

The fix is to make the subject's type known: annotate the parameter or local with the
sum type, or lift the match into a function that takes the sum as a typed parameter.
Where the sum is one of toke's own and is not nameable from loke source (ProcessErr),
declare a loke-side sum with the same variant names and use that as the parameter
type.

Usage
-----
    python3 scripts/check_match_labels.py                 # after a build
    python3 scripts/check_match_labels.py --check         # exit 1 if any are found
"""

from __future__ import annotations

import argparse
import collections
import pathlib
import re
import sys

LABEL = re.compile(r'(?m)^(rm_err\d+|rm_ok\d+):')


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ir-dir", default="packages/browser/build/ooke")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    d = repo / args.ir_dir
    if not d.is_dir():
        print(f"{d} not found — run scripts/build_loke.sh first")
        return 0

    bad = 0
    for f in sorted(d.iterdir()):
        if f.is_dir():
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        counts = collections.Counter(LABEL.findall(text))
        dupes = {k: v for k, v in counts.items() if v > 1}
        if not dupes:
            continue
        bad += 1
        print(f"{f.name}")
        for label, n in sorted(dupes.items()):
            print(f"  {label} defined {n}x")
    if bad:
        print(f"\n{bad} module(s) will fail to link. Give each match subject a known "
              f"sum type; see this script's docstring.")
    else:
        print("no duplicate match labels")
    return 1 if (args.check and bad) else 0


if __name__ == "__main__":
    sys.exit(main())
