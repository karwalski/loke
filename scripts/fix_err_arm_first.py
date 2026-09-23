#!/usr/bin/env python3
"""Move the `$ok` arm to the front of every `mt` over a result.

See `scripts/find_err_arm_first.py` for why this is a defect and not a style question:
`mt` binds arms by POSITION, not by label, so an `$ok` arm written second never runs on
success. This rewrites the arm order and nothing else — no arm body is touched, so the fix
is reviewable as a pure reordering in `git diff`.

    python3 scripts/fix_err_arm_first.py --dry-run packages
    python3 scripts/fix_err_arm_first.py packages src tests
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_err_arm_first import strip_noise  # noqa: E402  (length-preserving)

REPO = pathlib.Path(__file__).resolve().parent.parent
ARM = re.compile(r"^(\s*)\$([A-Za-z_][A-Za-z0-9_]*)\s*:")


def split_arms(block: str, sblock: str) -> list[str] | None:
    """Split a match block on its top-level `;`. `sblock` is the noise-stripped twin."""
    arms, depth, start = [], 0, 0
    for i, ch in enumerate(sblock):
        if ch in "({[":
            depth += 1
        elif ch in ")}]":
            depth -= 1
        elif ch == ";" and depth == 0:
            arms.append(block[start:i])
            start = i + 1
    arms.append(block[start:])
    return arms


def fix(text: str) -> tuple[str, int]:
    stripped = strip_noise(text)
    edits = []
    for m in re.finditer(r"\bmt\b", stripped):
        brace = stripped.find("{", m.end())
        if brace < 0:
            continue
        depth, j = 0, brace
        while j < len(stripped):
            if stripped[j] == "{":
                depth += 1
            elif stripped[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        if j >= len(stripped):
            continue
        a, b = brace + 1, j
        arms = split_arms(text[a:b], stripped[a:b])
        labels = []
        for arm in arms:
            lm = ARM.match(arm.strip("\n") and arm or arm)
            lm = ARM.match(arm) or ARM.match(arm.lstrip("\n"))
            labels.append(lm.group(2) if lm else None)
        if "ok" not in labels or labels[0] == "ok":
            continue
        if None in labels:
            continue          # an arm this splitter did not understand: leave it alone
        k = labels.index("ok")

        # Reorder the arm CONTENTS, keeping each slot's surrounding whitespace.
        #
        # An arm slice carries both its leading indent and — for the last arm — the newline
        # and indent that sit before the block's closing `}`. Moving the slice wholesale
        # drags that layout with it, which produced arms ending in `;` and a `}` welded to
        # the end of the moved text. Correct semantics, unreadable diff, and a reviewer
        # cannot tell a reordering from a rewrite. So whitespace belongs to the SLOT and
        # only the content moves.
        parts = []
        for arm in arms:
            lm = re.match(r"(\s*)(.*?)(\s*)$", arm, re.S)
            parts.append((lm.group(1), lm.group(2), lm.group(3)))
        order = [k] + [i for i in range(len(arms)) if i != k]
        rebuilt = ";".join(parts[slot][0] + parts[src][1] + parts[slot][2]
                           for slot, src in enumerate(order))
        edits.append((a, b, rebuilt))

    for a, b, rep in reversed(edits):
        text = text[:a] + rep + text[b:]
    return text, len(edits)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages"])
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total = files = 0
    for root in args.roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.tk")):
            if any(x in f.parts for x in ("_archived-tests", "build")):
                continue
            src = f.read_text(errors="replace")
            out, n = fix(src)
            if n:
                total += n
                files += 1
                print(f"  {f.relative_to(REPO)}: moved `$ok` first in {n} match(es)")
                if not args.dry_run:
                    f.write_text(out)
    verb = "would move" if args.dry_run else "moved"
    print(f"{verb} {total} arm(s) in {files} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
