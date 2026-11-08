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
per-day layer row matches a GROUP BY of the same rows. For the 24h, 7d and all windows the
same is judged over the rows since the window start the route reports, which must be now
minus the window, and each layer's latency p50/p95/p99 must be the nearest rank of the
database's completed, timed scans. An unknown window is refused with 400.

`evaluate` also posts a labelled file in the JSON-array format and judges the scores, and
refuses a malformed array (400) and one over 65536 bytes (413).

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
    ok(d.get("not_accepted") == [], "with no route configured, nothing is listed as not accepted by routing",
       json.dumps(d.get("not_accepted"))[:200])
    code, raw = call(base + "/api/evaluate", json.dumps({"text": ""}))
    ok(code == 400 and '"ok":false' in raw, "an empty text is refused with 400", "[%s] %s" % (code, raw[:200]))
    labelled(base, secret, text, start)


def labelled(base, secret, text, start):
    """F3b.9: a labelled file scored through {"labelled": ...}, in the JSON-array format."""
    entries = [{"text": text, "entities": [{"start": start, "end": start + len(secret), "type": "EMAIL"}]},
               {"text": "nothing personal in this one", "entities": []}]
    code, raw = call(base + "/api/evaluate", json.dumps({"labelled": json.dumps(entries)}))
    ok(code == 200, "POST /api/evaluate with a labelled JSON array answers 200", "[%s] %s" % (code, raw[:300]))
    try:
        d = json.loads(raw)
    except ValueError:
        ok(False, "the labelled reply is JSON", raw[:200])
        return
    ok(d.get("ok") is True and d.get("labelled") is True and d.get("format") == "json-array"
       and d.get("texts") == 2 and d.get("labelled_entities") == 1,
       "it read the JSON array: two texts, one labelled entity", raw[:300])
    scores = {r["layer"]: r for r in d.get("scores", [])}
    rx = scores.get("regex", {})
    ok(rx.get("scored") is True and rx.get("recall") == "100.00%" and rx.get("tp") == 1 and rx.get("fn") == 0
       and rx.get("texts") == 2 and rx.get("of") == 2,
       "the regex layer scanned both texts and found the labelled email (recall 100.00%, tp 1, fn 0)", json.dumps(rx))
    down = [r for r in d.get("scores", []) if not r.get("scored")]
    ok(all(r.get("recall") is None and r.get("tp") is None and r.get("reason") for r in down),
       "every layer that scanned nothing (%s) is not scored, with null figures and a reason"
       % (",".join(r["layer"] for r in down) or "none"), json.dumps(down)[:300])
    ok(d.get("scores", [{}])[-1].get("layer") == "consensus", "the consensus outcome is scored last", raw[:300])
    leaked = [p for p in (secret, "jane.smoke", "example.com", "nothing personal") if p in raw]
    ok(not leaked, "no text or value is in the labelled reply", ",".join(leaked))
    bad = json.dumps([{"text": text, "entities": [{"start": 0, "end": 9999, "type": "EMAIL"}]}])
    code, raw = call(base + "/api/evaluate", json.dumps({"labelled": bad}))
    ok(code == 400 and '"ok":false' in raw and "entry 1, entity 1 needs whole-number" in raw and secret not in raw,
       "a malformed array is refused with 400, naming the entry and entity at fault", "[%s] %s" % (code, raw[:300]))
    code, raw = call(base + "/api/evaluate", json.dumps({"labelled": "[" + " " * 65536 + "]"}))
    ok(code == 413 and '"ok":false' in raw, "a labelled file over 65536 bytes is refused with 413", "[%s] %s" % (code, raw[:200]))


def percentile(sorted_ms, p):
    n = len(sorted_ms)
    rank = min(max((p * n + 99) // 100, 1), n)
    return sorted_ms[rank - 1]


def layerwindow(base, dbpath, window, span_ms):
    """F3b.10: GET /api/layermetrics?window=..., judged against the database with the
    window start the route reports, which must itself be now minus the window."""
    import time
    code, raw = call(base + "/api/layermetrics?window=" + window)
    try:
        d = json.loads(raw)
    except ValueError:
        ok(False, "GET /api/layermetrics?window=%s answers JSON" % window, "[%s] %s" % (code, raw[:200]))
        return
    since = d.get("since_ms")
    now = int(time.time() * 1000)
    want = 0 if span_ms == 0 else now - span_ms
    ok(code == 200 and d.get("period") == window and isinstance(since, int) and abs(since - want) < 120000,
       "window %s: 200, and it starts at now minus the window (%s)" % (window, since), raw[:200])
    con = sqlite3.connect(dbpath)
    n = con.execute("SELECT COUNT(*) FROM privacy_layer_metrics WHERE kind='consensus' AND created_at>=?", (since,)).fetchone()[0]
    ok(d.get("requests") == n and d.get("recorded") is (n > 0),
       "window %s: requests is the database's count of requests since then (%d)" % (window, n), raw[:200])
    rows = con.execute("SELECT strftime('%Y-%m-%d', created_at/1000, 'unixepoch'), layer_id, COUNT(*), SUM(detections), "
                       "SUM(accepted) FROM privacy_layer_metrics WHERE kind='layer' AND created_at>=? GROUP BY 1, 2 ORDER BY 1, 2",
                       (since,)).fetchall()
    got = [(r["day"], r["layer"], r["requests"], r["detections"], r["accepted"]) for r in d.get("by_layer_day", [])]
    ok(got == [tuple(r) for r in rows], "window %s: every per-day layer row matches the database" % window,
       "%s vs %s" % (got[:4], rows[:4]))
    lat = {}
    for layer, ms in con.execute("SELECT layer_id, duration_ms FROM privacy_layer_metrics WHERE kind='layer' AND "
                                 "state='completed' AND duration_ms IS NOT NULL AND created_at>=? ORDER BY 1, 2", (since,)):
        lat.setdefault(layer, []).append(ms)
    want_lat = [{"layer": k, "samples": len(v), "p50_ms": percentile(v, 50), "p95_ms": percentile(v, 95),
                 "p99_ms": percentile(v, 99)} for k, v in sorted(lat.items())]
    ok(d.get("latency") == want_lat, "window %s: each layer's latency p50/p95/p99 is the nearest rank of the database's "
       "completed, timed scans (%d layer(s))" % (window, len(want_lat)), "%s vs %s" % (d.get("latency"), want_lat))
    # F3b.8 (2): the organisation policy's violations and overrides, from the audit trail.
    op = d.get("org_policy") or {}
    nv = con.execute("SELECT COUNT(*) FROM audit_log WHERE event_type='org_policy_violation' AND created_at>=?", (since,)).fetchone()[0]
    no = con.execute("SELECT COUNT(*) FROM audit_log WHERE event_type='org_policy_override' AND created_at>=?", (since,)).fetchone()[0]
    try:
        na = con.execute("SELECT COUNT(*) FROM governance_alert_ledger WHERE kind='privacy_org_policy' AND last_at>=?", (since,)).fetchone()[0]
    except sqlite3.Error:
        na = -1
    ok(op.get("violations") == nv and op.get("overrides") == no and len(op.get("alerts", [])) == min(na, 50),
       "window %s: org_policy counts the database's org_policy_violation (%d) and org_policy_override (%d) rows and "
       "lists its %d policy alert(s)" % (window, nv, no, na), raw[:300])


def layermetrics(base, dbpath):
    for window, span in (("24h", 86400000), ("7d", 604800000), ("all", 0)):
        layerwindow(base, dbpath, window, span)
    code, raw = call(base + "/api/layermetrics?window=1y")
    ok(code == 400 and "use 24h, 7d, 30d or all" in raw, "an unknown window is refused with 400", "[%s] %s" % (code, raw[:200]))
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
    # F3b.10: the per-entity record. Each request has one entity row per detection its
    # consensus resolved (the consensus row's `resolved`), and an entity row names layers, a
    # type and an action: its layer_id is ids only, never a value.
    short = con.execute("SELECT COUNT(*) FROM privacy_layer_metrics c WHERE c.kind='consensus' AND c.resolved <> "
                        "(SELECT COUNT(*) FROM privacy_layer_metrics e WHERE e.correlation_id=c.correlation_id AND e.kind='entity')").fetchone()[0]
    ents = con.execute("SELECT COUNT(*) FROM privacy_layer_metrics WHERE kind='entity'").fetchone()[0]
    odd = con.execute("SELECT COUNT(*) FROM privacy_layer_metrics WHERE kind='entity' AND (mode NOT IN ('mask','pass') OR "
                      "state<>'resolved' OR layer_id GLOB '*[@=]*')").fetchone()[0]
    ok(short == 0 and odd == 0, "every request has an entity row per resolved detection (%d rows), each naming layer "
       "ids, a type and mask or pass" % ents, "%d request(s) short, %d odd row(s)" % (short, odd))


if __name__ == "__main__":
    if sys.argv[1] == "evaluate":
        evaluate(sys.argv[2])
    else:
        layermetrics(sys.argv[2], sys.argv[3])
    sys.exit(1 if fails else 0)
