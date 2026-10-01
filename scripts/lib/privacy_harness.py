#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""The privacy pipeline test harness, end to end over the real request path. (F3.9)

Driven by scripts/smoke_privacy_harness.sh, which starts the built loke binary and puts
scripts/lib/http_recorder.py (echo mode) where loke expects Ollama. This script sends one
POST /api/pipeline per (template, detector case) pair and judges each on what the recorder
LOGGED (`<log>.bodies`, one json.dumps([method, path, body]) per request, written before the
recorder answers), never on what loke reports about itself.

Templates are read from core.privacy.template's own source, so a template added there is
covered here without editing this file. They are rendered here, by the same rule the
module's render applies (every `{{name}}` replaced by its value, optional parameters by their
default): no route on loke's request path renders a template, so a client does, and the
rendered text is what /api/pipeline receives. The renderer itself is tested by
tests/unit/privacy/test_template.tk and test_template_render.tk.

The detector cases name every type core.privacy.regex.getpatterns emits, each with a value
tests/unit/privacy/test_regex.tk shows that layer detecting, plus a PERSON for the NER layer
(the recorder's /api/chat always reports "Jane Citizen") and a control with no identifier.
CASE_TYPES below must equal the regex layer's list; the harness reads that list from
regex.tk and fails if they differ, so a new detector cannot go unexercised silently.

Then, outside the matrix, one system-prompt cell per detector case (F3.9b): the identifier is
put in the caller's `system_prompt` and the text carries none. Each is judged as a matrix cell
is, on what the stand-in received: the value in no request but the NER layer's, a placeholder
of its type in the `system` the model was sent, after the guardian.

Exit status 0 only when every assertion passes. The guardian check was an expected failure
(XFAIL, F3.9a) until /api/pipeline sent it; it is a required pass now.
"""
import argparse, json, re, sys, time, urllib.error, urllib.request

# (detector type, raw value, placeholder type prefix). Values from test_regex.tk.
CASES = [
    ("email", "harness.probe@example.com", "EMAIL"),
    # Second, as in getpatterns: an NHS number printed 3-3-4 is also a phone_us match, and
    # the pipeline keeps the first of two equal values. The label is part of the value.
    ("uk_nhs_number", "NHS number 943 476 5919", "UK_NHS_NUMBER"),
    ("phone_au", "0412 345 678", "PHONE_AU"),
    ("phone_us", "(555) 234-5678", "PHONE_US"),
    ("credit_card", "4111 1111 1111 1111", "CREDIT_CARD"),
    ("ip_v4", "192.168.1.1", "IP_V4"),
    ("au_tfn", "123 456 782", "AU_TFN"),
    ("au_abn", "51 824 753 556", "AU_ABN"),
    ("ssn_us", "219-09-9999", "SSN_US"),
    ("url", "https://intranet.example.com/payroll/q3", "URL"),
    ("api_key", "sk-ant-abcdefghijklmnopqrst", "API_KEY"),
    # RG1.7: BSB and account match only after their label, so the label is part of the
    # value; the leak check also looks for the bare digits, which is the identifier itself.
    ("au_medicare", "2123 45670 1", "AU_MEDICARE"),
    ("au_bsb", "BSB 062-000", "AU_BSB"),
    ("bank_account", "account 12345678", "BANK_ACCOUNT"),
    # RG1.7a: the same for CRN, passport, licence and super member number.
    ("au_crn", "CRN 123 456 789A", "AU_CRN"),
    ("passport", "passport number PA1234567", "PASSPORT"),
    ("driver_licence", "driver's licence 12345678", "DRIVER_LICENCE"),
    ("au_super_member", "super member number 987654321", "AU_SUPER_MEMBER"),
    # The UK and Singapore identifiers: values tests/unit/privacy/test_uk_sg_identifiers.tk
    # shows detected. Sort code and NRIC carry their label for the same reason.
    ("uk_nino", "AB123456C", "UK_NINO"),
    ("uk_sort_code", "sort code 12-34-56", "UK_SORT_CODE"),
    ("uk_driving_licence", "MORGA657054SM9IJ", "UK_DRIVING_LICENCE"),
    ("sg_nric", "NRIC S1234567D", "SG_NRIC"),
    ("PERSON (NER layer)", "Jane Citizen", "PERSON"),
    ("none (control)", "", ""),
]
REGEX_TYPES = [c[0] for c in CASES[:22]]
GUARDIAN = "LOKE_GUARDIAN_v"
PLACEHOLDER = re.compile(r"\[[A-Z][A-Z0-9_]*_[0-9]+\]|\[[A-Z][A-Z0-9_]*_[0-9a-f]{4,}_[0-9]+\]")


def field(block, name):
    m = re.search(name + r':"((?:[^"\\]|\\.)*)"', block, re.S)
    return m.group(1).replace('\\"', '"').replace("\\\\", "\\") if m else None


def builtin_block(src):
    """builtintemplates' body: from its `<@(` to the next function."""
    return src.split("f=builtintemplates()", 1)[1].split("<@(", 1)[1].split("\nf=", 1)[0]


def read_templates(path):
    body = builtin_block(open(path, encoding="utf-8").read())
    blocks = body.split("$prompttemplate{")[1:]
    templates = []
    for b in blocks:
        params = []
        for pm in re.finditer(r"\$templateparam\{(.*?)\}", b, re.S):
            p = pm.group(1)
            params.append({"name": field(p, "name"), "required": "required:true" in p,
                           "default": field(p, "defaultval") or ""})
        templates.append({"id": field(b, "id"), "system": field(b, "systemprompt"),
                          "user": field(b, "usertemplate"), "params": params})
    return templates


def read_regex_types(path):
    src = open(path, encoding="utf-8").read()
    body = src.split("f=getpatterns()", 1)[1].split("\nf=", 1)[0]
    return re.findall(r'\$patterndef\{name:"([^"]+)"', body)


def render(tmpl, values):
    sysp, user = tmpl["system"], tmpl["user"]
    for p in tmpl["params"]:
        v = values.get(p["name"], p["default"])
        sysp = sysp.replace("{{%s}}" % p["name"], v)
        user = user.replace("{{%s}}" % p["name"], v)
    return sysp, user


def raw_data(tmpl, value):
    """Parameter values: the identifier goes into the first required parameter, as raw data a
    user pastes; every other required parameter gets plain prose; optional ones their default."""
    vals, placed = {}, False
    for p in tmpl["params"]:
        if not p["required"]:
            continue
        if p["name"] == "categories":
            vals[p["name"]] = "billing, support, other"
        elif not placed:
            vals[p["name"]] = ("Customer record, keep it confidential: %s. Status open." % value) if value \
                else "Customer record with nothing personal in it. Status open."
            placed = True
        else:
            vals[p["name"]] = "What should happen next with this record?"
    return vals


def post(url, obj):
    req = urllib.request.Request(url, data=json.dumps(obj).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")


def recorded(path):
    try:
        with open(path, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except FileNotFoundError:
        return []


def leaks(body, value):
    """The forms of value that would count as it leaving: as typed, inside the JSON-decoded
    body, and (for a value with separators) as its bare digits."""
    if not value:
        return False
    forms = {value}
    digits = re.sub(r"\D", "", value)
    if len(digits) >= 8 and digits != value:
        forms.add(digits)
    texts = [body]
    try:
        texts.append(json.dumps(json.loads(body), ensure_ascii=False))
    except ValueError:
        pass
    return any(f in t for f in forms for t in texts)


def system_of(body):
    """The `system` field of an Ollama /api/generate body, or ""."""
    try:
        return json.loads(body).get("system", "") or ""
    except ValueError:
        return ""


def send_held(T, pipeline, approve, bodies, req, value, name, cell):
    """POST req; if it is held for approval (GA5.26), check nothing was sent while held, approve
    it and send it again. Returns (status, reply, the requests the stand-in received)."""
    before = len(recorded(bodies))
    status, out = post(pipeline, req)
    got = recorded(bodies)[before:]
    try:
        reply = json.loads(out)
    except ValueError:
        reply = {}
    if status == 409 and reply.get("approval_required"):
        cell["held"] = True
        T.check(not any(r[1] == "/api/generate" for r in got),
                "%s: held for approval, and the model received nothing" % name)
        T.check(not any(leaks(r[2], value) for r in got if r[1] != "/api/chat"),
                "%s: held, and no request but the local NER layer's carried the value" % name)
        ast, aout = post(approve, {"approval_id": reply.get("approval_id", ""), "decision": "approve"})
        T.check(ast == 200 and '"approved"' in aout, "%s: the approval was recorded" % name)
        req = dict(req, approval_id=reply.get("approval_id", ""))
        before = len(recorded(bodies))
        status, out = post(pipeline, req)
        got = recorded(bodies)[before:]
        try:
            reply = json.loads(out)
        except ValueError:
            reply = {}
    return status, reply, got


class Tally:
    def __init__(self):
        self.ok = self.fail = 0
        self.rows = []

    def check(self, cond, label):
        if cond:
            self.ok += 1
        else:
            self.fail += 1
            print("  FAIL " + label, file=sys.stderr)
        return cond



def record(path, templates, cells, syscells):
    """The run's counts as result rows, for docs/metrics-baseline.md (through the evidence
    ledger). Counts over fixed inputs, with a recording stand-in and no model: deterministic,
    so one observation each, and stated as counts, never as rates."""
    import pathlib
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
    from benchmarks.lib import result
    workload = "f3.9-privacy-harness: %d built-in templates (%s) x %d cases (%s), POST /api/pipeline -> Ollama stand-in" % (
        len(templates), ",".join(t["id"] for t in templates), len(CASES), ",".join(c[0] for c in CASES))
    dispatched = [c for c in cells if c.get("dispatched")]
    common = dict(units="cells", workload=workload, arm="loke-binary-api-pipeline",
                  notes="scripts/smoke_privacy_harness.sh; judged on what scripts/lib/http_recorder.py logged")
    result.write(result.Measurement(metric="privacy_harness_cells_passing", value=float(sum(1 for c in cells if c["passed"])),
                                    n=len(cells), caveat="One request path (browser /api/pipeline to a local model) and the "
                                    "regex layer's own fixture values; not a recall figure, and the Anthropic route is not driven.",
                                    **common), path=pathlib.Path(path))
    result.write(result.Measurement(metric="privacy_harness_guardian_reached_model", value=float(sum(1 for c in dispatched if c.get("guardian"))),
                                    n=len(dispatched), caveat="Ollama route only; the guardian is judged present by its version "
                                    "marker at the start of the request's system prompt, not by what a model does with it.",
                                    **common), path=pathlib.Path(path))
    sysworkload = "f3.9b-privacy-harness-system-prompt: %d cases (%s) with the identifier in system_prompt, POST /api/pipeline -> Ollama stand-in" % (
        len(syscells), ",".join(c["detector"] for c in syscells))
    result.write(result.Measurement(metric="privacy_harness_sysprompt_cells_passing", value=float(sum(1 for c in syscells if c["passed"])),
                                    n=len(syscells), units="cells", workload=sysworkload, arm="loke-binary-api-pipeline",
                                    notes="scripts/smoke_privacy_harness.sh; judged on what scripts/lib/http_recorder.py logged",
                                    caveat="One request path (browser /api/pipeline to a local model); the Anthropic route is "
                                    "driven by tests/integration/test_system_prompt_disclosure.tk, not here."), path=pathlib.Path(path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loke", required=True)
    ap.add_argument("--bodies", required=True)
    ap.add_argument("--templates", required=True)
    ap.add_argument("--report")
    ap.add_argument("--record", help="append the counts to this result file (benchmarks.lib.result)")
    a = ap.parse_args()

    T = Tally()
    templates = read_templates(a.templates)
    declared = builtin_block(open(a.templates, encoding="utf-8").read()).count("$prompttemplate{")
    T.check(len(templates) == declared and declared > 0 and all(t["id"] and t["user"] for t in templates),
            "every built-in template was read from template.tk (%d of %d)" % (len(templates), declared))
    regex_types = read_regex_types(a.templates.replace("template.tk", "regex.tk"))
    T.check(regex_types == REGEX_TYPES,
            "the cases cover exactly the regex layer's detector types: layer has %s" % regex_types)

    pipeline = a.loke + "/api/pipeline"
    approve = a.loke + "/api/approve"
    every_value = [c[1] for c in CASES if c[1]]
    cells = []

    for tmpl in templates:
        for (dtype, value, ptype) in CASES:
            name = "%s x %s" % (tmpl["id"], dtype)
            sysp, user = render(tmpl, raw_data(tmpl, value))
            req = {"text": user, "system_prompt": sysp,
                   "fallback_reason": "user_choice", "fallback_selected_by": "user"}
            cell = {"template": tmpl["id"], "detector": dtype, "held": False, "passed": False}

            before = len(recorded(a.bodies))
            status, out = post(pipeline, req)
            got = recorded(a.bodies)[before:]
            try:
                reply = json.loads(out)
            except ValueError:
                reply = {}

            if status == 409 and reply.get("approval_required"):
                # GA5.26: held. Nothing may have reached the model while it was held.
                cell["held"] = True
                T.check(not any(r[1] == "/api/generate" for r in got),
                        "%s: held for approval, and the model received nothing" % name)
                T.check(not any(leaks(r[2], value) for r in got if r[1] != "/api/chat"),
                        "%s: held, and no request but the local NER layer's carried the value" % name)
                ast, aout = post(approve, {"approval_id": reply.get("approval_id", ""), "decision": "approve"})
                T.check(ast == 200 and '"approved"' in aout, "%s: the approval was recorded" % name)
                req["approval_id"] = reply.get("approval_id", "")
                before = len(recorded(a.bodies))
                status, out = post(pipeline, req)
                got = recorded(a.bodies)[before:]
                try:
                    reply = json.loads(out)
                except ValueError:
                    reply = {}

            if not T.check(status == 200 and reply.get("ok") is True,
                           "%s: answered 200 ok (got %s %s)" % (name, status, out[:160])):
                cells.append(cell)
                continue
            gens = [r for r in got if r[0] == "POST" and r[1] == "/api/generate"]
            if not T.check(len(gens) == 1, "%s: exactly one dispatch reached the model (got %d)" % (name, len(gens))):
                cells.append(cell)
                continue
            body = gens[0][2]
            try:
                sent = json.loads(body).get("prompt", "")
            except ValueError:
                sent = ""
            before_fail = T.fail

            # 1. No raw identifier left, in any request but the local NER layer's.
            for r in got:
                if r[1] == "/api/chat":
                    continue
                T.check(not any(leaks(r[2], v) for v in every_value),
                        "%s: %s %s carries no raw identifier" % (name, r[0], r[1]))
            # 2. The value was replaced by a placeholder of its type, and nothing else was lost.
            if value:
                T.check(re.search(r"\[%s_[0-9a-f]+_[0-9]+\]|\[%s_[0-9]+\]" % (ptype, ptype), sent) is not None,
                        "%s: the model's prompt carries a %s placeholder" % (name, ptype))
                T.check("Status open." in sent and "Customer record" in sent,
                        "%s: the rest of the text reached the model" % name)
            else:
                T.check(sent == user, "%s: text with no identifier reached the model unchanged" % name)
            # 3. Restoration: the echo answers "echo: " + prompt, so the user must read exactly
            #    "echo: " + the text they sent.
            T.check(reply.get("response") == "echo: " + user,
                    "%s: the reply is restored byte for byte" % name)
            T.check(PLACEHOLDER.search(reply.get("response", "")) is None,
                    "%s: no placeholder survives into what the user reads" % name)
            # 5. The guardian reached the model, as /api/generate's `system` (F3.9a).
            cell["dispatched"] = True
            cell["guardian"] = system_of(body).startswith(GUARDIAN)
            T.check(cell["guardian"], "%s: the guardian system prompt reached the model" % name)

            cell["passed"] = T.fail == before_fail
            cells.append(cell)

    # F3.9b: an identifier in the caller's system_prompt, none in the text. One cell per case.
    syscells = []
    clean = "Summarise the weather report for today."
    for (dtype, value, ptype) in CASES:
        if not value:
            continue
        name = "system_prompt x %s" % dtype
        cell = {"detector": dtype, "held": False, "passed": False}
        req = {"text": clean, "system_prompt": "You are assisting a customer. Their record: %s. Be brief." % value,
               "fallback_reason": "user_choice", "fallback_selected_by": "user"}
        before_fail = T.fail
        status, reply, got = send_held(T, pipeline, approve, a.bodies, req, value, name, cell)
        if T.check(status == 200 and reply.get("ok") is True, "%s: answered 200 ok (got %s %s)" % (name, status, str(reply)[:160])):
            gens = [r for r in got if r[0] == "POST" and r[1] == "/api/generate"]
            if T.check(len(gens) == 1, "%s: exactly one dispatch reached the model (got %d)" % (name, len(gens))):
                sysfield = system_of(gens[0][2])
                for r in got:
                    if r[1] == "/api/chat":
                        continue
                    T.check(not leaks(r[2], value), "%s: %s %s does not carry the value" % (name, r[0], r[1]))
                T.check(sysfield.startswith(GUARDIAN), "%s: the model's system prompt starts with the guardian" % name)
                T.check(re.search(r"\[%s_[0-9a-f]+_[0-9]+\]|\[%s_[0-9]+\]" % (ptype, ptype), sysfield) is not None,
                        "%s: the model's system prompt carries a %s placeholder where the value was" % (name, ptype))
                T.check("You are assisting a customer." in sysfield and "Be brief." in sysfield,
                        "%s: the rest of the caller's system prompt reached the model" % name)
                T.check(reply.get("response") == "echo: " + clean, "%s: the reply is the text's echo, unchanged" % name)
        cell["passed"] = T.fail == before_fail
        syscells.append(cell)

    # A last sweep over everything the stand-in ever received.
    allrec = recorded(a.bodies)
    T.check(len(allrec) > 0, "the stand-in recorded requests")
    T.check(not any(leaks(r[2], v) for r in allrec if r[1] != "/api/chat" for v in every_value),
            "across all %d recorded requests, none but the NER layer's carried a raw identifier" % len(allrec))

    npass = sum(1 for c in cells if c["passed"])
    nheld = sum(1 for c in cells if c["held"])
    nguard = sum(1 for c in cells if c.get("guardian"))
    spass = sum(1 for c in syscells if c["passed"])
    sheld = sum(1 for c in syscells if c["held"])
    print("  privacy harness: %d templates x %d detector cases = %d cells, %d passed every assertion, "
          "%d held for approval first, guardian reached the model in %d; %d system-prompt cells, %d passed, "
          "%d held first; %d assertions ok, %d failed"
          % (len(templates), len(CASES), len(cells), npass, nheld, nguard, len(syscells), spass, sheld, T.ok, T.fail))
    if a.report:
        with open(a.report, "w") as f:
            json.dump({"templates": [t["id"] for t in templates], "cases": [c[0] for c in CASES],
                       "cells": cells, "syscells": syscells, "ok": T.ok, "fail": T.fail,
                       "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f, indent=1)
    if a.record:
        record(a.record, templates, cells, syscells)
    return 0 if T.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
