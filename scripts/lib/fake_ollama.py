#!/usr/bin/env python3
"""A stand-in for Ollama that records every request it receives (scripts/smoke_e2e.sh).

Answers /api/tags (listing FAKE_OLLAMA_MODELS, comma-separated) and /api/ps, and answers /api/generate and /api/chat by echoing the first
loke placeholder it finds in the prompt, so the round trip through restoration can be checked.
Every POST is appended to the log file named on the command line, so the test can assert
exactly what a model would have been given.

Four optional variables, all off by default so smoke_e2e.sh sees what it always saw:
FAKE_OLLAMA_REPLY replaces the echoed sentence with a fixed reply (smoke_benchmark.sh),
FAKE_OLLAMA_PORT moves it off 11434 so a run needs no machine-wide lock, and
FAKE_OLLAMA_COMPACT=1 writes JSON with no spaces, as Ollama itself does. shared.jsonobj's
nested lookup matches `"key":` with no space, so a reader built on it needs this.
FAKE_OLLAMA_DIGESTS ("name=digest,name=digest") gives a listed model its own digest in
/api/tags; any other model is listed with the digest "x" (smoke_e2e.sh, DA1.9).
FAKE_OLLAMA_DELAYS_MS ("0,40,5") delays the Nth logged completion by the Nth entry, cycling,
so repeated benchmark runs time differently and their interval is not a single point
(smoke_benchmark.sh, VM1.3).
"""
import http.server, json, os, sys, threading, time
MODELS=os.environ.get("FAKE_OLLAMA_MODELS","qwen2.5:7b,llama3:latest").split(",")
LOG=sys.argv[1]
REPLY=os.environ.get("FAKE_OLLAMA_REPLY")
PORT=int(os.environ.get("FAKE_OLLAMA_PORT","11434"))
SEPS=(",",":") if os.environ.get("FAKE_OLLAMA_COMPACT")=="1" else None
DIGESTS=dict(kv.split("=",1) for kv in os.environ.get("FAKE_OLLAMA_DIGESTS","").split(",") if "=" in kv)
DELAYS=[int(x) for x in os.environ.get("FAKE_OLLAMA_DELAYS_MS","").split(",") if x.strip()]
SERVED=[0]
SERVEDLOCK=threading.Lock()
class H(http.server.BaseHTTPRequestHandler):
    def _send(self,obj):
        b=json.dumps(obj,separators=SEPS).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
    def do_GET(self):
        if self.path.startswith('/api/tags'): self._send({"models":[{"name":m,"size":1,"digest":DIGESTS.get(m,"x")} for m in MODELS if m]})
        elif self.path.startswith('/api/ps'): self._send({"models":[]})
        else: self._send({})
    def do_POST(self):
        n=int(self.headers.get('Content-Length',0)); body=self.rfile.read(n).decode('utf-8','replace')
        # VM1.6e: loke's NER detection layer asks the same local Ollama to FIND entities, and
        # that request carries the prompt in clear, by design. It is not the model the prompt
        # is forwarded to, so it goes to its own log and does not count as "the model saw it".
        # Until VM1.6e the NER layer never sent anything, so this never arose. An empty array
        # is a completed scan that found nothing, which leaves the forward path unchanged.
        if self.path.startswith('/api/chat') and 'named entity recognition system' in body:
            open(LOG+'.ner','a').write(self.path+' '+body+'\n')
            self._send({"model":"llama3","message":{"role":"assistant","content":"[]"},"done":True}); return
        # VM1.6f: the router's intent classifier asks the local Ollama to name the task when its
        # keywords are unsure. That is not the forward either, so it is logged apart too. The
        # reply names no task, so the classifier keeps its keyword result and the routing the
        # smoke asserts is unchanged; tests/integration/test_local_posts.tk covers a real answer.
        if self.path.startswith('/api/chat') and 'Classify the intent' in body:
            open(LOG+'.intent','a').write(self.path+' '+body+'\n')
            self._send({"model":"llama3","message":{"role":"assistant","content":""},"done":True}); return
        open(LOG,'a').write(self.path+' '+body+'\n')
        if DELAYS:
            with SERVEDLOCK:
                k=SERVED[0]; SERVED[0]+=1
            time.sleep(DELAYS[k%len(DELAYS)]/1000.0)
        import re
        ph=re.findall(r'\[[A-Z_]+_[0-9a-f]+_[0-9]+\]',body)
        reply=REPLY if REPLY is not None else "Summary: the user asked to contact "+(ph[0] if ph else "nobody")+"."
        if self.path.startswith('/api/chat'): self._send({"model":"llama3","message":{"role":"assistant","content":reply},"done":True,"prompt_eval_count":12,"eval_count":9})
        else: self._send({"model":"llama3","response":reply,"done":True,"prompt_eval_count":12,"eval_count":9})
http.server.ThreadingHTTPServer(('127.0.0.1',PORT),H).serve_forever()
