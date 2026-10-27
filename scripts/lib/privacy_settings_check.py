#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Judge loke's privacy settings routes over HTTP: /api/privacylayers (F3b.2), /api/privacymodels
(F3b.7) and the policy-applied layers in /api/health (F3b.8).

Usage:
  privacy_settings_check.py <base-url> <loke-home>

<loke-home> is the HOME the server under test runs with (a throwaway one): the check writes its
.loke/config.toml and .loke/loke.policy.json, reads back what the server wrote, and removes all
three files it touched at the end.

Judged on the bodies and on the files, not on status alone:
  * a save keeps every other line of config.toml and is what GET and /api/health then report
    (the priority order and the switched-off layer);
  * switching the regex layer off is refused (400) naming the rule, and config.toml is unchanged;
  * under a policy requiring presidio with a 0.4 ceiling, switching presidio off is refused
    (409), and /api/health reports presidio's threshold as 0.4 with policy_changed naming it;
  * a model is registered through the route, written to privacy-models.json, listed, and
    reported as a layer by /api/health; a mapping to an unknown type is refused (400).

Prints `  ok   ...` per check and `  FAIL ...` to stderr; exits 1 on any failure.
"""
import json
import os
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
    req = urllib.request.Request(url, data=None if body is None else json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"},
                                 method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def parsed(text):
    try:
        return json.loads(text)
    except ValueError:
        return None


def layer(i, enabled=True, priority=1, mode="detect-and-mask", threshold=0, types=()):
    return {"id": i, "enabled": enabled, "priority": priority, "mode": mode,
            "confidence_threshold": threshold, "entity_filter": list(types)}


def by_id(items, key="id"):
    return {x.get(key): x for x in items or []}


def main():
    base, home = sys.argv[1], sys.argv[2]
    lokedir = os.path.join(home, ".loke")
    os.makedirs(lokedir, exist_ok=True)
    conf = os.path.join(lokedir, "config.toml")
    policy = os.path.join(lokedir, "loke.policy.json")
    models = os.path.join(lokedir, "privacy-models.json")
    for p in (conf, policy, models):
        if os.path.exists(p):
            ok(False, "the smoke HOME starts without " + os.path.basename(p))
            return
    start = '[privacy]\nconsensus_strategy = "most-restrictive"\n# the smoke keeps this line\n\n[[privacy.layers]]\nid = "ner"\npriority = 9\n'
    with open(conf, "w") as f:
        f.write(start)
    try:
        run(base, conf, policy, models)
    finally:
        for p in (conf, policy, models):
            if os.path.exists(p):
                os.remove(p)


def run(base, conf, policy, models):
    code, text = call(base + "/api/privacylayers")
    d = parsed(text) or {}
    ids = [l.get("id") for l in d.get("layers", [])]
    ok(code == 200 and ids == ["regex", "presidio", "openai-privacy-filter", "ner"] and d.get("error") == "",
       "GET /api/privacylayers lists the four layers in run order, ner last at config.toml's priority 9", text)
    ok(by_id(d.get("layers")).get("ner", {}).get("priority") == 9 and by_id(d.get("layers")).get("regex", {}).get("regex_locked") is True,
       "and shows config.toml's ner priority, with the regex layer locked", text)

    code, text = call(base + "/api/privacylayers", {"layers": [
        layer("regex", priority=1), layer("presidio", priority=0, mode="veto", threshold=0.5, types=["PERSON"]),
        layer("ner", enabled=False, priority=2)]})
    ok(code == 200 and (parsed(text) or {}).get("ok") is True, "POST /api/privacylayers saves a valid set [%d]" % code, text)
    saved = open(conf).read()
    ok(saved.startswith('[privacy]\nconsensus_strategy = "most-restrictive"\n# the smoke keeps this line\n') and "priority = 9" not in saved
       and 'id = "presidio"' in saved, "config.toml keeps every other line and holds the new entries in place of the old", saved)
    d = parsed(call(base + "/api/privacylayers")[1]) or {}
    pr = by_id(d.get("layers")).get("presidio", {})
    ok(pr.get("priority") == 0 and pr.get("mode") == "veto" and pr.get("confidence_threshold") == 0.5 and pr.get("entity_filter") == ["PERSON"],
       "GET reads the saved presidio back: priority 0, veto, 0.5, PERSON", json.dumps(pr))
    h = (parsed(call(base + "/api/health")[1]) or {}).get("privacy_layers", {})
    hl = h.get("layers", [])
    ok([l.get("id") for l in hl][:2] == ["presidio", "regex"] and by_id(hl).get("ner", {}).get("state") == "disabled",
       "/api/health runs presidio first and reports ner disabled, as saved", json.dumps(h))

    before = open(conf).read()
    code, text = call(base + "/api/privacylayers", {"layers": [layer("regex", enabled=False)]})
    err = (parsed(text) or {}).get("error", "")
    ok(code == 400 and "enabled = false is not applied to the regex layer" in err and "open decision" in err,
       "switching the regex layer off is refused, naming the rule and the open decision [%d]" % code, text)
    ok(open(conf).read() == before, "and config.toml is unchanged")

    with open(policy, "w") as f:
        f.write('{"required_layers":["presidio"],"max_confidence_threshold":0.4}')
    code, text = call(base + "/api/privacylayers", {"layers": [layer("presidio", enabled=False, priority=3)]})
    ok(code == 409 and "requires the presidio privacy layer, so it cannot be switched off" in (parsed(text) or {}).get("error", ""),
       "under a policy requiring presidio, switching it off is refused [%d]" % code, text)
    code, text = call(base + "/api/privacylayers", {"layers": [layer("presidio", priority=0, threshold=0.5)]})
    ok(code == 409 and "max_confidence_threshold 0.4" in (parsed(text) or {}).get("error", ""),
       "and a threshold above its 0.4 ceiling is refused [%d]" % code, text)
    ok(open(conf).read() == before, "and neither changed config.toml")
    d = parsed(call(base + "/api/privacylayers")[1]) or {}
    ok(d.get("policy", {}).get("required_layers") == ["presidio"] and by_id(d.get("layers")).get("presidio", {}).get("policy_required") is True,
       "GET shows the policy's floor beside the layers", json.dumps(d.get("policy")))
    h = (parsed(call(base + "/api/health")[1]) or {}).get("privacy_layers", {})
    pr = by_id(h.get("layers")).get("presidio", {})
    ok(pr.get("confidence_threshold") == 0.4 and pr.get("policy_changed") == ["confidence_threshold"]
       and any("presidio layer's confidence_threshold is lowered to 0.4" in n for n in h.get("org_policy", {}).get("overrides", [])),
       "/api/health reports presidio's threshold as the policy applies it, 0.4, marked changed by the policy (F3b.8)", json.dumps(h))
    os.remove(policy)

    code, text = call(base + "/api/privacymodels")
    ok(code == 200 and (parsed(text) or {}).get("models") == [], "GET /api/privacymodels lists none", text)
    code, text = call(base + "/api/privacymodels", {"id": "smoke/ner", "url": "http://127.0.0.1:9", "labels": ["PER=PERSON"],
                                                     "confidence_threshold": 0.3, "priority": 6})
    ok(code == 200 and (parsed(text) or {}).get("layer") == "model:smoke/ner", "POST /api/privacymodels registers a model [%d]" % code, text)
    reg = parsed(open(models).read()) if os.path.exists(models) else None
    ok(reg == {"models": [{"id": "smoke/ner", "url": "http://127.0.0.1:9", "labels": ["PER=PERSON"], "confidence_threshold": 0.3,
                           "priority": 6, "enabled": True}]}, "privacy-models.json holds it as add-model writes it",
       json.dumps(reg))
    listed = by_id((parsed(call(base + "/api/privacymodels")[1]) or {}).get("models"))
    ok(listed.get("smoke/ner", {}).get("layer") == "model:smoke/ner", "GET lists it", json.dumps(listed))
    h = (parsed(call(base + "/api/health")[1]) or {}).get("privacy_layers", {})
    ok(by_id(h.get("layers")).get("model:smoke/ner", {}).get("state") == "unavailable",
       "/api/health reports it as a layer, unavailable (nothing serves it)", json.dumps(h))
    code, text = call(base + "/api/privacymodels", {"id": "smoke/bad", "url": "http://127.0.0.1:9", "labels": ["X=NOT_A_TYPE"]})
    ok(code == 400 and "not an entity type loke knows" in (parsed(text) or {}).get("error", ""),
       "a mapping to an unknown type is refused [%d]" % code, text)


if __name__ == "__main__":
    main()
    sys.exit(1 if fails else 0)
