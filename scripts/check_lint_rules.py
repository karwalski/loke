#!/usr/bin/env python3
"""Run `toke --lint` and FAIL on the rules that describe defects, not style.

Why this exists
---------------
`toke --lint` has rules for real defects, and **nothing in this repository ran it.** Measured
2026-09-24 across 454 files: 3,287 diagnostics, including **61 sites of
`result discarded — write x=x.push(...)`** — the exact T-24 class this session had been finding
and fixing by hand all day, one module at a time, from failing tests.

Ten of those 61 were in the built trees. Every one was a silently empty collection:

    installer/pull.tk      x5   a model download reported no progress and no outcome, whatever
                                happened, and `listinstalledmodels` listed nothing ever
    memory/context.tk      x4   L3 deep memory contributed nothing to any context, and
                                `layersloaded` reported ["L0"] whatever loaded — so the struct's
                                provenance field and its token count disagreed, and the half a
                                human reads was the wrong one
    monitoring/sysmon.tk   x1   `cleaned.len>4` was always false, so no pid, CPU or RSS was ever
                                read out of `ps` for any process. The identical defect was found
                                independently in `moke.sysmon.splitws`: two copies of one
                                whitespace splitter, both inert.

That is the argument for this script. A hand sweep found these one at a time over a day; the
linter had them all along.

What fails, and what only counts
--------------------------------
`FAIL_RULES` are message fragments that indicate a defect — code that does not do what it
reads as doing. Everything else is counted and printed, not failed: `concat nested N deep`
(866 sites) and `imported module is never used` (111) are real cleanups, but they are LS1.2 and
LS1.3's work and failing the gate on them today would just mean the gate is off.

Scoped to the built trees by default. The legacy `src/` tree carries 874 diagnostics and is
gated on the F10.12 port decision; moke carries 435 and joins when it links (MK21.16).

    python3 scripts/check_lint_rules.py --check packages/core packages/shared packages/browser
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import pathlib
import subprocess
import sys
import collections

REPO = pathlib.Path(__file__).resolve().parent.parent
TOKE = pathlib.Path(
    subprocess.run(["sh", "-c", 'echo "${TOKE_DIR:-$HOME/tk/toke}"'],
                   capture_output=True, text=True).stdout.strip()) / "toke"

# A defect, not a preference. Each is a case where the code does not do what it reads as doing.
FAIL_RULES = (
    "result discarded",          # T-24: a bare push/append leaves the collection unchanged
)


def lint(path: pathlib.Path) -> list[dict]:
    r = subprocess.run(
        [str(TOKE), f"--config={REPO}/tkc.toml", "-I", f"{REPO}/build/interfaces",
         "--lint", str(path)],
        capture_output=True, text=True, cwd=str(REPO))
    out = []
    for line in (r.stdout + r.stderr).splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                out.append(json.loads(line))
            except Exception:
                pass
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*",
                    default=["packages/core", "packages/shared", "packages/browser"])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--baseline", action="store_true",
                    help="record the current style-diagnostic count as the ratchet floor")
    args = ap.parse_args()

    if not TOKE.exists():
        print(f"check_lint_rules: SKIP — no toke at {TOKE}")
        return 0

    files = []
    for root in args.roots:
        base = REPO / root
        if base.is_dir():
            files += [p for p in sorted(base.rglob("*.tk"))
                      if not any(x in p.parts for x in ("_archived-tests", "build"))]

    failures = []
    other = collections.Counter()
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for path, diags in zip(files, ex.map(lint, files)):
            for d in diags:
                msg = d.get("message", "")
                if any(r in msg for r in FAIL_RULES):
                    failures.append((path.relative_to(REPO), d["pos"]["line"], msg))
                else:
                    other[msg.split("—")[0].strip()[:52]] += 1

    for rel, line, msg in failures:
        print(f"  {rel}:{line}: {msg}")

    # ── The ratchet ───────────────────────────────────────────────────────────────
    #
    # The style rules are not gated as failures — 866 `concat nested N deep` sites are real
    # cleanup with no defect behind them, and failing the gate on them today would mean the gate
    # is switched off. But they must not GROW, which is the same argument `build_census.py` makes
    # for compile errors: a count that only ratchets down needs no campaign to be effective.
    #
    # `string-concat-chain` has **no fix span**, so there is no auto-migration to run — the 866
    # are hand work. Measured, so nobody has to guess: interpolation itself is correct for
    # ordinary strings (`"\(a) \(b)"` and the nested `str.concat` equivalent both produce 11
    # characters for "hello world"), so the rule's advice is sound; T-21's truncation is specific
    # to `std.homedir()` and is not a general hazard.
    # baselines/ is committed; build/ is gitignored, so a baseline there never survives a
    # clone and the ratchet cannot fail. See the note in build_census.py paths().
    baseline_path = REPO / "baselines" / "lint.json"
    total_other = sum(other.values())
    baseline = None
    if baseline_path.exists():
        try:
            baseline = json.loads(baseline_path.read_text())
        except Exception:
            baseline = None

    if other:
        print(f"\n  {sum(other.values())} other lint diagnostic(s), not gated as failures "
              f"(LS1.2/LS1.4 own these):")
        for msg, n in other.most_common(6):
            print(f"    {n:5}  {msg}")

    regressed = False
    if baseline is not None:
        was = baseline.get("total", 0)
        if total_other > was:
            print(f"\n  RATCHET: style diagnostics went {was} -> {total_other}. They are not "
                  f"gated as defects, but they must not grow.", file=sys.stderr)
            for msg, n in other.most_common():
                before = baseline.get("byrule", {}).get(msg, 0)
                if n > before:
                    print(f"    {msg}: {before} -> {n}", file=sys.stderr)
            regressed = True
        else:
            print(f"\n  ratchet: {was} -> {total_other} "
                  f"({'unchanged' if was == total_other else f'{was - total_other} fewer'})")
    else:
        print(f"\n  no lint baseline at {baseline_path.relative_to(REPO)} — "
              f"run with --baseline to record one")

    if args.baseline:
        baseline_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_path.write_text(json.dumps(
            {"total": total_other, "byrule": dict(other)}, indent=2, sort_keys=True))
        print(f"  baseline recorded: {total_other} style diagnostic(s)")

    if not failures and not regressed:
        print(f"\ncheck_lint_rules: OK — {len(files)} file(s), no defect-class lint rule fires.")
        return 0
    if failures:
        print(f"\n{len(failures)} defect-class lint diagnostic(s). A bare `x.push(...)` never "
              f"mutates — the collection stays as it was and nothing warns at runtime.",
              file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
