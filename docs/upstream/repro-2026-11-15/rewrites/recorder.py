#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""[w2 copy: fixed port from W2_PORT env, PUT recorded, selected headers logged]
A local HTTP server that records EVERY request it receives, whatever the method. (VM1.6e)

Usage: http_recorder.py <log-file> <port-file> [answer|garbage|silent]

It binds a port the OS hands out on 127.0.0.1 and writes the number to <port-file> once it
is listening, so a test needs no fixed port and two runs cannot collide. Each request is
appended to <log-file> as one line, `METHOD path body`, BEFORE the reply is sent, so a test
that reads the log after a call returns sees exactly what arrived.

It answers in the shape of the local sidecars loke talks to, enough for a client to parse:
Ollama (/api/tags, /api/ps, /api/version, /api/chat, /api/generate, /api/pull, /api/delete),
Presidio (/health, /analyze) and LLMLingua (/health, /compress). The replies are fixed and
compact (no spaces after `:`), as Ollama's are, because shared.jsonobj's nested lookup
matches `"key":` exactly.

The optional mode is for testing what a client does with a service that is up but useless:
`garbage` answers every request with 200 and a JSON object that is not what any caller asked
for (an error object where Presidio sends an array, prose where the NER model was asked for
an array); `silent` answers 200 with an empty body. Both still record.

scripts/lib/fake_ollama.py is the Ollama stand-in smoke_e2e.sh uses; it logs POSTs only, and
a GET that never arrives is precisely what VM1.6e is about, so this is a separate file.
"""
import http.server, json, os, sys

LOG = sys.argv[1]
PORTFILE = sys.argv[2]
MODE = sys.argv[3] if len(sys.argv) > 3 else "answer"
SEPS = (",", ":")

# Presidio's /analyze answer for "Jane Citizen" at the start of the text, and the NER model's
# reply, which Ollama wraps as message.content.
PRESIDIO = [{"entity_type": "PERSON", "start": 0, "end": 12, "score": 0.85}]
NER = '[{"type":"PERSON","value":"Jane Citizen"}]'


class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _record(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        body = self.rfile.read(n).decode("utf-8", "replace") if n else ""
        with open(LOG, "a") as f:
            f.write("%s %s %s | hdr:%s\n" % (self.command, self.path, body.replace("\n", "\\n"), ";".join("%s=%s" % (k, v) for k, v in self.headers.items() if k.lower().startswith("x-") or k.lower() in ("authorization", "content-type"))))
        return body

    def _send(self, obj):
        b = json.dumps(obj, separators=SEPS).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _answer(self):
        p = self.path.split("?")[0]
        if MODE == "silent":
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()
        elif MODE == "garbage":
            self._send({"error": "recorder in garbage mode", "message": {"role": "assistant", "content": "I could not find any entities."}})
        elif p == "/api/tags":
            self._send({"models": [{"name": "fake:latest", "size": 7, "digest": "d1"}]})
        elif p == "/api/ps":
            self._send({"models": [{"name": "fake:latest", "size": 7}]})
        elif p == "/api/version":
            self._send({"version": "0.0.0-recorder"})
        elif p == "/api/chat":
            self._send({"model": "fake", "message": {"role": "assistant", "content": NER}, "done": True})
        elif p == "/api/generate":
            self._send({"model": "fake", "response": "generated-by-recorder", "done": True})
        elif p == "/api/pull":
            self._send({"status": "success"})
        elif p == "/api/delete":
            self._send({})
        elif p == "/health":
            self._send({"status": "ok"})
        elif p == "/analyze":
            self._send(PRESIDIO)
        elif p == "/compress":
            self._send({"compressed_prompt": "short", "origin_tokens": 10, "compressed_tokens": 5, "ratio": "2.0x"})
        else:
            self._send({})

    def do_GET(self):
        self._record()
        self._answer()

    def do_POST(self):
        self._record()
        self._answer()

    def do_PUT(self):
        self._record()
        self._answer()

    def do_DELETE(self):
        self._record()
        self._answer()


srv = http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("W2_PORT","0"))), H)
tmp = PORTFILE + ".tmp"
with open(tmp, "w") as f:
    f.write(str(srv.server_address[1]))
os.replace(tmp, PORTFILE)
srv.serve_forever()
