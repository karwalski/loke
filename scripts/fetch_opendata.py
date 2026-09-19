#!/usr/bin/env python3
"""fetch_opendata.py — reproducibly fetch and attribute government open data.

Story MK19.4. Standard library only, matching the rest of the project's scripts.

Why this exists
---------------
moke currently ships 15 datasets labelled "Government Open Data" that contain
fabricated names and identifiers. Replacing them with real snapshots creates two
obligations this script exists to discharge:

1. **Attribution.** Committing a government CSV into a public repository is
   redistribution, and the common licence for Australian government data
   requires attribution. So every snapshot gets a licence sidecar and a manifest
   entry, and the repository NOTICE is extended.

2. **Reproducibility.** A snapshot with no record of where it came from, when,
   or what was done to it is not evidence of anything. Every fetch records the
   portal package and resource, the retrieval date, a SHA-256, and an explicit
   list of every transformation applied.

The licence guard is the point
------------------------------
The script reads the licence the portal itself declares and **aborts if it does
not match what the recipe expects**. That is what stops an unattributable or
non-redistributable file reaching git. Not every dataset on an open-data portal
is openly licensed — some energy market data, for instance, is published under
terms that do not permit redistribution — and the failure mode without this
guard is silent and legally consequential.

Usage
-----
    ./scripts/fetch_opendata.py --list
    ./scripts/fetch_opendata.py --dataset abs.labour_force
    ./scripts/fetch_opendata.py --all
    ./scripts/fetch_opendata.py --all --check      # report drift, write nothing
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
RECIPES = REPO / "scripts" / "opendata_recipes.json"
DATA_DIR = REPO / "packages" / "moke" / "static" / "data"
SNAPSHOT_DIR = DATA_DIR / "snapshots"
MANIFEST = DATA_DIR / "manifest.json"

USER_AGENT = "loke-opendata-fetch/1.0 (+https://github.com/karwalski/loke)"
TIMEOUT = 60

# Budgets. A demo dataset that makes the page slow defeats its own purpose, and
# an unbounded download is a way to commit something nobody reviews.
MAX_ROWS = 5_000
MAX_BYTES = 500_000
MAX_TOTAL_BYTES = 3_000_000

# Licence identifiers that permit redistribution with attribution. Anything not
# on this list must be explicitly allowed in the recipe, with a reason.
REDISTRIBUTABLE = {
    "cc-by", "cc-by-4.0", "cc-by-3.0", "cc-by-sa", "cc-by-sa-4.0",
    "cc-zero", "cc0-1.0", "odc-by", "odc-pddl", "notspecified-open",
}


class FetchError(RuntimeError):
    pass


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.read()
    except urllib.error.HTTPError as e:
        raise FetchError(f"HTTP {e.code} for {url}") from e
    except urllib.error.URLError as e:
        raise FetchError(f"cannot reach {url}: {e.reason}") from e


def ckan_package(base: str, package_id: str) -> dict:
    """Resolve a package through the portal API, so a moved resource URL still works."""
    url = f"{base.rstrip('/')}/package_show?{urllib.parse.urlencode({'id': package_id})}"
    raw = get(url)
    try:
        doc = json.loads(raw)
    except json.JSONDecodeError:
        # The most common cause is the wrong API base path, which returns an
        # HTML 404 page. Say so, because the message is otherwise baffling.
        raise FetchError(
            f"{url} did not return JSON. Check the API base — for data.gov.au it is "
            f"/data/api/3/action, not /api/3/action."
        )
    if not doc.get("success"):
        raise FetchError(f"portal reported failure for package {package_id}")
    return doc["result"]


def check_licence(pkg: dict, recipe: dict) -> tuple[str, str]:
    """Abort unless the portal's declared licence matches the recipe's expectation.

    Returns (licence_id, licence_url). This function is the whole reason the
    script exists, so it fails rather than warns.
    """
    declared = (pkg.get("license_id") or "").strip().lower()
    title = pkg.get("license_title") or ""
    url = pkg.get("license_url") or ""
    expected = recipe["expect_licence"].strip().lower()

    if not declared:
        raise FetchError(
            f"portal declares no licence for '{pkg.get('title')}'. Refusing to "
            f"commit a snapshot with no licence. If the terms are known from "
            f"elsewhere, record them in the recipe with allow_unlisted_licence "
            f"and a reason."
        )

    if declared != expected:
        raise FetchError(
            f"licence mismatch for '{pkg.get('title')}':\n"
            f"    portal declares : {declared}  ({title})\n"
            f"    recipe expects  : {expected}\n"
            f"  Refusing to fetch. Either the dataset's terms changed, or the "
            f"recipe is wrong. Verify the terms before updating the recipe — "
            f"this guard exists so a licence change is noticed rather than "
            f"silently absorbed."
        )

    if declared not in REDISTRIBUTABLE and not recipe.get("allow_unlisted_licence"):
        raise FetchError(
            f"licence '{declared}' is not on the known-redistributable list, and "
            f"this snapshot would be committed to a public repository. If the "
            f"terms do permit redistribution with attribution, set "
            f"allow_unlisted_licence with a reason in the recipe. If they do "
            f"not, this dataset must be live-fetch only with no committed "
            f"snapshot."
        )

    return declared, url


def pick_resource(pkg: dict, recipe: dict) -> dict:
    """Find the CSV resource named by the recipe."""
    want_id = recipe.get("resource_id")
    want_name = (recipe.get("resource_name") or "").lower()
    csvs = []
    for r in pkg.get("resources", []):
        if want_id and r.get("id") == want_id:
            return r
        fmt = (r.get("format") or "").lower()
        if fmt == "csv":
            csvs.append(r)
    if want_name:
        for r in csvs:
            if want_name in (r.get("name") or "").lower():
                return r
    if not csvs:
        raise FetchError(
            f"no CSV resource found for '{pkg.get('title')}'. Formats present: "
            + ", ".join(sorted({(r.get('format') or '?') for r in pkg.get('resources', [])}))
        )
    if len(csvs) > 1 and not (want_id or want_name):
        names = ", ".join((r.get("name") or r.get("id", "?"))[:40] for r in csvs[:5])
        raise FetchError(
            f"{len(csvs)} CSV resources for '{pkg.get('title')}' and the recipe "
            f"names none. Set resource_id or resource_name. Candidates: {names}"
        )
    return csvs[0]


def transform(raw: bytes, recipe: dict) -> tuple[str, list[str], int, int]:
    """Apply the recipe's transformations. Returns (csv_text, notes, rows, cols).

    Every edit is recorded in `notes`, which becomes the manifest's
    `transformations` list. A snapshot that differs from its source without
    saying how is not attributable.
    """
    notes: list[str] = []

    text = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            if enc != "utf-8":
                notes.append(f"Decoded as {enc} (source was not UTF-8)")
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise FetchError("could not decode the file in any of the attempted encodings")

    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        raise FetchError("file contains no rows")
    header, body = rows[0], rows[1:]

    # Column selection.
    keep = recipe.get("columns")
    if keep:
        missing = [c for c in keep if c not in header]
        if missing:
            raise FetchError(
                f"recipe names columns absent from the source: {missing}. "
                f"Source columns: {header[:12]}"
            )
        idx = [header.index(c) for c in keep]
        header = [header[i] for i in idx]
        body = [[r[i] if i < len(r) else "" for i in idx] for r in body]
        notes.append(f"Selected columns: {', '.join(keep)}")

    # Header renaming, applied after selection.
    rename = recipe.get("rename") or {}
    if rename:
        header = [rename.get(h, h) for h in header]
        notes.append("Renamed headers: " + ", ".join(f"{k} to {v}" for k, v in rename.items()))

    # Row filter — a simple equality or minimum on one column, deliberately
    # limited so a recipe stays reviewable.
    filt = recipe.get("filter")
    if filt:
        col, op, val = filt["column"], filt["op"], filt["value"]
        if col not in header:
            raise FetchError(f"filter column '{col}' not present after selection")
        ci = header.index(col)
        before = len(body)
        if op == "eq":
            body = [r for r in body if ci < len(r) and r[ci] == val]
        elif op == "gte":
            body = [r for r in body if ci < len(r) and r[ci] >= val]
        else:
            raise FetchError(f"unsupported filter op '{op}' (use eq or gte)")
        notes.append(f"Filtered {col} {op} {val}: {before} rows to {len(body)}")

    if recipe.get("sort_by") in header:
        ci = header.index(recipe["sort_by"])
        body.sort(key=lambda r: r[ci] if ci < len(r) else "")
        notes.append(f"Sorted by {recipe['sort_by']}")

    # Row cap. Recorded, because a truncated dataset that does not say so is
    # misleading about what it represents.
    cap = min(int(recipe.get("max_rows", MAX_ROWS)), MAX_ROWS)
    if len(body) > cap:
        before = len(body)  # captured before truncation, or the message is wrong
        if recipe.get("tail"):
            body = body[-cap:]
            notes.append(f"Kept the most recent {cap} rows of {before} (row cap)")
        else:
            body = body[:cap]
            notes.append(f"Truncated to the first {cap} of {before} rows (row cap)")

    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(header)
    w.writerows(body)
    return out.getvalue(), notes, len(body), len(header)


def licence_sidecar(recipe: dict, pkg: dict, lic_id: str, lic_url: str, retrieved: str) -> str:
    org = (pkg.get("organization") or {}).get("title") or recipe.get("publisher", "unknown")
    return (
        f"{recipe['name']}\n"
        f"{'=' * len(recipe['name'])}\n\n"
        f"Publisher      : {org}\n"
        f"Portal         : {recipe['portal']}\n"
        f"Package        : {recipe['package_id']}\n"
        f"Source         : {pkg.get('url') or recipe['portal']}\n"
        f"Licence        : {lic_id}\n"
        f"Licence URL    : {lic_url or 'see portal record'}\n"
        f"Retrieved      : {retrieved}\n\n"
        f"Attribution\n"
        f"-----------\n"
        f"{recipe['attribution']}\n\n"
        f"This file is a derived snapshot, not the original. See the manifest entry\n"
        f"for '{recipe['id']}' for the full list of transformations applied.\n\n"
        f"This sidecar duplicates information held in the manifest deliberately, so\n"
        f"that the CSV remains self-describing if it is ever copied out of this\n"
        f"repository.\n"
    )


def fetch_one(recipe: dict, *, check_only: bool) -> dict:
    print(f"\n{recipe['id']}  ({recipe['name']})")
    pkg = ckan_package(recipe["api_base"], recipe["package_id"])
    lic_id, lic_url = check_licence(pkg, recipe)
    print(f"  licence  : {lic_id}  (matches recipe)")

    res = pick_resource(pkg, recipe)
    url = res.get("url")
    if not url:
        raise FetchError("selected resource has no URL")
    print(f"  resource : {(res.get('name') or res.get('id'))[:56]}")

    raw = get(url)
    csv_text, notes, rows, cols = transform(raw, recipe)
    data = csv_text.encode("utf-8")

    if len(data) > MAX_BYTES:
        raise FetchError(
            f"snapshot is {len(data):,} bytes, over the {MAX_BYTES:,} budget. "
            f"Tighten the recipe's columns, filter or max_rows."
        )

    digest = hashlib.sha256(data).hexdigest()
    retrieved = datetime.now(timezone.utc).isoformat()
    target = SNAPSHOT_DIR / f"{recipe['id']}.csv"

    existing = hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    changed = existing != digest
    print(f"  rows     : {rows:,} x {cols} cols, {len(data):,} bytes")
    print(f"  sha256   : {digest[:16]}...  {'CHANGED' if changed and existing else 'new' if not existing else 'unchanged'}")
    for n in notes:
        print(f"  applied  : {n}")

    if check_only:
        return {"id": recipe["id"], "changed": changed, "written": False}

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    (SNAPSHOT_DIR / f"{recipe['id']}.LICENCE.txt").write_text(
        licence_sidecar(recipe, pkg, lic_id, lic_url, retrieved), encoding="utf-8"
    )

    entry = {
        "id": recipe["id"],
        "name": recipe["name"],
        "short_name": recipe.get("short_name", recipe["name"]),
        "description": recipe["description"],
        "domain": recipe["domain"],
        "category": "Government Open Data",
        "kind": "snapshot",
        "provenance": {
            "publisher": (pkg.get("organization") or {}).get("title") or recipe.get("publisher"),
            "portal": recipe["portal"],
            "package_id": recipe["package_id"],
            "resource_id": res.get("id"),
            "source_url": pkg.get("url") or recipe["portal"],
            "licence": lic_id,
            "licence_url": lic_url,
            "attribution": recipe["attribution"],
            "retrieved_at": retrieved,
            "snapshot_sha256": digest,
            "transformations": notes,
        },
        "data": {
            "format": "csv",
            "path": f"/static/data/snapshots/{recipe['id']}.csv",
            "rowcount": rows,
            "colcount": cols,
            "bytes": len(data),
        },
        "sensitivity": recipe.get("sensitivity", "PUBLIC"),
        "pii": recipe.get("pii", []),
        "pii_note": recipe.get("pii_note", ""),
        "prompts": recipe.get("prompts", {}),
        "relationships": recipe.get("relationships", []),
    }
    return {"id": recipe["id"], "changed": changed, "written": True, "entry": entry}


def write_manifest(entries: list[dict]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {"schema_version": 1, "datasets": []}
    if MANIFEST.is_file():
        try:
            existing = json.loads(MANIFEST.read_text())
        except json.JSONDecodeError:
            print("  manifest was not valid JSON; rewriting", file=sys.stderr)
    by_id = {d["id"]: d for d in existing.get("datasets", [])}
    for e in entries:
        by_id[e["id"]] = e
    doc = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).date().isoformat(),
        "note": (
            "Snapshots are committed so the demo works offline. Every entry records "
            "its licence and every transformation applied to the source. 'kind' "
            "distinguishes a real snapshot from a synthetic fixture — do not label "
            "synthetic data as government open data."
        ),
        "datasets": sorted(by_id.values(), key=lambda d: d["id"]),
    }
    MANIFEST.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    total = sum(d.get("data", {}).get("bytes", 0) for d in doc["datasets"])
    print(f"\nmanifest: {len(doc['datasets'])} dataset(s), {total:,} bytes total")
    if total > MAX_TOTAL_BYTES:
        print(f"  WARNING: over the {MAX_TOTAL_BYTES:,} total budget", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", action="append", help="recipe id; repeatable")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", action="store_true",
                    help="report what would change; write nothing")
    args = ap.parse_args()

    if not RECIPES.is_file():
        print(f"no recipe file at {RECIPES}", file=sys.stderr)
        return 1
    recipes = json.loads(RECIPES.read_text())["recipes"]

    if args.list:
        for r in recipes:
            note = "" if not r.get("snapshot_prohibited") else "  [LIVE-FETCH ONLY]"
            print(f"  {r['id']:<26} {r['domain']:<12} {r['name'][:44]}{note}")
        return 0

    wanted = recipes if args.all else [r for r in recipes if r["id"] in (args.dataset or [])]
    if not wanted:
        print("nothing selected; use --all, --dataset ID, or --list", file=sys.stderr)
        return 2

    entries, failures = [], []
    for r in wanted:
        if r.get("snapshot_prohibited"):
            print(f"\n{r['id']}: SKIPPED — {r.get('snapshot_prohibited')}")
            continue
        try:
            res = fetch_one(r, check_only=args.check)
            if res.get("entry"):
                entries.append(res["entry"])
        except FetchError as e:
            print(f"  FAILED: {e}", file=sys.stderr)
            failures.append(r["id"])

    if entries and not args.check:
        write_manifest(entries)

    if failures:
        print(f"\n{len(failures)} failed: {', '.join(failures)}", file=sys.stderr)
        return 1
    print("\ndone")
    return 0


if __name__ == "__main__":
    sys.exit(main())
