#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""A local HTTP server that records EVERY request it receives, whatever the method. (VM1.6e)

Usage: http_recorder.py <log-file> <port-file> [answer|garbage|silent|echo|mcpecho|analyzepast|harness] [<cert.pem> <key.pem>]

It binds a port the OS hands out on 127.0.0.1 and writes the number to <port-file> once it
is listening, so a test needs no fixed port and two runs cannot collide. Each request is
appended to <log-file> as one line, `METHOD path body`, BEFORE the reply is sent, so a test
that reads the log after a call returns sees exactly what arrived.

It answers in the shape of the local sidecars loke talks to, enough for a client to parse:
Ollama (/api/tags, /api/ps, /api/version, /api/chat, /api/generate, /api/pull, /api/delete),
Presidio (/health, /analyze), the privacy-filter sidecar (/detect, /anonymise, AD1.4), LLMLingua (/health, /compress), and since VM1.6f an MCP server
(/mcp), Exo (/v1/health, /v1/nodes, /v1/chat/completions), Ollama's /api/show and loke's own
/api/pipeline, and since VM1.6h a policy document (/policy.json), and since VM1.6g an OAuth
token endpoint (/oauth/token, /oauth/revoke) and GitHub's create-issue path
(/repos/<owner>/<repo>/issues, answered 201), and since VM1.6i a `?status=NNN` query on any
of those paths answers that status instead with the same body; any other path answers `{}`, which is what a webhook test needs. The replies are fixed and
compact (no spaces after `:`), as Ollama's are, because shared.jsonobj's nested lookup
matches `"key":` exactly.

The optional mode is for testing what a client does with a service that is up but useless:
`garbage` answers every request with 200 and a JSON object that is not what any caller asked
for (an error object where Presidio sends an array, prose where the NER model was asked for
an array); `silent` answers 200 with an empty body. Both still record. `pfbroken` (F3b.3)
answers everything as `answer` does except /detect, which claims two entities it does not
deliver in readable form.

`tokenmodel` (F3b.7) answers as `answer` does except /health and /detect, which answer as
packages/privacy-filter/server.py does serving a registered token classifier: see
TOKEN_SPANS below.

`echo` (GA1.5) answers as `answer` does except in two places, so that the request path can be
judged by what it sends: /compress keeps every word holding a `[` (a loke placeholder) and
every other word, as a compressor that respects placeholders would, and /api/generate answers
with the prompt it was given, as a model that repeats its input would. In `answer` mode
/compress answers "short", which keeps no placeholder: a compressor that drops them.

scripts/lib/fake_ollama.py is the Ollama stand-in smoke_e2e.sh uses; it logs POSTs only, and
a GET that never arrives is precisely what VM1.6e is about, so this is a separate file.

`mcpecho` (MK6.14) answers as `answer` does except a tools/call to /mcp, which answers with
one text content item per string value of the call's arguments, in document order, encoded
by Python's json.dumps with its default ensure_ascii, so a non-ASCII character comes back as
a \\uXXXX escape. An upstream tool that repeats what it was given is how a test sees whether
the broker restores a placeholder exactly, whatever escapes the upstream's encoder chose.
In that mode /analyze reports a PERSON wherever `Jane` and `Citizen` stand together across
whitespace, at the offsets Python gives (code points), instead of the fixed span above; since
MK6.16 also each name in PERSONS, which hold non-ASCII characters of every UTF-8 length.
`analyzepast` (MK6.16) answers as `answer` does except /analyze, which reports a PERSON span
ending past the end of the text it was sent: a span loke cannot place, which must refuse.

F5.11: every request's headers are also appended to `<log-file>.headers`, as a
`METHOD path` line, one `name: value` line per header in the order they arrived (a
duplicated header appears twice), and a blank line. The hosted-provider paths
(/v1/messages, /v1/chat/completions) answer in Anthropic's and OpenAI's shapes, so the
cloud dispatch can be judged by what arrives without a real key.

MK6.13: the log line above writes a raw newline in a body as the two characters `\n`, which
is exactly what an escaped one looks like, so it cannot tell a body a strict parser accepts
from one it refuses. Every request is therefore also appended to `<log-file>.bodies` as one
line, `json.dumps([method, path, body])`, which keeps the body's exact characters.
scripts/lib/json_field.py reads that file and judges a body with Python's strict parser.

F5.11 (https): given a certificate and its key after the mode, it serves TLS with them, so a
test can see what toke's https client does with a certificate it should or should not trust.
The handshake happens before any request is read, and each one is appended to
`<log-file>.tls` as `handshake ok` or `handshake failed: <reason>`. So when a client refuses
the certificate the test can see both that a connection was attempted (the `.tls` line) and
that no request arrived (nothing in `<log-file>`). scripts/lib/tls_fixture.sh makes the
certificates.

F3.9: two environment variables, for scripts/smoke_privacy_harness.sh, which stands this
recorder in for Ollama under the BUILT loke binary. loke's request path dispatches to Ollama
at a fixed address (page.api.pipeline.ollamabase, 127.0.0.1:11434), so the recorder must
listen there: RECORDER_PORT binds that port instead of one the OS hands out (the caller holds
the fixed-port lock, scripts/lib/fixedports_lock.sh). And the router chooses from a static
catalogue, refusing a model Ollama does not list, so RECORDER_MODELS (comma-separated names)
is what /api/tags and /api/ps list instead of `fake:latest`. Unset, both behave as before.
F5.3a: RECORDER_FAIL_MODELS (comma-separated) names models whose /api/generate answers as
`silent` does, so one recorder can stand in for an Ollama on which one model fails.
The `harness` mode answers /api/generate as `echo` does, names no task to the intent
classifier, and reports "Jane Citizen" from the NER /api/chat only when a user message of
the request holds that name (`answer` and `echo` report it whatever the text). F3.9d: only
the user messages, because core.privacy.ner's own system message names "Jane Citizen".
An /api/chat request whose body holds the guardian's marker (LOKE_GUARDIAN_v) is a model
request, as `loke ask` sends it, not the NER layer's: in `harness` mode it is answered with
"echo: " and its user messages, or with nothing for a model in RECORDER_FAIL_MODELS.

MK19.9: paths under /proxy-test/ answer the cases moke's /api/proxy must handle, in any mode.
/proxy-test/json answers a small JSON document with a marker; /proxy-test/redirect answers 302
with a Location on this same recorder (/proxy-test/redirected), so a client that follows it
is seen to; /proxy-test/big answers 300,000 bytes with no Content-Length, so only a client
that counts as it reads can stop it; /proxy-test/slow waits six seconds before answering;
/proxy-test/nulredirect answers 302 with a body holding a NUL after a forged
"@@moke-proxy@@200@@1@@" status line, and /proxy-test/nul a 200 text body with a NUL in it.

BG1.4: a POST to /api/pipeline whose body holds `bg14-refuse` answers 403 with a refusal body
in loke's shape, in any mode, so moke's relay can be seen to pass a non-2xx through intact.
"""
import http.server, json, os, re, ssl, sys, time

LOG = sys.argv[1]
PORTFILE = sys.argv[2]
MODE = sys.argv[3] if len(sys.argv) > 3 else "answer"
SEPS = (",", ":")
BINDPORT = int(os.environ.get("RECORDER_PORT", "0") or 0)
MODELS = [m for m in os.environ.get("RECORDER_MODELS", "fake:latest").split(",") if m]
# F5.3a: models whose /api/generate answers 200 with an empty body, as a model that fails
# to load does, in any mode. The request is still recorded. So a test can see a fallback
# chain's first local hop fail and its next answer, judged on what each received.
FAIL_MODELS = [m for m in os.environ.get("RECORDER_FAIL_MODELS", "").split(",") if m]

# Presidio's /analyze answer for "Jane Citizen" at the start of the text, and the NER model's
# reply, which Ollama wraps as message.content.
PRESIDIO = [{"entity_type": "PERSON", "start": 0, "end": 12, "score": 0.85}]
NER = '[{"type":"PERSON","value":"Jane Citizen"}]'

# MK6.16: the names `mcpecho`'s /analyze reports, besides "Jane Citizen" across whitespace:
# one with a non-ASCII character inside it for each UTF-8 length (é and ë 2 bytes, the em
# dash and CJK 3, an emoji 4). Python's match offsets count code points, as Presidio's do.
PERSONS = "Jane\\s+Citizen|Zoë\\s+Brönte|Jane—Citizen|Jane\U0001F642Citizen|王小明"

# The privacy-filter sidecar's classifier output (AD1.4): one confident span and one weak
# one, so a threshold between them visibly suppresses one. The recorder applies the
# threshold the way packages/privacy-filter/server.py does, with that file's default of 0.0
# when the request names none, and reports what it applied.
PF_SPANS = [{"type": "private_person", "value": "Jane Citizen", "start": 0, "end": 12, "confidence": 0.95, "placeholder": "[NAME_1]"},
            {"type": "private_date", "value": "Tuesday", "start": 20, "end": 27, "confidence": 0.4, "placeholder": "[DATE_1]"}]


# F3b.8 (7): the sidecar's own default threshold, applied when a request names none, as
# server.py's DEFAULT_THRESHOLD is (models.json's confidence_threshold, or LOKE_PF_THRESHOLD).
PF_DEFAULT = float(os.environ.get("RECORDER_PF_DEFAULT_THRESHOLD", "0") or 0)


def pf_answer(body, path):
    try:
        req = json.loads(body) if body else {}
    except ValueError:
        req = {}
    thr = req.get("threshold")
    thr = PF_DEFAULT if thr is None else min(max(float(thr), 0.0), 1.0)
    kept = [e for e in PF_SPANS if thr <= 0.0 or e["confidence"] >= thr]
    out = {"count": len(kept), "threshold": thr, "suppressed_below_threshold": len(PF_SPANS) - len(kept)}
    if path == "/detect":
        out["entities"] = kept
    else:
        out["anonymised"] = "recorder-anonymised"
        out["mappings"] = [{"placeholder": e["placeholder"], "type": e["type"]} for e in kept]
    return out

# F3b.7: `tokenmodel` stands in for packages/privacy-filter/server.py serving a registered
# token classifier (LOKE_PF_MODEL). /health names the model (RECORDER_MODEL_ID, default
# recorder/token-model) and its task; /detect reports, with the model's OWN labels, each of
# these values the text holds, at its code-point offsets, applying the threshold it is sent
# as the sidecar does. WIDGET is a label no test's mapping names.
TOKEN_MODEL_ID = os.environ.get("RECORDER_MODEL_ID", "recorder/token-model")
TOKEN_SPANS = [("Jane Citizen", "PER", 0.91), ("Brisbane", "LOC", 0.88),
               ("Zorblax", "WIDGET", 0.7), ("Acme", "ORG", 0.3)]


def token_answer(body):
    try:
        req = json.loads(body) if body else {}
    except ValueError:
        req = {}
    text = req.get("text", "")
    thr = req.get("threshold")
    thr = 0.0 if thr is None else min(max(float(thr), 0.0), 1.0)
    found = [{"type": label, "value": v, "start": text.find(v), "end": text.find(v) + len(v), "confidence": c}
             for v, label, c in TOKEN_SPANS if v in text]
    kept = [e for e in found if thr <= 0.0 or e["confidence"] >= thr]
    return {"entities": kept, "count": len(kept), "threshold": thr,
            "suppressed_below_threshold": len(found) - len(kept), "model": TOKEN_MODEL_ID}


# The hosted providers' success shapes, trimmed to the fields loke reads (F5.11).
ANTHROPIC = {"id": "msg_recorder", "type": "message", "role": "assistant", "model": "claude-recorder",
             "content": [{"type": "text", "text": "answered-by-recorder"}],
             "usage": {"input_tokens": 11, "output_tokens": 7}}
OPENAI = {"id": "chatcmpl-recorder", "object": "chat.completion", "model": "gpt-recorder",
          "choices": [{"index": 0, "message": {"role": "assistant", "content": "answered-by-recorder"}}],
          "usage": {"prompt_tokens": 13, "completion_tokens": 5}}

# VM1.6g: an OAuth token endpoint's answer and GitHub's created issue, trimmed to the fields
# core.auth and core.feedback read.
OAUTH = {"access_token": "recorder-access-token", "refresh_token": "recorder-refresh-token",
         "expires_in": 3600, "token_type": "Bearer"}
GITHUB_ISSUE = {"html_url": "https://recorder.invalid/issues/1", "number": 1}

# A policy set in the shape core.policy.loader reads from a file or a URL (VM1.6h).
POLICY = {"name": "recorder-policy", "regulations": [{"name": "recorder-reg", "jurisdiction": "AU", "version": "1",
          "rules": [{"id": "r1", "description": "no secrets", "action": "block", "severity": "high"}]}]}


def _strings(v):
    """Every string value in a decoded JSON value, in document order (keys excluded)."""
    if isinstance(v, str):
        return [v]
    if isinstance(v, list):
        return [s for x in v for s in _strings(x)]
    if isinstance(v, dict):
        return [s for x in v.values() for s in _strings(x)]
    return []


def _usertext(body):
    """The content of every `user` message of an Ollama /api/chat body, joined; "" when the
    body is not one. Not the system message, which is the caller's instruction (F3.9d)."""
    try:
        msgs = json.loads(body).get("messages", [])
    except (ValueError, AttributeError):
        return ""
    if not isinstance(msgs, list):
        return ""
    return "\n".join(m.get("content", "") for m in msgs
                     if isinstance(m, dict) and m.get("role") == "user" and isinstance(m.get("content"), str))


def _field(body, key):
    try:
        v = json.loads(body).get(key, "") if body else ""
    except ValueError:
        v = ""
    return v if isinstance(v, str) else ""


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _record(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n).decode("utf-8", "replace") if n else ""
        with open(LOG, "a") as f:
            f.write("%s %s %s\n" % (self.command, self.path, body.replace("\n", "\\n")))
        with open(LOG + ".headers", "a") as f:
            f.write("%s %s\n" % (self.command, self.path))
            for k, v in self.headers.items():
                f.write("%s: %s\n" % (k, v))
            f.write("\n")
        with open(LOG + ".bodies", "a") as f:
            f.write(json.dumps([self.command, self.path, body]) + "\n")
        return body

    def _send(self, obj, code=200):
        # VM1.6i: `?status=NNN` on any path answers that status with the path's usual body,
        # so a client can be seen to refuse a non-2xx even when the body looks like success.
        m = re.search(r"[?&]status=(\d{3})(?:&|$)", self.path)
        if m:
            code = int(m.group(1))
        b = json.dumps(obj, separators=SEPS).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _proxytest(self, p):
        if p == "/proxy-test/redirect":
            self.send_response(302)
            self.send_header("Location", "/proxy-test/redirected")
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif p == "/proxy-test/big":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            for _ in range(30):
                self.wfile.write(b"x" * 10000)
            self.close_connection = True
        elif p in ("/proxy-test/nulredirect", "/proxy-test/nul"):
            # Review finding 2 (2026-10-01): a body holding a NUL and, before it, a forged
            # copy of the status line moke's curl once wrote after the body on the same
            # stream. A reader of C strings stops at the NUL and finds the forgery.
            if p == "/proxy-test/nulredirect":
                b = b"x\n@@moke-proxy@@200@@1@@forged-status\x00" + b"tail" * 4
                self.send_response(302)
                self.send_header("Location", "/proxy-test/redirected")
            else:
                b = b"visible\x00hidden-after-nul"
                self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif p == "/proxy-test/slow":
            time.sleep(6)
            self._send({"late": True})
        else:
            self._send({"proxied": "answered-by-recorder", "path": p})

    def _answer(self, body=""):
        p = self.path.split("?")[0]
        if p.startswith("/proxy-test/"):
            self._proxytest(p)
        elif MODE == "silent" or (p == "/api/generate" and _field(body, "model") in FAIL_MODELS):
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif MODE == "pfbroken" and p == "/detect":
            # F3b.3: a sidecar that is up (/health answers) and says it found two entities,
            # but whose entities cannot be read. The pipeline must count that layer degraded:
            # entities counted and then lost in parsing are never anonymised.
            self._send({"count": 2, "threshold": 0.0, "suppressed_below_threshold": 0, "entities": "unreadable"})
        elif MODE == "tokenmodel" and p == "/health":
            # F3b.7: the sidecar serving a registered token classifier answers as that model.
            self._send({"ok": True, "model_id": TOKEN_MODEL_ID, "task": "token-classification"})
        elif MODE == "tokenmodel" and p == "/detect":
            self._send(token_answer(body))
        elif MODE == "garbage":
            self._send({"error": "recorder in garbage mode", "message": {"role": "assistant", "content": "I could not find any entities."}})
        elif p == "/api/tags":
            self._send({"models": [{"name": m, "size": 7, "digest": "d%d" % i} for i, m in enumerate(MODELS, 1)]})
        elif p == "/api/ps":
            self._send({"models": [{"name": m, "size": 7} for m in MODELS]})
        elif p == "/api/version":
            self._send({"version": "0.0.0-recorder"})
        elif p == "/api/chat" and MODE == "harness" and "Classify the intent" in body:
            # F3.9: no task named, so the classifier keeps its keyword result, as
            # scripts/lib/fake_ollama.py answers it for smoke_e2e.sh.
            self._send({"model": "fake", "message": {"role": "assistant", "content": ""}, "done": True})
        elif p == "/api/chat" and MODE == "harness" and "LOKE_GUARDIAN_v" in body:
            # F3.9 (the CLI paths): `loke ask` sends the model its request on /api/chat, with
            # the guardian as the system message, which the NER layer's request never holds.
            # Answered as /api/generate is, with the user messages echoed, so the restored
            # answer is exact; a model in RECORDER_FAIL_MODELS answers with nothing.
            if _field(body, "model") in FAIL_MODELS:
                self.send_response(200)
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self._send({"model": "fake", "message": {"role": "assistant", "content": "echo: " + _usertext(body)},
                            "done": True, "prompt_eval_count": 12, "eval_count": 9})
        elif p == "/api/chat" and MODE == "harness":
            # F3.9: an NER model that reports "Jane Citizen" only when the text holds it, so
            # a case without a name is not credited with one the text does not contain.
            # F3.9d: the text is the user messages' content alone. core.privacy.ner's own
            # system message names "Jane Citizen" as its example, so matching the whole body
            # reported the name on every request.
            found = NER if "Jane Citizen" in _usertext(body) else "[]"
            self._send({"model": "fake", "message": {"role": "assistant", "content": found}, "done": True})
        elif p == "/api/chat" and "Classify the intent" in body:
            # core.router.intent's classification request (VM1.6f): a task name.
            self._send({"model": "fake", "message": {"role": "assistant", "content": "code_review"}, "done": True})
        elif p == "/api/chat":
            self._send({"model": "fake", "message": {"role": "assistant", "content": NER}, "done": True})
        elif p == "/api/show":
            self._send({"digest": "sha256:recorder-digest", "modelinfo": {}})
        elif p == "/mcp" and MODE == "mcpecho" and '"tools/call"' in body:
            try:
                args = json.loads(body).get("params", {}).get("arguments", {})
            except ValueError:
                args = {}
            items = [{"type": "text", "text": s} for s in _strings(args)]
            b = json.dumps({"jsonrpc": "2.0", "id": 1, "result": {"content": items}}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
        elif p == "/mcp":
            # A JSON-RPC answer carrying both an initialize result and a tools/list result,
            # so one reply serves core.mcp and the broker (VM1.6f).
            self._send({"jsonrpc": "2.0", "id": 1, "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "recorder-mcp", "version": "9.9.9"},
                "tools": [{"name": "echo", "description": "echoes", "inputSchema": {"type": "object"}},
                          {"name": "sum", "description": "adds", "inputSchema": {"type": "object"}}],
                "content": [{"type": "text", "text": "tool-answer"}]}})
        elif p == "/v1/chat/completions":
            # Two callers share this path: the local Exo client (VM1.6f), which sends no
            # credentials, and the hosted OpenAI dispatch (F5.11), which always sends an
            # authorization header. The header decides which shape answers.
            if self.headers.get("authorization"):
                self._send(OPENAI)
            else:
                self._send({"choices": [{"message": {"role": "assistant", "content": "exo-answer"}}]})
        elif p == "/v1/nodes":
            self._send({"nodes": [{"id": "n1", "device": "recorder", "memory_gb": 16.0, "models": ["m"]}]})
        elif p == "/api/pipeline" and "bg14-refuse" in body:
            # BG1.4: a refusal in loke's shape, so a relay can be seen to keep the status and
            # the reason rather than turn them into a generic upstream error.
            self._send({"ok": False, "error": "refused-by-recorder", "approval_required": True}, 403)
        elif p == "/api/pipeline":
            self._send({"response": "pipeline-answer"})
        elif p == "/api/generate" and MODE in ("echo", "harness"):
            self._send({"model": "fake", "response": "echo: " + _field(body, "prompt"), "done": True,
                        "prompt_eval_count": 12, "eval_count": 9})
        elif p == "/api/generate":
            self._send({"model": "fake", "response": "generated-by-recorder", "done": True})
        elif p == "/api/pull":
            self._send({"status": "success"})
        elif p == "/api/delete":
            self._send({})
        elif p == "/health":
            self._send({"status": "ok"})
        elif p == "/analyze" and MODE == "mcpecho":
            # MK6.14: a PERSON wherever "Jane" and "Citizen" stand together, across any
            # whitespace, at Python's offsets (code points), as Presidio reports them.
            # MK6.16: and the names in PERSONS, which hold 2-, 3- and 4-byte characters.
            self._send([{"entity_type": "PERSON", "start": m.start(), "end": m.end(), "score": 0.85}
                        for m in re.finditer(PERSONS, _field(body, "text"))])
        elif p == "/analyze" and MODE == "analyzepast":
            # MK6.16: a span that cannot be placed: it ends three code points past the text.
            n = len(_field(body, "text"))
            self._send([{"entity_type": "PERSON", "start": 0, "end": n + 3, "score": 0.85}])
        elif p == "/analyze":
            self._send(PRESIDIO)
        elif p in ("/detect", "/anonymise"):
            self._send(pf_answer(body, p))
        elif p == "/v1/messages":
            self._send(ANTHROPIC)
        elif p in ("/oauth/token", "/oauth/revoke"):
            # VM1.6g: an OAuth token endpoint, as core.auth.oauth and refresh read it.
            self._send(OAUTH)
        elif p.startswith("/repos/") and p.endswith("/issues"):
            # VM1.6g: GitHub's create-issue answer (201), as core.feedback reads it.
            self._send(GITHUB_ISSUE, 201)
        elif p == "/policy.json":
            # core.policy.loader.loadurl's enterprise policy document (VM1.6h).
            self._send(POLICY)
        elif p == "/compress" and MODE == "echo":
            words = _field(body, "prompt").split(" ")
            kept = [w for i, w in enumerate(words) if i % 2 == 0 or "[" in w]
            self._send({"compressed_prompt": " ".join(kept), "origin_tokens": len(words),
                        "compressed_tokens": len(kept), "ratio": "echo"})
        elif p == "/compress":
            self._send({"compressed_prompt": "short", "origin_tokens": 10, "compressed_tokens": 5, "ratio": "2.0x"})
        else:
            self._send({})

    def do_GET(self):
        self._record()
        self._answer()

    def do_POST(self):
        self._answer(self._record())

    def do_DELETE(self):
        self._record()
        self._answer()


CERT = sys.argv[4] if len(sys.argv) > 5 else ""
KEY = sys.argv[5] if len(sys.argv) > 5 else ""


class TLSServer(http.server.ThreadingHTTPServer):
    """Handshakes each connection as it is accepted, and records the outcome."""

    def get_request(self):
        sock, addr = self.socket.accept()
        sock.settimeout(10)
        try:
            tls = TLS_CTX.wrap_socket(sock, server_side=True)
        except (ssl.SSLError, OSError) as e:
            with open(LOG + ".tls", "a") as f:
                f.write("handshake failed: %s\n" % (getattr(e, "reason", None) or e))
            sock.close()
            raise
        with open(LOG + ".tls", "a") as f:
            f.write("handshake ok\n")
        return tls, addr


if CERT:
    TLS_CTX = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    TLS_CTX.load_cert_chain(CERT, KEY)
    srv = TLSServer(("127.0.0.1", BINDPORT), H)
else:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", BINDPORT), H)
tmp = PORTFILE + ".tmp"
with open(tmp, "w") as f:
    f.write(str(srv.server_address[1]))
os.replace(tmp, PORTFILE)
srv.serve_forever()
