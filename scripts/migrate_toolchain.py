#!/usr/bin/env python3
"""Apply the toke/ooke 3.0.0-rc.1 API migrations, driven by the compiler (F10.7).

Why driven by the compiler
--------------------------
A repo-wide regex rewriter already did damage in this project once: it silently
deleted the Apache licence header from 520 files, and story F10.6 removed it on the
grounds that "a repo-wide destructive rewriter is a standing hazard whether or not
its regex is fixed". So this does not grep for patterns.

Instead it reads `build/break-report.txt` — toke's own JSON diagnostics, with a
file, a line and an error class — and edits only the exact lines the compiler
objected to. A line the compiler did not complain about is never touched. Each
migration is a named function, is applied only to its own error class, and refuses
to edit a line that does not match the shape it expects.

Always run with --dry-run first. Every pass prints what it would change.

Usage
-----
    python3 scripts/migrate_toolchain.py --list
    python3 scripts/migrate_toolchain.py --pass log-arity --dry-run
    python3 scripts/migrate_toolchain.py --pass log-arity
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REPORT = REPO / "build" / "break-report.txt"


def diagnostics() -> list[dict]:
    if not REPORT.exists():
        raise SystemExit(f"{REPORT} not found. Run scripts/build_loke.sh first.")
    out = []
    for line in REPORT.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except Exception:
            continue
        if d.get("severity") == "error":
            out.append(d)
    return out


def close_paren(s: str, open_idx: int) -> int:
    """Index of the ')' matching the '(' at open_idx, or -1.

    String-aware: a parenthesis inside a double-quoted literal does not count, and
    a backslash escape is honoured. Without that, a call containing "(" in a SQL
    string would be mis-balanced and the edit would land in the wrong place.
    """
    depth = 0
    in_str = False
    i = open_idx
    while i < len(s):
        c = s[i]
        if in_str:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    return i
        i += 1
    return -1



def span_of(lines: list[str], start: int, limit: int = 40) -> int | None:
    """Last line index of the call beginning on `start`.

    Balances parentheses from the first '(' on the starting line, string-aware, so
    a SQL literal containing a bracket does not end the span early. Returns None if
    the call does not close within `limit` lines, which means the shape is not what
    this script expects and a human should look.
    """
    text = lines[start]
    if "(" not in text:
        return None
    for end in range(start, min(start + limit, len(lines))):
        joined = "\n".join(lines[start:end + 1])
        open_idx = joined.index("(")
        if close_paren(joined, open_idx) >= 0:
            return end
    return None

# ── Passes ────────────────────────────────────────────────────────────────
# Each returns the new line, or None to decline. Declining is normal and safe:
# the line is left for a human and reported.

LOG_FNS = ("log.info", "log.warn", "log.error", "log.debug", "log.trace")


def log_arity(line: str, diag: dict) -> str | None:
    """std.log.* takes (message, fields). Add the empty field array.

    Only where the compiler says the call passes exactly one argument, and only to
    the call it named — several log calls can share a line.
    """
    if diag.get("got") != "1":
        return None
    fn = next((f for f in LOG_FNS if f + "(" in line), None)
    if fn is None:
        return None
    start = line.index(fn + "(")
    open_idx = start + len(fn)
    end = close_paren(line, open_idx)
    if end < 0:
        return None
    inner = line[open_idx + 1:end]
    # A second argument already present means this is not the call at fault.
    if inner.rstrip().endswith("@()"):
        return None
    return line[:end] + ";@()" + line[end:]


def http_post_arity(line: str, diag: dict) -> str | None:
    """std.http.postheaders takes (client, url, body, headers).

    loke calls it with three: url, body, headers. The client argument is new, and
    there is no client value in scope at these call sites, so this pass does NOT
    invent one — it declines and reports. Guessing a client handle would produce
    code that compiles and sends nothing.
    """
    return None


def process_spawn_arity(line: str, diag: dict) -> str | None:
    """std.process.spawn takes a single [str] argv array.

    loke calls spawn("cmd"; @("arg")). The migration is to fold the command into
    the array: spawn(@("cmd";"arg")).
    """
    if diag.get("expected") != "1":
        return None
    if "process.spawn(" not in line:
        return None
    start = line.index("process.spawn(")
    open_idx = start + len("process.spawn")
    end = close_paren(line, open_idx)
    if end < 0:
        return None
    inner = line[open_idx + 1:end]
    # Split on the top-level ';' only.
    parts = split_top(inner)
    if len(parts) != 2:
        return None
    cmd, rest = parts[0].strip(), parts[1].strip()
    if not rest.startswith("@("):
        return None
    args_inner = rest[2:-1].strip() if rest.endswith(")") else None
    if args_inner is None:
        return None
    merged = f"@({cmd})" if not args_inner else f"@({cmd};{args_inner})"
    return line[:open_idx + 1] + merged + line[end:]


def split_top(s: str) -> list[str]:
    """Split on ';' at depth zero, string-aware."""
    parts, depth, in_str, cur = [], 0, False, []
    i = 0
    while i < len(s):
        c = s[i]
        if in_str:
            cur.append(c)
            if c == "\\":
                if i + 1 < len(s):
                    cur.append(s[i + 1])
                    i += 2
                    continue
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
                cur.append(c)
            elif c in "([{":
                depth += 1
                cur.append(c)
            elif c in ")]}":
                depth -= 1
                cur.append(c)
            elif c == ";" and depth == 0:
                parts.append("".join(cur))
                cur = []
            else:
                cur.append(c)
        i += 1
    parts.append("".join(cur))
    return parts


def return_type(block: str, diag: dict) -> str | None:
    """A function declared :i64 that returns a struct.

    The compiler's own `fix` field says "cast return value to i64 using 'as'". That
    advice is wrong and worth naming: casting a struct to an integer would compile
    and destroy the value. The declaration is what is wrong, not the return.

    This pass is handled specially by run(), which passes the whole enclosing
    function declaration line rather than the erroring line — see RETURN_TYPE_PASS.
    """
    msg = diag.get("message", "")
    if "expected 'i64', got '" not in msg:
        return None
    got = msg.split("got '")[1].rstrip("'")
    if not got or " " in got:
        return None
    # :i64{  ->  :$type{     and  :i64!$err{ -> :$type!$err{
    if "):i64!" in block:
        return block.replace("):i64!", f"):${got}!", 1)
    if "):i64{" in block:
        return block.replace("):i64{", f"):${got}{{", 1)
    return None


def db_redesign(line: str, diag: dict) -> str | None:
    """std.db lost its connection argument.

        db.execparams(conn; sql; params)  ->  db.exec(sql; params)
        db.queryparams(conn; sql; params) ->  db.many(sql; params)
        db.query(conn; sql)               ->  db.many(sql; @())

    The connection is now module-level state established by db.open, so the first
    argument is dropped rather than moved.
    """
    for old, new, wants_params in (("db.execparams", "db.exec", True),
                                   ("db.queryoneparams", "db.one", True),
                                   ("db.queryparams", "db.many", True),
                                   ("db.queryone", "db.one", False),
                                   ("db.query", "db.many", False)):
        if old + "(" not in line:
            continue
        start = line.index(old + "(")
        open_idx = start + len(old)
        end = close_paren(line, open_idx)
        if end < 0:
            return None
        parts = split_top(line[open_idx + 1:end])
        if wants_params:
            if len(parts) != 3:
                return None
            inner = f"{parts[1].strip()};{parts[2].strip()}"
        else:
            if len(parts) != 2:
                return None
            inner = f"{parts[1].strip()};@()"
        return line[:start] + new + "(" + inner + line[end:]
    return None


def str_concat_arity(line: str, diag: dict) -> str | None:
    """str.concat is binary. A 3-argument call becomes a nested pair.

    Declines anything with more than three, and anything it cannot split cleanly:
    deeply nested concat chains are better rewritten as str.join by hand than
    unrolled by a script.
    """
    if "str.concat(" not in line:
        return None
    start = line.index("str.concat(")
    open_idx = start + len("str.concat")
    end = close_paren(line, open_idx)
    if end < 0:
        return None
    parts = split_top(line[open_idx + 1:end])
    if len(parts) != 3:
        return None
    a, b, c = (p.strip() for p in parts)
    return (line[:start] + f"str.concat({a};str.concat({b};{c}))" + line[end:])


PASSES = {
    "log-arity": ("std.log.* needs its fields array", "unclassified-E4026",
                  lambda d: "std.log." in d.get("message", ""), log_arity),
    "db-redesign": ("std.db lost the connection argument", "db-redesign",
                    lambda d: "std.db." in d.get("message", "")
                    and d.get("error_code") == "E4026", db_redesign),
    "process-spawn": ("std.process.spawn takes one argv array", "process-spawn-arity",
                      lambda d: "std.process.spawn" in d.get("message", ""),
                      process_spawn_arity),
    "str-concat": ("str.concat is binary", "str-concat-arity",
                   lambda d: "std.str.concat" in d.get("message", ""),
                   str_concat_arity),
    "return-type": ("a function declared :i64 that returns a struct", "return-type",
                    lambda d: d.get("error_code") == "E4031"
                    and "expected 'i64', got '$" not in d.get("message", "")
                    and "expected 'i64', got '" in d.get("message", ""), return_type),
    "http-post": ("std.http.post* arity — reports only, does not guess a client",
                  "http-post-arity",
                  lambda d: "std.http.post" in d.get("message", ""), http_post_arity),
}


def run(pass_name: str, dry: bool) -> int:
    label, _, match, fn = PASSES[pass_name]
    diags = [d for d in diagnostics() if match(d)]
    if not diags:
        print(f"{pass_name}: no matching diagnostics")
        return 0

    # Group by file, and apply from the bottom up so earlier line numbers stay valid.
    by_file: dict[str, list[dict]] = collections.defaultdict(list)
    for d in diags:
        by_file[d["file"]].append(d)

    changed = declined = 0
    for path, ds in sorted(by_file.items()):
        p = pathlib.Path(path)
        if not p.is_absolute():
            p = REPO / path
        if not p.exists():
            # Diagnostics for ooke-relative paths (pages/api/x.tk) resolve against
            # the package directory, not the repo root. Reported, not guessed at.
            print(f"  ? cannot locate {path}")
            declined += len(ds)
            continue
        lines = p.read_text().split("\n")
        # Edits operate on the whole CALL, which may span several lines: 66 of the
        # 126 db diagnostics point at a line ending in "db.execparams(" with the
        # arguments below it. A single-line rewriter silently declined every one of
        # those, which would have looked like less work rather than missed work.
        #
        # Bottom-up so earlier line numbers stay valid, and deduplicated because
        # several diagnostics often name the same call.
        seen = set()
        for d in sorted(ds, key=lambda x: -x["pos"]["line"]):
            ln = d["pos"]["line"] - 1
            if ln in seen or ln < 0 or ln >= len(lines):
                continue
            if pass_name == "return-type":
                # Walk back to the enclosing `f=` declaration: the defect is there,
                # not on the line that returns.
                decl = None
                for k in range(ln, -1, -1):
                    if lines[k].startswith("f="):
                        decl = k
                        break
                if decl is None:
                    declined += 1
                    continue
                ln, span_end = decl, decl
            else:
                span_end = span_of(lines, ln)
                if span_end is None:
                    declined += 1
                    continue
            block = "\n".join(lines[ln:span_end + 1])
            new_block = fn(block, d)
            if new_block is None or new_block == block:
                declined += 1
                continue
            for k in range(ln, span_end + 1):
                seen.add(k)
            if dry:
                print(f"  {p.relative_to(REPO)}:{ln+1}"
                      f"{'' if span_end == ln else f'-{span_end+1}'}")
                print(f"    - {' '.join(block.split())[:130]}")
                print(f"    + {' '.join(new_block.split())[:130]}")
            lines[ln:span_end + 1] = new_block.split("\n")
            changed += 1
        if not dry and seen:
            p.write_text("\n".join(lines))

    verb = "would change" if dry else "changed"
    print(f"\n{pass_name} ({label}): {verb} {changed} line(s), declined {declined}")
    if declined:
        print("  declined lines are left for a human — the pass refused a shape it "
              "did not recognise rather than guessing")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pass", dest="pass_name", choices=sorted(PASSES))
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()

    if args.list or not args.pass_name:
        print("passes:")
        for name, (label, _, _, _) in sorted(PASSES.items()):
            print(f"  {name:<16} {label}")
        return 0
    return run(args.pass_name, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
