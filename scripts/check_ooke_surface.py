#!/usr/bin/env python3
"""loke's dependence on ooke is the surface measured in F10.8, and it agrees with the pin.

F10.8 counted the drift in ooke's shared interfaces at 2.0.0 (`store` 40 changes, `template` 33,
`router` 15). Measured on ooke 3.0.0-rc.2 (2026-10-07), loke's own code imports four ooke
modules and calls five functions:

    ooke.template   tplrenderfile    every page module under packages/*/pages
    ooke.config     configload       the generated server mains
    ooke.serve      serverun         the generated server mains
    ooke.handlers   registerall      the generated server mains (the registry is loke's own,
                                     generated from its pages by ooke's gen_handlers.sh)

It imports neither `ooke.store` nor `ooke.router`. `core.feedback.store` and
`core.router.router` are loke modules of the same name, not copies of ooke's. The compiler
already holds the call shapes to the pinned interfaces; what it does not hold is the TEMPLATE
language, because a `.tkt` file is read at run time. rc.2's engine ignores a directive it does
not know, so `{! endblock !}` left a block open and /tabs rendered the base layout with no
content, with no error anywhere (docs/upstream/ooke-issues.md O-4).

This check fails when:
  1. loke imports an ooke module outside MEASURED: adopting one is a deliberate change to
     F10.8's table, not a side effect;
  2. a call through an ooke import names a function the pinned `ooke.<module>.tki` does not
     export, or passes a different number of arguments;
  3. a template uses a `{! directive !}` or a `| filter` that the pinned engine
     (`$OOKE_DIR/src/template.tk`) does not implement. The supported names are read from the
     engine's source, not listed here, so moving the pin re-derives them;
  4. a template opens more blocks than it closes, or closes more than it opens;
  5. an app's ooke.toml sets a key in [site], [build], [server], [log] or [tls] that the
     pinned ooke does not read (rc.2 reads `inlinecss`, so `inline_css = false` left the
     default, true), or still carries the [store] table 3.x removed. The keys are read out of
     ooke's source, as the template names are.

    python3 scripts/check_ooke_surface.py           # report the surface and any finding
    python3 scripts/check_ooke_surface.py --check   # exit 1 on any finding

OOKE_DIR is read from the environment, defaulting as scripts/build_loke.sh does.
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
MEASURED = {"template", "config", "serve", "handlers"}
SOURCES = [REPO / "packages", REPO / "scripts" / "build_loke.sh", REPO / "scripts" / "build_trees.sh"]
SKIP_DIRS = {"build", "node_modules", ".git"}
IMPORT = re.compile(r"\bi=([a-z][a-z0-9]*):ooke\.([a-z][a-z0-9]*);")
DIRECTIVE = re.compile(r"\{!(.*?)!\}", re.S)
EXPR = re.compile(r"\{=(.*?)=\}", re.S)
CONFIG_SECTIONS = ("site", "build", "server", "log", "tls")


def ooke_dir() -> pathlib.Path:
    return pathlib.Path(os.environ.get("OOKE_DIR") or (pathlib.Path.home() / "tk" / "toke-ooke"))


def exports(odir: pathlib.Path, module: str) -> dict[str, int] | None:
    tki = odir / "src" / f"ooke.{module}.tki"
    if not tki.is_file():
        return None
    data = json.loads(tki.read_text())
    return {e["name"]: len(e["params"]) for e in data["exports"] if e.get("kind") == "func"}


def engine_names(odir: pathlib.Path) -> tuple[set[str], set[str]]:
    src = (odir / "src" / "template.tk").read_text()
    return set(re.findall(r'dname=="([a-z]+)"', src)), set(re.findall(r'fname=="([a-z]+)"', src))


def config_keys(odir: pathlib.Path) -> dict[str, set[str]]:
    """The keys ooke reads from each of the tables its config loader names."""
    read: dict[str, set[str]] = {s: set() for s in CONFIG_SECTIONS}
    for src in (odir / "src").glob("*.tk"):
        for section, key in re.findall(r'toml\.[a-z0-9]+\(([a-z]+);"([a-z_]+)"\)', src.read_text()):
            if section in read:
                read[section].add(key)
    return read


def arity(text: str, start: int) -> int:
    """Top-level arguments of the call whose `(` is at text[start]."""
    depth, n, seen, i, instr = 0, 0, False, start, False
    while i < len(text):
        c = text[i]
        if instr:
            if c == "\\":
                i += 2
                continue
            if c == '"':
                instr = False
        elif c == '"':
            instr, seen = True, True
        elif c in "([{":
            depth += 1
            if depth > 1:
                seen = True
        elif c in ")]}":
            depth -= 1
            if depth == 0:
                return n + 1 if seen else 0
        elif c == ";" and depth == 1:
            n += 1
        elif not c.isspace() and depth >= 1:
            seen = True
        i += 1
    return -1


def source_files():
    for root in SOURCES:
        if root.is_file():
            yield root
            continue
        for p in sorted(root.rglob("*.tk")):
            if not SKIP_DIRS.intersection(p.relative_to(REPO).parts):
                yield p


def template_files():
    for p in sorted((REPO / "packages").glob("*/templates/**/*.tkt")):
        if not SKIP_DIRS.intersection(p.relative_to(REPO).parts):
            yield p


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    odir = ooke_dir()
    if not (odir / "src" / "template.tk").is_file():
        print(f"check_ooke_surface: no ooke source at {odir}/src (set OOKE_DIR)", file=sys.stderr)
        return 2

    findings: list[str] = []
    surface: dict[tuple[str, str], int] = {}
    cache: dict[str, dict[str, int] | None] = {}
    for path in source_files():
        text = path.read_text(errors="replace")
        rel = path.relative_to(REPO)
        aliases = dict(IMPORT.findall(text))
        for alias, module in aliases.items():
            if module not in MEASURED:
                findings.append(f"{rel}: imports ooke.{module}, outside the surface F10.8 measured")
            if module not in cache:
                cache[module] = exports(odir, module)
            table = cache[module]
            if table is None:
                findings.append(f"{rel}: ooke.{module} has no interface at {odir}/src")
                continue
            for m in re.finditer(rf"\b{alias}\.([a-z][a-z0-9]*)\(", text):
                fn = m.group(1)
                line = text.count("\n", 0, m.start()) + 1
                surface[(module, fn)] = surface.get((module, fn), 0) + 1
                if fn not in table:
                    findings.append(f"{rel}:{line}: ooke.{module}.{fn} is not exported by the pinned ooke")
                    continue
                got = arity(text, m.end() - 1)
                if got != table[fn]:
                    findings.append(f"{rel}:{line}: ooke.{module}.{fn} takes {table[fn]} argument(s), called with {got}")

    directives, filters = engine_names(odir)
    ntpl = 0
    for path in template_files():
        ntpl += 1
        text = path.read_text(errors="replace")
        rel = path.relative_to(REPO)
        opened = closed = 0
        for m in DIRECTIVE.finditer(text):
            body = m.group(1).strip()
            name = body.split("(", 1)[0].strip()
            line = text.count("\n", 0, m.start()) + 1
            if name not in directives:
                findings.append(f"{rel}:{line}: {{! {body} !}} is not a directive the pinned engine knows; it renders as nothing")
            opened += name == "block"
            closed += name == "end"
        for m in EXPR.finditer(text):
            if "|" in m.group(1):
                f = m.group(1).split("|", 1)[1].strip()
                if f not in filters:
                    line = text.count("\n", 0, m.start()) + 1
                    findings.append(f"{rel}:{line}: filter '{f}' is not one the pinned engine knows; it escapes instead")
        if opened != closed:
            findings.append(f"{rel}: {opened} block(s) opened, {closed} closed; an unclosed block renders as nothing")

    read = config_keys(odir)
    for path in sorted((REPO / "packages").glob("*/ooke.toml")):
        rel = path.relative_to(REPO)
        section = ""
        for n, line in enumerate(path.read_text().splitlines(), 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            if s.startswith("["):
                section = s.strip("[]").strip()
                if section == "store":
                    findings.append(f"{rel}:{n}: [store] is gone in ooke 3.x and is ignored")
                continue
            key = s.split("=", 1)[0].strip()
            if section in read and key not in read[section]:
                findings.append(f"{rel}:{n}: [{section}] {key} is not read by the pinned ooke (a misspelt key leaves the default in force)")

    if not args.check:
        print(f"ooke at {odir}")
        for (module, fn), n in sorted(surface.items()):
            print(f"  ooke.{module}.{fn}: {n} call site(s)")
        print(f"  {ntpl} templates; engine directives {sorted(directives)}; filters {sorted(filters)}")
    for f in findings:
        print(f"  {f}", file=sys.stderr)
    if findings:
        print(f"check_ooke_surface: {len(findings)} finding(s)", file=sys.stderr)
        return 1
    if not args.check:
        print("check_ooke_surface: ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
