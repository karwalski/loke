#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Judge a request body scripts/lib/http_recorder.py received, with Python's strict parser. (MK6.13)

Usage: json_field.py <log-file>.bodies <request-path> <field-path> <expected>
       json_field.py --body <json-text> <field-path> <expected>

Takes the LAST request to <request-path> (e.g. /api/generate) from the recorder's `.bodies`
file, parses its body with json.loads, which refuses a raw control character inside a string
(so does Ollama's Go decoder), follows <field-path> (dot-separated keys and array indices,
e.g. `messages.1.content`) and prints `ok` if the value there equals <expected> exactly.
Otherwise it prints what went wrong: no such request, a body that is not strict JSON (with
the parser's message), a missing field, or the value that was found instead.

The second form judges a text given directly, for an answer a module builds rather than a
request it sends. An empty <field-path> compares the whole decoded value.

<expected> arrives through argv, so it carries newlines, tabs and quotes unaltered, and the
comparison is of characters, after the body has been decoded: a body that escaped a
character wrongly fails it just as one that left it raw fails the parse.
"""
import json, sys


def lastbody(bodies, reqpath):
    """The body of the last request to reqpath, or a reason string and None."""
    found = None
    try:
        with open(bodies) as f:
            for line in f:
                method, path, body = json.loads(line)
                if path.split("?")[0] == reqpath:
                    found = body
    except OSError as e:
        return "no bodies file: %s" % e, None
    if found is None:
        return "no request to %s" % reqpath, None
    return "", found


def judge(text, field, expected):
    try:
        v = json.loads(text)
    except ValueError as e:
        return "not strict JSON: %s" % e
    for k in field.split(".") if field else []:
        try:
            v = v[int(k)] if isinstance(v, list) else v[k]
        except (KeyError, IndexError, ValueError, TypeError):
            return "no field %s" % field
    return "ok" if v == expected else "value differs: %r" % (v,)


if sys.argv[1] == "--body":
    print(judge(sys.argv[2], sys.argv[3], sys.argv[4]))
else:
    why, body = lastbody(sys.argv[1], sys.argv[2])
    print(why if body is None else judge(body, sys.argv[3], sys.argv[4]))
