#!/usr/bin/env python3
"""Find a function whose body ENDS in a bare `mt` with no `<` (LS1.1f, toke T-19).

toke's E4071 catches a trailing bare match when the function returns a scalar. It does
not when the function returns a sum or a struct: that compiles, and the function
returns whatever happened to be in the return slot rather than the match's value.

An earlier sweep fixed the 104 cases where the match is the function's FIRST statement.
This finds the rest — where the match is the last statement but something precedes it:

    f=decodescalarfloatorstr(s:str):$toonvalue{
      let asfloat=str.parsefloat(s);
      mt asfloat {                       <- no `<`, value discarded
        $ok:f $toonvalue{$tvfloat:0};
        $err:e2 $toonvalue{$tvstr:0}
      }
    };

The caller then matches on a value that is not of the declared type, and crashes.

Usage
-----
    python3 scripts/find_discarded_tail_match.py packages tests
    python3 scripts/find_discarded_tail_match.py --check packages tests
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

FUNC = re.compile(r'(?m)^f=(\w+)\([^)]*\):([^{]+)\{')


def braces(text: str):
    """Yield (offset, char) for braces outside strings and (* *) comments."""
    i, n, in_str = 0, len(text), False
    while i < n:
        c = text[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
            i += 1
            continue
        if c == '"':
            in_str = True
            i += 1
            continue
        if text.startswith("(*", i):
            j = text.find("*)", i)
            i = n if j < 0 else j + 2
            continue
        if c in "{}":
            yield i, c
        i += 1


def scan(path: pathlib.Path) -> list[tuple[int, str, str]]:
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    events = list(braces(text))
    out = []
    for m in re.finditer(r'(?m)^(\s*)mt\s', text):
        start = m.start(0) + len(m.group(1))
        # a `<` immediately before means the value is returned
        head = text[:start].rstrip()
        if head.endswith("<"):
            continue
        ob = text.find("{", start)
        if ob < 0:
            continue
        depth, end = 0, ob
        for off, c in events:
            if off < ob:
                continue
            depth += 1 if c == "{" else -1
            if depth == 0:
                end = off
                break
        # The match is in TAIL position if everything between its closing brace and the
        # function's `};` is closing braces — it may sit at the end of nested if/el
        # branches, which is how core.optimiser.toon.decodescalar hid one.
        # The match is in TAIL position when at least one closing brace stands between
        # its own `}` and the `;` that ends the function — those are the enclosing
        # if/el branches. A match used as a STATEMENT is followed by `;` immediately,
        # with no brace in between, and its value is meant to be discarded; adding a
        # return there would make the rest of the function unreachable.
        tail = text[end + 1:end + 400]
        j, closers = 0, 0
        while j < len(tail) and tail[j] in " \t\r\n}":
            if tail[j] == "}":
                closers += 1
            j += 1
        if closers == 0 or tail[j:j + 1] != ";":
            continue
        # and the enclosing function does not return void
        fn = None
        for fm in FUNC.finditer(text):
            if fm.start() < start:
                fn = fm
            else:
                break
        if fn is None or fn.group(2).strip() == "void":
            continue
        ln = text.count("\n", 0, start) + 1
        out.append((ln, fn.group(1), lines[ln - 1].strip()[:60]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    total = 0
    for root in args.roots:
        r = (repo / root) if not pathlib.Path(root).is_absolute() else pathlib.Path(root)
        for f in sorted(r.rglob("*.tk")):
            if "/build/" in str(f) or "/archive/" in str(f) or "_archived" in str(f):
                continue
            hits = scan(f)
            if not hits:
                continue
            print(f.relative_to(repo))
            for ln, fn, txt in hits:
                print(f"  L{ln} in f={fn}  |  {txt}")
                total += 1
    print(f"\n{total} function(s) discarding a trailing match")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
