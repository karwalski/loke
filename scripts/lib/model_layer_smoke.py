#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""A registered privacy model on the BUILT loke's /api/pipeline. (F3b.7 (8), (6))

Driven by scripts/smoke_privacy_harness.sh after the matrix, against the loke it started, with
its Ollama stand-in (scripts/lib/http_recorder.py, harness mode: /api/generate echoes the
prompt) and a second recorder in `tokenmodel` mode standing in for
packages/privacy-filter/server.py serving the model recorder/token-model: its /health names
that model and the task token-classification, and its /detect reports "Brisbane" (label LOC)
and "Zorblax" (label WIDGET) wherever the text holds them. No model is downloaded, and nothing
leaves the machine.

Usage:
  model_layer_smoke.py --loke <url> --bodies <ollama stand-in .bodies> \
                       --model-url <tokenmodel url> --model-bodies <its .bodies> --home <loke HOME>

The text holds no identifier the regex or NER layer reports, so whatever masks Brisbane and
Zorblax is the registered model. Judged on what the recorders received and on loke.db, not on
what loke says it sent:

  1. the model is registered through POST /api/privacymodels (the settings UI's path, and
     `loke privacy add-model`'s call) and written to <home>/.loke/privacy-models.json;
  2. POST /api/pipeline answers 200, and the one /api/generate the stand-in received carries
     neither value but a LOCATION placeholder and a WIDGET placeholder (the unmapped label,
     masked all the same), while the user reads the echo with both values restored;
  3. the model's sidecar was asked /health before it was sent the text on /detect;
  4. the reply's privacy_layers reports the layer model:recorder/token-model completed with 2
     detections;
  5. the request's decision_trace row and disclosure_log row in loke.db name the model among
     the layers that scanned, in detection_layers (the pipeline-trace stage, F3b.7 (6));
  6. the control: with the registration removed (POST {"remove":...}), the same request reaches
     the stand-in with Brisbane in it, and detection_layers no longer names the model. So 2 is
     the model's doing.

Prints `  ok   ...` per check and `  FAIL ...` to stderr; exits 1 on any failure. Leaves
privacy-models.json removed.
"""
import argparse
import json
import os
import re
import sqlite3
import sys
import urllib.request

LAYER = "model:recorder/token-model"
TEXT = "Summarise the plan for the Brisbane office and the Zorblax rollout."
VALUES = ("Brisbane", "Zorblax")
fails = 0


def ok(cond, label, detail=""):
    global fails
    if cond:
        print("  ok   " + label)
    else:
        fails += 1
        print("  FAIL " + label + (": " + detail[:300] if detail else ""), file=sys.stderr)
    return cond


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def parsed(text):
    try:
        return json.loads(text)
    except ValueError:
        return {}


def recorded(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []


def dispatch(a):
    """POST the text (approving it once if it is held, GA5.26). Returns (status, reply, the
    stand-in's new requests, the model sidecar's new requests)."""
    req = {"text": TEXT, "fallback_reason": "user_choice", "fallback_selected_by": "user"}
    before, mbefore = len(recorded(a.bodies)), len(recorded(a.model_bodies))
    status, out = post(a.loke + "/api/pipeline", req)
    reply = parsed(out)
    if status == 409 and reply.get("approval_required"):
        post(a.loke + "/api/approve", {"approval_id": reply.get("approval_id", ""), "decision": "approve"})
        req["approval_id"] = reply.get("approval_id", "")
        status, out = post(a.loke + "/api/pipeline", req)
        reply = parsed(out)
    return status, reply, recorded(a.bodies)[before:], recorded(a.model_bodies)[mbefore:]


def prompt_of(got):
    gens = [r for r in got if r[0] == "POST" and r[1] == "/api/generate"]
    if len(gens) != 1:
        return None
    return parsed(gens[0][2]).get("prompt", "")


def layers_column(dbpath, table, requestid):
    try:
        con = sqlite3.connect(dbpath)
        try:
            row = con.execute("SELECT detection_layers FROM %s WHERE request_id=? ORDER BY rowid DESC LIMIT 1" % table,
                              (requestid,)).fetchone()
        finally:
            con.close()
    except sqlite3.Error as e:
        return "error: %s" % e
    return row[0] if row else ""


def scanned(column):
    return column.split(";")[0][len("scanned="):].split(",") if column.startswith("scanned=") else []


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--loke", required=True)
    p.add_argument("--bodies", required=True)
    p.add_argument("--model-url", required=True)
    p.add_argument("--model-bodies", required=True)
    p.add_argument("--home", required=True)
    a = p.parse_args()
    models = os.path.join(a.home, ".loke", "privacy-models.json")
    dbpath = os.path.join(a.home, ".loke", "loke.db")
    try:
        run(a, models, dbpath)
    finally:
        if os.path.exists(models):
            os.remove(models)


def run(a, models, dbpath):
    code, text = post(a.loke + "/api/privacymodels", {"id": "recorder/token-model", "url": a.model_url,
                                                       "labels": ["PER=PERSON", "LOC=LOCATION"], "confidence_threshold": 0.5})
    ok(code == 200 and parsed(text).get("layer") == LAYER, "F3b.7: the model is registered through POST /api/privacymodels [%d]" % code, text)
    ok(os.path.exists(models) and parsed(open(models).read()).get("models", [{}])[0].get("url") == a.model_url,
       "and written to the HOME's privacy-models.json")

    status, reply, got, mgot = dispatch(a)
    if not ok(status == 200 and reply.get("ok") is True, "F3b.7: POST /api/pipeline answers 200 with the model registered [%d]" % status,
              json.dumps(reply)):
        return
    sent = prompt_of(got)
    if not ok(sent is not None, "exactly one dispatch reached the model stand-in"):
        return
    ok(not any(v in sent for v in VALUES), "neither value the registered model found reached the model stand-in", sent)
    ok(re.search(r"\[LOCATION_[0-9a-f]+_[0-9]+\]|\[LOCATION_[0-9]+\]", sent) is not None,
       "its prompt carries a LOCATION placeholder, the label mapping's type for LOC", sent)
    ok(re.search(r"\[WIDGET_[0-9a-f]+_[0-9]+\]|\[WIDGET_[0-9]+\]", sent) is not None,
       "and a WIDGET placeholder: the label the mapping does not name is masked all the same", sent)
    ok(reply.get("response") == "echo: " + TEXT, "the user reads the echo with both values restored", reply.get("response", ""))
    health = next((i for i, r in enumerate(mgot) if r[1] == "/health"), None)
    detect = next((i for i, r in enumerate(mgot) if r[0] == "POST" and r[1] == "/detect"), None)
    ok(health is not None and detect is not None and health < detect and TEXT in mgot[detect][2],
       "the model's sidecar was asked /health before it was sent the text on /detect", json.dumps(mgot)[:300])
    layer = next((l for l in reply.get("privacy_layers", []) or [] if isinstance(l, dict) and l.get("layer") == LAYER), {})
    ok(layer.get("state") == "completed" and layer.get("detections") == 2,
       "the reply's privacy_layers reports %s completed with 2 detections" % LAYER, json.dumps(layer))
    rid = reply.get("request_id", "")
    trace = layers_column(dbpath, "decision_trace", rid)
    ok(LAYER in scanned(trace), "F3b.7 (6): the request's decision_trace names the model among the layers that scanned", trace)
    disc = layers_column(dbpath, "disclosure_log", rid)
    ok(LAYER in scanned(disc), "and so does its disclosure_log row", disc)

    code, text = post(a.loke + "/api/privacymodels", {"remove": "recorder/token-model"})
    ok(code == 200 and parsed(text).get("removed") == LAYER, "the registration is removed through POST /api/privacymodels [%d]" % code, text)
    status, reply, got, mgot = dispatch(a)
    sent = prompt_of(got)
    ok(status == 200 and sent is not None and "Brisbane" in sent and not mgot,
       "control: without it, the same request reaches the stand-in with Brisbane in it, and the sidecar is sent nothing", sent or json.dumps(reply))
    trace = layers_column(dbpath, "decision_trace", reply.get("request_id", ""))
    ok(trace.startswith("scanned=") and LAYER not in trace, "and detection_layers no longer names the model", trace)


if __name__ == "__main__":
    main()
    sys.exit(1 if fails else 0)
