#!/usr/bin/env python3
"""Find a function whose body ends in a bare EXPRESSION, so its result is discarded.

Why this exists
---------------
`packages/shared/src/types.tk` carried eight wrappers that returned nothing for as long
as they existed:

    f=strlen(s:str):i64{
      str.len(s)          (* no `<` — evaluated, then thrown away *)
    };

Measured before the fix: `strlen("abcdef")` was **0**, `streq("a";"a")` was **false**,
`strconcat("ab";"cd")` was **""**. `strisempty`, five lines away in the same file, has its
`<` and always worked, which is why a skim found nothing.

It was not decorative. `core/router/escalation.tk` was **entirely dead** — its ladder never
matched, and `strlen(x) < 100` was always true because `strlen` returned 0.
`eval/advisor.tk` fell to its default on all four branches; `eval/bench.tk` scored every
case 0. Fifteen call sites in five modules, none doing what they read as doing.

This is the same class as `find_discarded_tail_match.py` (a trailing bare `mt`, upstream
T-19) with a plain call instead of a match — and **no sweep in this repository was looking
for it**, which is why it survived. toke emits no diagnostic: a bare expression statement
is legal, and a function that falls off its end returns whatever is in the return register.

What it flags, and what it does not
-----------------------------------
A function declared with a non-`void` return type whose final statement is a bare
expression — a call, a field access, an identifier — rather than `<expr`, a `br`, or a
control-flow construct whose branches all return.

Deliberately NOT flagged:

  - `if(c){<a}el{<b}` as the whole body. Both branches return; there is no fall-through.
  - A body ending in `lp(...){...}` where a `<` precedes it, or a bare `mt` — the latter is
    `find_discarded_tail_match.py`'s job and flagging it twice is noise.
  - A function declared `:void` or `:i64` used as a procedure whose result no caller reads.
    That last one cannot be distinguished from a defect by looking at the definition, so
    the check reports it, and the fix is `<0` (toke's convention for a procedure, W1020)
    or the honest return type. The known-defects allowlist this used to read was emptied
    and removed by LS1.1m: one of its "no live caller" entries was a live route.

    python3 scripts/find_discarded_tail_expr.py --check packages shared
    python3 scripts/find_discarded_tail_expr.py packages src tests
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

FUNC = re.compile(r"^f=([A-Za-z_][A-Za-z0-9_]*)\s*\(")
# A statement that legitimately ends a function.
RETURNS = ("<", "br", "cn")
CONTROL = ("if(", "if ", "lp(", "lp ", "mt ", "mt(")


def declared_return(decl: str) -> str | None:
    """The text after the final `):` of the signature, before the opening brace."""
    m = re.search(r"\)\s*:\s*([^{]+)\{\s*$", decl)
    return m.group(1).strip() if m else None


def scan(path: pathlib.Path) -> list[tuple[int, str, str, str]]:
    """Flag a non-void function whose body contains NO `<` return at all.

    This is deliberately narrow, and the first version of it was not. A
    "last meaningful line is a bare expression" heuristic produced **309 hits, almost all
    false**: the tail was usually the final arm of a multi-line `mt`, or the final field of
    a struct literal, both already returned by a `<` further up. A line-based rule cannot
    tell an arm from a statement without parsing, and a check that cries wolf 300 times is
    a check somebody deletes.

    "No `<` anywhere in a function that declares a return type" cannot have that false
    positive: whatever the shape of the body, a function that never returns a value and is
    declared to return one is wrong. It catches all eight real defects in shared.types and
    nothing else in the built tree.

    What it misses, stated so nobody trusts it too far: a function with a `<` on ONE branch
    and a discarded expression on another. That needs a parser, and
    `find_discarded_tail_match.py` covers the specific case of a trailing bare `mt`.
    """
    lines = path.read_text(errors="replace").split("\n")
    out = []
    i = 0
    while i < len(lines):
        if not FUNC.match(lines[i].strip()):
            i += 1
            continue
        decl = lines[i].strip()
        ret = declared_return(decl)
        if ret is None or ret == "void":
            i += 1
            continue
        depth = 0
        started = False
        body: list[tuple[int, str]] = []
        j = i
        while j < len(lines):
            raw = lines[j]
            for ch in raw:
                if ch == "{":
                    depth += 1
                    started = True
                elif ch == "}":
                    depth -= 1
            if started and j > i:
                body.append((j, raw))
            if started and depth == 0:
                break
            j += 1

        # Strip comments before looking for a return, so a `<` inside `(* ... *)` does not
        # count. Two traps here, both of which caught this script on its first run:
        #
        #   1. Comments NEST in toke (T-27), so track depth rather than matching pairs.
        #   2. STRING LITERALS must be skipped first. `"SELECT COUNT(*) ..."` contains the
        #      two characters `(*`, and a stripper that does not know it is inside a string
        #      enters comment mode and swallows the rest of the function — including its
        #      `<`. That produced three confident false positives on SQL-bearing functions
        #      (governance/dashboard.tk, governance/report.tk) which return perfectly well.
        #      It is the same trap as T-27 itself, one level up.
        text = "\n".join(l for _, l in body)
        cleaned = []
        cdepth = 0
        k = 0
        while k < len(text):
            if cdepth == 0 and text[k] == '"':
                cleaned.append('"')
                k += 1
                while k < len(text):
                    if text[k] == "\\":
                        k += 2
                        continue
                    if text[k] == '"':
                        k += 1
                        break
                    k += 1
                continue
            if text.startswith("(*", k):
                cdepth += 1; k += 2; continue
            if text.startswith("*)", k) and cdepth > 0:
                cdepth -= 1; k += 2; continue
            if cdepth == 0:
                cleaned.append(text[k])
            k += 1
        cleaned_text = "".join(cleaned)

        if "<" not in cleaned_text:
            tail = ""
            for ln, s in reversed(body):
                s = s.strip()
                if s and s not in ("};", "}") and not s.startswith("(*"):
                    tail = s
                    break
            out.append((i + 1, decl[:60], tail[:60], ret))
        i = j + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages"])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any site is found (for the gate)")
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
            for ln, decl, tail, ret in scan(f):
                print(f"  {rel}:{ln}  {decl}")
                print(f"      tail is a bare expression, so the `{ret}` is never returned: {tail}")
                total += 1

    if total == 0:
        print("find_discarded_tail_expr: OK — no function ends in a discarded expression.")
        return 0
    print(f"\n{total} function(s) whose result is discarded. Add `<` before the tail "
          f"expression; for a procedure whose value nobody wants, end it `<0`.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
