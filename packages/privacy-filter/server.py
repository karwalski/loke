"""OpenAI Privacy Filter sidecar — HTTP API for PII detection.

Runs on port 11435. loke calls POST /detect with {"text": "..."} and gets back
detected entities with types, confidence scores, and character spans.

Entity types: private_person, private_email, private_phone, private_address,
private_url, private_date, account_number, secret
"""

import json
import time
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from transformers import pipeline

print("Loading OpenAI Privacy Filter model...")
t0 = time.time()
classifier = pipeline(
    task="token-classification",
    model="openai/privacy-filter",
    aggregation_strategy="simple"
)
print(f"Model loaded in {time.time()-t0:.1f}s")

PLACEHOLDER_MAP = {
    "private_person": "NAME",
    "private_email": "EMAIL",
    "private_phone": "PHONE",
    "private_address": "ADDRESS",
    "private_url": "URL",
    "private_date": "DATE",
    "account_number": "ACCOUNT",
    "secret": "SECRET",
}

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == "/detect":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            text = body.get("text", "")
            
            t0 = time.time()
            results = classifier(text)
            elapsed = int((time.time() - t0) * 1000)
            
            entities = []
            counters = {}
            for r in results:
                etype = r["entity_group"]
                prefix = PLACEHOLDER_MAP.get(etype, etype.upper())
                counters[prefix] = counters.get(prefix, 0) + 1
                placeholder = f"[{prefix}_{counters[prefix]}]"
                entities.append({
                    "type": etype,
                    "value": r["word"].strip(),
                    "start": r["start"],
                    "end": r["end"],
                    "confidence": round(float(r["score"]), 4),
                    "placeholder": placeholder,
                })
            
            # Compute sensitivity
            sensitivity = "PUBLIC"
            if len(entities) > 0:
                sensitivity = "CONFIDENTIAL"
            if len(entities) > 5:
                sensitivity = "RESTRICTED"
            
            response = {
                "entities": entities,
                "count": len(entities),
                "sensitivity": sensitivity,
                "elapsed_ms": elapsed,
                "model": "openai/privacy-filter",
                "layer": "openai-privacy-filter",
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/anonymise":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            text = body.get("text", "")
            
            results = classifier(text)
            
            # Sort by start position descending to replace from end
            results.sort(key=lambda r: r["start"], reverse=True)
            anonymised = text
            counters = {}
            mappings = []
            for r in results:
                etype = r["entity_group"]
                prefix = PLACEHOLDER_MAP.get(etype, etype.upper())
                counters[prefix] = counters.get(prefix, 0) + 1
                placeholder = f"[{prefix}_{counters[prefix]}]"
                original = text[r["start"]:r["end"]]
                anonymised = anonymised[:r["start"]] + placeholder + anonymised[r["end"]:]
                mappings.append({"placeholder": placeholder, "original": original, "type": etype})
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({
                "original": text,
                "anonymised": anonymised,
                "mappings": mappings,
                "count": len(mappings),
            }).encode())
        
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "model": "openai/privacy-filter", "layer": "openai-privacy-filter"}).encode())
        
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "model": "openai/privacy-filter"}).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress request logging

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11435
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Privacy filter sidecar listening on http://127.0.0.1:{port}")
    print("Endpoints: POST /detect, POST /anonymise, GET /health")
    server.serve_forever()
