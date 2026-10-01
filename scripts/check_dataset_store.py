#!/usr/bin/env python3
"""moke has one dataset store, and nothing else in the tree holds a copy of a dataset.

Why this exists
---------------
MK19.1 (2026-10-01). moke had two dataset stores that had drifted apart. The pages used a
230KB `var DATASETS` object inline in templates/index.tkt; the server's /api/datasets read
data/csv through four toke modules and a hand-written catalogue. Five datasets were the same
table in both. Six were different tables under the SAME id: au.medicare was 500 rows and 28
columns on the landing page and 30 rows and 26 columns from the API, and the landing page's
server-inventory card described the API's table while loading the other one. The upload
page carried a third copy of the catalogue, whose header lists matched neither.

Both stores were merged into packages/moke/static/data: manifest.json names each dataset
and points at one CSV file under fixtures/ or snapshots/. The pages fetch it through
static/js/moke-data.js and the server reads the same files through moke.data.registry.
This script keeps it that way.

What it checks
--------------
1. Every manifest entry points at a file in the store that exists, whose sha256 is the one
   the entry records, and whose row and column counts are the entry's.
2. Every CSV file in the store is named by exactly one entry.
3. No two datasets in the store are the same table (headers and rows compared).
4. No file anywhere else in packages/, scripts/ or tests/ holds a copy of a dataset:
   - a CSV/TSV file whose table, or whose header row, is a store dataset's;
   - any text file (template, JavaScript, toke, JSON, ...) that spells out a dataset's
     column list (its first six column names, in order) or one of its records (the first
     six fields of its first, middle or last row, in order);
   - a `var DATASETS =` / `BUILTIN_DATASETS =` object, or a packages/moke/data/csv
     directory, the two shapes the old copies took.

What it does NOT flag
---------------------
A single column name used to address a column (a join key, a chart field): that is a
reference to the data, not a copy of it. This file and test-moke-store.js, which name
the old shapes in order to forbid them.

Usage: check_dataset_store.py [--check]
"""
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STORE = os.path.join(ROOT, "packages", "moke", "static", "data")
MANIFEST = os.path.join(STORE, "manifest.json")
STORE_DIRS = ("fixtures", "snapshots")
SCAN_ROOTS = ("packages", "scripts", "tests")
SELF = {
    os.path.join("scripts", "check_dataset_store.py"),
    os.path.join("packages", "moke", "static", "js", "tests", "test-moke-store.js"),
}
TEXT_EXT = {".tk", ".tkt", ".js", ".mjs", ".json", ".html", ".py", ".sh", ".toml", ".md",
            ".txt", ".csv", ".tsv", ".sql", ".yaml", ".yml"}
RUN = 6  # consecutive column names, or fields, that make a copy rather than a reference


def read_table(text):
    """Headers and rows of a CSV/TSV text, the delimiter sniffed from the header line."""
    if text.startswith("﻿"):
        text = text[1:]
    first = text.split("\n", 1)[0]
    delim = max(",;\t|", key=first.count)
    rows = [r for r in csv.reader(io.StringIO(text), delimiter=delim) if r != []]
    if not rows:
        return [], []
    return [h.strip() for h in rows[0]], rows[1:]


def table_hash(headers, rows):
    return hashlib.sha256(json.dumps([headers, rows], ensure_ascii=False).encode()).hexdigest()


def tracked_files():
    try:
        out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others",
                              "--exclude-standard", "--"] + list(SCAN_ROOTS),
                             cwd=ROOT, capture_output=True, check=True).stdout
        return [p for p in out.decode().split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        found = []
        for top in SCAN_ROOTS:
            for d, _, files in os.walk(os.path.join(ROOT, top)):
                found += [os.path.relpath(os.path.join(d, f), ROOT) for f in files]
        return found


def run_pattern(values):
    """A regex for `values` in order, each optionally quoted, comma/semicolon/tab separated."""
    parts = [r"""["'`]?""" + re.escape(v) + r"""["'`]?""" for v in values]
    return re.compile(r"\s*[,;\t|]\s*".join(parts))


def distinctive(fields):
    """The first RUN fields of a record, if together they are worth matching on."""
    vals = [f for f in fields[:RUN]]
    if len(vals) < RUN or sum(len(v) for v in vals) < 24:
        return None
    return vals


def main(argv):
    quiet = "--check" in argv
    problems = []

    with open(MANIFEST, encoding="utf-8") as f:
        manifest = json.load(f)
    datasets = {}
    for d in manifest.get("datasets", []):
        did = d.get("id", "")
        path = (d.get("data") or {}).get("path", "")
        m = re.match(r"^/static/data/((?:%s)/[^/]+\.csv)$" % "|".join(STORE_DIRS), path)
        if not m:
            problems.append(f"{did}: data.path {path!r} is not a CSV file in the store")
            continue
        rel = m.group(1)
        full = os.path.join(STORE, rel)
        if not os.path.isfile(full):
            problems.append(f"{did}: {path} does not exist")
            continue
        raw = open(full, "rb").read()
        want = d["data"].get("sha256") or (d.get("provenance") or {}).get("snapshot_sha256")
        if hashlib.sha256(raw).hexdigest() != want:
            problems.append(f"{did}: {path} is not the file the manifest hashed (sha256 differs)")
        headers, rows = read_table(raw.decode("utf-8"))
        if len(rows) != d["data"].get("rowcount") or len(headers) != d["data"].get("colcount"):
            problems.append(f"{did}: {path} has {len(rows)} rows and {len(headers)} columns; "
                            f"the manifest says {d['data'].get('rowcount')} and {d['data'].get('colcount')}")
        if did in datasets:
            problems.append(f"{did}: two manifest entries share this id")
        datasets[did] = {"rel": rel, "headers": headers, "rows": rows,
                         "hash": table_hash(headers, rows)}

    # 2. Every store file is named by exactly one entry.
    named = {}
    for did, ds in datasets.items():
        named.setdefault(ds["rel"], []).append(did)
    for sub in STORE_DIRS:
        for name in sorted(os.listdir(os.path.join(STORE, sub))) if os.path.isdir(os.path.join(STORE, sub)) else []:
            if not name.endswith(".csv"):
                continue
            rel = f"{sub}/{name}"
            ids = named.get(rel, [])
            if not ids:
                problems.append(f"static/data/{rel} is in the store but no manifest entry names it")
            elif len(ids) > 1:
                problems.append(f"static/data/{rel} is named by {len(ids)} entries: {', '.join(ids)}")

    # 3. No two datasets in the store are the same table.
    by_hash = {}
    for did, ds in datasets.items():
        by_hash.setdefault(ds["hash"], []).append(did)
    for ids in by_hash.values():
        if len(ids) > 1:
            problems.append(f"the store holds one table twice: {', '.join(sorted(ids))}")

    # 4. No copy anywhere else.
    patterns = []
    for did, ds in datasets.items():
        if len(ds["headers"]) >= RUN:
            patterns.append((did, "its column list", ds["headers"][1], run_pattern(ds["headers"][:RUN])))
        rows = ds["rows"]
        for label, idx in (("its first record", 0), ("a middle record", len(rows) // 2),
                           ("its last record", len(rows) - 1)):
            if 0 <= idx < len(rows):
                vals = distinctive(rows[idx])
                if vals:
                    patterns.append((did, label, vals[1], run_pattern(vals)))
    header_sets = {tuple(ds["headers"]): did for did, ds in datasets.items() if len(ds["headers"]) >= 3}
    hashes = {ds["hash"]: did for did, ds in datasets.items()}
    store_rel = os.path.relpath(STORE, ROOT)

    for rel in tracked_files():
        full = os.path.join(ROOT, rel)
        if rel in SELF or rel.startswith(store_rel + os.sep) or not os.path.isfile(full):
            continue
        if rel.startswith(os.path.join("packages", "moke", "data", "csv") + os.sep):
            problems.append(f"{rel}: packages/moke/data/csv was the second store and is retired")
        ext = os.path.splitext(rel)[1].lower()
        if ext not in TEXT_EXT or not os.path.isfile(full) or os.path.getsize(full) > 8_000_000:
            continue
        try:
            text = open(full, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        if ext in (".csv", ".tsv"):
            headers, rows = read_table(text)
            if table_hash(headers, rows) in hashes:
                problems.append(f"{rel}: a copy of {hashes[table_hash(headers, rows)]}")
                continue
            if tuple(headers) in header_sets:
                problems.append(f"{rel}: has the columns of {header_sets[tuple(headers)]}; "
                                f"a variant of a dataset belongs in the store under its own id")
                continue
        if re.search(r"\b(?:var|let|const)\s+(?:BUILTIN_)?DATASETS\s*=", text):
            problems.append(f"{rel}: declares a DATASETS object; datasets are read from the store")
        hit = None
        for did, label, first, pat in patterns:
            # The substring test is a cheap prefilter; the regex decides.
            if first in text and pat.search(text):
                hit = (did, label)
                break
        if hit:
            problems.append(f"{rel}: spells out {hit[1]} of {hit[0]} — a copy of the dataset, "
                            f"or of its schema, outside the store")

    if problems:
        print("check_dataset_store: %d problem(s). moke's datasets live in packages/moke/static/data "
              "and nowhere else (MK19.1):" % len(problems), file=sys.stderr)
        for p in problems:
            print("  " + p, file=sys.stderr)
        return 1
    if not quiet:
        print(f"check_dataset_store: {len(datasets)} datasets, one copy each, all in the store")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
