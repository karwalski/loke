#!/usr/bin/env python3
"""A stand-in for Ollama that records every request it receives (scripts/smoke_e2e.sh).

Answers /api/tags and /api/ps, and answers /api/generate and /api/chat by echoing the first
loke placeholder it finds in the prompt, so the round trip through restoration can be checked.
Every POST is appended to the log file named on the command line, so the test can assert
exactly what a model would have been given.
"""
import http.server, json, sys
LOG=sys.argv[1]
class H(http.server.BaseHTTPRequestHandler):
    def _send(self,obj):
        b=json.dumps(obj).encode(); self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(b))); self.end_headers(); self.wfile.write(b)
    def log_message(self,*a): pass
    def do_GET(self):
        if self.path.startswith('/api/tags'): self._send({"models":[{"name":"llama3:latest","size":1,"digest":"x"}]})
        elif self.path.startswith('/api/ps'): self._send({"models":[]})
        else: self._send({})
    def do_POST(self):
        n=int(self.headers.get('Content-Length',0)); body=self.rfile.read(n).decode('utf-8','replace')
        open(LOG,'a').write(self.path+' '+body+'\n')
        import re
        ph=re.findall(r'\[[A-Z_]+_[0-9a-f]+_[0-9]+\]',body)
        reply="Summary: the user asked to contact "+(ph[0] if ph else "nobody")+"."
        if self.path.startswith('/api/chat'): self._send({"model":"llama3","message":{"role":"assistant","content":reply},"done":True,"prompt_eval_count":12,"eval_count":9})
        else: self._send({"model":"llama3","response":reply,"done":True,"prompt_eval_count":12,"eval_count":9})
http.server.ThreadingHTTPServer(('127.0.0.1',11434),H).serve_forever()
