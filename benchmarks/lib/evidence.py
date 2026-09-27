# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""The committed evidence ledger behind every published figure (story VM1.3a).

Why this exists
---------------
`benchmarks/lib/result.py` writes measurements to `benchmarks/results/`, which is gitignored:
it is a working directory, and CI uploads it as an artefact that expires. A figure in
`docs/metrics-baseline.md` needs evidence that lasts as long as the figure does, so the rows a
published figure was read from are promoted into `benchmarks/evidence/ledger.jsonl`, which is
committed and append-only.

A published figure cites its row by digest, next to the number:

    | Uniform tabular, 100 rows | **1.80x** <sub>[ev:4c1d0e8e2a9b n=2]</sub> |

The digest is the first twelve hex digits of the SHA-256 of the row's canonical JSON (keys
sorted, no whitespace), so a row cannot be edited without breaking every citation of it.
`scripts/check_figure_evidence.py` resolves each citation, re-validates the row through
`result.validate`, and compares the value, N and interval with what the page prints.

Usage
-----
    python3 -m benchmarks.lib.evidence list
    python3 -m benchmarks.lib.evidence promote benchmarks/results/2026-09-20.jsonl --metric X --workload Y

`promote` copies matching rows verbatim, after validating them, and prints each row's citation.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import pathlib
import sys

from benchmarks.lib import result

LEDGER = result.REPO / "benchmarks" / "evidence" / "ledger.jsonl"
LEDGER_REL = "benchmarks/evidence/ledger.jsonl"
DIGEST_LEN = 12

_FIELDS = {f.name for f in dataclasses.fields(result.Measurement)}


def canonical(row: dict) -> str:
    """The one serialisation a digest is taken over."""
    return json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(row: dict) -> str:
    return hashlib.sha256(canonical(row).encode("utf-8")).hexdigest()[:DIGEST_LEN]


def validate_row(row: dict) -> None:
    """Re-run result.validate on a recorded row. Raises result.ResultRejected."""
    unknown = sorted(set(row) - _FIELDS)
    if unknown:
        raise result.ResultRejected(f"row has fields the result sink does not know: {unknown}")
    missing = [k for k in ("metric", "value", "units", "workload", "n") if k not in row]
    if missing:
        raise result.ResultRejected(f"row lacks required fields: {missing}")
    result.validate(result.Measurement(**row))


def parse_ledger(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def read_ledger(path: pathlib.Path | None = None) -> list[dict]:
    path = path or LEDGER
    if not path.is_file():
        return []
    return parse_ledger(path.read_text(encoding="utf-8"))


def promote(rows: list[dict], path: pathlib.Path | None = None) -> list[str]:
    """Validate and append rows to the ledger, skipping any already present."""
    path = path or LEDGER
    present = {digest(r) for r in read_ledger(path)}
    added = []
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            validate_row(row)
            d = digest(row)
            if d not in present:
                fh.write(canonical(row) + "\n")
                present.add(d)
            added.append(d)
    return added


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description="The committed evidence ledger (VM1.3a).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="print every ledger row with its citation")
    p = sub.add_parser("promote", help="copy validated rows from a results file into the ledger")
    p.add_argument("results", type=pathlib.Path)
    p.add_argument("--metric")
    p.add_argument("--workload", help="exact workload, or a prefix ending in '/'")
    p.add_argument("--recorded-at", help="exact recorded_at of one row")
    args = ap.parse_args(argv)

    if args.cmd == "list":
        for row in read_ledger():
            print(f"ev:{digest(row)} n={row['n']}  {row['metric']}={row['value']} "
                  f"{row['units']}  {row['workload']}  {row.get('arm')}  {row['recorded_at']}")
        return 0

    rows = parse_ledger(args.results.read_text(encoding="utf-8"))
    if args.metric:
        rows = [r for r in rows if r.get("metric") == args.metric]
    if args.workload:
        w = args.workload
        rows = [r for r in rows
                if r.get("workload") == w or (w.endswith("/") and r.get("workload", "").startswith(w))]
    if args.recorded_at:
        rows = [r for r in rows if r.get("recorded_at") == args.recorded_at]
    if not rows:
        print("no rows matched", file=sys.stderr)
        return 1
    for d, row in zip(promote(rows), rows):
        print(f"<sub>[ev:{d} n={row['n']}]</sub>  {row['metric']}={row['value']}  {row['workload']}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
