#!/usr/bin/env python3
"""Find an open-paren-star sequence INSIDE a comment — it opens a nested one (T-27).

Why this exists
---------------
Comments nest in toke. An open-paren immediately followed by a star opens another level, and a
single close only closes one — so one stray sequence inside a comment swallows the rest of the
file. The module still TYPE-CHECKS, because the swallowed text simply is not there; what you lose
is every declaration after the comment, and the failure surfaces somewhere else entirely as
`module X has no exported member Y`.

This check exists because the hazard was documented as T-27 for weeks and nothing detected it, and
on 2026-09-24 it cost two build cycles in ten minutes:

  1. A comment added to `core/storage/db.tk` contained a SQL aggregate written with a star.
     `db.tk` type-checked clean, its emitted interface silently lost every export after that
     comment, and **fourteen call sites across six modules** failed with
     `core.storage.db has no exported member 'tableexists'` — none of them anywhere near the
     cause.
  2. The paragraph added to explain (1) contained the sequence twice, in prose, while describing
     it. Same outcome.

`packages/core/src/privacy/placeholder_store.tk:68` had already adopted the workaround —
writing the aggregate without its star — which is how the convention was found.

What it flags, and what it does not
-----------------------------------
**An UNCLOSED comment**, reported as the offset of the outermost open that is never closed.

Balanced nesting is legal and harmless, and flagging it was this check's first mistake: three
comments in `agents/registry.tk` and `governance/trace.tk` quote a fragment of defective code that
itself contains a comment, e.g.

    trace.piidetected==entitiesfound;      ( * a COMPARISON, evaluated and discarded * )

Each inner comment is properly closed, so the depth returns to 1 and the outer close ends the
comment as intended. The build has always been fine with those. So depth alone is not the signal —
the signal is a file that ENDS at depth greater than zero, which is precisely the case where
declarations have been swallowed.

That also makes the check exact rather than heuristic: there is no allowlist and no judgement,
because a source file whose comment never closes is wrong in every circumstance.

    python3 scripts/find_nested_comment_open.py --check packages src
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
OPEN = "(" + "*"
CLOSE = "*" + ")"


def scan(src: str) -> tuple[int, int] | None:
    """(offset, depth) of the outermost comment left unclosed at EOF, or None.

    Strings are skipped first: a SQL literal containing an aggregate written with a star is fine,
    because the hazard exists only inside a comment.
    """
    i = 0
    depth = 0
    first_open = -1
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
        if src.startswith(OPEN, i):
            if depth == 0:
                first_open = i
            depth += 1
            i += 2
            continue
        if src.startswith(CLOSE, i) and depth > 0:
            depth -= 1
            i += 2
            continue
        i += 1
    return (first_open, depth) if depth > 0 else None


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
            src = f.read_text(errors="replace")
            found = scan(src)
            if not found:
                continue
            off, depth = found
            line = src.count("\n", 0, off) + 1
            ctx = src[off:off + 64].replace("\n", " ")
            print(f"  {f.relative_to(REPO)}:{line}: comment never closes "
                  f"(depth {depth} at end of file) — every declaration after it is swallowed")
            print(f"      …{ctx}…")
            total += 1

    if total == 0:
        print("find_nested_comment_open: OK — every comment closes.")
        return 0
    print(f"\n{total} site(s). The module will still type-check and its interface will silently "
          f"lose every declaration after the comment, surfacing elsewhere as "
          f"'module X has no exported member Y'. Write an aggregate without its star, as "
          f"core.storage.db does.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
