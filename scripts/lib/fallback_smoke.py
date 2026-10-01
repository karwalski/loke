#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""F5.3a: POST /api/pipeline falls back when its first local model fails, over the real binary.

Run by scripts/smoke_privacy_harness.sh after the harness, with the stand-in restarted so that
the router's first local choice (qwen2.5:7b) answers /api/generate with an empty body
(http_recorder.py's RECORDER_FAIL_MODELS). One request carrying an email is sent. It is judged
on the reply's BODY and on what the stand-in RECEIVED:

  - the reply is 200 ok, names the hop that answered (`answered_by`) and the one that failed
    (`hops_failed`), and claims no answer from the failed one;
  - two /api/generate requests arrived, the failed model's first, and neither carried the raw
    email: each hop sent the anonymised text and the guardian system prompt;
  - the two hops sent the same prompt and the same system prompt (one privacy run);
  - the answer is restored byte for byte with that run's placeholder map.

Usage: fallback_smoke.py --loke URL --bodies FILE
"""
import argparse, json, sys, urllib.request

GUARDIAN = "LOKE_GUARDIAN_v"
FAILING = "qwen2.5:7b"
TEXT = "Please write to user.probe@example.com about the invoice."
VALUE = "user.probe@example.com"


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def recorded(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except OSError:
        return []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loke", required=True)
    ap.add_argument("--bodies", required=True)
    a = ap.parse_args()
    ok = fail = 0

    def check(cond, label):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print("  FAIL fallback: " + label)
        return cond

    before = len(recorded(a.bodies))
    status, out = post(a.loke + "/api/pipeline", {"text": TEXT, "fallback_reason": "user_choice", "fallback_selected_by": "user"})
    got = recorded(a.bodies)[before:]
    try:
        reply = json.loads(out)
    except ValueError:
        reply = {}
    check(status == 200 and reply.get("ok") is True, "answered 200 ok (got %s %s)" % (status, out[:200]))
    check(reply.get("hops_failed") == ["ollama:" + FAILING], "hops_failed names the failed first hop (got %s)" % reply.get("hops_failed"))
    answered = reply.get("answered_by", "")
    check(answered.startswith("ollama:") and answered != "ollama:" + FAILING,
          "answered_by names a different local hop (got %r)" % answered)
    check(reply.get("hops_attempted", [None])[0] == "ollama:" + FAILING and reply.get("hops_attempted", [])[-1] == answered,
          "hops_attempted lists the failed hop, then the one that answered (got %s)" % reply.get("hops_attempted"))
    gens = [r for r in got if r[0] == "POST" and r[1] == "/api/generate"]
    if check(len(gens) == 2, "two dispatches reached the model (got %d)" % len(gens)):
        b = [json.loads(g[2]) for g in gens]
        check(b[0].get("model") == FAILING and "ollama:" + b[1].get("model", "") == answered,
              "the failing model was sent first and the answering one second (%s, %s)" % (b[0].get("model"), b[1].get("model")))
        check(all(VALUE not in g[2] for g in gens), "neither hop received the raw email")
        check(all("[EMAIL_" in x.get("prompt", "") for x in b), "each hop received the anonymised text")
        check(all(x.get("system", "").startswith(GUARDIAN) for x in b), "each hop received the guardian system prompt")
        check(b[0].get("prompt") == b[1].get("prompt") and b[0].get("system") == b[1].get("system"),
              "both hops received the same prompt and system prompt: one privacy run")
    check(not any(VALUE in r[2] for r in got if r[1] != "/api/chat"), "no request but the NER layer's carried the email")
    check(reply.get("response") == "echo: " + TEXT, "the answer is restored byte for byte (got %r)" % reply.get("response"))
    print("  fallback smoke: %d assertions ok, %d failed" % (ok, fail))
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
