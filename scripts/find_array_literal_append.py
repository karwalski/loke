#!/usr/bin/env python3
"""Find `@(collection; item)` written where an append was meant.

`@(a;b)` is a two-element ARRAY LITERAL. It is not an append. Where `a` is itself an
array, the result is `[[...], b]` — length 2 whatever `a` held — and the next loop over
it reads element 0 as if it were the element type, dereferences an array handle as a
struct, and segfaults intermittently depending on what that memory happens to hold.

`tests/unit/governance/test_kill_switch.tk` did exactly this and crashed in 19 runs out
of 20. `.push()` is the append.

The check is a heuristic: two top-level arguments, the first a bare name or dotted path
with no call and no literal. That shape is almost never a genuine two-element literal,
but each hit still needs reading — the point is to produce a short list, not to rewrite.

    python3 scripts/find_array_literal_append.py
"""

from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


def args_of(text: str, open_paren: int):
    depth = 0
    i = open_paren
    args = []
    start = open_paren + 1
    while i < len(text):
        c = text[i]
        if c == '"':
            i += 1
            while i < len(text):
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
                args.append(text[start:i])
                return args, i
        elif c == ";" and depth == 1:
            args.append(text[start:i])
            start = i + 1
        i += 1
    return None, i


def main() -> int:
    hits = 0
    for f in sorted(REPO.rglob("*.tk")):
        if "archive" in f.parts or "build" in f.parts:
            continue
        text = f.read_text(errors="replace")
        pos = 0
        while True:
            k = text.find("@(", pos)
            if k < 0:
                break
            args, end = args_of(text, k + 1)
            pos = end + 1
            if not args or len(args) != 2:
                continue
            first = args[0].strip()
            if not NAME.match(first):
                continue
            # A bare scalar name is a legitimate two-element literal; a dotted path
            # ending in a plural, or one the file declares as an array, is the shape
            # that means append. Report both and let a human read them.
            line = text.count("\n", 0, k) + 1
            rel = f.relative_to(REPO)
            snippet = text[k:end + 1].replace("\n", " ")[:90]
            print(f"{rel}:{line}: {snippet}")
            hits += 1
    print(f"\n{hits} candidate(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
