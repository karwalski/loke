#!/usr/bin/env python3
"""fix_diagnostics.py — apply mechanical fixes driven by toke's own diagnostics.

toke emits one JSON diagnostic per line with exact byte offsets (span_start /
span_end). This tool parses those and rewrites only the spans toke itself
flagged, then re-runs to a fixpoint.

This is deliberately NOT a regex sweep over source text. scripts/migrate_v3.py
used a regex (`^[ \\t]*//.*\\n`) and silently deleted the licence header from
520 files. Only compiler-identified spans are touched here, so a legitimate
assignment is never rewritten as a comparison.

Currently handles:
  E2002  "`=` is assignment; use `==` for equality"  ->  `=` becomes `==`

Usage:
  ./scripts/fix_diagnostics.py --check          # report what would change
  ./scripts/fix_diagnostics.py --apply          # rewrite files
  ./scripts/fix_diagnostics.py --apply --paths packages/moke
"""

import argparse
import json
import os
import pathlib
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
TOKE_DIR = pathlib.Path(os.environ.get("TOKE_DIR", pathlib.Path.home() / "tk" / "toke"))
TOKE = TOKE_DIR / "toke"
IFACE = REPO / "build" / "interfaces"

# error_code -> (predicate on message, span replacement)
HANDLERS = {
    "E2002": (lambda m: "`=` is assignment" in m, "=="),
}


def diagnose(path: pathlib.Path) -> list[dict]:
    """Type-check one file and return its parsed diagnostics."""
    proc = subprocess.run(
        [str(TOKE), "-I", str(IFACE), "--check", str(path)],
        capture_output=True, text=True,
    )
    out = []
    for line in (proc.stdout + proc.stderr).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def fixable(diags: list[dict]) -> list[tuple[int, int, str]]:
    """Return (span_start, span_end, replacement) for diagnostics we handle."""
    edits = []
    for d in diags:
        code = d.get("error_code")
        handler = HANDLERS.get(code)
        if not handler:
            continue
        pred, repl = handler
        if not pred(d.get("message", "")):
            continue
        start, end = d.get("span_start"), d.get("span_end")
        if start is None or end is None or end <= start:
            continue
        edits.append((start, end, repl))
    # Deduplicate, then apply back-to-front so earlier offsets stay valid.
    return sorted(set(edits), key=lambda e: -e[0])


def fix_file(path: pathlib.Path, apply: bool) -> int:
    """Iterate until no more handled diagnostics remain. Returns edits made."""
    total = 0
    for _ in range(40):  # fixpoint guard
        edits = fixable(diagnose(path))
        if not edits:
            break
        raw = path.read_bytes()
        for start, end, repl in edits:
            raw = raw[:start] + repl.encode() + raw[end:]
        total += len(edits)
        if not apply:
            break  # --check reports the first pass only; don't write
        path.write_bytes(raw)
    return total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="write changes")
    ap.add_argument("--check", action="store_true", help="report only (default)")
    ap.add_argument("--paths", nargs="*", default=["packages"],
                    help="directories to sweep (default: packages)")
    args = ap.parse_args()

    if not TOKE.is_file():
        print(f"ERROR: toke not found at {TOKE}; set TOKE_DIR", file=sys.stderr)
        return 1

    files = []
    for p in args.paths:
        root = REPO / p
        if root.is_file():
            files.append(root)
        else:
            files.extend(sorted(root.rglob("*.tk")))
    files = [f for f in files if "_archived" not in str(f)]

    changed_files = 0
    changed_edits = 0
    for f in files:
        n = fix_file(f, apply=args.apply)
        if n:
            changed_files += 1
            changed_edits += n
            verb = "fixed" if args.apply else "would fix"
            print(f"{verb} {n:3d}  {f.relative_to(REPO)}")

    verb = "Applied" if args.apply else "Would apply"
    print(f"\n{verb} {changed_edits} edit(s) across {changed_files} file(s) "
          f"of {len(files)} scanned.")
    if not args.apply and changed_edits:
        print("Re-run with --apply to write.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
