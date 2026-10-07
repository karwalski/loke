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
(the recorder's /api/chat reports "Jane Citizen" when the user message it is sent holds that
name, F3.9d) and a control with no identifier. Every dispatched cell also checks, in the
reply's privacy_layers, that the NER layer completed and found one entity exactly when the
scanned text holds the name and none otherwise.
CASE_TYPES below must equal the regex layer's list; the harness reads that list from
regex.tk and fails if they differ, so a new detector cannot go unexercised silently.

Then, outside the matrix, one system-prompt cell per detector case (F3.9b): the identifier is
put in the caller's `system_prompt` and the text carries none. Each is judged as a matrix cell
is, on what the stand-in received: the value in no request but the NER layer's, a placeholder
of its type in the `system` the model was sent, after the guardian.

Then the no-custody dispatch (F3.9c): requests carrying their dataset (`headers`, `rows`), whose
cells include words of the guardian (`never`, `data`, `audit`) and values that are not. A clean
question is dispatched no-custody, and the `system` the stand-in received is the guardian, byte
for byte as core.privacy.guardian.guardianprompt holds it (read from its source), then the
caller's system prompt. A guardian word, or another cell, in the question or the caller's system
prompt is refused (422 sentinel_fail) and nothing reaches the model.

Then the CLI path (F3.9, F5.3), with --cli-bin and no --loke: the same template x case matrix
and system-prompt cells through `loke ask` over the built loke-cli binary, each a process with
a throwaway HOME, judged on what its own stand-in received and on the disclosure and audit rows
it wrote; a refused hop (the kill switch) that writes no disclosure row; `loke audit verify`;
and no raw identifier anywhere in loke.db. With --cli-fallback-bodies, one request whose first
hop fails: two disclosure rows, failed and completed. See cli_phase. cli.proxy is not driven:
`loke proxy` is not a command of the binary (cli.commands has no `proxy`), so it cannot be.

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


def read_guardian(path):
    """core.privacy.guardian.guardianprompt's literal, as compiled into loke."""
    src = open(path, encoding="utf-8").read()
    m = re.search(r'f=guardianprompt\(\):str\{\s*<"(.*?)"\s*\};', src, re.S)
    return m.group(1) if m else ""


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


def ner_layer(reply):
    """The NER layer's entry in a reply's privacy_layers (F3b.10), or {}."""
    for l in reply.get("privacy_layers", []) or []:
        if isinstance(l, dict) and l.get("layer") == "ner":
            return l
    return {}


def check_ner(T, reply, scanned, name):
    """F3.9d: the stand-in's NER answer is judged by what loke reports the layer found. It must
    have scanned, and found the one PERSON exactly when the text loke scanned (system prompt
    and text) holds "Jane Citizen", and nothing otherwise. With the stand-in matching the
    whole request body, NER's own system message made every cell report one."""
    ner = ner_layer(reply)
    want = 1 if "Jane Citizen" in scanned else 0
    T.check(ner.get("state") == "completed" and ner.get("detections") == want,
            "%s: the NER layer completed and reported %d detection(s) (got %s %s)"
            % (name, want, ner.get("state"), ner.get("detections")))


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



# ── F3.9 / F5.3: the CLI path, `loke ask`, over the BUILT loke-cli binary ─────────────────
#
# Each cell runs `loke ask <text> --system <system>` as a separate process with a throwaway
# HOME whose config.toml points providers.ollama_url at a recorder in `harness` mode on a port
# the OS handed out. `loke ask` sends the model its request on Ollama's /api/chat, with the
# guardian as the system message (the recorder echoes the user messages back for such a
# request); the NER layer's own /api/chat holds no guardian. Judged, as the browser cells are,
# on what the stand-in received: no raw identifier in any request but the NER layer's, a
# placeholder of the detector's type in the user message, the guardian at the start of the
# system message, and the answer printed restored byte for byte with no placeholder left.
#
# And, per cell, on what `loke ask` wrote to loke.db (F5.3): exactly one new disclosure_log row
# for the one hop that sent, completed, whose bytes_body is the octet count of the body the
# stand-in received; its llm_dispatch and llm_request audit rows on the same correlation id,
# each bound to the disclosure row's digest. After the matrix: `loke audit verify` exits 0 (the
# hash chain and the reconciliation), and no raw identifier, as typed, is anywhere in the
# database file.
#
# RESTRICTED cells are not held on this path: `loke ask` evaluates no organisation policy and has
# no approval gate (filed as F5.3c). They are routed to a local model and judged as any cell is.

def model_requests(got):
    return [r for r in got if r[0] == "POST" and r[1] == "/api/chat" and GUARDIAN in r[2]]


def ner_or_intent(r):
    return r[1] == "/api/chat" and GUARDIAN not in r[2]


def chat_parts(body):
    """(system, user) of an Ollama /api/chat body."""
    try:
        msgs = json.loads(body).get("messages", [])
    except ValueError:
        return "", ""
    sysm = "\n".join(m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("role") == "system")
    user = "\n".join(m.get("content", "") for m in msgs if isinstance(m, dict) and m.get("role") == "user")
    return sysm, user


class CliRun:
    def __init__(self, binary, home):
        import sqlite3
        self.binary, self.home = binary, home
        self.db = home + "/.loke/loke.db"
        self.sqlite3 = sqlite3

    def run(self, args, timeout=120):
        import os, subprocess
        env = dict(os.environ, HOME=self.home)
        p = subprocess.run([self.binary] + args, env=env, capture_output=True, timeout=timeout)
        return p.returncode, p.stdout.decode("utf-8", "replace"), p.stderr.decode("utf-8", "replace")

    def rows(self, sql, params=()):
        try:
            con = self.sqlite3.connect(self.db)
            try:
                return con.execute(sql, params).fetchall()
            finally:
                con.close()
        except self.sqlite3.Error:
            return []

    def count(self, table):
        r = self.rows("SELECT COUNT(*) FROM %s" % table)
        return r[0][0] if r else -1


def disclosure_checks(T, C, name, before_rowid, sent_bodies, want_states):
    """The disclosure rows written since before_rowid: one per sent body, in order, each with
    the state wanted, bytes_body equal to the octets received, and its two audit rows bound."""
    rows = C.rows("SELECT rowid, correlation_id, state, bytes_body, provider, custody, fallback_reason, fallback_selected_by "
                  "FROM disclosure_log WHERE rowid>? ORDER BY rowid", (before_rowid,))
    T.check(len(rows) == len(sent_bodies),
            "%s: one disclosure row per hop that sent (rows %d, hops sent %d)" % (name, len(rows), len(sent_bodies)))
    for k, (row, body) in enumerate(zip(rows, sent_bodies)):
        _, cid, state, nbody, provider, custody, fbr, fbby = row
        T.check(state == want_states[k], "%s: hop %d's disclosure row is %s (got %s)" % (name, k, want_states[k], state))
        T.check(nbody == len(body.encode("utf-8")),
                "%s: hop %d's bytes_body is the octets the stand-in received (%s vs %d)" % (name, k, nbody, len(body.encode("utf-8"))))
        T.check(provider == "ollama" and custody == "redacted-data" and fbr == "user_choice" and fbby == "user",
                "%s: hop %d's row names ollama, redacted-data, user_choice by user (got %s %s %s %s)" % (name, k, provider, custody, fbr, fbby))
        outcome = "llm_request" if want_states[k] == "completed" else "llm_request_failed"
        aud = C.rows("SELECT event_type, COALESCE(disclosure_digest,''), use_case FROM audit_log WHERE correlation_id=? ORDER BY created_at, rowid", (cid,))
        kinds = [a[0] for a in aud]
        T.check(kinds.count("llm_dispatch") == 1 and kinds.count(outcome) == 1,
                "%s: hop %d has its llm_dispatch and %s audit rows (got %s)" % (name, k, outcome, kinds))
        T.check(all(a[1] for a in aud if a[0] in ("llm_dispatch", outcome)) and all(a[2] == "cli-ask" for a in aud),
                "%s: hop %d's audit rows bind the disclosure digest, use case cli-ask" % (name, k))
    return rows


def cli_phase(T, a, templates, every_value):
    import os
    C = CliRun(a.cli_bin, a.cli_home)
    bodies = a.cli_bodies
    cells, syscells = [], []
    rowid = lambda: (C.rows("SELECT COALESCE(MAX(rowid),0) FROM disclosure_log") or [[0]])[0][0]

    def one(name, text, sysp, value, ptype, cell, judge_text):
        before = len(recorded(bodies))
        brow = rowid()
        args = ["ask", text] + (["--system", sysp] if sysp else [])
        rc, out, err = C.run(args)
        got = recorded(bodies)[before:]
        before_fail = T.fail
        if not T.check(rc == 0, "%s: loke ask exited 0 (got %s: %s)" % (name, rc, (err or out)[-200:])):
            return
        gens = model_requests(got)
        if not T.check(len(gens) == 1, "%s: exactly one request reached the model (got %d)" % (name, len(gens))):
            return
        body = gens[0][2]
        msys, muser = chat_parts(body)
        for r in got:
            if ner_or_intent(r):
                continue
            T.check(not any(leaks(r[2], v) for v in every_value),
                    "%s: %s %s carries no raw identifier" % (name, r[0], r[1]))
        T.check(msys.startswith(GUARDIAN), "%s: the guardian is the start of the model's system message" % name)
        where = muser if judge_text else msys
        if value:
            T.check(re.search(r"\[%s_[0-9a-f]+_[0-9]+\]|\[%s_[0-9]+\]" % (ptype, ptype), where) is not None,
                    "%s: the model was sent a %s placeholder where the value was" % (name, ptype))
        elif judge_text:
            T.check(muser == text, "%s: text with no identifier reached the model unchanged" % name)
        T.check(("echo: " + text) in out, "%s: the answer printed is restored byte for byte" % name)
        T.check(PLACEHOLDER.search(out) is None, "%s: no placeholder survives into what the user reads" % name)
        disclosure_checks(T, C, name, brow, [body], ["completed"])
        cell["guardian"] = msys.startswith(GUARDIAN)
        cell["dispatched"] = True
        cell["passed"] = T.fail == before_fail

    for tmpl in templates:
        for (dtype, value, ptype) in CASES:
            name = "cli %s x %s" % (tmpl["id"], dtype)
            sysp, user = render(tmpl, raw_data(tmpl, value))
            cell = {"template": tmpl["id"], "detector": dtype, "passed": False}
            one(name, user, sysp, value, ptype, cell, True)
            cells.append(cell)

    clean = "Summarise the weather report for today."
    for (dtype, value, ptype) in CASES:
        if not value:
            continue
        name = "cli system_prompt x %s" % dtype
        cell = {"detector": dtype, "passed": False}
        one(name, clean, "You are assisting a customer. Their record: %s. Be brief." % value, value, ptype, cell, False)
        syscells.append(cell)

    # A refused hop (F5.3): with the kill switch on, nothing is sent and no disclosure row is
    # written; the refusal is audited.
    rc, out, err = C.run(["kill-switch", "on"])
    T.check(rc == 0, "cli: loke kill-switch on (got %s %s)" % (rc, (err or out)[-160:]))
    before, brow = len(recorded(bodies)), rowid()
    nks = len(C.rows("SELECT id FROM audit_log WHERE event_type='kill_switch_refused'"))
    rc, out, err = C.run(["ask", "Customer record: harness.probe@example.com. Status open."])
    got = recorded(bodies)[before:]
    T.check(rc != 0, "cli kill switch: loke ask refuses (exit %s)" % rc)
    T.check(len(model_requests(got)) == 0, "cli kill switch: nothing reached the model")
    T.check(rowid() == brow, "cli kill switch: NO DISCLOSURE ROW FOR A REFUSED HOP")
    T.check(len(C.rows("SELECT id FROM audit_log WHERE event_type='kill_switch_refused'")) > nks,
            "cli kill switch: the refused hop is audited as kill_switch_refused")
    rc, out, err = C.run(["kill-switch", "off"])
    T.check(rc == 0, "cli: loke kill-switch off")

    # The chain and the record, intact over everything above.
    rc, out, err = C.run(["audit", "verify"])
    T.check(rc == 0, "cli: loke audit verify passes over every row written (exit %s: %s)" % (rc, (out + err)[-300:]))
    raw = b""
    for suffix in ("", "-wal"):
        try:
            with open(C.db + suffix, "rb") as f:
                raw += f.read()
        except FileNotFoundError:
            pass
    T.check(len(raw) > 0, "cli: loke.db was written")
    found = [v for v in every_value if v.encode("utf-8") in raw]
    T.check(not found, "cli: NO RAW IDENTIFIER IS ANYWHERE IN loke.db (found %s)" % found)
    allrec = recorded(bodies)
    T.check(not any(leaks(r[2], v) for r in allrec if not ner_or_intent(r) for v in every_value),
            "cli: across all %d recorded requests, none but the NER layer's carried a raw identifier" % len(allrec))
    return cells, syscells


def cli_fallback(T, a, every_value):
    """F5.3: the first hop fails (its model answers nothing), the next answers. Two disclosure
    rows, the first failed and the second completed, on <id> and <id>-h1."""
    C = CliRun(a.cli_bin, a.cli_home)
    bodies = a.cli_fallback_bodies
    brow = (C.rows("SELECT COALESCE(MAX(rowid),0) FROM disclosure_log") or [[0]])[0][0]
    text = "Customer record, keep it confidential: harness.probe@example.com. Status open."
    rc, out, err = C.run(["ask", text])
    got = recorded(bodies)
    gens = model_requests(got)
    name = "cli fallback"
    T.check(rc == 0, "%s: loke ask exited 0 (got %s %s)" % (name, rc, (err or out)[-200:]))
    T.check(len(gens) == 2, "%s: two hops reached the model (got %d)" % (name, len(gens)))
    T.check(("echo: " + text) in out and "fallback: answered by" in out, "%s: answered by the second hop, restored" % name)
    T.check(not any(leaks(r[2], v) for r in gens for v in every_value), "%s: neither hop sent a raw value" % name)
    rows = disclosure_checks(T, C, name, brow, [g[2] for g in gens], ["failed", "completed"])
    if len(rows) == 2:
        T.check(rows[1][1] == rows[0][1] + "-h1", "%s: the second hop's correlation id is the first's with -h1 (%s, %s)" % (name, rows[0][1], rows[1][1]))
    rc, out, err = C.run(["audit", "verify"])
    T.check(rc == 0, "%s: loke audit verify passes (exit %s)" % (name, rc))



def cli_main(T, a, templates, every_value):
    """The CLI phases only, run by scripts/smoke_privacy_harness.sh after the browser's, each
    against its own stand-in."""
    if a.cli_bodies:
        cells, syscells = cli_phase(T, a, templates, every_value)
        print("  privacy harness (loke ask, CLI): %d templates x %d detector cases = %d cells, %d passed every "
              "assertion, guardian reached the model in %d; %d system-prompt cells, %d passed; %d assertions ok, %d failed"
              % (len(templates), len(CASES), len(cells), sum(1 for c in cells if c["passed"]),
                 sum(1 for c in cells if c.get("guardian")), len(syscells), sum(1 for c in syscells if c["passed"]),
                 T.ok, T.fail))
        if a.report:
            with open(a.report, "w") as f:
                json.dump({"path": "cli.ask", "cells": cells, "syscells": syscells, "ok": T.ok, "fail": T.fail,
                           "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f, indent=1)
    if a.cli_fallback_bodies:
        cli_fallback(T, a, every_value)
        print("  privacy harness (loke ask fallback): %d assertions ok, %d failed" % (T.ok, T.fail))
    return 0 if T.fail == 0 else 1

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loke", help="the loke server: drive POST /api/pipeline")
    ap.add_argument("--bodies", help="the browser phase's stand-in log (<log>.bodies)")
    ap.add_argument("--templates", required=True)
    ap.add_argument("--cli-bin", help="the built loke-cli binary: drive `loke ask` (F3.9, F5.3)")
    ap.add_argument("--cli-home", help="the throwaway HOME whose .loke/config.toml names the CLI stand-in")
    ap.add_argument("--cli-bodies", help="the CLI stand-in's log: run the CLI matrix")
    ap.add_argument("--cli-fallback-bodies", help="the CLI stand-in's log, first model failing: run the CLI fallback")
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

    every_value = [c[1] for c in CASES if c[1]]
    if not a.loke:
        return cli_main(T, a, templates, every_value)
    pipeline = a.loke + "/api/pipeline"
    approve = a.loke + "/api/approve"
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
            # 6. The NER layer found the name only where the text holds it (F3.9d).
            check_ner(T, reply, sysp + "\n" + user, name)
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
                check_ner(T, reply, req["system_prompt"] + "\n" + clean, name)
        cell["passed"] = T.fail == before_fail
        syscells.append(cell)

    # F3.9c: the no-custody dispatch carries the guardian, and the guardian's words are framing.
    guardian = read_guardian(a.templates.replace("template.tk", "guardian.tk"))
    gl = guardian.lower()
    T.check(guardian.startswith(GUARDIAN) and all(w in gl for w in ("never", "data", "audit")),
            "the guardian was read from guardian.tk and holds the words the no-custody dataset's cells equal")
    ncsent = "ZQ-NC-SENTINEL-3917"
    ncdata = {"dataset_name": "words", "headers": ["word", "customer"],
              "rows": [["never", ncsent], ["data", "Harriet Oyelaran"], ["Audit", "Bo"]]}
    ncq = "Which word appears most often?"
    nccells = []
    for (name, text, sysp, refused) in [
            ("no-custody x clean", ncq, "", False),
            ("no-custody x clean system prompt", ncq, "Answer in one sentence.", False),
            ("no-custody x guardian word in the question", "Did any customer never renew?", "", True),
            ("no-custody x guardian word in the system prompt", ncq, "Treat the data carefully.", True),
            ("no-custody x other cell in the question", "What did Harriet Oyelaran choose?", "", True),
            ("no-custody x other cell in the system prompt", ncq, "Note %s first." % ncsent, True)]:
        cell = {"case": name, "passed": False}
        before_fail = T.fail
        req = dict(ncdata, text=text)
        if sysp:
            req["system_prompt"] = sysp
        before = len(recorded(a.bodies))
        status, out = post(pipeline, req)
        got = recorded(a.bodies)[before:]
        gens = [r for r in got if r[0] == "POST" and r[1] == "/api/generate"]
        try:
            reply = json.loads(out)
        except ValueError:
            reply = {}
        if refused:
            T.check(status == 422 and reply.get("refusal") == "sentinel_fail",
                    "%s: refused as sentinel_fail (got %s %s)" % (name, status, out[:160]))
            T.check(len(gens) == 0, "%s: nothing reached the model (got %d)" % (name, len(gens)))
        elif T.check(status == 200 and reply.get("custody") == "no-custody" and reply.get("custody_check") == "sentinel_pass",
                     "%s: answered no-custody, sentinel_pass (got %s %s)" % (name, status, out[:160])):
            if T.check(len(gens) == 1, "%s: exactly one dispatch reached the model (got %d)" % (name, len(gens))):
                sysfield = system_of(gens[0][2])
                want = guardian + ("\n" + sysp if sysp else "")
                cell["guardian"] = sysfield.startswith(guardian)
                T.check(sysfield == want, "%s: the model's system is the guardian byte for byte%s" % (
                    name, ", then the caller's" if sysp else ""))
                try:
                    sent = json.loads(gens[0][2])
                except ValueError:
                    sent = {}
                rest = "\n".join([sysfield[len(guardian):] if cell["guardian"] else sysfield,
                                  sent.get("prompt", ""), sent.get("model", "")])
                T.check(not any(v.lower() in rest.lower() for row in ncdata["rows"] for v in row if len(v) >= 4),
                        "%s: outside the guardian, the body holds no cell of the dataset" % name)
                T.check(reply.get("response") == "echo: " + text, "%s: the reply is the question's echo" % name)
        cell["passed"] = T.fail == before_fail
        nccells.append(cell)

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
          "%d held first; %d no-custody cells, %d passed, guardian reached the model in %d of the %d dispatched; "
          "%d assertions ok, %d failed"
          % (len(templates), len(CASES), len(cells), npass, nheld, nguard, len(syscells), spass, sheld,
             len(nccells), sum(1 for c in nccells if c["passed"]), sum(1 for c in nccells if c.get("guardian")),
             sum(1 for c in nccells if "guardian" in c), T.ok, T.fail))
    if a.report:
        with open(a.report, "w") as f:
            json.dump({"templates": [t["id"] for t in templates], "cases": [c[0] for c in CASES],
                       "cells": cells, "syscells": syscells, "nccells": nccells, "ok": T.ok, "fail": T.fail,
                       "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}, f, indent=1)
    if a.record:
        record(a.record, templates, cells, syscells)
    return 0 if T.fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
