#!/usr/bin/env python3
"""Find a call to one of std.json's untyped ABI helpers in product code (LS1.1w).

Why this exists
---------------
`std.json` declares about fifty names in a `gen:"abi"` block, (i64, ...) -> i64, plus a
family of `get*` readers whose parameters are i64. The compiler cannot check either: a str, a
handle and a struct are all accepted, which is how loke came to call `json.getstr` on a
string (T-32, SIGSEGV), `json.getarray` over a decode handle (found nothing, LS1.1t) and
`json.getregulations` (every policy loaded with no rules, X4b.5). toke 3.1.0 checks every
call against the typed .tki, but these names stay untyped in it, so they still compile.

The census of 2026-09-25 counted 93 sites. Re-counted on toke 3.1.0 (2026-10-01) it was 50,
and LS1.1w converted 43 of them to the typed calls (json.dec, json.str, json.i64, json.f64,
json.bool, json.arr) and to shared.jsonobj (strvalue, rawvalue, keys, arrayof, strelems, has,
isnull, escape). One defect was measured among them: core.privacy.template.renderuser
returned "" for any parameter object holding a non-string, and crashed on parameters that were
not JSON (tests/unit/privacy/test_template_render.tk).

ALLOWED below is what remained, file by file, and the reason. It is a ratchet: a file may
have FEWER calls than allowed (say so by lowering the number), never more, and a file not
listed may have none.

    python3 scripts/find_json_untyped.py --check packages
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from find_sql_literal_now import comment_mask  # noqa: E402

REPO = pathlib.Path(__file__).resolve().parent.parent

# std.json at toke 3.1.0 (86c432da), stdlib/json.tki: every export with `gen: "abi"`, and the
# get* readers declared with i64 parameters. Read from the interface, not guessed.
UNTYPED = {
    "arrget", "arrlen", "decode", "encarr", "encbool", "encf64", "encnum", "encode", "encstr",
    "entries", "err", "get", "getarr", "getarray", "getbool", "getf32", "getfloat", "geti32",
    "geti64", "getint", "getobj", "getopt", "getregulations", "getstr", "getstring", "has",
    "haskey", "isnullkey", "keys", "kv", "len", "obj", "ok", "parse", "parsearray",
    "parseobj", "print", "printarr", "quote", "serialize", "set", "setint", "strarr",
    "strarray", "stringify", "tryarr", "trybool", "tryboolkey", "tryfloat", "tryfloatkey",
    "tryint", "tryintkey", "trystr", "trystrkey", "values",
}

# file -> calls allowed, and why they are still there.
ALLOWED = {
    # Owned by a concurrent story (W40, the MCP broker's JSON anonymisation), left for it.
    "packages/mcp-broker/src/server.tk": 4,
    "packages/core/src/mcp/client.tk": 3,
}


def scan(src: str) -> list[tuple[int, str]]:
    aliases = re.findall(r"^i=(\w+):std\.json;", src, re.M)
    if not aliases:
        return []
    mask = comment_mask(src)
    hits = []
    for a in aliases:
        for m in re.finditer(r"\b" + re.escape(a) + r"\.(\w+)\s*\(", src):
            if mask[m.start()] or m.group(1) not in UNTYPED:
                continue
            hits.append((src.count("\n", 0, m.start()) + 1, f"json.{m.group(1)}"))
    return sorted(hits)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("roots", nargs="*", default=["packages"])
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    over = 0
    for root in args.roots:
        base = REPO / root
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.tk")):
            if any(x in f.parts for x in ("_archived-tests", "build")):
                continue
            rel = str(f.relative_to(REPO))
            hits = scan(f.read_text(errors="replace"))
            allowed = ALLOWED.get(rel, 0)
            if len(hits) > allowed:
                over += 1
                for ln, what in hits:
                    print(f"  {rel}:{ln}: {what}")
                print(f"  {rel}: {len(hits)} untyped std.json call(s), {allowed} allowed")
            elif len(hits) < allowed:
                print(f"  note: {rel} has {len(hits)} of its {allowed} allowed; lower ALLOWED")

    if over == 0:
        print("find_json_untyped: OK — no untyped std.json helper beyond the allowance.")
        return 0
    print(f"\n{over} file(s) over. Use json.dec / json.str / json.i64 / json.f64 / json.bool / "
          f"json.arr, or shared.jsonobj (strvalue, rawvalue, keys, arrayof, strelems, has, "
          f"isnull, escape).", file=sys.stderr)
    return 1 if args.check else 0


if __name__ == "__main__":
    sys.exit(main())
