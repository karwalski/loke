#!/usr/bin/env python3
"""Find a child process that is WAITED for before its output is read. That deadlocks.

Why this exists
---------------
Found 2026-09-24, when /sysmon hung the loke server intermittently. The page ran
`ps`, called `process.wait(h)` and then `process.stdout(h)`. The child writes into a pipe,
and a pipe holds 65,536 bytes on macOS. The `ps` listing measured 64,608 bytes, so once the
process list grew a little, ps blocked on a full pipe and waited for a reader. loke was
waiting for ps to exit, and neither ever moved. It sat right at the edge, which is why it
hung on some requests and not on others.

`process.stdout` reads to EOF, so reading first and waiting second is always safe. That is
the fix everywhere this reports. The same order held in nine places, in the monitoring
module, moke's sysmon page, the installer, and the CLI's updater and signer. Most had small
outputs today, which is luck rather than safety.

It flags a `process.wait(h)` followed, within the next few hundred characters, by
`process.stdout(h)` or `process.stderr(h)` on the same handle.

    python3 scripts/find_wait_before_read.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
WAIT = re.compile(r"process\.wait\((\w+)\)")


def scan(raw: str) -> list[tuple[int, str]]:
    incomment = comment_mask(raw)
    hits = []
    for m in WAIT.finditer(raw):
        if incomment[m.start()]:
            continue
        h = m.group(1)
        after = raw[m.end():m.end() + 800]
        r = re.search(r"process\.std(out|err)\(" + re.escape(h) + r"\)", after)
        if r and not incomment[m.end() + r.start()]:
            hits.append((raw.count("\n", 0, m.start()) + 1, h))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    total = 0
    for root in args.roots:
        base = pathlib.Path(root) if pathlib.Path(root).is_absolute() else REPO / root
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = sorted(base.rglob("*.tk"))
        else:
            continue
        for f in files:
            if any(x in f.parts for x in ("_archived-tests", "build")):
                continue
            for ln, h in scan(f.read_text(errors="replace")):
                shown = f.relative_to(REPO) if f.is_relative_to(REPO) else f
                print(f"  {shown}:{ln}: process.wait({h}) before its output is read. "
                      f"Once the output fills the pipe, this deadlocks")
                total += 1
    if total == 0:
        print("find_wait_before_read: OK — every child's output is read before it is waited for.")
        return 0
    print(f"\n{total} site(s). Read stdout and stderr first, then wait.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
