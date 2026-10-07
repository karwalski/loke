#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Every moke route that must refuse a foreign page does so first. (BG1.5)

Why this exists
---------------
moke reaches loke server to server with no Origin header, which loke allows (GA2.6: curl,
the CLI and tests send none). So a moke route that forwards to loke without first making
loke's own refusal (`shared.origin.requestrefused`: a foreign Origin, or a Host that is not
loopback, which is DNS rebinding) lets any page the user has open drive loke through moke.
BG1.4 guarded two routes; BG1.5 found four more without it (/api/stream, /api/ml/propose,
/api/session, /api/health) and guarded every moke API route.

What it checks
--------------
The routes are read from packages/moke/src/_handlers.tk, the tracked file that registers
them, and from every get/post in packages/moke/pages/api, so a handler that is registered
and one that is not yet are both seen. For each handler function the FIRST statement, with
toke comments removed, must be

    if(<alias>.requestrefused(req)){ <<alias>.refuse() }el{};

where <alias> imports shared.origin in that file. A route needs it when

  * its path is under /api/ (every API route, by default), or
  * its page module reaches loke, a model or the network: it, or a moke module it imports
    (transitively), imports shared.reachability or moke.lokerelay, or calls the std.http
    client (postheaders, clientget, clientpost, clientdelete, geturl) or process.spawn.

HTML pages that reach nothing are not guarded (GA2.7: they carry no data of their own).

The one exception is POST /api/proxy (MK19.9), which makes a STRICTER check of its own in
moke.proxy.fetch.handle (Host and Origin must name moke's own port, Sec-Fetch-Site must be
same-origin); its handler must pass the request's Host and Origin headers to fetch.handle.

Usage: check_moke_origin.py [--check] [moke-root]
  --check   quiet; exit 1 when any route lacks the guard (the gate)
"""
import os
import re
import sys

REACH_IMPORTS = ("shared.reachability", "moke.lokerelay")
REACH_CALLS = re.compile(r"\b(?:http\.(?:postheaders|clientget|clientpost|clientdelete|geturl)|process\.spawn)\s*\(")
GUARD = re.compile(r"^if\((\w+)\.requestrefused\(req\)\)\{<(\w+)\.refuse\(\)\}el\{\};")

# Routes that guard themselves differently, and what their handler must contain instead.
EXCEPTIONS = {
    ("POST", "/api/proxy"): (
        re.compile(r'http\.reqheader\(req;"host"\).*http\.reqheader\(req;"origin"\).*fetch\.handle\(', re.S),
        "its own stricter Host/Origin/Sec-Fetch-Site check in moke.proxy.fetch.handle (MK19.9)",
    ),
}


def strip_comments(text):
    """Remove toke (* ... *) comments, which nest. String literals are skipped over so a
    "(*" inside one is not taken as a comment."""
    out, i, depth, n = [], 0, 0, len(text)
    while i < n:
        if depth == 0 and text[i] == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        elif text.startswith("(*", i):
            depth += 1
            i += 2
        elif depth and text.startswith("*)", i):
            depth -= 1
            i += 2
        else:
            if depth == 0:
                out.append(text[i])
            elif text[i] == "\n":
                out.append("\n")
            i += 1
    return "".join(out)


def read(path):
    with open(path, encoding="utf-8") as f:
        return strip_comments(f.read())


def imports(text):
    return dict(re.findall(r"^i=(\w+):([\w.]+);", text, re.M))


def module_name(text):
    m = re.search(r"^m=([\w.]+);", text, re.M)
    return m.group(1) if m else None


def function_body(text, name):
    """The text of f=<name>(...){ ... } up to its matching brace, or None."""
    m = re.search(r"^f=%s\([^)]*\)[^{]*\{" % re.escape(name), text, re.M)
    if not m:
        return None
    i, depth = m.end(), 1
    while i < len(text) and depth:
        c = text[i]
        if c == '"':
            j = i + 1
            while j < len(text) and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        depth += {"{": 1, "}": -1}.get(c, 0)
        i += 1
    return text[m.end():i - 1]


def load_modules(moke):
    """Every moke module (src and pages): name -> (path, text)."""
    mods = {}
    for sub in ("src", "pages"):
        for dirpath, dirnames, filenames in os.walk(os.path.join(moke, sub)):
            dirnames.sort()
            for fn in sorted(filenames):
                if fn.endswith(".tk"):
                    path = os.path.join(dirpath, fn)
                    text = read(path)
                    name = module_name(text)
                    if name:
                        mods[name] = (path, text)
    return mods


def reaching(mods):
    """The set of moke modules that reach loke, a model or the network, directly or through
    a moke module they import."""
    direct = set()
    for name, (_, text) in mods.items():
        imps = imports(text).values()
        if any(i in REACH_IMPORTS for i in imps) or REACH_CALLS.search(text):
            direct.add(name)
    reach, changed = set(direct), True
    while changed:
        changed = False
        for name, (_, text) in mods.items():
            if name not in reach and any(i in reach for i in imports(text).values()):
                reach.add(name)
                changed = True
    return reach


def routes(moke, mods):
    """(method, path, module, function) for every registered route, plus every get/post in
    pages/api whose module no registration names."""
    handlers = read(os.path.join(moke, "src", "_handlers.tk"))
    alias = imports(handlers)
    found = []
    for meth, path, h in re.findall(r'http\.(get|post|put|delete)\("([^"]+)";&(\w+)\)', handlers):
        body = function_body(handlers, h) or ""
        m = re.search(r"<(\w+)\.(\w+)\(req\)", body)
        if not m or m.group(1) not in alias:
            found.append((meth.upper(), path, None, h))
            continue
        found.append((meth.upper(), path, alias[m.group(1)], m.group(2)))
    seen = {(mod, fn) for _, _, mod, fn in found}
    for name, (path, text) in sorted(mods.items()):
        if not name.startswith("page.moke.api."):
            continue
        for fn in re.findall(r"^f=(get|post|put|delete)\(", text, re.M):
            if (name, fn) not in seen:
                found.append((fn.upper(), "/" + name[len("page.moke."):].replace(".", "/") + " (unregistered)", name, fn))
    return found


def judge(moke):
    mods = load_modules(moke)
    reach = reaching(mods)
    rows, bad = [], []
    regs = routes(moke, mods)
    if not regs:
        bad.append(("?", "?", "no route registrations were found in src/_handlers.tk"))
    for meth, path, mod, fn in regs:
        if mod is None or mod not in mods:
            bad.append((meth, path, "its handler %s does not resolve to a moke page module" % fn))
            continue
        fpath, text = mods[mod]
        rel = os.path.relpath(fpath, moke)
        reaches = mod in reach
        needs = path.startswith("/api/") or reaches
        body = function_body(text, fn)
        if body is None:
            bad.append((meth, path, "%s has no function %s" % (rel, fn)))
            continue
        flat = re.sub(r"\s+", "", body)
        g = GUARD.match(flat)
        origin_alias = {a for a, m in imports(text).items() if m == "shared.origin"}
        guarded = bool(g and g.group(1) == g.group(2) and g.group(1) in origin_alias)
        exc = EXCEPTIONS.get((meth, path))
        if guarded:
            how = "guarded"
        elif exc and exc[0].search(body):
            how = "guarded by " + exc[1]
        elif needs:
            why = "reaches loke, a model or the network" if reaches else "is an API route"
            bad.append((meth, path, "%s %s, and its first statement is not the shared.origin refusal" % (rel, why)))
            how = "UNGUARDED"
        else:
            how = "not guarded: an HTML page that reaches nothing"
        rows.append((meth, path, rel, "reaches" if reaches else "-", how))
    return rows, bad


def main(argv):
    check = "--check" in argv
    args = [a for a in argv if not a.startswith("--")]
    moke = args[0] if args else "packages/moke"
    rows, bad = judge(moke)
    if not check:
        for meth, path, rel, reaches, how in rows:
            print("%-6s %-26s %-28s %-8s %s" % (meth, path, rel, reaches, how))
    for meth, path, why in bad:
        print("check_moke_origin: %s %s %s (BG1.5)" % (meth, path, why), file=sys.stderr)
    if not check and not bad:
        print("check_moke_origin: OK, every moke API route and every route that reaches loke makes the shared.origin refusal first (%d routes)" % len(rows))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
