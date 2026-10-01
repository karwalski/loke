#!/usr/bin/env python3
"""Find a type name used as a value — toke reports nothing and the link fails (T-4).

The defect
----------
A bare type name in expression position (`fb.exportevents(store; ...)` where `store`
is std.db's `store` TYPE and no local of that name exists) passes name resolution and
type checking without a diagnostic. toke emits a reference to an SSA value that was
never defined, and the only error is

    error: use of undefined value '%store'
    E9003 clang invocation failed with exit code 1

which carries no file, line, or identifier from the loke source. E4033 ("'x' is a
type name, not a value") exists and fires for `$x.field`, but not for a bare `x`
passed as an argument.

This sweep finds them in the source, where the name is still attached to a line.

Usage
-----
    python3 scripts/find_typename_values.py packages
    python3 scripts/find_typename_values.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

# toke's own nameable types, which no `t=$x{` in this repo declares
TOKE_TYPES = {"store", "row", "httpresp", "httperr", "dbconn", "httpclient",
              "json", "handle", "conn"}
FUNC = re.compile(r'(?m)^f=(\w+)\(([^)]*)\)')
# a bare name in an argument position: after `(` or `;`, before `;` or `)`
ARG = re.compile(r'[(;]\s*([a-z_]\w*)\s*[;)]')


def declared_types(files: list[pathlib.Path]) -> set[str]:
    names = set(TOKE_TYPES)
    for f in files:
        names.update(re.findall(r'(?m)^t=\$(\w+)\{', f.read_text(errors="replace")))
    return names


def strip_noise(text: str) -> str:
    """Blank out (* *) comments and embedded <script> bodies.

    Both contain code that is not toke: a comment quoting the defect it describes, and
    the JavaScript inside a page template, where `function(row)` is perfectly ordinary.
    Blanking rather than deleting keeps every byte offset, so line numbers stay right.
    """
    out = list(text)
    i, n = 0, len(text)
    while i < n:
        if text.startswith("(*", i):
            j = text.find("*)", i)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if text[i] == '"':
            # a string literal, which in this codebase can hold a whole JS block
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        if text.startswith("<script", i):
            j = text.find("</script", i)
            j = n if j < 0 else j + 8
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def scan(path: pathlib.Path, types: set[str]) -> list[tuple[int, str, str]]:
    raw = path.read_text(errors="replace")
    text = strip_noise(raw)
    lines = raw.splitlines()
    starts = [(m.start(), m.group(1), m.group(2)) for m in FUNC.finditer(text)]
    out = []
    for idx, (pos, fname, params) in enumerate(starts):
        end = starts[idx + 1][0] if idx + 1 < len(starts) else len(text)
        body = text[pos:end]
        bound = set(re.findall(r'(\w+)\s*:', params))
        bound |= set(re.findall(r'(?<![\w.])let\s+(\w+)\s*[:=]', body))
        bound |= set(re.findall(r'lp\(let\s+(\w+)', body))
        bound |= set(re.findall(r'\$\w+\s*:\s*(\w+)\s', body))       # match bindings
        for m in ARG.finditer(body):
            name = m.group(1)
            if name not in types or name in bound:
                continue
            ln = text.count("\n", 0, pos + m.start()) + 1
            out.append((ln, name, lines[ln - 1].strip()[:90]))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    allfiles = [f for f in (repo / "packages").rglob("*.tk")
                if "/build/" not in str(f) and "/archive/" not in str(f)]
    types = declared_types(allfiles)

    total = 0
    for root in args.roots:
        r = (repo / root) if not pathlib.Path(root).is_absolute() else pathlib.Path(root)
        for f in sorted(r.rglob("*.tk")):
            if "/build/" in str(f) or "/archive/" in str(f):
                continue
            hits = scan(f, types)
            if not hits:
                continue
            print(f.relative_to(repo))
            for ln, name, txt in hits:
                print(f"  L{ln} `{name}` is a type, not a value  |  {txt}")
                total += 1
    print(f"\n{total} type name(s) used as a value")
    return 1 if (args.check and total) else 0


if __name__ == "__main__":
    sys.exit(main())
