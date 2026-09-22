#!/usr/bin/env python3
"""Swap the arguments of every `str.join` call (toke issue T-23).

`str.join` is declared `(str, [str]) -> str` — separator first, array second.
Every call site in this repository passes them the other way round. It compiles
because `str` and `[str]` are both an i64 handle at the ABI, so the type checker
cannot tell them apart; at run time `join` walks a string as if it were an array
and segfaults.

The stdlib's own neighbours go the other way (`fmt.strs([str], str)`,
`fmt.arr([i64], str)`), which is why the wrong order looked right.

Arguments are found by balancing parentheses, not by regex: several call sites
span many lines and contain nested calls, string interpolation and `@(...)`
literals.

    python3 scripts/fix_join_order.py --check    # report, change nothing
    python3 scripts/fix_join_order.py --apply
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
NEEDLE = "str.join("


def split_args(text: str, start: int) -> tuple[list[tuple[int, int]], int] | None:
    """Return each top-level argument's span and the index past the closing paren.

    Tracks nesting through (), [], {} and @( ) alike, and skips string literals so
    that a `;` or `)` inside one is not mistaken for structure. toke strings carry
    `\\(...)` interpolation, whose parens are inside the literal and must not count.
    """
    depth = 0
    i = start
    args: list[tuple[int, int]] = []
    arg_start = start + 1
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
            i += 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                args.append((arg_start, i))
                return args, i + 1
        elif c == ";" and depth == 1:
            args.append((arg_start, i))
            arg_start = i + 1
        i += 1
    return None


def process(path: pathlib.Path) -> tuple[str, list[str]]:
    text = path.read_text()
    notes: list[str] = []
    out = []
    pos = 0
    while True:
        k = text.find(NEEDLE, pos)
        if k < 0:
            break
        open_paren = k + len(NEEDLE) - 1
        parsed = split_args(text, open_paren)
        if parsed is None:
            notes.append(f"{path.name}: unbalanced call at offset {k}, left alone")
            out.append(text[pos:k + len(NEEDLE)])
            pos = k + len(NEEDLE)
            continue
        args, end = parsed
        line = text.count("\n", 0, k) + 1
        if len(args) != 2:
            notes.append(f"{path.name}:{line}: {len(args)} arguments, left alone")
            out.append(text[pos:end])
            pos = end
            continue
        a = text[args[0][0]:args[0][1]]
        b = text[args[1][0]:args[1][1]]
        # Already separator-first? A bare string literal in the first position and
        # something that is not one in the second is the shape we want to keep.
        if a.strip().startswith('"') and not b.strip().startswith('"'):
            notes.append(f"{path.name}:{line}: already separator-first, left alone")
            out.append(text[pos:end])
            pos = end
            continue
        out.append(text[pos:open_paren + 1])
        out.append(b.strip())
        out.append(";")
        out.append(a)
        out.append(")")
        notes.append(f"{path.name}:{line}: swapped")
        pos = end
    out.append(text[pos:])
    return "".join(out), notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    changed = 0
    swaps = 0
    for f in sorted(REPO.rglob("*.tk")):
        if "archive" in f.parts or "build" in f.parts:
            continue
        if NEEDLE not in f.read_text(errors="replace"):
            continue
        new, notes = process(f)
        for n in notes:
            print("  " + n)
            if n.endswith("swapped"):
                swaps += 1
        if new != f.read_text():
            changed += 1
            if args.apply:
                f.write_text(new)
    verb = "swapped" if args.apply else "would swap"
    print(f"\n{verb} {swaps} call(s) across {changed} file(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
