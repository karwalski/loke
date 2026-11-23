"""OpenAI Privacy Filter sidecar — HTTP API for PII detection.

Runs on port 11435. loke calls POST /detect with {"text": "..."} and gets back
detected entities with types, confidence scores, and character spans.

Entity types: private_person, private_email, private_phone, private_address,
private_url, private_date, account_number, secret

Operating point (story AD1.4)
----------------------------
A detector without a tunable threshold has no operating point, so no
precision/recall curve can be reported for it. `confidence_threshold` in
models.json is applied to every span on both /detect and /anonymise, and a
per-request `threshold` overrides it so the operating point can be swept.
Because a missed entity leaks and a spurious one only costs utility, the
threshold is deliberately a floor on what is *reported*, and the number of spans
suppressed by it is returned so a caller can see what was withheld.

Model pinning (story VM1.2)
---------------------------
The model revision is read from models.json or LOKE_PF_REVISION. Left unset, the
hub resolves whatever is current, which makes any measurement taken against this
service unreproducible - so the service says so loudly at startup rather than
staying quiet about it.
"""

import json
import os
import time
import sys
import socketserver
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

_CONFIG = load_models_config()


def _primary_model():
    """The model this sidecar serves.

    Story F3b.7: LOKE_PF_MODEL names it, so one sidecar per model can serve a token
    classifier registered with `loke privacy add-model <id>`: the models.json entry with that
    id, or else a hub id or local directory loaded as given. Unset, the enabled model with the
    lowest priority number, or a default.
    """
    wanted = os.environ.get("LOKE_PF_MODEL")
    if wanted:
        for m in _CONFIG.get("models", []):
            if m.get("id") == wanted:
                return m
        return {"id": wanted, "model_path": wanted}
    enabled = [m for m in _CONFIG.get("models", []) if m.get("enabled")]
    enabled.sort(key=lambda m: m.get("priority", 99))
    return enabled[0] if enabled else {}


_PRIMARY = _primary_model()
MODEL_PATH = _PRIMARY.get("model_path", "openai/privacy-filter")
# Story F3b.7: what /health names, and what loke checks before it sends this sidecar any
# text for a registered model.
MODEL_ID = _PRIMARY.get("id", "openai-privacy-filter")
TASK = "token-classification"

# transformers' pipeline loads PyTorch and SafeTensors weights; it does not load an ONNX
# file, and this sidecar has no ONNX runtime. Say so rather than fail obscurely (F3b.7).
if str(MODEL_PATH).lower().endswith(".onnx"):
    print(f"ERROR: {MODEL_PATH} is an ONNX model; this sidecar loads only transformers "
          "token-classification models (PyTorch or SafeTensors weights).", file=sys.stderr)
    sys.exit(2)

# Story VM1.2: pin the revision so a measurement can be reproduced.
MODEL_REVISION = os.environ.get("LOKE_PF_REVISION") or _PRIMARY.get("model_revision") or None

# Story AD1.4: the operating point. Applied on every path, overridable per
# request so a precision/recall curve can actually be swept.
DEFAULT_THRESHOLD = float(
    os.environ.get("LOKE_PF_THRESHOLD", _PRIMARY.get("confidence_threshold", 0.0))
)

print(f"Loading {MODEL_PATH} (revision: {MODEL_REVISION or 'UNPINNED'})...")
t0 = time.time()
_pipeline_kwargs = {
    "task": "token-classification",
    "model": MODEL_PATH,
    "aggregation_strategy": "simple",
}
if MODEL_REVISION:
    _pipeline_kwargs["revision"] = MODEL_REVISION
classifier = pipeline(**_pipeline_kwargs)
print(f"Model loaded in {time.time()-t0:.1f}s")
print(f"Confidence threshold: {DEFAULT_THRESHOLD}")
if not MODEL_REVISION:
    print(
        "WARNING: model revision is not pinned. The hub resolves whatever is "
        "current, so results from this service are NOT reproducible. Set "
        "model_revision in models.json or LOKE_PF_REVISION before recording any "
        "measurement (story VM1.2).",
        file=sys.stderr,
    )
if DEFAULT_THRESHOLD > 0.0:
    print(
        f"WARNING: confidence threshold is {DEFAULT_THRESHOLD}, so spans scoring "
        "below it are NOT reported. For a privacy filter that increases leakage: "
        "a missed entity leaks, whereas a spurious one only costs utility. This "
        "value should be justified against a measured recall floor (story AD1.2) "
        "rather than assumed. The safe default is 0.",
        file=sys.stderr,
    )


def _request_threshold(body):
    """Per-request operating point, falling back to the configured default."""
    raw = body.get("threshold")
    if raw is None:
        return DEFAULT_THRESHOLD
    try:
        val = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_THRESHOLD
    return min(max(val, 0.0), 1.0)


def _apply_threshold(results, threshold):
    """Split spans into those reported and those suppressed by the threshold.

    Returns (kept, suppressed_count). The count is reported so a caller can see
    that something was withheld rather than inferring silence means nothing was
    found - a false negative is the dangerous error here.
    """
    if threshold <= 0.0:
        return list(results), 0
    kept = [r for r in results if float(r.get("score", 0.0)) >= threshold]
    return kept, len(results) - len(kept)

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
            
            threshold = _request_threshold(body)

            t0 = time.time()
            raw_results = classifier(text)
            elapsed = int((time.time() - t0) * 1000)
            results, suppressed = _apply_threshold(raw_results, threshold)

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
                "model": MODEL_PATH,
                "model_revision": MODEL_REVISION,
                "layer": MODEL_ID,
                "threshold": threshold,
                "suppressed_below_threshold": suppressed,
            }
            
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())
        
        elif self.path == "/anonymise":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            text = body.get("text", "")
            
            threshold = _request_threshold(body)
            results, suppressed = _apply_threshold(classifier(text), threshold)

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
                "threshold": threshold,
                "suppressed_below_threshold": suppressed,
                "model": MODEL_PATH,
                "model_revision": MODEL_REVISION,
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
            self.wfile.write(json.dumps({"ok": True, "model": MODEL_PATH, "model_id": MODEL_ID, "task": TASK, "layer": MODEL_ID}).encode())

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
            self.wfile.write(json.dumps({"ok": True, "model": MODEL_PATH, "model_id": MODEL_ID, "task": TASK}).encode())
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

class Server(HTTPServer):
    """HTTPServer without the reverse-DNS lookup in server_bind (story X8.13).

    HTTPServer.server_bind calls socket.getfqdn(host) only to fill in server_name. On the
    GitHub macOS runner that lookup of 127.0.0.1 took 35 s (measured in CI for
    scripts/lib/http_recorder.py, which had the same server), and the sidecar would not
    listen until it returned: loke fails closed meanwhile, but reports this layer down.
    server_name is the bound host string instead; nothing here reads it."""

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 11435
    server = Server(("127.0.0.1", port), Handler)
    print(f"Privacy filter sidecar listening on http://127.0.0.1:{server.server_port}", flush=True)
    print("Endpoints: POST /detect, POST /anonymise, POST /models/add, GET /models, GET /health, DELETE /models/{id}")
    server.serve_forever()
