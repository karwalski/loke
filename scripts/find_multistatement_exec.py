#!/usr/bin/env python3
"""Find a `db.exec` whose SQL holds more than one statement (story GA5.18).

Why this exists
---------------
`std.db.exec` is `sqlite3_prepare_v2` plus step, and it **discards the tail pointer**.
`prepare_v2` compiles the FIRST statement of the string it is handed and returns a pointer
to whatever follows; a binding that ignores that pointer applies statement one, never sees
statements two onward, and reports success for the lot.

Found 2026-09-23 while writing the GA5.9 append-only triggers: a migration that read

    CREATE TABLE x (...); CREATE INDEX ix_x ON x(...);

created the table, skipped the index, and reported that the migration had applied. The
work-around in `storage/migrations.tk` is one statement per migration, and it is documented
there — but a work-around in one file is not a guard, and nothing in this repository was
looking for the next occurrence. This is that guard.

It is also worth an upstream note in its own right. An interface that accepts a
multi-statement string and silently runs one of them cannot express what it does: the same
family as T-23 and T-36, where the declared shape and the real behaviour disagree and the
compiler has nothing to say about it.

What it flags
-------------
A `db.exec(...)` (or `.exec(` on any alias bound to `std.db`) whose SQL argument contains a
`;` that is not the final character of the statement. Three forms are resolved:

  1. A string literal argument, the common case.
  2. `str.concat(...)` / `str.join(...)` nests — every literal inside the argument is
     examined, and a `;` at the very end of one fragment is still a separator when another
     fragment follows it.
  3. A bare call or identifier, e.g. `db.exec(upsertsql();@(...))`. The referenced function
     is looked up **in the same file** and its returned literals examined. If it cannot be
     resolved the site is reported as INDETERMINATE and does not fail the check — a guard
     that fails on what it cannot see gets switched off.

Deliberately NOT flagged:

  - A trailing `;` on a single statement. It is legal and idiomatic, and `prepare_v2` is
    perfectly happy with it.
  - A `;` inside a quoted SQL string or an SQL comment (`--` to end of line). A default
    value of `';'` is not a statement separator.
  - `proc.exec`, `sh.exec` and anything else whose last segment happens to be `exec` — the
    alias must resolve to `std.db` through an `i=` line in the file.

    python3 scripts/find_multistatement_exec.py --check packages tests
    python3 scripts/find_multistatement_exec.py packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

IMPORT = re.compile(r"^\s*i=([A-Za-z_][A-Za-z0-9_]*)\s*:\s*std\.db\s*;", re.M)
# core.storage.db.exec and .execparams are pass-throughs to std.db.exec, so a multi-statement
# string handed to either is the same defect one call deeper. Without this the ten sites this
# check could not read were all pass-through wrappers, which is to say the check was blind to
# exactly the layer most callers actually use.
DBMOD = re.compile(r"^\s*i=([A-Za-z_][A-Za-z0-9_]*)\s*:\s*core\.storage\.db\s*;", re.M)
FUNCDEF = re.compile(r"^f=([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)", re.M)


def comment_mask(text: str) -> list[bool]:
    """True at every index that is inside a toke comment.

    Comments NEST (T-27) and a string may contain the two characters `(*` — an
    `"INSERT ... VALUES (*)"` would otherwise open a comment that swallows the rest of the
    file. Strings are skipped first, then comment depth is tracked.
    """
    mask = [False] * len(text)
    depth = 0
    i = 0
    while i < len(text):
        if depth == 0 and text[i] == '"':
            i += 1
            while i < len(text):
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if text.startswith("(*", i):
            depth += 1
            mask[i] = mask[i + 1] = True
            i += 2
            continue
        if text.startswith("*)", i) and depth > 0:
            mask[i] = mask[i + 1] = True
            depth -= 1
            i += 2
            continue
        if depth > 0:
            mask[i] = True
        i += 1
    return mask


def literals_in(text: str) -> list[str]:
    """Every toke string literal in `text`, unescaped enough to read the SQL."""
    out = []
    i = 0
    while i < len(text):
        if text[i] != '"':
            i += 1
            continue
        i += 1
        buf = []
        while i < len(text):
            if text[i] == "\\":
                # \" and \\ are the ones that matter for reading SQL; \n and friends are
                # whitespace and are kept as a space so a separator is not welded to a word.
                nxt = text[i + 1] if i + 1 < len(text) else ""
                buf.append(nxt if nxt in ('"', "\\") else " ")
                i += 2
                continue
            if text[i] == '"':
                i += 1
                break
            buf.append(text[i])
            i += 1
        out.append("".join(buf))
    return out


def strip_sql_noise(sql: str) -> str:
    """Blank out SQL string literals and `--` comments, length-preserving.

    Length-preserving so a reported column still points at the right character. A `;` inside
    `DEFAULT ';'` is not a statement separator, and neither is one in a trailing comment.
    """
    out = list(sql)
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]
        if c == "'":
            out[i] = " "
            i += 1
            while i < n:
                if sql[i] == "'":
                    out[i] = " "
                    i += 1
                    # '' is an escaped quote inside an SQL string.
                    if i < n and sql[i] == "'":
                        out[i] = " "
                        i += 1
                        continue
                    break
                out[i] = " "
                i += 1
            continue
        if sql.startswith("--", i):
            while i < n and sql[i] != "\n":
                out[i] = " "
                i += 1
            continue
        i += 1
    return "".join(out)


def separators(sql: str) -> int:
    """Count `;` that separate statements, i.e. that have non-space text after them."""
    clean = strip_sql_noise(sql)
    count = 0
    for m in re.finditer(r";", clean):
        if clean[m.end():].strip():
            count += 1
    return count


def arg_span(text: str, open_paren: int) -> tuple[int, int]:
    """The span inside the parentheses opened at `open_paren`, brackets balanced."""
    depth = 0
    i = open_paren
    n = len(text)
    while i < n:
        c = text[i]
        if c == '"':
            i += 1
            while i < n:
                if text[i] == "\\":
                    i += 2
                    continue
                if text[i] == '"':
                    break
                i += 1
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return open_paren + 1, i
        i += 1
    return open_paren + 1, n


def top_arguments(args: str) -> list[str]:
    """Split on top-level `;` — toke's argument separator."""
    out = []
    depth = 0
    i = 0
    start = 0
    n = len(args)
    while i < n:
        c = args[i]
        if c == '"':
            i += 1
            while i < n:
                if args[i] == "\\":
                    i += 2
                    continue
                if args[i] == '"':
                    break
                i += 1
        elif c in "([{":
            depth += 1
        elif c in ")]}":
            depth -= 1
        elif c == ";" and depth == 0:
            out.append(args[start:i])
            start = i + 1
        i += 1
    out.append(args[start:])
    return out


def first_argument(args: str) -> str:
    """The text before the first top-level `;` — toke's argument separator."""
    depth = 0
    i = 0
    n = len(args)
    while i < n:
        c = args[i]
        if c == '"':
            i += 1
            while i < n:
                if args[i] == "\\":
                    i += 2
                    continue
                if args[i] == '"':
                    break
                i += 1
        elif c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == ";" and depth == 0:
            return args[:i]
        i += 1
    return args


def params_of(decl: str) -> list[str]:
    """Parameter NAMES of an `f=` declaration's captured parameter list."""
    out = []
    for part in decl.split(";"):
        nm = part.split(":")[0].strip()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", nm):
            out.append(nm)
    return out


def function_bodies(text: str, mask: list[bool]) -> dict[str, str]:
    """name -> body text, for every `f=` in the file. Used to resolve `db.exec(sqlfn())`."""
    out: dict[str, str] = {}
    for m in FUNCDEF.finditer(text):
        if mask[m.start()]:
            continue
        brace = text.find("{", m.end())
        if brace < 0:
            continue
        # Braces walked directly: arg_span is parenthesis-shaped.
        depth = 0
        i = brace
        n = len(text)
        while i < n:
            if text[i] == '"':
                i += 1
                while i < n:
                    if text[i] == "\\":
                        i += 2
                        continue
                    if text[i] == '"':
                        break
                    i += 1
            elif text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        out[m.group(1)] = (brace, i, text[brace:i])
    return out


def enclosing_body(bodies: dict[str, tuple[int, int, str]], offset: int) -> str:
    """The body text of the function containing `offset`, or "" if none does."""
    for _, (lo, hi, body) in bodies.items():
        if lo <= offset <= hi:
            return body
    return ""


LET = re.compile(r"\blet\s+(?:mut\.)?([A-Za-z_][A-Za-z0-9_]*)\s*=")


def local_binding(body: str, name: str) -> str | None:
    """The initialiser text of `let <name>=...` in `body`, to its top-level terminator.

    This is what makes the check see most of its subjects: the prevailing idiom is
    `let sql=str.concat(...)` on one line and `db.exec(sql;@(...))` on the next, and the
    argument alone carries no SQL at all. Resolving one level of local binding took the
    number of sites this check can actually read from 5 to 30.
    """
    best = None
    for m in LET.finditer(body):
        if m.group(1) != name:
            continue
        i = m.end()
        depth = 0
        n = len(body)
        while i < n:
            c = body[i]
            if c == '"':
                i += 1
                while i < n:
                    if body[i] == "\\":
                        i += 2
                        continue
                    if body[i] == '"':
                        break
                    i += 1
            elif c in "([{":
                depth += 1
            elif c in ")]}":
                if depth == 0:
                    break
                depth -= 1
            elif c == ";" and depth == 0:
                break
            i += 1
        best = body[m.end():i]
    return best


def scan(path: pathlib.Path) -> tuple[list[tuple[int, str, int, str]], list[tuple[int, str]]]:
    text = path.read_text(errors="replace")
    aliases = set(IMPORT.findall(text)) | set(DBMOD.findall(text))
    if not aliases:
        return [], []
    mask = comment_mask(text)
    bodies = function_bodies(text, mask)

    # A same-file pass-through: a function that hands one of its OWN parameters straight to
    # exec. Its callers are the real subjects, so the parameter's position is recorded and
    # calls to it are scanned at that position. tests/unit/memory/test_search.tk's `exec`,
    # storage/db.tk's `exec`/`execparams` and memory/schema.tk's `execok` are all this shape.
    passthrough: dict[str, int] = {}
    for fm in FUNCDEF.finditer(text):
        if mask[fm.start()] or fm.group(1) not in bodies:
            continue
        names = params_of(fm.group(2))
        body = bodies[fm.group(1)][2]
        for a in aliases:
            for pm in re.finditer(re.escape(a) + r"\.exec(?:params)?\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*[;)]", body):
                if pm.group(1) in names:
                    passthrough[fm.group(1)] = names.index(pm.group(1))

    hits: list[tuple[int, str, int, str]] = []
    unknown: list[tuple[int, str]] = []

    def sql_of(expr: str, body: str, depth: int = 0) -> tuple[str, str] | None:
        """(sql, how) for an argument expression, resolving one level of indirection.

        Returns None when the SQL cannot be seen from this file, which is reported as
        indeterminate rather than failing the check.
        """
        lits = literals_in(expr)
        if lits:
            return "".join(lits), ""
        if depth > 1:
            return None
        ref = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*\)\s*$", expr)
        if ref and ref.group(1) in bodies:
            inner = "".join(literals_in(bodies[ref.group(1)][2]))
            return (inner, f"{ref.group(1)}() -> ") if inner else None
        ident = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*$", expr)
        if ident and body:
            init = local_binding(body, ident.group(1))
            if init is not None:
                got = sql_of(init, body, depth + 1)
                if got:
                    return got[0], f"{ident.group(1)} = "
        return None

    call = re.compile(r"\b(" + "|".join(re.escape(a) for a in aliases) + r")\.exec(?:params)?\s*\(")
    for m in call.finditer(text):
        if mask[m.start()]:
            continue
        lo, hi = arg_span(text, m.end() - 1)
        argv = top_arguments(text[lo:hi])
        line = text.count("\n", 0, m.start()) + 1
        body = enclosing_body(bodies, m.start())

        # Two call shapes are in use: exec(sql;params) and exec(conn;sql;params) — see
        # storage/backup.tk:58 and browser/src/tabs.tk:18. So the first argument that yields
        # SQL wins, and a connection handle in slot one simply yields nothing.
        got = None
        for arg in argv[:2]:
            got = sql_of(arg, body)
            if got:
                shown = arg.strip()[:70]
                break
        if not got:
            unknown.append((line, argv[0].strip()[:70]))
            continue

        sql, how = got
        n = separators(sql)
        if n:
            hits.append((line, f"{how}{shown}", n, sql.strip()[:110]))

    for fname, idx in sorted(passthrough.items()):
        # `(?<!f=)` skips the declaration itself: `f=exec(sql:str)` matches the call shape
        # otherwise, and its "argument" is the parameter list, which is never resolvable and
        # so reported every wrapper as an indeterminate site of its own.
        for cm in re.finditer(r"(?<![\w.])(?<!f=)" + re.escape(fname) + r"\s*\(", text):
            if mask[cm.start()]:
                continue
            lo, hi = arg_span(text, cm.end() - 1)
            argv = top_arguments(text[lo:hi])
            if len(argv) <= idx:
                continue
            line = text.count("\n", 0, cm.start()) + 1
            got = sql_of(argv[idx], enclosing_body(bodies, cm.start()))
            if not got:
                unknown.append((line, f"{fname}(...) arg {idx + 1}: {argv[idx].strip()[:50]}"))
                continue
            sql, how = got
            n = separators(sql)
            if n:
                hits.append((line, f"{fname}(...) <- {how}{argv[idx].strip()[:50]}", n,
                             sql.strip()[:110]))

    # The migration table is where this defect was found, and `db.exec(mg.sql;...)` reads a
    # field of a struct built in another module — invisible from the call site. So any
    # `sql:` field initialiser is checked where it is WRITTEN, which is where a two-statement
    # migration would be introduced.
    for fm in re.finditer(r"\bsql\s*:\s*", text):
        if mask[fm.start()]:
            continue
        rest = text[fm.end():]
        stop = len(rest)
        d = 0
        i = 0
        while i < len(rest):
            c = rest[i]
            if c == '"':
                i += 1
                while i < len(rest):
                    if rest[i] == "\\":
                        i += 2
                        continue
                    if rest[i] == '"':
                        break
                    i += 1
            elif c in "([{":
                d += 1
            elif c in ")]}":
                if d == 0:
                    stop = i
                    break
                d -= 1
            elif c == ";" and d == 0:
                stop = i
                break
            i += 1
        expr = rest[:stop]
        sql = "".join(literals_in(expr))
        if not sql:
            continue
        n = separators(sql)
        if n:
            line = text.count("\n", 0, fm.start()) + 1
            hits.append((line, "sql: field initialiser", n, sql.strip()[:110]))

    return hits, unknown


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages", "tests"])
    ap.add_argument("--check", action="store_true", help="exit 1 on any multi-statement site")
    ap.add_argument("--verbose", action="store_true",
                    help="also list sites whose SQL could not be resolved")
    args = ap.parse_args()

    total = 0
    indet = 0
    for root in args.roots:
        # An absolute root is used as given, so the fixture that proves this check can fail
        # can live outside the repository. A check whose failing case is not demonstrable is
        # the fourth thing in this repository that could not fail; see the header of
        # scripts/quality-gate.sh.
        base = pathlib.Path(root) if pathlib.Path(root).is_absolute() else REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.tk")):
            if any(x in f.parts for x in ("build", "_archived-tests")):
                continue
            hits, unknown = scan(f)
            try:
                rel = str(f.relative_to(REPO))
            except ValueError:
                rel = str(f)
            for line, argtext, n, sql in hits:
                print(f"  {rel}:{line}  {argtext}")
                print(f"      {n} statement separator(s) in the SQL — only the FIRST "
                      f"statement is applied, and exec reports success for all of them")
                print(f"      SQL: {sql}")
                total += 1
            if args.verbose:
                for line, argtext in unknown:
                    print(f"  {rel}:{line}  INDETERMINATE (SQL not resolvable here): {argtext}")
            indet += len(unknown)

    if total == 0:
        print(f"find_multistatement_exec: OK — every db.exec applies one statement "
              f"({indet} site(s) whose SQL is built elsewhere, reported with --verbose).")
        return 0
    print(f"\n{total} db.exec site(s) pass more than one statement. std.db.exec discards "
          f"prepare_v2's tail pointer, so everything after the first `;` is silently not "
          f"applied — split them into one exec per statement (see storage/migrations.tk).",
          file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
