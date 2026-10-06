#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""docs/privacy-filters.md documents only privacy config keys the code reads. (F3b.11)

The document's key table (between the privacy-config-keys markers) names each key and the file
that reads it. This fails when:

  - a key in the table is not a string literal in the file named beside it (a documented key
    nothing reads, or one renamed in the code and not in the document); a section key such as
    `privacy.consensus_strategy` is looked for whole, as shared.config passes it to std.toml;
    an array-of-tables header such as `[[privacy.layers]]` by its name, `privacy.layers`;
  - a key core.privacy.layerconfig or core.privacy.entityrouting accepts (their `knownkey`) is
    not in the table, or a strategy core.privacy.consensus knows (`isknown`) is not named in
    the document (a key or strategy added in code and not documented).

It checks that a key is READ, by finding its literal in the reader's source; it does not show
what is done with it. The tests the table names do that.

    python3 scripts/check_privacy_doc_keys.py           # exit 0 when they agree
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DOC = ROOT / "docs" / "privacy-filters.md"
PRIV = ROOT / "packages" / "core" / "src" / "privacy"


def table(doc):
    m = re.search(r"<!-- privacy-config-keys:start -->(.*?)<!-- privacy-config-keys:end -->", doc, re.S)
    if not m:
        return None
    rows = []
    for line in m.group(1).splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or not cells[0].startswith("`"):
            continue
        key = cells[0].strip("`")
        files = re.findall(r"`(packages/[^`]+\.tk)`", cells[1])
        rows.append((key, files))
    return rows


def literal(key):
    """The string the reader's source must hold for key."""
    m = re.fullmatch(r"\[\[(.+)\]\]", key)
    return m.group(1) if m else key


def function_body(src, name):
    m = re.search(r"\nf=%s\(.*?\n(?=f=|\Z)" % re.escape(name), src, re.S)
    return m.group(0) if m else ""


def main():
    doc = DOC.read_text(encoding="utf-8")
    rows = table(doc)
    errors = []
    if not rows:
        print("check_privacy_doc_keys: no key table between the privacy-config-keys markers in %s" % DOC, file=sys.stderr)
        return 1
    documented = set()
    for key, files in rows:
        documented.add(key)
        if not files:
            errors.append("%s: the table names no reading file" % key)
            continue
        for f in files:
            p = ROOT / f
            if not p.exists():
                errors.append("%s: %s does not exist" % (key, f))
            elif '"%s"' % literal(key) not in p.read_text(encoding="utf-8"):
                errors.append('%s: documented as read by %s, which has no "%s" literal' % (key, f, literal(key)))

    for mod in ("layer_config.tk", "entity_routing.tk"):
        body = function_body((PRIV / mod).read_text(encoding="utf-8"), "knownkey")
        keys = re.findall(r'str\.eq\(key;"([^"]+)"\)', body)
        if not keys:
            errors.append("%s: knownkey not found, so its keys cannot be compared with the document" % mod)
        for k in keys:
            if k not in documented:
                errors.append("%s accepts the key %s, which the document's key table does not list" % (mod, k))

    body = function_body((PRIV / "consensus.tk").read_text(encoding="utf-8"), "isknown")
    strategies = re.findall(r'str\.eq\(strategy;"([^"]+)"\)', body)
    if not strategies:
        errors.append("consensus.tk: isknown not found, so its strategies cannot be compared with the document")
    for s in strategies:
        if "`%s`" % s not in doc:
            errors.append("consensus.tk knows the strategy %s, which the document does not name" % s)

    if errors:
        for e in errors:
            print("check_privacy_doc_keys: " + e, file=sys.stderr)
        return 1
    print("check_privacy_doc_keys: %d documented keys are read where the document says; %d strategies named"
          % (len(rows), len(strategies)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
