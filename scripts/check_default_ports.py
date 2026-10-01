#!/usr/bin/env python3
"""check_default_ports.py — no two services default to the same port (F3b.12).

Found by F3b.3: the privacy-filter sidecar and mcp-toke both defaulted to 11435. With both at
their defaults only one could bind, and if mcp-toke held the port, the privacy-filter layer's
health GET and /detect POST went to mcp-toke. Nothing in the gate could have noticed, because
each default is a literal in its own file.

SERVICES below is the one place that says which port each service defaults to. For every
service it names the files that declare that default and a pattern that reads the port out of
each. The check fails when:
  * a declaration is missing (a pattern matches nothing: the code moved and this table did not);
  * a declaration disagrees with the table (one site changed and the others did not);
  * two services share a port, unless the pair is in KNOWN_SHARED with the row that owns it;
  * the "Default ports" table in docs/architecture.md disagrees with SERVICES.

    python3 scripts/check_default_ports.py          # report, exit 1 on any failure
"""
from __future__ import annotations

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent

# service -> (default port, [(file, regex with one group capturing the port)])
SERVICES: dict[str, tuple[int, list[tuple[str, str]]]] = {
    "loke API": (11430, [
        ("packages/shared/src/config.tk", r"^\s*port:(\d+);"),
        ("packages/browser/ooke.toml", r"^port = (\d+)"),
    ]),
    "loke CLI proxy": (11431, [
        ("packages/cli/src/proxy.tk", r"^\s*port:(\d+);"),
    ]),
    "moke": (11432, [
        ("packages/moke/ooke.toml", r"^port = (\d+)"),
    ]),
    "Ollama": (11434, [
        ("packages/shared/src/config.tk", r'ollamaurl:"http://localhost:(\d+)"'),
        ("packages/core/src/privacy/filter_registry.tk", r'defaultollamaurl\(\):str\{ <"http://127\.0\.0\.1:(\d+)"'),
    ]),
    "privacy-filter sidecar": (11435, [
        ("packages/privacy-filter/server.py", r"len\(sys\.argv\) > 1 else (\d+)"),
        ("packages/shared/src/config.tk", r'pfurl:"http://127\.0\.0\.1:(\d+)"'),
        ("packages/core/src/privacy/filter_registry.tk", r'defaultpfurl\(\):str\{ <"http://127\.0\.0\.1:(\d+)"'),
        ("packages/moke/templates/chat.tkt", r"PRIVACY_URL = window\.PRIVACY_URL \|\| 'http://127\.0\.0\.1:(\d+)'"),
        ("packages/moke/templates/confirm.tkt", r"PRIVACY_URL = window\.PRIVACY_URL \|\| 'http://127\.0\.0\.1:(\d+)'"),
    ]),
    "mcp-broker": (11436, [
        ("packages/mcp-broker/src/server.tk", r"defaultport\(\):i32\{ <\((\d+) as i32\)"),
        ("packages/mcp-broker/src/main.tk", r"mcp broker starting on port (\d+)"),
    ]),
    "mcp-memory": (11437, [
        ("packages/mcp-broker/src/registry.tk", r'name:"mcp-memory"; host:"localhost"; port:(\d+);'),
        ("packages/moke/src/mcp/broker_status.tk", r'name:"loke-memory";\s*transport:"http";\s*url:"http://127\.0\.0\.1:(\d+)"'),
    ]),
    "mcp-toke": (11460, [
        ("packages/mcp-toke/src/server.tk", r'host:"127\.0\.0\.1";\s*port:(\d+);\s*servername:"loke-mcp"'),
        ("packages/mcp-broker/src/registry.tk", r'name:"mcp-toke"; host:"localhost"; port:(\d+);'),
        ("packages/moke/src/mcp/broker_status.tk", r'name:"loke-mcp-toke";\s*transport:"http";\s*url:"http://127\.0\.0\.1:(\d+)"'),
    ]),
    "Presidio": (5000, [
        ("packages/shared/src/config.tk", r'presidiourl:"http://localhost:(\d+)"'),
        ("packages/core/src/privacy/filter_registry.tk", r'defaultpresidiourl\(\):str\{ <"http://127\.0\.0\.1:(\d+)"'),
    ]),
    "LLMLingua": (5001, [
        ("packages/shared/src/config.tk", r'llmlinguaurl:"http://localhost:(\d+)"'),
    ]),
    "RouteLLM sidecar": (11461, [
        ("packages/core/src/router/routellm.tk", r'defaulturl\(\):str\{ <"http://127\.0\.0\.1:(\d+)"'),
    ]),
}

# Pairs that share a default today, each owned by a backlog row. A pair not listed here fails.
# Empty since F3b.14 moved the RouteLLM sidecar off the CLI proxy's 11431.
KNOWN_SHARED: dict[frozenset[str], str] = {
}

DOC = "docs/architecture.md"
DOC_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|\s*(\d+)\s*\|")


def doctable(text: str) -> dict[str, int]:
    """The rows of the table under the "Default ports" heading."""
    rows: dict[str, int] = {}
    inside = False
    for line in text.splitlines():
        if line.startswith("#"):
            inside = line.lstrip("#").strip().lower().startswith("default ports")
            continue
        if inside:
            m = DOC_ROW.match(line)
            if m:
                rows[m.group(1).strip("` ")] = int(m.group(2))
    return rows


def main() -> int:
    problems: list[str] = []
    for service, (port, sites) in SERVICES.items():
        for rel, pattern in sites:
            path = REPO / rel
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as e:
                problems.append(f"{service}: cannot read {rel}: {e}")
                continue
            found = [int(x) for x in re.findall(pattern, text, flags=re.MULTILINE)]
            if not found:
                problems.append(f"{service}: no default port found in {rel} (pattern {pattern!r}); "
                                "update SERVICES if the declaration moved")
            for f in found:
                if f != port:
                    problems.append(f"{service}: {rel} declares {f}, SERVICES says {port}")

    byport: dict[int, list[str]] = {}
    for service, (port, _) in SERVICES.items():
        byport.setdefault(port, []).append(service)
    for port, names in sorted(byport.items()):
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pair = frozenset({names[i], names[j]})
                if pair in KNOWN_SHARED:
                    print(f"  known: {names[i]} and {names[j]} share {port} ({KNOWN_SHARED[pair]})")
                else:
                    problems.append(f"{names[i]} and {names[j]} both default to port {port}")

    documented = doctable((REPO / DOC).read_text(encoding="utf-8"))
    for service, (port, _) in SERVICES.items():
        if documented.get(service) != port:
            problems.append(f"{DOC} 'Default ports' table: {service} is "
                            f"{documented.get(service, 'missing')}, SERVICES says {port}")
    for service in documented:
        if service not in SERVICES:
            problems.append(f"{DOC} 'Default ports' table lists {service}, which SERVICES does not")

    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        print(f"check_default_ports: FAIL — {len(problems)} problem(s)", file=sys.stderr)
        return 1
    print(f"check_default_ports: OK — {len(SERVICES)} services, distinct defaults "
          f"(except {len(KNOWN_SHARED)} known pair(s)), every declaration agrees")
    return 0


if __name__ == "__main__":
    sys.exit(main())
