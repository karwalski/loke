#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""A local HTTP server that records EVERY request it receives, whatever the method. (VM1.6e)

Usage: http_recorder.py <log-file> <port-file> [answer|garbage|silent]

It binds a port the OS hands out on 127.0.0.1 and writes the number to <port-file> once it
is listening, so a test needs no fixed port and two runs cannot collide. Each request is
appended to <log-file> as one line, `METHOD path body`, BEFORE the reply is sent, so a test
that reads the log after a call returns sees exactly what arrived.

It answers in the shape of the local sidecars loke talks to, enough for a client to parse:
Ollama (/api/tags, /api/ps, /api/version, /api/chat, /api/generate, /api/pull, /api/delete),
Presidio (/health, /analyze), LLMLingua (/health, /compress), and since VM1.6f an MCP server
(/mcp), Exo (/v1/health, /v1/nodes, /v1/chat/completions), Ollama's /api/show and loke's own
/api/pipeline; any other path answers `{}`, which is what a webhook test needs. The replies are fixed and
compact (no spaces after `:`), as Ollama's are, because shared.jsonobj's nested lookup
matches `"key":` exactly.

The optional mode is for testing what a client does with a service that is up but useless:
`garbage` answers every request with 200 and a JSON object that is not what any caller asked
for (an error object where Presidio sends an array, prose where the NER model was asked for
an array); `silent` answers 200 with an empty body. Both still record.

scripts/lib/fake_ollama.py is the Ollama stand-in smoke_e2e.sh uses; it logs POSTs only, and
a GET that never arrives is precisely what VM1.6e is about, so this is a separate file.

F5.11: every request's headers are also appended to `<log-file>.headers`, as a
`METHOD path` line, one `name: value` line per header in the order they arrived (a
duplicated header appears twice), and a blank line. The hosted-provider paths
(/v1/messages, /v1/chat/completions) answer in Anthropic's and OpenAI's shapes, so the
cloud dispatch can be judged by what arrives without a real key.
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

# The hosted providers' success shapes, trimmed to the fields loke reads (F5.11).
ANTHROPIC = {"id": "msg_recorder", "type": "message", "role": "assistant", "model": "claude-recorder",
             "content": [{"type": "text", "text": "answered-by-recorder"}],
             "usage": {"input_tokens": 11, "output_tokens": 7}}
OPENAI = {"id": "chatcmpl-recorder", "object": "chat.completion", "model": "gpt-recorder",
          "choices": [{"index": 0, "message": {"role": "assistant", "content": "answered-by-recorder"}}],
          "usage": {"prompt_tokens": 13, "completion_tokens": 5}}


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
        return body

    def _send(self, obj):
        b = json.dumps(obj, separators=SEPS).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _answer(self, body=""):
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
        elif p == "/api/chat" and "Classify the intent" in body:
            # core.router.intent's classification request (VM1.6f): a task name.
            self._send({"model": "fake", "message": {"role": "assistant", "content": "code_review"}, "done": True})
        elif p == "/api/chat":
            self._send({"model": "fake", "message": {"role": "assistant", "content": NER}, "done": True})
        elif p == "/api/show":
            self._send({"digest": "sha256:recorder-digest", "modelinfo": {}})
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
        elif p == "/api/pipeline":
            self._send({"response": "pipeline-answer"})
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
        elif p == "/v1/messages":
            self._send(ANTHROPIC)
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


srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
tmp = PORTFILE + ".tmp"
with open(tmp, "w") as f:
    f.write(str(srv.server_address[1]))
os.replace(tmp, PORTFILE)
srv.serve_forever()
