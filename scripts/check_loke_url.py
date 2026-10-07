#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""No moke page reads window.LOKE_URL by truthiness. (BG1.4)

Why this exists
---------------
base.tkt sets window.LOKE_URL to '' when moke's own origin answers for loke, meaning "send
loke's requests to this origin". Five pages read it as `window.LOKE_URL || 'http://...'`, and
'' is falsy, so every one of their requests went cross-origin to loke anyway. Measured in
headless Chrome by BG1.1: window.LOKE_URL was '' and the dashboard's Phase 1 request went to
http://127.0.0.1:11430/api/pipeline. The fix reads it with `??` (or an explicit undefined
test); this keeps `||`, `? :` on its truthiness and `!window.LOKE_URL` from coming back.

Flagged, in every .tkt, .js, .html and .tk file under the roots (default packages/moke),
with JavaScript comments ignored:

  * `window.LOKE_URL ||`             the original bug
  * `window.LOKE_URL ?`  (not `??`)  a ternary on its truthiness
  * `!window.LOKE_URL`               a negated truthiness test
  * `if (window.LOKE_URL)`           an if on its truthiness
  * `window.LOKE_URL &&`             a guard on its truthiness

Usage: check_loke_url.py [--check] [root ...]
  --check   quiet; exit 1 when anything is flagged (the gate)
"""
import os
import re
import sys

EXTS = (".tkt", ".js", ".html", ".tk")
SKIP_DIRS = {"build", "node_modules", ".git"}

PATTERNS = [
    (re.compile(r"window\.LOKE_URL\s*\|\|"), "`window.LOKE_URL ||` takes '' (same origin) as missing"),
    (re.compile(r"window\.LOKE_URL\s*\?(?![?.])"), "a ternary on window.LOKE_URL's truthiness takes '' as missing"),
    (re.compile(r"!\s*window\.LOKE_URL\b(?!\s*[!=]=)"), "`!window.LOKE_URL` takes '' as missing"),
    (re.compile(r"\bif\s*\(\s*window\.LOKE_URL\s*\)"), "`if (window.LOKE_URL)` takes '' as missing"),
    (re.compile(r"window\.LOKE_URL\s*&&"), "`window.LOKE_URL &&` takes '' as missing"),
]

BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
LINE_COMMENT = re.compile(r"(^|[^:\\])//[^\n]*")


def strip_js_comments(text):
    """Blank out /* */ and // comments, keeping line numbers. A `//` after a colon (a URL)
    is kept. Good enough for a lint over moke's own scripts."""
    text = BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return LINE_COMMENT.sub(lambda m: m.group(1), text)


def scan(roots):
    found = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for name in sorted(filenames):
                if not name.endswith(EXTS):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                for lineno, line in enumerate(strip_js_comments(text).split("\n"), 1):
                    for rx, why in PATTERNS:
                        if rx.search(line):
                            found.append((path, lineno, line.strip(), why))
    return found


def main(argv):
    check = "--check" in argv
    roots = [a for a in argv if not a.startswith("--")] or ["packages/moke"]
    found = scan(roots)
    if not check:
        for path, lineno, line, why in found:
            print("%s:%d: %s\n    %s" % (path, lineno, why, line))
        if found:
            print("check_loke_url: %d use(s) of window.LOKE_URL by truthiness; read it with ?? (BG1.4)" % len(found))
        else:
            print("check_loke_url: OK, no truthiness read of window.LOKE_URL under %s" % ", ".join(roots))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
