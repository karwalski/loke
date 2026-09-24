#!/usr/bin/env python3
"""Find a `std.str` call whose result is interpolated. Some of them print a POINTER.

Why this exists
---------------
Measured 2026-09-24 at toke `fedd48d`, and again on toke main `444a55c`:

    io.println("[\\(str.fromi64(5))]")         -> [4349761984]
    io.println("[\\(str.randhex(4))]")         -> [4335262192]
    io.println("[\\(str.tolower("A"))]")       -> [a]

`std.str` declares about 90 functions in a `gen:"abi"` block with a return type of `i64`
(T-36). Interpolation formats a value by its declared type, so for those functions it
prints the string's address as a decimal integer. A binding inherits the declared type,
so `let s=str.fromi64(5); "\\(s)"` is wrong in the same way. Two forms are correct and
were measured:

    let s:str=str.fromi64(5); "\\(s)"          -> 5     (the annotation retypes it)
    str.concat("n=";str.fromi64(5))           -> n=5   (concat takes it as a string)

BUT THE ANNOTATION IS NOT SAFE EITHER (LS1.1s, measured 2026-09-24 at `fedd48d`, T-42). A
`let s:str=` binding of one of these names, written as an ELEMENT of an array literal, is
compiled as a SPREAD of `s`: the literal reads a length header off the string and copies
that many words. For `fromi64` the length reads 0, so the element silently disappears —
`db.exec(sql;@("k";s))` binds NULL for the second `?`, which a NOT NULL column refuses as
an error. For `randhex` it reads garbage and the process dies with SIGBUS. The same call
written inline, `@("k";str.fromi64(n))`, or through an unannotated binding, is correct.

So the form that is safe everywhere is a function DECLARED to return `str`:
`str.fromint(n)` for a number, or `str.concat("";...)` around anything else. The second
check below flags an annotated binding of an affected name used as an array element.

Which functions are affected cannot be read off the interface. `tolower`, `toupper` and
`substr` are in the same block and interpolate correctly. So AFFECTED below is the list
that was MEASURED to print an address, one call per name, and it is not derived from
the .tki file. A name that is not on it has not been proven safe. It has just not been
tested.

What it found, the day it was written:

  core/privacy/pipeline.tk   the privacy pipeline's summary printed three addresses where
                             it meant to give the RESTRICTED count, the CONFIDENTIAL count
                             and the stage count. That is the one line of the
                             pipeline that tells a person what it did.
  moke/src/workspace.tk      every project id was "p-" followed by an address, so ids were
                             neither random nor hex, and two projects created from the same
                             heap state could collide.

    python3 scripts/find_interp_abi_str.py --check packages tests
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent

# Measured to interpolate as an address, 2026-09-24, one probe per name. See the docstring.
AFFECTED = {
    "fromi64", "fromint64", "fromi32", "fromu32", "fromu16", "frombool", "randhex",
    "nowiso8601", "padleft", "padright", "sha256prefix", "trimws", "strip", "reverse",
    "replaceall",
}

IMPORT = re.compile(r"\bi=(\w+):std\.str;")
NAMES = "|".join(sorted(AFFECTED))


def scan(raw: str) -> list[tuple[int, str]]:
    incomment = comment_mask(raw)
    aliases = set(IMPORT.findall(raw))
    if not aliases:
        return []
    alias = "|".join(re.escape(a) for a in sorted(aliases))
    direct = re.compile(r"\\\((?:" + alias + r")\.(" + NAMES + r")\(")
    # An unannotated binding takes the declared i64 type. `let x:str=` does not.
    bound = re.compile(r"\blet\s+(\w+)\s*=\s*(?:mut\.)?(?:" + alias + r")\.(" + NAMES + r")\(")

    hits = []

    def line(pos: int) -> int:
        return raw.count("\n", 0, pos) + 1

    for m in direct.finditer(raw):
        if not incomment[m.start()]:
            hits.append((line(m.start()), f"\\({m.group(0)[2:]}...) interpolates str.{m.group(1)}"
                                          f" — prints an ADDRESS, not the string"))

    for m in bound.finditer(raw):
        if incomment[m.start()]:
            continue
        name, fn = m.group(1), m.group(2)
        # The same function body: up to the next top-level `f=` definition.
        end = raw.find("\nf=", m.end())
        body = raw[m.end(): end if end >= 0 else len(raw)]
        u = re.search(r"\\\(" + re.escape(name) + r"\)", body)
        if u:
            pos = m.end() + u.start()
            if not incomment[pos]:
                hits.append((line(pos), f"\\({name}) where {name} is an unannotated "
                                        f"str.{fn} result (line {line(m.start())}) — prints an ADDRESS, "
                                        f"not the string"))
    # LS1.1s / T-42: an ANNOTATED binding of an affected name, used as an array-literal
    # element, is compiled as a spread of it and dropped (or crashes).
    annotated = re.compile(r"\blet\s+(\w+)\s*:\s*str\s*=\s*(?:mut\.)?(?:" + alias + r")\.("
                           + NAMES + r")\(")
    literal = re.compile(r"@\(([^()]*(?:\([^()]*\)[^()]*)*)\)")
    for m in annotated.finditer(raw):
        if incomment[m.start()]:
            continue
        name, fn = m.group(1), m.group(2)
        end = raw.find("\nf=", m.end())
        body = raw[m.end(): end if end >= 0 else len(raw)]
        for u in literal.finditer(body):
            pos = m.end() + u.start()
            if incomment[pos]:
                continue
            if name in [e.strip() for e in u.group(1).split(";")]:
                hits.append((line(pos), f"{name} is a `let {name}:str=str.{fn}(...)` binding "
                                        f"used as an ARRAY ELEMENT (line {line(m.start())}) — "
                                        f"compiled as a spread, so it is dropped (T-42)"))
    return sorted(hits)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages", "tests"])
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
            rel = str(f.relative_to(REPO))
            for ln, what in scan(f.read_text(errors="replace")):
                print(f"  {rel}:{ln}: {what}")
                total += 1

    if total == 0:
        print("find_interp_abi_str: OK — no affected std.str result is interpolated.")
        return 0
    print(f"\n{total} site(s). Use a function declared to return str: `str.fromint(n)` for a "
          f"number, `str.concat(\"\";...)` otherwise. Annotating the binding fixes interpolation "
          f"but not an array element (T-42).",
          file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
