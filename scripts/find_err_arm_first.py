#!/usr/bin/env python3
"""Find a `mt` on a result whose ERROR arm is written before its `$ok` arm.

Why this exists
---------------
Measured 2026-09-23, and it unifies two findings that looked separate:

**`mt` binds arms by POSITION, not by label.**

    mt json.dec("{{{not json") { $jsonerr:e 2; $ok:o 1 }   -> runs `$ok:o 1`
    mt json.dec("{\"a\":1}")   { $jsonerr:e 2; $ok:o 1 }   -> runs `$jsonerr:e 2`

With a **stdlib** error type the discriminant IS read, but it selects arm[0] for ok and
arm[1] for err — so the match is correct only when `$ok` happens to be written first. Write
it second and every outcome is exactly backwards: success runs the error handler and failure
runs the success handler.

With a **user-declared** error side (`X!$lokeerr`) the discriminant is not read at all and
arm[0] always runs, whatever the value. That is upstream T-18, and this is the same bug —
T-18 is the special case where the discriminant is missing entirely.

This is not theoretical. `mcptoke.server` had the error arm first in six matches, so
`handlerequest` returned "Parse error" for every well-formed request and `start()` logged
"failed to listen" without accepting a connection: the entire MCP server was unreachable, with
no diagnostic anywhere.

So the rule is mechanical and worth gating: in a `mt` over a result, `$ok` comes first.

What it flags
-------------
A `mt` block whose first arm label is not `$ok` and which has an `$ok` arm later. That is
narrow on purpose — a `mt` over a plain sum (`$sensitivitylevel`, `$provider`) has no `$ok`
arm and is not affected, and plain-sum matches DO discriminate correctly by label.

    python3 scripts/find_err_arm_first.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
ARM = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\s*:")


def strip_noise(s: str) -> str:
    """Blank out string literals and (nesting) comments, PRESERVING LENGTH.

    Length-preserving matters and the first version of this was not. Deleting the
    characters instead of blanking them shifted every newline after the first comment, so
    the reported line numbers drifted — one hit in `mcp/client.tk` was reported 17 lines
    from its actual `mt`, pointing at an unrelated function. A sweep that names the wrong
    line is worse than one that names none, because it gets fixed at the wrong site.

    So each removed character becomes a space, and newlines are always kept: offsets and
    line numbers in the result are identical to the source.
    """
    out = list(s)
    i = 0
    depth = 0

    def blank(a: int, b: int) -> None:
        for k in range(a, b):
            if out[k] != "\n":
                out[k] = " "

    while i < len(s):
        if depth == 0 and s[i] == '"':
            start = i
            i += 1
            while i < len(s):
                if s[i] == "\\":
                    i += 2
                    continue
                if s[i] == '"':
                    i += 1
                    break
                i += 1
            blank(start, i)
            continue
        if s.startswith("(*", i):
            if depth == 0:
                cstart = i
            depth += 1
            i += 2
            continue
        if s.startswith("*)", i) and depth > 0:
            depth -= 1
            i += 2
            if depth == 0:
                blank(cstart, i)
            continue
        i += 1
    if depth > 0:
        blank(cstart, len(s))
    return "".join(out)


def scan(path: pathlib.Path) -> list[tuple[int, str, str]]:
    text = strip_noise(path.read_text(errors="replace"))
    hits = []
    for m in re.finditer(r"\bmt\b", text):
        brace = text.find("{", m.end())
        if brace < 0:
            continue
        # Balance to the closing brace of the match block.
        depth = 0
        j = brace
        while j < len(text):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        block = text[brace + 1:j]
        labels = ARM.findall(block)
        if not labels or "ok" not in labels:
            continue          # not a result match
        if labels[0] != "ok":
            line = text.count("\n", 0, m.start()) + 1
            hits.append((line, labels[0], ",".join(labels)))
    return hits


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
            for line, first, allarms in scan(f):
                print(f"  {f.relative_to(REPO)}:{line}: `${first}` is written before `$ok`, "
                      f"so this match is INVERTED — success runs the error arm. Arms: {allarms}")
                total += 1

    if total == 0:
        print("find_err_arm_first: OK — every `mt` over a result writes `$ok` first.")
        return 0
    print(f"\n{total} inverted match(es). Move `$ok` to the first arm. Arms bind by POSITION, "
          f"not by label — see the docstring.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
