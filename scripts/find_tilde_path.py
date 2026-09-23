#!/usr/bin/env python3
"""Find a string literal beginning `~/` used as a PATH. The tilde is never expanded.

Why this exists
---------------
Measured at toke `fedd48d`, with the file genuinely present:

    file.exists("~/.loke/probe")                 -> false
    file.exists("/Users/<me>/.loke/probe")       -> true
    file.appendline("~/.loke/probe"; "hello")    -> writes NOTHING

The write neither reaches `$HOME` nor creates a literal `~` directory in the working
directory; it fails and the result is discarded. The tilde is a shell convention and nothing
in toke's path layer expands it.

29 string literals in this repository began with `~/`. What that cost, in descending order:

  shared/log.tk (x4)        every log.debug/info/warn/error appended to "~/.loke/loke.log", so
                            **loke has never written a log file** — every log line this project
                            ever emitted was silently discarded. It is why nothing here has ever
                            been diagnosed from logs.
  shared/config.tk          defaultconfig().datadir was "~/.loke", making the default store
                            path a literal `./~/.loke/loke.db`.
  3 config load sites       browser/extensions/core.tk, cli/src/main.tk,
                            mcp-broker/src/main.tk all loaded "~/.loke/config.toml", so a user's
                            configuration file was never read. Compounded by T-18: the `$err`
                            arm that was meant to fall back to defaults could not run either,
                            so callers read fields off an error payload.
  cli/src/doctor.tk (x2)    tested file.exists("~/.loke") and so reported the data directory and
                            the config file MISSING on a correct installation.
  agents/templates.tk (x2)  granted a sandbox permission scoped to `$readfile("~/.loke/")`,
                            which can never match a real path, so the permission never granted.

Use `shared.types.homepath` / `lokedir` / `lokefile` / `configpath`.

What it does NOT flag
---------------------
A literal `~` in text SHOWN to a user is correct — `detail:"~/.loke/ exists"` in a doctor report
is the right thing to print, and rewriting it to an absolute path would be worse. Those sites
are listed in DISPLAY_SITES below, by file and line, with the reason. The list is short on
purpose: a long allowlist is how this check would stop meaning anything.

    python3 scripts/find_tilde_path.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent
TILDE = re.compile(r'"~/[^"]*"')

# Sites where a literal `~` is text for a human, not a path for the runtime.
# Keyed by path, value is a set of the exact literals allowed in that file.
DISPLAY_SITES = {
    # `loke doctor` prints these to the operator. `~/.loke/` is how a person writes that
    # directory, and printing "/Users/<someone>/.loke/" instead would be worse, not better.
    "packages/cli/src/doctor.tk": {
        '"~/.loke/ exists"',
        '"~/.loke/ not found"',
        '"~/.loke/config.toml exists"',
        '"~/.loke/config.toml not found"',
    },
}


def scan(path: pathlib.Path, rel: str) -> list[tuple[int, str]]:
    raw = path.read_text(errors="replace")
    incomment = comment_mask(raw)
    allowed = DISPLAY_SITES.get(rel, set())
    hits = []
    for m in TILDE.finditer(raw):
        if incomment[m.start()]:
            continue
        if m.group(0) in allowed:
            continue
        hits.append((raw.count("\n", 0, m.start()) + 1, m.group(0)))
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
            rel = str(f.relative_to(REPO))
            for line, lit in scan(f, rel):
                print(f"  {rel}:{line}: {lit} — the tilde is NOT expanded, so this path never "
                      f"resolves")
                total += 1

    if total == 0:
        print("find_tilde_path: OK — no unexpanded `~/` path literal.")
        return 0
    print(f"\n{total} site(s). Use shared.types.homepath / lokedir / lokefile / configpath. If "
          f"the literal is text shown to a USER, add it to DISPLAY_SITES in this script with "
          f"the reason.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
