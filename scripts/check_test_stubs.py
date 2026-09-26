#!/usr/bin/env python3
"""check_test_stubs.py — a test that re-declares its subject is a gate failure.

X7.3. Around 93 of the 130 discovered test files import no production module at all:
they declare a copy of the module under test inside the test file and assert against the
copy. Such a file cannot fail when production code changes, which is the only thing a
regression test is for. `tests/unit/privacy/test_regex_detector.tk` asserted
`str.len("123456789")==9` and nothing else while the module it is named for reported
every Australian mobile as a Tax File Number.

THE GATE IS PER DIRECTORY, and that is deliberate. Turning it on repo-wide only after
X7.2 finishes leaves it unenforced for exactly the period in which the count could grow
back. A directory is added to ENFORCED the moment it reaches zero, and from then on a
new stub in it is a build failure.

Three things fail a file in an enforced directory:

  1. no live production import — every `i=` is `std.*`, so nothing outside the file
     is exercised;
  2. a commented-out import, e.g. `(* i=ph:core.privacy.placeholder; -- linker issue,
     stubbed below *)`. That note is the stub pattern's own signature and the linker
     gap it blames closed upstream (UPSTREAM.md:77);
  3. a stub DECLARATION marker — `(* --- stub … *)`, `(* Stub: … *)`, `(* Stub types … *)`,
     `stubbed below`, `mirrors core.…`.

(2) and (3) are judged at comment nesting DEPTH 1 only, and (3) additionally only in the
opening of a comment. That is what separates a stub from a de-stubbed test explaining what
its stub used to be — and most of them now do, because the history is the point. toke
comments NEST (T-27), so a quoted

    (* X7.2 — this file used to say
         (* i=ph:core.privacy.placeholder; -- linker issue, stubbed below *)
         (* --- stub placeholder map --- *)
       and assert against the copy. *)

sits at depth 2 and is prose about a stub, not a stub. Reading the raw text flagged four
de-stubbed files for quoting the thing they had removed.

Allowlist: scripts/known-defects.txt, one path per line with a story ID, described there
as a file that "should only ever get shorter".

Usage:
  scripts/check_test_stubs.py --check      # gate mode: exit 1 on any violation
  scripts/check_test_stubs.py              # report every directory, enforced or not
  scripts/check_test_stubs.py --report     # same, with the per-file detail
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Directories at zero. Append one the moment it gets there; never remove one.
ENFORCED = [
    "tests",
    "tests/integration",
    "tests/unit/agents",
    "tests/unit/browser",
    "tests/unit/governance",
    "tests/unit/mcp",
    "tests/unit/memory",
    "tests/unit/models",
    "tests/unit/optimiser",
    "tests/unit/policy",
    "tests/unit/privacy",
    "tests/unit/providers",
    "tests/unit/router",
    "tests/unit/shared",
    "tests/unit/storage",
    "tests/e2e",
    "tests/unit/mcp_broker",
    "tests/unit/platform",
    "tests/unit/audit",
    "tests/unit/companion",
    "tests/unit/feedback",
    "tests/unit/installer",
    "tests/unit/mcp_toke",
    "tests/unit/monitoring",
    "tests/unit/pipeline",
    "tests/unit/cli",
]

LIVE_IMPORT = re.compile(r"^\s*i=([A-Za-z0-9_]+):([A-Za-z0-9_.]+)\s*;", re.M)
COMMENTED_IMPORT = re.compile(r"^\s*i=[A-Za-z0-9_]+:[A-Za-z0-9_.]+\s*;")
STUB_MARKER = re.compile(
    r"^-*\s*stub\b"               # --- stub placeholder map ---
    r"|^\s*stubs?\s*:"            # Stub: construct a pipeline stage
    r"|^\s*stub\s+types?\b"      # Stub types for pipeline stages
    r"|\bstubbed\s+below\b"      # -- linker issue, stubbed below
    r"|\bmirror(s|ing)\s+`?core\.",
    re.I,
)
# How much of a comment's opening is read for a declaration marker. A stub header says so
# immediately; a paragraph of prose that mentions the word later is not a header.
MARKER_WINDOW = 60


def split_comments(src: str):
    """Return (code, [depth-1 comment bodies]). Comments NEST in toke (T-27), so the
    nesting level is tracked rather than matched: a `(*` inside a comment opens another
    one, and everything to its matching `*)` belongs to the outer comment's text."""
    code, top, cur, depth, i = [], [], [], 0, 0
    while i < len(src):
        if src[i:i + 2] == "(*":
            depth += 1
            i += 2
            if depth == 1:
                cur = []
            continue
        if src[i:i + 2] == "*)" and depth > 0:
            depth -= 1
            i += 2
            if depth == 0:
                top.append("".join(cur))
            continue
        if depth == 0:
            code.append(src[i])
        elif depth == 1:
            cur.append(src[i])
        i += 1
    return "".join(code), top


def allowlist() -> set:
    kd = REPO / "scripts" / "known-defects.txt"
    if not kd.exists():
        return set()
    paths = set()
    for line in kd.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        paths.add(line.split()[0])
    return paths


# The one product module whose name begins with test_. scripts/run_tests.sh excludes it
# from discovery by full path for the same reason: it declares no main and is not a test.
NOT_A_TEST = {"packages/core/src/privacy/test_harness.tk"}


def test_files(directory: Path):
    return sorted(p for p in directory.glob("test_*.tk")
                  if str(p.relative_to(REPO)) not in NOT_A_TEST)


def audit(directory: Path, allowed: set):
    """Return (violations, clean_count) for one directory."""
    violations, clean = [], 0
    for path in test_files(directory):
        rel = str(path.relative_to(REPO))
        src = path.read_text(encoding="utf-8", errors="replace")
        code, comments = split_comments(src)

        reasons = []
        prod = [m for _, m in LIVE_IMPORT.findall(code)
                if not m.startswith("std.") and m != "std"]
        if not prod:
            reasons.append("imports no production module: every i= is std.*")
        for c in comments:
            if COMMENTED_IMPORT.search(c):
                reasons.append("has a commented-out import — the stub pattern's signature")
                break
        for c in comments:
            marker = STUB_MARKER.search(c[:MARKER_WINDOW].strip())
            if marker:
                reasons.append(f"declares a stub: {marker.group(0).strip()!r}")
                break

        if not reasons:
            clean += 1
        elif rel in allowed:
            clean += 1  # allowlisted debt, counted as not-a-failure but still listed
            violations.append((rel, reasons, True))
        else:
            violations.append((rel, reasons, False))
    return violations, clean


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    report = "--report" in args or not check
    allowed = allowlist()

    failed = 0
    for d in ENFORCED:
        directory = REPO / d
        if not directory.is_dir():
            print(f"  {d}: ENFORCED but the directory does not exist", file=sys.stderr)
            failed = 1
            continue
        violations, clean = audit(directory, allowed)
        hard = [v for v in violations if not v[2]]
        total = len(test_files(directory))
        if total == 0:
            # Zero violations over zero files is not a clean directory, it is a stale
            # entry. Say so rather than printing 0/0 and passing.
            print(f"  {d}: ENFORCED but holds no test files — remove it from ENFORCED",
                  file=sys.stderr)
            failed = 1
            continue
        if hard:
            failed = 1
            print(f"  {d}: {len(hard)} of {total} test file(s) do not exercise "
                  f"production code", file=sys.stderr)
            for rel, reasons, _ in hard:
                for r in reasons:
                    print(f"    {rel}: {r}", file=sys.stderr)
            print("    A test that re-declares its subject cannot fail when the subject "
                  "breaks.", file=sys.stderr)
            print("    Import the real module, delete the file, or list it in "
                  "scripts/known-defects.txt", file=sys.stderr)
            print("    with the story that removes it.", file=sys.stderr)
        elif report:
            print(f"  {d}: {clean}/{total} exercise production code")
        for rel, reasons, was_allowed in violations:
            if was_allowed:
                print(f"    {rel}: allowlisted debt — {reasons[0]}")
    return failed


if __name__ == "__main__":
    sys.exit(main())
