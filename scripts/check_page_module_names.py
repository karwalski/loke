#!/usr/bin/env python3
"""Every ooke page module is named after its path (F10.15a).

`pages/api/approve.tk` declared `m=page.api.approve` while its sibling `pages/api/health.tk`
declared `m=browser.pages.api.health`, and the generated `_handlers.tk` imported both spellings.
Two prefixes for one kind of module is how a handler gets registered under a name nothing else
uses, or not registered at all.

The rule, derived from the path under an app's `pages/` directory:

    packages/browser/pages/api/health.tk   ->  m=page.api.health
    packages/moke/pages/api/health.tk      ->  m=page.moke.api.health

browser is loke's own app and takes the bare `page.` prefix; any other app inserts its name, so
two apps' pages cannot collide at link time.

    python3 scripts/check_page_module_names.py --check
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
APPS = {"browser": "page", "moke": "page.moke"}
DECL = re.compile(r"^m=([A-Za-z0-9_.]+);", re.M)


def expected(app: str, rel: pathlib.PurePath) -> str:
    parts = list(rel.with_suffix("").parts)
    return ".".join([APPS[app]] + parts)


def scan(root: pathlib.Path) -> list[tuple[pathlib.Path, str, str]]:
    bad = []
    for app in APPS:
        pages = root / "packages" / app / "pages"
        if not pages.is_dir():
            continue
        for f in sorted(pages.rglob("*.tk")):
            m = DECL.search(f.read_text(encoding="utf-8"))
            want = expected(app, f.relative_to(pages))
            got = m.group(1) if m else "(no m= declaration)"
            if got != want:
                bad.append((f, got, want))
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 on any mismatch, quietly")
    ap.add_argument("--root", default=str(REPO))
    a = ap.parse_args()
    root = pathlib.Path(a.root).resolve()
    bad = scan(root)
    if not bad:
        print("check_page_module_names: OK — every page module is named after its path.")
        return 0
    if not a.check:
        print(f"{len(bad)} page module(s) not named after their path (F10.15a):")
        for f, got, want in bad:
            print(f"  {f.relative_to(root)}: m={got}; expected m={want};")
    return 1


if __name__ == "__main__":
    sys.exit(main())
