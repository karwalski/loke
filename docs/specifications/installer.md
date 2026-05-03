# Local Model Installer — Specification

**Story:** A7.1 — Production-ready Ollama and model installer
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-30

---

## 1. Overview

loke requires a local language model to function. Without one, the privacy pipeline can detect PII but cannot perform NER, intent classification, summarisation, or any LLM interaction. This specification defines a production-ready installer that ensures every loke user has a working local model within two minutes of first launch — with zero manual terminal commands.

The installer handles three things:
1. **Ollama** — the local model server
2. **A default model** — Qwen 2.5 (sized to the user's hardware)
3. **Verification** — confirm the model can generate a response

### 1.1 Design Alignment

- **The first minute should feel magical.** The user clicks "Install" and watches a progress bar. No terminal, no brew, no curl pipes.
- **The user is the authority.** The installer explains what it will install, where, and how much disk space. The user approves before anything happens.
- **Do the right thing by default.** The installer picks the right model size for the hardware. A user with 8 GB RAM gets Qwen 2.5 3B; 16 GB gets 7B; 32 GB+ gets 14B.
- **Complexity is available, not imposed.** Advanced users can skip the installer and point loke at an existing Ollama instance or a custom model.

---

## 2. Prerequisites and Detection

### 2.1 Pre-Install Checks

Before offering to install, loke checks:

| Check | Method | Result |
|-------|--------|--------|
| Ollama already installed | Probe `ollama --version` via std.process | Skip Ollama install step |
| Ollama already running | HTTP GET `http://localhost:11434/api/version` | Skip start step |
| Default model already pulled | HTTP GET `http://localhost:11434/api/tags`, check for qwen2.5 | Skip model pull step |
| Disk space | std.sys disk_free on loke data dir | Warn if < model size + 2 GB headroom |
| RAM | std.sys total_ram | Determines recommended model size |
| Architecture | std.sys is_arm64 | Determines MLX eligibility |
| Internet connectivity | HTTP GET to a known endpoint | Required for download |

### 2.2 Detection States

| State | Action |
|-------|--------|
| Ollama installed + model pulled + running | Show "Ready" — no installer needed |
| Ollama installed + model pulled + not running | Offer to start Ollama |
| Ollama installed + no model | Offer to pull recommended model |
| Ollama not installed | Offer full install (Ollama + model) |
| Ollama not installed + no internet | Show manual install instructions |

---

## 3. Ollama Installation

### 3.1 macOS

**Method:** Download the official Ollama macOS installer (DMG or zip) from `https://ollama.com/download/Ollama-darwin.zip`.

**Steps:**
1. Display consent: "loke will download Ollama (~ 90 MB) from ollama.com and install it to /usr/local/bin."
2. User clicks "Install" or presses Enter
3. Download with progress bar (HTTP GET, Content-Length for progress)
4. Extract zip to temporary directory
5. Copy `ollama` binary to `~/.loke/bin/ollama` (user-local, no sudo required)
6. Add `~/.loke/bin` to PATH via shell profile if not already present
7. Verify: run `~/.loke/bin/ollama --version`

**Fallback:** If download fails, show: "Download Ollama manually from https://ollama.com/download" with a clickable link.

**No sudo required.** The installer places the binary in the user's home directory. System-wide install is an optional advanced step.

### 3.2 Windows

**Method:** Download official Ollama Windows installer from `https://ollama.com/download/OllamaSetup.exe`.

**Steps:**
1. Display consent with download size
2. Download with progress bar
3. Launch installer via std.process (NSIS per-user install, no admin)
4. Wait for completion
5. Verify: probe `ollama --version`

### 3.3 Linux

**Method:** Official install script: `curl -fsSL https://ollama.com/install.sh | sh`

**Steps:**
1. Display consent: "loke will run the official Ollama install script"
2. Run via std.process.spawn, capture stdout for progress
3. Verify: `ollama --version`

---

## 4. Starting Ollama

After installation (or if already installed but not running):

1. Start Ollama server: `ollama serve` via std.process.spawn (background, detached)
2. Wait for health: poll `http://localhost:11434/api/version` every 500ms, timeout 15s
3. If healthy: proceed to model pull
4. If timeout: show error with troubleshooting steps

**On subsequent loke launches:** If Ollama is installed but not running, loke auto-starts it. This is configurable:
```yaml
# In loke settings
ollama:
  auto_start: true        # start ollama serve if not running
  url: "http://localhost:11434"  # custom URL for existing instances
```

---

## 5. Model Selection and Pull

### 5.1 Recommended Models

Based on hardware detection (Section 2):

| Available RAM | Recommended Model | Size on Disk | Tokens/sec (est.) | Rationale |
|---------------|-------------------|--------------|--------------------|-----------|
| 4-7 GB | qwen2.5:1.5b | ~1.0 GB | 40-60 tok/s | Fits comfortably; suitable for NER and classification |
| 8-15 GB | qwen2.5:3b | ~2.0 GB | 30-50 tok/s | Good balance of quality and speed for interactive use |
| 16-31 GB | qwen2.5:7b | ~4.5 GB | 20-40 tok/s | Strong general-purpose; handles summarisation well |
| 32-63 GB | qwen2.5:14b | ~9.0 GB | 10-25 tok/s | High quality for complex analysis and code tasks |
| 64+ GB | qwen2.5:32b | ~20 GB | 5-15 tok/s | Considered tier; excellent quality, slower response |

### 5.2 Why Qwen 2.5

- Open-weight, Apache 2.0 licence (compatible with loke)
- Strong multilingual performance (important for i18n)
- Excellent instruction-following for NER, classification, and structured output
- Available in multiple sizes matching all hardware tiers
- Well-supported by Ollama with optimised quantisations

### 5.3 Model Pull Flow

1. Display: "Downloading [model name] ([size] GB). This may take a few minutes."
2. Call `ollama pull [model]` via std.process, parse progress output
3. Show progress bar with: percentage, downloaded/total MB, estimated time remaining
4. On completion: verify model is listed in `ollama list`
5. On failure: show error, offer retry or manual instructions

### 5.4 User Override

The user can choose a different model:
- **Browser:** Dropdown showing all recommended models with size/speed trade-offs
- **CLI:** `loke init --model qwen2.5:14b` or interactive picker
- **Advanced:** Point to any Ollama-compatible model, including custom fine-tunes

---

## 6. Verification

After Ollama is running and the model is pulled:

1. Send a simple test prompt: "What is 2 + 2? Reply with just the number."
2. Verify response contains "4"
3. Measure response latency
4. Display result: "✓ Local model working — [model name] responded in [X]ms"

If verification fails:
- Retry once with a 10-second timeout
- If still failing: show error with model name, Ollama URL, and "Run `ollama run [model]` in your terminal to troubleshoot"

---

## 7. Browser Mode UI

### 7.1 Install Flow (within first-run wizard or standalone)

```
┌──────────────────────────────────────────────────────┐
│  Local Model Setup                                    │
│                                                       │
│  loke needs a local language model for privacy        │
│  filtering, intent classification, and local          │
│  inference.                                           │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │  Recommended: Qwen 2.5 7B                       │  │
│  │  Size: 4.5 GB download                          │  │
│  │  Speed: ~30 tokens/second on your hardware      │  │
│  │  Licence: Apache 2.0 (open)                     │  │
│  │                                                  │  │
│  │  Your hardware: Apple M2 Pro, 16 GB unified     │  │
│  │  Disk available: 89 GB                          │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  This will:                                           │
│    1. Download Ollama (~90 MB)                        │
│    2. Download Qwen 2.5 7B (~4.5 GB)                 │
│    3. Start the local model server                    │
│                                                       │
│  [ Change model ▾ ]                                  │
│                                                       │
│          [ Skip ]            [ Install ]              │
└──────────────────────────────────────────────────────┘
```

### 7.2 Progress Flow

```
┌──────────────────────────────────────────────────────┐
│  Installing Local Model                               │
│                                                       │
│  Step 1 of 3: Downloading Ollama                     │
│  ████████████████████████░░░░░░  78%                 │
│  71 MB / 90 MB  ·  ~4 seconds remaining              │
│                                                       │
│  Step 2 of 3: Downloading Qwen 2.5 7B               │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  waiting...           │
│                                                       │
│  Step 3 of 3: Verification                           │
│  ░░░░░░░░░░░░░░░░░░░░░░░░░░░░  waiting...           │
│                                                       │
│                              [ Cancel ]               │
└──────────────────────────────────────────────────────┘
```

### 7.3 Completion Flow

```
┌──────────────────────────────────────────────────────┐
│  ✓ Local Model Ready                                  │
│                                                       │
│  Ollama v0.5.x installed                             │
│  Qwen 2.5 7B loaded and responding                   │
│  Response time: 45ms (first token)                   │
│  Throughput: ~32 tokens/second                        │
│                                                       │
│  Your data will be processed locally before           │
│  anything leaves your device.                         │
│                                                       │
│                         [ Continue to loke → ]        │
└──────────────────────────────────────────────────────┘
```

---

## 8. Terminal Mode (CLI)

### 8.1 `loke init` Flow

```
$ loke init

  Hardware detected:
    Chip:      Apple M2 Pro (arm64)
    Memory:    16 GB unified
    Disk:      89 GB available

  Checking for Ollama... not found.

  loke needs a local model server. Install Ollama? [Y/n] y

  Downloading Ollama (90 MB)...
  ████████████████████████████████ 100%

  Starting Ollama server... ✓ running on :11434

  Recommended model: qwen2.5:7b (4.5 GB)
  Pull this model? [Y/n] y

  Pulling qwen2.5:7b...
  ████████████████░░░░░░░░░░░░░░░░ 52%  2.3 GB / 4.5 GB  ~45s remaining
  ████████████████████████████████ 100%

  Verifying... ✓ qwen2.5:7b responded in 38ms

  ✓ loke is ready. Run `loke ask "hello"` to get started.
```

### 8.2 Non-Interactive Mode

```
$ loke init --yes --model qwen2.5:3b
```

Accepts all defaults without prompting. For CI, Docker, or scripted setups.

### 8.3 Skip Model Install

```
$ loke init --skip-model
```

Configures loke without installing a model. Useful when pointing to an existing Ollama instance:
```
$ loke init --skip-model --ollama-url http://192.168.1.50:11434
```

---

## 9. Auto-Start on Subsequent Launches

After initial setup, loke manages Ollama automatically:

| Event | Action |
|-------|--------|
| loke starts, Ollama running | No action needed |
| loke starts, Ollama installed but not running | Auto-start via `ollama serve` (if `auto_start: true`) |
| loke starts, Ollama not installed | Show "Setup required" banner with link to installer |
| loke stops | Leave Ollama running (other tools may use it) |
| Ollama crashes during loke session | Auto-restart once, then show error |

---

## 10. Model Updates

loke checks for model updates periodically (default: weekly):

1. Compare installed model digest with Ollama registry
2. If newer version available: subtle notification "Qwen 2.5 7B update available (security fixes)"
3. User can update from Settings or CLI: `loke models update`
4. Update runs `ollama pull` in background
5. Old model version is kept until new one is verified

---

## 11. Uninstall

```
$ loke uninstall-model
  Remove qwen2.5:7b? [y/N] y
  Removing... ✓ freed 4.5 GB

$ loke uninstall-ollama
  Remove Ollama from ~/.loke/bin? [y/N] y
  Removing... ✓
  Note: Models in ~/.ollama were not removed.
```

---

## 12. Error Handling

| Error | Response |
|-------|----------|
| No internet | "Cannot download. Connect to the internet or install Ollama manually from ollama.com/download" |
| Download interrupted | Resume from last byte (HTTP Range header); if server doesn't support Range, restart |
| Disk full | "Not enough disk space. Need [X] GB, have [Y] GB available. Free some space or choose a smaller model." |
| Ollama won't start | "Ollama failed to start. Check if port 11434 is in use: `lsof -i :11434`" |
| Model pull fails | Retry once; then "Pull failed. Try manually: `ollama pull [model]`" |
| Verification fails | "Model loaded but not responding. Try: `ollama run [model]` in your terminal" |
| Permission denied | "Cannot write to [path]. Check permissions or run with `--install-dir ~/custom/path`" |

---

## 13. Security Considerations

- **Download verification:** Validate Ollama binary checksum against published SHA256 from ollama.com
- **No sudo:** User-local installation only. System-wide install is a separate, optional, documented step
- **No arbitrary script execution:** On macOS, download the binary directly (not `curl | sh`). The Linux path uses the official install script with clear disclosure
- **Model provenance:** Log model digest and source in audit trail
- **Network:** All downloads over HTTPS. No HTTP fallback

---

## 14. Acceptance Criteria

1. User with no Ollama can go from first launch to working local model in under 2 minutes on a broadband connection
2. User with existing Ollama is detected and skipped — no redundant install
3. User with existing Ollama but no model is offered model pull only
4. RAM-appropriate model is recommended (not oversized for hardware)
5. Progress is visible throughout (no "please wait" with no indication of progress)
6. User can cancel at any point without leaving the system in a broken state
7. CLI and browser flows are feature-equivalent
8. Works offline if Ollama is pre-installed (just pull model from local cache or skip)
9. No sudo or admin privileges required
10. Passes accessibility audit (keyboard navigable, screen reader announced, focus managed)
