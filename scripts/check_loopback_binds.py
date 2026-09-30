#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Every listening socket loke's code opens is bound to loopback. (GA2.5)

Why this exists
---------------
GA2.5, reopened 2026-09-24: measured with lsof, the server listened on `*:11430`, every
interface, because nothing read `[server] host` and toke's glue passed a NULL host (T-43).
ooke rc.2 binds `[server] host` (default 127.0.0.1) and F10.39 gave the three net.listen
servers an explicit "127.0.0.1:port". scripts/smoke_serve.sh and smoke_serve_moke.sh check
the two ooke servers with lsof while they run (port_owner.sh, assert_loopback_only). The cli
proxy, the MCP broker and the MCP server have no binary of their own to smoke (their mains
are kept off the loke-cli link), so their bind addresses are checked here, in the source:

  1. every `net.listen(` takes a string literal starting "127.0.0.1:", or a name the same
     file binds to one (`let listenaddr="127.0.0.1:...`);
  2. no port-only `http.serve*(` call: toke's port-only serve functions bind every
     interface (ooke's config.tk says so), and only the `...on(host;...)` forms take a host;
  3. every ooke.toml with a `[server]` table sets `host` explicitly, to 127.0.0.1, ::1 or
     localhost. ooke's default is 127.0.0.1, but a default is one upstream change away from
     being something else; the file says what loke means.

toke comments are ignored, and so are tests and build output.

Usage: check_loopback_binds.py [--check] [root ...]   (default roots: packages src)
"""
import os
import re
import sys

SKIP_DIRS = {"build", "tests", "node_modules", ".git", "_archived-tests"}
LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}

LISTEN = re.compile(r"\bnet\.listen\(\s*([^;)]*)")
SERVE = re.compile(r"\bhttp\.(serve[a-z]*)\(")
LET_LOOPBACK = r'\blet\s+{name}\s*=\s*"127\.0\.0\.1:'


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


def check_tk(path, text):
    hits = []
    code = strip_toke_comments(text)
    for lineno, line in enumerate(code.splitlines(), 1):
        for m in LISTEN.finditer(line):
            arg = m.group(1).strip()
            if arg.startswith('"127.0.0.1:'):
                continue
            if re.fullmatch(r"[a-z][a-z0-9]*", arg) and re.search(LET_LOOPBACK.format(name=arg), code):
                continue
            hits.append((path, lineno, "net.listen(%s) is not bound to 127.0.0.1" % arg))
        for m in SERVE.finditer(line):
            if not m.group(1).endswith("on"):
                hits.append((path, lineno, "http.%s( binds every interface; use the ...on(host;...) form with 127.0.0.1" % m.group(1)))
    return hits


def check_toml(path, text):
    section = None
    has_server = False
    host = None
    host_line = 0
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]").strip()
            has_server = has_server or section == "server"
            continue
        if section == "server":
            m = re.match(r'host\s*=\s*"([^"]*)"', line)
            if m:
                host, host_line = m.group(1), lineno
    if not has_server:
        return []
    if host is None:
        return [(path, 0, "[server] has no host; set host = \"127.0.0.1\" explicitly")]
    if host not in LOOPBACK_HOSTS:
        return [(path, host_line, "[server] host = \"%s\" is not loopback" % host)]
    return []


def scan(roots):
    hits = []
    for root in roots:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not (name.endswith(".tk") or name == "ooke.toml"):
                    continue
                try:
                    with open(path, encoding="utf-8") as f:
                        text = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                hits += check_tk(path, text) if name.endswith(".tk") else check_toml(path, text)
    return hits


def main(argv):
    check = "--check" in argv
    roots = [a for a in argv if not a.startswith("--")] or ["packages", "src"]
    hits = scan(roots)
    for path, lineno, what in hits:
        print(f"{path}:{lineno}: {what}")
    if hits and not check:
        print(f"{len(hits)} listener(s) not bound to loopback only; see GA2.5.", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
