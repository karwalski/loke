#!/usr/bin/env python3
"""Find `lp(...){ if(i>n){br} ... }` loops that read one past the end (LS1.1f).

The defect
----------
The idiom for a counted loop in this codebase is

    let i=mut.0;
    lp(let lv=0;true;lv=lv){
      if(i>count){ br }el{ let x=arr.get(i); … ; i=i+1 }
    };

`i>count` breaks one iteration too late: when `i==count` the guard is false, so
`arr.get(count)` runs — an out-of-bounds read. For an array of structs that is a
garbage pointer, and dereferencing a field of it is how these turn into SIGSEGV.
The guard has to be `i>=count`, or better `lp(let i=0;i<count;i=i+1)`.

It is invisible in testing whenever the element happens to sit on a mapped page and
the garbage field read happens to be harmless, which is why it survived: the loop
produces the right answer and reads one extra element.

Usage
-----
    python3 scripts/find_offbyone_loops.py packages
    python3 scripts/find_offbyone_loops.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# `if(i>count){ br }` or `if(!(i<count))` is correct; `if(i>count)` is not
BAD = re.compile(r'if\s*\(\s*(\w+)\s*>\s*(\w+(?:\.\w+)*)\s*\)\s*\{\s*br\b')


def scan(path: pathlib.Path) -> list[tuple[int, str, str]]:
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    out = []
    for m in BAD.finditer(text):
        var, bound = m.group(1), m.group(2)
        ln = text.count("\n", 0, m.start()) + 1
        out.append((ln, f"{var}>{bound}", lines[ln - 1].strip()[:80]))
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
            if "/build/" in str(f) or "/archive/" in str(f):
                continue
            hits = scan(f)
            if not hits:
                continue
            print(f.relative_to(repo))
            for ln, cond, txt in hits:
                print(f"  L{ln} {cond}  |  {txt}")
                total += 1
    print(f"\n{total} loop(s) that break one iteration too late")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
