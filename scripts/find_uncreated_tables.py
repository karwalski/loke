#!/usr/bin/env python3
"""Find a table named in SQL that no `CREATE TABLE` anywhere in the tree creates.

Why this exists
---------------
Measured 2026-09-24: **five tables were referenced and created nowhere.** Every read against
them failed, and `core.storage.db`'s row accessors map a failed read to `0` or `""` (LS1.1i), so
nothing reported it — the data was simply always empty.

  memory_graph_entities    every field of every memory-graph entity was empty or zero
  memory_graph_relations   likewise, and `memory/graph.tk` is the only reader
  memory_settings          `memory/privacy.tk` could not store a privacy preference
  metrics_raw              `core.metrics.collector` is its only writer, so **no metric event
                           this project ever emitted was stored**. Worth reading next to
                           eval/bench.tk reporting 0 ms for every benchmark (LS1.1q): between
                           them, nothing measurable was being measured.
  audit_entries            queried by `policy/export.tk` for an audit export. NOT created,
                           deliberately — see GA5.12. It is a second name for the audit trail,
                           and creating it would give loke two.

M1.7 had recorded four of these for a day and was still open; the sweep found them in one pass,
along with `metrics_raw`, which belonged to a different epic (DA1.2) and so had not been
connected to them.

What it checks
-------------
Collects every identifier appearing after `FROM`, `INTO`, `UPDATE` or `JOIN` in a string literal,
and subtracts every `CREATE TABLE IF NOT EXISTS <name>` found anywhere in the roots — not only in
`storage/migrations.tk`, because several modules legitimately create their own tables at runtime
(`feedback.store.ensuretable`, `governance.incidents`, `governance.quota`).

It is deliberately lenient in one direction: a table created by a module rather than a migration
counts as created. That is a real pattern here and this check is not the place to argue with it.

`scripts/known-tables.txt` carries the deliberate exceptions, one per line with a story ID —
`audit_entries` is there because GA5.12 owns the decision.

    python3 scripts/find_uncreated_tables.py --check packages/core packages/shared
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
# Case-SENSITIVE, uppercase. This codebase writes SQL keywords in capitals, and requiring that
# is what separates a query from prose: the second version of this check scanned string literals
# but case-insensitively, and still reported 33 tables because user-facing messages contain
# phrases like "data from any source" and "check for available updates". Requiring `FROM` over
# `from` removes every one of those without an allowlist.
# A name followed by `.` is a schema qualifier (`temp.`, `main.`), not a table: the table name
# is whatever follows it, and is skipped when it is concatenated in rather than literal (NC1.7).
REF = re.compile(r"\b(?:FROM|INTO|UPDATE|JOIN)\s+(?:[a-z_][a-z0-9_]*\.)?([a-z_][a-z0-9_]*)\b(?!\.)")
# A literal is only treated as SQL if it contains a SQL verb in capitals.
SQLISH = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|REPLACE)\b")
CREATE = re.compile(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([a-z_][a-z0-9_]*)", re.I)

# SQLite's own catalogue, and SQL keywords that can follow FROM/INTO.
BUILTIN = {"sqlite_master", "sqlite_sequence", "sqlite_temp_master"}
# SQL keywords that can follow FROM/INTO, plus the English conjunctions that appear after an
# uppercase SQL verb in PROSE — `compliance.tk` carries operator messages like "audit_log rejects
# UPDATE and DELETE by database trigger". A real `UPDATE <x>` is followed by a table name, and the
# words that can follow it in a sentence are a small closed set, so listing them is exact rather
# than a heuristic.
NOT_A_TABLE = {"select", "values", "set", "where", "on", "as", "dual",
               "and", "or", "is", "by", "a", "an", "the", "it", "them", "any", "all"}


def string_literals(src: str) -> list[str]:
    """Every double-quoted literal in the source, comments excluded.

    SQL only ever appears inside a string, and scanning raw text instead was the first version
    of this check: it matched English prose in comments — "from a", "into the", "from another" —
    and reported **76 tables**, of which 71 were words. A check that cries wolf 71 times is one
    somebody deletes, so the scan is narrowed to where SQL can actually be.

    Comments nest in toke and `(*` can appear inside a string (T-27), so string state is
    tracked first and comment depth only outside it.
    """
    out = []
    i = 0
    depth = 0
    while i < len(src):
        if depth == 0 and src[i] == '"':
            j = i + 1
            buf = []
            while j < len(src):
                if src[j] == "\\":
                    buf.append(src[j:j + 2])
                    j += 2
                    continue
                if src[j] == '"':
                    break
                buf.append(src[j])
                j += 1
            out.append("".join(buf))
            i = j + 1
            continue
        if src.startswith("(*", i):
            depth += 1
            i += 2
            continue
        if src.startswith("*)", i) and depth > 0:
            depth -= 1
            i += 2
            continue
        i += 1
    return out


def allow() -> dict[str, str]:
    out = {}
    p = REPO / "scripts" / "known-tables.txt"
    if p.exists():
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                parts = line.split(None, 1)
                out[parts[0]] = parts[1] if len(parts) > 1 else ""
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages/core"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    referenced: dict[str, list[str]] = {}
    created: set[str] = set()
    for root in args.roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.tk")):
            if any(x in f.parts for x in ("_archived-tests", "build")):
                continue
            lits = string_literals(f.read_text(errors="replace"))
            for lit in lits:
                created.update(m.group(1).lower() for m in CREATE.finditer(lit))
            for lit in lits:
                if not SQLISH.search(lit):
                    continue
                for m in REF.finditer(lit):
                    name = m.group(1).lower()
                    if name in NOT_A_TABLE or name in BUILTIN:
                        continue
                    referenced.setdefault(name, []).append(str(f.relative_to(REPO)))

    allowed = allow()
    missing = {t: v for t, v in referenced.items() if t not in created and t not in allowed}
    for t in sorted(missing):
        where = sorted(set(missing[t]))
        print(f"  {t}: referenced in {', '.join(where[:3])}"
              f"{' …' if len(where) > 3 else ''} — no CREATE TABLE anywhere")
    if not missing:
        skipped = [t for t in referenced if t in allowed]
        note = f" ({len(skipped)} allowlisted)" if skipped else ""
        print(f"find_uncreated_tables: OK — every table referenced in SQL is created{note}.")
        return 0
    print(f"\n{len(missing)} table(s) referenced and never created. Every read against one "
          f"fails, and the row accessors map a failed read to 0 or \"\" — so the data is "
          f"silently always empty. Add a migration, or allowlist it in "
          f"scripts/known-tables.txt with a story ID.", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
