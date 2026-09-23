#!/usr/bin/env python3
"""Attribute a tree's undefined symbols to the module that calls them (story F10.23c).

Why this exists
---------------
T-7: toke does not check an unknown method call at compile time. `foo.bar()` where
`bar` does not exist in `foo` type-checks, compiles, and becomes an undefined symbol
at LINK time. The default experience of that is a wall of

    ld: Undefined symbols:
      _core_privacy_placeholder_restore, referenced from: ...

which attributes nothing to any module, orders nothing by severity, and stops at the
first hundred. 247 non-test `.tk` files in six trees had never been compiled once
before F10.23, so they were never linked either: every one of those unknown calls is
still in there, undetected.

This inverts toke's mangling instead. toke mangles a module path by replacing `.`
with `_` and appending the function name — `core.privacy.placeholder.restore` becomes
`_core_privacy_placeholder_restore`, and `scripts/build_loke.sh` relies on the same
convention to name its object files. Given the set of module paths the repo and the
toolchain actually declare, the longest matching prefix recovers the module, and what
is left is the function. That turns a flat symbol list into buckets, because they are
different kinds of work — three of them for toke symbols, and a fourth for what is
left:

  * `absent-toolchain-module` — the module is `std.*`/`ooke.*` and the toolchain has
    no interface for it. `packages/browser/src/shell.tk` imports `std.webview`, which
    does not exist in toke's stdlib. This is an upstream ask, not a loke defect, and
    no amount of editing loke fixes it.
  * `missing-function` — a module that DOES exist exports no such function. A rename,
    a typo, or a function that was planned and never written. Fix it in loke.
  * `unknown-module` — nothing in the repo or the toolchain declares any module that
    prefixes this symbol. The call names a module that does not exist at all.
  * `unresolved-c` — an undefined symbol at the C level that no library on the link
    line provides. This bucket exists because the first version of this script filed
    everything non-toke as "c-runtime (expected from libtokestd.a)" and buried two
    real link failures in it: `packages/moke/src/feedback/feedback.tk` calls
    `std.nowms()` against a bare `std` import, which toke mangles to
    `_tk_std_nowms_w` — the real symbol is `_tk_time_nowms_w`, from `std.time` — and
    `src/core/health/api.tk` references a bare `_json`. Neither is a compile error and
    neither would ever have been reported. Membership is decided empirically: the
    symbol is declared and referenced in a one-line C file and linked against the same
    libraries the real link uses. If that succeeds it is a genuine system import
    (`_malloc`, `_pow`) and is counted separately as `system-library`; if it fails, it
    is a defect.

toke's stdlib calls are mangled differently from its module calls — `std.time.nowms`
becomes `_tk_time_nowms_w`, not `_std_time_nowms`. Those are recognised too, so a call
against a `std.*` module that does not exist is filed as an upstream ask rather than as
mysterious C.

What it measures
----------------
Per tree: how many undefined symbols remain after subtracting everything the tree's
own objects, the extra object dirs, and libtokestd.a define; which module each is
called from; and, with --probe, how many of the tree's modules link individually.

What it does NOT measure
------------------------
Whether a call is REACHABLE. An undefined symbol in a function nothing calls still
fails the link, so that distinction does not matter for linking, but it does mean the
count is not a count of bugs a user can hit. It also does not find unknown calls that
the optimiser deleted, and it cannot see a call that was never compiled — a module
that failed to compile contributes no object and therefore no symbols, so a falling
error count can RAISE this number. That is expected; both numbers are baselined.

The per-module probe links lazily, against archives, deliberately.
`scripts/run_tests.sh` records why `-force_load` is wrong here: it drags in every
page handler, which need ooke's own objects, and turns a single-module probe into a
link against the whole application.

Usage
-----
    scripts/symbol_census.py --tree cli --objdir build/trees/loke-cli/obj \\
        --source-root packages/cli/src --stdlib-archive /tmp/loke-tests/libtokestd.a
    scripts/symbol_census.py --tree cli --objdir ... --probe   # per-module link probe
    scripts/symbol_census.py --tree cli --objdir ... --json out.json
"""

from __future__ import annotations

import argparse
import collections
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
TOKE_DIR = pathlib.Path(os.environ.get("TOKE_DIR", pathlib.Path.home() / "tk" / "toke"))
OOKE_DIR = pathlib.Path(os.environ.get("OOKE_DIR", pathlib.Path.home() / "tk" / "toke-ooke"))

M_RE = re.compile(r"^m=([A-Za-z0-9_.]+)\s*;", re.M)
I_RE = re.compile(r"^i=[A-Za-z0-9_]+:([A-Za-z0-9_.]+)\s*;", re.M)

# Buckets, in report order. The name is the class recorded in the baseline.
BUCKETS = [
    ("absent-toolchain-module",
     "stdlib/toolchain module absent — upstream ask, not fixable in loke"),
    ("missing-function",
     "module exists, function does not — rename, typo, or never written"),
    ("unknown-module",
     "no such module: nothing in the repo or the toolchain declares it"),
    ("unresolved-c",
     "undefined at the C level and no library on the link line defines it"),
]

# toke mangles a STDLIB call as _tk_<module>_<function>_w, dropping the `std.`
# prefix: std.time.nowms -> _tk_time_nowms_w. A call on a std module that does not
# exist lands here rather than looking like unexplained C.
TK_CALL_RE = re.compile(r"^_tk_([a-z0-9]+)_([a-z0-9_]+)_w$")

# The libraries the real link line uses (scripts/lib/build_tree.sh step 7). A residual
# symbol is probed against exactly these, so "is this a genuine system import?" is
# answered by the linker rather than by a hand-maintained list of libc names.
LINK_LIBS = ["-lm", "-lz", "-lsqlite3", "-lssl", "-lcrypto", "-lobjc",
             "-framework", "Security", "-framework", "CoreFoundation"]


def system_provides(syms: list[str], workdir: pathlib.Path) -> set[str]:
    """Which of these symbols a system library on the real link line defines.

    One link per symbol, and the residual set is normally one to three symbols. If
    clang is missing this raises rather than guessing: a tool that is not there is a
    failure, not a reason to skip the step.
    """
    if not syms:
        return set()
    clang = shutil.which("clang")
    if not clang:
        raise SystemExit("ERROR: clang is required to classify undefined C symbols")
    ok = set()
    for sym in syms:
        name = sym[1:] if sym.startswith("_") else sym
        src = workdir / "sysprobe.c"
        src.write_text(f"extern long {name}(void);\n"
                       f"long (*p_{name})(void) = {name};\n"
                       f"int main(void){{ return p_{name} != 0; }}\n")
        p = subprocess.run([clang, "-w", "-L/opt/homebrew/lib", str(src),
                            "-o", str(workdir / "sysprobe.out")] + LINK_LIBS,
                           capture_output=True, text=True)
        if p.returncode == 0:
            ok.add(sym)
    return ok


def run(cmd: list[str]) -> str:
    """Run a command and return stdout. A non-zero exit is reported, never ignored.

    Reading `head`'s exit status instead of the program's has produced false passes in
    this repo before, so the status is checked here and the failure is printed.
    """
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0 and not p.stdout:
        print(f"WARNING: {' '.join(cmd[:2])} ... exited {p.returncode}: "
              f"{p.stderr.strip()[:200]}", file=sys.stderr)
    return p.stdout


def nm_undefined(path: pathlib.Path) -> set[str]:
    out = set()
    for line in run(["nm", "-u", str(path)]).splitlines():
        s = line.strip()
        if s and " " not in s:
            out.add(s)
    return out


def nm_defined(path: pathlib.Path) -> set[str]:
    """Globally defined symbols. -U on BSD nm means 'do not show undefined'."""
    out = set()
    for line in run(["nm", "-gU", str(path)]).splitlines():
        parts = line.split()
        if len(parts) >= 2:
            out.add(parts[-1])
    return out


def objects_in(d: pathlib.Path) -> list[pathlib.Path]:
    return sorted(d.rglob("*.o")) if d.is_dir() else []


def declared_modules(roots: list[pathlib.Path]) -> dict[str, pathlib.Path]:
    """Every module path declared by an `m=` line under these roots."""
    owner: dict[str, pathlib.Path] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*.tk")):
            m = M_RE.search(f.read_text(errors="replace"))
            if m and m.group(1) not in owner:
                owner[m.group(1)] = f
    return owner


def toolchain_modules() -> set[str]:
    """`std.*` from toke's stdlib interfaces and `ooke.*` from ooke's."""
    mods = set()
    for tki in (TOKE_DIR / "stdlib").glob("*.tki"):
        mods.add("std." + tki.stem)
    for tki in (TOKE_DIR / "src" / "stdlib").glob("*.tki"):
        mods.add("std." + tki.stem)
    for tki in (OOKE_DIR / "src").glob("ooke.*.tki"):
        mods.add(tki.stem)
    for tki in (OOKE_DIR / "src" / "ooke").glob("*.tki"):
        mods.add("ooke." + tki.stem)
    return mods


def imported_modules(roots: list[pathlib.Path]) -> set[str]:
    mods = set()
    for root in roots:
        if not root.is_dir():
            continue
        for f in root.rglob("*.tk"):
            mods |= set(I_RE.findall(f.read_text(errors="replace")))
    return mods


def demangle(sym: str, prefixes: list[tuple[str, str]]) -> tuple[str | None, str]:
    """Longest-prefix match of a mangled symbol against known module paths.

    `prefixes` is sorted longest-first and holds ('_core_privacy_placeholder_',
    'core.privacy.placeholder') pairs. Returns (module, function) or (None, guess).
    """
    for mangled, mod in prefixes:
        if sym.startswith(mangled):
            return mod, sym[len(mangled):]
    return None, sym.lstrip("_").replace("_", ".")


def module_of_object(obj: pathlib.Path) -> str:
    """The object file is named for the module path with '.' replaced by '_'."""
    stem = obj.name
    for suffix in (".ll.o", ".o"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    return stem.replace("_", ".")


def probe_modules(objs: list[pathlib.Path], archives: list[pathlib.Path],
                  workdir: pathlib.Path) -> dict:
    """Link each module on its own against the tree's archive, lazily.

    Turns "the tree does not link" into "37 of 96 modules link" — a number that moves
    and attributes its failures per module. The archive is lazy on purpose: a module
    pulls in the members it actually references and their transitive dependencies,
    and nothing else.
    """
    clang = shutil.which("clang")
    ar = shutil.which("ar")
    if not clang or not ar:
        # A missing tool is a failure, not a reason to skip the step.
        raise SystemExit("ERROR: clang and ar are required for --probe and one is missing")

    tree_a = workdir / "libtree.a"
    subprocess.run([ar, "rcs", str(tree_a)] + [str(o) for o in objs],
                   capture_output=True, check=False)
    if not tree_a.exists():
        raise SystemExit(f"ERROR: could not build {tree_a}; the probe cannot run")

    stub_c = workdir / "probe_stub.c"
    stub_c.write_text("int main(void){return 0;}\n")
    stub_o = workdir / "probe_stub.o"
    subprocess.run([clang, "-c", str(stub_c), "-o", str(stub_o)],
                   capture_output=True, check=False)

    linked, failed = [], []
    for obj in objs:
        mod = module_of_object(obj)
        defines_main = "_main" in nm_defined(obj)
        cmd = [clang, "-L/opt/homebrew/lib", "-x", "none", str(obj)]
        if not defines_main:
            cmd.append(str(stub_o))
        cmd += [str(a) for a in archives if a.exists()]
        cmd += [str(tree_a), "-o", str(workdir / "probe.out"),
                "-lm", "-lz", "-lsqlite3", "-lssl", "-lcrypto",
                "-framework", "Security", "-framework", "CoreFoundation", "-lobjc"]
        p = subprocess.run(cmd, capture_output=True, text=True)
        if p.returncode == 0:
            linked.append(mod)
        else:
            # Two ld formats, and getting this wrong reports every failure as
            # "(no symbol named by ld)". The classic linker quotes the symbol
            # ("_foo", referenced from:); ld_prime does not (_foo, referenced from:).
            missing = sorted(set(re.findall(
                r'"?(_[A-Za-z0-9_.$]+)"?,\s*referenced from', p.stderr)))
            failed.append({"module": mod, "missing": missing[:10],
                           "missing_total": len(missing)})
    return {"modules": len(objs), "linked": len(linked),
            "failed": len(failed), "failures": failed,
            "linked_modules": sorted(linked)}


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tree", required=True, help="tree name, for the report heading")
    ap.add_argument("--objdir", action="append", default=[],
                    help="directory of the tree's own objects (repeatable)")
    ap.add_argument("--object", action="append", default=[],
                    help="a single extra object of the tree (repeatable)")
    ap.add_argument("--defines-objdir", action="append", default=[],
                    help="object dir that only CONTRIBUTES definitions (repeatable)")
    ap.add_argument("--defines-skip", action="append", default=[],
                    help="basename to omit from --defines-objdir, because the real "
                         "link omits it too (repeatable). The link excludes ooke's own "
                         "handlers.o — the application supplies ooke.handlers — and "
                         "counting it as defined made the census miss a missing "
                         "registerall that the link then failed on.")
    ap.add_argument("--source-root", action="append", default=[],
                    help="the tree's source roots, for the import list (repeatable)")
    ap.add_argument("--stdlib-archive", default=None,
                    help="libtokestd.a; without it C runtime symbols are only counted")
    ap.add_argument("--probe-archive-dir", action="append", default=[],
                    help="extra object dir archived for the link probe (repeatable)")
    ap.add_argument("--probe", action="store_true", help="per-module link probe")
    ap.add_argument("--json", default=None, help="write the census here")
    ap.add_argument("--limit", type=int, default=40,
                    help="symbols printed per bucket (default 40)")
    args = ap.parse_args()

    def p(s: str) -> pathlib.Path:
        q = pathlib.Path(s)
        return q if q.is_absolute() else REPO / q

    tree_objs: list[pathlib.Path] = []
    for d in args.objdir:
        tree_objs += objects_in(p(d))
    for f in args.object:
        if p(f).is_file():
            tree_objs.append(p(f))
    tree_objs = sorted(set(tree_objs))

    if not tree_objs:
        print(f"[{args.tree}] no objects found — nothing compiled, so nothing to "
              f"census. This is not a pass.", file=sys.stderr)
        # An empty object set is a real result and must be recorded as such rather
        # than as zero undefined symbols.
        if args.json:
            out = p(args.json)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(
                {"tree": args.tree, "objects": 0, "undefined_symbols": None,
                 "buckets": {}, "note": "no objects compiled"}, indent=2) + "\n")
        return 1

    # ── the defined set ──────────────────────────────────────────────────────
    defined: set[str] = set()
    for o in tree_objs:
        defined |= nm_defined(o)
    skip = set(args.defines_skip)
    for d in args.defines_objdir:
        for o in objects_in(p(d)):
            if o.name in skip:
                continue
            defined |= nm_defined(o)
    stdlib_used = False
    if args.stdlib_archive and p(args.stdlib_archive).exists():
        defined |= nm_defined(p(args.stdlib_archive))
        stdlib_used = True

    # ── the undefined set, with the module that references each ──────────────
    refs: dict[str, set[str]] = collections.defaultdict(set)
    for o in tree_objs:
        caller = module_of_object(o)
        for sym in nm_undefined(o) - defined:
            refs[sym].add(caller)

    # ── the module universe ──────────────────────────────────────────────────
    repo_mods = declared_modules([REPO / "src", REPO / "packages"])
    tool_mods = toolchain_modules()
    roots = [p(r) for r in args.source_root]
    absent_imports = {m for m in imported_modules(roots)
                      if m not in repo_mods and m not in tool_mods}
    # Anything the tree imports that nothing provides is still a real module path, so
    # it must be in the prefix table or `std.webview.create` would look unattributable.
    known = set(repo_mods) | tool_mods | absent_imports
    prefixes = sorted((("_" + m.replace(".", "_") + "_", m) for m in known),
                      key=lambda t: -len(t[0]))
    namespaces = {m.split(".", 1)[0] for m in known}

    rows: dict[str, list[tuple[str, str, str]]] = {b: [] for b, _ in BUCKETS}
    residual: list[tuple[str, str]] = []

    for sym, callers in refs.items():
        caller_txt = ",".join(sorted(callers)[:3])

        # A toke STDLIB call first: _tk_<mod>_<fn>_w. std.time.nowms is
        # _tk_time_nowms_w, so a bare `i=std:std;` + std.nowms() emits
        # _tk_std_nowms_w and there is no std.std to satisfy it.
        tk = TK_CALL_RE.match(sym)
        if tk:
            stdmod = "std." + tk.group(1)
            name = f"{stdmod}.{tk.group(2)}"
            if tk.group(1) == "std":
                # _tk_std_<fn>_w means the source bound an alias to a bare `std`
                # and called std.<fn>() — there is no module `std`, only std.time,
                # std.str and the rest. Report it as the source wrote it.
                name = f"std.{tk.group(2)} (bare `std` import; no such module)"
            if stdmod in tool_mods:
                rows["missing-function"].append((name, caller_txt, sym))
            else:
                rows["absent-toolchain-module"].append((name, caller_txt, sym))
            continue

        mod, func = demangle(sym, prefixes)
        if mod is None:
            head = sym.lstrip("_").split("_", 1)[0]
            if head in namespaces:
                rows["unknown-module"].append((func, caller_txt, sym))
            else:
                residual.append((sym, caller_txt))
            continue
        name = f"{mod}.{func}" if func else mod
        if mod in absent_imports or (mod not in repo_mods and mod not in tool_mods):
            rows["absent-toolchain-module"].append((name, caller_txt, sym))
        else:
            rows["missing-function"].append((name, caller_txt, sym))

    # What is left is C-level. Ask the linker which of them a system library on the
    # real link line actually provides; the rest are defects, and burying them under
    # "expected from libtokestd.a" is how _tk_std_nowms_w and _json went unreported.
    with tempfile.TemporaryDirectory(prefix="loke-sysprobe-") as td:
        provided = system_provides([s for s, _ in residual], pathlib.Path(td))
    system_library = sorted(s for s, _ in residual if s in provided)
    for sym, caller_txt in residual:
        if sym not in provided:
            rows["unresolved-c"].append((sym, caller_txt, sym))

    counts = {b: len(rows[b]) for b, _ in BUCKETS}
    toke_total = sum(counts.values())

    # ── report ───────────────────────────────────────────────────────────────
    print("")
    print(f"[{args.tree}] undefined-symbol census: {toke_total} unresolved symbol(s) "
          f"across {len(tree_objs)} object(s)")
    if not stdlib_used:
        print(f"[{args.tree}] WARNING: libtokestd.a was not consulted "
              f"(--stdlib-archive not given or missing), so every C runtime symbol the "
              f"archive defines is counted below as unresolved. The count is wrong, "
              f"not merely noisy — pass --stdlib-archive.")
    for bucket, advice in BUCKETS:
        print("")
        print(f"{counts[bucket]:>5}  {bucket}")
        print(f"       {advice}")
        for name, caller, _sym in sorted(rows[bucket])[: args.limit]:
            print(f"  {name:<46s} called from {caller:<26s} — {advice.split(' —')[0]}")
        if counts[bucket] > args.limit:
            print(f"  ... {counts[bucket] - args.limit} more")
    print("")
    print(f"{len(system_library):>5}  system-library (the linker resolves these from "
          f"libSystem/libm/etc; not counted)")
    for sym in system_library[:10]:
        print(f"  {sym}")
    if len(system_library) > 10:
        print(f"  ... {len(system_library) - 10} more")

    out = {
        "tree": args.tree,
        "objects": len(tree_objs),
        "undefined_symbols": toke_total,
        "buckets": counts,
        "system_library": len(system_library),
        "stdlib_archive_consulted": stdlib_used,
        "detail": {b: [{"symbol": s, "name": n, "callers": c.split(",")}
                       for n, c, s in sorted(rows[b])] for b, _ in BUCKETS},
        "system_library_symbols": system_library,
    }

    if args.probe:
        archives = [p(a) for a in ([args.stdlib_archive] if args.stdlib_archive else [])]
        with tempfile.TemporaryDirectory(prefix="loke-probe-") as td:
            work = pathlib.Path(td)
            extra = []
            for d in args.probe_archive_dir:
                objs = [o for o in objects_in(p(d)) if o.name not in skip]
                if not objs:
                    continue
                a = work / (p(d).name + ".a")
                subprocess.run(["ar", "rcs", str(a)] + [str(o) for o in objs],
                               capture_output=True, check=False)
                extra.append(a)
            res = probe_modules(tree_objs, extra + archives, work)
        print("")
        print(f"[{args.tree}] link probe: {res['linked']} of {res['modules']} "
              f"module(s) link on their own")
        for f in res["failures"][:20]:
            miss = ", ".join(f["missing"][:3]) or "(no symbol named by ld)"
            print(f"  FAIL {f['module']:<45s} {f['missing_total']} missing: {miss}")
        if len(res["failures"]) > 20:
            print(f"  ... {len(res['failures']) - 20} more")
        out["probe"] = res

    if args.json:
        j = p(args.json)
        j.parent.mkdir(parents=True, exist_ok=True)
        j.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
        print(f"[{args.tree}] wrote {j}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
