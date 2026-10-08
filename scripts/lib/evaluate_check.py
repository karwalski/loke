#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Judge the bodies of loke's POST /api/evaluate (F3b.9) and GET /api/layermetrics (F3b.10).

Usage:
  evaluate_check.py evaluate <base-url>
  evaluate_check.py layermetrics <base-url> <loke.db>

`evaluate` posts a text holding an email address and judges the reply: valid JSON; the regex
layer completed and reports an EMAIL detection at the address's byte span with its
placeholder; every layer that did not complete has detections null, never a number; the
consensus names its voters and decisions; and neither the address nor any part of it is
anywhere in the body. An empty text is refused with 400.

`layermetrics` reads the route and judges it against the database file directly with
Python's sqlite3, an independent count of privacy_layer_metrics: requests equals the number
of consensus rows; with none, recorded is false and no figure is given; with some, each
per-day layer row matches a GROUP BY of the same rows.

Prints `  ok   ...` per check and `  FAIL ...` to stderr; exits 1 on any failure.
"""
import json
import sqlite3
import sys
import urllib.request

fails = 0


def ok(cond, label, detail=""):
    global fails
    if cond:
        print("  ok   " + label)
    else:
        fails += 1
        print("  FAIL " + label + (": " + detail if detail else ""), file=sys.stderr)


def call(url, body=None):
    req = urllib.request.Request(url, data=None if body is None else body.encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def evaluate(base):
    secret = "jane.smoke@example.com"
    text = "please write to " + secret + " today"
    start = text.index(secret)
    code, raw = call(base + "/api/evaluate", json.dumps({"text": text}))
    ok(code == 200, "POST /api/evaluate answers 200", "[%s] %s" % (code, raw[:200]))
    try:
        d = json.loads(raw)
    except ValueError:
        ok(False, "POST /api/evaluate answers JSON", raw[:200])
        return
    ok(d.get("ok") is True and d.get("values_shown") is False and d.get("text_bytes") == len(text),
       "it is ok, says values are not shown, and measured the text", raw[:200])
    layers = {l["id"]: l for l in d.get("layers", [])}
    rx = layers.get("regex", {})
    want = {"start": start, "end": start + len(secret)}
    hit = [h for h in rx.get("hits", []) if h.get("placeholder", "").lower() == "[email]" and want in h.get("spans", [])]
    ok(rx.get("completed") is True and isinstance(rx.get("detections"), int) and len(hit) == 1,
       "the regex layer completed and reports [email] at %d-%d" % (want["start"], want["end"]), json.dumps(rx)[:300])
    down = [l for l in layers.values() if not l.get("completed")]
    names = ",".join(l["id"] for l in down) or "none"
    ok(all(l.get("detections") is None and l.get("state") in ("unavailable", "failed", "disabled") and l.get("reason")
           for l in down),
       "every layer that did not scan (%s) has detections null and says why" % names, json.dumps(down)[:300])
    c = d.get("consensus", {})
    ok("regex" in c.get("voters", []) and any(x.get("reported_by") == "regex" and x.get("action") in ("mask", "pass")
                                              for x in c.get("decisions", [])),
       "the consensus lists regex as a voter and decides on its detection", json.dumps(c)[:300])
    leaked = [p for p in (secret, "jane.smoke", "example.com") if p in raw]
    ok(not leaked, "no detected value, or part of one, is in the body", ",".join(leaked))
    code, raw = call(base + "/api/evaluate", json.dumps({"text": ""}))
    ok(code == 400 and '"ok":false' in raw, "an empty text is refused with 400", "[%s] %s" % (code, raw[:200]))


def layermetrics(base, dbpath):
    code, raw = call(base + "/api/layermetrics")
    ok(code == 200, "GET /api/layermetrics answers 200", "[%s] %s" % (code, raw[:200]))
    try:
        d = json.loads(raw)
    except ValueError:
        ok(False, "GET /api/layermetrics answers JSON", raw[:200])
        return
    con = sqlite3.connect(dbpath)
    n = con.execute("SELECT COUNT(*) FROM privacy_layer_metrics WHERE kind='consensus'").fetchone()[0]
    ok(d.get("measured") is True and d.get("requests") == n,
       "requests is the database's own count of recorded requests (%d)" % n, raw[:200])
    if n == 0:
        ok(d.get("recorded") is False and d.get("agreement") is None and d.get("by_layer_day") == [],
           "with none recorded it says recorded false and gives no figure", raw[:200])
        return
    rows = con.execute("SELECT strftime('%Y-%m-%d', created_at/1000, 'unixepoch'), layer_id, COUNT(*), SUM(detections), "
                       "SUM(accepted) FROM privacy_layer_metrics WHERE kind='layer' GROUP BY 1, 2 ORDER BY 1, 2").fetchall()
    got = [(r["day"], r["layer"], r["requests"], r["detections"], r["accepted"]) for r in d.get("by_layer_day", [])]
    ok(d.get("recorded") is True and got == [tuple(r) for r in rows],
       "every per-day layer row matches the database (%d rows)" % len(rows), "%s vs %s" % (got[:4], rows[:4]))


if __name__ == "__main__":
    if sys.argv[1] == "evaluate":
        evaluate(sys.argv[2])
    else:
        layermetrics(sys.argv[2], sys.argv[3])
    sys.exit(1 if fails else 0)
