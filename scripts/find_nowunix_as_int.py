#!/usr/bin/env python3
"""Find `str.nowunix()` used as a number. As a number it is a heap ADDRESS, not the time.

Why this exists
---------------
Measured 2026-09-24 at toke fedd48d:

    str.fromint(str.nowunix())        -> 37631297824, then 37631297856 on the next call
    let s:str=str.nowunix(); s        -> 1790327645   (the real time, as TEXT)

`std.str` declares nowunix in its `gen:"abi"` block with an i64 return (T-36, T-41). It
returns a string, so arithmetic on it is arithmetic on an address. There were 17 sites.
The kill switch's engaged_at and auto-release deadline were addresses, so whether a timed
block expired depended on the allocator; that was the intermittent test_kill_switch
failure. The budget's day number was an address divided by 86400, so "today" moved with
allocation. Every request duration in the audit trail and in metrics_raw was a
difference of two addresses. The metrics windows (24h, 7d, ...) were measured back from
an address.

Use shared.types.nowi64() for seconds and nowms() for milliseconds. The only safe use of
str.nowunix() is `let x:str=str.nowunix();` as text. Even that is fragile (T-46), so this
flags every use.

    python3 scripts/find_nowunix_as_int.py --check packages tests
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
USE = re.compile(r"\bstr\.nowunix\(\)")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages", "tests"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    total = 0
    for root in args.roots:
        base = pathlib.Path(root) if pathlib.Path(root).is_absolute() else REPO / root
        files = [base] if base.is_file() else sorted(base.rglob("*.tk")) if base.is_dir() else []
        for f in files:
            if any(x in f.parts for x in ("_archived-tests", "build")):
                continue
            raw = f.read_text(errors="replace")
            mask = comment_mask(raw)
            for m in USE.finditer(raw):
                if mask[m.start()]:
                    continue
                shown = f.relative_to(REPO) if f.is_relative_to(REPO) else f
                print(f"  {shown}:{raw.count(chr(10), 0, m.start()) + 1}: str.nowunix() is a "
                      f"string; as a number it is an address. Use shared.types.nowi64()/nowms()")
                total += 1
    if total == 0:
        print("find_nowunix_as_int: OK — no str.nowunix() in code.")
        return 0
    print(f"\n{total} site(s).", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
