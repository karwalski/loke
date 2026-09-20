#!/usr/bin/env python3
"""Find accumulators that are re-declared with `let` instead of assigned (story LS1.1c).

Why this exists
---------------
`let x=...` inside an if-branch does not assign to an `x` declared outside it — it
declares a second, branch-local `x`. The outer one keeps its initial value, so the
accumulation silently does nothing. A counter written that way never advances, which
turns `lp(...){ if(i>n){br} ... let i=i+1; }` into an infinite loop.

It also produces invalid LLVM: toke emits the alloca inside the branch and the load
after it, and clang rejects the module with "Instruction does not dominate all uses".
So the same source defect shows up as a link failure with no file name attached,
which is why this sweep exists rather than a read of the linker output.

The fix in every case is `let x=mut.<init>` outside, and a bare `x=...` inside.

Usage
-----
    python3 scripts/find_shadowed_lets.py packages
    python3 scripts/find_shadowed_lets.py --check packages    # exit 1 if any found
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

FUNC = re.compile(r'(?m)^f=(\w+)\(')
LET = re.compile(r'(?<![\w.])let\s+(\w+)\s*=')


def depths(body: str) -> list[int]:
    """Brace depth at each character, ignoring braces inside strings and comments."""
    out = []
    d = 0
    i = 0
    n = len(body)
    in_str = False
    while i < n:
        c = body[i]
        if in_str:
            if c == "\\":
                out.append(d); out.append(d); i += 2; continue
            if c == '"':
                in_str = False
        elif c == '"':
            in_str = True
        elif body.startswith("(*", i):
            j = body.find("*)", i)
            j = n if j < 0 else j + 2
            out.extend([d] * (j - i))
            i = j
            continue
        elif c == "{":
            d += 1
        elif c == "}":
            d -= 1
        out.append(d)
        i += 1
    return out


def scan_file(path: pathlib.Path) -> list[tuple[str, str, int, list[int]]]:
    """Report a `let` that shadows an OUTER `let` of the same name still in scope.

    Two sequential loops each declaring their own `lv` are disjoint sibling scopes
    and perfectly legal — the defect is specifically an inner declaration sitting
    inside the outer one's braces, because that is the one that looks like an
    assignment and is not.
    """
    text = path.read_text(errors="replace")
    starts = [(m.start(), m.group(1)) for m in FUNC.finditer(text)]
    out = []
    for idx, (pos, name) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(text)
        body = text[pos:end]
        dep = depths(body)
        decls: dict[str, list[tuple[int, int]]] = {}
        for m in LET.finditer(body):
            off = m.start()
            if off >= len(dep):
                continue
            decls.setdefault(m.group(1), []).append((off, dep[off]))
        for var, ds in decls.items():
            shadowed = []
            for k in range(1, len(ds)):
                off, d = ds[k]
                for poff, pd in ds[:k]:
                    if pd >= d:
                        continue
                    # still in scope if depth never fell back to pd between them
                    if min(dep[poff:off] or [pd]) >= pd:
                        shadowed.append(off)
                        break
            if shadowed:
                lines = sorted({text.count("\n", 0, pos + o) + 1
                                for o in [ds[0][0]] + shadowed})
                out.append((name, var, len(shadowed) + 1, lines))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--check", action="store_true", help="exit 1 if any are found")
    args = ap.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    total = 0
    files = 0
    for root in args.roots:
        r = (repo / root) if not pathlib.Path(root).is_absolute() else pathlib.Path(root)
        for f in sorted(r.rglob("*.tk")):
            if "/build/" in str(f) or "/archive/" in str(f):
                continue
            hits = scan_file(f)
            if not hits:
                continue
            files += 1
            print(f"{f.relative_to(repo)}")
            for fn, var, n, lines in hits:
                print(f"  {fn}: `{var}` declared {n}x at lines {lines}")
                total += 1
    print(f"\n{total} shadowed binding(s) across {files} file(s)")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
