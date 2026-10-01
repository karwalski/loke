#!/usr/bin/env python3
"""Find a failure sentinel that can never be seen: `x == @()`, and a spawn whose error arm is
not the NULL handle.

Why this exists
---------------
F10.44, found by MK19.9 and confirmed by its independent review (2026-10-01). The repository's
spawn-failure check was

    let h=mt process.spawn(argv) { $ok:h h; $err:e @() };
    if(h == @()){ ...fail... }el{};

and it never fails. Measured at toke 3.1.0 (86c432da): `==` on an array is a POINTER compare
(`icmp eq i8*`), and `@()` allocates a fresh block every time it is evaluated, so `h == @()` is
false for every h, including the very empty array the error arm produced. The code then went on
to `process.stdout(h)` and `process.wait(h)` with that empty array's address as the handle.
process_glue.c casts it to a ProcessHandle* and reads a pid and an fd out of the array header:
a pid of 0 or -1 makes waitpid wait for ANY child, so the caller can block for good. MK19.9's
first draft did exactly that when it spawned a `getent` macOS does not have.

The same holds for any other non-NULL value in the error arm: `$err:e ""` (a pointer to an
empty string) or `$err:e $installresult{...}` (a pointer to a struct) is also read as a handle.
The runtime's own "bad handle" is NULL: with `$err:e 0`, process.stdout answers its error arm,
process.wait answers -1 and process.kill false, so even a missed check fails closed. Measured.

What it flags (comments are skipped):
  1. any `== @()` or `!= @()` comparison (either order). It is always false (always true for
     `!=`), whatever the left side holds.
  2. a `process.spawn` result matched with `$ok:h h` (the handle passed through) whose `$err`
     arm is anything but `0`. The subject is `process.spawn(...)` itself or a name bound to one
     earlier in the file.

Known exceptions are files another story owns; each is capped at the count it has today, so a
new instance in those files still fails, and a fixed one is reported as stale (not a failure).

    python3 scripts/find_empty_array_sentinel.py --check packages tests scripts
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent

# path -> (hits allowed, owner). Owned by another worker's story at the time of F10.44.
KNOWN = {
    "packages/moke/src/proxy/fetch.tk": (
        4, "moke's /api/proxy runout and fetchpinned; fixed with MK19.9's review finding 1 (W54), not F10.44"),
}

EMPTYCMP = re.compile(r"(?:[=!]=\s*@\(\s*\))|(?:@\(\s*\)\s*[=!]=)")
SPAWNBIND = re.compile(r"let\s+(\w+)\s*=\s*process\.spawn\(")
MTSUBJ = re.compile(r"\bmt\s+")
OKPASS = re.compile(r"\{\s*\$ok:(\w+)\s+(\w+)\s*;\s*\$err:\w+\s+")


def line_of(raw: str, pos: int) -> int:
    return raw.count("\n", 0, pos) + 1


def balanced_end(raw: str, start: int, open_: str, close: str) -> int:
    """Index just past the bracket that closes the one at start."""
    depth = 0
    i = start
    while i < len(raw):
        c = raw[i]
        if c == '"':
            i += 1
            while i < len(raw) and raw[i] != '"':
                i += 2 if raw[i] == "\\" else 1
        elif c == open_:
            depth += 1
        elif c == close:
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return len(raw)


def err_value(raw: str, pos: int) -> str:
    """The text of the $err arm's value starting at pos, up to the match's closing brace."""
    end = balanced_end(raw, raw.rfind("{", 0, pos), "{", "}")
    return raw[pos:end - 1].strip().rstrip(";").strip()


def scan(raw: str) -> list[tuple[int, str]]:
    incomment = comment_mask(raw)
    hits: list[tuple[int, str]] = []
    for m in EMPTYCMP.finditer(raw):
        if not incomment[m.start()]:
            hits.append((line_of(raw, m.start()),
                         "compares with `@()`: an array `==` is a pointer compare against a "
                         "fresh allocation, so it is never true and the failure is never seen"))
    spawned = {b.group(1) for b in SPAWNBIND.finditer(raw) if not incomment[b.start()]}
    for m in MTSUBJ.finditer(raw):
        if incomment[m.start()]:
            continue
        j = m.end()
        if raw.startswith("process.spawn(", j):
            k = balanced_end(raw, j + len("process.spawn"), "(", ")")
        else:
            nm = re.match(r"(\w+)\s*\{", raw[j:])
            if not nm or nm.group(1) not in spawned:
                continue
            k = j + len(nm.group(1))
        ok = OKPASS.match(raw, k) or OKPASS.match(raw, k + len(raw[k:]) - len(raw[k:].lstrip()))
        if not ok or ok.group(1) != ok.group(2):
            continue
        val = err_value(raw, ok.end())
        if val != "0":
            hits.append((line_of(raw, m.start()),
                         f"spawn passes the handle through but its $err arm is `{val[:40]}`: "
                         "that is read as a handle; use 0, the NULL handle, and test h==0"))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages", "tests", "scripts"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    total = 0
    seen: dict[str, int] = {}
    for root in args.roots:
        base = pathlib.Path(root) if pathlib.Path(root).is_absolute() else REPO / root
        if base.is_file():
            files = [base]
        elif base.is_dir():
            files = sorted(base.rglob("*.tk"))
        else:
            continue
        for f in files:
            rel = f.relative_to(base.parent if base.is_file() else base)
            if any(x in rel.parts for x in ("_archived-tests", "build", ".claude", "node_modules")):
                continue
            shown = str(f.relative_to(REPO)) if f.is_relative_to(REPO) else str(f)
            hits = scan(f.read_text(errors="replace"))
            if not hits:
                continue
            seen[shown] = len(hits)
            if shown in KNOWN and len(hits) <= KNOWN[shown][0]:
                continue
            for ln, why in hits:
                print(f"  {shown}:{ln}: {why}")
                total += 1
    for path, (cap, owner) in KNOWN.items():
        n = seen.get(path, 0)
        if n < cap:
            print(f"  note: known exception {path} now has {n} of {cap} allowed; "
                  f"lower its cap ({owner})", file=sys.stderr)
    if total == 0:
        print("find_empty_array_sentinel: OK — every spawn failure is a NULL handle that is tested.")
        return 0
    print(f"\n{total} site(s). Use `$err:e 0` and test `h==0`, or handle the failure inside the "
          f"$err arm.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
