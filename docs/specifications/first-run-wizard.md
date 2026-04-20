# First-Run Setup Wizard — Specification

**Story:** A4.1 — First-run setup wizard
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

The first-run wizard guides new users from installation to a working loke configuration in under two minutes. It detects hardware capabilities, sets up local model inference, optionally configures cloud LLM providers, applies a privacy preset appropriate to the user's region, and finishes with a live demonstration of the anonymisation pipeline.

The wizard runs once — on the first launch of loke in either browser or terminal mode. It produces a complete, valid configuration that allows the user to begin working immediately. Users who prefer to skip the wizard and configure manually can do so; users who want to revisit it later can re-run it at any time.

### 1.1 Design Alignment

This specification follows the loke design principles:

- **The first minute should feel magical, not bureaucratic.** The wizard is fast, opinionated, and gets out of the way. Every step has a sensible default that can be accepted with a single keypress or click.
- **Do the right thing by default.** Hardware detection and region inference select the best local model and the most appropriate privacy preset without requiring the user to understand the options.
- **The user is the authority.** Every default is visible and overridable. Nothing is hidden behind "we chose this for you" without explanation.
- **Complexity is available, not imposed.** The wizard shows the simple path by default. Advanced options (custom privacy rules, manual model selection, non-interactive CI flags) are accessible but not in the way.
- **Privacy is the foundation.** The wizard defaults to local-only operation. Cloud providers are optional. The privacy preset defaults to the most restrictive applicable regulation.

### 1.2 Scope

This specification covers:

- Hardware detection and capability assessment
- Local model setup (Ollama, MLX, @electron/llm)
- Cloud provider configuration and API key storage
- Privacy preset selection
- Guided test interaction
- Browser mode wizard flow (step-by-step UI)
- Terminal mode wizard flow (`loke init`)
- Post-wizard configuration state
- Hardware capability tiers
- Error handling
- Accessibility requirements

---

## 2. Hardware Detection

On wizard start, loke performs a non-blocking hardware inventory. The results determine which local models are recommended, whether GPU/NPU acceleration is available, and what capability tier the device falls into (see [Section 9](#9-hardware-capability-tiers)).

### 2.1 Detected Properties

| Property | Detection method | Platform notes |
|----------|-----------------|----------------|
| **Total RAM** | `os.totalmem()` (Node.js) | Unified memory on Apple Silicon is shared between CPU and GPU |
| **Available RAM** | `os.freemem()` at wizard start | Used to warn if current memory pressure is high |
| **CPU architecture** | `os.arch()` + `os.cpus()` | Distinguishes `arm64` (Apple Silicon, Snapdragon) from `x64` (Intel/AMD) |
| **Apple Silicon generation** | `sysctl hw.optional` flags (macOS) | Determines MLX eligibility and Neural Engine capability |
| **GPU** | `electron.app.getGPUInfo('complete')` (browser mode), `system_profiler SPDisplaysDataType` (macOS), `nvidia-smi` / `rocm-smi` (Linux) | Discrete GPU with sufficient VRAM enables larger models |
| **NPU / Neural Engine** | `sysctl hw.optional.neural_engine` (macOS), DirectML device enumeration (Windows) | Used for accelerated NER and small model inference |
| **Disk space available** | `fs.statfs()` on the loke data directory | Models require 2-20 GB; warn if insufficient |
| **OS version** | `os.release()` + `os.platform()` | Minimum versions: macOS 13+, Windows 10 21H2+, Ubuntu 22.04+ |
| **Ollama installed** | Probe `ollama --version` and `http://localhost:11434/api/version` | Detects existing installation and running instance |

### 2.2 Detection Behaviour

- Detection runs in parallel across all probes. The wizard UI shows a brief "Checking your hardware..." animation (browser) or spinner (terminal) while detection completes.
- Target completion time: < 3 seconds on all platforms.
- If any individual probe fails, the wizard continues with that property marked as `unknown`. No probe failure is fatal.
- Results are cached in the loke configuration directory and refreshed on each wizard run or when `loke doctor` is invoked.

### 2.3 Hardware Report

The wizard presents a summary to the user before proceeding:

**Browser mode example:**

```
Your Hardware
  Chip       Apple M2 Pro (arm64)
  Memory     16 GB unified
  Disk       89 GB available
  GPU        Integrated (Apple M2 Pro, 19-core)
  NPU        Apple Neural Engine (16-core)
  OS         macOS 15.3
  Ollama     Not installed

  Capability tier: Standard — most local models will run well.
```

**Terminal mode example:**

```
Hardware detected:
  CPU:     Apple M2 Pro (arm64)
  RAM:     16 GB
  Disk:    89 GB free
  GPU:     Apple M2 Pro 19-core (integrated)
  NPU:    Neural Engine 16-core
  OS:      macOS 15.3
  Ollama:  not found

Tier: Standard (16 GB) — recommended models will run comfortably.
```

---

## 3. Local Model Setup

Local models are the foundation of loke's privacy guarantee — they enable PII detection, intent classification, summarisation, and simple completions without any data leaving the device. The wizard prioritises getting at least one working local model running.

### 3.1 Ollama Detection and Installation

**Step 1: Check for existing Ollama installation.**

- Probe `ollama --version` (PATH lookup) and `http://localhost:11434/api/version` (running instance).
- If Ollama is installed and running, skip to model selection (3.2).
- If Ollama is installed but not running, offer to start it.
- If Ollama is not installed, offer to install it.

**Step 2: Ollama installation (if needed).**

| Platform | Installation method |
|----------|-------------------|
| macOS | Download from `https://ollama.com/download/Ollama-darwin.zip`, extract to `/Applications`, launch |
| Windows | Download from `https://ollama.com/download/OllamaSetup.exe`, run installer |
| Linux | `curl -fsSL https://ollama.com/install.sh \| sh` (with user confirmation) |

- The wizard downloads in the background and shows progress.
- The user can skip Ollama installation entirely. loke functions without local models if at least one cloud provider is configured (see Section 4). If no local model and no cloud provider are configured, the wizard warns but still allows completion.
- Installation requires internet access. See [Section 10.1](#101-no-internet-connection) for offline handling.

**Step 3: Verify installation.**

- After installation, verify Ollama is responsive via the health endpoint.
- If verification fails after 30 seconds, show error and offer to retry or skip.

### 3.2 Model Selection

Based on the hardware capability tier (Section 9), the wizard recommends a set of models and pre-selects the best fit.

**Recommended model matrix:**

| Tier | RAM | Primary model | NER/classification model | Disk required |
|------|-----|--------------|-------------------------|---------------|
| Lite | 8 GB | `qwen2.5:3b` (2.0 GB) | `qwen2.5:0.5b` (0.4 GB) | ~3 GB |
| Standard | 16 GB | `qwen2.5:7b` (4.7 GB) | `qwen2.5:1.5b` (1.0 GB) | ~7 GB |
| Performance | 32 GB+ | `qwen2.5:14b` (9.0 GB) | `qwen2.5:3b` (2.0 GB) | ~12 GB |
| Performance (NVIDIA) | 32 GB+ with 12 GB+ VRAM | `qwen2.5:14b` (CUDA) | `qwen2.5:3b` (CUDA) | ~12 GB |

- The wizard pre-selects the tier matching the detected hardware.
- Users can override the selection — a dropdown (browser) or numbered list (terminal) shows all available options with size and expected performance notes.
- Model pulls run in the background with progress indication. The wizard can proceed to the next step while models download.

### 3.3 MLX on Apple Silicon

When Apple Silicon is detected (`arm64` on macOS), the wizard additionally offers MLX-accelerated models:

- MLX models are 8-9% faster than llama.cpp equivalents on Apple hardware (per F2.3 benchmarks).
- The wizard explains the benefit in one line: "MLX uses your Mac's unified memory more efficiently. Same models, ~9% faster."
- If the user opts in, loke downloads MLX-format model weights instead of (or in addition to) GGUF weights.
- MLX is offered alongside Ollama, not as a replacement. Ollama remains the primary backend; MLX is used when it provides a measurable advantage for a given task.

### 3.4 @electron/llm (Browser Mode Only)

In browser mode, the wizard checks whether `@electron/llm` is available for in-process inference:

- If supported by the Electron version and hardware, the wizard notes this as an option for lightweight tasks (intent classification, NER).
- No additional download is required — models are bundled or shared with Ollama.
- This is presented as an "Advanced" option, not shown by default.

### 3.5 Model Download Progress

- Browser mode: progress bar with estimated time remaining, model name, and size.
- Terminal mode: progress bar using ANSI escape codes, percentage, and transfer speed.
- The wizard allows the user to proceed to subsequent steps while the download continues. A notification appears when the download completes.
- If the download is interrupted, it resumes on next wizard run or next `loke` launch.

---

## 4. Cloud Provider Configuration

Cloud providers are optional. loke is fully functional with local models only. The wizard makes this explicit: "loke works entirely on your device. Cloud providers are optional — add them if you want access to larger models."

### 4.1 Supported Providers

| Provider | API key format | Validation endpoint |
|----------|---------------|-------------------|
| OpenAI | `sk-...` | `GET /v1/models` |
| Anthropic | `sk-ant-...` | `GET /v1/models` |
| Google (Gemini) | `AI...` | `GET /v1beta/models` |
| Mistral | Alphanumeric | `GET /v1/models` |
| OpenRouter | `sk-or-...` | `GET /api/v1/models` |
| Ollama (remote) | None (or custom) | `GET /api/version` |

### 4.2 API Key Entry Flow

1. The wizard presents the list of supported providers with a brief description of each (model strengths, pricing tier).
2. The user selects one or more providers to configure, or skips this step entirely.
3. For each selected provider, the user enters their API key.
4. The wizard validates the key by making a lightweight read-only API call (model listing, not a completion).
5. On success, the key is stored in the OS keychain (see 4.3). On failure, the wizard shows the error and offers to retry or skip.

**Browser mode:** API key input fields use `type="password"` with a show/hide toggle. A "Test" button validates without leaving the step.

**Terminal mode:** API key input uses a masked prompt (characters shown as `*`). Validation runs automatically after entry.

### 4.3 OS Keychain Storage

API keys are stored in the operating system's native credential store, never in plaintext configuration files:

| Platform | Credential store | Implementation |
|----------|-----------------|----------------|
| macOS | Keychain (`security` CLI or `keytar`) | Service: `dev.loke`, Account: `provider-{name}` |
| Windows | Credential Manager (via `keytar`) | Target: `dev.loke/provider-{name}` |
| Linux | `libsecret` (GNOME Keyring / KWallet) | Schema: `dev.loke`, attribute: `provider={name}` |

- If no keychain is available (headless Linux without a secret service), the wizard warns the user and offers encrypted-file fallback (SQLCipher-protected local store). This is clearly marked as less secure than OS keychain.
- Keys are never written to log files, configuration files, environment variables, or console output.

### 4.4 Provider Priority

If multiple providers are configured, the wizard asks the user to set a preference order. This feeds into the router's provider selection (F5.3):

- Default order: Local (Ollama/MLX) > cheapest cloud > most capable cloud.
- The user can drag-and-drop (browser) or number (terminal) to reorder.
- This is stored in user-level configuration and can be changed later.

---

## 5. Privacy Preset Selection

The privacy preset determines which PII entity types loke detects, how aggressively it anonymises, what data retention rules apply, and which cross-border transfer restrictions are enforced. Presets are fully defined in the [Regulatory Defaults specification](regulatory-defaults.md).

### 5.1 Region Detection

The wizard infers the user's likely region from:

1. **OS locale** (`Intl.DateTimeFormat().resolvedOptions().locale` or `os.locale()`)
2. **OS timezone** (`Intl.DateTimeFormat().resolvedOptions().timeZone`)
3. **Keyboard layout** (supplementary signal)

This inference is used to pre-select a privacy preset. The user always sees the selection and can change it.

**Mapping logic:**

| Detected region | Pre-selected preset | Rationale |
|----------------|-------------------|-----------|
| EU/EEA member state | EU GDPR | Direct applicability |
| United Kingdom | UK GDPR | Post-Brexit UK variant |
| Australia | AU Privacy Act | Australian Privacy Principles |
| United States (California) | US CCPA/CPRA | State-level, most restrictive US general regulation |
| United States (other) | US CCPA/CPRA | CCPA as conservative US default; HIPAA shown as option if healthcare context detected |
| Singapore | SG PDPA | Personal Data Protection Act |
| Other / unknown | EU GDPR | Most restrictive general-purpose baseline |

### 5.2 Preset Presentation

Each preset is presented with a plain-language explanation, not legal jargon:

**Example (EU GDPR):**

> **European Union (GDPR)**
> The strictest general privacy standard. loke will detect and anonymise a broad range of personal information — names, emails, addresses, financial data, health information, and more. Data stays on your device unless you explicitly choose to send it to a cloud provider, and even then it's anonymised first. Audit logs are kept for 5 years.

**Example (Minimal):**

> **Minimal**
> Basic protection only — emails and phone numbers are detected. No cross-border restrictions, no audit logging, no retention limits. Suitable for non-sensitive personal use where convenience is the priority. Not recommended for professional use.

### 5.3 Custom Preset

A "Customise" option allows the user to start from any preset and modify individual settings:

- Toggle entity categories on/off (e.g. "Detect financial data: Yes/No")
- Set anonymisation strength (full anonymisation, pseudonymisation, placeholder only)
- Set retention period
- Configure cross-border transfer rules

In the wizard, customisation is limited to the most common settings. Full policy editing is available post-wizard via the policy file (A3.1).

### 5.4 Multiple Regulations

If the user operates under multiple regulatory regimes (e.g. an Australian company with EU clients), the wizard offers to apply multiple presets. Conflict resolution follows the strategy defined in the Regulatory Defaults specification: the most restrictive setting from any applicable regulation wins.

---

## 6. Test Interaction

The wizard concludes with a guided demonstration that shows loke's pipeline working end-to-end. This is the "magical first minute" — the moment the user sees the value of loke.

### 6.1 Demo Prompt

The wizard provides a pre-written prompt containing synthetic PII:

```
Summarise this customer note:

Sarah Chen (sarah.chen@meridian.com.au, 0412 345 678) called about
her account #MC-20948. She's based in 42 Wallaby Way, Sydney NSW 2000.
Her tax file number is 123 456 789. She wants to switch from the
Premium plan ($149/month) to the Business plan and asked whether her
team (David Okonkwo, Priya Sharma, and James McTavish) can be added
to the new plan.
```

The user can edit the prompt or use their own text. The demo prompt is designed to include a variety of PII types (names, email, phone, address, TFN, account number) to showcase multi-layer detection.

### 6.2 Pipeline Visualisation

As the prompt is processed, the wizard shows each pipeline stage:

**Stage 1 — PII Detection**

```
Found 9 entities:
  Sarah Chen               → person name      (NER)
  sarah.chen@meridian.com.au → email address   (regex)
  0412 345 678             → phone number      (regex)
  MC-20948                 → account number    (regex)
  42 Wallaby Way, Sydney NSW 2000 → address    (NER)
  123 456 789              → tax file number   (regex)
  David Okonkwo            → person name       (NER)
  Priya Sharma             → person name       (NER)
  James McTavish           → person name       (NER)
```

**Stage 2 — Anonymisation**

The wizard shows the anonymised version of the prompt, with placeholders highlighted:

```
Summarise this customer note:

$person_1 ($email_1, $phone_1) called about her account $account_1.
She's based in $address_1. Her tax file number is $tfn_1. She wants
to switch from the Premium plan ($149/month) to the Business plan and
asked whether her team ($person_2, $person_3, and $person_4) can be
added to the new plan.
```

**Stage 3 — Routing**

```
Route: Local model (qwen2.5:7b via Ollama)
Reason: Sensitivity RESTRICTED (TFN detected), local-first policy active
Cost: $0.00
```

**Stage 4 — Response**

The LLM response is shown with placeholders, then the restored version with original PII reinserted, with the restored entities highlighted to show the reversal worked.

### 6.3 Feedback Prompt

After the test interaction, the wizard asks:

> "Did loke detect the right information? [Thumbs up / Thumbs down]"

This is the user's first encounter with the feedback system (Design Principle 3). A thumbs down opens the lightweight comment box.

### 6.4 Offline Test

If no model is available yet (still downloading, or user skipped all model setup), the wizard runs the detection and anonymisation stages only (no LLM completion) and explains: "We'll show the full pipeline once a model is ready. Here's what loke found in your prompt."

---

## 7. Browser Mode Wizard Flow

The browser mode wizard is a multi-step UI rendered in the Electron window. It replaces the main workspace on first launch.

### 7.1 Step Sequence

| Step | Title | Content | Can skip? | Can go back? |
|------|-------|---------|-----------|-------------|
| 1 | Welcome | Brief introduction, estimated time ("~2 minutes"), privacy promise | No (entry point) | No |
| 2 | Hardware | Auto-detected hardware summary, capability tier | No (auto-advances after detection) | No |
| 3 | Local Models | Ollama status, recommended model, install/pull actions | Yes | Yes |
| 4 | Cloud Providers | Provider list, API key entry, validation | Yes | Yes |
| 5 | Privacy | Region-based preset, plain-language summary, customise option | No (must select, but default is pre-selected) | Yes |
| 6 | Test Drive | Demo prompt, pipeline visualisation, feedback | Yes | Yes |
| 7 | Done | Summary of configuration, links to settings, "Start using loke" button | No (exit point) | Yes |

### 7.2 UI Components

- **Progress indicator:** Horizontal stepper at the top showing all steps, current step highlighted. Steps are labelled with short titles.
- **Navigation:** "Back" and "Next" buttons at the bottom. "Skip" link (where applicable) is a text link, not a button, to de-emphasise it.
- **Async operations:** Model downloads and API key validation run without blocking navigation. A non-modal toast notification reports completion or failure.
- **Animations:** Subtle transitions between steps. The pipeline visualisation in the test step uses staged reveal (each stage appears in sequence) to build comprehension.

### 7.3 Responsive Layout

- The wizard is designed for the Electron window's default size (1280x800).
- Content is centred with a maximum width of 640px for readability.
- All steps are scrollable if content exceeds viewport height.

---

## 8. Terminal Mode Wizard Flow

The terminal mode wizard runs as `loke init`. It uses interactive prompts for manual setup and supports non-interactive flags for CI/automation.

### 8.1 Interactive Mode

`loke init` runs the wizard as a series of prompts using a library such as `@inquirer/prompts` or `@clack/prompts`:

```
$ loke init

  loke — first-run setup
  ───────────────────────

  Checking hardware...

  ✓ Hardware detected
    CPU:     Apple M2 Pro (arm64)
    RAM:     16 GB
    Disk:    89 GB free
    Ollama:  not found
    Tier:    Standard

  ? Install Ollama? (Y/n) Y
    Downloading Ollama... done
    Starting Ollama... done

  ? Pull recommended model qwen2.5:7b (4.7 GB)? (Y/n) Y
    Pulling qwen2.5:7b... ████████████████████ 100% (4.7 GB)

  ? Configure a cloud LLM provider? (y/N) n
    Skipped — loke will use local models only.

  ? Privacy preset: (Use arrow keys)
  ❯ Australian Privacy Act (detected: en-AU)
    EU GDPR
    US CCPA/CPRA
    UK GDPR
    Minimal
    Custom...

  Selected: Australian Privacy Act

  ? Run a test interaction? (Y/n) Y

    ── Pipeline Demo ──────────────────────
    Input:  "Sarah Chen (sarah.chen@meridian.com.au)..."
    Found:  9 PII entities
    Sent:   "$person_1 ($email_1, $phone_1)..."
    Route:  qwen2.5:7b (local, $0.00)
    Result: Response with PII restored ✓
    ────────────────────────────────────────

  ✓ Setup complete

  Config written to: ~/.config/loke/config.yaml
  Privacy preset:    au-privacy-act
  Local model:       qwen2.5:7b (Ollama)
  Cloud providers:   none

  Run `loke ask "hello"` to get started.
  Run `loke init --reconfigure` to change these settings.
```

### 8.2 Non-Interactive Mode

For CI, Docker, and automation, `loke init` accepts flags that bypass all prompts:

```bash
loke init \
  --non-interactive \
  --preset au-privacy-act \
  --skip-ollama \
  --provider openai \
  --provider-key-env OPENAI_API_KEY \
  --skip-test
```

**Flags:**

| Flag | Default | Description |
|------|---------|-------------|
| `--non-interactive` | `false` | Skip all prompts; use defaults and provided flags |
| `--preset <id>` | Auto-detected | Privacy preset identifier (`eu-gdpr`, `au-privacy-act`, etc.) |
| `--skip-ollama` | `false` | Do not install or configure Ollama |
| `--skip-models` | `false` | Do not pull any models |
| `--model <name>` | Tier-based default | Specific model to pull |
| `--provider <name>` | None | Cloud provider to configure (repeatable) |
| `--provider-key-env <VAR>` | None | Environment variable containing the API key |
| `--skip-test` | `false` | Skip the test interaction |
| `--reconfigure` | `false` | Re-run wizard even if configuration already exists |
| `--json` | `false` | Output results as JSON (for scripting) |

In non-interactive mode, if a required decision cannot be resolved from flags or defaults, the command exits with a non-zero status and a descriptive error message.

### 8.3 Re-Running the Wizard

- `loke init` with an existing configuration prompts: "loke is already configured. Re-run setup? This will not delete your existing API keys or conversation history."
- `loke init --reconfigure` skips the prompt and enters the wizard directly.
- Existing API keys in the keychain are preserved unless the user explicitly reconfigures a provider.

---

## 9. Hardware Capability Tiers

Tiers determine default model recommendations and set user expectations about local model performance.

### 9.1 Tier Definitions

| Tier | RAM | GPU/NPU | What works | What doesn't |
|------|-----|---------|-----------|-------------|
| **Lite** | 8 GB | Any | 0.5b-3b models, regex + NER privacy detection, basic intent classification, simple completions | 7b+ models (too slow or OOM), SLM-based NER (marginal), long-context tasks |
| **Standard** | 16 GB | Any | 3b-7b models comfortably, SLM NER, summarisation, code completion, full privacy pipeline | 14b+ models (marginal), large-context windows (>8K tokens under load) |
| **Performance** | 32 GB+ | Any | 7b-14b models, long-context, multiple concurrent tasks, Presidio sidecar | 30b+ models (marginal without quantisation) |
| **Performance (GPU)** | 32 GB+ | NVIDIA 12 GB+ VRAM or Apple Silicon | Same as Performance but with GPU-accelerated inference | 30b+ at full precision |

### 9.2 Tier Assignment Logic

```
if total_ram >= 32 GB:
    if discrete_gpu with vram >= 12 GB OR apple_silicon:
        tier = "Performance (GPU)"
    else:
        tier = "Performance"
elif total_ram >= 16 GB:
    tier = "Standard"
else:
    tier = "Lite"
```

### 9.3 Tier Presentation

The wizard presents the tier with practical implications, not just a label:

- **Lite:** "Your device can run small language models for privacy filtering and basic tasks. For complex tasks, a cloud provider is recommended."
- **Standard:** "Your device can run most local models comfortably. Cloud providers are optional but useful for the most demanding tasks."
- **Performance:** "Your device can run large local models. You may not need cloud providers at all."

### 9.4 Below Minimum

If total RAM is less than 4 GB or the OS version is below the minimum, the wizard warns:

> "Your hardware may not support local model inference. loke's privacy filtering will use regex and rule-based detection only. For LLM completions, configure a cloud provider."

The wizard does not block — loke can still function as a privacy proxy for cloud-only operation.

---

## 10. Error Handling

### 10.1 No Internet Connection

- **Ollama install:** The wizard detects the lack of connectivity when the download fails. It shows: "No internet connection detected. You can install Ollama later — run `loke init --reconfigure` when you're online." The wizard skips the model setup steps.
- **Model pull:** Same handling as Ollama install. If Ollama is already installed, the wizard notes that models can be pulled later.
- **API key validation:** The wizard stores the key and marks it as "not yet validated". Validation runs automatically on next launch.
- **Region detection fallback:** Without network-based geolocation (which loke does not use — privacy), region detection relies entirely on OS locale. This works offline.

### 10.2 Ollama Installation Failure

- The wizard shows the error message from the installation process.
- It offers three options: retry, skip (configure cloud providers instead), or open a browser to Ollama's troubleshooting page.
- The failure is logged but does not prevent wizard completion.

### 10.3 Model Pull Failure

- Common causes: insufficient disk space, network timeout, corrupted download.
- The wizard shows the cause if determinable and suggests remediation ("Free up 3 GB of disk space", "Check your network connection").
- Partial downloads are preserved for resumption.

### 10.4 Unsupported Hardware

- If the OS is below minimum version, the wizard warns and allows the user to proceed at their own risk.
- If the architecture is unrecognised, hardware detection marks all hardware-dependent fields as `unknown` and defaults to the Lite tier.
- If no GPU is detected, GPU-related options are hidden rather than shown and disabled.

### 10.5 No API Keys and No Local Models

If the user skips both local model setup and cloud provider configuration:

> "loke needs at least one way to process prompts — either a local model or a cloud provider. You can continue without either, but loke won't be able to generate responses until you configure one. Privacy detection and anonymisation will still work."

The wizard allows completion. The user can add models or providers later.

### 10.6 API Key Validation Failure

- Invalid key format: rejected client-side with a format hint ("OpenAI keys start with `sk-`").
- Authentication failure (401/403): "This key was rejected by the provider. Check that it's correct and has not been revoked."
- Network error: "Could not reach the provider. The key has been saved and will be validated when connectivity is restored."
- Rate limit (429): "The provider rate-limited the validation request. The key has been saved and will be validated on next use."

---

## 11. Post-Wizard State

### 11.1 Configuration Files Created

The wizard produces the following artefacts:

| Artefact | Location | Contents |
|----------|----------|----------|
| **User config** | `~/.config/loke/config.yaml` (Linux/macOS) or `%APPDATA%\loke\config.yaml` (Windows) | Selected privacy preset, provider priority, model preferences, capability tier |
| **Hardware profile** | `~/.config/loke/hardware.json` | Cached hardware detection results, tier assignment, detection timestamp |
| **API keys** | OS keychain (see Section 4.3) | Provider API keys — not in any file |
| **Wizard state** | `~/.config/loke/wizard-state.json` | Completion status, version of wizard that ran, timestamp |
| **Audit entry** | loke audit log (F6.2) | Record of wizard completion with selected options (no API keys logged) |

### 11.2 Config File Structure

The generated `config.yaml` follows the hierarchical configuration schema (F1.5):

```yaml
# Generated by loke first-run wizard
# Version: 0.1.0
# Timestamp: 2026-04-05T10:30:00Z

privacy:
  preset: "au-privacy-act"
  # Custom overrides go here

models:
  local:
    backend: "ollama"             # ollama | mlx | electron-llm
    primary: "qwen2.5:7b"
    ner: "qwen2.5:1.5b"
  preference_order:
    - "local"
    - "cloud"

providers:
  # Cloud providers configured via OS keychain
  # Provider names listed here; keys stored securely
  configured: []

hardware:
  tier: "standard"
  ram_gb: 16
  architecture: "arm64"
  apple_silicon: true
  mlx_available: true
```

### 11.3 Re-Running the Wizard

| Method | Effect |
|--------|--------|
| `loke init` (first run) | Full wizard |
| `loke init` (subsequent) | Prompts to re-run; preserves existing keys |
| `loke init --reconfigure` | Full wizard, preserves existing keys |
| Browser: Settings > Setup Wizard | Opens wizard in a tab, same as `--reconfigure` |
| `loke doctor` | Runs hardware detection and validates configuration without changing anything |

### 11.4 Wizard Versioning

The wizard state file records which version of the wizard was run. If a future loke update introduces new wizard steps (e.g. a new provider, a new privacy regulation), the application may prompt the user to run the updated wizard for the new sections only, without repeating completed steps.

---

## 12. Accessibility Requirements

The wizard must be usable by all users, including those relying on assistive technology.

### 12.1 Keyboard Navigation

- Every interactive element is reachable via Tab / Shift+Tab.
- Step navigation supports keyboard shortcuts: Enter (next/confirm), Escape (back/cancel), number keys (1-7) for direct step navigation.
- Focus is managed explicitly: when a step transitions, focus moves to the first interactive element of the new step.
- No keyboard traps — the user can always navigate away from any element.

### 12.2 Screen Reader Support

- All steps use semantic HTML: `<h1>` for step title, `<h2>` for subsections, `<form>` for input groups.
- Progress indicator uses `aria-current="step"` and `aria-label` for each step.
- Status messages (download progress, validation results) use `aria-live="polite"` regions.
- The pipeline visualisation in the test step has a text-based alternative that reads linearly: "Stage 1: 9 PII entities detected. Stage 2: prompt anonymised. Stage 3: routed to local model. Stage 4: response restored."
- Password fields (API keys) are labelled with the provider name and include `aria-describedby` pointing to format hints.

### 12.3 Visual Accessibility

- All text meets WCAG 2.1 AA contrast ratio (4.5:1 for body text, 3:1 for large text).
- The wizard respects the OS high-contrast / reduced-motion preferences (`prefers-contrast: more`, `prefers-reduced-motion: reduce`).
- When reduced motion is active, step transitions are instant (no animation), and the pipeline visualisation shows all stages simultaneously rather than staged reveal.
- Interactive elements have visible focus indicators (minimum 2px outline).
- Colour is never the sole indicator of state — icons and text labels accompany all colour-coded elements (e.g. tier indicators, validation success/failure).

### 12.4 Terminal Mode Accessibility

- All terminal output is plain text compatible with screen readers (no reliance on colour alone for meaning).
- Progress bars include a percentage figure alongside the visual bar.
- Interactive prompts use clear text labels and explicit key hints: `? Install Ollama? (Y/n)`.
- `--json` output mode provides machine-readable results for users with custom tooling.

---

## 13. Open Questions

| # | Question | Impact | Resolution path |
|---|----------|--------|----------------|
| 1 | Should the wizard auto-detect healthcare context (for HIPAA pre-selection) or is self-declaration sufficient? | Privacy preset accuracy | User research in beta |
| 2 | What is the minimum acceptable model for the privacy pipeline? Can regex + compromise.js alone provide an adequate experience on Lite tier? | Lite tier viability | Benchmarking in F3.1/F3.2 |
| 3 | Should the test interaction use a real LLM call or a canned response when the model is still downloading? | Test step design | Implementation decision |
| 4 | How should the wizard handle enterprise MDM policies that pre-configure settings? Should it skip those steps or show them as read-only? | Enterprise deployment | A3.1 policy loader integration |
| 5 | Should `loke init` in terminal mode support piped input for API keys (e.g. from a secrets manager)? | CI/automation ergonomics | Community feedback |
