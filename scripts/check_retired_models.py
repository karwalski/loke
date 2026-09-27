#!/usr/bin/env python3
"""Find a retired Anthropic model id in product code. A request naming one is refused.

Why this exists
---------------
F5.11b (2026-09-27). The model catalogue, the router's cost and context tables, the
escalation ladder, the local-feasibility advisor, the Anthropic provider's rates, moke's
cost comparison and two templates all named `claude-3-5-sonnet-20241022` and
`claude-3-5-haiku-20241022`. Anthropic's models overview lists both as retired (Sonnet 3.5
on 2025-10-28, Haiku 3.5 on 2026-02-19), so every request loke routed to Anthropic would
have come back as an error document. Nothing noticed, because nothing had ever reached the
provider (F5.11).

tests/unit/models/test_registry.tk checks the catalogue, the ladder and the advisor through
the production modules. This script covers what a toke test cannot reach: templates, static
JavaScript, and a string-matched rate table in a module no test imports.

What counts as retired
----------------------
What Anthropic's models overview and pricing page list as retired on the Claude API, read
2026-09-27: every Claude 2 and Claude 3 id (Claude 3.x included), `claude-instant-*`, and
the dated Sonnet 4, Opus 4 and Opus 4.1 ids with their `-0` aliases. When Anthropic retires
another model, add it here and to `isretired` in the test.

What it does NOT flag
---------------------
toke comments, where the old ids are named on purpose to record what changed. Test
directories, where a retired id is used to assert that it is NOT priced or routed as a
current model. Documentation.

Usage: check_retired_models.py [--check] [root ...]   (default root: packages)
"""
import os
import re
import sys

RETIRED = re.compile(
    r"claude-(?:"
    r"2(?:\.\d)?\b"
    r"|instant-[0-9.]+"
    r"|3[-.][0-9a-z.-]*"
    r"|(?:sonnet|opus)-4-(?:0\b|2025\d{4})"
    r"|opus-4-1\b(?:-\d{8})?"
    r")"
)

EXTENSIONS = {".tk", ".tkt", ".js", ".html", ".json", ".toml", ".py", ".sh"}
SKIP_DIRS = {"build", "tests", "node_modules", ".git"}


def strip_toke_comments(text):
    """Blank out (* ... *) comments, which nest, keeping newlines so line numbers hold."""
    out = []
    depth = 0
    i = 0
    n = len(text)
    while i < n:
        pair = text[i:i + 2]
        if pair == "(*":
            depth += 1
            out.append("  ")
            i += 2
            continue
        if pair == "*)" and depth > 0:
            depth -= 1
            out.append("  ")
            i += 2
            continue
        ch = text[i]
        out.append(ch if depth == 0 or ch == "\n" else " ")
        i += 1
    return "".join(out)


def scan(roots):
    hits = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                if os.path.splitext(name)[1] not in EXTENSIONS:
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                if path.endswith(".tk"):
                    text = strip_toke_comments(text)
                for lineno, line in enumerate(text.splitlines(), 1):
                    for m in RETIRED.finditer(line):
                        hits.append((path, lineno, m.group(0)))
    return hits


def main(argv):
    check = "--check" in argv
    roots = [a for a in argv if not a.startswith("--")] or ["packages"]
    hits = scan(roots)
    for path, lineno, ident in hits:
        print(f"{path}:{lineno}: retired Anthropic model id {ident}")
    if hits and not check:
        print(f"{len(hits)} retired model id(s). Route to a current model; see F5.11b.",
              file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
