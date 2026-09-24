#!/usr/bin/env python3
"""Classify a tree's build diagnostics so a migration can be worked and measured.

Why this exists
---------------
The first honest build against toke 6cc9061+ and ooke v3.0.0-rc.1 produced
**83 modules compiled, 116 failed, 505 errors**. A list of 505 errors is not a work
plan, and "the build is red" is not a progress measure.

The errors are not 505 problems. They are a handful of upstream API changes multiplied
across call sites: `std.db` was redesigned, `std.http.post` lost two parameters,
integer widths got stricter. This groups them so each class can be fixed once and the
count can be watched going down.

Why it has a tree dimension (F10.23b)
-------------------------------------
Until F10.23 this read one hardcoded `build/break-report.txt`, because there was one
build: the four roots `scripts/build_loke.sh` compiles. The other 247 non-test `.tk`
files in this repository had never been compiled, and measured cold they cost 951
errors across 247 files. Onboarding them one tree at a time needs one baseline per
tree, or the first tree to move would mask the tree that regressed.

Two ratchets, because the trees are in two states:

  * `--check` fails when the error count goes UP. That is the right bar for a tree
    with 553 errors walking down to zero.
  * `--strict` fails on ANY error. That is the right bar for a tree already at zero,
    and it is the only thing that stops `loke` slipping 0 -> 1 unnoticed while `moke`
    is busy going 553 -> 0. An increase-only check cannot see that, because the
    project total still fell.

Why the classes were rewritten (F10.23b)
----------------------------------------
The CLASSES table was written against the May std.db/std.http redesign, on the four
roots that were already being built. On the 247 that were not, ~60% of the errors fell
into `unclassified-*`, which is a number with no work plan attached — the exact
failure this script's own docstring names. What was missing:

  * E2030 (module not found), 94 of the 308 in the old baseline, in two shapes that
    are completely different jobs: a sibling module whose interface was not emitted,
    and a `std.*` module the toolchain does not have at all.
  * `type mismatch: expected 'i64', got 'toolresult'`. The old needle was
    `expected 'i64', got '$` and toke does not print the `$` sigil in that message,
    so the class matched nothing; 11 of the cli/mcp errors sat in unclassified-E4031.
  * `expected 'unknown', got 'str'` and its inverse — 99 errors, and the largest
    single class in the never-compiled trees. An inference failure, not a type error:
    annotating the binding fixes it without changing a value.
  * `std.log.info` arity — 160 errors on their own, one mechanical edit per call site.
  * E4070 (assignment to an immutable binding), E4027 "has no exported member" on a
    loke module, E2004, E2001, E3011, E2002's "unexpected token" and its
    "`=` is assignment; use `==`" variant, and the `expected 'f32'` / same-printed-name
    type mismatches.

With those added, all 771 errors across the four never-compiled targets classify; none
land in `unclassified-*`. The report prints the unclassified share explicitly so the
next gap is visible rather than inferred.

E2030 is also refined against the repository: the module name is pulled out of the
message and looked up among every `m=` declaration in `src/` and `packages/`. A module
that exists needs an interface pass or a wider root list; a module that does not exist
needs the import deleted or the module written. Those are not the same work and they
should not be one number.

What it measures / does not measure
-----------------------------------
It measures the count and the shape of what the compiler rejected, plus the undefined
symbols scripts/symbol_census.py attributed (they ratchet in the same baseline, as
their own class, because an unknown method call is not a compile error in toke — it is
a link error, and it is only visible once the tree compiles).

It does NOT measure correctness. A tree at zero errors has been type-checked, nothing
more. It also cannot see anything in a module that failed to compile: a module with no
object contributes no symbols, so a FALLING error count can raise the undefined-symbol
count. Both halves are baselined for exactly that reason.

Usage
-----
    python3 scripts/build_census.py                      # build/break-report.txt
    python3 scripts/build_census.py --tree moke          # build/trees/moke/...
    python3 scripts/build_census.py --tree moke --by-file
    python3 scripts/build_census.py --tree moke --baseline   # record the count
    python3 scripts/build_census.py --tree moke --check      # fail if it went UP
    python3 scripts/build_census.py --tree loke --strict     # fail on ANY error
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# Each class is one upstream change or one defect shape, with the migration it
# implies. Matched on the error code plus a substring, IN ORDER, so the first match
# wins and the specific classes must precede the general ones.
CLASSES = [
    # ── the May std.db / std.http redesign ───────────────────────────────────
    ("db-redesign", "E4026", "std.db.",
     "std.db was redesigned: db.exec/one/many take (sql, params) with no connection "
     "argument. db.execparams -> db.exec, db.queryparams -> db.many, "
     "db.query(conn,sql) -> db.many(sql,@())."),
    ("db-row-access", "E4031", "cannot index into 'i64'",
     "A query used to return an opaque i64. db.many now returns [Row]; read columns "
     "with row.str/i64/u64/f64/bool(r, name), each of which returns a result to match."),
    ("db-member-gone", "E4027", "'std.db' has no member",
     "The old db member no longer exists. See stdlib/db.tki for the current exports."),
    ("http-post-arity", "E4026", "std.http.post",
     "std.http.post takes (url, body). Headers and content type moved; use "
     "http.postheaders where headers are needed."),
    ("log-arity", "E4026", "for 'std.log.",
     "std.log.info/warn/debug/error take TWO arguments (message, fields), not three. "
     "The third argument was a correlation id; it moved into the fields map. This is "
     "160 of the legacy tree's errors on its own and is one mechanical edit per call "
     "site — do it first, because it hides everything else in those files."),
    ("process-spawn-arity", "E4026", "std.process.spawn",
     "std.process.spawn takes one argument."),
    ("str-concat-arity", "E4026", "std.str.concat",
     "str.concat is binary. Nested calls, or str.join."),

    # ── imports (F10.23b). Refined against the repo by refine_e2030(). ───────
    ("stdlib-module-absent", "E2030", "standard-library module",
     "toke's stdlib has no such module. Nothing in loke can fix this: it is an "
     "upstream ask (see UPSTREAM.md). packages/browser/src/shell.tk imports "
     "std.webview, which is why the browser-app target is check-only."),
    ("module-not-found", "E2030", "not found",
     "An import did not resolve. refine_e2030() splits this by whether the repository "
     "declares the module; if you are reading this label, the message did not carry a "
     "quoted module name."),

    # ── type errors ──────────────────────────────────────────────────────────
    ("struct-offset", "E4034", "declared at different offsets",
     "The same field name is declared at different offsets by two struct types, so "
     "the compiler cannot resolve the access. Give the local a declared type, or "
     "align the structs."),
    ("int-width", "E4031", "expected 'i32'",
     "Integer widths are stricter. Cast explicitly with 'as'."),
    ("int-width", "E4031", "expected 'u32'",
     "Integer widths are stricter. Cast explicitly with 'as'."),
    ("int-width", "E4031", "expected 'u64'",
     "Integer widths are stricter. Cast explicitly with 'as'."),
    ("float-width", "E4031", "expected 'f32'",
     "Float widths are stricter too; 'as f32' at the call site. Check whether the "
     "declaration should be f64 instead — narrowing a measurement to f32 to satisfy "
     "the compiler loses precision silently."),
    ("type-not-inferred", "E4031", "'unknown'",
     "The compiler could not infer one side's type and printed it as 'unknown'. This "
     "is the single largest class across the never-compiled trees (99 of 771). It is "
     "not a type error in the usual sense: annotate the binding (let x:str=...) or "
     "the function's parameter/return, and the error goes away without changing any "
     "value. Most cases are a let bound to a match expression or to an empty array "
     "literal."),
    ("return-type", "E4031", "expected 'i64', got '",
     "A function declared -> i64 returns a struct. Declare the real return type. The "
     "old needle here was \"got '$\" and toke prints the struct name WITHOUT the "
     "sigil (\"got 'toolresult'\"), so this class matched nothing and 11 of the "
     "cli/mcp errors were filed as unclassified-E4031."),
    ("array-elem-mismatch", "E4031", "expected 'array', got 'array'",
     "Two array types with different element types, both printed as 'array'. The "
     "message cannot tell you which; check the element type of each side. Usually a "
     "[str] passed where [Row] or a struct array is wanted."),
    ("same-name-type-mismatch", "E4031", "expected 'str', got 'str'",
     "Two types the compiler prints with the SAME name and still considers unequal — "
     "usually a str vs a str-typed alias or a struct field read through a differently "
     "declared local. The diagnostic cannot distinguish them; give the local an "
     "explicit declared type so both sides name the same one."),
    ("immutable-assign", "E4070", "",
     "Assignment to an immutable binding. Declare it with 'let x=mut.<value>'. Scan "
     "the WHOLE function: every 'let X=' whose X is later reassigned needs it, and "
     "fixing one at a time re-triggers the error on the next."),
    ("undeclared-identifier", "E3011", "",
     "Identifier not declared in scope. Often a match arm binding used outside its "
     "arm, or a variable declared inside an if/loop body and read after it."),

    # ── ooke and loke's own interfaces ───────────────────────────────────────
    ("ooke-member", "E4027", "'ooke.",
     "An ooke module member moved or was renamed in 3.0.0-rc.1."),
    ("interface-arity", "E4026", "the interface d",
     "A loke .tki interface disagrees with its implementation."),
    ("loke-member-missing", "E4027", "has no exported member",
     "A loke module is being called for a function it does not export. Either the "
     "function was renamed/removed and the caller was not updated, or the .tki in "
     "build/trees/<tree>/interfaces is stale — the interface pass rebuilds it from "
     "scratch every run, so a stale one means the owning module failed to compile."),

    # ── general stdlib drift: these must stay AFTER the std.db/std.http ──────
    #    classes above, which are the same codes with a narrower needle.
    ("stdlib-member-gone", "E4027", "module 'std.",
     "A std.* member does not exist: neither the interface nor the runtime declares "
     "it. toke does not check an unknown module member at --check time, so these are "
     "found only by a real compile — and an unknown METHOD is not found even then, it "
     "becomes an undefined symbol at link (see scripts/symbol_census.py). Check the "
     "module's .tki in $TOKE_DIR/stdlib for the current exports."),
    ("stdlib-arity", "E4026", "for 'std.",
     "A std.* function is being called with the wrong number of arguments. The "
     "diagnostic names the real arity; check the .tki in $TOKE_DIR/stdlib."),

    # ── parse ────────────────────────────────────────────────────────────────
    ("missing-semicolon", "E2003", "",
     "Parse error: missing semicolon."),
    ("unclosed-delimiter", "E2004", "",
     "Parse error: unclosed delimiter. The reported line is where the parser gave up, "
     "not always where the delimiter opened."),
    ("decl-order", "E2001", "",
     "Declaration ordering violation. toke requires m=, then i=, then types, then "
     "functions; a declaration appears after something that must follow it."),
    ("assign-vs-equality", "E2002", "use `==` for equality",
     "`=` is assignment in toke; `==` is equality. One character per site, and the "
     "parser reports it at the condition rather than where the intent went wrong."),
    ("parse-unexpected-token", "E2002", "unexpected token",
     "Parse error: unexpected token. This is the largest single class in the cli and "
     "mcp trees (15 of 88) and is not one defect — read each one. Common causes here: "
     "'mut' where 'mut.' is meant, and '=' inside a call's argument list."),
    ("parse", "E2002", "",
     "Parse error."),
]

# The class scripts/symbol_census.py contributes. Not a compile error: toke does not
# check an unknown method call at all, so it survives until the link.
SYMBOL_CLASS = "undefined-symbol"
SYMBOL_ADVICE = (
    "An unknown method call. toke does not check it at compile time; it becomes an "
    "undefined symbol at link time. scripts/symbol_census.py attributes each one to "
    "the module that calls it and splits them three ways: a stdlib module the "
    "toolchain lacks (upstream ask), a module that exists but has no such function, "
    "and a module nothing declares. Read build/trees/<tree>/symbol-census.json.")

MODNAME_RE = re.compile(r"module '([A-Za-z0-9_.]+)'")
M_DECL_RE = re.compile(r"^m=([A-Za-z0-9_.]+)\s*;", re.M)


def paths(tree: str | None) -> tuple[pathlib.Path, pathlib.Path, pathlib.Path]:
    """(break report, baseline, symbol census) for a tree, or the legacy paths.

    With no --tree the legacy locations are used unchanged: build/break-report.txt is
    where CI uploads the artifact from and where scripts/quality-gate.sh expects it.
    """
    # The BASELINE lives under baselines/, which is committed. Everything else stays under
    # build/, which is not.
    #
    # This was `build/trees/<tree>/census-baseline.json`, and `build/` is gitignored
    # (.gitignore:7) — so the baseline was never committed, and on a fresh clone or in CI there
    # was nothing to compare against. A ratchet whose floor does not survive a clone cannot
    # fail, which is the fifth check in this repository found to be inert for a reason like
    # this. Found 2026-09-24 while adding the lint ratchet, which would have had the same defect.
    if tree:
        d = REPO / "build" / "trees" / tree
        return (d / "break-report.txt",
                REPO / "baselines" / f"census-{tree}.json",
                d / "symbol-census.json")
    return (REPO / "build" / "break-report.txt",
            REPO / "baselines" / "census-loke.json",
            REPO / "build" / "trees" / "loke" / "symbol-census.json")


def repo_modules() -> set[str]:
    """Every module path declared by an `m=` line anywhere in the repository."""
    mods: set[str] = set()
    for root in (REPO / "src", REPO / "packages"):
        if not root.is_dir():
            continue
        for f in root.rglob("*.tk"):
            m = M_DECL_RE.search(f.read_text(errors="replace"))
            if m:
                mods.add(m.group(1))
    return mods


def classify(d: dict) -> tuple[str, str]:
    code = d.get("error_code", "")
    msg = d.get("message", "") or ""
    for name, want_code, needle, advice in CLASSES:
        if code == want_code and (not needle or needle in msg):
            return name, advice
    return f"unclassified-{code}", msg[:100]


def refine_e2030(msg: str, declared: set[str]) -> tuple[str, str] | None:
    """Split "module 'X' not found" by whether the repository declares X.

    Two different jobs. A module that EXISTS needs its interface emitted before its
    importer is compiled — either the target's root list omits its tree, or an earlier
    module in the dependency chain failed and the single-pass interface emission
    cascaded (one broken module in packages/core took 126 of 210 interfaces with it
    while this was being written). A module that does NOT exist needs the import
    deleted or the module written.
    """
    m = MODNAME_RE.search(msg)
    if not m:
        return None
    mod = m.group(1)
    if mod in declared:
        return ("module-interface-missing",
                "The module IS declared in this repository but its interface was not "
                "available when this file was compiled. Either the target's root list "
                "omits the tree that owns it (scripts/build_trees.sh), or a module "
                "earlier in the dependency chain failed and took its dependents' "
                "interfaces with it — the interface pass is a SINGLE pass in "
                "dependency order, so one failure at depth N blinds everything above "
                "it. Check the 'N of M interface(s) emitted' line first.")
    return ("module-absent",
            "Nothing in src/ or packages/ declares this module. The import names "
            "something that does not exist — a module that was renamed, moved into "
            "another package, or planned and never written. Delete the import or "
            "write the module; no interface pass will ever satisfy it.")


def load(report: pathlib.Path) -> list[dict]:
    if not report.exists():
        raise SystemExit(f"{report} not found. Run scripts/build_trees.sh first.")
    out = []
    for line in report.read_text(errors="replace").splitlines():
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


def load_symbols(path: pathlib.Path) -> tuple[int | None, str]:
    """(undefined-symbol count, note). None means "not measured", which is not zero."""
    if not path.exists():
        return None, "no symbol census (scripts/symbol_census.py has not run)"
    try:
        d = json.loads(path.read_text())
    except Exception as e:
        return None, f"symbol census unreadable: {e}"
    n = d.get("undefined_symbols")
    if n is None:
        return None, d.get("note", "symbol census recorded no count")
    return int(n), ""


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", default=None,
                    help="tree name; omit for the legacy build/break-report.txt")
    ap.add_argument("--by-file", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="fail if the count went UP (for a tree walking down to zero)")
    ap.add_argument("--strict", action="store_true",
                    help="fail on ANY error (for a tree already AT zero)")
    args = ap.parse_args()

    report, baseline, symjson = paths(args.tree)
    label = args.tree or "loke (legacy paths)"

    errs = load(report)
    declared = repo_modules()

    classes: collections.Counter[str] = collections.Counter()
    advice: dict[str, str] = {}
    files: collections.Counter[str] = collections.Counter()
    per_class_files: dict[str, set[str]] = collections.defaultdict(set)

    for d in errs:
        name, adv = classify(d)
        if d.get("error_code") == "E2030" and name == "module-not-found":
            r = refine_e2030(d.get("message", "") or "", declared)
            if r:
                name, adv = r
        classes[name] += 1
        advice.setdefault(name, adv)
        short = d.get("file", "?").replace(str(REPO) + "/", "")
        files[short] += 1
        per_class_files[name].add(short)

    n_errors = len(errs)
    n_undef, undef_note = load_symbols(symjson)
    if n_undef:
        classes[SYMBOL_CLASS] += n_undef
        advice.setdefault(SYMBOL_CLASS, SYMBOL_ADVICE)
    total = n_errors + (n_undef or 0)

    if args.baseline:
        baseline.parent.mkdir(parents=True, exist_ok=True)
        baseline.write_text(json.dumps(
            {"tree": args.tree, "total": total, "errors": n_errors,
             "undefined_symbols": n_undef, "files": len(files),
             "classes": dict(classes)},
            indent=2, sort_keys=True) + "\n")
        print(f"[{label}] baseline written: {n_errors} error(s) across {len(files)} "
              f"file(s) + {n_undef if n_undef is not None else '?'} undefined "
              f"symbol(s) = {total}")
        return 0

    if args.strict:
        # For a tree already at zero. An increase-only check cannot protect it: the
        # project total can fall while this tree slips 0 -> 1.
        bad = []
        if n_errors > 0:
            bad.append(f"{n_errors} compile error(s)")
        if n_undef:
            bad.append(f"{n_undef} undefined symbol(s)")
        if n_undef is None:
            bad.append(f"undefined symbols not measured ({undef_note})")
        if bad:
            print(f"[{label}] STRICT FAILURE: " + ", ".join(bad), file=sys.stderr)
            for name, n in classes.most_common(10):
                print(f"    {n:>4}  {name}", file=sys.stderr)
            print(f"    see {report}", file=sys.stderr)
            return 1
        print(f"[{label}] strict OK: 0 errors, 0 undefined symbols")
        return 0

    if args.check:
        if not baseline.exists():
            print(f"[{label}] no baseline at {baseline}; run --baseline first")
            return 0
        base = json.loads(baseline.read_text())
        regressed = []
        b_err = base.get("errors", base["total"])
        if n_errors > b_err:
            regressed.append(f"errors {b_err} -> {n_errors}")
        b_und = base.get("undefined_symbols")
        if b_und is not None and n_undef is not None and n_undef > b_und:
            regressed.append(f"undefined symbols {b_und} -> {n_undef}")
        if regressed:
            print(f"[{label}] REGRESSION: " + "; ".join(regressed), file=sys.stderr)
            print(f"    see {report}", file=sys.stderr)
            return 1
        fixed = b_err - n_errors
        print(f"[{label}] OK: {n_errors} error(s), baseline {b_err} "
              f"({fixed} fixed), {n_undef if n_undef is not None else '?'} undefined "
              f"symbol(s), baseline {b_und if b_und is not None else '?'}")
        return 0

    if args.by_file:
        print(f"[{label}] {n_errors} errors across {len(files)} files — worst first\n")
        for f, n in files.most_common(25):
            print(f"  {n:>4}  {f}")
        return 0

    print(f"[{label}] {n_errors} error(s) across {len(files)} file(s)")
    if n_undef is None:
        print(f"[{label}] undefined symbols: NOT MEASURED — {undef_note}")
    else:
        print(f"[{label}] undefined symbols: {n_undef}")
    print("")
    for name, n in classes.most_common():
        nf = len(per_class_files[name]) if name != SYMBOL_CLASS else 0
        where = f"{nf:>3} files" if name != SYMBOL_CLASS else "  (link)"
        print(f"{n:>5} errors  {where}  {name}")
        for line in _wrap(advice[name]):
            print(f"              {line}")
        print()

    unclassified = sum(n for c, n in classes.items() if c.startswith("unclassified-"))
    if unclassified:
        pct = 100.0 * unclassified / max(total, 1)
        print(f"{unclassified} of {total} ({pct:.0f}%) are unclassified. An "
              f"unclassified count is a number without a work plan: add a class to "
              f"CLASSES with its migration advice.")
        print("")

    if baseline.exists():
        base = json.loads(baseline.read_text())
        delta = base["total"] - total
        word = "fixed" if delta >= 0 else "ADDED"
        print(f"[{label}] baseline {base['total']} -> now {total} "
              f"({abs(delta)} {word})")
    else:
        print(f"[{label}] no baseline at {baseline} yet — run --baseline to record one")
    return 0


def _wrap(text: str, width: int = 74) -> list[str]:
    out, line = [], ""
    for word in text.split():
        if len(line) + len(word) + 1 > width:
            out.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        out.append(line)
    return out


if __name__ == "__main__":
    sys.exit(main())
