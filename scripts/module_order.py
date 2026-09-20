#!/usr/bin/env python3
"""Print loke's toke modules in dependency order (story F10.7).

Why the build needs this
------------------------
A module's interface can only be emitted once the interfaces of everything it
imports already exist. Emitting in alphabetical order and repeating until the count
stops growing reached 33 of 199 and stalled: a chain deeper than the number of
passes never resolves, and repetition cannot fix an ordering problem.

So the order is computed instead. Each `.tk` file declares its module with `m=` and
its imports with `i=alias:module.path`; that is the whole graph, and a topological
sort of it is the order the compiler needs.

Cycles are reported rather than hidden. A cycle between two toke modules cannot be
resolved by ordering at all, and knowing that is the useful output — the modules in
it are printed last so the build still attempts them.

Usage
-----
    python3 scripts/module_order.py packages/core/src packages/shared/src
    python3 scripts/module_order.py --cycles packages/core/src
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys

M_RE = re.compile(r"^m=([A-Za-z0-9_.]+)\s*;", re.M)
I_RE = re.compile(r"^i=[A-Za-z0-9_]+:([A-Za-z0-9_.]+)\s*;", re.M)


def scan(roots: list[pathlib.Path]) -> tuple[dict[str, pathlib.Path], dict[str, set[str]]]:
    owner: dict[str, pathlib.Path] = {}
    deps: dict[str, set[str]] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for f in sorted(root.rglob("*.tk")):
            text = f.read_text(errors="replace")
            m = M_RE.search(text)
            if not m:
                continue
            mod = m.group(1)
            # A duplicate module declaration is a real problem, but not this
            # script's to solve: first one wins and the second is reported.
            if mod in owner:
                print(f"# duplicate module {mod}: {f} and {owner[mod]}", file=sys.stderr)
                continue
            owner[mod] = f
            deps[mod] = set(I_RE.findall(text))
    # Keep only edges to modules we actually own. std.* and ooke.* come from the
    # toolchain and are always available.
    for mod in deps:
        deps[mod] = {d for d in deps[mod] if d in owner}
    return owner, deps


def toposort(owner: dict, deps: dict) -> tuple[list[str], list[list[str]]]:
    """Kahn's algorithm, with the remaining strongly-connected nodes as cycles."""
    indeg = {m: 0 for m in owner}
    rdeps: dict[str, set[str]] = {m: set() for m in owner}
    for m, ds in deps.items():
        for d in ds:
            rdeps[d].add(m)
            indeg[m] += 1

    ready = sorted(m for m, n in indeg.items() if n == 0)
    order: list[str] = []
    while ready:
        m = ready.pop(0)
        order.append(m)
        for dependent in sorted(rdeps[m]):
            indeg[dependent] -= 1
            if indeg[dependent] == 0:
                ready.append(dependent)
                ready.sort()

    stuck = [m for m, n in indeg.items() if n > 0]
    cycles = find_cycles(stuck, deps) if stuck else []
    return order, cycles


def find_cycles(stuck: list[str], deps: dict) -> list[list[str]]:
    """Report the cycles among the nodes that never reached in-degree zero."""
    stuck_set = set(stuck)
    seen: set[str] = set()
    cycles: list[list[str]] = []
    for start in sorted(stuck_set):
        if start in seen:
            continue
        path: list[str] = []
        on_path: set[str] = set()

        def walk(node: str) -> bool:
            if node in on_path:
                cycles.append(path[path.index(node):] + [node])
                return True
            if node in seen:
                return False
            seen.add(node)
            path.append(node)
            on_path.add(node)
            for d in sorted(deps.get(node, ())):
                if d in stuck_set and walk(d):
                    break
            path.pop()
            on_path.discard(node)
            return False

        walk(start)
    return cycles


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("roots", nargs="+")
    ap.add_argument("--cycles", action="store_true", help="report cycles only")
    args = ap.parse_args()

    repo = pathlib.Path(__file__).resolve().parent.parent
    roots = [(repo / r) if not pathlib.Path(r).is_absolute() else pathlib.Path(r)
             for r in args.roots]
    owner, deps = scan(roots)
    order, cycles = toposort(owner, deps)

    if args.cycles:
        if not cycles:
            print(f"no cycles among {len(owner)} modules")
            return 0
        print(f"{len(cycles)} cycle(s) among {len(owner)} modules:")
        for c in cycles:
            print("  " + " -> ".join(c))
        return 1

    # Ordered modules first, then anything in a cycle so the build still tries it.
    stuck = [m for m in owner if m not in set(order)]
    for mod in order + sorted(stuck):
        print(owner[mod])
    if stuck:
        print(f"# {len(stuck)} module(s) in cycles, emitted last", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
