#!/usr/bin/env python3
"""Find a statement followed by `<expr` with no semicolon between them (LS1.1d).

Why it matters
--------------
`<` is both the return operator and the less-than operator. So

    (log.info("...";"c";""))
    <$ok(1)

parses as ONE expression — `(log.info(...)) < $ok(1)` — a comparison whose result is
discarded. The function returns that comparison instead of `$ok(1)`, and nothing is
reported: no parse error, no type error, no warning. toke only complains when the
left operand is a void call, and then the error arrives from clang as

    error: void type only allowed for function results

naming an LLVM line, not this one.

Usage
-----
    python3 scripts/find_missing_return_semi.py packages
    python3 scripts/find_missing_return_semi.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# a line that ends a statement without a terminator, where the NEXT non-blank line
# starts a return
OPENS_RETURN = re.compile(r'^\s*<[^-=]')


def scan(path: pathlib.Path) -> list[tuple[int, str, str]]:
    lines = path.read_text(errors="replace").splitlines()
    out = []
    for i in range(len(lines) - 1):
        cur = lines[i].rstrip()
        if not cur or cur.lstrip().startswith("(*"):
            continue
        # must look like a completed call, not a comment or a block opener. A comment
        # ends in `*)` and an `el{` branch ends in `}`; neither is a statement missing
        # its semicolon, and both matched the naive "ends with )" rule.
        if not cur.endswith(")") or cur.endswith("*)"):
            continue
        if cur.lstrip().startswith(("(*", "*", "el", "}")):
            continue
        nxt = lines[i + 1]
        if not OPENS_RETURN.match(nxt):
            continue
        out.append((i + 1, cur.strip()[:80], nxt.strip()[:50]))
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
            for ln, cur, nxt in hits:
                print(f"  L{ln} {cur}")
                print(f"  L{ln+1} {nxt}   <- parses as a comparison, not a return")
                total += 1
    print(f"\n{total} missing semicolon(s) before a return")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
