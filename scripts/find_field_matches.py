#!/usr/bin/env python3
"""Find `mt <struct field>` with three or more arms — toke miscompiles these (T-2).

The defect
----------
toke emits duplicate basic-block labels for a match of three or more arms whose
subject is a struct field access, and clang rejects the whole module with
"Terminator found in the middle of a basic block!". The module compiles; only the
link fails, and the error names an LLVM label, not a source file — which is why this
sweep exists instead of a read of the linker output.

Measured shape of the bug, from scripts/../docs/upstream/toke-issues.md T-2:

    mt x        { 3 arms }   links      (a plain local or parameter)
    mt mk()     { 3 arms }   links      (a call result)
    mt w.tier   { 2 arms }   links      (two arms are fine — $ok/$err is unaffected)
    mt w.tier   { 3 arms }   FAILS
    let t=w.tier; mt t {3}   FAILS      (binding it to a local does NOT help)

The workaround is to pass the field through a function boundary: put the match in
its own function taking the sum type as a parameter, and pass the field at the call
site.

Usage
-----
    python3 scripts/find_field_matches.py packages
    python3 scripts/find_field_matches.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

ARM = re.compile(r'(?m)\$\w+\s*:')


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


def scan(path: pathlib.Path) -> list[tuple[int, str, int, str]]:
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    events = list(braces(text))
    out = []
    # `mt` followed by a dotted subject, i.e. a field access rather than a bare name
    for m in re.finditer(r'(?<![\w.])mt\s+([A-Za-z_]\w*(?:\.\w+)+)\s*\{', text):
        subject = m.group(1)
        ob = text.index("{", m.end() - 1)
        depth, end = 0, ob
        for off, c in events:
            if off < ob:
                continue
            depth += 1 if c == "{" else -1
            if depth == 0:
                end = off
                break
        arms = len(ARM.findall(text[ob + 1:end]))
        if arms >= 3:
            ln = text.count("\n", 0, m.start()) + 1
            out.append((ln, subject, arms, lines[ln - 1].strip()[:90]))
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
            for ln, subj, arms, txt in hits:
                print(f"  L{ln} mt {subj} ({arms} arms)  {txt}")
                total += 1
    print(f"\n{total} match(es) on a struct field with 3+ arms")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
