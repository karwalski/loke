#!/usr/bin/env python3
"""Find `x.field == value;` used as a STATEMENT — an assignment that silently does nothing.

Why this exists
---------------
toke has no assignment to a struct field or array element at all (upstream T-26). `x.f = v` is
a parse error, and E2002's advice for it is to "use `==`" — which turns the parse error into a
legal expression statement whose value is discarded. The struct is unchanged, nothing warns,
and the function reads exactly like one that works by mutation.

**21 sites in 6 modules of the built trees**, every one silent, found 2026-09-24. What they
cost:

  governance/gateway.tk x4     `activatekillswitch` logged "kill switch activated" at ERROR
                               level and left the flag false. `deactivatekillswitch` the same
                               in reverse. A control whose only observable effect is a log line
                               saying it worked.
  governance/trace.tk x6       the decision trace recorded no PII finding, no model, no
                               provider, no response and no duration; `addstep` added no step.
                               GA5.5's subject, and worse than "not persisted" — never
                               populated in memory either.
  agents/observability.tk x3   same three recorders, same nothing.
  agents/registry.tk x2        `enable` and `disable` built the updated agent array correctly,
                               discarded it, and returned `$ok(0)` — **reporting success for
                               work they had not done.** `listenabled` kept returning the old
                               set whatever anyone enabled.
  governance/suppression.tk x1 a suppressed violation was pushed back with `suppressed:false`,
                               so the count went up and the flag did not.
  cli/src/installer.tk x5      every installer flag ignored — and that function had two further
                               defects on top (an `if` where a `lp` was meant, so only argv[0]
                               was examined, and value flags reading their own position instead
                               of the one after).

**No existing check covered this class**, which is why it survived a session of sweeps.
`find_field_matches.py` sounds like it would and does not — it is about a `mt` over a struct
field with three or more arms (T-2), a different defect.

What it flags
-------------
A line whose whole content is `<lowercase-ident>.<field-path> == <expr>`, with or without a
trailing semicolon, outside comments. That is never useful as a statement: a comparison in
statement position has no effect in any language, so there is no false-positive shape to
exclude. A real comparison appears inside `if(...)`, as a `<` return, or bound to a `let`.

Deliberately NOT flagged: `a == b` with no field access (a bare local comparison is equally
useless but is not the T-26 trap and does not appear here), and anything inside `(* ... *)`.

    python3 scripts/find_discarded_field_compare.py --check packages/core packages/shared
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent

# `recv.field == value` (or `recv.a.b == value`) as the entire statement.
STMT = re.compile(r"^\s*([a-z][A-Za-z0-9_]*)\.([a-z][A-Za-z0-9_.]*)\s*==\s*([^;{}=]+);?\s*$")


def scan(path: pathlib.Path) -> list[tuple[int, str]]:
    raw = path.read_text(errors="replace")
    incomment = comment_mask(raw)
    hits = []
    pos = 0
    for line in raw.split("\n"):
        if pos < len(incomment) and not incomment[pos] and STMT.match(line):
            hits.append((raw.count("\n", 0, pos) + 1, line.strip()))
        pos += len(line) + 1
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
            for line, text in scan(f):
                print(f"  {f.relative_to(REPO)}:{line}: {text[:78]}")
                print(f"      a comparison in statement position. An assignment was meant, and "
                      f"toke has none (T-26) — rebuild the struct and RETURN it.")
                total += 1

    if total == 0:
        print("find_discarded_field_compare: OK — no field comparison used as a statement.")
        return 0
    print(f"\n{total} site(s). Each one is a function that does nothing and looks like it "
          f"works. Return a rebuilt struct instead of mutating; see "
          f"core.governance.trace for the shape.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
