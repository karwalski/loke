"""OpenAI Privacy Filter sidecar — HTTP API for PII detection.

Runs on port 11435. loke calls POST /detect with {"text": "..."} and gets back
detected entities with types, confidence scores, and character spans.

Entity types: private_person, private_email, private_phone, private_address,
private_url, private_date, account_number, secret
"""

import json
import os
import time
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from transformers import pipeline

MODELS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models.json")

def load_models_config():
    """Load the model registry from models.json."""
    if os.path.exists(MODELS_FILE):
        with open(MODELS_FILE, "r") as f:
            return json.load(f)
    return {"models": []}

def save_models_config(config):
    """Save the model registry to models.json."""
    with open(MODELS_FILE, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")

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
        
        elif self.path == "/models/add":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}

            model_id = body.get("id", "")
            model_path = body.get("model_path", "")
            entity_mapping = body.get("entity_mapping", {})

            if not model_id or not model_path:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "id and model_path are required"}).encode())
                return

            config = load_models_config()

            # Check for duplicate id
            for m in config["models"]:
                if m["id"] == model_id:
                    self.send_response(409)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Model '{model_id}' already registered"}).encode())
                    return

            new_model = {
                "id": model_id,
                "name": body.get("name", model_id),
                "model_path": model_path,
                "type": body.get("type", "token-classification"),
                "entity_mapping": entity_mapping,
                "confidence_threshold": body.get("confidence_threshold", 0.7),
                "priority": body.get("priority", len(config["models"]) + 1),
                "enabled": body.get("enabled", True),
                "installed": False,
            }

            config["models"].append(new_model)
            save_models_config(config)

            self.send_response(201)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "model": new_model}).encode())

        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "model": "openai/privacy-filter", "layer": "openai-privacy-filter"}).encode())

        else:
            self.send_response(404)
            self.end_headers()
    
    def do_DELETE(self):
        if self.path.startswith("/models/"):
            model_id = self.path[len("/models/"):]
            config = load_models_config()

            original_count = len(config["models"])
            config["models"] = [m for m in config["models"] if m["id"] != model_id]

            if len(config["models"]) == original_count:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Model '{model_id}' not found"}).encode())
                return

            save_models_config(config)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "deleted": model_id}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_GET(self):
        if self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "model": "openai/privacy-filter"}).encode())
        elif self.path == "/models":
            config = load_models_config()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(config).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress request logging

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11435
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"Privacy filter sidecar listening on http://127.0.0.1:{port}")
    print("Endpoints: POST /detect, POST /anonymise, POST /models/add, GET /models, GET /health, DELETE /models/{id}")
    server.serve_forever()
