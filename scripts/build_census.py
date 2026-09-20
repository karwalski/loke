#!/usr/bin/env python3
"""Classify the build's diagnostics so a migration can be worked and measured.

Why this exists
---------------
The first honest build against toke 6cc9061+ and ooke v3.0.0-rc.1 produced
**83 modules compiled, 116 failed, 505 errors**. A list of 505 errors is not a
work plan, and "the build is red" is not a progress measure.

The errors are not 505 problems. They are a handful of upstream API changes
multiplied across call sites: `std.db` was redesigned, `std.http.post` lost two
parameters, integer widths got stricter. This groups them so each class can be
fixed once and the count can be watched going down.

Usage
-----
    python3 scripts/build_census.py                 # classify build/break-report.txt
    python3 scripts/build_census.py --by-file       # worst files first
    python3 scripts/build_census.py --baseline      # write the current count as the baseline
    python3 scripts/build_census.py --check         # fail if the count went UP
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
REPORT = REPO / "build" / "break-report.txt"
BASELINE = REPO / "build" / "census-baseline.json"

# Each class is one upstream change, with the migration it implies. Matched on the
# error code plus a substring, in order, so the first match wins.
CLASSES = [
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
    ("process-spawn-arity", "E4026", "std.process.spawn",
     "std.process.spawn takes one argument."),
    ("str-concat-arity", "E4026", "std.str.concat",
     "str.concat is binary. Nested calls, or str.join."),
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
    ("return-type", "E4031", "expected 'i64', got '$",
     "A function declared -> i64 returns a struct. Declare the real return type."),
    ("ooke-member", "E4027", "'ooke.",
     "An ooke module member moved or was renamed in 3.0.0-rc.1."),
    ("interface-arity", "E4026", "the interface d",
     "A loke .tki interface disagrees with its implementation."),
    ("missing-semicolon", "E2003", "",
     "Parse error: missing semicolon."),
    ("parse", "E2002", "",
     "Parse error."),
]


def classify(d: dict) -> tuple[str, str]:
    code = d.get("error_code", "")
    msg = d.get("message", "") or ""
    for name, want_code, needle, advice in CLASSES:
        if code == want_code and (not needle or needle in msg):
            return name, advice
    return f"unclassified-{code}", msg[:100]


def load() -> list[dict]:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--by-file", action="store_true")
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    errs = load()
    classes = collections.Counter()
    advice = {}
    files = collections.Counter()
    per_class_files = collections.defaultdict(set)

    for d in errs:
        name, adv = classify(d)
        classes[name] += 1
        advice.setdefault(name, adv)
        f = d.get("file", "?")
        short = f.replace(str(REPO) + "/", "")
        files[short] += 1
        per_class_files[name].add(short)

    total = len(errs)

    if args.baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(
            {"total": total, "files": len(files), "classes": dict(classes)},
            indent=2, sort_keys=True) + "\n")
        print(f"baseline written: {total} errors across {len(files)} files")
        return 0

    if args.check:
        if not BASELINE.exists():
            print("no baseline; run --baseline first")
            return 0
        base = json.loads(BASELINE.read_text())
        if total > base["total"]:
            print(f"REGRESSION: {total} errors, baseline was {base['total']}",
                  file=sys.stderr)
            return 1
        print(f"OK: {total} errors, baseline {base['total']} "
              f"({base['total'] - total} fixed)")
        return 0

    if args.by_file:
        print(f"{total} errors across {len(files)} files — worst first\n")
        for f, n in files.most_common(25):
            print(f"  {n:>4}  {f}")
        return 0

    print(f"{total} errors across {len(files)} files\n")
    for name, n in classes.most_common():
        nf = len(per_class_files[name])
        print(f"{n:>5} errors  {nf:>3} files  {name}")
        print(f"              {advice[name]}")
        print()

    if BASELINE.exists():
        base = json.loads(BASELINE.read_text())
        delta = base["total"] - total
        word = "fixed" if delta >= 0 else "ADDED"
        print(f"baseline {base['total']} → now {total} ({abs(delta)} {word})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
