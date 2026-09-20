# loke — Epics & Stories

**License:** Apache 2.0
**Version:** v1.2 (toolchain hold cleared 2026-09-20 — see `TOOLCHAIN.lock`; the build is mid-migration under F10)

---

> **This is the project's only backlog.** `progress.json` was retired on 2026-09-19 and is archived at
> [`archive/progress.json.retired-2026-09-19`](archive/progress.json.retired-2026-09-19); its open
> items were re-verified and migrated as **Epic BG1**. Do not create a second backlog — the previous
> pair produced ID collisions where the same letter named different epics, and statuses that were four
> months stale.

## How This Document Is Structured

Epics are grouped into three layers: **Foundation** (the core engine that all modes share), **Platform** (the extensibility, UI, and infrastructure layer that applications build on), and **Application** (the user-facing modes and interfaces). Cross-cutting concerns span all layers.

Story sizing uses T-shirt sizes: **S** (< 1 day), **M** (1-3 days), **L** (3-5 days), **XL** (1-2 weeks).

Stories sourced from the platform requirements document are tagged with their R-number origin (e.g. `[R2.3]`) for traceability.

Story status values: blank (not started) · **Spec done** · **Done** · **⏸ On hold**

> **⏸ On hold** stories are blocked pending a dependency becoming ready for development. See the hold notice on each affected layer for detail. **The toolchain hold was cleared on 2026-09-20** — toke `6cc9061`+ and ooke `v3.0.0-rc.1` are published and the build runs — so the only remaining holds are hardware (LC1), a missing toke capability (zip/XLSX/OCR/PDF), or another story.

---

# FOUNDATION LAYER

> **Foundation layer — now in development**
>
> loke is built on **ooke** ([github.com/karwalski/ooke](https://github.com/karwalski/ooke)) — a lightweight CMS and web application framework written in the toke programming language. **The toolchain hold was cleared on 2026-09-20:** toke `6cc9061`+ and ooke `v3.0.0-rc.1` are both published and fetchable, and CI builds loke for the first time. [`TOOLCHAIN.lock`](../TOOLCHAIN.lock) is the authority. **The build is not green** — 58 of 199 modules compile, and the remaining work is split into F10.14–F10.24. Stories that need a compiled binary are queued behind that rather than held; the only real holds left are hardware (LC1), a genuinely missing toke capability (zip, XLSX, OCR, PDF) or another story.
>
> **Architectural impact of ooke:**
>
> | Previously specified | Replaced by |
> |---|---|
> | TypeScript (strict, ESM) | toke programming language |
> | pnpm workspaces monorepo | ooke build system (`ooke.toml`) |
> | Electron (browser mode app shell) | ooke native binary + web view |
> | Node.js runtime | ooke compiled native binary (C) |
> | ESLint / Prettier | toke linting and formatting tools |
> | Vitest test runner | toke test runner |
> | @electron/llm (in-process inference) | Native inference via ooke bindings |
> | Transformers.js (browser-side NER) | Local SLM via ooke native bindings |
> | compromise.js (JS NLP library) | NER via local SLM (language-agnostic) |
> | LanceDB (Node.js vector store) | Vector store via ooke native bindings |
> | better-sqlite3 / SQLCipher | SQLite + SQLCipher via ooke native bindings |
>
> What does **not** change: Ollama (REST API, language-agnostic), Presidio (Python sidecar via REST), MCP protocol (implemented in toke), the pipeline architecture, all functional requirements, and all acceptance criteria.

## Epic F1: Project Scaffolding & Build System

*Establish the ooke project structure, build tooling, CI, and application shell so that all subsequent Foundation work has a stable base.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F1.1 | M | **Done** | Initialise ooke project structure (`ooke.toml`, toke source layout, linting, formatting — replaces pnpm/TypeScript/ESLint/Prettier) |
| F1.2 | L | **Done** | Application shell — browser mode (ooke native binary with web view; window management; IPC equivalent; multi-platform Mac + Windows builds — replaces Electron) |
| F1.3 | M | **Done** | Application shell — CLI mode (`loke` command in toke; config loading; structured logging with correlation IDs; auto-redaction of sensitive fields) `[R1.3]` |
| F1.4 | M | **Done** | CI/CD pipeline (GitHub Actions: toke lint, toke test, ooke build, release, licence compliance, dependency vulnerability scanning) `[R12.6]` |
| F1.5 | L | **Done** | Configuration and secrets management (hierarchical config via `ooke.toml` + environment overrides, schema validation, OS keychain for API keys, fail-fast on invalid) `[R1.1, R1.2]` |
| F1.6 | M | **Done** | Ordered startup and graceful shutdown (boot sequence: config → logger → database → migrations → settings → routes → server → health check → summary; signal handling, request draining, connection cleanup) `[R1.5, R1.6]` |
| F1.7 | M | **Done** | Health check system (subsystem probes for database, integrations, AI services; aggregate status endpoint; readiness probe; applications register custom health checks) `[R1.4]` |

## Epic F2: Local Model Integration

*Enable loke to run small language models locally for privacy filtering, intent classification, summarisation, simple completions, and tiered inference — matching model size to task urgency.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F2.1 | L | **Done** | Ollama service manager (auto-detect, start/stop via REST API, health check, model management — Ollama is language-agnostic, no change to functional requirement) |
| F2.2 | M | **Done** | Model capability registry (capabilities, benchmarks, task-to-model mapping — implemented in toke) |
| F2.3 | L | **Done** | MLX backend for Apple Silicon (native toke/ooke bindings or REST bridge to MLX — 8-9% faster than llama.cpp on Apple hardware) |
| F2.4 | M | **Done** | Native in-process inference via ooke bindings (replaces @electron/llm — same functional requirement: low-latency local inference without spawning a separate process) |
| F2.5 | M | **Done** | Local NER and embeddings (replaces Transformers.js — NER and embedding inference via local SLM through ooke native bindings or Ollama REST) |
| F2.6 | XL | **Done** | Tiered inference engine (three tiers: Interactive — fully in GPU/unified memory, 25–55 tok/s, models up to 10B; Considered — partial GPU offload via Ollama `num_gpu`/llama.cpp `--n-gpu-layers`, 5–15 tok/s, up to 70B quantised; Background — maximum offload with heavy RAM/disk streaming, 0.5–5 tok/s, 70B+ full precision; tier selected by F5 router based on request source, user flag, task classification, and AG1 latency tolerance; progress indicator for Considered and Background; tier benchmarked on first run per model) |
| F2.7 | L | **Done** | Background inference queue (sequential job queue for Background-tier requests; priority: user-initiated > agent-scheduled > evaluation; Interactive always preempts — Background job pauses and resumes; `loke queue list/cancel/prioritise/pause/resume`; persists across restarts; completion notifications; queue metrics fed into G4 dashboards) |
| F2.8 | L | **Done** | Hardware-aware model recommendations (profile RAM, GPU VRAM, unified memory, disk type/speed, CPU on first run; per-model viability assessment at each inference tier; recommendations shown in model selector with tier badges; refreshed on hardware change, new model added, or companion device paired; `loke models recommend` CLI; disk space warnings) |
| F2.9 | L | **Done** | Disk-streaming inference for extreme offload (Background tier only; load model layers from NVMe sequentially with overlapped I/O prefetch; decompose large model into per-layer shards in `~/.loke/models/shards/`; configurable RAM ceiling; requires NVMe — warns on SATA/HDD; graceful degradation if < 0.1 tok/s; actual tok/s displayed with cloud cost comparison; equivalent of AirLLM layer-by-layer execution via llama.cpp mmap/partial-offload) |

## Epic F3: Privacy & Anonymisation Pipeline

*Build the multi-layer defence-in-depth system that detects PII, replaces it with reversible placeholders, and restores originals in responses. All implemented in toke on ooke.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F3.1 | M | **Done** | Regex PII detector in toke (emails, phones, SSNs, credit cards, IPs, AU TFNs/ABNs — 10MB/s target, zero external deps) |
| F3.2 | M | **Done** | NLP NER detector (names, places, organisations via local SLM — replaces compromise.js JS library with toke-native or Ollama-backed NER) |
| F3.3 | L | **Done** | SLM-based NER detector (context-aware PII: "my boss John" vs "John Deere tractor" — via Ollama REST or ooke native inference) |
| F3.4 | L | **Done** | Presidio integration (180+ entity types, Python sidecar via REST — unchanged: Presidio is language-agnostic) |
| F3.5 | L | **Done** | Placeholder mapping and reversal engine (SQLCipher via ooke native bindings, relational consistency, secure deletion — replaces better-sqlite3) |
| F3.6 | L | **Done** | Privacy pipeline orchestrator (layer sequencing, conflict resolution, dedup, dry-run, visual diff, pluggable entity type registration) `[R4.1, R4.2]` |
| F3.7 | L | **Done** | Prompt template engine (versioned templates, parameter injection, no raw data concatenation, reviewable) `[R4.3]` — *spec remains valid, implementation moves to toke* |
| F3.8 | M | **Done** | Guardian system prompt (mandatory non-bypassable safety injection into every LLM call, version-controlled) `[R4.5]` — *spec remains valid* |
| F3.9 | L | **Done** | Privacy pipeline test harness (end-to-end: raw data + template → assert no restricted identifiers, guardian present, rehydration correct; 100% coverage) `[R4.9, R15.3]` |

## Epic F3b: Configurable Multi-Layer Privacy Filters

*Extend the privacy pipeline to support multiple pluggable PII detection models — including the OpenAI Privacy Filter and other compatible token-classification models — with configurable layer ordering, per-layer confidence thresholds, and organisation-level trust policies. Users and organisations can compose their own defence-in-depth stack by choosing which filters run, in what order, and what to do when layers disagree.*

**Context:** The existing privacy pipeline (F3) uses regex (F3.1), local SLM NER (F3.2/F3.3), and Presidio (F3.4) as detection layers, orchestrated by the pipeline orchestrator (F3.6). This epic generalises the layer concept so that any compatible token-classification model — starting with [OpenAI Privacy Filter](https://huggingface.co/openai/privacy-filter) (Apache 2.0, 1.5B params, 50M active, runs on laptop, 128K context, 8 PII entity types, BIOES span decoding) — can be added as a detection layer alongside existing detectors. The key design goal is **composability**: organisations with strict compliance requirements can stack multiple independent models and require consensus before data leaves the device.

**Architectural principle:** Each privacy filter layer implements a common interface (`detect(text:str):@$piientity`). The pipeline orchestrator already supports layer sequencing and conflict resolution (F3.6). This epic adds: a filter registry, a layer configuration schema, trust/priority ordering, consensus policies, and the first external model integration (OpenAI Privacy Filter).

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F3b.1 | L | **Done** | **Privacy filter layer abstraction and registry** — Define a `$privacyfilter` interface type: `id:str`, `name:str`, `kind:str` (regex/ner/model/external), `detect(text:str):@$piientity`, `entitytypes():@str`, `isavailable():bool`, `confidence():f64`. Create a filter registry (`$filterregistry`) where layers are registered at startup. Migrate existing detectors (regex F3.1, NER F3.2/F3.3, Presidio F3.4) to implement this interface without changing their behaviour. Registry supports `register`, `list`, `get`, `remove`. Each filter declares its supported entity types and a default confidence score. |
| F3b.2 | L | **Done** | **Layer ordering and trust configuration** — Add a `$layerconfig` type to `ooke.toml` and the settings UI: `[[privacy.layers]]` entries, each with `id`, `enabled:bool`, `priority:i32` (lower = runs first = higher trust), `mode:str` (detect-only / detect-and-mask / veto), `confidence_threshold:f64` (minimum confidence to accept a detection), `entity_filter:@str` (subset of entity types this layer handles, empty = all). Pipeline orchestrator reads layer config and executes filters in priority order. Layers with `mode:veto` can block the request entirely if PII is found above threshold. Default config: regex (priority 1), NER (priority 2), Presidio (priority 3, if available). Organisation-managed configs override user configs. |
| F3b.3 | XL | **Done** | **OpenAI Privacy Filter integration** — Integrate [openai/privacy-filter](https://huggingface.co/openai/privacy-filter) as a privacy filter layer. The model runs locally via ONNX runtime through ooke native bindings or via Ollama as a token-classification task. Supports the 8 entity types: `account_number`, `private_address`, `private_email`, `private_person`, `private_phone`, `private_url`, `private_date`, `secret`. Map OpenAI entity types to loke's normalised entity type taxonomy (F3.6 already has this). Handle BIOES span decoding to extract entity boundaries. Configurable operating point (precision/recall tradeoff via Viterbi transition biases). 128K context window means full-document scanning without chunking for most inputs. Register as `openai-privacy-filter` in the filter registry. |
| F3b.4 | L | **Done** | **Consensus and conflict resolution policies** — When multiple layers detect overlapping entities, define resolution strategies: `first-match` (highest-priority layer wins), `unanimous` (all layers must agree for entity to be masked), `majority` (> 50% of layers agree), `most-restrictive` (union of all detections — anything any layer flags gets masked), `confidence-weighted` (weighted average of confidence scores across layers, threshold determines action). Store the chosen strategy in `privacy.consensus_strategy` in config. Default: `most-restrictive` (safety-first). Each resolved entity records which layers detected it and their individual confidence scores for auditability. |
| F3b.5 | M | **Done** | **Per-entity-type layer routing** — Allow configuration to route specific entity types to specific layers. Example: `private_person` detection routed to OpenAI Privacy Filter (strong at contextual name disambiguation — "my boss John" vs "John Deere") while `account_number` and `secret` routed to regex (deterministic, no false negatives for known patterns). Config: `[[privacy.entity_routing]]` entries with `entity_type`, `preferred_layers:@str`, `fallback_layers:@str`. When preferred layers are unavailable, fallback layers are used. Unrouted entity types use the default layer ordering. |
| F3b.6 | M | **Done** | **Layer health monitoring and graceful degradation** — Each filter layer reports health status via `isavailable()`. The pipeline orchestrator checks health before each request. If a layer is unavailable (model not downloaded, Presidio not running, ONNX runtime error): log a warning with the layer name and reason; skip the layer; record the degradation in the pipeline trace (F3.6 already has stage-level tracing); if the unavailable layer was the only one configured for a specific entity type, emit a governance alert (G1). Never block the pipeline because a single layer is down — degrade gracefully with clear audit trail. Dashboard widget shows layer health status. |
| F3b.7 | M | **Done** | **Custom model registration for compatible token-classifiers** — Provide a registration interface for adding arbitrary HuggingFace-compatible token-classification models as privacy filter layers. User specifies: model path (local or HuggingFace ID), label mapping (model labels → loke entity types), confidence threshold, and priority. Validate that the model outputs token-level classifications. Support ONNX, SafeTensors, and Ollama-served models. Include a `loke privacy add-model <model-id>` CLI command and a settings UI panel. Ship with the OpenAI Privacy Filter as the first pre-configured model; others added via this interface. |
| F3b.8 | L | **Done** | **Organisation-managed layer policies** — Organisations can define mandatory privacy filter configurations that override user settings. Policy schema: `minimum_layers:i32` (e.g. require at least 2 independent filters), `required_layers:@str` (e.g. must include `openai-privacy-filter`), `locked_consensus:str` (e.g. force `most-restrictive`), `banned_layers:@str` (e.g. disallow external API-based filters), `max_confidence_threshold:f64` (prevent users from setting thresholds so high that detections are suppressed). Policies distributed via `loke.policy.json` managed by the compliance engine (A3). Violations surfaced in governance dashboard (G4). |
| F3b.9 | M | **Done** | **Privacy filter comparison and evaluation mode** — Provide a `loke privacy evaluate` command and UI panel that runs a text sample through all configured layers side-by-side and shows: which entities each layer detected, confidence scores, overlaps, disagreements, false positive/negative estimates (when ground-truth labels are provided). Supports importing labelled evaluation datasets (JSON format: `[{text, entities: [{start, end, type}]}]`). Outputs a comparison matrix with per-layer precision/recall/F1 against the labelled data. Helps users choose which layers to trust and in what order. |
| F3b.10 | M | **Done** | **Privacy filter layer metrics and audit integration** — Record per-layer detection metrics in the audit trail (F6): layer ID, entities detected, confidence scores, processing time, consensus outcome. Aggregate metrics in the governance dashboard (G4): detection counts by layer over time, agreement rate between layers, per-entity-type detection distribution, layer latency percentiles. Expose metrics via the MCP server so external tools can query filter performance. |
| F3b.11 | S | **Done** | **Documentation and migration guide** — Document the multi-layer privacy filter architecture, configuration schema, and how to add custom models. Include a migration guide for existing deployments that explains: existing regex/NER/Presidio layers continue to work unchanged; the OpenAI Privacy Filter is optional and additive; how to enable it; recommended configurations for different compliance regimes (GDPR, HIPAA, Australian Privacy Act). Add to `docs/privacy-filters.md`. |

## Epic F4: Token Optimisation Pipeline

*Reduce token consumption through format conversion, compression, caching, and serialisation — targeting 60-80% reduction. All implemented in toke on ooke.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F4.1 | L | **Done** | TOON serialiser/deserialiser in toke (30-60% savings over JSON — toke is the natural home for TOON implementation) |
| F4.2 | L | **Done** | Data profiler for schema extraction in toke (CSV, JSON, DB results → compact TOON profiles) |
| F4.3 | L | **Done** | LLMLingua prompt compression (5-20x, Python sidecar via REST or ONNX runtime — interface unchanged) |
| F4.4 | L | **Done** | Semantic cache (vector store via ooke native bindings — replaces LanceDB Node.js library; embedding similarity, configurable threshold and TTL) |
| F4.5 | M | **Done** | Token budget manager (pre-flight estimates, daily/weekly/monthly limits, usage dashboard — implemented in toke) |

## Epic F5: LLM Router

*Intelligently route each request to the best available model based on sensitivity, complexity, cost, speed, latency tolerance, and preference. Implemented in toke on ooke.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F5.1 | L | **Done** | Semantic intent classifier (< 10ms, embedding-based via ooke native inference or Ollama REST, configurable categories) |
| F5.2 | M | **Done** | Sensitivity scorer (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED based on PII + policy — implemented in toke) |
| F5.3 | XL | **Reopened — see X8.6.** Not done: zero matches for any of the four strategy names across `packages/` and `src/` (`docs/claims.md` D3). One fixed selection path exists in `packages/core/src/router/selector.tk` | Model selection engine (cheapest-adequate, fastest, best-quality, local-first bias, fallback chains) |
| F5.4 | L | **Done** | Provider abstraction layer in toke (Ollama, OpenAI, Anthropic, Google, Mistral, OpenRouter — all via REST; streaming; tool calling) `[R4.8, R8.1]` |
| F5.5 | L | **Done** | Cost-optimised routing via RouteLLM signal integration (85% cost reduction, 95% quality retention — RouteLLM called via REST or subprocess) |
| F5.6 | M | **Done** | Latency tolerance routing dimension (`instant` < 2s / `patient` < 30s / `background` minutes-hours; determined by request source, task type, AG1 agent declaration, or user flag; unlocks larger local models in Considered/Background tiers for non-urgent tasks; cost vs speed comparison shown when tolerance is `background`; logged in audit trail for explainability) |
| F5.7 | M | **Done** | Model size escalation with user consent (non-blocking dismissible prompt when a larger model would improve quality but requires a slower tier: "This would benefit from Qwen-72B — ~30s instead of instant. [Use larger] [Stay fast] [Always for this task]"; preferences remembered per task type; capped at once per session per task type unless opted in; escalation acceptance rate feeds router learning via X5.3) |

## Epic F6: Storage & Audit Layer

*Persistent encrypted local storage for conversations, audit trails, PII mappings, configuration, and cache. Implemented in toke using SQLite + SQLCipher via ooke native bindings.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F6.1 | L | **Done** | SQLite database schema (SQLCipher via ooke native bindings, WAL mode, foreign keys, numbered migrations with checksum verification, typed data access layer with parameterised queries) `[R3.1, R3.2, R3.6, R3.7]` |
| F6.2 | L | **Done** | Audit trail system (append-only, hash chain, tamper detection, export, SIEM forwarding; metadata only — never stores prompt/response content) `[R3.5, R4.7]` |
| F6.3 | M | **Done** | Vector store for semantic operations (via ooke native bindings — replaces LanceDB; prompt cache, routing examples) |
| F6.4 | L | **Done** | Secure ephemeral storage (mlock equivalent via ooke, secure wipe, auto-expiry, no disk serialisation) |
| F6.5 | M | **Done** | Database backup and restore (consistent snapshot via SQLite VACUUM INTO, timestamped naming, configurable retention, restore with validation) `[R3.8, R8.5]` — *spec remains valid* |
| F6.6 | M | **Done** | Persistent sync queue (enqueue/dequeue with retry and exponential backoff, survives restarts — implemented in toke) `[R3.4, R8.7]` — *spec remains valid* |
| F6.7 | M | **Done** | Namespaced settings store (typed key-value: string, number, boolean, JSON; `loke.*` prefix + application prefix; get/set/list API — implemented in toke) `[R3.3]` — *spec remains valid* |

## Epic F7: MCP Framework

*Host, connect to, and broker MCP servers with full privacy filtering on all data flows. MCP protocol is language-agnostic; client and server implemented in toke.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F7.1 | L | **Done** | MCP client implementation in toke (tool discovery, invocation, privacy filtering on all data) |
| F7.2 | L | **Done** | MCP server hosting in toke (expose loke.anonymise, loke.compress, etc. to connected LLMs) |
| F7.3 | XL | **Done** | MCP broker for intermediary routing — config-driven, connects to any MCP-compatible service (stdio/SSE/HTTP transport); no dependency on any specific upstream; broker configured via `ooke.toml` `[[mcp.servers]]` entries (name, transport, command/url, env); privacy pipeline applied on all tool call data in both directions; per-server permissions: tool allowlist/denylist, max-cost, require-approval flag; audit trail on every tool invocation (server, tool, anonymised args, outcome); health check per server; `loke mcp list/test/disable` CLI; used by moke and any loke application to connect external tools through the privacy boundary |
| F7.4 | L | **Done** | toke MCP server in toke (compress, decompress, template, analyse — TOON+LLMLingua backend; toke is the natural implementation language) |
| F7.5 | M | **Done** | Local MCP server discovery (mDNS/Bonjour via ooke, explicit approval, companion devices) |

## Epic F8: Companion Device Support

*Extend local compute to nearby high-power devices over secure direct connections. Implemented in toke on ooke.*

> The std.mdns and std.tls bindings are available and the compiler now is too. **F8.1–F8.4 are marked Done for behaviour that has never executed** — mDNS pairing, TLS 1.3 mutual auth with pinning, remote model execution and the Exo integration. They are in the RV1 re-verification set.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F8.1 | L | **Done** | Companion device discovery and pairing (mDNS via ooke, confirmation codes, security checks) |
| F8.2 | L | **Done** | Secure communication channel (TLS 1.3 mutual auth, certificate pinning, heartbeat — via ooke TLS primitives) |
| F8.3 | XL | **Done** | Remote model execution (companion Ollama/Exo via REST, router integration, privacy pipeline applied) |
| F8.4 | L | **Done** | Exo distributed inference integration (GPL-3.0 boundary maintained — REST API only, cluster monitoring) |

## Epic F9: Model Evaluation & Benchmarking

*Give users objective, workload-specific data on every local model so they can make informed routing decisions — not trust generic benchmarks that don't reflect their actual usage.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F9.1 | L | **Done** | Local model benchmarking suite (dimensions: throughput tok/s per tier, quality scored against reference outputs for user's task types, cost efficiency, memory footprint; built-in generic workloads plus user-custom workloads from usage history; runs in Background tier; results stored and comparable across models; triggered on model download, hardware change, user request, or monthly; `loke models benchmark <model>`; results feed F5.3 model selection engine and G4.3 provider scorecard) |
| F9.2 | M | **Done** | Model comparison A/B testing (`loke ask --compare "model-a,model-b" "prompt"` sends to both; browser mode split view; blind comparison option — names hidden until user rates; user rates both responses; cost and latency displayed; comparison data feeds router learning, benchmark database, and provider scorecard; `loke models compare-history`; bulk comparison in Background tier produces report) |
| F9.3 | M | **Done** | "Could this run locally?" advisor (after every cloud API response, local SLM assesses whether a local model at any inference tier could handle this task type with acceptable quality; if yes: subtle indicator with opt-in to local routing; weekly summary of cloud requests that could have run locally with estimated savings; only suggests local routing after benchmark evidence confirms quality; feeds G4.2 value realisation dashboard) |

---

# PLATFORM LAYER

*Infrastructure and extension points that make loke a platform applications can build on. These epics enable third-party applications to use loke's privacy, routing, and storage capabilities without forking the core.*

## Epic P1: Platform HTTP Server

*Local web server that applications can extend with their own routes, middleware, and views — alongside or independent of Electron/CLI modes.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P1.1 | M | **Done** | HTTP server core (configurable host:port, default localhost:3000, optional TLS for local use, serves client directory as static assets with SPA fallback) `[R2.1, R2.2]` |
| P1.2 | L | **Done** | Versioned API routing (prefix `/api/v1/`, plugin-based route registration, applications register under own namespace) `[R2.3]` |
| P1.3 | L | **Done** | Composable middleware pipeline (enforced order: request ID → logging → CORS localhost-only → body size limit → timeout → auth pluggable → validation → error handling; named insertion points for app middleware) `[R2.4]` |
| P1.4 | M | **Done** | Standard response envelopes and request validation (success/error/paginated shapes, Zod schema validation on params/query/body, structured 400 errors) `[R2.5, R2.6]` |
| P1.5 | M | **Done** | Security hardening (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS in production, configurable per-route rate limiting with 429 responses) `[R12.1, R12.3]` |

## Epic P2: Platform Extensibility

*Plugin system and extension points so applications add domain-specific behaviour without forking the core.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P2.1 | XL | **Done** | Plugin registration system (routes, middleware at named insertion points, health checks, navigation items, settings sections, views — single registration API) `[R2.3, R1.4, Section 6]` |
| P2.2 | M | **Done** | Startup and shutdown hooks (onBeforeStart, onAfterStart, onBeforeShutdown callbacks; applications run custom init/cleanup logic within the lifecycle) `[Section 6]` |
| P2.3 | M | **Done** | Extensible configuration modules (applications extend base Zod schema with domain-specific sections, additional env variables, validated at startup alongside platform config) `[R1.2, Section 6]` |
| P2.4 | M | **Done** | Anonymisation pattern registration (applications register entity types + detection regexes + confidence weights; merged into privacy pipeline at startup; hot-reload supported) `[R4.2, Section 6]` |
| P2.5 | L | **Done** | Extension point documentation and contracts (versioned interfaces, semver compatibility guarantees, breaking change policy, migration guides for major versions) `[Section 6]` |
| P2.6 | L | **Done** | Privacy pipeline hook API (applications insert custom stages into the privacy pipeline without forking core; hook slots: `before_ner`, `after_anonymise`, `before_restore`, `after_restore`; each hook receives the current pipeline state and returns a modified state; hooks registered at startup via `pipeline.register_hook(slot; f)`; hook execution order: registration order; errors in hooks are logged and skipped — never crash the pipeline; hooks visible in pipeline console A4.2; used by moke for schema-first and local compute injection) |
| P2.7 | M | **Done** | Custom LLM provider registration (applications register new provider adapters without forking `providers/dispatcher.tk`; adapter interface: `connect():bool`, `generate(prompt;opts):str`, `embed(text):@(f32)`, `health():bool`; registered via `providers.register(id; adapter)`; auto-included in router model registry; appears in model selector UI; capability declarations: streaming, tool-calling, embedding; used by moke to route data-analysis requests to schema-aware custom handler) |
| P2.8 | M | **Done** | Governance rule hook (applications inject custom rule evaluation into the governance gateway; hook receives `$eval_context` before risk classification; returns `?(str)` — `none` to proceed, a string reason to block; registered via `gateway.register_rule_hook(id; f)`; hook outcome logged in audit trail with hook id; used by moke to enforce schema-first protocol — block requests where raw data detected in prompt) |

## Epic P3: UI Platform

*Design tokens, theming, component primitives, and application shell — so applications get accessible, themed UI without building from scratch.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P3.1 | L | **Done** | Design token system (CSS custom properties, semantic tokens for colours/spacing/typography/borders/shadows/transitions, neutral default palette, applications override for branding) `[R5.1]` |
| P3.2 | M | **Done** | Dark mode and theming (system/light/dark via `data-theme` on root, CSS custom property overrides, OS preference detection in real time, persisted in settings) `[R5.2]` |
| P3.3 | S | **Done** | CSS reset and base styles (modern reset, typographic baseline, `:focus-visible` rings, `prefers-reduced-motion` handling, no framework dependency) `[R5.3]` |
| P3.4 | L | **Done** | Component primitives CSS (buttons, cards, badges, form elements with all states, tables with responsive scroll, alerts, loading indicators, tooltips — all via tokens, all overridable) `[R5.4]` |
| P3.5 | M | **Done** | Application shell (semantic HTML: header, sidebar nav, main content area, responsive sidebar collapse on narrow viewports; applications populate with own items) `[R5.5]` |
| P3.6 | L | **Done** | Client-side router (hash-based, route definitions with parameter extraction, 404 fallback, document title updates, screen reader announcements on navigation) `[R5.6]` |
| P3.7 | M | **Done** | Navigation component (configurable data-driven items, icons, badges, active state, keyboard arrow-key navigation, compact/expanded modes) `[R5.7]` |
| P3.8 | L | **Done** | Notification system (bell with unread count, dropdown panel, toast variants: info/success/warning/error, auto-dismiss, screen reader announcements, stored in local DB, API for applications) `[R5.8]` |
| P3.9 | M | **Done** | Base settings UI (appearance toggle, timezone, language, integration status, backup, about/version, update check — applications extend with own sections) `[R5.9]` |

## Epic P4: Internationalisation

*i18n framework so every user-facing string passes through a translation layer from day one.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P4.1 | L | **Done** | Translation function and locale loader (`t(key, params?)`, namespaced keys, `{{name}}` interpolation, pluralisation via `_zero/_one/_other` suffixes, fallback to base locale, lazy-loading of additional locales) `[R6.1, R6.3]` |
| P4.2 | M | **Done** | Locale file structure (JSON in `locales/`, platform keys prefixed `loke.*`, application keys use own prefix, community-contributed translations) `[R6.2]` |
| P4.3 | M | **Done** | Layout accommodation and formatting (30-50% text expansion tolerance, no hardcoded widths, LTR-safe without hardcoding LTR; locale-aware date/time/number via `Intl` APIs, relative time via `Intl.RelativeTimeFormat`) `[R6.4, R6.5, R9.5]` |

## Epic P5: Integration Framework

*Reusable primitives for connecting to external services — authentication, retry, circuit-breaking, offline queuing.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P5.1 | L | **Done** | Integration adapter interface (standard contract: connect, disconnect, health check, domain methods; handles auth, retry, timeout, circuit-breaking; applications implement for their own services) `[R8.1]` |
| P5.2 | L | **Done** | OAuth 2.0 support (authorisation code grant, token storage in OS credential store, automatic refresh, expiry handling; reusable by any integration needing OAuth) `[R8.2]` |
| P5.3 | M | **Done** | Base HTTP client (configurable timeout, retry with exponential backoff, circuit breaker — open after N failures/half-open after cooldown, request/response header logging, `Retry-After` awareness) `[R8.6]` |
| P5.4 | M | **Done** | Input sanitisation utilities (HTML stripping, SQL escape supplementary to parameterised queries, log injection prevention, schema validation with unknown property stripping) `[R12.2]` |

## Epic P6: Error Handling Framework

*Consistent error handling across server, client, and API boundaries — no raw errors leak to users.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P6.1 | M | **Done** | Server error handling (global catch for unhandled errors, log with correlation ID, consistent error response shape `{ error: { code, message, requestId } }`, never expose stack traces to client) `[R13.1]` |
| P6.2 | M | **Done** | Client error handling (global handlers for uncaught exceptions and unhandled rejections, report to server for logging, user sees toast notification not raw error, rate-limited to prevent floods) `[R13.2]` |
| P6.3 | M | **Done** | API client wrapper (handles network errors, timeouts, HTTP error statuses, JSON parse failures; retries on 5xx with configurable attempts; applications use this instead of raw fetch) `[R13.3]` |

---

# APPLICATION LAYER

## Epic A1: Browser Mode — Chromium Workspace

*Browser-based workspace with full privacy protection.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A1.1 | L | **Done** | Tab and navigation management (tabs, history, bookmarks, keyboard shortcuts) |
| A1.2 | XL | **Done** | Webpage content extraction with privacy filtering (selection, full page, form data, visual preview) |
| A1.3 | L | **Done** | Chat interface / LLM interaction panel (dockable, streaming, transparency bar, pre-send preview) |
| A1.4 | L | **Done** | Dashboard persistence and reuse (template extraction, parameterised re-rendering, token savings) |
| A1.5 | M | **Done** | Web privacy metadata detection (robots.txt AI directives, data-ai-sensitivity attributes) |

## Epic A2: Terminal Mode — CLI & Coding LLM Proxy

*CLI that channels coding LLM interactions through loke's pipeline.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A2.1 | M | **Done** | Direct prompting via CLI (`loke ask`, model selection, dry-run, stdin support, streaming) |
| A2.2 | XL | **Done** | Coding LLM proxy mode (`loke proxy claude-code`, HTTP proxy/wrapper, real-time indicators) |
| A2.3 | L | **Done** | Local compute preprocessing for code (codebase profiling, proprietary pattern detection, config scrubbing) |
| A2.4 | L | **Done** | Multi-session terminal management (named sessions, shared/isolated contexts, audit trails) |
| A2.5 | M | **Done** | Environment integration (`loke init`, shell profile, git hooks, VS Code config, `loke doctor`) |

## Epic A3: Policy & Compliance Engine

*Enterprise policy loading, regulatory defaults, and compliance enforcement.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A3.1 | L | **Done** | Policy definition format and loader (YAML/TOML, enterprise URL fetch, merge rules, hot-reload) |
| A3.2 | M | **Done** | Regional regulatory defaults (EU GDPR, AU Privacy Act, HIPAA, CCPA, UK GDPR, Singapore PDPA) |
| A3.3 | M | **Done** | Compliance feedback loop (response scanning, warning UI, require-confirmation mode) |
| A3.4 | L | **Done** | Audit reporting and export (PDF/CSV/JSON, time ranges, templates, scheduled reports) |

## Epic A4: User Onboarding & Experience

*Guide new users, provide visibility, and reinforce value.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A4.1 | L | **Done** | First-run setup wizard (hardware check, Ollama install, provider config, privacy presets, test interaction) |
| A4.2 | M | **Done** | Pipeline visibility panel (real-time stage display, expandable details, CLI --verbose equivalent) |
| A4.3 | M | **Done** | Savings dashboard (tokens saved, cost saved, PII intercepted, local ratio, trends) |
| A4.4 | M | **Done** | Prompt approval workflow for beta (pre-send display, approve/edit/cancel, "don't ask again") |

## Epic A6: Desktop Distribution

*Package, sign, and distribute loke as a no-admin desktop application on macOS and Windows, with auto-update and a portable CLI binary. Full specification in `docs/specifications/desktop-distribution.md` and `docs/desktop-distribution-epics.md`.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A6.1 | M | **Done** | ooke packaging config (DMG for Mac, per-user NSIS for Windows, universal binary, output paths, app metadata — `dev.tokelang.loke`) |
| A6.2 | L | **Done** | Code signing and notarization (Apple Developer ID + notarization pipeline, Windows EV certificate + timestamping, CI secret wiring) |
| A6.3 | L | **Done** | Auto-update (ooke update mechanism, startup version check, background download, user-prompted restart via P3.8, stable and beta channels, force-update flag for security releases, channel preference in F6.7) |
| A6.4 | M | **Done** | Portable CLI binary (ooke native build for `packages/cli`, bundles core + mcp-toke + mcp-broker + shared, single-file Mac/Windows output, GitHub Release attachment) |
| A6.5 | M | **Done** | Per-user proxy configuration (MCP environment variable injection into shell profiles without admin; system-wide proxy as optional elevated step; runs after A6.6 port confirmation) |
| A6.6 | S | **Done** | Port conflict detection and resolution (bind default `11430`, auto-select next free port in range, persist in F6.7, surface in first-run wizard A4.1 and `loke doctor` A2.5) |

## Epic A5: In-App Feedback & Issue Reporting

*Built-in feedback mechanisms beyond thumbs-up/down — structured issue reporting and enhancement requests using the privacy pipeline.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A5.1 | M | **Done** | Issue reporting form (accessible from any view, captures type/description/repro steps/expected behaviour/optional screenshots, configurable destination — API endpoint, email, or external tracker) `[R14.1]` |
| A5.2 | M | **Done** | AI-assisted report drafting (optional: use LLM via privacy pipeline to help user refine problem statement and benefit description; form works without AI) `[R14.2]` |
| A5.3 | M | **Done** | Version check and update notification (check configurable endpoint daily or on demand, display update availability in UI, manual update trigger in settings — no auto-update) `[R11.1, R11.2]` |

---

# ACCOUNTABLE AI SYSTEMS LAYER

*Every AI capability executes within accountability controls. This layer sits between user intent and AI services, making every interaction governed, risk-classified, auditable, and owned. The goal is not to control the model — it's to control the system in which the model operates.*

## Epic G1: AI Governance Gateway

*Every AI request — browser mode, terminal mode, MCP tool call, or agent action — passes through a single governance gateway that enforces policy, logs decisions, and ensures accountability before anything executes.*

| Story | Size | Summary |
|-------|------|---------|
| G1.1 | XL | Governance gateway implementation (single mandatory entry point for all AI interactions; executes in order: authenticate → classify risk → check policy → filter data → log → route; `gateway.submit(request)` → `GatewayDecision`; < 100ms overhead; hot-reloadable config; F3/F4/F5 plug in as stages) **[Done]** |
| G1.2 | L | Use case registry (built-in use cases: chat-completion, code-generation, code-review, summarisation, data-analysis, translation, classification, agent-task, mcp-tool-call; custom use case registration; each stores id, name, risk_level, purpose, approved_models, required_controls, owner; `loke use-cases list/add`) **[Done]** |
| G1.3 | L | Risk classification and control gates (three tiers: Low → logging + guardrails + anonymisation; Medium + human-visible preview + cost confirmation; High + mandatory approval + explainability trace + enhanced audit; dynamic escalation when data sensitivity exceeds use case default; colour-coded indicator on every request) **[Done]** |
| G1.4 | M | Accountability and ownership registry (business/technical/risk owner per use case; defaults to user for individual installs; owner metadata on every audit event; no use case active without assigned owner; `loke owners list`; changes logged) **[Done]** |
| G1.5 | M | AI justification requirement (new use case registration requires: purpose, why AI vs simpler alternative, expected value, identified risks; built-in justifications pre-written; suggest simpler paths when AI is unnecessary; enterprise sign-off workflow) **[Done]** |
| G1.6 | M | Kill switch and fallback mode (global: `loke kill-switch on` stops all external AI calls; per-provider, per-use-case, per-agent; graceful fallback messaging; persisted across restarts; audit trail; enterprise remote trigger via policy push) **[Done]** |

## Epic G2: Transparency and Explainability

*Make every AI decision explainable after the fact — not just for compliance, but because users deserve to understand what happened with their data.*

| Story | Size | Summary |
|-------|------|---------|
| G2.1 | L | Decision trace system (captures: original input, PII detected, anonymisation applied, compression applied, risk classification, policy decisions, model selected + why, prompt sent, response received, deanonymisation, final output; `loke trace <id>`; JSON export; agentic workflows trace every step; 90-day default retention) **[Done]** |
| G2.2 | L | "Why this output?" explanation generator (right-click → "Explain this" or `loke explain <id>`; generated locally by SLM from decision trace — no cloud call; plain language; source attribution for RAG responses; confidence indicators; thumbs up/down on the explanation) **[Done]** |
| G2.3 | S | AI content disclosure (all AI responses marked with subtle clear indicator; categories: AI-generated/AI-assisted/AI-summarised/AI-translated; disclosure metadata on copy/export; enterprise-configurable; user-configurable visibility) **[Done]** |

## Epic G3: Operational Monitoring and Incident Management

*Treat AI like a production system with failure modes — because it is one.*

| Story | Size | Summary |
|-------|------|---------|
| G3.1 | L | Output quality monitoring (automated checks: hallucination detection, coherence scoring, relevance scoring; thumbs-down rate tracking per model/use case/period; baseline establishment over 30 days; drift detection alerts; provider comparison; feeds G4 dashboards) **[Done]** |
| G3.2 | L | Incident management workflow (types: pii_leakage_suspected, policy_violation, quality_degradation, provider_outage, cost_overrun, agent_misbehaviour, security_concern; auto-created from monitoring or manual; severity: critical/high/medium/low; post-incident review template; `loke incidents list/create/resolve`; trends in G4) **[Done]** |

---

# VALUE AND GOVERNANCE METRICS

## Epic G4: Metrics, Dashboards, and Reporting

*Live dashboards that show — at a glance — whether the system is staying between the lines, delivering value, and operating safely.*

| Story | Size | Summary |
|-------|------|---------|
| G4.1 | XL | Governance health dashboard (scorecard: privacy %, compliance violations, risk tier breakdown, ownership coverage, open incidents; trend charts 7d/30d/90d; drill-down; red/amber/green status; auto-refresh in browser mode; `loke dashboard` in CLI; PDF export; customisable thresholds) **[Done]** |
| G4.2 | L | Value realisation dashboard (financial: total cost, cost saved by compression/caching/local routing/model selection; privacy: PII intercepted by type, data that never left device; efficiency: local request %, cache hit rate, compression ratio; "What would have happened without loke?" comparison; personal milestones) **[Done]** |
| G4.3 | M | Provider performance scorecard (per provider/model: quality thumbs ratio, latency p50/p95/p99, cost per useful response, availability, error rate; comparative view; trend lines; recommendations; anomaly alerts; signals feed back into F5.3 router) **[Done]** |
| G4.4 | L | Regulatory compliance reporting (templates: EU AI Act, Australian Privacy Act, HIPAA, GDPR, general enterprise audit; evidence attachment to audit events; `loke report generate --template eu-ai-act --period Q1-2026`; PDF output; scheduled generation; draft → review → approve → distribute; no PII or prompt content in reports) **[Done]** |
| G4.5 | M | Cost forecasting and budget planning (forecast based on trailing 7d/30d/90d; scenario planning: current rate / model swap / local routing increase; budget alerts; optimisation suggestions with $ estimates; subscription utilisation tracking; multi-subscription balancing) **[Done]** |
| G4.6 | M | Inference tier utilisation dashboard (per tier: request count and %, average response time, average quality rating from thumbs up/down, models used and frequency, tok/s achieved, cloud API cost comparison; trend charts of tier usage over time; quality comparison for same task types at different tiers; overnight window utilisation; hardware utilisation per tier — GPU%, RAM%, disk I/O; total cost avoided by running large models locally) **[Done]** |

---

# AGENTIC AI

## Epic AG1: Agent Framework

*Lightweight AI agents that run small, well-defined tasks — on schedules, from triggers, or on demand — all governed by the same accountability controls as interactive use.*

| Story | Size | Summary |
|-------|------|---------|
| AG1.1 | L | Agent definition and registration (YAML/TOML format: name, description, schedule/trigger, model_preference, risk_level, permissions, max_cost_per_run, requires_approval, owner; auto-registered in G1.2 use case registry; deny-by-default permissions; validation before activation; `loke agents create/list/enable/disable`) **[Done]** |
| AG1.2 | L | Agent scheduling and triggers (cron schedules; file change triggers; webhook triggers on local endpoint; MCP event triggers; manual via `loke agents run` or UI button; chained triggers A→B; debouncing with configurable cooldown; missed schedule policy; all triggers logged) **[Done]** |
| AG1.3 | XL | Agent execution sandbox (permission enforcement: file read/write only to declared paths; MCP tool restriction; model restriction; cost limit enforcement with pause-and-alert; configurable time limit default 5 min; output staging with optional auto-commit for low-risk; no arbitrary network calls; agent isolation; all G1 governance controls apply) **[Done]** |
| AG1.4 | L | Agent observability and debugging (status: running/idle/scheduled/paused/errored/disabled; run history with timestamp/trigger/duration/tokens/cost/outcome; live streaming log; step-through debug mode; G2.1 trace on every action; error handling with pause after N failures; metrics feed G4) **[Done]** |
| AG1.5 | L | Agent templates and marketplace (built-in: daily digest, code review assistant, expense categoriser, meeting prep, documentation updater, security scanner; `loke agents install <template>`; full YAML editing after install; community export/sharing; templates include governance metadata) **[Done]** |
| AG1.6 | L | Agent-to-agent communication (output triggers another agent; governed structured data handoff; handoff logged; circular dependency detection; declarative pipeline YAML: A→B→C; pipeline-level cost/time/risk limits; user notification on pipeline completion) **[Done]** |
| AG1.7 | M | Agent latency tolerance and model tier selection (`latency_tolerance: instant|patient|background` field in agent YAML; `model_preference: largest-local` tells router to use most capable model achievable at declared tier even with heavy offloading; execution time budgeted with confirmation required for long-running agents; Background agents preferentially scheduled during low-usage windows; fallback to largest feasible model logged if preferred model unavailable) **[Done]** |
| AG1.8 | L | Overnight batch processing pipeline (`loke overnight start` enters low-power full-utilisation mode for Background queue; user-configurable overnight window (e.g. 11pm–7am); full RAM/GPU allocation to Background tier during window; morning digest of all agent activity — results, findings, errors, costs; `loke overnight status/plan`; laptop power management — requires AC; interactive session preempts Background jobs within 10 seconds) **[Done]** |

---

# MEMORY PALACE AND AAAK SHORTHAND

*Persistent cross-session memory organised into a navigable palace structure, with AAAK shorthand for efficient context loading. Adapted from the MemPalace architecture (MIT, github.com/milla-jovovich/mempalace) for local-first use. All memory stays on-device, passes through the privacy pipeline, and integrates with governance and audit.*

## Epic M1: Structured Memory System

| Story | Size | Summary |
|-------|------|---------|
| M1.1 | XL | Palace structure implementation (hierarchy: Wings → Halls → Rooms → Closets [AAAK summaries] → Drawers [verbatim] → Tunnels [cross-wing links]; auto-classification by local SLM; manual organisation; `loke memory walk`; SQLite + ChromaDB storage; `loke memory status`) **[Done]** |
| M1.2 | L | Verbatim conversation storage (every turn stored verbatim in drawers, never summarised; classified into wing/hall/room; metadata: timestamp, models, tokens, session ID; pre-anonymisation content stored (stays local); conversation imports from Claude/ChatGPT/Slack exports; configurable retention and storage budget alerts) **[Done]** |
| M1.3 | L | Semantic memory search (`loke memory search "why did we choose Clerk?"`; scoped by wing/hall; returns excerpts with context, source, timestamp, confidence; semantic similarity + palace structure boost; fully local embeddings; < 500ms for 100K drawers; integrated into browser chat panel) **[Done]** |
| M1.4 | L | Automatic context enrichment (before every LLM call: search palace for relevant memories; top-N included as AAAK context; "Added N memories from palace" disclosure; user can disable; relevance threshold configurable; token budget cap default 2000; enrichment passes through anonymisation before cloud LLMs) **[Done]** |
| M1.5 | XL | Knowledge graph with temporal awareness (entity extraction by local SLM; relationship mapping; temporal validity windows — facts have start/end dates; contradiction detection flags for user review; `loke memory facts "who works on project-alpha?"`; `--as-of` time queries; graph visualisation in browser mode; privacy pipeline on any externally-included graph data) **[Done]** |
| M1.6 | L | Agent memory / diaries (each AG1 agent gets a dedicated palace wing; structured diary entries in AAAK after each run; diary loaded as context on startup; searchable; agent-scoped permissions; diary entries feed into project wings; older entries auto-compressed to closets) **[Done]** |

## Epic M2: AAAK Shorthand Integration

*AAAK is compressed English shorthand readable by any LLM without a decoder — not a programming language, not a binary format. Complementary to TOON (F4.1, structured data) and toke (prompt syntax): AAAK specifically optimises natural-language memory and context loading.*

| Story | Size | Summary |
|-------|------|---------|
| M2.1 | L | AAAK encoder/decoder (encoder: natural language → AAAK; e.g. "Priya manages Driftwood: Kai backend 3yr, Soren frontend, Maya infra" → `TEAM: PRI(lead) \| KAI(backend,3yr) SOR(frontend) MAY(infra)`; decoder: AAAK → natural language for human review; 5–30x compression; lossless for structured facts; works with any LLM; configurable compression level; benchmark token savings; integrates with mcp-toke F7.4) **[Done]** |
| M2.2 | L | Layered context loading (L0 ~20 tokens: identity; L1 ~150 tokens: AAAK palace map; L2 ~500 tokens: AAAK active context for current task; L3 variable: deep memory via M1.3 semantic search; startup loads L0+L1 only; L2 on task identification; L3 on-demand; configurable layer sizes; total budget enforced; progressive disclosure of what's loaded) **[Done]** |
| M2.3 | M | AAAK prompt shorthand (users write shorthand: `refactor auth.module \| extract.jwt.validation → separate.util \| keep.backward.compat`; loke expands locally before pipeline; optional — natural language always works; dots/pipes/arrows syntax; user-defined abbreviations via `loke shorthand add`; expanded version shown in pre-send preview) **[Done]** |
| M2.4 | L | Memory mining from external sources (import: Claude exports, ChatGPT exports, Slack JSON, markdown, code repos; mining modes: projects/conversations/general; privacy pipeline scan on import; local SLM processing only; incremental mining; `loke memory mine <path> --mode <type>`; interruptible and resumable; source attribution on mined content) **[Done]** |
| M2.5 | L | Memory MCP server (tools: `memory.search`, `memory.store`, `memory.facts`, `memory.context`, `memory.diary_write`, `memory.diary_read`, `memory.status`; all responses pass through privacy pipeline; access control: search allowed, delete/modify requires explicit permission; auto-registered with F7.3 MCP broker; compatible with Claude Code, Codex, and any MCP-capable tool) **[Done]** |

---

# CROSS-CUTTING

## Epic X1: Documentation & Community

*Documentation, contribution guides, and community infrastructure.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X1.1 | L | **Done** | Project documentation site (Starlight/VitePress, architecture diagrams, versioned, searchable) |
| X1.2 | M | **Done** | Contribution and governance framework (CONTRIBUTING, CODE_OF_CONDUCT, GOVERNANCE, issue/PR templates, DCO) |
| X1.3 | M | **Done** | Security policy and vulnerability disclosure (SECURITY.md, response SLA, threat model, quarterly audits) |
| X1.4 | L | **Done** | Architecture document (layered model, runtime modes, pipeline data flow, package structure, extension point map, storage model, security boundaries, deployment model) |
| X1.5 | M | **Done** | Update threat model for platform layer (HTTP server attack surface, plugin system trust, OAuth token handling, i18n injection, middleware bypass, new trust boundaries) |
| X1.6 | M | **Done** | Update security audit checklist for platform layer (HTTP hardening, plugin sandboxing, OAuth flows, input sanitisation, rate limiting, CSP verification) |

## Epic X2: Research Track

*Academic and technical research outputs.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X2.1 | XL | **Done** | Peer-reviewed research proposal (architecture, benchmarks, privacy analysis, user study design) |
| X2.2 | L | **Done** | TOON benchmark publication (10+ tasks, 5+ models, reproducible scripts) |
| X2.3 | XL | **Done** | Web privacy metadata RFC (data-ai-sensitivity attributes, W3C/IETF submission) |

## Epic X3: Accessibility Platform

*Platform-level accessibility infrastructure — ensures all loke-provided UI meets WCAG 2.1 AA and provides utilities for applications.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X3.1 | M | **Done** | Semantic HTML enforcement and ARIA support (all platform components use semantic elements, ARIA roles/states/properties where semantic HTML is insufficient, labels for all form controls) `[R7.1, R7.2]` |
| X3.2 | M | **Done** | Keyboard navigation framework (every interactive element reachable via keyboard, tab order follows visual order, arrow keys in composite widgets, Escape closes overlays, no mouse-only interactions) `[R7.3]` |
| X3.3 | M | **Done** | Focus management utilities (focus trapping for modals/dialogs, focus restoration on overlay close, programmatic focus on route changes, skip-to-content link as first focusable element) `[R7.4, R7.5]` |
| X3.4 | M | **Done** | Screen reader live regions (aria-live utility function for dynamic changes — page loads, notifications, status updates; polite and assertive priority levels) `[R7.6]` |
| X3.5 | S | **Done** | Colour independence and motion sensitivity (no colour-only state indicators, WCAG 2.1 AA contrast ratios, `prefers-reduced-motion` respected, no essential info via animation alone) `[R7.7, R7.8]` |
| X3.6 | M | **Done** | Automated a11y testing (axe-core integration in test suite, platform components must pass with zero violations, helper function for applications to run a11y checks) `[R7.9]` |

## Epic X4: Testing & Developer Experience

*Test infrastructure, quality gates, and developer tooling that both loke and applications share.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4.1 | M | **Done** | Test utilities (in-memory test databases, test server instances, test config generators, integration mocks — reduce boilerplate for application tests) `[R15.2]` |
| X4.2 | M | **Done** | Quality gate script (single command: lint → format check → dependency audit → unit tests → integration tests → a11y tests → build; fails on any step; used as pre-push hook and CI gate) `[R15.5]` |
| X4.3 | S | **Done** | Watch mode for development (server restart + client reload on file change, fast feedback loop) `[R16.1]` |
| X4.4 | M | **Done** | Scaffold generator CLI (`loke generate migration`, `loke generate route`, `loke generate adapter`, `loke generate locale` — reduces manual boilerplate creation) `[R16.3]` |
| X4.5 | M | **Done** | Debug mode (request/response inspection, database query logging, pipeline stage tracing, route matching details — never enabled in production, activated via config flag) `[R16.5]` |

## Epic X4a: Module-Aware API Handler Compilation

*loke's API handlers (`pages/api/*.tk`) are toke source files that import modules from the core engine (`core.privacy.pipeline`, `core.router`, `shared.types`, etc.). Currently ooke compiles page templates but falls through to a static echo for API handlers because the toke compiler cannot resolve cross-module imports at serve time. This means all API endpoints (`/api/pipeline`, `/api/health`, `/api/models`, etc.) return either ooke's default response or echo the request body — no loke business logic executes.*

**Root cause:** When ooke serves an API route backed by a `.tk` handler, it needs to compile that handler into a callable function. The handler imports other modules via `i=alias:module.path;`, but the compiler has no module search path configured — it can only compile single-file programs. The same gap blocks the test suite (X4b.3).

**Impact:** loke and moke build and serve static pages correctly, but every API call that requires the privacy pipeline, router, model registry, governance gateway, or any core module returns a no-op response. The product is visually complete but functionally inert.

**Dependency:** This requires changes in both toke (module search path, multi-file compilation) and ooke (passing module roots to the compiler when compiling handlers). The `--emit-deps` standalone build pipeline works for single-file programs (proven by the test suite) but not for files with cross-module imports.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.1 | XL | **Done** | **toke: multi-file module resolution** — Add a `--module-path <dir>` flag (repeatable) to toke that tells the compiler where to search for imported modules. When compiling `source.tk` that contains `i=alias:module.path;`, the compiler searches each `--module-path` directory for a file whose `m=` declaration matches `module.path`. Resolves the module's type interface (generates `.tki` if needed) so the importing file can type-check. At link time, compiles all transitively imported modules and links them together. This is the critical missing piece — without it, no multi-file toke program can compile. |
| X4a.2 | L | **Done** | **ooke: pass module paths when compiling handlers** — When ooke compiles an API handler `.tk` file, pass the project's source directories as `--module-path` arguments to toke. For loke, this means: `--module-path packages/core/src --module-path packages/shared/src --module-path packages/browser/src --module-path src`. Read module paths from `ooke.toml` config (new `[build] module_paths = [...]` field). Handlers should compile with full access to the project's module graph. |
| X4a.3 | L | **Done** | **Verify loke API handlers compile and execute** — Once X4a.1 and X4a.2 are complete, verify that all loke API handlers compile with module resolution and return correct responses: `/api/health` (returns loke version, Ollama status, port), `/api/pipeline` (runs privacy pipeline on input text, returns anonymised output), `/api/models` (returns available model list from Ollama), `/api/settings` (returns current config). Test from moke's chat interface — a prompt should flow through the full pipeline and return an LLM response. |
| X4a.4 | M | **Done** | **Verify moke API handlers compile and execute** — Verify moke's API handlers: `/api/health` (proxies to loke health), `/api/feedback` (stores feedback), `/api/memory` (searches memory palace), `/api/datasets` (lists uploaded datasets), `/api/upload` (processes CSV upload), `/api/pipeline` (proxies pipeline call through loke). |

## Epic X4a.5: Core Module Semantic Fixes

*With toke v3 syntax migration complete (562/562 files) and module-aware compilation working (X4a.1–X4a.2), 94 of 168 core modules still fail semantic checks. These are code-level issues — undeclared identifiers, missing imports, type mismatches, and mutability errors — that prevent `.tki` interface generation and block the full module dependency graph from resolving.*

**Root cause:** The v3 migration fixed syntax but not semantics. Many modules reference sum type variants, stdlib functions, or types without proper imports or declarations. Some use `i64` where `i32`/`u32` is expected. Some assign to immutable bindings.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.5.1 | S | **Done** | **Add missing `std.json` imports** — 9 modules call `json.str()`, `json.i64()`, etc. without `i=json:std.json;`. Add the import to: `core.feedback.store`, `core.governance.aigov`, `core.governance.consent`, `core.governance.dsar`, `core.governance.monitoring`, `core.governance.quota`, `core.governance.report`, `core.governance.rulesengine`, `core.storage.syncqueue`. |
| X4a.5.2 | S | **Done** | **Fix `let` → `let mut` bindings** — 12 modules assign to immutable bindings. Add `mut.` prefix: `core.companion.discovery` (n), `core.eval.advisor` (runline), `core.governance.compliance` (result), `core.governance.scorecard` (rows), `core.governance.value` (result), `core.installer.uninstall` (models), `core.installer.updater` (found), `core.mcp.protocol` (items), `core.policy.loader` (sets), `core.privacy.placeholderstore` (result), `core.privacy.presidio` (entities), `core.storage.dashboard` (found). |
| X4a.5.3 | M | **Done** | **Fix type mismatches (`i32`/`u32` vs `i64`)** — 11 modules pass `i64` where `i32` or `u32` is expected (or vice versa). Add explicit casts (`as i32`, `as u32`) in: `core.agents.observability`, `core.governance.forecast`, `core.governance.killswitch`, `core.memory.export`, `core.memory.privacy`, `core.optimiser.llmlingua`, `core.router.intent`, `core.router.latencyrouter`, `core.router.sensitivity`, `core.storage.ephemeral`. Fix `void` return mismatches in `core.governance.policy`, `core.memory.aaak`. |
| X4a.5.4 | M | **Done** | **Add missing imports and type declarations** — Fix undeclared identifiers by adding imports or local type definitions. Missing imports: `core.mcp.discovery` (std.time), `core.memory.decay` (std.math), `core.auth.oauth` (std.crypto), `core.auth.refresh` (std.http), `core.feedback.reporter` (shared.types), `core.pipeline.history` (shared.types). Missing type declarations: `core.models.hardware` ($hwvendor), `core.models.infer` ($inferbackend), `core.models.mlx` ($mlxloaded), `core.models.queue` ($queuedrequest), `core.optimiser.budget` ($budgetperiod), `core.optimiser.toon` ($toontoken), `core.privacy.template` ($templateerr), `core.memory.schema` ($dbconn import from core.storage.db). |
| X4a.5.5 | M | **Done** | **Fix wrong import paths (remaining)** — Modules with incorrect import paths: `core.companion.executor` (companion.channel → core.companion.channel), `core.eval.bench` (providers.dispatcher → core.providers.dispatcher), `core.memory.mining` (memory.aaak → core.memory.aaak). |
| X4a.5.6 | S | **Done** | **Fix duplicate identifier declarations** — 3 modules declare the same identifier twice: `core.agents.sandbox` (readfile), `core.governance.usecases` (usecase), `shared.result` ($ok conflicts with built-in). Rename duplicates or remove redundant declarations. |
| X4a.5.7 | S | **Done** | **Fix `mut` parse errors** — 2 modules have `mut` in expression position where it's not valid: `core.extensions.providerregistry`, `core.installer.pull`. Likely double-mutation from prior automated fix — clean up. |
| X4a.5.8 | S | **Done** | **Suppress warnings / minor fixes** — Handle: `core.agents.overnight` (Python keyword `class`), `core.memory.search` / `core.router.examples` / `loke.browser.workspace.tabs` (value escapes scope — move binding). These are warnings, not errors, but should be cleaned up. |

## Epic X4a.6: Live API Handler Implementations

*loke builds and serves a native binary (X4a.1–X4a.5 complete). **Corrected 2026-09-20: this was false.** Measured against the current toolchain, 58 of 199 modules compile and the test suite has not run. The claim was written while the interface directory held a stale nested tree that toke never read, so modules were type-checked against four-month-old signatures. See F10 and RV1. But the API handlers return stub/placeholder data because the core module functions (`browser.extensions.core`, `core.models.ollama`) have placeholder implementations. This epic implements the real business logic so API endpoints return live data.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.6.1 | M | **Done** | **Implement `browser.extensions.core` state management** — Replace stub getters (`getconfig`, `getrouter`, `getdispatcher`, etc.) with real state. On init: load `ooke.toml` config, create Ollama client, initialise privacy pipeline config with default entity types and detection layers. Store state in a module-level struct initialised once at startup. `getconfig()` returns a struct with `.ollamaurl` (default `http://127.0.0.1:11434`), `.port` (11430), `.datadir`, `.loglevel`. |
| X4a.6.2 | M | **Done** | **Implement `/api/health` — live Ollama check** — The health handler calls `ollama.healthcheck(client)` which should HTTP GET `http://127.0.0.1:11434/api/tags`. Return `{"ok":true,"loke":"0.2.0","ollama":"running"/"stopped","port":11430}`. Use `std.http` GET with timeout. |
| X4a.6.3 | M | **Done** | **Implement `/api/models` — list from Ollama** — GET `http://127.0.0.1:11434/api/tags`, parse JSON response, return model list with name/size. Use `std.http` and `std.json`. |
| X4a.6.4 | L | **Done** | **Implement `/api/pipeline` — proxy to Ollama** — Accept `{text, system_prompt, model}`, POST to `http://127.0.0.1:11434/api/generate` with model and prompt, return response. Privacy pipeline runs first (placeholder pass-through for now). |
| X4a.6.5 | S | **Done** | **Wire moke → loke pipeline** — moke's chat sends to loke's `/api/pipeline`, loke proxies to Ollama, response flows back. Verify end-to-end from moke UI. |

## Epic X4a.7: CORS Architecture Resolution

*Cross-origin issues between moke (:11432) and loke (:11430) have been a recurring problem. The `ooke.toml` `corsorigins = "*"` setting works for preflight (OPTIONS) and actual requests when the Origin header is present, but the browser-side JS health polling still shows connectivity issues. This epic proposes an architectural change to eliminate CORS as a concern.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.7.1 | S | **Done** | **Audit current CORS state** — Document exactly where CORS is configured (ooke.toml, ooke http.c headers), what the browser sees (inspect Network tab), and whether the issue is CORS headers missing on specific routes or a different connectivity problem (e.g. moke's JS fetching wrong URL, health endpoint returning non-JSON). |
| X4a.7.2 | M | **Done** | **Auto-detect same-origin or cross-origin** — `base.tkt` probes `/api/health` as a relative path first. If it returns a valid loke response (has `d.loke` field), sets `window.LOKE_URL = ''` so all templates use relative paths (no CORS). If the probe fails, falls back to `CROSS_ORIGIN_URL = 'http://127.0.0.1:11430'` for dev-mode cross-origin. All templates already use `window.LOKE_URL \|\| 'http://127.0.0.1:11430'` fallback. |
| X4a.7.3 | S | **Done** | **Both approaches work** — Same-origin works when loke serves moke (single port or reverse proxy). Cross-origin works in dev (moke:11432 → loke:11430) with ooke CORS headers. No code changes needed per deployment — auto-detection handles it. |
| X4a.7.4 | S | **Done** | **Verified implementation** — `probeAndResolve()` in base.tkt handles the decision at runtime. `corsorigins` kept in ooke.toml as a safety net for dev mode. Templates use `window.LOKE_URL + '/api/...'` which resolves to either relative or absolute paths. |

## Epic X4b: Archive Legacy Tests & Create New Test Suites

*The v3 migration converted all 562 source files to valid toke v3 syntax. The 170 existing test files (156 loke + 14 moke) were written against the pre-ooke architecture using patterns that no longer compile (v2 test framework references, unresolvable module imports, pre-migration assertion patterns). These tests need to be archived and replaced with clean test suites for loke and moke separately.*

**Blocker:** The toke compiler currently links `tk_web_glue.o` on every build, which requires ooke's db/collections C libraries. A standalone `--no-web-glue` compilation mode is needed in toke before any test binary can be produced. This is being addressed in the toke project. Once resolved, test files can compile to standalone binaries via `tkc --out <binary> <test.tk>`.

**Context:** `std.test` exists in toke's stdlib (`tk_test.c` / `tk_test.h`) and provides `test.assert(cond;msg)`, `test.assert_eq(a;b;msg)`, `test.assert_ne(a;b;msg)`. Test files should follow the convention `f=main():i64` returning 0 for all-pass, non-zero for failure count. The existing `.tkc.md` companion files (156 of them) document the intended test behaviour and can be used as specifications for rewriting.

### Part 1: Archive

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.1 | S | **Done** | **Archive legacy loke test files** — Move the 156 existing test files from `tests/unit/`, `tests/integration/`, and `tests/e2e/` into `_archived-tests/loke/`. Preserve directory structure. These files are syntactically valid v3 but cannot compile due to unresolvable module imports and broken test framework references. Keep the `.tkc.md` companion files alongside their test files — they document intended test behaviour and serve as specs for rewriting. Add a `_archived-tests/README.md` explaining the archive reason (v3 migration, test framework gap) and that companion files contain the canonical test specifications. |
| X4b.2 | S | **Done** | **Archive legacy moke test files** — Move the 14 existing test files from `packages/moke/tests/` into `_archived-tests/moke/`. Same approach: preserve structure, keep companion files, document the archive. The 3 test files we rewrote during migration (`feedback_test.tk`, `memory_test.tk`, `pipeline_panel_test.tk`) are placeholder stubs — archive them with the rest. |

### Part 2: loke Test Suite

*A clean test suite for the loke core engine. Each test file is a standalone `.tk` program that imports only `std.test` and the module under test. Tests are grouped by subsystem. Every test file compiles independently and returns 0 on success.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.3 | L | **Done** | **Privacy pipeline tests** — Write new test files for the privacy subsystem: `test_regex_detector.tk` (email, phone, SSN, credit card, IP, AU TFN/ABN patterns — assert detection and non-detection), `test_ner_detector.tk` (name/place/org detection via local SLM — assert entity extraction from sample texts), `test_placeholder_store.tk` (store placeholder, retrieve, reverse — assert round-trip fidelity), `test_pipeline_orchestrator.tk` (full pipeline: raw text → detect → anonymise → assert no PII in output, assert restoration produces original), `test_guardian.tk` (assert guardian prompt injected into every LLM call). Use `.tkc.md` companion files from archived tests as specifications. Target: 5 test files, each with 10+ assertions. |
| X4b.4 | L | **Done** | **Memory palace tests** — `test_palace_drawers.tk` (store/retrieve/search drawers in wings/halls/rooms), `test_decay.tk` (time-based decay scoring), `test_graph.tk` (entity/relation upsert, traversal), `test_search.tk` (keyword search, relevance scoring), `test_aaak.tk` (shorthand compression levels), `test_export.tk` (JSON/CSV/markdown export, import round-trip). Target: 6 test files. |
| X4b.5 | L | **Done** | **Governance tests** — `test_gateway.tk` (submit request, assert policy decision), `test_rules_engine.tk` (evaluate conditions, AND/OR/NOT), `test_policy_loader.tk` (load from file/URL, merge), `test_incidents.tk` (create/resolve/list), `test_ownership.tk` (assign/get/missing roles), `test_consent.tk` (record/check consent), `test_dsar.tk` (access/erasure requests), `test_kill_switch.tk` (enable/disable/check blocked), `test_scorecard.tk` (compute governance score). Target: 9 test files. |
| X4b.6 | M | **Done** | **Storage tests** — `test_db.tk` (open/migrate/query), `test_settings.tk` (get/set string/int/bool/float), `test_audit.tk` (append/query/export), `test_keychain.tk` (store/retrieve/delete credentials), `test_ephemeral.tk` (store/get/wipe/expire). Target: 5 test files. |
| X4b.7 | M | **Done** | **Model & router tests** — `test_model_registry.tk` (register/find/filter models), `test_model_tiers.tk` (tier config, selection, labels), `test_router.tk` (route request, model selection, cost estimation), `test_sensitivity.tk` (sensitivity levels, risk classification), `test_queue.tk` (enqueue/dequeue/priority). Target: 5 test files. |
| X4b.8 | M | **Done** | **Provider tests** — `test_anthropic.tk` (request building, response parsing), `test_openai.tk` (request building, response parsing), `test_ollama.tk` (health check, chat completion parsing), `test_dispatcher.tk` (provider routing by type). Target: 4 test files. |
| X4b.9 | M | **Done** | **Agent & MCP tests** — `test_agent_types.tk` (type construction, defaults), `test_scheduler.tk` (check due, trigger types), `test_sandbox.tk` (permission checks, file/http access), `test_mcp_protocol.tk` (request/response encoding), `test_mcp_permissions.tk` (tool allow/deny, TOML parsing). Target: 5 test files. |
| X4b.10 | M | **Done** | **CLI & companion tests** — `test_commands.tk` (parse command-line args into command struct), `test_session.tk` (create/activate/find sessions), `test_init.tk` (environment checks), `test_companion_discovery.tk` (discover/confirm/reject devices), `test_exo.tk` (health check, model list). Target: 5 test files. |
| X4b.11 | M | **Done** | **Optimiser tests** — `test_toon.tk` (JSON→TOON encoding/decoding round-trip, savings measurement), `test_budget.tk` (limit checking, period matching), `test_profiler.tk` (column type inference, PII candidate detection). Target: 3 test files. |
| X4b.12 | S | **Done** | **Integration tests** — `test_pipeline_api.tk` (HTTP POST with JSON body → assert anonymised response, assert audit trail written), `test_health_api.tk` (health endpoint returns status/version), `test_mcp_roundtrip.tk` (tool discovery → invocation → response). These require a running loke instance; document setup in test file comments. Target: 3 test files. |

### Part 3: moke Test Suite

*A clean test suite for moke. Each test covers a moke-specific feature using moke's own types and modules.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.13 | M | **Done** | **moke core tests** — `test_cost_comparison.tk` (estimate cloud cost, compute savings, accumulate session), `test_tier_visualiser.tk` (tier stats construction, JSON serialisation), `test_console_log.tk` (append log entry, session log structure), `test_profiler.tk` (column type inference, PII candidate, format profile output), `test_ddl.tk` (dashboard card construction, JSON serialisation, validation). Target: 5 test files. |
| X4b.14 | M | **Done** | **moke feature tests** — `test_streaming.tk` (session event tracking, JSON output), `test_governance.tk` (regulatory preset lookup, risk classification), `test_companion_simulator.tk` (cluster status, model list), `test_routing_explainer.tk` (decision trace formatting), `test_agents_status.tk` (agent status construction, panel state). Target: 5 test files. |
| X4b.15 | S | **Done** | **moke pipeline panel tests** — `test_pipeline_stages.tk` (all 9 stages defined, labels, status symbols), `test_emitter.tk` (start/complete/skip/error stage events, finalise run with totals), `test_history.tk` (add run, recent, evict, last). Rewrite from archived `pipeline_panel_test.tk` companion spec. Target: 3 test files. |

### Part 4: Infrastructure

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.16 | M | **Done** | **Test runner script** — Write a `scripts/run_tests.sh` that discovers all `*_test.tk` files under `tests/` and `packages/moke/tests/`, compiles each with `tkc --out <tmp> <file>`, runs the binary, captures exit code, and reports pass/fail summary. Handles the `--no-web-glue` flag (or equivalent) once available in toke. Supports `./scripts/run_tests.sh tests/unit/privacy/` for subset runs. Exit code = total failures. |
| X4b.17 | M | **Done** | **CI integration** — Add test runner to GitHub Actions CI pipeline. Run on every push and PR. Fail the build on any test failure. Report results as structured JSON artefact. Add test status badge to README. |
| X4b.18 | S | **Done** | **Test coverage map** — Document which source modules are covered by which test files. Output as `docs/test-coverage.md` with a table: source module path, test file(s), assertion count, last verified date. Identify untested modules. Target: >80% of source modules have at least one test file. |

## Epic X4c: Companion Documentation Audit

*Every `.tk` source file should have a companion `.tkc.md` file — a one-paragraph description of the module's purpose, dependencies, and key exports. The archived tests have 514 companion files; the 406 active source modules have zero. This epic audits the gap and generates the missing companions.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4c.1 | S | **Done** | **Audit companion coverage** — Script that scans all `.tk` files (excluding `test_*` and `_archived-tests/`) and reports which have a sibling `.tkc.md` and which don't. Output as a checklist to `docs/companion-coverage.md` with counts per package: browser (34), moke (61), core (168), cli (26), mcp-toke (4), mcp-broker (6), shared (5), src (102). Total: 406 missing. |
| X4c.2 | M | **Done** | **Generate core companions** — Create `.tkc.md` for all 168 `packages/core/` modules. Each file: one paragraph describing purpose, key functions/types exported, and direct dependencies (imports). Follow the format established in the archived companions. |
| X4c.3 | S | **Done** | **Generate src companions** — Create `.tkc.md` for all 102 `src/` modules. Same format as X4c.2. |
| X4c.4 | S | **Done** | **Generate moke companions** — Create `.tkc.md` for all 61 `packages/moke/` modules. |
| X4c.5 | S | **Done** | **Generate browser companions** — Create `.tkc.md` for all 34 `packages/browser/` modules (loke API handlers, serve entry point, handler registry). |
| X4c.6 | S | **Done** | **Generate remaining companions** — Create `.tkc.md` for cli (26), mcp-toke (4), mcp-broker (6), shared (5). mcp-broker already has archived companions that can be referenced for content. |
| X4c.7 | S | **Done** | **Verify 100% coverage** — Re-run audit script from X4c.1, confirm 406/406 covered. Update `docs/companion-coverage.md` with final status. |

## Epic X5: Feedback System

*Extends the feedback architecture from the design principles document with specific implementation stories. The thumbs up/down widget is a first-class feature on every AI interaction, governance decision, warning, and agent output.*

| Story | Size | Summary |
|-------|------|---------|
| X5.1 | L | Universal feedback widget (thumbs-up/down on every AI output, governance decision, warning, and agent result; browser: icon adjacent to output; CLI: `[y/n/comment]` prompt or `loke feedback <id> --down "comment"`; thumbs-down opens inline comment box; stored locally with feature_area, model, use case, risk level — no PII, no prompt content; opt-in submission with privacy pipeline (F3) anonymisation) **[Done]** |
| X5.2 | M | Feedback pipeline to development (submitted feedback → structured GitHub Issues; auto-tagged by feature area; auto-prioritised by volume; deduplication and theme grouping; status tracking visible to user; resolution notification in update; "You asked, we built" changelog links; metrics in G4 dashboards) **[Done]** |
| X5.3 | L | Feedback-driven learning loops (thumbs-down on wrong model → RouteLLM retraining signal; false-positive PII → reduce detection sensitivity for that pattern; high thumbs-down on a warning type → sensitivity review; agent diary includes feedback received; compression tuning from quality signals; all adjustments reversible; local only — no cross-user data sharing; `loke learned` shows adaptations) **[Done]** |

## Epic W1: Website — loke.tokelang.dev

*Public-facing website explaining what loke is, its relationship to toke, and how to get involved.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| W1.1 | M | **Done** | Astro/Starlight site scaffolding (match tokelang.dev style, blue title colour, deploy to loke.tokelang.dev) |
| W1.2 | S | **Done** | Homepage hero section (one-liner, core philosophy, animated pipeline diagram) |
| W1.3 | M | **Done** | "How It Works" page (operating modes, pipeline stages, data flow diagrams) |
| W1.4 | M | **Done** | "Key Components" page (privacy, optimisation, routing, MCP, companion devices) |
| W1.5 | S | **Done** | "Relationship to toke" page (toke ecosystem, toke MCP server, link back to tokelang.dev) |
| W1.6 | S | **Done** | "Get Involved" page (GitHub repo link, contributing guide, community channels) |
| W1.7 | S | **Done** | Nginx configuration for loke.tokelang.dev subdomain on production server |

---

# WRAPPER PROJECT SCOPE

*The following requirements from the platform requirements document are domain-specific or application-level concerns. They should be implemented in the application built on loke, not in loke itself. loke provides the extension points; the wrapper provides the implementation.*

| Requirement | Why it's wrapper scope | loke provides |
|---|---|---|
| **R8.3 — Calendar integration** (Microsoft Graph adapter, list/create/update/delete events, free/busy) | Domain-specific — not every loke application needs calendar. | P5.1 integration adapter interface + P5.2 OAuth 2.0 flow. Wrapper implements the calendar adapter. |
| **R8.4 — Conferencing integration** (Teams/Zoom meeting links, recordings, transcripts) | Domain-specific. | P5.1 adapter interface. Wrapper implements conferencing adapters. |
| **R9.2 — Multi-timezone display** (simultaneous timezone comparison) | Meeting-planning UX, not core to privacy/LLM proxy. | P4.3 locale-aware date/time formatting. Wrapper builds the multi-tz UI. |
| **R9.3 — Meeting planner** (timezone overlap grid, working hours, participant availability) | Productivity-app feature. | UTC storage (F6.1), Intl APIs (P4.3). Wrapper builds the planner. |
| **R9.4 — InterPlanet timezone provider** | Novelty/future-proof feature, not core. | P4.3 uses standard Intl.DateTimeFormat. Wrapper implements custom provider. |
| **R10.1–R10.3 — P2P metadata sync, sync status, conflict resolution** | Multi-user collaboration beyond loke's local-first single-user model. F8 companion devices cover compute offload, not data sync. | F8 companion device infrastructure (mDNS, TLS). Wrapper builds sync protocol and conflict resolution on top. |
| **R11.3 — Central notifications** (policy changes, announcements from central source) | Enterprise distribution concern. | P3.8 notification system. Wrapper pushes notifications from its central endpoint. |
| **R11.4 — Central authentication** (each install authenticates against configurable endpoint) | Enterprise deployment concern. | P1.3 middleware pipeline with pluggable auth. Wrapper implements the auth adapter. |
| **R14.3 — Enhancement request form** (structured feature request with use case, priority) | Application-level UX, not platform infrastructure. | A5.1 issue reporting form pattern. Wrapper extends with enhancement-specific fields. |

### Timezone note

loke stores all timestamps in UTC (F6.1) and uses `Intl` APIs for display formatting (P4.3). R9.1 (UTC throughout) and R9.5 (relative time) are covered by P4.3. The wrapper is responsible for any multi-timezone comparison UI, meeting planning, or custom timezone providers.

### Multi-user note

loke is local-first and single-user by design. The companion device support (F8) provides secure device-to-device communication for compute offload. If the wrapper needs multi-user data sync, it should build on F8's mDNS discovery and TLS channel, implementing its own sync protocol, conflict resolution, and metadata scope. loke's F6.6 sync queue provides the persistent outbound queue primitive.

---

# DEMO LAYER — moke

*moke is a data analysis demo application built on loke, demonstrating the extension API (P2.6–P2.8) and showing what a domain-specific application looks like. moke is a toke/ooke package at `/packages/moke/` that imports from `core.*` and adds its own pages, data, and pipeline stages without forking any loke source. It is the reference implementation of loke's extensibility pattern.*

*The original moke was a Node.js/Express prototype (`/moke/`) that proved the schema-first data protocol, local compute engine, dashboard generation, and Insight Lab concepts. The toke moke re-implements all DONE features from that prototype as a first-class ooke application.*

---

## Epic MK1: Core Data Analysis App

*The base moke experience: load a sensitive dataset, have loke anonymise it schema-first (no raw rows to the LLM), ask questions, see answers.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK1.1 | L | **Done** | ooke package scaffold (`packages/moke/ooke.toml`, extension init hook, registers with loke gateway; `moke` command entry point; browser mode on port 11432 alongside loke on 11430) |
| MK1.2 | M | **Done** | Dataset loader (CSV, Excel .xlsx, paste CSV/TSV; PapaParse-equivalent in toke via `std.csv`; first-5-row preview before commit; drag-drop upload handler; stores in session — never persisted) |
| MK1.3 | L | **Done** | Schema-first data protocol hook (P2.6 hook registered `before_anonymise`; intercepts requests containing raw tabular data; extracts column names, types, stats (mean/min/max/nulls/sample 3 values); replaces raw data with TOON-compressed schema profile; raw rows stay local; hook enforced via P2.8 governance rule — blocks any prompt where raw row data detected) |
| MK1.4 | L | **Done** | Local compute engine (15 operations: count, sum, avg, min, max, group, timeseries, topN, distribution, correlate, percentile, countBy, latest, distinct, join; LLM requests computations via structured JSON query; moke executes locally against in-memory dataset; results fed back to LLM as next turn; no raw data ever sent) |
| MK1.5 | M | **Done** | Data profiler (auto-detect column types: numeric/categorical/datetime/boolean/text; compute per-column stats; identify cardinality; detect PII columns by name pattern; produce compact TOON profile; shown in dataset sidebar) |
| MK1.6 | M | **Done** | Sensitivity classification UI (PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED selector on dataset load; classification propagates to loke governance gateway as `sensitivity` field in `$eval_context`; colour-coded badge on all dataset views; RESTRICTED forces local-only routing via P2.7 custom provider) |
| MK1.7 | M | **Done** | Pipeline console (real-time stage-by-stage log: schema extraction → profile → query dispatch → local compute → result injection → LLM call → response; colour-coded stages; expandable detail per stage; matches A4.2 panel style) |
| MK1.8 | M | **Done** | Confirmation modal (human-in-the-loop before every LLM call; shows: schema profile being sent vs original data stayed local; PII summary from loke pipeline; entity count; approve/edit/cancel; "don't ask again for this session") |

## Epic MK2: Insight Lab (Local ML Engine)

*In-browser ML analysis with zero data egress — cluster, detect anomalies, correlate, all on the local dataset.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK2.1 | L | **Done** | Insight Lab engine in toke (k-means clustering: configurable k, convergence detection, cluster assignment, centroid output; Z-score anomaly detection: per-column, configurable threshold, anomaly list with row index and score; IQR outlier detection: Q1/Q3/IQR per column, lower/upper fence, outlier classification; Pearson correlation matrix: all numeric column pairs, r value and p-value approximation; all operations on in-memory dataset — no network) |
| MK2.2 | M | **Done** | AI-assisted analysis proposal (LLM receives schema profile only; proposes 3-5 relevant ML analyses with column selection and params; e.g. "K-means on spend/frequency columns to segment customers"; fallback to heuristic proposals if LLM unavailable: numeric column count → suggest clustering, datetime + numeric → suggest timeseries; user selects which to run) |
| MK2.3 | M | **Done** | Animated ML processing screen (step-by-step progress: Loading data → Running algorithm → Computing results → Preparing visualisation; named stage display with elapsed time; real computation feedback — not fake delay; "complete" reveal with result summary card) |
| MK2.4 | L | **Done** | Insight Lab → Dashboard hand-off (ML results converted to Dashboard Definition Language (DDL); scatter chart with cluster colouring added for clustering results; anomaly table for anomaly detection; correlation heatmap for Pearson matrix; rendered in Dashboard view as a new dashboard card set) |

## Epic MK3: Dashboard Generation

*LLM-driven dashboard layout: the LLM defines what to show (titles, metrics, charts, tables), moke's local compute engine fetches the numbers, client renders.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK3.1 | L | **Done** | Dashboard Definition Language (DDL) (JSON schema for LLM to define dashboards: title, summary, and cards array; card types: `metric` (label, value, delta, trend), `chart` (type: line/bar/pie/area/scatter, title, x/y columns, filter), `table` (title, columns, sort, limit), `text` (markdown prose), `list` (title, items); DDL validated before rendering; stored per session for replay) |
| MK3.2 | L | **Done** | Multi-turn dashboard flow (Phase 1: LLM receives schema profile → returns DDL with compute queries; Phase 2: moke resolves each query via local compute engine; Phase 3: resolved DDL with actual values rendered as dashboard; follow-up prompts refine specific cards; "Refine this chart" → LLM receives current DDL + user instruction → updated DDL) |
| MK3.3 | M | **Done** | Dashboard renderer (renders DDL cards client-side; Chart.js for charts (line, bar, pie, area, scatter with cluster colouring); metric cards with delta arrows and trend sparklines; responsive 2/3/4 column grid; export dashboard as PNG or JSON DDL; "Copy DDL" for sharing the layout definition) |
| MK3.4 | M | **Done** | Dashboard persistence and templates (save current DDL as named template; re-run template against new dataset with matching schema; `loke memory store` integration — dashboard templates stored in memory palace as structured facts; list/load/delete templates) |

## Epic MK4: Demo Datasets

*All original moke demo datasets ported to toke as data modules — Australian open data plus synthetic project datasets.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.1 | L | **Done** | Australian open data datasets (6 datasets, ~1000 rows each: Medicare Benefits Schedule claims (26 cols, patient IDs, procedure codes, costs); NSW Public Schools (22 cols, school IDs, ATAR, enrolment, LBOTE%); Opal card tap data (24 cols, card tokens, journey times, fares); Sydney Water quality readings (23 cols, sensor IDs, turbidity, chlorine, pH); NSW Land Registry property transactions (25 cols, titles, addresses, prices); ABS employment by occupation (22 cols, ANZSCO codes, salaries, regions); all datasets have deliberate PII seeded in free-text fields for demo purposes) |
| MK4.2 | M | **Done** | IT Server Hardware project (4 linked datasets: server inventory (48 servers, specs, purchase date, warranty), performance metrics (CPU%, RAM%, disk I/O time series), network topology (switch/VLAN/port assignments), user-server assignments (user accounts, access levels); Banksia Digital SYD/MEL data centres; deliberate anomalies: 3 servers at >95% CPU, 2 servers with expired warranties, 1 misconfigured VLAN) |
| MK4.3 | M | **Done** | IT Web Platform project (6 linked datasets: user accounts (350 users), orders (1900 orders, statuses, values), web traffic (sessions, bounce rate, conversion), incidents (22 P1-P3 incidents), customer feedback (NPS scores, verbatim), shipping events (courier, SLA breach flags); Wattle & Co fictional e-commerce; deliberate anomalies: 22 high-value orders with mismatched shipping, 1 recurring P1 incident pattern) |
| MK4.4 | M | **Done** | Customer Intelligence dataset (392 synthetic customers, 4 natural clusters: budget shoppers / loyal mid-tier / occasional big spenders / inactive; 22 deliberate anomalies: 5 whale accounts, 7 suspected fraudsters, 4 ghost accounts, 6 luxury category buyers; 18 columns: customer_id, age, region, tenure_days, ltv, orders_ytd, avg_order_value, category_affinity, nps_score, churn_risk, last_purchase_days, support_tickets, email_domain, payment_method, referral_source, pii_name, pii_email, pii_phone) |
| MK4.5 | S | **Done** | Dataset selector UI (landing screen lists all built-in datasets with description, row count, column count, sensitivity level, and demo scenario; or upload own CSV/Excel/paste; grouped by type: Government Open Data / IT Operations / Customer Intelligence / Your Data) |

## Epic MK4.6: UX Overhaul — Workspace, Navigation, and Demo Experience

*The moke UI needs a significant UX improvement to feel like a professional data analysis platform. Analysis view shows raw CSV instead of tables, navigation loses state between views, Insight Lab shows meaningless clusters, and there's no project/workspace concept for managing multiple datasets and artefacts.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.6.1 | M | **Done** | **Analysis view: data table instead of raw CSV** — Replace the raw CSV/text display with a proper HTML table. Show schema panel (collapsible) with column names, types, sensitivity tags. Show active dataset info (name, row count, columns). Make pipeline trace collapsible. Make sidebar menu collapsible on mobile. |
| MK4.6.2 | M | **Done** | **Preserve chat history across view switches** — When navigating Analysis → Dashboard → Analysis, restore the chat history. Store messages in sessionStorage. On view load, re-render stored messages including any rendered charts. |
| MK4.6.3 | L | **Done** | **Project workspace with asset directory** — Add a workspace/project concept: user can upload/select multiple datasets into a project. All artefacts (chats, dashboards, insight results, reports, generated datasets) are stored in a project asset directory. Sidebar shows project assets tree. Assets persist in sessionStorage/localStorage. |
| MK4.6.4 | L | **Done** | **Rich demo datasets with guided prompts** — For each built-in dataset, provide 3-5 suggested prompts per screen (Analysis, Dashboard, Insight). Dataset selector shows preview of what each demo produces. Prompts are dataset-specific (e.g., Medicare: "Show top 10 specialties by cost", Water Quality: "Alert on pH below 6.5"). No canned results — all go through loke pipeline. |
| MK4.6.5 | M | **Done** | **Richer dataset schemas** — Expand demo datasets with more columns, derived fields, and relationships. Add data types (numeric, categorical, date, boolean, pii). Add column descriptions. Schema display groups columns by type with icons. |
| MK4.6.6 | M | **Done** | **Insight Lab improvements** — Replace generic "Cluster 1/2/3" with meaningful cluster labels derived from the data (e.g., "High-value loyal customers", "Budget occasional shoppers"). Show cluster characteristics, outlier details, and statistical summaries. Use the LLM to generate human-readable insight narratives. |
| MK4.6.7 | S | **Done** | **Collapsible UI panels** — Schema, pipeline trace, sidebar nav, debug panel all collapsible with smooth animation. Remember collapse state in sessionStorage. Default: schema collapsed, pipeline collapsed, sidebar expanded. |
| MK4.6.8 | S | **Done** | **Dataset directory and multi-select** — Allow selecting multiple datasets in a project. Show a dataset directory panel listing all loaded datasets with status (loaded/not loaded). Click to switch active dataset. Upload adds to directory. |

## Epic MK4.7: Privacy Pipeline Visibility & Governance Demo

*loke's core value proposition — privacy, governance, and transparency — is invisible in the current moke demo. Users see text responses but not what loke did to protect them. This epic makes the pipeline tangible: PII detection counts, anonymisation evidence, sensitivity classification, routing decisions, cost awareness, and human-in-the-loop confirmation.*

**Why this matters:** Without visible privacy features, moke is just another chat-with-data UI. With them, it demonstrates what makes loke unique — the user sees their data being protected in real time.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.7.1 | L | **Done** | **Privacy detection display in pipeline trace** — When loke returns a response, show PII detection results in the pipeline trace: entity count by type (names, emails, phones, etc.), which privacy layers detected them (regex, NER, SLM), confidence scores. Requires loke's `/api/pipeline` response to include `entities_found`, `entity_types`, `sensitivity`, `detection_layers` fields. Update pipeline handler to populate these from the privacy filter run. Display in the collapsible pipeline trace panel with colour-coded entity badges. |
| MK4.7.2 | M | **Done** | **Sensitivity classification badge and routing explanation** — Prominent sensitivity badge (PUBLIC green / INTERNAL amber / CONFIDENTIAL orange / RESTRICTED red) on every response. Below the badge, one-line routing explanation: "CONFIDENTIAL → routed to local Ollama (data stays on device)" or "PUBLIC → routed to Claude Sonnet 4 (fastest, $0.003)". Show "Could run locally?" advisor when cloud model was used. |
| MK4.7.3 | L | **Done** | **Human-in-the-loop confirmation modal** — Before each LLM call, show the confirmation modal (confirm.tkt already exists). Display: schema profile being sent (not raw data), PII summary from pipeline, entity count, sensitivity classification, target model/provider, estimated cost. Buttons: Approve / Edit prompt / Use local model / Cancel. Configurable: can be disabled in settings for trusted workflows. |
| MK4.7.4 | M | **Done** | **Real pipeline stages in console** — Replace simulated `setTimeout` stages with actual pipeline timing from loke's response. Show real stages: Schema Extract → Privacy Filter (N entities, Xms) → Token Optimise (Y% saved) → Route (model, reason) → LLM Call (provider, Xms) → Restore (placeholders replaced). Each stage shows duration and outcome. Failed stages show red with error detail. |
| MK4.7.5 | M | **Done** | **Cost and token tracking** — Show token counts (in/out) and cost per request in the pipeline trace. Running session totals in the sidebar: "Session: 12 requests · 4,230 tokens · $0.0127". Compare local vs cloud cost: "This request: $0.003 (Claude) — would be free locally". Monthly savings estimate visible in governance dashboard. |
| MK4.7.6 | S | **Done** | **Anonymisation evidence view** — In the detail/debug panel, show before/after: "Original: john.smith@example.com → Sent: [EMAIL_1]". Show each entity with its placeholder. For demo: use the dataset's PII columns (patient_name, medicare_number etc.) to demonstrate real anonymisation. Never show the mapping in the audit trail — only in the user's local session. |
| MK4.7.7 | S | **Done** | **Feedback capture** — Thumbs up/down on every response stores to localStorage: `{timestamp, requestId, vote, comment, model, provider}`. Thumbs-down opens lightweight comment box. Show feedback count in settings. Export as JSON for development review. |

## Epic MK4.8: Dashboard & Insight Lab End-to-End

*The Dashboard tab and Insight Lab need to work as complete demo flows — from dataset selection through LLM-guided design to rendered interactive output.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.8.1 | M | **Done** | **Dashboard tab Phase 1-2-3 pipeline working** — Dashboard tab's generate flow: Phase 1 (LLM designs dashboard via loke pipeline — handle `anthropic_raw` response format), Phase 2 (local compute resolves queries against loaded dataset rows), Phase 3 (render Chart.js charts). Fix the `extractJSON` → `resolveQueries` → render pipeline end-to-end. Test with each built-in dataset. |
| MK4.8.2 | M | **Done** | **Dashboard demo prompts per dataset** — On the Dashboard tab, show dataset-specific dashboard suggestions. Medicare: "Claims by specialty and month", "Cost distribution by state". Water Quality: "pH trends by location", "Alert frequency heatmap". Clicking a suggestion auto-fills and generates. |
| MK4.8.3 | L | **Done** | **Insight Lab meaningful results** — Replace generic "Cluster 1/2" labels with LLM-generated descriptions. Flow: (1) Auto-profile dataset columns, (2) Send schema to LLM asking "propose 3 analyses", (3) Run local ML (k-means, z-score, correlation), (4) Send results back to LLM for narrative interpretation, (5) Display with human-readable labels and visualisations. Each cluster shows: label, size, key characteristics, representative rows. |
| MK4.8.4 | S | **Done** | **Insight Lab demo configs per dataset** — Pre-configured analysis settings per dataset: Customer Intelligence → k=4 clustering on spend/frequency, Medicare → anomaly detection on benefit_paid, Water Quality → correlation matrix on chemical readings. One-click to run with sensible defaults. |
| MK4.8.5 | M | **Done** | **Dashboard export** — Export rendered dashboard as PNG (html2canvas already loaded), JSON DDL (the chart definition), or shareable link (encode DDL in URL hash). Export button on dashboard header. |
| MK4.8.6 | S | **Done** | **Dashboard templates** — Save/load dashboard configurations. Store DDL in localStorage with name. Template selector dropdown on dashboard page. Share templates between datasets. |
| MK4.8.7 | M | **Done** | **Semantic colour coding for chart values** — Dashboard charts should colour-code data values by semantic meaning when grouping by categorical columns. Three tiers: (1) **Known-value matching** — pattern-match group labels against a built-in dictionary: negative/warning/error terms (failed, critical, expired, breach, overdue, rejected, blocked, offline, down, high-risk, P1, RESTRICTED) → red; positive/success terms (passed, healthy, active, approved, resolved, online, up, compliant, low-risk, PUBLIC) → green; neutral/missing terms (unknown, null, n/a, other, pending, none, unclassified) → grey. (2) **LLM-assisted** — when the LLM generates DDL, it can nominate `"colour": "red"/"green"/"amber"/"grey"` per data series based on the question context (e.g., "show servers with expired warranties" → expired = red, valid = green). Add `colour` as an optional field in the DDL card schema. (3) **Local pattern fallback** — for values not in the dictionary and no LLM hint, run a simple client-side classifier: numeric ranges (high = amber/red, low = green for metrics like CPU/error rate; inverted for metrics like uptime/availability), boolean (true = green, false = red), status-like strings (regex against common status patterns). Implement the colour map as a JS object in `dashboard.tkt` with the dictionary and pattern matcher. Chart.js `backgroundColor` array populated per data point. |

## Epic MK4.9: Data Experience & Multi-Dataset Workspace

*Transform moke from a single-dataset tool into a project workspace where multiple datasets, analyses, dashboards and conversations are managed as a collection of assets.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.9.1 | M | **Done** | **Data profiler on load** — When a dataset is loaded, automatically profile all columns: detect type (numeric/categorical/date/boolean/text), compute stats (min/max/mean/median/stddev for numeric; cardinality/top-5 for categorical; date range for dates), identify PII columns by name pattern (name, email, phone, ssn, dob, address). Display as a rich schema card with sparklines for numeric distributions. |
| MK4.9.2 | L | **Done** | **Project workspace** — Sidebar shows a project asset tree: Datasets (loaded CSVs), Conversations (saved chats), Dashboards (saved DDLs), Insights (saved analysis results), Reports (exported summaries). Click any asset to open it. Assets persist in localStorage. New project / open project / rename. Default project created on first visit. |
| MK4.9.3 | M | **Done** | **Multi-dataset directory** — Load multiple datasets into the same project. Dataset directory panel in sidebar shows all loaded datasets with row count, column count, sensitivity badge. Click to switch active dataset. Cross-dataset references in chat: "Compare Medicare claims with Water Quality readings". Upload adds to the directory. |
| MK4.9.4 | S | **Done** | **Richer dataset schemas** — Add column descriptions to built-in datasets (e.g., `benefit_paid: "Amount reimbursed by Medicare for this service"`). Show descriptions in schema preview tooltip. Add relationships between datasets in multi-dataset projects (e.g., server_inventory.rack_id links to network_topology.rack_id). |
| MK4.9.5 | M | **Done** | **Governance dashboard page** — Wire the governance.tkt page with real data from loke. Show: total requests today, PII entities detected, local vs cloud ratio, cost this session, top triggered privacy rules, model usage breakdown. Pull from `/api/savings` and session-local counters. Refresh on interval. |
| MK4.9.6 | S | **Done** | **Settings page improvements** — Show masked API key status (configured/not set with last-4 chars). Test connection button for each provider. Show current routing preference. Session memory toggle. Export/import settings. |


## Epic MK4.10: Advanced Data Type Detection

*The data profiler should detect types beyond numeric/categorical. Detection follows a priority cascade — try the most specific type first, fall back to generic. Users can override any detection via the schema panel dropdown.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.10.1 | M | **Done** | **Date/datetime detection + boolean detection + user override** — Detect ISO dates (YYYY-MM-DD), booleans (true/false/yes/no/0/1). Type override dropdown in schema panel persists to sessionStorage. Date columns show range (min→max). |
| MK4.10.2 | M | **Done** | **Advanced type cascade** — Detection order (most specific first): (1) PII by column name (email/phone/name/ssn/dob/address/medicare), (2) Email by regex, (3) Phone by regex, (4) URL by regex, (5) Currency (\.NN pattern), (6) Percentage (NN.N% pattern), (7) ID/key (unique values = row count, often first column), (8) Boolean, (9) Datetime (ISO, AU dd/mm/yyyy, US mm/dd/yyyy, timestamps), (10) Integer (no decimal), (11) Float (has decimal), (12) Categorical (low cardinality text), (13) Free text (high cardinality text, long values). Each type stores relevant stats (e.g., currency: min/max/sum, datetime: range, ID: uniqueness %). |
| MK4.10.3 | S | **Done** | **Type-specific schema display** — Each type gets a distinct icon/colour in the schema panel. Date: calendar icon, range. Currency: dollar icon, sum/mean. Percentage: percent icon. Email/Phone: PII lock. ID: key icon. Boolean: toggle icon with true/false ratio. Free text: text icon with avg length. |
| MK4.10.4 | S | **Done** | **Type detection confidence score** — Each detection reports a confidence (0-1). Show confidence in the schema detail panel. Low-confidence detections (<0.7) get an amber badge suggesting user review. |

## Epic MK5: Upload and Workspace

*User-supplied data and multi-dataset project workspace.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK5.1 | M | **Done** | CSV and Excel upload (drag-drop or file picker; `std.csv` parser for CSV/TSV; SheetJS-equivalent via `std.xlsx` for .xlsx/.xls; first 5 rows preview before commit; column count, row count, detected types shown; cancel upload before commit) |
| MK5.2 | S | **Done** | Paste data (textarea accepting CSV or TSV; toggle for "first row is header"; auto-detect delimiter; parse on submit) |
| MK5.3 | M | **Done** | Project workspace (group multiple datasets into a named project; tabbed navigation between datasets within project; cross-dataset queries: LLM can reference columns from multiple loaded datasets; combined schema profile sent to LLM includes all datasets; join operation in local compute engine links datasets by shared key) |
| MK5.4 | S | **Done** | Dataset pagination and search (50 rows per page, prev/next; column filter: select which columns to show; row search: filter rows containing substring in any column; export filtered view as CSV) |

## Epic MK6: moke UX and Infrastructure

*App shell, navigation, settings, and serving infrastructure.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK6.1 | M | **Done** | moke app shell and navigation (sidebar: Datasets / Dashboard / Insight Lab / Pipeline / Settings; dark theme matching loke base.tkt; moke-specific accent colour (teal, distinct from loke indigo); responsive layout; moke version badge in header) |
| MK6.2 | M | **Done** | Multi-provider LLM routing (Claude Sonnet/Haiku via loke's Anthropic provider; GPT-4o-mini via loke's OpenAI provider; model selector in chat panel; local Ollama models when available; API keys from loke keychain (F1.5) — no re-entry in moke settings) |
| MK6.3 | S | **Done** | moke settings page (session memory toggle — clear on close or persist; pipeline console verbosity; default sensitivity level; preferred model; about/version) |
| MK6.4 | M | **Done** | Presentation mode (full-screen dashboard view for demos; hide sidebar; auto-cycle through cards; keyboard arrows to navigate; ESC to exit; timer overlay showing time in presentation; `?` overlay for keyboard shortcuts; used in user research sessions) |

## Epic MK7: Demo Readiness

*The three gaps between implemented code and a runnable demo: dataset serving API, unified registry, and static assets.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK7.1 | S | **Done** | Unified dataset registry (`data/registry.tk`) — single `get_dataset(id):$dataset` and `list_all():@($dataset_info)` that delegates across all four data modules (au_datasets, it_hardware, it_platform, customer_intel); used by the API layer so it never needs to know which module owns which dataset |
| MK7.2 | M | **Done** | Dataset serving API (`pages/api/datasets.tk`) — `GET /api/moke/datasets` returns JSON list of all available datasets with metadata; `GET /api/moke/datasets/:id` returns full dataset as JSON `{ headers, rows, profile }` so the browser can load built-in demo data into memory; also serves IT project sub-datasets by qualified id (e.g. `it_hardware.inventory`) |
| MK7.3 | S | **Done** | Static assets and Chart.js wiring — update `templates/base.tkt` to load Chart.js from CDN; add `packages/moke/static/favicon.svg` (teal variant of loke favicon); verify all template `<script src="/static/...">` references resolve |
| MK7.4 | S | **Done** | html2canvas local bundle — download html2canvas 1.4.1 to `packages/moke/static/html2canvas.min.js` and update `templates/base.tkt` to load from `/static/html2canvas.min.js` instead of CDN; enables PNG dashboard export in offline / air-gapped environments |

---

# Epic T: Test Suite

*Comprehensive behavioural test coverage for every module. Tests verify runtime correctness — not just that files compile, but that functions return expected values for known inputs. Each story produces one or more `.tk` test files under `tests/unit/`, `tests/integration/`, or `tests/e2e/`. Every test file exposes a `run_all():bool` entry point that logs `PASS`/`FAIL` per assertion and returns `true` only if every assertion passes.*

## T1 — Privacy Core

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T1.1 | M | Done | `tests/unit/privacy/test_regex.tk` — PII detection: email (`john@example.com`), AU phone (`0412 345 678`), US phone (`(555) 123-4567`), credit card (`4111 1111 1111 1111`), AU TFN (`123 456 789`), AU ABN (`51 824 753 556`), API key (`sk-ant-...`), IPv4 (`192.168.1.1`); verify entity_type, sensitivity level, and placeholder format `[TYPE_N]`; verify clean text returns zero entities and `PUBLIC` sensitivity |
| T1.2 | S | Done | `tests/unit/privacy/test_placeholder.tk` — `make_placeholder("email", 1)` → `"[EMAIL_1]"`; `make_placeholder("phone_au", 3)` → `"[PHONE_AU_3]"`; `new_map()` returns empty entries; `add_entry` + `restore` round-trips original value; multiple entries restored independently; restore on text with no placeholder returns text unchanged |
| T1.3 | S | **Done** | `tests/unit/privacy/test_placeholder_store.tk` — add entry and retrieve by placeholder; retrieve unknown placeholder returns none; duplicate placeholder overwrites; `restore_all` replaces every placeholder in a string; store with zero entries returns text unchanged |
| T1.4 | S | Done | `tests/unit/privacy/test_patterns.tk` — all `pat_*` constants are non-empty strings; `pat_email` contains `@`; `pat_credit_card` contains a digit character class; `pat_au_tfn` and `pat_au_abn` are distinct; none of the patterns is identical to another |
| T1.5 | M | Done | `tests/unit/privacy/test_pipeline.tk` — full pipeline run: input with email → anonymised output does not contain original email → restore returns original; pipeline with no PII leaves text unchanged; pipeline preserves non-PII context around replaced value; chained pipeline (two PII types) restores both; sensitivity escalates correctly from PUBLIC → CONFIDENTIAL on email detection |
| T1.6 | S | Done | `tests/unit/privacy/test_guardian.tk` — `build_system_prompt("")` returns non-empty string; `is_guardian_present` returns true on the built system prompt; `is_guardian_present` returns false on empty string; guardian text contains "GUARDIAN" keyword; custom system prompt is included in built prompt |
| T1.7 | S | **Done** | `tests/unit/privacy/test_content.tk` — content type detected correctly for CSV, JSON, markdown, plaintext; content with `<html>` tag detected as HTML; empty string returns a valid (not-crash) result; very long string (1000+ chars) handled without truncation |
| T1.8 | S | **Done** | `tests/unit/privacy/test_template.tk` — template with no substitutions returns base string; template with one `{{field}}` substituted; template with multiple fields substituted in order; missing field key leaves placeholder intact; `to_json` on a built template produces valid JSON shape |

## T2 — Router

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T2.1 | M | Done | `tests/unit/router/test_sensitivity.tk` — `score_from_pii($public, 0)` → PUBLIC; `score_from_pii($confidential, 1)` → CONFIDENTIAL; `score_from_pii($confidential, 3)` → RESTRICTED (escalation); `score_from_pii($restricted, 1)` → RESTRICTED; `score_from_content("password reset")` → RESTRICTED; `score_from_content("bank account details")` → RESTRICTED; `score_from_content("patient diagnosis")` → CONFIDENTIAL; `score_from_content("the weather today")` → PUBLIC; `combine($confidential, $restricted)` → RESTRICTED; `combine($public, $internal)` → INTERNAL; `can_use_cloud($restricted)` → false; `can_use_cloud($public)` → true; `level_to_str($confidential)` → "CONFIDENTIAL" |
| T2.2 | M | Done | `tests/unit/router/test_selector.tk` — selection with `prefer_local=true` and RESTRICTED sensitivity picks local/Ollama model; selection with PUBLIC sensitivity and cloud allowed returns a model with cost > 0 or local fallback; selection criteria with `max_cost_per_1k=0.001` excludes expensive models; empty registry returns error variant; `$instant` tolerance prefers interactive tier; `$background` tolerance accepts background tier |
| T2.3 | M | Done | `tests/unit/router/test_router.tk` — `new_config("http://127.0.0.1:11434")` sets `prefer_local=true`; `provider_from_str("anthropic")` → `$anthropic`; `provider_from_str("unknown")` → `$local`; `ctx_from_model("claude-3-5-sonnet-20241022")` → 200000; `ctx_from_model("gpt-4o-mini")` → 128000; `cost_in_from_model("gpt-4o-mini")` → 0.00015; `estimate_latency` for `$interactive` tier → 500 ms |
| T2.4 | S | Done | `tests/unit/router/test_escalation.tk` — escalation path selected when sensitivity is RESTRICTED; non-escalation path selected for PUBLIC; escalation message contains model name; escalation result includes reason field |
| T2.5 | S | Done | `tests/unit/router/test_intent.tk` — intent classify on code-like text returns `$code_generation` or `$code_review` task; classify on "summarise this document" returns `$summarisation`; confidence is between 0.0 and 1.0 inclusive; result includes task and confidence fields |

## T3 — Optimiser

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T3.1 | M | Done | `tests/unit/optimiser/test_cache.tk` — `default_config("/tmp")` sets threshold 0.92 and TTL 86400; stats start at zeros; hit rate = hits/(hits+misses); eviction increments evictions counter; cache result with score above threshold is a hit; result with score below threshold is a miss |
| T3.2 | M | Done | `tests/unit/optimiser/test_budget.tk` — budget with 1000 token limit and 900 token prompt returns 100 remaining; budget at exactly limit returns 0 remaining; budget exceeded returns error/negative; token count estimate for known short string is non-zero; token count for empty string is 0 |
| T3.3 | M | Done | `tests/unit/optimiser/test_toon.tk` — TOON profile for dataset with 3 columns contains all 3 column names; profile marks PII columns as SUPPRESSED; profile preserves non-PII column stats; `to_json` output contains "toon_profile" key; empty dataset produces valid (empty) profile |

## T4 — Governance Core

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T4.1 | M | Done | `tests/unit/governance/test_kill_switch.tk` — `is_engaged` returns false on fresh state; after `engage`, `is_engaged` returns true; `release` sets `is_engaged` to false; `format_widget` on engaged state contains "ENGAGED"; `format_widget` on disengaged state contains "DISENGAGED"; `engage` with auto_release_minutes=0 sets `auto_release_at=0`; `check_auto_release` on non-auto state returns false |
| T4.2 | M | Done | `tests/unit/governance/test_quota.tk` — quota not exceeded when usage below limit; quota exceeded when usage equals limit; quota exceeded when usage above limit; `remaining` returns correct value; `reset` zeros the counter; quota for a non-existent namespace returns the full limit |
| T4.3 | M | Done | `tests/unit/governance/test_policy.tk` — policy loaded from valid JSON is valid; `evaluate` on matching rule returns action; `evaluate` on non-matching rule returns default; empty rule set returns allow; conflicting rules respect priority order; policy with missing required field returns error |
| T4.4 | M | Done | `tests/unit/governance/test_rules_engine.tk` — rule with `all` conditions passes only when all conditions met; rule with `any` condition passes when at least one condition met; rule with no conditions always passes; rule with contradictory conditions never passes; `evaluate_all` returns first matching rule action |
| T4.5 | S | Done | `tests/unit/governance/test_gateway.tk` — gateway allows PUBLIC request through; gateway blocks RESTRICTED request when kill switch engaged; gateway blocks request exceeding quota; gateway logs decision reason; blocked request returns `$loke_err` variant |
| T4.6 | S | Done | `tests/unit/governance/test_compliance.tk` — AU default regulations loaded correctly; GDPR defaults loaded correctly; `is_compliant` returns true for clean data; `is_compliant` returns false for data with RESTRICTED PII and no justification; compliance report includes regulation name |

## T5 — Storage

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T5.1 | M | Done | `tests/unit/storage/test_settings.tk` — `set_str`/`get_str` round-trip; `set_bool`/`get_bool` round-trip; `get_str` on missing key returns error; `set_int`/`get_int` round-trip; overwrite of existing key returns updated value; `get_bool` on non-bool value returns error |
| T5.2 | M | Done | `tests/unit/storage/test_audit.tk` — append entry increments count; filter by type returns only matching entries; filter by date range returns only in-range entries; `to_json` on entry includes type, timestamp, actor fields; audit trail is append-only (no delete function); CSV export contains header row |
| T5.3 | S | Done | `tests/unit/storage/test_ephemeral.tk` — `store` then `retrieve` returns value before TTL; `retrieve` after TTL expiry returns none; `wipe` removes entry; `wipe_expired` removes only expired entries; `wipe_all` leaves store empty; store with empty key returns error |
| T5.4 | S | Done | `tests/unit/storage/test_keychain.tk` — `store` and `retrieve` round-trip API key; `retrieve` unknown service returns none; `delete` makes subsequent `retrieve` return none; service name is preserved exactly |

## T6 — Memory

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T6.1 | M | **Done** | `tests/unit/memory/test_palace.tk` — new palace has zero wings; add wing increases count; retrieve wing by name returns correct wing; retrieve unknown wing returns none; wing has correct type and name; palace `to_json` contains wings array |
| T6.2 | M | **Done** | `tests/unit/memory/test_graph.tk` — `add_node` increases node count; `add_relation` creates edge between existing nodes; `query_facts` with subject filter returns only matching facts; `query_facts` with predicate filter returns only matching relations; `detect_contradictions` returns empty for non-contradicting relations; `detect_contradictions` returns entry when same relation has conflicting valid_to for same from+relation; `visualise_dot` output starts with "digraph" |
| T6.3 | M | **Done** | `tests/unit/memory/test_decay.tk` — access count increases relevance score; old last-accessed time decreases score; score is between 0.0 and 1.0 inclusive; `should_evict` returns true when score below threshold; `should_evict` returns false when score above threshold; `apply_decay` reduces score over time |
| T6.4 | S | **Done** | `tests/unit/memory/test_aaak.tk` — AAAK context built from non-empty diary has non-empty output; AAAK context for empty diary is empty string or minimal header; `to_aaak` on single entry includes entry content; format includes "Agents", "Actions", "Artefacts", "Knowledge" sections |

## T7 — Models & Inference

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T7.1 | M | Done | `tests/unit/models/test_registry.tk` — new registry has default models; lookup by ID returns correct model; lookup by unknown ID returns none/error; add model increases count; models can be filtered by provider; models can be filtered by tier; `list_all` returns all registered models |
| T7.2 | M | Done | `tests/unit/models/test_tiers.tk` — model with latency ≤ 500 ms classified as `$interactive`; model with latency ≤ 5000 ms classified as `$considered`; model above 5000 ms classified as `$background`; tier label for `$interactive` is "interactive"; Q4 memory estimate for 7B model is < 8 GB; FP16 estimate for 7B model is > Q4 estimate |
| T7.3 | S | Done | `tests/unit/models/test_hardware.tk` — `detect()` returns non-empty profile; `total_memory_gb` uses unified_memory when set; `total_memory_gb` sums ram+vram when unified=0; `summary()` is a non-empty human-readable string; `to_json` contains all expected keys |

## T8 — Platform HTTP, Plugin, i18n, Integration, Error

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T8.1 | M | Done | `tests/unit/platform/test_http_response.tk` — `success(200, "{}")` envelope has `ok=true`; `error_resp(404, "not found")` has `ok=false` and correct code; `paginated` result includes `total`, `page`, `per_page` fields; error response does not include internal stack trace; `to_json` for success envelope is valid JSON shape |
| T8.2 | M | Done | `tests/unit/platform/test_http_router.tk` — register route and find exact match returns it; find unknown path returns none; prefix match returns correct route when exact not found; multiple routes registered — each findable independently; `list_routes` count matches registered count |
| T8.3 | S | Done | `tests/unit/platform/test_http_security.tk` — `security_headers()` contains CSP header; output contains X-Frame-Options; output contains X-Content-Type-Options; `default_config()` has HSTS enabled; CSP includes "default-src 'self'" |
| T8.4 | M | Done | `tests/unit/platform/test_plugin_registry.tk` — register plugin increases count; `get` by name returns correct plugin; `get` unknown name returns none; `all_routes` aggregates routes from all plugins; `all_nav_items` aggregates nav items; `all_health_checks` aggregates health checks; duplicate plugin name is handled without crash |
| T8.5 | M | Done | `tests/unit/platform/test_plugin_anonymisation.tk` — AU TFN pattern registered by default; AU ABN pattern registered by default; AU Medicare pattern registered by default; `find_by_type("au_tfn")` returns correct pattern; pattern confidence for Medicare is 0.90; `list_patterns` count ≥ 3 |
| T8.6 | S | Done | `tests/unit/platform/test_plugin_contracts.tk` — `current_version()` returns `{0,1,0}`; `is_compatible({0,1,0}, {0,0,1})` → true (same major, higher minor); `is_compatible({1,0,0}, {0,9,0})` → false (different major); `version_string({1,2,3})` → "1.2.3"; `list_breaking_changes()` returns empty array for 0.1.0 |
| T8.7 | M | Done | `tests/unit/platform/test_i18n_translator.tk` — `t("loke.privacy.on")` returns non-empty string after loading en-AU; `t("nonexistent.key")` returns the key itself as fallback; `t_n("loke.entities", 1)` uses singular form; `t_n("loke.entities", 3)` uses plural form; `t_params("loke.greeting", ["Alice"])` substitutes `{{0}}` with "Alice"; `set_locale`/`get_locale` round-trip; `format_number(1234.5)` returns "1234.50" |
| T8.8 | M | Done | `tests/unit/platform/test_sanitise.tk` — `strip_html("<b>hello</b>")` → "&lt;b&gt;hello&lt;/b&gt;" (entities); `strip_tags("<b>hello</b>")` → "hello"; `sql_escape("O'Brien")` → "O''Brien"; `prevent_log_injection("line1\nline2")` → "line1 line2"; `clamp_length("hello", 3)` → "hel…"; `clamp_length("hi", 10)` → "hi" unchanged |
| T8.9 | M | Done | `tests/unit/platform/test_adapter.tk` — new adapter starts in "disconnected" state; `record_failure` increments failure count; after threshold failures circuit opens; `record_success` resets to "connected"; `is_open` returns true when open, false when closed; `status_label` matches state |
| T8.10 | M | Done | `tests/unit/platform/test_error_server.tk` — `new_error` creates error with code and message; `to_json` does not contain internal field; `to_json` contains code and message; `log_error` does not crash; error with same code+message is equal |

## T9 — CLI & Browser Workspace

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T9.1 | M | Done | `tests/unit/cli/test_sessions.tk` — `new_store()` has zero sessions; `create` adds session; `activate` sets that session as active; `deactivate` clears active; `get_active` returns none when no active session; `list` returns all sessions; `find` by id returns correct session; `find` unknown id returns none; `format_list` for empty store returns a non-empty header string |
| T9.2 | M | Done | `tests/unit/cli/test_code_preprocess.tk` — `detect_language(".py")` → "python"; `detect_language(".ts")` → "typescript"; `detect_language(".unknown")` → "unknown"; `find_proprietary_patterns` on text with `INTERNAL_ONLY` marker returns ≥ 1 match; `scrub_secrets` on text with `sk-` key removes it; `scrub_secrets` on clean text returns text unchanged; profile result has language field set |
| T9.3 | M | Done | `tests/unit/browser/test_tabs.tk` — `new_store()` has zero tabs; `open` adds tab; `close` removes tab; `activate` sets active_id; `pin` toggles pinned state; close active tab activates next available; `list_tabs` count matches open count; `add_bookmark` and `remove_bookmark` update bookmarks list |
| T9.4 | M | Done | `tests/unit/browser/test_extractor.tk` — `strip_html_tags("<p>hello</p>")` → "hello"; `detect_pii` on text with email address returns true; `detect_pii` on clean text returns false; `detect_pii` on text with digit run > 8 returns true; extraction result includes content and kind fields |
| T9.5 | M | Done | `tests/unit/browser/test_privacy_metadata.tk` — `resolve_page_sensitivity` with RESTRICTED attr → RESTRICTED; CONFIDENTIAL + PUBLIC → CONFIDENTIAL (takes highest); no attrs → PUBLIC; `parse_robots_txt` with GPTBot Disallow sets `disallow_ai=true`; `parse_robots_txt` with empty content sets `disallow_ai=false`; compliance note is non-empty string |

## T10 — Governance src/

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T10.1 | M | Done | `tests/unit/governance_src/test_kill_switch.tk` — `enable_global` blocks all; `disable_global` unblocks; `enable_provider("anthropic")` blocks that provider; `is_blocked("anthropic", "any")` → true after enable; `is_blocked("ollama", "any")` → false when only anthropic blocked; `list_active` returns all active entries; `fallback_message` returns non-empty string |
| T10.2 | M | Done | `tests/unit/governance_src/test_incidents.tk` — `create` returns incident with id and open status; `append` makes incident retrievable; `resolve` sets resolved=true; `list_open` excludes resolved; `list_all` includes both; `get` unknown id returns none; `post_incident_template` is a non-empty string |
| T10.3 | M | Done | `tests/unit/governance_src/test_justification.tk` — `submit` creates justification; `get` returns submitted justification; `approve` sets approved=true; `suggest_simpler` returns ≥ 1 built-in simpler paths; simpler path for rule-based use case suggests rule engine; `to_json` contains use_case_id and rationale |
| T10.4 | M | Done | `tests/unit/governance_src/test_ownership.tk` — `assign` stores owner; `get` returns assigned owner; `has_all_owners` returns false when role missing; `has_all_owners` returns true when all required roles assigned; `missing_roles` returns only unassigned roles; `list` count matches assigned count |
| T10.5 | M | Done | `tests/unit/governance_src/test_tier_dashboard.tk` — `new_report` has all-zero stats; `update_interactive` increments interactive count; percentages recalculate correctly after update (sum = 100%); `report_to_json` contains all three tier keys; running averages update after second call; zero total does not divide by zero |

## T11 — MCP Broker & src/memory

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T11.1 | M | Done | `tests/unit/mcp_broker/test_config.tk` — `new_server` with allowlist blocks unlisted tool; `new_server` with empty allowlist allows any tool; `is_tool_allowed` with denylist blocks denied tool; `is_tool_allowed` with both allow and deny — deny wins; `to_json` contains name, transport, enabled fields |
| T11.2 | M | Done | `tests/unit/mcp_broker/test_registry.tk` — register server increases count; `get_server` by name returns correct entry; `get_server` unknown returns none; `set_status` updates status; `set_tools` stores tool list; `list_tools` returns prefixed tool names (`server_name.tool_name`); `list_servers` count matches registered |
| T11.3 | M | Done | `tests/unit/memory_src/test_knowledge_graph.tk` — `new_graph` has zero nodes; `add_node` increases count; `add_relation` creates edge; `query_facts` with subject filter returns only matching; temporal query with `as_of` excludes future relations; `detect_contradictions` empty for no overlap; contradictions detected when two relations have conflicting valid_to; `visualise_dot` starts with "digraph" |
| T11.4 | M | Done | `tests/unit/memory_src/test_agent_diary.tk` — `get_or_create_diary` for new agent has zero entries; `append_entry` adds entry; `get_entries` returns most-recent-first; `get_recent(1)` returns only the latest; `build_startup_context` for non-empty diary returns non-empty string; `record_feedback` on matching entry updates feedback field; `to_aaak` on single entry is non-empty |

## T12 — Feedback, Agents, Providers

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T12.1 | M | Done | `tests/unit/feedback/test_store.tk` — `append` adds feedback entry; `list` returns all entries; filter by feature_area returns only matching; filter by thumbs_down returns only negative; entry has no prompt content (privacy invariant); `count` matches appended entries; `clear` empties store |
| T12.2 | M | Done | `tests/unit/feedback/test_learning.tk` — thumbs-down on model decrements its score; false-positive PII reduces confidence for that pattern; high thumbs-down on warning type triggers sensitivity review flag; `list_adaptations` contains description of each change; `revert` removes adaptation |
| T12.3 | M | Done | `tests/unit/agents/test_registry.tk` — register agent increases count; `get` by name returns correct agent; `get` unknown returns none; duplicate name registration returns error; `list` returns all agents; agent has name, description, and capability fields |
| T12.4 | M | Done | `tests/unit/providers/test_dispatcher.tk` — dispatch to "ollama" calls Ollama provider path; dispatch to unknown provider returns error; dispatch with kill switch engaged returns blocked error; response includes model and provider fields; `to_json` on response is valid shape |

## T13 — a11y Testing

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T13.1 | M | Done | `tests/unit/a11y/test_scanner.tk` — HTML with `<img>` missing `alt` produces VIOLATION; HTML with all images having `alt` produces no violations; `<button>` without label produces VIOLATION; well-formed semantic HTML produces zero violations; `assert_no_violations` returns true for clean HTML; `result_to_json` contains violations array; violation includes element and message fields |

## T14 — Integration & E2E

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T14.1 | L | Done | `tests/integration/test_health_api.tk` — `GET /api/health` returns `{ok: true}` shape; response includes version field; Ollama status field is present (may be "offline" in test); response time < 100 ms; endpoint accessible without authentication |
| T14.2 | L | Done | `tests/integration/test_pipeline_api.tk` — POST to `/api/pipeline` with clean text returns response with no PII; POST with email in body returns anonymised prompt; POST with RESTRICTED content is blocked or requires approval; response includes session_id; response includes sensitivity classification |
| T14.3 | L | Done | `tests/e2e/test_moke_flow.tk` — dataset load stores headers and rows in session; privacy pipeline run on dataset with PII returns anonymised schema; confirm page receives local_view and llm_view; restore after LLM response returns original values; sensitivity classification flows through all stages correctly |

---

# SUMMARY

| Layer | Epics | Stories | Done/Spec done |
|-------|-------|---------|----------------|
| Foundation (F1–F9) | 9 | 56 | 55 |
| Platform (P1–P6) | 6 | 32 | 29 |
| Application (A1–A6) | 6 | 27 | 17 |
| Accountable AI (G1–G3) | 3 | 11 | 5 |
| Value & Governance (G4) | 1 | 6 | 5 |
| Agentic AI (AG1) | 1 | 8 | 8 |
| Memory Palace (M1–M2) | 2 | 11 | 7 |
| Cross-cutting (X1–X5, W1) | 6 | 30 | 30 |
| Demo — moke (MK1–MK7) | 7 | 34 | 34 |
| Test Suite (T1–T14) | 14 | 65 | 65 marked Done, **0 verified** |
| **Total** | **55** | **268** | **193** |

---

## Epic MK8: Enriched Demo Datasets & Guided Walkthroughs

*Transform demo datasets from minimal samples into rich, realistic data with deliberate patterns for demonstrating every moke capability. Each dataset should have clear outliers, clusters, time series trends, PII examples, and cross-dataset relationships. Add complementary IT operations datasets for a complete observability scenario.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK8.1 | L | **Done** | **IT Server Hardware enrichment** — Expand from 48 to 200 servers across 4 data centres (SYD-1, SYD-2, MEL-1, BNE-1). Add columns: `os_patch_level`, `last_reboot_days`, `cpu_util_avg`, `ram_util_avg`, `disk_util_avg`, `network_throughput_mbps`, `open_incidents`, `maintenance_window`, `environment` (prod/staging/dev/dr), `criticality` (P1-P4), `application_owner`, `cost_centre`. Deliberate patterns: 12 servers at >90% CPU (cluster: overloaded), 8 with expired warranties (cluster: risk), 5 with no recent patches (cluster: vulnerable), 3 in DR never tested. |
| MK8.2 | L | **Done** | **IT Performance Metrics dataset** — New complementary dataset: 10,000 rows of time-series metrics. Columns: `server_id` (links to server hardware), `timestamp`, `cpu_percent`, `ram_percent`, `disk_iops`, `disk_latency_ms`, `network_in_mbps`, `network_out_mbps`, `active_connections`, `error_rate`, `response_time_ms`, `gc_pause_ms`. Deliberate patterns: daily CPU spike 09:00-10:00, gradual memory leak on 3 servers, disk latency degradation before failure, correlated network/error spikes. |
| MK8.3 | L | **Done** | **IT Incidents & Alerts dataset** — New: 500 incident records. Columns: `incident_id`, `server_id`, `severity` (P1-P4), `category` (hardware/software/network/security), `status` (open/investigating/resolved/closed), `opened_at`, `resolved_at`, `mttr_minutes`, `assignee`, `root_cause`, `affected_services`, `change_id`, `related_incidents`, `sla_breached`. Patterns: recurring P1 on 2 servers (same root cause), P2 cluster during maintenance windows, SLA breach rate >15% for network category. |
| MK8.4 | M | **Done** | **IT Change Management dataset** — New: 300 change records. Columns: `change_id`, `type` (standard/normal/emergency), `status` (approved/implemented/rolled_back/failed), `requested_by`, `approved_by`, `implement_date`, `affected_servers`, `risk_level`, `success`, `rollback_reason`, `downtime_minutes`. Patterns: emergency changes correlate with P1 incidents, Friday deployments have 3x rollback rate. |
| MK8.5 | M | **Done** | **IT Application Performance dataset** — New: 2,000 rows. Columns: `app_id`, `app_name`, `endpoint`, `method` (GET/POST/PUT/DELETE), `timestamp`, `response_time_ms`, `status_code`, `error_message`, `user_count`, `request_count`, `apdex_score`, `deployment_version`. Patterns: version 2.3.1 introduced latency regression, one endpoint has 5x error rate, apdex drops during peak hours. |
| MK8.6 | M | **Done** | **IT Asset & Cost dataset** — New: links servers to financial data. Columns: `asset_id`, `server_id`, `purchase_date`, `purchase_cost`, `depreciation_rate`, `current_value`, `monthly_opex`, `power_watts`, `rack_units`, `licence_count`, `licence_cost_monthly`, `support_contract`, `support_expiry`, `vendor`. Patterns: 20% of servers consume 60% of costs, 5 servers past depreciation still running. |
| MK8.7 | S | **Done** — it was not, until MK20.5. The registry and its suggestions were defined in `index.tkt` and called from nowhere, and the `relationships` structure rendered on no page; a function the calling page cannot reach is not a shipped feature. Now in `static/js/moke-relationships.js`, rendered on `/chat`, with every declared join verified against the real columns | **Cross-dataset relationships** — Define foreign key relationships: server_id links hardware↔metrics↔incidents↔changes↔assets. app_id links performance↔servers (via deployment mapping). Add relationship metadata to dataset registry so moke can suggest joins and cross-dataset queries. |
| MK8.8 | L | **Done** | **Guided demo walkthrough** — Add a "Demo" button on the landing page that launches a step-by-step walkthrough: (1) Load IT Server Hardware, (2) View schema with type detection, (3) Ask "Show servers with expired warranties", (4) Navigate to Dashboard → generate dashboard, (5) Navigate to Insight Lab → run clustering, (6) Load IT Performance Metrics, (7) Ask "Which servers have memory leaks?", (8) Navigate to Governance → view session stats. Each step has a prompt chip that auto-fills. Walkthrough tracks progress and can be resumed. |
| MK8.9 | M | **Done** | **Medicare & Water Quality enrichment** — Expand Medicare from 30 to 500 rows with realistic claim patterns (seasonal flu spike in July, bulk billing rate varies by state, gap amounts cluster by specialty). Expand Water Quality from 30 to 200 readings with seasonal temperature variation, 3 sensors showing deteriorating pH trend, 2 turbidity alerts. Add columns: `follow_up_required`, `rebate_percentage` to Medicare. Add `weather_condition`, `rainfall_mm` to Water Quality. |
| MK8.10 | S | **Done** | **Customer Intelligence enrichment** — Expand from 392 to 1,000 customers. Add columns: `acquisition_date`, `last_login_days`, `email_open_rate`, `cart_abandonment_rate`, `preferred_channel` (web/app/store), `lifetime_orders`, `returns_count`, `social_sentiment`. Sharpen clusters: whales (top 2% by LTV), at-risk (high spend + declining frequency), growth (increasing spend trajectory), dormant (>180 days inactive). |

## Epic MK9: API Data Sources & External Connections

*Enable moke to connect to external data sources via REST APIs, GraphQL, and file URLs. This transforms moke from a CSV-upload tool into a data platform that can pull live data from any API endpoint, including Australian open data portals.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK9.1 | L | **Done** | **API connection configuration UI** — New page/panel: "Connect to API". Fields: URL, method (GET/POST/PUT/DELETE), headers (key-value pairs, add/remove rows), query parameters, request body (JSON editor), authentication type (None/API Key/Bearer Token/Basic Auth/OAuth 2.0). Preview button sends test request, shows response status, headers, and first 500 chars of body. Save connection as named data source. |
| MK9.2 | M | **Done** | **REST/JSON data source** — Parse JSON API responses into tabular datasets. Auto-detect: (a) array of objects `[{...},{...}]` → each object is a row, keys are columns, (b) nested `{data: [{...}]}` → unwrap common wrapper patterns, (c) paginated responses → follow `next` links or increment `page` param. Transform options: flatten nested objects (dot notation), select specific JSON paths, rename columns. |
| MK9.3 | M | **Done** | **GraphQL data source** — GraphQL query editor with: endpoint URL, query text area, variables JSON, headers. Execute query, parse response `data` field into tabular format. Introspection query to discover schema. Save queries as named data sources. |
| MK9.4 | S | **Done** | **OpenAPI/Swagger discovery** — Paste an OpenAPI spec URL (JSON or YAML). Parse the spec, list available endpoints with descriptions, parameters, response schemas. Click an endpoint to auto-fill the API connection form. Support Swagger 2.0 and OpenAPI 3.0/3.1. |
| MK9.5 | L | **Done** | **Authentication methods** — Full auth configuration: (a) API Key — header name + value or query param, (b) Bearer Token — static token in Authorization header, (c) Basic Auth — username + password, (d) OAuth 2.0 — client credentials flow: token URL, client ID, client secret, scopes → auto-fetch and refresh access token, (e) Certificate auth — upload client cert + key (PEM), CA cert for mTLS. Store credentials in `~/.loke/connections.json` (encrypted via loke keychain). |
| MK9.6 | M | **Done** | **data.gov.au integration** — Discover and connect to Australian government open data. Search data.gov.au CKAN API (`https://data.gov.au/api/3/action/package_search`). List datasets with title, description, format, organisation, last updated. Filter by format (CSV, JSON, API), organisation, tags. One-click download CSV datasets. For API datasets, auto-configure the connection. Pre-populate suggested datasets: ABS employment, Medicare statistics, Bureau of Meteorology, NSW transport. |
| MK9.7 | S | **Done** | **CSV/Excel URL import** — Fetch CSV or Excel file from a URL and load as dataset. Support: direct file URLs, Google Sheets published CSV URL, S3 presigned URLs. Show download progress. Auto-detect delimiter, encoding, header row. |
| MK9.8 | M | **Done** | **Connection manager** — List all saved API connections with status (last tested, last fetched). Refresh data on demand or on schedule (every N minutes/hours). Show connection health (green/amber/red). Delete connections. Export/import connection configs as JSON (excluding secrets). |
| MK9.9 | S | **Done** | **API response caching** — Cache API responses locally to reduce repeated calls during analysis. Configurable TTL per connection (default 5 minutes). Cache stored in sessionStorage. Show cache hit/miss in pipeline console. Manual cache clear button. |
| MK9.10 | S | **Done** | **Rate limiting and retry** — Respect API rate limits: detect `429 Too Many Requests` and `Retry-After` header. Exponential backoff with configurable max retries (default 3). Show rate limit status in connection manager. Queue concurrent requests to same host. |

---

# TOOLCHAIN

## Epic F10: Toolchain Currency and Upstream Feedback

*Get loke building on a current toke and ooke, and keep it there, so it cannot drift four months behind again.*

loke's last commit before this work was 2026-05-21. toke was being committed daily and ooke had moved a
major version past loke's declared `ooke >= 1.0.0` without anyone noticing, because nothing checked.

### The hold criterion, and why it is a commit and not a version

**loke needs toke at commit `6cc9061` or later — in practice a build of `main` — and ooke `v3.0.0-rc.1`.**
`TOOLCHAIN.lock` is the authority; this section explains it.

Upstream is explicit that **no tagged toke release works** and that there is no version number to give.
That is not a preference: toke's `VERSION` file still reads 2.8.0 well past the `v2.8.0` tag, so a semver
comparison would happily accept a checkout that cannot build loke. toke is therefore gated on **commit
ancestry** with its version recorded as advisory only. ooke is gated on a **tag**, which it now has.

**Current position, 2026-09-20: the hold is CLEARED.** Both pins are published and fetchable, which was
itself a blocker — neither was on a remote until now, so CI could not obtain a compiler at any migration
status and no figure this project published was reproducible by anyone else. CI now builds loke and
reproduces the local census exactly.

Accepting a release candidate reverses the earlier decision to wait for a final 3.0.0. That reversal was
deliberate and instructed. What does **not** move is the publication bar: a figure measured against an rc
is labelled with the rc, so if the final tag changes, every affected number can be found again.

**The build is not green.** 58 of 199 modules compile and 52 of 179 interfaces emit. Of the 291 errors,
**226 are `E2030` cascade** from modules that have not compiled yet — so the real work is 65 errors in 19
files, split into F10.14–F10.24 below. Three defects in the build itself were masking this and are fixed:
the interface directory held a stale nested tree toke never read, the interface pass omitted
`--emit-llvm` so every library failed on "no main function", and interfaces were emitted alphabetically
rather than in dependency order.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F10.1 | M | **Done** | **Make the build fail loudly** — every compiler invocation in `build_loke.sh` ended `2>/dev/null \|\| true` and it linked with `-Wl,-undefined,dynamic_lookup`, so a build in which every module failed still printed "Done" and produced a binary, turning undefined symbols into runtime crashes. Now reports a per-module census to `build/break-report.txt` and refuses to link an incomplete build. |
| F10.2 | M | **Done** | **Path portability** — `run_tests.sh` and `build_test.sh` hardcoded an absolute home path with no environment override while CI exported `TOKE_DIR`, so **CI's test job could never have passed** regardless of code correctness, despite a badge in the README. Both now honour `TOKE_DIR` and fail fast when the compiler is absent instead of reporting every test as a compile error. |
| F10.3 | M | **Done** | **Pin and gate the toolchain** — `TOOLCHAIN.lock` plus `scripts/check_toolchain.sh`, gating toke by commit ancestry and ooke by released version, per the criterion above. CI clones the pinned commits rather than chasing upstream HEAD, which previously meant CI could break on somebody else's commit at random with no local reproduction. |
| F10.4 | S | **Done** | **Drift watch** — pinning alone would let loke drift silently again, which is how it fell four months behind. A scheduled job compares the lock against upstream HEAD weekly and warns without turning `main` red. |
| F10.5 | M | **Done** | **Diagnostics-driven fixer** — `scripts/fix_diagnostics.py` applies mechanical fixes by byte offset from toke's own JSON diagnostics, so only spans the compiler itself flags are touched. This replaces the regex approach in the previous migration script, whose `^[ \t]*//.*\n` silently deleted the licence header from 520 files. 968 equality fixes applied; `packages/` type-check went 167 to 246 passing. |
| F10.6 | S | **Done** | **Remove the destructive migration scripts** — their job is finished and a repo-wide destructive rewriter is a standing hazard whether or not its regex is fixed. |
| F10.7 | M | **In progress** — re-scoped 2026-09-20. The "74 type errors" figure was measured against stale interfaces and is wrong. Measured now: 58 of 199 modules compile, 291 errors of which **226 are E2030 cascade**, leaving 65 real errors in 19 files. The classes are split out as F10.14–F10.24 | **Finish the migration** — the 74 remaining genuine type errors, and whatever the expression-`if` part of the v0.4 change requires. Boolean operators are already migrated (53 `&&`, 74 `\|\|`, zero `and(`/`or(` call sites) and the equality split is done, so this is the residual. |
| F10.8 | M | | **Adopt ooke 3.x interfaces** — every shared interface but two had already drifted at 2.0.0 (`store` 40 changes, `template` 33, `router` 15), plus two new modules. A major version means more. Note `packages/browser/_serve_main.tk` is generated by a heredoc inside `build_loke.sh`, so the build script changes, not just source. |
| F10.9 | M | | **Capability manifest** — toke has a capability broker with runtime traps for ungranted capabilities, and loke declares nothing. Add a `tkc.toml` with a **minimal, justified** grant set and document why each is granted. This is also an opportunity rather than a chore: a minimal audited grant set is a real, verifiable privacy property to replace some unverified claims. |
| F10.10 | M | **Done** | **Consolidate the upstream gap docs** — four existed, addressed to the toke and ooke teams and filed nowhere. All re-verified and archived under `docs/archive/` with a do-not-file banner, superseded by [`UPSTREAM.md`](../UPSTREAM.md). The verification was the point: **every historical gap has closed.** `linker-gaps.md` has 0 genuine gaps of its 131 symbols (115 now exist, 14 were prose fragments, and the 2 that looked real are loke bugs — `str.nowiso8601` should be `std.time`, and `str.between` composes from `str.indexof` and `str.slice`). `ooke-gaps.md` has 0 of 6 remaining. The `<a<b` parser ambiguity is fixed. Had these been filed as written, loke would have reported about 137 already-fixed problems to its own upstream. |
| F10.11 | S | | **File the genuine gaps upstream** — after F10.10's verification the list is short: the document and image library asks in [`toke-libraries-required.md`](toke-libraries-required.md), and the three toke documents that still state "toke has no comment syntax" after `(* *)` shipped (`companion-file-spec.md`, `companion-fidelity-methodology.md`, `conventions.md`). Two further asks were found on 2026-09-20, both tool hazards rather than niceties. **(1) `toke --lint --fix` deletes imports that are needed.** The `unused-import` rule looks only at alias usage (`t.foo`) and ignores **type** references, so it removes `i=t:shared.types;` from a file whose only use of that module is `$lokeerr`. Applied here it dropped 197 imports across 119 files and produced 265 `identifier 'lokeerr' is not declared` errors. Worth filing with the observation that this is the same class of hazard F10.6 removed loke's own destructive rewriter for — a `--fix` flag that breaks a correct file is worse than no `--fix`. **(2) `http.post` is declared twice in `http.tki`**, once as a `route` taking `(str, funcdecl)` and once as a `func` taking `(httpclient, str, [byte], str)`. toke resolves the route, so the diagnostic reports "the implementation takes 2 arguments" for a four-parameter function; the arity in that message is misleading. Cross-reference into toke's own progress tracker so they are scheduled rather than noted. |
| F10.12 | M | | **Resolve the two source trees** — `packages/**` declares 344 modules and a legacy root `src/**` declares 102. The only genuine cross-tree dependency is five CLI files importing `loke.platform.i18n` from `src/platform/i18n/`; the apparent auth dependency is a red herring, since `packages/core/src/auth/pkce.tk` declares `m=loke.core.auth.pkce` itself. So about 99 of the 102 legacy files are dead weight. Move i18n into a package, rename the four stray `loke.core.auth.*` modules, archive the rest. |
| F10.12a | S | | **Call `std.time` instead of the nonexistent `str.nowiso8601`** — surfaced by F10.10. Five files call it (`agents/types.tk`, `governance/gateway.tk`, `governance/dashboard.tk`, `governance/trace.tk`, `shared/src/log.tk`). The capability exists in the wrong module: `std.time` has `time.now`, `time.format`, `time.parse` and more. Worth fixing for its own sake — `storage/audit.tk` writes the literal string `'now()'` into `created_at` (GA5.1), and a missing timestamp helper is a plausible reason why. |
| F10.12b | S | Superseded by F10.16, which collapses this and five other stdlib drifts into one shim | **Add a local `between` helper** — `privacy/content.tk` calls the nonexistent `str.between` at two sites. `str.indexof` and `str.slice` both exist, so compose it in `packages/core/src/util/strings.tk`, which already exists untracked. Not an upstream ask. |
| F10.13 | S | | **Commit and push the held work** — 521 `.tk` files are uncommitted pending this epic, including the 968 mechanical fixes. **`packages/browser/pages/api/pipeline.tk` must not be committed as it stands** — it carries a privacy regression that fails open, tracked as NC1.9. Push only once the build and tests are green locally, so CI's first honest run is meaningful. |
| F10.14 | S | **Done** — `str.format` replaced with interpolation in `shared/src/log.tk` (the canonical form per the pattern catalogue, not just a fix), and `str.arrayget(patterns;pi)` replaced with `patterns.get(pi)` in `privacy/regex.tk`, which preserves the element type. **Two files, 7 errors, and it released 33 interfaces and 23 modules** — 52→85 interfaces, 58→81 compiling | **Unblock the two root modules** — 7 errors in 2 files transitively block ~130 modules. `packages/shared/src/log.tk` has 4 `str.format` calls and **`str.format` reverses its arguments** in the new runtime — `(val, fmt)`, not `(fmt, ...values)` — and drops varargs, so these become `str.concat` or interpolation. `packages/core/src/privacy/regex.tk` has 3 struct-offset errors from `arrayget` type erasure. `shared.log` alone accounts for 115 of the 226 cascade errors. **Re-run `scripts/build_census.py` immediately after: every estimate below was written against a number this story changes.** |
| F10.15 | S | **Done** — the page handlers and `main` were compiled *before* the interface pass, and the pass did not cover `packages/browser/pages` either, so pages neither resolved their imports nor contributed interfaces. Both halves fixed: interfaces first, over the pages too. 85→92 interfaces, 81→88 modules. The inconsistent page module naming (`m=page.api.approve` vs `m=browser.pages.api.health`) is still outstanding and moves to F10.15a | **Close the build-script interface gaps** — `scripts/build_loke.sh` step 4a runs `module_order.py` over `packages/core/src`, `packages/shared/src` and `extensions` but **not `packages/browser/pages`**, and step 4 compiles the pages *before* 4a runs at all. 32 of the E2030 errors are this, with zero source change. Also fix the inconsistent page module naming — `pages/api/approve.tk` declares `m=page.api.approve` while `pages/api/health.tk` declares `m=browser.pages.api.health`, and the generated `_handlers.tk` imports both spellings. |
| F10.15a | S | | **Consistent page module naming** — `pages/api/approve.tk` declares `m=page.api.approve` while `pages/api/health.tk` declares `m=browser.pages.api.health`, and the generated `_handlers.tk` imports both spellings. Pick one prefix and apply it. Split from F10.15, which fixed the ordering |
| F10.16 | M | **Partial** — the `http.post` and `json.obj` halves are done and both turned up something the story did not anticipate. **`std.http.post` is not callable at all**: `http.tki` declares it twice, once as a `route` taking `(str, funcdecl)` and once as a `func` taking `(httpclient, str, [byte], str)`, and toke resolves the route — so no argument list satisfies it. That escalates the F10.11 upstream ask from "misleading diagnostic" to "the function is unreachable". Worked around with `http.postheaders`, which is not double-declared and preserves the existing `$ok`/`$httperr` handling; `http.postjson` also works. `json.obj` takes a raw JSON string rather than key/value pairs, so the four bodies in `models/ollama.tk` are built with interpolation — the canonical form, and correctly escaped via `json.enc` on each value. Still open: `str.between`, the `replacere`/`countre`/`containsre` flags argument, `http.gettimeout`, `std.process.exec`, `std.tls.tlsconfig`, `std.infer.generate` | **One stdlib compatibility shim, `shared.strcompat`** — six drifts, none of them mechanical. `str.between` does not exist at all (needs an `indexof`+`slice` helper; supersedes F10.12b). `replacere`/`countre`/`containsre` lost their trailing flags argument, so each `"gi"`/`"g"`/`"i"` has to be folded into the pattern — a per-site regex judgement. `str.format` reverses its arguments and drops varargs (9 sites, 4 files). `json.obj` takes a raw JSON string, not key/value pairs (9 sites, 5 files). `json.try*` each need a second argument (5 sites in `optimiser/toon.tk`). `str.pad`/`padleft`/`padright` take `(s, width, padchar)`; 3 sites pass 2 and are latent. |
| F10.17 | L | | **`std.string` → `std.str` across 71 files** — `std.string` does not exist and never did; it is `std.str`. 46 of the files are in `packages/moke` and 35 in legacy `src/`, which is why the build has never reported it: neither tree is compiled. Also seven other imported-but-absent modules — `std.arr` (2 files), `std.fs` (9), `std.io` (3), `std.shell` (2), `std.clipboard` (1), `std.webview` (1). Each needs a decision: shim, replace, or delete the caller. Depends on F10.23. |
| F10.18 | S | **Done** — 24 sites, not the 7 the story estimated: the count only looked at `packages/browser/pages` and `packages/moke/pages` has 15 more. Decision taken as planned: ooke's `tplrenderfile(path; ctx; templatesdir)`, matching how ooke's own `serve.tk` and `build.tk` call it. The third argument is the layout-resolution directory and the template path stays unchanged — verified against the implementation, which uses `file.exists(templatepath)` directly. Also fixed the error path: the return is `str!tplerr`, and every site now matches it to `http.res(200;h)` or `http.res(500;...)` rather than returning the result raw. ooke's own callers default to `""` on error, which would serve a blank page with a 200 — not acceptable here. 257 → 233 errors, 90 → 106 modules | **`ooke.template.renderfile` → `tplrenderfile`** — renamed in 3.0.0-rc.1 and gained a third parameter. 7 identical sites (`pages/approve.tk:9`, `chat.tk`, `pipeline.tk`, `privacy.tk`, `savings.tk`, `setup.tk`, `tabs.tk`). One decision first, made once and applied seven times: ooke's `tplrenderfile(str, [str:str], str)` or `std.template`'s surviving `tpl.renderfile(str, tmplvars)`. **Decision taken: ooke's**, because the page layer is ooke's and `std.template` being still-present looks like the stale half of the same split. |
| F10.19 | S | **Done** — all seven definitions deleted and 35 call sites re-pointed at `shared.types.strpad`, which takes `i64` so integer literals need no cast. Two files needed the `shared.types` import added. Also fixes a latent bug the duplicates carried: each padded by slicing a 30-space literal, so any width above 30 would have failed; `strpad` loops. 284 → 257 errors | **Delete six of the seven `padright` definitions** — loke declares its own `padright` **seven times** with two different width types: `i32` in `governance/scorecard.tk:58`, `governance/value.tk:127` and `mcp/discovery.tk:176`; `u32` in `memory/mining.tk:166`, `governance/monitoring.tk:153`, `governance/incidents.tk:131` and `governance/dashboard.tk:229`. All 16 int-width errors are integer literals hitting the `i32` variants. One shared definition taking `i64` removes the errors and six copies; adding 16 `as i32` casts would keep all seven. |
| F10.20 | S | **Partial — 16 of 33 sites.** A `return-type` pass in `scripts/migrate_toolchain.py` walks back from the erroring return to the enclosing `f=` declaration and rewrites `:i64` to the struct the function actually returns, including the `:i64!$err` form. The class turned out wider than `regulations.tk`: `memory/storage.tk` (17, `$palacelocation`/`$drawer`), `governance/gateway.tk` (3, `$gatewaydecision`), `policy/loader.tk`, `providers/anthropic.tk`, `providers/openai.tk`, `router/latency_router.tk`. 17 declined where the shape differed — left for a human rather than guessed | **Declare the real return types in `policy/regulations.tk`** — 8 functions are declared `:i64` and return a `$regulation` or `$policyset`. Note the compiler's own `fix` field says "cast return value to i64 using 'as'", which is **wrong advice** — casting a struct to an integer would compile and destroy the value. Declare the type the function actually returns. |
| F10.21 | S | | **`void` sweep** — 205 `f=name(...):void` declarations and 25 `<void` returns across 58 files. toke functions return `i64`; the compiler warns `C keyword 'void' detected` on each, twice per function. `):void{` → `):i64{` and `<void` → `<0`, scriptable from the diagnostics. Warnings only, so this is hygiene rather than a blocker — but it is 122 of the report's noise. Note upstream's own `str.tki` still declares `str.add`/`str.addbyte` as `-> void`, so the keyword is not gone from the toolchain. |
| F10.22 | M | | **`arrayget` type erasure** — `str.arrayget` is typed `(i64,i64) -> i64`, so it throws away the element type even where the array is declared correctly: `privacy/regex.tk:67` declares `patterns:@$patterndef` and still breaks. 152 call sites in 58 files, plus 23 `:@i64` placeholder params in 8 files that need a per-site judgement about the real element type. **Produces zero errors today** — the diagnostics do not mention it — so it is invisible to the census and 128 of the 152 sites sit in modules that have never been type-checked. Size this after F10.14; the 4 E4034 struct-offset errors are the leading indicator. |
| F10.23 | S | | **Extend the build to the other 320 files** — `build_loke.sh` compiles 212 of the repo's 532 non-archived `.tk` files. Entirely outside it: `packages/moke` (96), legacy `src/` (102), `packages/cli` (26), `packages/mcp-broker` (6), `packages/mcp-toke` (4), `tests/` (86). Until this lands, "the build is green" means 40% of the repo and the census is not a measure of the project. |
| F10.24 | S | | **Two parse errors** — unbalanced parentheses in `packages/browser/pages/api/settings.tk:100` (one `)` too many in a nested `str.concat`) and `packages/core/src/governance/dsar.tk:143`. Pre-existing, nothing to do with the migration. |


---

# DEMO LAYER — moke: DATASETS AND PERSONAL USE

> **Scope note.** Everything in this section is **moke**, the demo application, not loke core. Demo
> datasets, guided flows, import paths and the personal-finance workspace all live in
> `packages/moke/`. loke core gains nothing dataset-specific from these epics — where a story needs a
> core capability it depends on an NC1, DA1 or AD1 story rather than adding domain logic to core.
> The test corpora under `tests/fixtures/` are the exception and are deliberately core: they test the
> detector, not the demo.

## Epic MK19: Government Open Data Expansion

*Broaden the demo beyond synthetic data with real, attributed, offline-first snapshots of Australian government open data, each arriving complete with its own prompts, dashboard and flow.*

The current 15 datasets are synthetic despite being labelled "Government Open Data", and the enrichment
recorded in MK8 landed only in the frontend, so the backend still holds pre-enrichment row counts. Three
different wrong dataset counts appear across the docs. This epic replaces guesswork with attributed
snapshots and one manifest that drives everything.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK19.1 | M | Partial — `static/js/moke-data.js` is the canonical data layer (manifest, lazy CSV fetch, value-free schema profile, and the `MokeActive` shim that lets both stores coexist safely). 23 tests pass against the real fixtures. **The inline 230KB object in `index.tkt` is not yet replaced** and the 17 direct sessionStorage call sites are not yet migrated | **Decide the canonical store and stop the split** — Two divergent dataset stores exist: `packages/moke/data/*.tk` with `data/registry.tk`, served by `pages/api/datasets.tk`, and a `var DATASETS` object inline in `templates/index.tkt` which is **230KB of data and UI fused together**. `grep "api/moke/datasets"` returns zero hits, so the backend path is orphaned and the frontend object is what the demo uses. The two hold different dataset sets. Pick one — recommended: a static manifest plus CSV snapshots under `static/data/`, fetched lazily, because it needs no recompilation, is diffable and reviewable, and drops the weight of `/` from 230KB to about 25KB. Also fix `registry.tk::listall()`, which has an `if` where a loop belongs and therefore returns only one AU dataset. |
| MK19.2 | M | **Done** — manifest schema implemented and populated by the fetch script; `packages/moke/static/data/manifest.json` | **Manifest-driven dataset metadata** — One entry per dataset carrying id, name, description, domain, **kind** (`snapshot` / `synthetic` / `generated`), provenance, sensitivity, PII columns, per-column descriptions, relationships, **suggested prompts**, and a **pre-baked dashboard**. This replaces six hardcoded touch points: the hand-written cards in `index.tkt`, the `DATASETS` object, `DASH_PROMPTS` in `dashboard.tkt`, the prompt map in `chat.tkt`, `suggestCrossQueries`, and `DEMO_WALKTHROUGH` in `base.tkt`. A new dataset should arrive complete rather than needing edits in four files. |
| MK19.3 | M | **Done** — provenance, verbatim licence, SHA-256 and a `transformations` list per snapshot, plus a licence sidecar and an extended `NOTICE` | **Provenance and licence attribution** — Each snapshot ships publisher, source URL, retrieval date, verbatim licence name and URL, an attribution string, a SHA-256, and a **`transformations` list naming every edit made to the raw file**. Committing a government CSV to a public repository is redistribution, so attribution is a licence obligation, not tidiness. Extend the repo `NOTICE` and surface attribution in the UI. |
| MK19.4 | M | **Done** — `scripts/fetch_opendata.py` with the licence guard, verified firing on a deliberate mismatch | **Reproducible fetch script** — No dataset generator exists. Add one driven by a recipe file: resolve the resource through the portal API, apply column selection and row caps, enforce a size budget, write the CSV plus a licence sidecar, compute the hash, and patch the manifest. **Abort if the portal's declared licence does not match the recipe's expected licence** — that guard is what stops an unattributable or non-redistributable file reaching git. Add a `--check` mode that reports drift without writing. |
| MK19.5 | L | Partial — transport done (BITRE road fatalities, cc-by, 4,000 rows). **ABS publishes no CSV**, so the economy dataset is blocked on the XLSX gap in `toke-libraries-required.md`; AEMO is flagged live-fetch-only pending a terms review; health still to do | **First four datasets, one per domain** — Health (emergency department or elective surgery waiting times, aggregate only), energy and environment (electricity price and demand, or daily climate observations), transport (road deaths), economy (labour force). Chosen for a clear analytical story and an unambiguous licence. **Verify each licence individually from the portal's own metadata rather than assuming CC-BY**: some energy market data is published under terms that do not permit redistribution, in which case it ships as live-fetch-only with a manifest entry and no committed snapshot. |
| MK19.6 | M | **Done** — but only half was, until MK20.3 needed it. The `real` badge was applied; **`.badge-synthetic` was defined and used nowhere**, so six cards sat under a bare "Government Open Data" heading with no marking — including "Medicare Benefits Schedule", described as "MBS claims data with patient, provider, and billing information", which reads as real health data. That is precisely the misrepresentation this story exists to prevent. The badge is now on all six, and the heading says "Synthetic Fixtures" with a sentence stating every name and identifier is fabricated. The section hides itself if the manifest is unavailable, so a failure degrades the page rather than breaking it. | **Distinguish real from synthetic in the UI** — The existing `au.*` datasets are labelled "Government Open Data" and contain fabricated names and identifiers. Badge them `synthetic`, and badge the new snapshots `real`. The most persuasive privacy demonstration in the whole product is the contrast: a real public aggregate where the filter finds nothing, against a synthetic patient fixture where it finds everything, on the same pipeline, back to back. |
| MK19.7 | M | **Done** — pre-baked dashboard for the road-fatalities snapshot, 12 cards, rendered locally with no provider call. `--validate-dashboards` checks every column and operation against the real snapshot header and against the resolver's actual op set, and refuses baked-in values. Verified it catches a typo'd column, an unsupported operation and a baked value | **Pre-baked dashboards so demos never need a live model** — Ship a dashboard definition per dataset, rendered through the existing local resolution path with no provider call. Constrain every card to the operations the resolver actually implements, and validate column names against the snapshot header in CI — a typo produces a blank card on stage with no error. |
| MK19.8 | M | | **Wire the orphaned connection modules** — Nine modules totalling ~199KB in `static/js/` are referenced only by a standalone test runner; `templates/connections.tkt` has one inline script and empty placeholder comments where they should mount, and its "Load as Dataset" button is disabled with an error string saying a module is unimplemented that is in fact written. Mount them and make live refresh a separately demonstrated feature, never the demo path. **Note before mounting:** `datagov-source.js` had the wrong CKAN base URL (`/api/3/action`, which returns 404 with an HTML body; the correct base is `/data/api/3/action`). That is now fixed, but it is a warning about the rest — these modules have never been exercised against a live endpoint, so mounting them is the beginning of the work rather than the end of it. |
| MK19.9 | L | | **The `/api/proxy` endpoint they all depend on** — `/api/proxy` does not exist, and six call sites reference it, so the existing "Test Connection" button has never worked either. It is an **SSRF vector by construction**: a local service fetching an arbitrary caller-supplied URL, on a machine also running loke, Ollama and a database. Non-negotiable: a default-deny host allowlist, rejection of localhost, link-local, cloud metadata and all private ranges, HTTPS only, a body-size cap and timeout, and no cross-host redirect without re-checking the allowlist. Needs its own security review and a toke change, so it is gated on the toolchain. |
| MK19.10 | S | **Done** — verified the real count (15 synthetic keys in the `DATASETS` object, plus 1 real snapshot) and corrected `README.md` to state the synthetic-versus-real split explicitly rather than hiding it behind "Australian-themed". Row counts now live in the manifest so a figure cannot drift from the data. | **Correct the dataset counts** — README, `features-moke.md` and `registry.tk` state three different numbers, none of which is 15. Fix all of them and add the count to the manifest so it is derived rather than asserted. |

## Epic MK20: Declarative Demo Flows

*Make a demo flow something a dataset supplies, rather than something hardcoded per scenario.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK20.1 | M | **Done** — [`static/js/moke-flow.js`](../packages/moke/static/js/moke-flow.js) with [`static/data/flows.json`](../packages/moke/static/data/flows.json); 81 tests in the gate. Found and fixed a live three-step off-by-one: the dashboard, Insight Lab and governance steps each wrote the next index *before* navigating, so arriving at `/dashboard` displayed the Insight Lab instruction and the final step completed the walkthrough on arrival. `planStep()` returns navigation and advancement as separate outcomes, so that is now unrepresentable | **Flow interpreter** — `DEMO_WALKTHROUGH` in `templates/base.tkt` is eight steps of imperative closures, each hand-writing session storage and navigation. Replace with an interpreter over a declarative flow in the manifest. Five step kinds cover every existing step: `load`, `navigate`, `prompt`, `dashboard`, `note`. Each carries presenter narration and an optional selector to wait for, so a flow cannot race ahead of a slow page. Keep the existing step-index persistence: it works and survives navigation. |
| MK20.2 | S | **Done** — the flow is data, and narration is templated (`{{dataset.rowcount}}`). It said "48 servers across SYD and MEL" for a dataset of **200 servers across four** data centres; the count now comes from the dataset. An unresolved placeholder renders as a visible gap and logs a warning, never as a stale default. Note "48" survives in six other places (`index.tkt` x4, `upload.tkt`, `data/registry.tk`, the `.tkc.md`) which MK19.1 should clear when the catalogue moves to the manifest | **Port the existing flow and fix its stale copy** — Move the server-hardware walkthrough into manifest form so behaviour is preserved and testable. Its step-1 text still says "48 servers" after the dataset was enriched to 200 — template the count from the manifest so copy cannot drift from data again. |
| MK20.3 | M | **Partial** — the cross-domain flow is built and is the half that mattered: real BITRE road fatalities (CC BY, PUBLIC, nothing to redact) then the synthetic MBS fixture (CONFIDENTIAL, five PII columns), same pipeline, opposite outcomes, ending on Governance with the contrast. A picker lists title and duration from `flows.json`, so adding a flow needs no template change. Tests assert the contrast is real and that the narration carries none of the four withdrawn claims. Still outstanding: a flow for each remaining dataset | **A flow per dataset, plus a cross-domain flow** — The cross-domain one is the real story: a real public aggregate where nothing is redacted, then a synthetic patient fixture where everything is, on the same pipeline. Add a flow picker listing title and duration. |
| MK20.4 | L | **Done** — slides are built from the DDL through [`static/js/moke-provenance.js`](../packages/moke/static/js/moke-provenance.js) (66 tests), which is now the single definition of the NC1.5/NC1.6 rule for both the dashboard and the presentation. Every fabricated figure and false provenance caption is gone, and two gate checks guard the class | **Make presentation mode dataset-driven** — `templates/presentation.tkt` is a fixed four-slide deck over a literal ten-row array, and its own comment concedes slides are not rendered from the dashboard definition it is handed. It also hardcodes a figure captioned "Count computed locally — no data left the device" and generates synthetic clusters with `Math.random()` — the same dishonesty NC1.6 removed from the dashboard, in a page the NC1 stories did not name. Build slides from the dashboard cards, reusing the card renderer. **Riskier than it looks:** extracting that renderer touches a 1,387-line file wired to chart instance tracking and sort state, so do it after the manifest and pre-baked dashboards are stable. |
| MK20.5 | S | **Done** — called, not deleted: the suggestions were good and MK8.7 was a false Done. [`static/js/moke-relationships.js`](../packages/moke/static/js/moke-relationships.js) is now the single table (56 tests, including verifying every declared join against the real column lists). There were **three** overlapping copies: `suggestCrossQueries()` in `index.tkt` which nothing called, a live `DEMO_PROMPTS` in `chat.tkt` covering different datasets, and five hardcoded chips of which three — "Find anomalies in the revenue data", "Cluster customers by spending behaviour" — were offered unchanged over a server inventory with neither column | **Call or remove the dead cross-query code** — `suggestCrossQueries` covers four datasets and is never called; the `relationships` structure it reads renders nowhere, despite MK8.7 being marked Done. Drive it from the manifest or delete it. |

## Epic MK21: Personal Finance Workspace

*The demo where the no-custody claim is tested to destruction: import your own bank statements, structure and analyse them entirely on-device, and use the model to build the analysis without ever showing it the data.*

**Why this epic matters more than the others.** Every other dataset in moke is public or synthetic, so
"no data left the device" is a claim nobody has to trust. A bank statement is the opposite: it is
genuinely the user's, it is maximally sensitive, and nobody would accept "we redact it first" as an
answer — which is precisely the argument the external literature supports
(`docs/research/disclosure-measurement-findings.md` §1). If any personal financial value leaves the
device during a session in this workspace, the architecture claim in NC1 has failed. This workspace is
therefore both the flagship demonstration and the hardest test.

**What the model is for, and what it is never given.** The model helps *build the analysis* — proposing
a category taxonomy, generating the query or rule set, explaining what a tax category generally covers.
It is never given a transaction, a merchant, an amount, an account number or a balance. Merchant names
in particular are not "low sensitivity": a pharmacy, a clinic, a solicitor or a gambling site each
discloses something material about a person, so merchant text is treated as personal data throughout and
never leaves, not even for categorisation.

> **Two things this epic must say plainly to the user, not bury.**
>
> 1. **Storage is not encrypted today.** The database encryption pragma is inert (X8), so imported
>    statements would sit in plaintext on disk. Personal financial data makes that materially worse than
>    it is for demo data. Either X8 lands first, or this workspace keeps its data in a separately
>    encrypted store, or it refuses to persist at all and works per-session. **MK21.2 decides this, and
>    it gates the rest of the epic.**
> 2. **This is not tax advice, and it does not lodge anything.** It organises figures and shows its
>    working so a person or their accountant can check it. Any output that looks like a determination
>    must be labelled as an estimate with its method shown.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK21.1 | M | | **Workspace scaffolding and the disclosure contract** — A distinct workspace with its own explicit contract shown on entry: what is read, what is computed locally, what is sent (a schema profile and a question), and what is never sent. State the storage position from MK21.2 honestly rather than in a tooltip. Everything in this workspace defaults to no-custody; the redaction fallback is not offered here at all, because for this data it is not an acceptable second choice. |
| MK21.2 | L | | **Decide and implement at-rest protection — gates the epic** — Choose between waiting for X8, using a separately encrypted store via `std.encrypt` (verified present: `aes256gcmencrypt`/`decrypt`/`keygen`/`noncegen` and `hkdfsha`) with a key derived through the existing keychain path, or running session-only with nothing written to disk. Recommended while X8 is outstanding: **session-only by default**, with persistence an explicit opt-in that states what it writes and where. Also provide a single, verifiable "delete everything" that actually removes files rather than dropping rows, and prove it by inspecting the filesystem afterwards. |
| MK21.3 | L | | **CSV import with column mapping** — Bank CSV exports differ by institution in column order, header naming, date format, and whether amounts are signed in one column or split across debit and credit. Build an import step that proposes a mapping (date, description, amount or debit/credit, balance, currency) and lets the user correct it before anything is accepted. toke provides `std.csv` with a reader and writer, so this path has a binding. On the frontend, reuse one of the three existing `parseCSV` implementations rather than adding a fourth. |
| MK21.3a | M | | **XLSX import — needs a capability that does not exist** — There is **no XLSX or zip binding in toke** (`std.csv` exists; `std.zip` and `std.xlsx` do not), and XLSX is a zip of XML, so it cannot be parsed with what is available. Two honest routes: file an upstream ask for a zip binding and build on it, or handle XLSX in the local sidecar of MK21.4a. **Until one lands, the workspace accepts CSV only and says so** — every bank and every spreadsheet can export CSV, so this is a real limitation rather than a blocker. Do not list Excel support until it works. |
| MK21.4 | L | | **Two extraction paths, and do not conflate them** — Many statements are **text PDFs** where characters can be extracted directly with no recognition at all, and only scanned or photographed statements need OCR. Detect which and always prefer extraction, because it is exact and OCR is not. Specify the detection rule and the fallback, and record which path produced each field so MK21.5 can weight confidence accordingly. |
| MK21.4a | XL | | **On-device extraction sidecar — the binding does not exist** — toke has **no OCR and no PDF capability**. It does, however, already have the *preprocessing* primitives: `std.image` decodes and encodes PNG, JPEG, WebP and BMP and provides `tograyscale`, `crop`, `resize`, `pixelat` and `fromraw`, all from a single dependency-free `image.c`. What is missing is recognition itself, and PDF entirely. So the extraction step cannot be built in toke today, though less of it is missing than it first appears. The right answer is a **local sidecar process**, following the precedent already in the repository at `packages/privacy-filter/` — a small local service loke talks to over loopback. That keeps extraction on-device, which is what matters here, without waiting on an upstream binding. Candidate engines, both local: the platform text recogniser on macOS, or a bundled Tesseract for cross-platform. **The acceptance criterion is the privacy one, not the accuracy one: prove no network call occurs during extraction**, by running a full import with networking disabled and asserting it still succeeds. A cloud OCR service would defeat the entire point of the workspace, so engine choice here is a privacy decision. **Known risk from the precedent:** the existing sidecar's checked-in virtualenv lacks its own dependencies and cannot run, so this story owns a working install path and a health check, not just a server file. |
| MK21.4b | S | | **File the upstream asks** — Register the missing capabilities against the toolchain rather than leaving them as folklore: a zip binding (which unblocks XLSX and much else), and a decision on whether PDF text extraction and OCR belong in the standard library or stay sidecar concerns. The asks are written up in [`docs/toke-libraries-required.md`](toke-libraries-required.md), which states the interfaces expected, the implementation route for each, and the recommendation that OCR live in its own repository rather than the standard library. The sidecar is recorded there as the interim answer so nothing is blocked waiting. |
| MK21.5 | L | | **Surface OCR confidence — do not repeat the dashboard's mistake** — A misread amount produces a wrong budget presented with total confidence, which is exactly the failure NC1.6 removed from the dashboard. Every OCR-derived field carries its confidence; anything below a threshold is **flagged for review rather than silently accepted**; and the running totals show how many fields are unreviewed. A reconciliation check against the statement's own opening and closing balance is the strongest available signal that extraction was correct — if the transactions do not sum to the balance change, say so prominently instead of proceeding. |
| MK21.6 | L | | **Local transaction structuring** — Normalise dates across formats, unify signed and split amount columns, strip payment-processor noise and card suffixes from merchant strings, and **deduplicate across overlapping statement periods**, which is the common real-world case when a user imports several months that share a boundary. All of it on-device. Show the user what was merged and why, and let them undo it. |
| MK21.7 | L | | **Categorisation without disclosure** — The interesting problem in the epic. Categorising needs semantic understanding of merchant names, and merchant names are exactly what must not leave. Three approaches, in preference order: (a) a local rule set the user can see and edit; (b) **the no-custody pattern — ask the model for a *taxonomy and a rule set*, given only category names and counts, then apply those rules locally to the actual merchants**; (c) a local small model, if one is available. Never send merchant text. Acceptance: with a sentinel merchant name present in the data, that string appears zero times in every outbound payload of a full categorisation session. |
| MK21.8 | M | | **Budget review and planning, computed locally** — Spend by category and period, trend against a user-set budget, recurring-payment detection, largest movers between periods, and projected position. All through the local compute path, all with provenance states from NC1.6 so an unresolved figure shows as unresolved. No figure in this workspace may originate from a model. |
| MK21.9 | L | | **Tax preparation support, framed honestly** — Organise the financial year (1 July to 30 June in Australia), group candidate deductions by category, total them, and show the working. The model's role is limited to explaining what a category generally covers, which needs no personal data. **It must not state that an expense is deductible, and it must not produce anything resembling a lodgement.** Output is a worksheet with its method visible, labelled as an estimate for the user or their accountant to check. Include the receipt and substantiation requirement as a prompt to the user rather than an assertion about their affairs. |
| MK21.10 | M | | **The disclosure ledger for a whole session** — Depends on DA1. Show the user, for a complete session, exactly what left the device: the bytes, the field names, the category names, and the fact that zero transaction rows and zero merchant strings were included. This is the artefact that makes the claim checkable rather than merely stated, and it is the single most persuasive thing in the demo. |
| MK21.11 | M | | **Adversarial test: the no-custody invariant under real pressure** — Depends on AD1. Seed a statement with unique sentinel values in the account number, a merchant name, an amount and a balance. Run every path in the workspace — import, OCR, structuring, categorisation, budgeting, tax, refine, export, presentation — and assert each sentinel appears **zero times** in every captured outbound payload. Include the paths that leaked elsewhere: a refine round-trip, a saved template reload, and a session restored from history. This is the regression test for the architecture claim, and it belongs in CI. |
| MK21.12 | S | Partial — **CSV fixtures done** (`tests/fixtures/bank-statements/`): two institution shapes with genuinely different conventions, a ragged export, and a deliberately non-reconciling statement so MK21.5's check has something to catch. Ground truth included so an import is scored rather than eyeballed, and the generator verifies its own reconciliation. **PDF and scanned-image fixtures are blocked** on the extraction sidecar (MK21.4a) — there is no way to author a realistic scan without it, and a fake one would test nothing. | **A synthetic statement fixture, so the demo needs nobody's real data** — Ship a realistic but wholly synthetic statement in each supported format: text PDF, scanned image, CSV in two institution shapes, and XLSX. Include deliberate difficulties — a misaligned scan, an ambiguous date format, a duplicated period boundary, a merchant string with processor noise — so the confidence and reconciliation work in MK21.5 has something to demonstrate against. Real statements stay with their owners. |


---

# AUDIT-DRIVEN GAPS

> **Generated:** 2026-05-20 — Full audit of specification, design principles, and architecture against actual implementation. These epics address gaps where the vision has not aligned with what was built.

## Epic GA1: Pipeline Integration — Wire Core Engine into Browser

*Written when the browser API handler bypassed the core engine entirely. **Five of the nine wirings now exist at HEAD** — privacy pipeline, response restoration, kill switch, audit logging and policy evaluation. Four do not: the optimiser, the semantic cache, the router (the provider is still chosen by an if/else on API-key length), and therefore the end-to-end verification. Corrected 2026-09-19 against the committed tree; see `docs/claims.md` A13 for the line-level evidence.*

> **Do not read the working tree for this epic's status.** The uncommitted copy of `pipeline.tk` strips all nine core imports and is a regression, not the state of the repository (F10.13, X8.5).

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| GA1.1 | L | **Done** | **Wire privacy pipeline into browser handler** — Replace the stub string-matching in `pipeline.tk` with actual calls to `core.privacy.pipeline.run()`. Import the privacy pipeline module, run all text through regex + NER + Presidio layers, generate reversible placeholders, and send only anonymised text to LLM providers. This is the **#1 critical fix** — currently ALL browser traffic flows unfiltered to external LLMs. |
| GA1.2 | M | **Done** | **Wire response restoration into browser handler** — After receiving LLM response, call `core.privacy.placeholder.restore()` to swap placeholders back to original values before returning to the user. Currently the browser returns raw LLM output with no restoration. The CLI proxy (`cli/src/proxy.tk`) does this correctly — use it as reference. |
| GA1.3 | M | **Done** | **Wire kill switch check before LLM dispatch** — Before any outbound LLM request in `pipeline.tk`, call `core.governance.kill_switch.isengaged()`. If engaged, return an error response explaining why and when it will auto-release. Currently the kill switch is implemented but never checked — a user who trips it can continue sending data unprotected. |
| GA1.4 | M | **Done** | **Wire audit logging into request path** — After each LLM call, call `core.storage.audit.logevent()` with: event type, model, provider, sensitivity, token counts (in/out), cost estimate, duration, and correlation ID. Currently `audit.tk` is never called from any request path. Note its hashing is **not** tamper-evident — the stored digest is a concatenation of two non-secret fields and does not incorporate the previous record; see GA5.2. |
| GA1.5 | M | **Reopened** — no optimiser call exists in the handler | **Wire token optimisation into pipeline** — Before sending to LLM, run prompt through `core.optimiser.toon.encode()` for structured data and/or `core.optimiser.llmlingua.compress()` for natural language. Report compression ratio in pipeline console. Target: 60-80% token reduction per spec. Currently TOON and LLMLingua are fully implemented but dormant. |
| GA1.6 | M | **Reopened** — no cache lookup exists in the handler | **Wire semantic cache into pipeline** — Before dispatching to LLM, check `core.optimiser.cache.lookup()` for semantically similar previous requests. If cache hit (similarity > 0.92), return cached response with `[cache hit]` indicator. On cache miss, store response via `cache.store()` after receiving. Target: up to 73% savings on cache hits per spec. |
| GA1.7 | M | **Reopened** — `selector.select()` is never called; the provider is chosen by `str.len(anthropickey)>20`. Overlaps X8.6, which owns the four named strategies | **Wire intelligent router into pipeline** — Replace the if/else API key check with actual `core.router.selector.select()` which evaluates sensitivity × cost × latency × capability to choose the optimal model. Currently the router makes simplistic binary local/cloud choices; the spec requires multi-dimensional optimisation. |
| GA1.8 | S | **Done** | **Wire governance policy evaluation** — Before dispatching, call `core.governance.policy.evaluate()` to get risk classification (low/medium/high) and decision ($allow/$allowwithwarning/$requireapproval). Show warnings to user per graduated severity. Currently policy evaluation exists but is never called from the browser. |
| GA1.9 | S | **Reopened** — cannot pass while GA1.5-GA1.7 are unwired, and the existing test asserts on JSON shape rather than on whether anonymisation occurred | **Verify end-to-end pipeline in browser** — Full integration test: send a prompt containing PII through the browser, verify privacy filter detects and masks it, token optimiser compresses it, router selects appropriate model, audit log records the event, kill switch blocks when engaged, and response restoration returns clean output. Document the verified flow. |

## Epic GA2: Security Hardening

*API keys stored in plaintext JSON, SQLite unencrypted, no license headers. These are specification requirements that are not met.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| GA2.1 | L | Done | **Migrate API keys to OS keychain** — Replace `~/.loke/settings.json` plaintext key storage with OS keychain integration. On macOS use Security framework via toke/ooke bindings. Keys fetched per-request with expiry validation, never written to disk, never appear in logs. Update `settings.tk` handler and all consumers. Spec: "Secrets and API keys stored in OS keychain, NEVER in config files." |
| GA2.2 | M | **Reopened — see X8.1.** Not done: `PRAGMA key` is issued and silently ignored by plain SQLite, so the database is plaintext on disk. SQLCipher is not available in the toolchain and may never be; the replacement approach is field-level `std.encrypt` under X8.2 | **Enable SQLCipher encryption** — Switch from plaintext SQLite to SQLCipher for `~/.loke/loke.db`. Derive encryption key from OS keychain. All tables encrypted at rest. Spec: "All tables encrypted at rest via SQLCipher from OS keychain secret." |
| GA2.3 | L | Done | **Add Apache 2.0 license headers to all source files** — Add `// Copyright 2026 loke contributors\n// SPDX-License-Identifier: Apache-2.0` header to all 629 `.tk` files and all `.tkt` template files (using appropriate comment syntax). Spec: "ALL source files MUST include header at top." Currently 0% compliance. |
| GA2.4 | S | Done | **Auto-redact PII from all log output** — Implement log redaction filter per spec: "ALL log output passes through auto-redaction filter. Debug mode subject to same redaction rules as production." Ensure no PII appears in any log, console output, or error message. |
| GA2.5 | S | Done | **Localhost-only HTTP binding enforcement** — Verify HTTP server binds to `127.0.0.1` only (not `0.0.0.0`). If external binding configured, log as warning per spec. Verify CORS restricted to localhost origins. |

## Epic GA3: UX Alignment with Design Principles

*Accessibility, graduated warnings, progressive disclosure, and cost pre-estimation are specified in design principles but weakly or not implemented.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| GA3.1 | L | Done | **Accessibility overhaul** — Add ARIA labels to all interactive elements across all templates. Include: `aria-expanded` on collapsible panels, `aria-label` on icon buttons (thumbs, settings, nav), `role="dialog"` on modals, `aria-live="polite"` on dynamic content (typing indicator, pipeline console, loading states), skip navigation links, visible focus states, logical tab order. Currently only 2 ARIA labels in the entire app. Score: 2/10. |
| GA3.2 | M | Done | **Graduated warning system** — Implement 4-level warning system per spec: Info (non-interruptive, shown in pipeline view), Advisory (subtle indicator, dismissible), Warning (clear banner, requires acknowledgement), Block (cannot proceed without decision). Currently all alerts display at the same level. Apply to: PII detection, cost thresholds, sensitivity changes, policy violations. |
| GA3.3 | M | Done | **Progressive disclosure toggle** — Add "Simple View / Advanced View" toggle to chat page. Simple: just chat bubbles and send button. Advanced: schema panel, pipeline console, session stats, data preview. Currently all panels are visible (collapsed) which overwhelms new users. Spec: "Layer 0 (default) = 'Your prompt was processed and sent.'" |
| GA3.4 | S | Done | **Pre-send cost and token estimation** — Before sending a prompt, show estimated token count and cost based on selected model pricing. Allow user to see "This will cost ~$0.003 (245 tokens)" before confirming. Currently cost is only shown after the request completes. Spec: "Help users understand costs before spending, prevent accidental overspend." |
| GA3.5 | S | Done | **Cancel in-flight request** — Add a "Cancel" button visible during LLM processing. Allow users to abort a request that's taking too long. Currently there is no way to cancel once a request is sent. Spec: "Speed is a feature — if slow, users will bypass it." |
| GA3.6 | S | Done | **Feedback comment on thumbs-down** — When user clicks thumbs-down, show a lightweight text input with "What went wrong?" prompt. No required fields. Store comment alongside the rating. Spec: "Thumbs down always invites lightweight comment." Currently thumbs-down records rating but no comment field. |
| GA3.7 | S | Done | **"Why this sensitivity?" tooltip** — Add tooltip/popover on sensitivity badges (PUBLIC/CONFIDENTIAL/RESTRICTED) explaining how sensitivity was inferred. E.g., "CONFIDENTIAL: dataset contains patient_name and medicare_number columns." Spec: "Every intervention MUST include what's happening, why it matters, what the user can do about it." |

## Epic GA4: Architectural Completeness

*Core architectural components specified but not started: Governance Gateway (G1-G4), Agent Framework (AG1), Memory Palace (M1-M2), Policy Engine (A3), Onboarding (A4), Feedback Pipeline (A5/X5). These are tracked in existing epics but noted here for visibility.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| GA4.1 | S | **Done** | **Unblock G1-G4 governance epics** — Review and update the 17 governance stories (G1: gateway, G2: transparency, G3: monitoring, G4: dashboards) for current architecture. Remove any blockers related to ooke readiness (now resolved). Schedule for implementation. |
| GA4.2 | S | **Done** | **Unblock AG1 agent framework** — Review the 8 agent framework stories for current architecture. These depend on memory (M1) — establish dependency chain and schedule. |
| GA4.3 | S | **Done** | **Unblock M1-M2 memory system** — Review the 11 memory palace and AAAK stories. These are foundational for agents. Schedule for implementation. |
| GA4.4 | S | **Done** | **Implement A3 policy engine** — Move 4 stories from "Spec Done" to active development: policy loader, regulatory defaults, compliance feedback loop, audit reporting. |
| GA4.5 | S | **Done** | **Implement A4 onboarding** — Move 4 stories from "Spec Done": first-run wizard, pipeline visibility panel, savings dashboard, prompt approval workflow. |
| GA4.6 | S | **Done** | **Implement A5 feedback pipeline** — Move 3 stories from "Spec Done": in-app feedback form, issue report drafting, status updates. Also unblock X5 (3 stories): universal widget, feedback-to-development pipeline, feedback-driven learning loops. |

## Epic T15: Full Test Suite Audit and Expansion

*Audit all existing test suites against features and functionality. Create new tests for untested modules. Run full regression testing of loke and moke. Target: >80% module coverage with all tests passing.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| T15.1 | M | Done | **Audit existing test coverage** — Run `scripts/run_tests.sh`, document results. Cross-reference `docs/test-coverage.md` against current source modules. Identify: (a) modules with no test at all, (b) tests that fail to compile, (c) tests that compile but fail at runtime. Update coverage map. |
| T15.2 | L | **Done** | **Privacy pipeline tests** — Create/expand tests for: `core/privacy/pipeline.tk` (end-to-end anonymise + restore), `regex.tk` (all PII patterns: email, phone, TFN, Medicare, credit card, DOB), `placeholder.tk` (reversible masking), `consensus.tk` (all 4 strategies), `entity_routing.tk` (per-type layer assignment), `layer_health.tk` (graceful degradation), `filter_metrics.tk` (detection counts). Target: 100% of privacy modules tested. |
| T15.3 | M | Done | **Router and optimiser tests** — Create/expand tests for: `router/selector.tk` (sensitivity × cost × latency decisions), `router/router.tk` (intent classification), `optimiser/toon.tk` (TOON encode/decode roundtrip), `optimiser/cache.tk` (semantic cache hit/miss/eviction), `optimiser/budget.tk` (token budget tracking). |
| T15.4 | M | **Done** | **Governance and storage tests** — Create/expand tests for: `governance/kill_switch.tk` (engage/release/auto-release), `governance/policy.tk` (risk classification, decision types), `storage/audit.tk` (append-only logging, chain-of-custody hashing), `storage/db.tk` (migrations, parameterised queries). |
| T15.5 | M | **Done** | **Browser handler tests** — Create tests for all API handlers in `packages/browser/pages/api/`: health, pipeline, models, settings, privacy, savings, tabs, approve. Test: correct HTTP status codes, proper response format, error handling, input validation. |
| T15.6 | M | **Done** | **Moke page handler tests** — Create tests for moke page handlers: verify each handler renders its template, returns 200, handles missing templates gracefully. Test the connections page (MK9.1) handler specifically. |
| T15.7 | L | **Done** | **Integration tests — full pipeline flow** — End-to-end tests: (a) send prompt with PII through pipeline, verify anonymisation + LLM call + restoration, (b) trigger kill switch then send prompt, verify block, (c) send duplicate prompt, verify cache hit, (d) send prompt exceeding cost budget, verify warning. These require a running loke instance. |
| T15.8 | M | Done | **JavaScript utility tests** — Create test harness for the 9 MK9 JS utilities (`static/js/*.js`): json-parser, graphql-source, openapi-discovery, auth-methods, datagov-source, url-import, connection-manager, api-cache, rate-limiter. Test core parsing and transformation functions. Can use Node.js or browser test runner. |
| T15.9 | S | **Done** | **Fix known test failures** — Address `test_kill_switch` exit 139 (toke `.get()` dispatch regression). Fix any other test failures discovered in T15.1. Target: 100% of existing tests passing. |
| T15.10 | S | **Done** | **Run full regression and update coverage doc** — Execute `scripts/run_tests.sh` with all new tests. Update `docs/test-coverage.md` with final module coverage map. Target: >80% of source modules have at least one test file. Report total tests, pass rate, and any remaining gaps. |


---

# NO-CUSTODY ARCHITECTURE

> **Why this layer exists**
>
> loke's original core path is: detect PII, substitute placeholders, send the redacted text to an
> external model. Peer-reviewed work establishes that this is not an effective privacy defence —
> large models infer and re-identify obscured entities from surrounding context (Staab et al.,
> ICLR 2024, arXiv:2310.07298; Staab et al., ICLR 2025, arXiv:2402.13846; RUPTA, arXiv:2407.11770;
> the Text Anonymization Benchmark, *Computational Linguistics* 48(4), 2022). Redaction reduces
> disclosure; it does not prevent identification.
>
> The architecture that does not depend on redaction working is one where **the model never receives
> the data at all**: loke sends a schema profile and the user's intent, the model returns an
> executable artifact, and loke runs that artifact locally against data that never leaves the device.
>
> **Before writing or repositioning any claim in this layer, read
> `docs/research/disclosure-measurement-findings.md`.** It records what the external literature
> already establishes, what remains genuinely open, and — in §8 — a list of nine things loke must not
> claim because they are already published or are definitions rather than findings.
>
> loke already implements this, in one place, without having named it. moke's Insight Lab sends only
> column names, receives an analysis specification, and executes it locally
> (`packages/moke/src/ml/proposal.tk`, `packages/moke/templates/insight.tkt`). This layer makes that
> pattern the primary architecture rather than an accident, and demotes anonymise-and-send to an
> explicitly-labelled fallback for the cases that genuinely require prose in the prompt.

## Epic NC1: No-Custody Artifact Execution

*Make schema-out / artifact-back / execute-locally the default path. The model receives names, types and intent; it never receives rows.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| NC1.1 | M | **Done** | **Define the artifact contract** — Specify the closed operation set an artifact may express, building on the existing `$dashboard` DDL (`packages/moke/src/ddl.tk`) and the 15 operations in `packages/moke/src/compute.tk` (`opcount`, `opsum`, `opavg`, `opmin`, `opmax`, `opgroup`, `optimeseries`, `optopn`, `opdistribution`, `opcorrelate`, `oppercentile`, `opcountby`, `oplatest`, `opdistinct`, `opjoin`). The set MUST remain non-Turing-complete and MUST NOT include arbitrary code: toke exposes no sandboxing primitive (`process.tki` offers spawn/wait/kill only, with no jail, resource cap or syscall filter), so a closed op set is the only safe design. Write `docs/specifications/artifact-contract.md` with the grammar, the validation rules, and the explicit rejection criteria. |
| NC1.2 | M | | **No-custody schema profile** — Build a profile emitter that carries column names, inferred types, cardinality, null-rate and row count, and **nothing else**. This replaces `packages/moke/src/hooks.tk::profiletotoon` and `packages/core/src/optimiser/profiler.tk::totoonschema`, both of which currently embed **three real sample values per column plus real min/max/mean** — so today's "schema-first" request ships real data. Acceptance: a profile built from a dataset containing a unique sentinel value contains that value zero times. |
| NC1.3 | M | | **Wire the Insight Lab's proposal path** — The no-custody LLM path never executes: `packages/moke/templates/insight.tkt:897` posts `{columns: [...]}` while `packages/moke/pages/api/ml.tk:146-160` requires at least one of `schema_toon`, `num_cols`, `cat_cols` and returns 400 otherwise, so the client silently falls back to `heuristicSuggestions()`. Fix the contract, and fix `packages/moke/src/ml/proposal.tk`'s `if(i<n){...}` loops, which process only one element where `lp` was intended. |
| NC1.4 | L | **Done** | **Send the schema on the dashboard path** — `packages/moke/templates/dashboard.tkt`'s `buildPhase1Prompt(question)` sends only the question while telling the model *"You have access to this dataset"*. It does not. Pass the NC1.2 profile. Remove the instruction `Use realistic sample values that match the dataset schema` from both system prompts (`:1019` and `:1095`), and the equivalent clause in `templates/chat.tkt:2527`. |
| NC1.5 | M | **Done** | **Make fabricated values inadmissible** — Drop `normaliseDDL`'s ingestion of the model's `data` array into the render slot (`dashboard.tkt:448-468`) and the `Math.round(Math.random() * 900 + 100)` chart fallback (`:791-794`). A card with no locally-resolved value MUST NOT display a number. |
| NC1.6 | M | **Done** | **Provenance state on every card** — Render one of `resolved` / `unresolved` / `no-data` per card. `renderMetricCard` (`dashboard.tkt:714`) currently emits `→ computed locally` **unconditionally**, including on values the model invented; the only honest signal today is a `console.info` no user sees. `resolveQueries` MUST record why each `continue` fired so the reason can be surfaced. |
| NC1.7 | L | | **Promote local execution into core** — `packages/moke/src/compute.tk::execute()` is a complete local query engine with no production caller. Make it (or a core equivalent) the execution target for artifacts, and add a second backend using toke's parameterised SQL (`std.db`'s `db.many` with bound parameters) so generated queries can run against the local store without string interpolation. |
| NC1.8 | M | | **Demote anonymise-and-send to a labelled fallback** — Keep the path for tasks that genuinely need prose, but make selecting it explicit, record it as a custody event (DA1), and state its residual risk at the point of use. Update the pipeline so no-custody is attempted first and the fallback is a deliberate, logged decision rather than the default. |
| NC1.9 | M | | **Fail closed** — The defect is in **core, not the browser**: `packages/core/src/privacy/pipeline.tk:568` initialises `anonymisedtext` to the raw input and `:582` reassigns it from `anonymisetext(text; deduped)`. When the NER and Presidio layers are both unreachable the pipeline logs degraded mode (`:392`, `:523`, `:540`) and continues with an empty entity list, so `anonymisetext` returns the input unchanged and `packages/browser/pages/api/pipeline.tk:125-126,171` transmits it — while still reporting an `entities_found` count and a sensitivity label. A filter that fails open is worse than one that fails closed. Add a health gate: when no detection layer is healthy, return 503 and never dispatch. Fixing it in core fixes every caller at once; fixing it in the browser handler would leave the CLI path open. |
| NC1.10 | L | | **Bound the query-shaped channel** — A returned artifact is itself an information channel. An adversary able to shape queries and observe results across several turns can extract cell values a piece at a time, including by binary search, without ever being sent a row. So "the model never receives data" is true at the byte level and not necessarily at the information level, and **no published benchmark tests this** (`docs/research/disclosure-measurement-findings.md` §11). Bound it: per-session limits on result cardinality and on repeated near-identical predicates, detection of value-probing query sequences, and disclosure accounting that counts *results returned to the model* as well as bytes sent. Until this is bounded, the no-custody claim must be stated with the limitation attached. |
| NC1.11 | S | **Done** | **Correct the architecture documents** — `docs/features-moke.md:200` states the schema is sent on the dashboard path; it is not. Update `docs/architecture.md` so the pipeline diagram shows the no-custody path as primary and the redaction path as fallback. |

## Epic DA1: Disclosure Accounting

*Record what actually left the device on every external call. Today nothing does.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| DA1.1 | M | **Done** | **Define the disclosure record** — Per external call: bytes transmitted, estimated tokens, field/column names disclosed, entity types and counts, whether any real data values were included, a custody flag (`no-custody` / `redacted-data` / `raw`), model and provider, and the correlation ID. This is the substrate every later claim depends on. |
| DA1.2 | M | | **Create the missing metrics table** — `packages/core/src/metrics/collector.tk` writes to `metrics_raw`, which **no migration creates** (`packages/core/src/storage/migrations.tk` defines only `schema_migrations`, `settings`, `audit_log`, `placeholder_maps`, `sessions`), so `record()` fails at runtime. Add the migration, extend the schema with the DA1.1 fields, and fix `summarise()`'s hardcoded `avgsavingpct:0.0` (`collector.tk:91`). |
| DA1.3 | M | | **Wire the collector** — Nothing anywhere calls `collector.record`. Call it on every external dispatch. Acceptance: after one request, exactly one row exists with non-null disclosure fields. |
| DA1.4 | S | | **Typed stage records** — `packages/moke/src/console_log.tk`'s `$logentry{stage, status, detail, durationms, ts}` already rides along in the pipeline response and already reports column counts, but `detail` is free text. Add typed disclosure fields so the per-stage record is machine-readable rather than a string. |
| DA1.5 | S | **Partial — the fabrications are gone; the real figures need DA1.2.** `packages/browser/templates/savings.tkt` was 238 lines reporting thirteen invented numbers under "Cost & token savings / Today": $1.47 saved, 38% cache hit rate, 1.31x compression, 14 620 chars removed, 24% average prompt reduction, 142 optimised requests, and a per-provider table with costs to the cent for 142 requests that never happened. The page had **no data source at all** — no fetch, no storage read — and directly contradicted `metrics-baseline.md`, which says no cost, cache or token-reduction figure has been measured. Every figure now renders as unmeasured with the story that would produce it. The chat.tkt:2764 reference in this story is stale; that code is the locally-computed series path and is correct | **Surface it** — Show disclosure per request in the pipeline panel and in aggregate on the savings view, replacing the hardcoded percentages currently in `packages/browser/templates/savings.tkt:138,225` and `packages/moke/templates/chat.tkt:2764`. |
| DA1.6 | M | | **Replace the stubbed metrics module** — `packages/core/src/audit/metrics.tk:37-87` returns zeros from every function and `""` from `export()`, while ignoring the `store` and `period` arguments it is passed. Implement against DA1.2. |

## Epic EM1: Exposure Metric

*A disclosure measure that is defined, computed and validated — not asserted. Depends on DA1 and research spike RS2.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| EM1.1 | M | **Done** | **Specify the metric on established axes** — Adopt the three axes already established for disclosure risk — **singling out, linkability, inference** — each as a *control-corrected* rate, rather than inventing a scheme (`docs/research/disclosure-measurement-findings.md` §4). A vector, never a weighted-sum scalar with hand-chosen weights. Quasi-identifier *combination* presence is the strongest single component; presence of any real value is a **gate, not a summand**; bytes and tokens are the strawman baseline to beat, not a privacy measure. State the threat model per component — mixing provider-side linkage, third-party analytics exposure and model memorisation into one number is the specific error the consensus literature warns against. If a single display number is needed, present it explicitly as a lossy projection of the validated vector. |
| EM1.2 | L | | **Validate the metric, do not assert it** — In the order of persuasiveness set out in `docs/research/disclosure-measurement-findings.md` §7: (a) **dose-response** — inject disclosure of known magnitude and show the metric scales with the dose; (b) **Spearman ρ against attack success across ≥30–50 *configurations*** (arm × dataset × model × redaction level, not individual requests) with bootstrap intervals; (c) against **two structurally different attacks** — linkage and attribute inference — since validating only against the attack the metric was built around is circular; (d) reported as **TPR at low FPR on a log ROC**, not AUC, because one confident identification is the breach. Skip membership inference against model weights: prompts to a frontier API are not training data under standard retention, and reaching for it looks like instrument-shopping. If the metric does not correlate, report that. |
| EM1.3 | M | | **Comparative measurement across arms** — Report exposure for the three arms of CB1 (data-in-prompt, schema-only, full no-custody) on the same workload, so the architectural claim is quantified as *relative reduction*, never as elimination. |
| EM1.4 | S | | **Surface through the Scorecard pattern** — `docs/design-principles.md:145` already defines an ambient, queryable scorecard tracking "privacy, cost, compliance, local ratio". Exposure belongs there, not in a warning. |
| EM1.5 | S | **Done** | **State the limits** — Publish, alongside the metric, what it cannot measure: inference from context, provider-side retention and training, and correlation across accounts. The metric bounds disclosure, not consequence. |

## Epic PL1: Placeholder Correctness and Linkage

*Fix a live restoration bug, then make the consistency decision deliberately. Depends on research spike RS1.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| PL1.1 | M | | **Fix entity collision — live correctness bug** — `packages/core/src/privacy/ner.tk:83-87` and `ner_local.tk:59-62` both return a **hardcoded constant**, `"[" + label + "_NER_1]"`. Every `PERSON` detected by NER becomes `[PERSON_NER_1]`, so three people in one prompt collapse to one token, and `placeholder.tk:42-55 restore()` then replaces that token with whichever original it encounters first. **A response can therefore return person A's name where person B was referenced.** This is both a correctness defect and a disclosure defect, and it means `docs/security-audit-checklist.md:54`'s `[CRITICAL]` round-trip assertion cannot hold for multi-entity input. |
| PL1.2 | S | | **Fix the off-by-one in restore** — `placeholder.tk:46` uses `if(i>len){br}` where `len=str.arraylen(...)`, reading one index past the end. The same `if(i>n){br}` idiom appears in `packages/core/src/eval/bench.tk:85,128,171` and `privacy/test_harness.tk:181,190,229`; fix them together. |
| PL1.3 | M | | **Decide scoping deliberately** — Placeholder indices are ordinal *within a single request* and shared across entity types (`makeplaceholder(entitytype, index)` called with the whole array's length: `regex.tk:85`, `presidio.tk:166`), so the same value gets different tokens in different prompts. Choose between stable-per-entity tokens (better coherence, introduces a cross-prompt linkage channel) and per-session salted tokens (defeats it, costs cross-session continuity), implement the choice as a documented default with the surrogate *style* — opaque token versus type-consistent realistic value — as a second explicit axis. Note the defence is not itself novel: published work already scopes mappings per conversation (`docs/research/disclosure-measurement-findings.md` §2). |
| PL1.4 | L | | **Measure the residual** — Run the five-arm scoping ablation specified in `docs/research/disclosure-measurement-findings.md` §6 (persistent global / per-session / per-request / no-substitution / **random re-pairing control**), crossed with surrogate style. Report **control-corrected linkage advantage** against the re-pairing arm — never raw accuracy, since type-consistent surrogates leak structure and inflate the naive chance rate — with Wilson intervals, plus TPR at 1% and 0.1% FPR. The headline is the residual after the defence. Framing constraint: the *existence* of a linkage channel from stable surrogates is a definition, not a finding; only the magnitude, the scoping frontier and the residual are results. |
| PL1.5 | S | **Done** | **Correct the documents that assume a property the code lacks** — `~/tk/toke-website/templates/loke.tkt:51` publicly claims "consistent placeholders"; `docs/specifications/regulatory-defaults.md:99` reasons about whether consistent placeholders meet the Recital 26 threshold; `packages/core/src/privacy/placeholder_store.tkc.md:1` claims restoration "across sessions" when the store is scoped `WHERE request_id=?` with 24-hour expiry. All three describe behaviour that does not exist. |

---

# VERIFICATION PROGRAMME

> **Why this layer exists**
>
> loke publishes specific numbers — token reduction, pipeline overhead, classification latency,
> compression ratio, retrieval latency, cache hit rate — and none of them is produced by a
> measurement. The methodology, however, already exists and is genuinely rigorous:
> `docs/research/toon-benchmark-methodology.md` specifies named baselines, twelve task types, four
> data shapes, a licensed dataset table, N with warm-up discard, BCa bootstrap confidence intervals,
> Wilcoxon signed-rank tests, Benjamini-Hochberg correction, Cliff's delta, SHA-256 frozen snapshots
> and judge calibration against human annotation. `docs/research/research-proposal.md` §5.2 specifies
> per-entity precision/recall/F1 and marginal recall per added detection layer.
>
> The task is therefore **implementation, not design**. One thing must be built first: `std.test`
> exposes three assertion functions over string comparison and cannot record a numeric result, so
> today a test can prove a threshold was met but cannot publish the value it measured.

## Epic VM1: Verification Measurement Substrate

*Build the apparatus that lets a measurement be recorded, repeated and reproduced. Prerequisite for every other story in this layer.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| VM1.1 | M | **Done** | **Numeric result sink** — A structured results file (one JSON object per measurement) carrying the value, units, N, the workload identifier, the tokenizer where relevant, the model and its pinned version, the seed, the timestamp and the toolchain commit from `TOOLCHAIN.lock`. `std.test` cannot carry a number, so measurement runs must write results directly rather than asserting through the test harness. |
| VM1.2 | S | **Done** | **Pin what is currently unpinned** — `packages/privacy-filter/server.py:34-38` loads `openai/privacy-filter` with no revision, so the model is whatever the hub resolves at first run. Pin the revision. Record every external model's exact version string in each result. |
| VM1.3 | M | Partial — repetition with warm-up discard and bootstrap intervals are implemented in `benchmarks/lib/result.py`, and a repeated measurement with no interval is rejected. **The interval is a percentile bootstrap, not the BCa the methodology specifies**, and says so rather than claiming BCa | **Repetition and intervals** — Run each configuration N times with the first run discarded as warm-up, and report BCa bootstrap confidence intervals, exactly as `docs/research/toon-benchmark-methodology.md` already specifies. No single-run number may be published. |
| VM1.4 | M | **Done** | **Containerised harness** — No Dockerfile exists anywhere in the repo. Add a pinned container so a measurement can be reproduced by someone else, and record the image digest in each result. |
| VM1.5 | S | **Done** | **Numbers out of CI** — `.github/workflows/ci.yml` uploads one artefact containing pass/fail counts only. Add a second artefact carrying measurement results, so a number can be traced to the commit that produced it. |
| VM1.6 | S | | **Repair and wire the existing harness** — `packages/core/src/eval/bench.tk` is a working keyword-scoring benchmark with no callers, no persistence, and loop bounds that read one element past the end (`:85`, `:128`, `:171`). Give it an entry point, persist through VM1.1, and add the `loke benchmark` subcommand missing from `packages/cli/src/commands.tk`. |
| VM1.7 | M | **Partial — baselines done, and they matter.** [`benchmarks/toon/`](../benchmarks/toon/README.md) measures B1/B2/B3 with real tokenisers (tiktoken, offline) through the result sink; 7 self-test guard groups in the gate. The finding is about the baseline rather than any technique: **whitespace removal alone is worth 1.35x-1.80x**, so a figure quoted against pretty-printed JSON is mostly measuring indentation, and YAML is worse than minified JSON on every payload. Published in [`metrics-baseline.md`](metrics-baseline.md). **TOON itself is not measured** — no faithful encoder exists outside toke, and one written from the format's description would measure this harness's own invention under TOON's name. Anthropic and Google token counts are absent, not approximated. The accuracy half needs model spend (decision M) | **Implement the TOON methodology** — Build `benchmarks/toon/` to the specification already written in `docs/research/toon-benchmark-methodology.md`: baselines B1 (raw JSON, primary), B2 (minified), B3 (YAML); the named dataset table with licence checks and SHA-256 snapshots; token counting per provider tokenizer rather than the character-length ratio `optimiser/toon.tk:282` currently computes. |
| VM1.8 | S | **Done** | **Single source for published numbers** — Create `docs/metrics-baseline.md` as the only file the project publishes figures from, each with its tokenizer or "bytes", its N and its date; and adopt the precedence rule that any other page disagreeing with it is a bug. Publish negative results there too. |

## Epic CB1: Correctness Benchmark — Three Arms

*Prove that a no-custody architecture can do the work, or find out that it cannot. Depends on VM1 and research spike RS3.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| CB1.1 | M | **Done** | **Define the three arms, and the honest framing** — (A) data in the prompt; (B) schema only, model answers directly; (C) schema only, model returns an artifact, loke executes locally. State which model does what in each arm: arm C does not use a *local* model for generation at all, only for custody, which answers the "handicapped by weak local models" objection. **Framing constraint:** the arm-C data flow is not novel — it is how every text-to-SQL benchmark already works and it ships in several commercial products (`docs/research/disclosure-measurement-findings.md` §10). This epic measures the **cost** of strict no-custody, candidly, and should be expected to lose ground on some question classes; it does not claim the architecture as an invention. |
| CB1.2 | L | | **Execution-based scoring harness** — Primary benchmark: **InfiAgent-DABench** (257 closed-form questions over 52 CSV files, Apache-2.0, Python sandbox), because it is the only candidate where paste-the-data is the honest status-quo baseline; on the text-to-SQL suites schema-only is already the norm, so measuring there proves nothing. Score by executing the result with a gold-executability invariant asserted first. **257 items gives roughly ±6 pp binomial confidence, so comparisons must be paired on identical items and tested with McNemar, not as two independent proportions.** Secondary: BIRD Mini-Dev (500 items), noting its efficiency metric is computed only over queries that pass execution accuracy and is therefore not comparable across systems with different accuracy. **Avoid Spider 2.0-Snow** — audited annotation-error rate 62.8–66.1%. |
| CB1.2a | M | | **Freeze the output-contract reformat step — largest validity threat** — DABench post-processes model output into its answer template with a separate reformat model, and that step is worth **up to 32 accuracy points** (Mistral-7B 6.23 → 38.67; GPT-4 72.76 → 78.99). That is larger than any plausible effect of the disclosure regime under test. If arm C returns a structured spec (naturally parseable) and arm A returns prose with an embedded answer, the experiment measures format compliance and calls it privacy-preserving correctness. The reformat step must be **identical, frozen and applied symmetrically to every arm**, and both reformat-on and reformat-off numbers reported. |
| CB1.3 | M | **Done** | **Output-contract control** — Adherence to the required output format materially changes scores on published analysis benchmarks, so the contract must be treated as a controlled variable and reported, not left implicit. |
| CB1.4 | M | | **Pre-empt the corrected-benchmark critique** — Published benchmarks carry large annotation-error rates (BIRD Mini-Dev 52.8%; Spider 2.0-Snow 62.8–66.1%), moving scores by −7% to 31% and rankings by up to nine positions across 16 re-evaluated agents. Cite the journal version (arXiv:2601.08778 = PVLDB 19(5)), not only the workshop precursor. **loke's cheaper and stronger pre-emption:** because the comparison is within-benchmark and paired — same question, same data, two disclosure regimes — annotation errors are a *shared* confound that largely cancels in the difference. Say so, then report paired deltas rather than leaderboard absolutes, hand-audit a stratified sample of ~100 items, publish the audit, and report raw and audited subsets separately. |
| CB1.5 | M | | **Cost and token accounting per arm** — Tokens per completed task against arm A as the named baseline. This is what makes "minimising token spend" falsifiable; today no baseline workload is defined anywhere. |
| CB1.6 | M | | **Position against the closest prior art on its own datasets** — The nearest work formalises minimisation as an ordinal lattice over per-entity actions (retain, abstract, redact) and searches it under a utility floor, but **every point in that lattice still sends data to the model**. loke's no-custody path sits outside it, made feasible by moving the computation rather than the data (`docs/research/disclosure-measurement-findings.md` §5). That is a real contribution **only if** loke demonstrates comparable utility at a comparable operating point **on the same datasets** that work uses; anything less reads as redacting everything and losing the task. Also reuse its two black-box recovery audits verbatim so loke's numbers are directly comparable to a published baseline. Schema-only prompting is already standard in text-to-SQL — cite it as support, do not deny it. Depends on RS4. |

## Epic AD1: Adversarial Corpora

*Ground truth for detection, and real attacks for enforcement. None of this exists today.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| AD1.1 | L | **Done** | **PII ground-truth corpus** — No labelled corpus exists in the repo and no public dataset is referenced anywhere in code. Build or import one in the span format `[{text, entities:[{start,end,type}]}]` that `docs/epics-and-stories.md` F3b.9 already specifies, with a documented matching rule (exact span versus overlap — currently unspecified anywhere) and locale coverage including Australian identifier types. |
| AD1.2 | M | Partial — regex layer measured (`metrics-baseline.md`); the compiled detector and the recall floor need the toolchain | **Entity-level scoring with a recall floor** — False negatives leak identity, so recall is the decisive metric: set a high floor on direct identifiers and report precision as a utility cost, not as the headline. `packages/core/src/privacy/evaluation.tk` already implements correct precision/recall/F1 with zero-division guards but has no callers and no data source — wire it. |
| AD1.3 | M | | **Marginal value per detection layer** — Report what each added layer contributes in recall and what it costs in false positives, as `docs/research/research-proposal.md` §5.2 already specifies. This is the evidence that determines whether the multi-layer design earns its complexity. |
| AD1.4 | M | Partial — sidecar applies and reports the threshold; the toke client still does not pass one | **Operating-point control** — The sidecar's `confidence_threshold` is declared in `packages/privacy-filter/models.json` and **never applied**: `/detect` and `/anonymise` return every classifier span regardless of score. Without it there is no operating point to tune and no precision/recall curve to report. Plumb it through `packages/core/src/privacy/sidecar_client.tk`, which currently returns unparsed response strings with no timeout or retry. |
| AD1.5 | L | | **Injection and exfiltration corpus** — Single-turn injections now yield near-zero attack success on frontier models while a persistent multi-step attack reaches **95.5%** on the same model, so a single-turn corpus scores misleadingly well. Build around loke's own invariants and the four attack families in `docs/research/disclosure-measurement-findings.md` §14: outbound disclosure (including the iterative query-oracle class of NC1.10), artifact abuse with parser-differential variants between validator and executor, data-flow exfiltration, and **persistence** — injections landing in cached schema descriptions, column comments, saved queries or few-shot examples and firing on a later request. If loke caches schemas or learns from prior queries, persistence is the highest-severity untested class. **Every attack case needs a paired benign twin**, and every configuration must report a 4-tuple: benign utility, utility under attack, attack success rate, and **false-block rate** — over-refusal is the failure mode a schema-enforcing proxy is most exposed to. Define the acceptance gate as a composite up front. Add an adaptive tier: publish the rules, let a red team optimise against them for a fixed budget, report static and adaptive separately. Extend the published data-flow exfiltration methodology rather than reinventing it. |
| AD1.6 | M | **Done** | **Enumerated bypass corpus — six classes** — Each has vendor or RFC authority and is independently testable (`docs/research/disclosure-measurement-findings.md` §14): (1) default TLS-interception do-not-decrypt exemptions, shipped enabled — test whether any provider endpoint falls in one; (2) certificate pinning in native apps and SDKs, where the documented remedy is *deliberate* loss of visibility; (3) split tunnelling, including URL-based exclusion shipped as a browser extension — test whether a user can exclude an API host without admin rights; (4) browser extensions, both as a bypass vector and as the only enforcement point surviving encrypted transport metadata; (5) **encrypted transport metadata — RFC 9849 TLS Encrypted Client Hello, Standards Track, March 2026, with OpenSSL support shipped**, against which SNI-based rules fail *silently*, plus QUIC/HTTP-3 and DNS-over-HTTPS; (6) direct-to-API egress with the caller's own credentials, for which **no vendor documents a reliable network-layer control**. loke additionally ships `--no-privacy` (`locales/en.json:390`) and its proxy requires opt-in client reconfiguration rather than intercepting anything. Publish as "enforced at N of 6, with these requiring endpoint or managed-policy co-deployment" — never as unbypassability. |
| AD1.7 | M | | **Wire Epic F3b's orphaned modules or withdraw the claim** — Ten multi-layer privacy modules have zero importers: `filter_registry`, `layer_config`, `consensus`, `filter_metrics`, `evaluation`, `sidecar_client`, `layer_health`, `entity_routing`, `org_policy`, `test_harness`. `privacy/pipeline.tk` imports none of them and uses its own `dedupentities()`. `consensus.tk:24 resolveoverlaps` ignores its `strategy` argument entirely and marks every detection `action:"mask"`, so the four named strategies exist only as display strings. Either connect them or mark the epic unimplemented. |
| AD1.8 | S | | **Un-exclude the existing harness** — `packages/core/src/privacy/test_harness.tk` holds seven real PII cases and is explicitly skipped by `scripts/run_tests.sh:25`, so it has never run in CI. |

## Epic GA5: Assurance Evidence

*Make the audit trail something an assessor could actually rely on, and be precise about what it does and does not evidence.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| GA5.1 | S | | **Fix audit timestamps** — `packages/core/src/storage/audit.tk:47` writes the **string literal** `'now()'` into `created_at`, so every row carries the same seven characters instead of a time. `ORDER BY created_at` is therefore undefined and the period filters in `packages/core/src/governance/dashboard.tk:63,75,86,97` cannot work. Without a time basis there is no period, and without a period there is no evidence of a control operating *over* one. |
| GA5.2 | M | | **Real hash chain** — `audit.tk:38` computes `hash = str.concat(correlationid, eventtype)`. That is not a hash, it covers none of the payload, and `prev_hash` is stored but is **not an input**, so nothing chains. Compute a cryptographic digest over a canonical serialisation of every persisted field **including the previous row's hash**, using an unambiguous field separator and a defined genesis value. toke provides `crypto.sha256`, `crypto.tohex` and `crypto.constanteq`. |
| GA5.3 | M | | **Chain verification** — No verifier exists anywhere in the codebase. Add one that reads forward in insertion order, recomputes each digest, and reports the first divergent row. Expose it so a user can check their own trail. Acceptance: detects a field mutation, a digest mutation, **and a deleted row** — deletion is the case that proves the chain actually chains. |
| GA5.4 | S | Blocked — file carries uncommitted migration edits; belongs with the legacy `src/` removal in **F10.12** | **Delete the duplicate implementation** — `src/core/audit/trail.tk` is worse than the live one: `chainhash()` returns `str.fromi32(str.len(acc))` (a string length), `verifychain()` is hardcoded `<true`, and `newevent()` sets `let now:i64=0`. It has no callers and has never compiled. Remove it rather than fixing it. |
| GA5.5 | M | | **Persist the decision trace** — `packages/core/src/governance/trace.tk`'s `$decisiontrace` has seventeen well-chosen fields, no caller, no table and no insert; `complete()` writes a single log line and discards the structure. Persist it, and add the fields an assessor needs that exist nowhere in `$auditevent`: policy decision, entities detected, detection layer, approval or override outcome, and kill-switch state. |
| GA5.6 | M | | **Fix the report engine** — `packages/core/src/governance/report-engine.tk:86,104,122,140,158` all query `SELECT timestamp, event_type, detail FROM audit_log`, but `audit_log` has neither a `timestamp` nor a `detail` column, so all five report types fail. `buildcompliancerows` also hardcodes `generatedat:"now"`. |
| GA5.7 | M | | **Replace hardcoded compliance results** — `packages/core/src/governance/compliance.tk:42-56,82-90` returns a literal `PASS` for "PII anonymised before cloud" and "Audit trail complete" without querying the store it is passed. Compute every check from real state. Note the module is already honest about encryption at `:91-95` — that honesty should propagate outward, not be overwritten. |
| GA5.8 | S | **Done** | **State what the trail evidences** — Document plainly that the record is a per-interaction usage and cost ledger, that it deliberately excludes prompt content and placeholder values (`docs/architecture.md:207`), and therefore what it can and cannot support. Distinguish design effectiveness at a point in time from operating effectiveness over a period, and do not describe the ledger as the latter. |
| GA5.9 | S | | **Enforce append-only** — The trail is described as append-only but nothing enforces it: no trigger, no immutability constraint, and ordinary `DELETE`/`UPDATE` on `audit_log` are unrestricted. |

## Epic RG1: Regulatory Alignment — ANZ First

*Reduce every regulatory statement to what is actually shipped, and add the standards that matter for the primary market.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| RG1.1 | M | Partial — policy specification written as [`apra-cps-234.yaml`](specifications/policy-examples/apra-cps-234.yaml); the `.tk` preset module and `regulations.tk` entry are queued behind the green build | **APRA CPS 234 preset** — Currently the standard exists as a single string in `packages/moke/tests/test_governance.tk:41` and nowhere else: no preset module, no entry in `packages/core/src/policy/regulations.tk`, no specification section, no UI option. Build it as a real preset with information-security control mapping. |
| RG1.2 | M | Partial — policy specification written as [`apra-cps-230.yaml`](specifications/policy-examples/apra-cps-230.yaml); the `.tk` preset module is queued behind the green build | **APRA CPS 230 preset** — Absent from the codebase entirely. Operational risk and service-provider management are precisely what a third-party model dependency engages, so this is the more consequential of the two for the primary market. |
| RG1.3 | M | | **Australian Privacy Act reforms** — Named at `docs/specifications/regulatory-defaults.md:272` with zero implementation. Add the preset fields and rules the reforms require. |
| RG1.4 | S | **Done** | **Reword "makes you compliant" to "ships a preset for"** — Three statements cross the line: `docs/specifications/regulatory-defaults.md:58` (anonymisation "removes the need for" a lawful basis), `docs/privacy-filters.md:226` (the pipeline "satisfies" Article 25), and `docs/privacy-filters.md:227` (deleting the local mapping "enables Article 17" — factually wrong, since it does nothing about data already transmitted and retained). |
| RG1.5 | S | **Done** | **Withdraw the absolutes** — `docs/specifications/regulatory-defaults.md:456` claims all eighteen HIPAA identifier categories are detected and replaced "No exceptions", which `docs/threat-model.md:751` directly contradicts ("no combination of layers guarantees 100% detection"). The threat model is right. |
| RG1.6 | M | **Done** — [`control-framework-mapping.md`](control-framework-mapping.md): NIST AI RMF 1.0, ISO/IEC 42001:2023, and the OWASP top-tens for LLM and agentic applications, with per-row gaps and a five-item blocking list. Uses an **inert** status distinct from **absent**, because code that looks like a control and is not is worse than a known gap | **Control-framework mapping** — Map loke's controls to NIST AI RMF, ISO/IEC 42001, and the OWASP top-tens for LLM and agentic applications, as a reference table with honest coverage gaps rather than a compliance claim. |

## Epic RS: Research Spikes

*Time-boxed investigations that must complete before the stories depending on them can be specified properly.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| RS1 | M | **Done** | **Pseudonym linkage** — Complete; findings in `docs/research/disclosure-measurement-findings.md` §2, §3, §6.
| RS2 | M | **Done** | **Exposure metric foundations** — Complete; findings in `docs/research/disclosure-measurement-findings.md` §4, §5, §7.
| RS3 | M | **Done** | **Benchmark harness requirements** — Complete; findings in `docs/research/disclosure-measurement-findings.md` §13, §14. |
| RS4 | M | **Done** | **Prior art and differentiation** — Complete; findings in `docs/research/disclosure-measurement-findings.md` §10, §12, §15, §16. |

## Epic X6: Claims Register

*One file that maps every public assertion to its evidence, and a gate that keeps it honest.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X6.1 | M | **Done** | **Create `docs/claims.md`** — Every externally-visible claim in `README.md`, `docs/features-loke.md`, `docs/features-moke.md`, `docs/architecture.md` and the public site, with a verdict (verified / partial / stub / absent), the implementing code at file and line, and the test or measurement that proves it. Seed it from the audit already completed. |
| X6.2 | S | **Done** | **Mark unverified claims inline** — Apply an explicit marker to every claim in the register that is not verified, so the assertion stays visible but flagged, using the withdrawal idiom already established on the public site rather than inventing a new one. |
| X6.3 | S | **Done** | **CI gate** — Fail the build when a claim marked verified has no evidence pointer, and when a published figure has no corresponding entry in `docs/metrics-baseline.md`. `scripts/check_claims.py` implements both checks (standard library only, `--check` mode for CI) and runs in CI through `scripts/quality-gate.sh --step checks`, which the `static-checks` job invokes — so the gate is live and needs no compiler. It is called from the gate script rather than named directly in the workflow, which is why a grep of `.github/` finds nothing. |
| X6.4 | S | **Done** | **Correct the coverage statement** — `docs/test-coverage.md` reports 35.5% module coverage, which counts files that have a test rather than modules actually exercised; of 86 test files, 54 carry an explicit stub marker and re-declare the module under test instead of importing it, and only about 12 import real production code. State both numbers and what each means. |
| X6.5 | S | **Done** | **Withdraw unsupported results language** — `docs/research/research-proposal.md:15` states "We present empirical benchmarks demonstrating" token savings, detection accuracy and call reduction figures that no measurement produced. Rewrite as proposed methodology pending execution. |

## Epic X8: Security Guarantee Hardening

*The controls that documents describe as protections and that do not operate. Cited in thirteen files
before this epic existed, which is why it is written now.*

> **Unblocked 2026-09-20.** `std.encrypt` is a toke library and the toolchain is available, so this epic
> is live. X8.5 stays held behind NC1.9 because `pipeline.tk` must not be edited until the fail-open is
> fixed. The stories still queue behind a compiling build — see F10.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X8.1 | S | | **Reverse the GA2.2 "Done" marking** — GA2.2 "Enable SQLCipher encryption" is marked **Done** in this document while `packages/core/src/governance/compliance.tk:91-95`, `docs/claims.md` A10, `docs/threat-model.md:181`, `docs/metrics-baseline.md:162`, `docs/security-audit-checklist.md:111` and both APRA presets correctly state the opposite. `packages/core/src/storage/db.tk:37-43` issues `PRAGMA key`; the toolchain links plain `-lsqlite3`, which ignores it and returns success. Mark GA2.2 not done and point it here. A story marked Done for a control that does not operate is the most dangerous kind of backlog entry. |
| X8.2 | L | | **Encrypt the mapping table at rest** — The placeholder↔value mapping is the highest-value data in the system (`docs/threat-model.md:181` rates it Maximum) and is plaintext on disk. SQLCipher is not available and may never be: toke links plain SQLite and there is no sqlcipher anywhere in the toolchain. Use field-level encryption via `std.encrypt` (`aes256gcmencrypt`/`decrypt`/`keygen`/`noncegen`, `hkdfsha` — verified present) with a per-record nonce, applied in `packages/core/src/privacy/placeholder_store.tk`. Do not reinstate a database-level claim. |
| X8.3 | M | | **Keychain-only key handling** — The key is derived through the OS keychain and exists nowhere else: no key file, no environment-variable fallback, no default. A missing key fails the operation rather than falling back to plaintext. Test that removing the keychain entry makes the store unreadable rather than transparently readable. |
| X8.4 | M | | **Verifiable deletion** — "Delete everything" is proven by filesystem inspection, not asserted in the interface: after deletion, no file under `~/.loke` contains any mapping value or imported record, verified by a test that greps the tree for known fixture values. Applies to MK21's workspace as well as the mapping table. |
| X8.5 | S | ⏸ On hold — `pipeline.tk` must not be edited until NC1.9 is resolved | **Remove the two hardcoded home directories** — `packages/browser/pages/api/pipeline.tk` and `settings.tk` both hardcode the original developer's home path, so the settings file silently resolves nowhere for anyone else. Tolerated in `scripts/known-defects.txt:20-21`; both lines come out when this lands. |
| X8.6 | L | | **Router strategies: implement or withdraw** — `docs/claims.md` D3: "cheapest-adequate, fastest, best-quality, local-first" has zero matches across `packages/` and `src/`. One fixed selection path exists in `packages/core/src/router/selector.tk`. F5.3 is marked **Done** and must be reopened. Either implement the four named strategies as selectable and configurable, or remove the names from `docs/features-loke.md:86`. Note decision **R** in the open-decisions register: sensitivity-scored provider routing is claimed by US 12,556,533 and wants a professional read before the router is promoted outwardly. |

Related and deliberately **not** duplicated here: fail-closed on detection unavailability is **NC1.9**;
the ten orphaned multi-layer modules including `consensus` are **AD1.7**; the audit chain is **GA5.2**
and **GA5.3**.

## Epic X7: Test Suite De-stubbing

*Fifty-four test files declare the module they are meant to be testing instead of importing it. The
reason that was tolerated no longer exists.*

> **Why now:** the stub pattern existed because the linker gap made cross-module imports fail. That gap
> closed upstream — `UPSTREAM.md:77` records the verification. The excuse is dead; the stubs are not.
>
> **Unblocked 2026-09-20.** The toolchain is available, so execution queues behind the green build
> rather than upstream: a de-stubbed test has to compile to be worth anything. X7.1 needs nothing and is
> overdue.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X7.1 | S | | **Inventory and triage the 54** — Of 86 test files, 54 carry an explicit stub marker and re-declare the module under test; about 12 import real production code (`docs/test-coverage.md`, corrected under X6.4). Classify each: de-stub, rewrite, or delete as testing nothing worth testing. Publish the list so the count cannot drift. |
| X7.2 | XL | Queued behind the green build (§F10) — a de-stubbed test has to compile to be worth anything | **De-stub the tests that guard a privacy or governance path first** — Priority order by what a passing stub currently misrepresents: the privacy pipeline, the governance gateway, the placeholder store, the router, then everything else. A test that re-declares its subject cannot fail when the subject breaks, which is how A13 came to be marked complete while the browser handler posted raw text. |
| X7.3 | M | Queued behind X7.2 | **Make a stubbed test a gate failure** — Add the stub-marker check to `scripts/quality-gate.sh` with `scripts/known-defects.txt` as the shrinking allowlist, so the count can only go down. |
| X7.4 | S | Queued behind X7.2 | **Restate coverage once** — Re-measure and update `docs/test-coverage.md` and the claims register with both numbers (files carrying a test, modules actually exercised) and what each means. |

## Epic LC1: Local Compute Validation on Target Hardware

*Nine stories are marked Done for behaviour that has never executed on the hardware it was written for.*

> **This epic is blocked on a purchase, not on the toolchain.** `README.md:354-360`, `docs/claims.md` §J
> and `docs/features-loke.md:161` all record the same blocker: there is no Apple Silicon test machine.
> VM1.4's containerised harness is a partial substitute and cannot validate unified memory or MLX.
> See decision **H** in the open-decisions register.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| LC1.1 | S | Blocked — hardware | **Acquire or arrange target hardware** — A base Apple Silicon Mac Mini is sufficient and is the recommendation. A cloud GPU instance cannot substitute: unified memory is the premise of the layer-offload design and a discrete-GPU instance has a PCIe boundary that predicts nothing about a Mini; MLX is Apple-Silicon-only, so a non-Apple host validates it not at all. `benchmarks/README.md:42` requires every local-inference figure to state which host produced it. |
| LC1.2 | L | Blocked — LC1.1 | **Run the five unverifiable F2 claims** — `docs/claims.md` J1-J5. Record each through `benchmarks/lib/result.py` with the host, model version, workload and N, so the results are admissible rather than anecdotal. Any that fails becomes its own defect. |
| LC1.3 | M | Blocked — LC1.1 | **MLX: exercise or withdraw** — The MLX path has zero importers and `generate()` would return `""` if called; F2.9 has no implementing code at all despite being marked Done. Either make it work on the target hardware or remove the MLX claim from the public site and the feature documents. |
| LC1.4 | M | Blocked — LC1.1 | **Validate the CPS 230 continuity control** — `docs/specifications/policy-examples/apra-cps-230.yaml:82,213` carries `validation_status: UNVALIDATED` on the local-provider fallback and states twice that an untested fallback must not be presented to an assessor as a continuity control. This is the control the whole preset rests on. Exercise the degraded path end to end with the network disabled, then change that field and nothing before. |
| LC1.5 | L | Blocked — LC1.1 | **Memory-splitting and layer offload** — Measure what actually fits and at what throughput when a model exceeds available memory, on real unified memory. This is the technique the tiered-inference design assumes; it has never been measured. Report tokens/second and resident memory per tier, and state the physical-security difference between a desk machine and a remote host in any write-up. |

## Epic W2: Website Honesty and Positioning

*Recorded retrospectively. The work landed before the epic was written, which is the defect this entry
closes.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| W2.1 | M | **Done** | **Withdraw the two false absolutes** — The live site asserted "No AI usage bypasses governance — it is architecturally impossible" and "The LLM never sees real data". Both are false: enforcement is bypassable at six points (`docs/specifications/enforcement-bypass-corpus.md`) and the shipping path is redact-and-forward, which sends redacted real text. Replaced using the established withdrawal idiom rather than deletion, so a reader who remembers the claim finds out what happened to it. |
| W2.2 | M | **Done** | **Remove the dead "try loke" link** — loke is not an online tool and must not be implied to be one. The call to action is now a local install, not a hosted demo. |
| W2.3 | S | **Done** | **Reposition on the no-custody architecture, in the future tense it deserves** — The page describes schema-out/execute-locally as the intended primary path and says plainly that it is specified rather than shipped (NC1). It does not claim novelty: this is the text-to-SQL default and ships in several commercial products. The contribution claimed is treating it as a security control with a threat model, artifact validation and an audit obligation. |
| W2.4 | S | | **Screenshots** — Three genuine screens, each captioned with its capture date: the Insight Lab (genuinely local), the dataset catalogue with real and synthetic badged apart, and the privacy review modal showing the placeholder mapping. Not the dashboard until NC1.4 lands. See decision **D**. |

## Epic BG1: Playwright-Found Defects — Migrated from `progress.json`

*The last twelve open items from the retired `progress.json`, re-verified against the committed tree on
2026-09-19 rather than carried across on trust.*

> **Nine of the twelve were already closed** and are recorded here so nobody reinstates them:
>
> | Retired item | Why it is closed |
> |---|---|
> | BUG-1 ooke API POST handlers not executing | `scripts/gen_handlers.sh` detects and registers `f=post(` — `UPSTREAM.md:84` |
> | BUG-2 ooke API GET handlers not executing | Same mechanism for `f=get(` — `UPSTREAM.md:83` |
> | BUG-3 page `get()` bypassed when a template exists | `serve.tk::serveregisterstatic` takes `handledpaths` and the handler claims the path first — `UPSTREAM.md:85,87` |
> | FEAT-1 register API handlers in loke | 18 API routes registered in `packages/browser/src/_handlers.tk` |
> | FEAT-2 register API handlers in moke | 15 API routes registered in `packages/moke/src/_handlers.tk` |
> | FEAT-3 remove moke's direct Ollama call | moke forwards to loke at `packages/moke/pages/api/pipeline.tk:72` and `stream.tk:53`. The only remaining `11434` references are health checks |
> | BUG-6 API key in localStorage | `packages/browser/pages/api/settings.tk:6,56-59` reads the keychain first, with a JSON migration fallback. Zero `localStorage` API-key references remain in the templates |
> | BUG-7 moke dataset load/upload | Implemented — `packages/moke/pages/api/datasets.tk`, `upload.tk`; verified under X4a.4 |
> | BUG-8 moke ML analysis | Implemented — `packages/moke/pages/api/ml.tk` (188 lines); Insight Lab verified under MK2.1 |
>
> The `V3`/`V3B` epics are also retired: the v3 migration completed at 562/562 files, so their
> `not_started` statuses were stale by four months.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| BG1.1 | S | Queued behind the green build | **Confirm the dashboard returns DDL JSON, not plain text** — Retired as BUG-4. MK3.2 and MK4.8.1 are both marked Done and the NC1.5/NC1.6 provenance work changed what the dashboard renders, so this is a re-verification rather than a fix. If it still returns plain text, MK4.8.1 reopens. |
| BG1.2 | S | Queued behind the green build | **Confirm the sysmon widget reports real figures** — Retired as BUG-5, which reported zeros and dashes. `packages/core/src/monitoring/sysmon.tk` exists; whether it is reached from the browser widget is unverified. A widget that displays dashes is a cosmetic defect; one that displays plausible zeros is a misreporting defect, so distinguish which it is. |
| BG1.3 | S | Queued behind the green build | **Confirm the multi-phase DDL flow end to end** — Retired as FEAT-4. Overlaps MK3.2 (Done) and BG1.1; close as a duplicate if BG1.1 passes. |


## Epic LS1: Canonical Form Sweep

*toke publishes a measured pattern catalogue and a linter that enforces it. loke has never been run
through either.*

> **Why this is not bikeshedding.** `docs/guide/11-patterns-and-efficiency.md` in the toke repository
> picks one form for each everyday construct **by measurement** — the form that costs the fewest tokens
> under the decision tokenizer *and* runs as fast in as little memory as any alternative. For a project
> whose premise is reducing what is spent on a model, the canonical form is the product, not a style
> preference.
>
> Measured across 223 loke source files on 2026-09-20: **1,668 violations**.
>
> | Rule | Count | Files | Category |
> |---|---|---|---|
> | `single-use-let` | 974 | 145 | hint |
> | `string-concat-chain` | 407 | 101 | warning |
> | `unused-import` | 232 | 127 | warning |
> | **`discarded-value-result`** | **30** | **11** | **error** |
> | `loop-rebuilds-array` | 8 | 7 | hint |
> | `unused-let` | 7 | 3 | warning |
> | `mut-flag-if` | 6 | 4 | warning |
> | `mutable-never-mutated` | 3 | 2 | warning |
> | `empty-fn-body` | 1 | 1 | warning |
>
> **Token efficiency here means canonical constructs, not minified source.** `toke --fmt` is the
> canonical *source* form and makes files slightly larger; `--min` is the shipped form. Do not minify
> source to chase a byte count — the catalogue's verdicts are what count.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| LS1.1 | S | | **The 30 `discarded-value-result`, first and on their own** — This is a defect story, not hygiene. The rule is **error** category and its rationale is blunt: *"the discarded value is a bug in every case"*. Arrays and maps have value semantics, so a bare `arr.push(v);` or `trace.steps.push(...)` statement **returns a new collection and throws it away**, and the syntax card notes a bare push *can crash at runtime*. 30 sites in 11 files, worst `agents/observability.tk:222`. The program does not do what it says it does; fix before anything cosmetic. |
| LS1.2 | M | | **407 `string-concat-chain` → interpolation** — The token-efficiency win, and the one the catalogue measures most starkly. For a 3-part string: nested `concat` costs 20 proxy tokens, 95 minified bytes, 104 ms and 76,784 KB RSS; interpolation `"\(a)-\(b)-\(c)"` costs 13, 47, 82 ms and 39,136 KB. Roughly half the memory and a third fewer tokens, for the same output. 101 files. Prefer interpolation; `str.join` where the parts are already an array. |
| LS1.3 | S | | **232 `unused-import`** — By hand, or by a script that understands type references. **Never with `toke --lint --fix`** until the upstream bug in F10.11 is fixed: its `unused-import` rule ignores `$type` references and deleted 197 needed imports here. Cross-check each removal against `$typename` usage in the same file before deleting. |
| LS1.4 | M | | **The remaining 999 hints and warnings** — 974 `single-use-let`, 8 `loop-rebuilds-array`, 7 `unused-let`, 6 `mut-flag-if`, 3 `mutable-never-mutated`, 1 `empty-fn-body`. Lowest value per change and the largest diff, so it goes last and in reviewable batches by directory. `mut-flag-if` and `flag-soup` are pattern rules with measured verdicts behind them; the `single-use-let` hints are taste and may be declined with a reason. |
| LS1.5 | S | | **Hold the line in the gate** — Add a lint step to `scripts/quality-gate.sh` that fails on any **error**-category rule (`discarded-value-result`, `unreachable-code`) and on `string-concat-chain`, with `scripts/known-defects.txt` as a shrinking allowlist and a story ID required per line. Hints stay advisory. Without this the sweep is a one-off and the count grows back. |

## Epic RV1: Re-verify the Done Markers That Need a Binary

*The build was red for four months. Roughly 120 stories were marked Done by reading code.*

> **The problem, stated plainly.** A story marked Done for behaviour that has never executed is worse
> than one marked not-started: it is an assertion with no evidence, and this document is the input to
> `claims.md`, which is the input to everything the project says publicly. Two examples already found and
> corrected show the shape — the X4a.6 preamble asserted *"All 172 modules compile, 19/19 tests pass"*
> (it is 58 of 199), and GA2.2 was Done for SQLCipher encryption that the toolchain cannot do at all.
>
> Every row in scope gets exactly one of three outcomes. **Holds** — exercised and true, with the
> command that showed it. **Reopened** — exercised and false. **Untestable** — names what is missing.
> "Done" without one of those three is not an acceptable result for any row here.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| RV1.1 | M | | **The 65 T1–T14 rows** — Every one is marked Done under an epic preamble that demands runtime evidence: *"Tests verify runtime correctness — not just that files compile, but that functions return expected values for known inputs."* Several assert specific outcomes, e.g. T4.5 (*"gateway blocks RESTRICTED request when kill switch engaged"*), T10.1, T14.2 (*"POST to `/api/pipeline` with email in body returns anonymised prompt"*). Run them and record per-assertion results. Depends on the green build and on X7. |
| RV1.2 | M | | **The X4a verification claims** — X4a.3 and X4a.4 (*"Verify loke/moke API handlers compile and execute"*), X4a.5.1–5.8 (each claims a named module now passes semantic checks — cheap to re-check against the current 141 failures), X4a.6.1–6.5 (live Ollama health, model list, `/api/pipeline` proxy) and X4a.7.1–7.4 (runtime CORS behaviour; X4a.7.4 is literally titled *"Verified implementation"*). X4a.4 is also the cited evidence for retiring BUG-7, so a failure reopens that too. |
| RV1.3 | M | | **X4b.3–X4b.18 and T15.1–T15.10** — 13 test suites each claimed to compile independently and return 0, written under that epic's own blocker note that *"a standalone `--no-web-glue` compilation mode is needed in toke before any test binary can be produced"*. Plus the runner, the CI badge and `docs/test-coverage.md`'s assertion counts — F10.2 already established the badge was meaningless. T15.9 claims *"100% of existing tests passing"* and T15.10 *">80% of source modules have at least one test file"*. |
| RV1.4 | M | | **The governance and privacy runtime claims** — GA1.1–GA1.4 and GA1.8 (pipeline, restoration, kill switch, audit logging, policy evaluation wired into the browser handler; GA1.5–GA1.7 and GA1.9 are already reopened), GA2.1 (keychain-only keys *"never written to disk, never appear in logs"*), GA2.4 (*"no PII appears in any log, console output, or error message"*), GA2.5 (binds `127.0.0.1` only), GA3.1–GA3.7 (ARIA, graduated warnings, cost estimate, cancel in-flight, thumbs-down), NC1.4–NC1.6 (schema actually sent, no fabricated values rendered, per-card provenance — BG1.1 and BG1.3 exist to re-verify exactly this). |
| RV1.5 | S | | **The measurement claims** — F3.1 (*"10MB/s target"* regex detector), F3.9 (*"100% coverage"* privacy test harness, which AD1.8 records has never run because `run_tests.sh:25` skips it), F10.1 (the build refuses to link an incomplete build — confirm it fires at 141 failures rather than silently linking), F10.5 (*"type-check went 167 to 246 passing"*, re-measurable and contradicted by 58/199), X6.4 (the corrected coverage statement, honest only once tests run), VM1.5 (numbers out of CI, needs a CI run that gets past compilation). |
| RV1.6 | S | | **F8.1–F8.4** — mDNS pairing, TLS 1.3 mutual auth with certificate pinning, remote model execution and the Exo integration, all four Done under an epic notice that simultaneously said they *"still need a compiler"*. TLS mutual auth with pinning is a security claim; it does not get to stay Done on inspection. |
| RV1.7 | S | | **Reconcile the document with itself** — The SUMMARY table and the story rows disagreed on the test suite (`53 \| 0` against 65 individually Done). Add a rule to the top of this document: the SUMMARY is derived, never hand-maintained, and a Done marker for runtime behaviour must name the command that exercised it. Consider a `scripts/check_backlog.py` that fails when the two disagree — the reconciliation script the retired `progress.json` was supposed to have and never got. |

> **Out of scope, deliberately:** F2.1–F2.9 (the throughput and tier claims) stay with epic **LC1**. They
> are blocked on Apple Silicon hardware, not on the compiler, and moving them here would imply the build
> can settle them.
