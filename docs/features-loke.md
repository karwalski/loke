# loke — Feature Document

**Version:** 0.2.0
**Generated:** 2026-05-20
**License:** Apache 2.0

loke is a locally-run intelligence layer between users and external LLMs. It intercepts, anonymises, optimises, and routes LLM traffic. The mission is to keep people "between the lines" — regulatory, organisational, cost, and ethical.

---

## Architecture

loke is built on a four-layer architecture, all implemented in toke and compiled to a single native binary via ooke.

```
MOKE DEMO LAYER          — Reference application exercising platform APIs
APPLICATION LAYER         — Browser mode, CLI mode, policy engine, onboarding, MCP
PLATFORM LAYER            — HTTP server, plugins, UI shell, i18n, error handling
FOUNDATION LAYER          — Privacy pipeline, token optimiser, router, cache, storage, audit, governance, agents, memory
```

---

## Foundation Layer

### Privacy & Anonymisation Pipeline

Multi-layer detection system ensuring all outbound data passes through privacy filtering before reaching external LLMs.

**Detection Layers:**

| Layer | Module | Description | Confidence |
|-------|--------|-------------|-----------|
| Regex | `core/privacy/regex.tk` | 10 deterministic patterns: email, phone (AU/US), credit card, IP, TFN/ABN, SSN, URL, API key | 0.60–0.99 |
| Local NER | `core/privacy/ner.tk` | SLM-based named entity recognition via Ollama — contextual understanding of names, organisations, addresses | Configurable |
| Presidio | `core/privacy/presidio.tk` | Microsoft Presidio via REST API (optional sidecar) — 180+ entity types, enterprise-grade | Configurable |
| Sidecar | `core/privacy/sidecar_client.tk` | OpenAI Privacy Filter model (1.5B params) on port 11435 — detect and anonymise via local inference | Model-dependent |

**Consensus Strategies** (`core/privacy/consensus.tk`):

| Strategy | Behaviour | Best For |
|----------|-----------|----------|
| `most-restrictive` (default) | Union of all detections — if any layer flags it, it's masked | Regulatory compliance, maximum safety |
| `first-match` | Highest priority layer wins on overlaps | Performance-sensitive deployments |
| `unanimous` | All layers must agree | Minimising false positives |
| `majority` | >50% of layers agree | Balanced deployments with 3+ layers |

**Entity Routing** (`core/privacy/entity_routing.tk`): Different entity types assigned to the layer that handles them best — emails and phones to regex, person names to NER, medical records to Presidio.

**Layer Health** (`core/privacy/layer_health.tk`): Monitors availability of each layer. System degrades gracefully — remains operational with at least one layer available. Reports HEALTHY or DEGRADED status.

**Pipeline Orchestrator** (`core/privacy/pipeline.tk`): Sequences all layers, deduplicates overlapping detections, escalates sensitivity classification (PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED), generates reversible placeholders, injects guardian prompt. The browser handler now calls the core privacy pipeline directly (GA1.1-GA1.8 completed) — all browser traffic flows through the full detection stack, response restoration, kill switch check, audit logging, token optimisation, semantic cache, intelligent routing, and governance policy evaluation.

**Placeholder System** (`core/privacy/placeholder.tk`): Generates `[ENTITY_TYPE_N]` tokens (e.g., `[EMAIL_1]`, `[PERSON_2]`). Stores original → placeholder mapping. Restores placeholders in LLM responses to original values.

**Evaluation Mode** (`core/privacy/evaluation.tk`): Measures layer quality against labelled datasets — precision, recall, F1 score per layer.

**Metrics** (`core/privacy/filter_metrics.tk`): Tracks detection count, processing time, average confidence, and entity counts per layer.

---

### Token Optimisation

| Component | Module | Savings | Description |
|-----------|--------|---------|-------------|
| TOON serialiser | `core/optimiser/toon.tk` | 30–60% | Converts JSON to compact TOON format with type detection and abbreviation |
| LLMLingua | `core/optimiser/llmlingua.tk` | 5–20x | Python sidecar REST API for adaptive prompt compression |
| Semantic cache | `core/optimiser/cache.tk` | Up to 73% on hits | Vector-store backed prompt cache — embedding similarity (0.92 threshold), 24h TTL, auto-eviction |
| Token budget | `core/optimiser/budget.tk` | — | Daily/weekly/monthly limits with pre-flight cost estimates |

**Combined target:** 60–80% token reduction on typical prompts.

---

### LLM Router

**Intent Classification** (`core/router/intent.tk`): < 10ms embedding-based classifier. Categories: chat, code generation, code review, summarisation, classification, NER, embedding, data analysis.

**Sensitivity Scoring** (`core/router/sensitivity.tk`): Derives PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED from PII detection and content analysis.

**Model Selection** (`core/router/selector.tk`):
- Decision factors: task type, sensitivity, latency tolerance, cost constraints, model tier
- Strategies: cheapest-adequate, fastest, best-quality, local-first
- Model registry: Ollama, Anthropic (Claude), OpenAI (GPT-4o), Google (Gemini), Mistral, OpenRouter, local inference
- Context windows: Claude (200K), GPT-4o (128K), Qwen-72B (128K), Qwen-7B (32K)

**Latency Tolerance** (`core/router/latencyrouter.tk`): instant (<2s), patient (<30s), background (minutes-hours). Unlocks larger models for non-urgent tasks.

**RouteLLM Integration**: Cost-signal integration via REST — 85% cost reduction with 95% quality retention.

---

### Storage & Audit

**Database** (`core/storage/db.tk`): SQLite + SQLCipher via ooke native bindings. WAL mode, numbered migrations, parameterised queries (no string concatenation). SQLCipher encryption is enabled by default (GA2.2) — the encryption key is derived from the OS keychain and all tables are encrypted at rest.

**OS Keychain Integration** (`core/storage/keychain.tk`, `core/config/keychain.tk`): API keys and secrets stored in the OS keychain via Security framework bindings (GA2.1). Keys are fetched per-request with expiry validation, never written to disk, and never appear in log output.

**Audit Trail** (`core/storage/audit.tk`): Append-only log with hash chain for tamper detection. Records: event type, model, provider, sensitivity, risk tier, token counts, cost, duration, correlation ID. Never stores prompt/response content. Now wired into every browser and CLI request path (GA1.4).

**Log Redaction** (`core/privacy/logsanitiser.tk`): All log output passes through an auto-redaction filter (GA2.4). Emails, phone numbers, API keys, authorization tokens, passwords, and other sensitive values are replaced with `[REDACTED]` before reaching any log destination. Debug mode is subject to the same redaction rules as production.

**Settings Store** (`core/storage/settings.tk`): Namespaced typed key-value (string, int, bool, float, JSON).

**Vector Store**: ooke native bindings for semantic cache and memory palace.

**Ephemeral Store**: In-memory key-value with auto-expiry, no disk serialisation. Scoped per-session.

---

### Governance Gateway

**Policy Engine** (`core/governance/policy.tk`): Risk classification (low/medium/high) based on sensitivity × use case risk × cost. Decisions: allow, allow-with-warning, require-approval. Controls escalate with risk: anonymisation → audit logging → guardian prompt → human preview → cost confirmation → explainability trace.

**Kill Switch** (`core/governance/kill_switch.tk`): Global, per-provider, per-use-case, per-agent scope. Engage with reason and auto-release time. Persisted to settings with chain-of-custody metadata. Checked before every AI call.

**Use Case Registry** (`core/governance/types.tk`): Built-in categories: chat-completion, code-generation, code-review, summarisation, data-analysis, translation, classification, agent-task, mcp-tool-call. Schema: ID, name, risk level, purpose, approved models, owner.

**Decision Trace**: Captures full pipeline path — original input, PII detected, anonymisation applied, compression, risk classification, policy decisions, model selected (with reason), prompt sent, response received, de-anonymisation.

**Monitoring** (`core/governance/monitoring.tk`): Incident types: PII leakage suspected, policy violation, quality degradation, provider outage, cost overrun, agent misbehaviour, security concern. Severity levels, post-incident review templates, trend tracking.

**Scorecard** (`core/governance/scorecard.tk`): Privacy %, compliance violations, risk tier breakdown, ownership coverage, open incidents. Trend charts (7d/30d/90d), drill-down.

---

### Agent Framework

**Agent Definition** (`core/agents/`): YAML/TOML format with name, schedule/trigger, model preference, risk level, permissions, max cost per run, owner. Auto-registered in governance use case registry.

**Scheduling & Triggers**: Cron schedules, file change triggers, webhook triggers, MCP event triggers. Manual via `loke agents run` or UI. Chained execution with circular dependency detection.

**Execution Sandbox**: Permission enforcement (file access restricted to declared paths), cost limit enforcement with pause-and-alert, configurable time limit (default 5 min). All governance controls apply.

**Templates**: Daily digest, code review assistant, expense categoriser, meeting prep, documentation updater, security scanner.

**Overnight Batch**: Low-power mode 11pm–7am (configurable), full resource allocation, morning digest.

---

### Memory Palace

**Palace Structure** (`core/memory/palace.tk`): Wings → Halls → Rooms → Closets (AAAK summaries) → Drawers (verbatim) → Tunnels (cross-links). Storage: SQLite + vector store.

**Semantic Search** (`core/memory/search.tk`): < 500ms for 100K drawers. Local embeddings only. Scoped by wing/hall.

**Automatic Context Enrichment**: Before every LLM call, search palace for relevant memories. Top-N included as AAAK context. Anonymised before cloud LLMs.

**Knowledge Graph** (`core/memory/graph.tk`): Entity extraction, relationship mapping, temporal validity windows, contradiction detection, graph visualisation.

**AAAK Shorthand** (`core/memory/aaak.tk`): Natural language → compressed shorthand (5–30x compression). Readable by any LLM without decoder. Layered context loading (L0: 20 tokens → L3: deep memory via search).

**Memory MCP Server** (`core/memory/mcp.tk`): Tools: `memory.search`, `memory.store`, `memory.facts`, `memory.context`, `memory.diary_write/read`, `memory.status`.

---

## Platform Layer

### HTTP Server

Port 11430 (localhost-only by default). ooke native binary serving both API endpoints and UI pages.

**API Endpoints:**

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/health` | GET | System status (loke version, Ollama status, port) |
| `/api/models` | GET | Ollama model list |
| `/api/pipeline` | POST | Privacy pipeline + LLM inference |
| `/api/settings` | GET/POST | Configuration (API keys, port, preferences) |
| `/api/privacy` | GET/POST | Privacy filter status and controls |
| `/api/savings` | GET/POST | Token savings dashboard data |
| `/api/approve` | POST | Approval workflow |
| `/api/tabs` | GET/POST | Browser tab management |

**Security**: CSP headers, HSTS, rate limiting, no stack traces leaked. CORS restricted to localhost origins.

### Extensibility

**Plugin Registration**: Via `plugin.registry.register(name, version, hooks)`. Privacy pipeline hooks (`privacy.before`, `privacy.after` — can append detections but cannot suppress built-in layers). Custom provider registration. Governance rule hooks (can only restrict, not relax).

### UI Platform

CSS custom properties design system (dark theme). Semantic HTML with responsive layout. Client-side routing, notification system, settings UI.

### Internationalisation

Translation function `t(key, params?)` with namespaced keys, interpolation, pluralisation. Locale files in JSON.

### Integration Framework

Adapter interface (connect/disconnect/health). OAuth 2.0 support with token refresh. HTTP client with timeout, retry, circuit breaker.

### Error Handling

Global catch with correlation ID logging. Consistent JSON error responses. Client-side toast notifications.

---

## Application Layer

### Browser Mode

ooke native binary with web view. Tab management, history, bookmarks. Chat interface with streaming responses. Dashboard persistence. Web privacy metadata (robots.txt AI directives).

### Terminal Mode (CLI)

**CLI Proxy** (`cli/src/proxy.tk`): Port 11431. Intercepts Claude Code, Codex, Gemini CLI traffic. Full privacy pipeline → LLM → response restoration. Session tracking (requests intercepted, entities redacted, tokens saved).

**Direct Prompting**: `loke ask <prompt>` with model selection, dry-run, stdin support, streaming.

**Environment Integration**: `loke init`, shell profile setup, git hooks, VS Code config, `loke doctor` diagnostics.

### MCP Framework

**MCP Server** (`mcp-toke/src/server.tk`): Port 11435. Tools: compress, decompress, template, analyse.

**MCP Broker** (`mcp-broker/src/server.tk`): Port 11436. Connects local MCP servers. Per-server permissions (tool allowlist/denylist, max-cost, require-approval). Privacy pipeline on all tool call data. Audit trail on every invocation.

### Desktop Distribution

DMG (macOS), NSIS (Windows). Code signing and notarisation. Auto-update via GitHub Releases. Portable CLI binary.

---

## Build & Test

**Build**: `./scripts/build_loke.sh` — compiles all toke modules to LLVM IR, links to 1.5MB arm64 native binary.

**Tests**: `./scripts/run_tests.sh` — discovers `test_*.tk` files, compiles and runs each, reports pass/fail. 52 test files covering privacy, memory, governance, storage, models, providers, agents, MCP, CLI, optimiser.

**CI**: GitHub Actions workflow — builds toke/ooke from source, runs tests, produces structured JSON artefact.

---

## Deployment

- **Single native binary**: No external runtime dependencies
- **Ollama**: Local models via REST API (installed separately)
- **Presidio**: Optional Python sidecar for enterprise PII detection
- **LLMLingua**: Optional Python sidecar for prompt compression
- **Privacy Filter**: Optional Python sidecar (OpenAI model, port 11435)
- **No data leaves device during local inference**
- **Cloud routing**: Explicit user opt-in with per-request confirmation available

---

## Compliance Configurations

| Regulation | Consensus | Layers | Thresholds | Key Entity Types |
|-----------|-----------|--------|-----------|-----------------|
| GDPR | most-restrictive | All enabled | 0.6–0.7 | EMAIL, PHONE, PERSON, ADDRESS, DOB, IBAN, NATIONAL_ID |
| HIPAA | most-restrictive | All + Presidio | 0.6 | PERSON, DOB, MEDICAL_RECORD, SSN, PHONE, EMAIL, DEVICE_ID |
| AU Privacy Act | most-restrictive | Regex + NER | 0.7 | PERSON, TFN, MEDICARE, PHONE, EMAIL, ADDRESS, DRIVERS_LICENCE |

---

## Performance Targets

| Metric | Target |
|--------|--------|
| Pipeline overhead (anonymise + compress + route) | < 1 second |
| Intent classification | < 10ms |
| First response token streaming | < 2 seconds after pipeline |
| UI interactions | < 100ms |
| Memory search (100K drawers) | < 500ms |

---

## GA Epics — Completed

The following GA (General Availability) epics have been completed, bringing all core engine features into active use across browser and CLI modes:

- **GA1: Pipeline Integration** (GA1.1-GA1.9) — All core engine modules (privacy pipeline, response restoration, kill switch, audit logging, token optimisation, semantic cache, intelligent router, governance policy) are wired into the browser handler. End-to-end verification complete.
- **GA2: Security Hardening** (GA2.1-GA2.5) — API keys migrated to OS keychain, SQLCipher encryption enabled, Apache 2.0 licence headers on all source files, auto-redaction on all log output, localhost-only HTTP binding enforced.
- **GA3: UX Alignment** (GA3.1-GA3.7) — Full accessibility overhaul with ARIA labels, graduated 4-level warning system, simple/advanced view toggle, pre-send cost estimation, cancel in-flight requests, feedback comments on thumbs-down, sensitivity explanation tooltips.
