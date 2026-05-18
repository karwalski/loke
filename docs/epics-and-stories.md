# loke — Epics & Stories

**License:** Apache 2.0
**Version:** v1.0 (all ooke bindings available — full backlog unblocked)

---

## How This Document Is Structured

Epics are grouped into three layers: **Foundation** (the core engine that all modes share), **Platform** (the extensibility, UI, and infrastructure layer that applications build on), and **Application** (the user-facing modes and interfaces). Cross-cutting concerns span all layers.

Story sizing uses T-shirt sizes: **S** (< 1 day), **M** (1-3 days), **L** (3-5 days), **XL** (1-2 weeks).

Stories sourced from the platform requirements document are tagged with their R-number origin (e.g. `[R2.3]`) for traceability.

Story status values: blank (not started) · **Spec done** · **Done** · **⏸ On hold**

> **⏸ On hold** stories are blocked pending a dependency becoming ready for development. See the hold notice on each affected layer for detail.

---

# FOUNDATION LAYER

> **Foundation layer — now in development**
>
> loke is built on **ooke** ([github.com/karwalski/ooke](https://github.com/karwalski/ooke)) — a lightweight CMS and web application framework written in the toke programming language. ooke Phase 1 and all required native bindings are complete. All stories are now unblocked.
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
| F3b.1 | L | | **Privacy filter layer abstraction and registry** — Define a `$privacyfilter` interface type: `id:str`, `name:str`, `kind:str` (regex/ner/model/external), `detect(text:str):@$piientity`, `entitytypes():@str`, `isavailable():bool`, `confidence():f64`. Create a filter registry (`$filterregistry`) where layers are registered at startup. Migrate existing detectors (regex F3.1, NER F3.2/F3.3, Presidio F3.4) to implement this interface without changing their behaviour. Registry supports `register`, `list`, `get`, `remove`. Each filter declares its supported entity types and a default confidence score. |
| F3b.2 | L | | **Layer ordering and trust configuration** — Add a `$layerconfig` type to `ooke.toml` and the settings UI: `[[privacy.layers]]` entries, each with `id`, `enabled:bool`, `priority:i32` (lower = runs first = higher trust), `mode:str` (detect-only / detect-and-mask / veto), `confidence_threshold:f64` (minimum confidence to accept a detection), `entity_filter:@str` (subset of entity types this layer handles, empty = all). Pipeline orchestrator reads layer config and executes filters in priority order. Layers with `mode:veto` can block the request entirely if PII is found above threshold. Default config: regex (priority 1), NER (priority 2), Presidio (priority 3, if available). Organisation-managed configs override user configs. |
| F3b.3 | XL | | **OpenAI Privacy Filter integration** — Integrate [openai/privacy-filter](https://huggingface.co/openai/privacy-filter) as a privacy filter layer. The model runs locally via ONNX runtime through ooke native bindings or via Ollama as a token-classification task. Supports the 8 entity types: `account_number`, `private_address`, `private_email`, `private_person`, `private_phone`, `private_url`, `private_date`, `secret`. Map OpenAI entity types to loke's normalised entity type taxonomy (F3.6 already has this). Handle BIOES span decoding to extract entity boundaries. Configurable operating point (precision/recall tradeoff via Viterbi transition biases). 128K context window means full-document scanning without chunking for most inputs. Register as `openai-privacy-filter` in the filter registry. |
| F3b.4 | L | | **Consensus and conflict resolution policies** — When multiple layers detect overlapping entities, define resolution strategies: `first-match` (highest-priority layer wins), `unanimous` (all layers must agree for entity to be masked), `majority` (> 50% of layers agree), `most-restrictive` (union of all detections — anything any layer flags gets masked), `confidence-weighted` (weighted average of confidence scores across layers, threshold determines action). Store the chosen strategy in `privacy.consensus_strategy` in config. Default: `most-restrictive` (safety-first). Each resolved entity records which layers detected it and their individual confidence scores for auditability. |
| F3b.5 | M | | **Per-entity-type layer routing** — Allow configuration to route specific entity types to specific layers. Example: `private_person` detection routed to OpenAI Privacy Filter (strong at contextual name disambiguation — "my boss John" vs "John Deere") while `account_number` and `secret` routed to regex (deterministic, no false negatives for known patterns). Config: `[[privacy.entity_routing]]` entries with `entity_type`, `preferred_layers:@str`, `fallback_layers:@str`. When preferred layers are unavailable, fallback layers are used. Unrouted entity types use the default layer ordering. |
| F3b.6 | M | | **Layer health monitoring and graceful degradation** — Each filter layer reports health status via `isavailable()`. The pipeline orchestrator checks health before each request. If a layer is unavailable (model not downloaded, Presidio not running, ONNX runtime error): log a warning with the layer name and reason; skip the layer; record the degradation in the pipeline trace (F3.6 already has stage-level tracing); if the unavailable layer was the only one configured for a specific entity type, emit a governance alert (G1). Never block the pipeline because a single layer is down — degrade gracefully with clear audit trail. Dashboard widget shows layer health status. |
| F3b.7 | M | | **Custom model registration for compatible token-classifiers** — Provide a registration interface for adding arbitrary HuggingFace-compatible token-classification models as privacy filter layers. User specifies: model path (local or HuggingFace ID), label mapping (model labels → loke entity types), confidence threshold, and priority. Validate that the model outputs token-level classifications. Support ONNX, SafeTensors, and Ollama-served models. Include a `loke privacy add-model <model-id>` CLI command and a settings UI panel. Ship with the OpenAI Privacy Filter as the first pre-configured model; others added via this interface. |
| F3b.8 | L | | **Organisation-managed layer policies** — Organisations can define mandatory privacy filter configurations that override user settings. Policy schema: `minimum_layers:i32` (e.g. require at least 2 independent filters), `required_layers:@str` (e.g. must include `openai-privacy-filter`), `locked_consensus:str` (e.g. force `most-restrictive`), `banned_layers:@str` (e.g. disallow external API-based filters), `max_confidence_threshold:f64` (prevent users from setting thresholds so high that detections are suppressed). Policies distributed via `loke.policy.json` managed by the compliance engine (A3). Violations surfaced in governance dashboard (G4). |
| F3b.9 | M | | **Privacy filter comparison and evaluation mode** — Provide a `loke privacy evaluate` command and UI panel that runs a text sample through all configured layers side-by-side and shows: which entities each layer detected, confidence scores, overlaps, disagreements, false positive/negative estimates (when ground-truth labels are provided). Supports importing labelled evaluation datasets (JSON format: `[{text, entities: [{start, end, type}]}]`). Outputs a comparison matrix with per-layer precision/recall/F1 against the labelled data. Helps users choose which layers to trust and in what order. |
| F3b.10 | M | | **Privacy filter layer metrics and audit integration** — Record per-layer detection metrics in the audit trail (F6): layer ID, entities detected, confidence scores, processing time, consensus outcome. Aggregate metrics in the governance dashboard (G4): detection counts by layer over time, agreement rate between layers, per-entity-type detection distribution, layer latency percentiles. Expose metrics via the MCP server so external tools can query filter performance. |
| F3b.11 | S | | **Documentation and migration guide** — Document the multi-layer privacy filter architecture, configuration schema, and how to add custom models. Include a migration guide for existing deployments that explains: existing regex/NER/Presidio layers continue to work unchanged; the OpenAI Privacy Filter is optional and additive; how to enable it; recommended configurations for different compliance regimes (GDPR, HIPAA, Australian Privacy Act). Add to `docs/privacy-filters.md`. |

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
| F5.3 | XL | **Done** | Model selection engine (cheapest-adequate, fastest, best-quality, local-first bias, fallback chains — implemented in toke) |
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

> Now unblocked — std.mdns and std.tls bindings are available.

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
| A3.1 | L | **Spec done** | Policy definition format and loader (YAML/TOML, enterprise URL fetch, merge rules, hot-reload) |
| A3.2 | M | **Spec done** | Regional regulatory defaults (EU GDPR, AU Privacy Act, HIPAA, CCPA, UK GDPR, Singapore PDPA) |
| A3.3 | M | **Spec done** | Compliance feedback loop (response scanning, warning UI, require-confirmation mode) |
| A3.4 | L | **Spec done** | Audit reporting and export (PDF/CSV/JSON, time ranges, templates, scheduled reports) |

## Epic A4: User Onboarding & Experience

*Guide new users, provide visibility, and reinforce value.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| A4.1 | L | **Spec done** | First-run setup wizard (hardware check, Ollama install, provider config, privacy presets, test interaction) |
| A4.2 | M | **Spec done** | Pipeline visibility panel (real-time stage display, expandable details, CLI --verbose equivalent) |
| A4.3 | M | **Spec done** | Savings dashboard (tokens saved, cost saved, PII intercepted, local ratio, trends) |
| A4.4 | M | **Spec done** | Prompt approval workflow for beta (pre-send display, approve/edit/cancel, "don't ask again") |

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
| A5.1 | M | **Spec done** | Issue reporting form (accessible from any view, captures type/description/repro steps/expected behaviour/optional screenshots, configurable destination — API endpoint, email, or external tracker) `[R14.1]` |
| A5.2 | M | **Spec done** | AI-assisted report drafting (optional: use LLM via privacy pipeline to help user refine problem statement and benefit description; form works without AI) `[R14.2]` |
| A5.3 | M | **Spec done** | Version check and update notification (check configurable endpoint daily or on demand, display update availability in UI, manual update trigger in settings — no auto-update) `[R11.1, R11.2]` |

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
| X4a.1 | XL | | **toke: multi-file module resolution** — Add a `--module-path <dir>` flag (repeatable) to toke that tells the compiler where to search for imported modules. When compiling `source.tk` that contains `i=alias:module.path;`, the compiler searches each `--module-path` directory for a file whose `m=` declaration matches `module.path`. Resolves the module's type interface (generates `.tki` if needed) so the importing file can type-check. At link time, compiles all transitively imported modules and links them together. This is the critical missing piece — without it, no multi-file toke program can compile. |
| X4a.2 | L | | **ooke: pass module paths when compiling handlers** — When ooke compiles an API handler `.tk` file, pass the project's source directories as `--module-path` arguments to toke. For loke, this means: `--module-path packages/core/src --module-path packages/shared/src --module-path packages/browser/src --module-path src`. Read module paths from `ooke.toml` config (new `[build] module_paths = [...]` field). Handlers should compile with full access to the project's module graph. |
| X4a.3 | L | | **Verify loke API handlers compile and execute** — Once X4a.1 and X4a.2 are complete, verify that all loke API handlers compile with module resolution and return correct responses: `/api/health` (returns loke version, Ollama status, port), `/api/pipeline` (runs privacy pipeline on input text, returns anonymised output), `/api/models` (returns available model list from Ollama), `/api/settings` (returns current config). Test from moke's chat interface — a prompt should flow through the full pipeline and return an LLM response. |
| X4a.4 | M | | **Verify moke API handlers compile and execute** — Verify moke's API handlers: `/api/health` (proxies to loke health), `/api/feedback` (stores feedback), `/api/memory` (searches memory palace), `/api/datasets` (lists uploaded datasets), `/api/upload` (processes CSV upload), `/api/pipeline` (proxies pipeline call through loke). |

## Epic X4a.5: Core Module Semantic Fixes

*With toke v3 syntax migration complete (562/562 files) and module-aware compilation working (X4a.1–X4a.2), 94 of 168 core modules still fail semantic checks. These are code-level issues — undeclared identifiers, missing imports, type mismatches, and mutability errors — that prevent `.tki` interface generation and block the full module dependency graph from resolving.*

**Root cause:** The v3 migration fixed syntax but not semantics. Many modules reference sum type variants, stdlib functions, or types without proper imports or declarations. Some use `i64` where `i32`/`u32` is expected. Some assign to immutable bindings.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.5.1 | S | | **Add missing `std.json` imports** — 9 modules call `json.str()`, `json.i64()`, etc. without `i=json:std.json;`. Add the import to: `core.feedback.store`, `core.governance.aigov`, `core.governance.consent`, `core.governance.dsar`, `core.governance.monitoring`, `core.governance.quota`, `core.governance.report`, `core.governance.rulesengine`, `core.storage.syncqueue`. |
| X4a.5.2 | S | | **Fix `let` → `let mut` bindings** — 12 modules assign to immutable bindings. Add `mut.` prefix: `core.companion.discovery` (n), `core.eval.advisor` (runline), `core.governance.compliance` (result), `core.governance.scorecard` (rows), `core.governance.value` (result), `core.installer.uninstall` (models), `core.installer.updater` (found), `core.mcp.protocol` (items), `core.policy.loader` (sets), `core.privacy.placeholderstore` (result), `core.privacy.presidio` (entities), `core.storage.dashboard` (found). |
| X4a.5.3 | M | | **Fix type mismatches (`i32`/`u32` vs `i64`)** — 11 modules pass `i64` where `i32` or `u32` is expected (or vice versa). Add explicit casts (`as i32`, `as u32`) in: `core.agents.observability`, `core.governance.forecast`, `core.governance.killswitch`, `core.memory.export`, `core.memory.privacy`, `core.optimiser.llmlingua`, `core.router.intent`, `core.router.latencyrouter`, `core.router.sensitivity`, `core.storage.ephemeral`. Fix `void` return mismatches in `core.governance.policy`, `core.memory.aaak`. |
| X4a.5.4 | M | | **Add missing imports and type declarations** — Fix undeclared identifiers by adding imports or local type definitions. Missing imports: `core.mcp.discovery` (std.time), `core.memory.decay` (std.math), `core.auth.oauth` (std.crypto), `core.auth.refresh` (std.http), `core.feedback.reporter` (shared.types), `core.pipeline.history` (shared.types). Missing type declarations: `core.models.hardware` ($hwvendor), `core.models.infer` ($inferbackend), `core.models.mlx` ($mlxloaded), `core.models.queue` ($queuedrequest), `core.optimiser.budget` ($budgetperiod), `core.optimiser.toon` ($toontoken), `core.privacy.template` ($templateerr), `core.memory.schema` ($dbconn import from core.storage.db). |
| X4a.5.5 | M | | **Fix wrong import paths (remaining)** — Modules with incorrect import paths: `core.companion.executor` (companion.channel → core.companion.channel), `core.eval.bench` (providers.dispatcher → core.providers.dispatcher), `core.memory.mining` (memory.aaak → core.memory.aaak). |
| X4a.5.6 | S | | **Fix duplicate identifier declarations** — 3 modules declare the same identifier twice: `core.agents.sandbox` (readfile), `core.governance.usecases` (usecase), `shared.result` ($ok conflicts with built-in). Rename duplicates or remove redundant declarations. |
| X4a.5.7 | S | | **Fix `mut` parse errors** — 2 modules have `mut` in expression position where it's not valid: `core.extensions.providerregistry`, `core.installer.pull`. Likely double-mutation from prior automated fix — clean up. |
| X4a.5.8 | S | | **Suppress warnings / minor fixes** — Handle: `core.agents.overnight` (Python keyword `class`), `core.memory.search` / `core.router.examples` / `loke.browser.workspace.tabs` (value escapes scope — move binding). These are warnings, not errors, but should be cleaned up. |

## Epic X4a.6: Live API Handler Implementations

*loke builds and serves a native binary (X4a.1–X4a.5 complete). All 172 modules compile, 19/19 tests pass. But the API handlers return stub/placeholder data because the core module functions (`browser.extensions.core`, `core.models.ollama`) have placeholder implementations. This epic implements the real business logic so API endpoints return live data.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.6.1 | M | | **Implement `browser.extensions.core` state management** — Replace stub getters (`getconfig`, `getrouter`, `getdispatcher`, etc.) with real state. On init: load `ooke.toml` config, create Ollama client, initialise privacy pipeline config with default entity types and detection layers. Store state in a module-level struct initialised once at startup. `getconfig()` returns a struct with `.ollamaurl` (default `http://127.0.0.1:11434`), `.port` (11430), `.datadir`, `.loglevel`. |
| X4a.6.2 | M | | **Implement `/api/health` — live Ollama check** — The health handler calls `ollama.healthcheck(client)` which should HTTP GET `http://127.0.0.1:11434/api/tags`. Return `{"ok":true,"loke":"0.2.0","ollama":"running"/"stopped","port":11430}`. Use `std.http` GET with timeout. |
| X4a.6.3 | M | | **Implement `/api/models` — list from Ollama** — GET `http://127.0.0.1:11434/api/tags`, parse JSON response, return model list with name/size. Use `std.http` and `std.json`. |
| X4a.6.4 | L | | **Implement `/api/pipeline` — proxy to Ollama** — Accept `{text, system_prompt, model}`, POST to `http://127.0.0.1:11434/api/generate` with model and prompt, return response. Privacy pipeline runs first (placeholder pass-through for now). |
| X4a.6.5 | S | | **Wire moke → loke pipeline** — moke's chat sends to loke's `/api/pipeline`, loke proxies to Ollama, response flows back. Verify end-to-end from moke UI. |

## Epic X4a.7: CORS Architecture Resolution

*Cross-origin issues between moke (:11432) and loke (:11430) have been a recurring problem. The `ooke.toml` `corsorigins = "*"` setting works for preflight (OPTIONS) and actual requests when the Origin header is present, but the browser-side JS health polling still shows connectivity issues. This epic proposes an architectural change to eliminate CORS as a concern.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4a.7.1 | S | | **Audit current CORS state** — Document exactly where CORS is configured (ooke.toml, ooke http.c headers), what the browser sees (inspect Network tab), and whether the issue is CORS headers missing on specific routes or a different connectivity problem (e.g. moke's JS fetching wrong URL, health endpoint returning non-JSON). |
| X4a.7.2 | M | | **Architectural option: reverse proxy** — Instead of moke fetching cross-origin to loke directly, moke proxies `/api/loke/*` through its own server to `127.0.0.1:11430`. All browser requests stay same-origin. Eliminates CORS entirely. Implement in ooke as a `[proxy]` config section: `proxy = [{path="/api/loke", target="http://127.0.0.1:11430"}]`. |
| X4a.7.3 | S | | **Architectural option: single-origin deployment** — Run loke and moke on the same port with path-based routing (`/moke/*` → moke handlers, everything else → loke). Eliminates the multi-port setup entirely. Evaluate feasibility with ooke's routing. |
| X4a.7.4 | S | | **Decision and implementation** — Pick one approach (proxy or single-origin), implement it, verify moke→loke calls work without CORS, remove `corsorigins` config as it's no longer needed. |

## Epic X4b: Archive Legacy Tests & Create New Test Suites

*The v3 migration converted all 562 source files to valid toke v3 syntax. The 170 existing test files (156 loke + 14 moke) were written against the pre-ooke architecture using patterns that no longer compile (v2 test framework references, unresolvable module imports, pre-migration assertion patterns). These tests need to be archived and replaced with clean test suites for loke and moke separately.*

**Blocker:** The toke compiler currently links `tk_web_glue.o` on every build, which requires ooke's db/collections C libraries. A standalone `--no-web-glue` compilation mode is needed in toke before any test binary can be produced. This is being addressed in the toke project. Once resolved, test files can compile to standalone binaries via `tkc --out <binary> <test.tk>`.

**Context:** `std.test` exists in toke's stdlib (`tk_test.c` / `tk_test.h`) and provides `test.assert(cond;msg)`, `test.assert_eq(a;b;msg)`, `test.assert_ne(a;b;msg)`. Test files should follow the convention `f=main():i64` returning 0 for all-pass, non-zero for failure count. The existing `.tkc.md` companion files (156 of them) document the intended test behaviour and can be used as specifications for rewriting.

### Part 1: Archive

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.1 | S | | **Archive legacy loke test files** — Move the 156 existing test files from `tests/unit/`, `tests/integration/`, and `tests/e2e/` into `_archived-tests/loke/`. Preserve directory structure. These files are syntactically valid v3 but cannot compile due to unresolvable module imports and broken test framework references. Keep the `.tkc.md` companion files alongside their test files — they document intended test behaviour and serve as specs for rewriting. Add a `_archived-tests/README.md` explaining the archive reason (v3 migration, test framework gap) and that companion files contain the canonical test specifications. |
| X4b.2 | S | | **Archive legacy moke test files** — Move the 14 existing test files from `packages/moke/tests/` into `_archived-tests/moke/`. Same approach: preserve structure, keep companion files, document the archive. The 3 test files we rewrote during migration (`feedback_test.tk`, `memory_test.tk`, `pipeline_panel_test.tk`) are placeholder stubs — archive them with the rest. |

### Part 2: loke Test Suite

*A clean test suite for the loke core engine. Each test file is a standalone `.tk` program that imports only `std.test` and the module under test. Tests are grouped by subsystem. Every test file compiles independently and returns 0 on success.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.3 | L | | **Privacy pipeline tests** — Write new test files for the privacy subsystem: `test_regex_detector.tk` (email, phone, SSN, credit card, IP, AU TFN/ABN patterns — assert detection and non-detection), `test_ner_detector.tk` (name/place/org detection via local SLM — assert entity extraction from sample texts), `test_placeholder_store.tk` (store placeholder, retrieve, reverse — assert round-trip fidelity), `test_pipeline_orchestrator.tk` (full pipeline: raw text → detect → anonymise → assert no PII in output, assert restoration produces original), `test_guardian.tk` (assert guardian prompt injected into every LLM call). Use `.tkc.md` companion files from archived tests as specifications. Target: 5 test files, each with 10+ assertions. |
| X4b.4 | L | | **Memory palace tests** — `test_palace_drawers.tk` (store/retrieve/search drawers in wings/halls/rooms), `test_decay.tk` (time-based decay scoring), `test_graph.tk` (entity/relation upsert, traversal), `test_search.tk` (keyword search, relevance scoring), `test_aaak.tk` (shorthand compression levels), `test_export.tk` (JSON/CSV/markdown export, import round-trip). Target: 6 test files. |
| X4b.5 | L | | **Governance tests** — `test_gateway.tk` (submit request, assert policy decision), `test_rules_engine.tk` (evaluate conditions, AND/OR/NOT), `test_policy_loader.tk` (load from file/URL, merge), `test_incidents.tk` (create/resolve/list), `test_ownership.tk` (assign/get/missing roles), `test_consent.tk` (record/check consent), `test_dsar.tk` (access/erasure requests), `test_kill_switch.tk` (enable/disable/check blocked), `test_scorecard.tk` (compute governance score). Target: 9 test files. |
| X4b.6 | M | | **Storage tests** — `test_db.tk` (open/migrate/query), `test_settings.tk` (get/set string/int/bool/float), `test_audit.tk` (append/query/export), `test_keychain.tk` (store/retrieve/delete credentials), `test_ephemeral.tk` (store/get/wipe/expire). Target: 5 test files. |
| X4b.7 | M | | **Model & router tests** — `test_model_registry.tk` (register/find/filter models), `test_model_tiers.tk` (tier config, selection, labels), `test_router.tk` (route request, model selection, cost estimation), `test_sensitivity.tk` (sensitivity levels, risk classification), `test_queue.tk` (enqueue/dequeue/priority). Target: 5 test files. |
| X4b.8 | M | | **Provider tests** — `test_anthropic.tk` (request building, response parsing), `test_openai.tk` (request building, response parsing), `test_ollama.tk` (health check, chat completion parsing), `test_dispatcher.tk` (provider routing by type). Target: 4 test files. |
| X4b.9 | M | | **Agent & MCP tests** — `test_agent_types.tk` (type construction, defaults), `test_scheduler.tk` (check due, trigger types), `test_sandbox.tk` (permission checks, file/http access), `test_mcp_protocol.tk` (request/response encoding), `test_mcp_permissions.tk` (tool allow/deny, TOML parsing). Target: 5 test files. |
| X4b.10 | M | | **CLI & companion tests** — `test_commands.tk` (parse command-line args into command struct), `test_session.tk` (create/activate/find sessions), `test_init.tk` (environment checks), `test_companion_discovery.tk` (discover/confirm/reject devices), `test_exo.tk` (health check, model list). Target: 5 test files. |
| X4b.11 | M | | **Optimiser tests** — `test_toon.tk` (JSON→TOON encoding/decoding round-trip, savings measurement), `test_budget.tk` (limit checking, period matching), `test_profiler.tk` (column type inference, PII candidate detection). Target: 3 test files. |
| X4b.12 | S | | **Integration tests** — `test_pipeline_api.tk` (HTTP POST with JSON body → assert anonymised response, assert audit trail written), `test_health_api.tk` (health endpoint returns status/version), `test_mcp_roundtrip.tk` (tool discovery → invocation → response). These require a running loke instance; document setup in test file comments. Target: 3 test files. |

### Part 3: moke Test Suite

*A clean test suite for moke. Each test covers a moke-specific feature using moke's own types and modules.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.13 | M | | **moke core tests** — `test_cost_comparison.tk` (estimate cloud cost, compute savings, accumulate session), `test_tier_visualiser.tk` (tier stats construction, JSON serialisation), `test_console_log.tk` (append log entry, session log structure), `test_profiler.tk` (column type inference, PII candidate, format profile output), `test_ddl.tk` (dashboard card construction, JSON serialisation, validation). Target: 5 test files. |
| X4b.14 | M | | **moke feature tests** — `test_streaming.tk` (session event tracking, JSON output), `test_governance.tk` (regulatory preset lookup, risk classification), `test_companion_simulator.tk` (cluster status, model list), `test_routing_explainer.tk` (decision trace formatting), `test_agents_status.tk` (agent status construction, panel state). Target: 5 test files. |
| X4b.15 | S | | **moke pipeline panel tests** — `test_pipeline_stages.tk` (all 9 stages defined, labels, status symbols), `test_emitter.tk` (start/complete/skip/error stage events, finalise run with totals), `test_history.tk` (add run, recent, evict, last). Rewrite from archived `pipeline_panel_test.tk` companion spec. Target: 3 test files. |

### Part 4: Infrastructure

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4b.16 | M | | **Test runner script** — Write a `scripts/run_tests.sh` that discovers all `*_test.tk` files under `tests/` and `packages/moke/tests/`, compiles each with `tkc --out <tmp> <file>`, runs the binary, captures exit code, and reports pass/fail summary. Handles the `--no-web-glue` flag (or equivalent) once available in toke. Supports `./scripts/run_tests.sh tests/unit/privacy/` for subset runs. Exit code = total failures. |
| X4b.17 | M | | **CI integration** — Add test runner to GitHub Actions CI pipeline. Run on every push and PR. Fail the build on any test failure. Report results as structured JSON artefact. Add test status badge to README. |
| X4b.18 | S | | **Test coverage map** — Document which source modules are covered by which test files. Output as `docs/test-coverage.md` with a table: source module path, test file(s), assertion count, last verified date. Identify untested modules. Target: >80% of source modules have at least one test file. |

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
| MK4.6.1 | M | | **Analysis view: data table instead of raw CSV** — Replace the raw CSV/text display with a proper HTML table. Show schema panel (collapsible) with column names, types, sensitivity tags. Show active dataset info (name, row count, columns). Make pipeline trace collapsible. Make sidebar menu collapsible on mobile. |
| MK4.6.2 | M | | **Preserve chat history across view switches** — When navigating Analysis → Dashboard → Analysis, restore the chat history. Store messages in sessionStorage. On view load, re-render stored messages including any rendered charts. |
| MK4.6.3 | L | | **Project workspace with asset directory** — Add a workspace/project concept: user can upload/select multiple datasets into a project. All artefacts (chats, dashboards, insight results, reports, generated datasets) are stored in a project asset directory. Sidebar shows project assets tree. Assets persist in sessionStorage/localStorage. |
| MK4.6.4 | L | | **Rich demo datasets with guided prompts** — For each built-in dataset, provide 3-5 suggested prompts per screen (Analysis, Dashboard, Insight). Dataset selector shows preview of what each demo produces. Prompts are dataset-specific (e.g., Medicare: "Show top 10 specialties by cost", Water Quality: "Alert on pH below 6.5"). No canned results — all go through loke pipeline. |
| MK4.6.5 | M | | **Richer dataset schemas** — Expand demo datasets with more columns, derived fields, and relationships. Add data types (numeric, categorical, date, boolean, pii). Add column descriptions. Schema display groups columns by type with icons. |
| MK4.6.6 | M | | **Insight Lab improvements** — Replace generic "Cluster 1/2/3" with meaningful cluster labels derived from the data (e.g., "High-value loyal customers", "Budget occasional shoppers"). Show cluster characteristics, outlier details, and statistical summaries. Use the LLM to generate human-readable insight narratives. |
| MK4.6.7 | S | | **Collapsible UI panels** — Schema, pipeline trace, sidebar nav, debug panel all collapsible with smooth animation. Remember collapse state in sessionStorage. Default: schema collapsed, pipeline collapsed, sidebar expanded. |
| MK4.6.8 | S | | **Dataset directory and multi-select** — Allow selecting multiple datasets in a project. Show a dataset directory panel listing all loaded datasets with status (loaded/not loaded). Click to switch active dataset. Upload adds to directory. |

## Epic MK4.7: Privacy Pipeline Visibility & Governance Demo

*loke's core value proposition — privacy, governance, and transparency — is invisible in the current moke demo. Users see text responses but not what loke did to protect them. This epic makes the pipeline tangible: PII detection counts, anonymisation evidence, sensitivity classification, routing decisions, cost awareness, and human-in-the-loop confirmation.*

**Why this matters:** Without visible privacy features, moke is just another chat-with-data UI. With them, it demonstrates what makes loke unique — the user sees their data being protected in real time.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.7.1 | L | | **Privacy detection display in pipeline trace** — When loke returns a response, show PII detection results in the pipeline trace: entity count by type (names, emails, phones, etc.), which privacy layers detected them (regex, NER, SLM), confidence scores. Requires loke's `/api/pipeline` response to include `entities_found`, `entity_types`, `sensitivity`, `detection_layers` fields. Update pipeline handler to populate these from the privacy filter run. Display in the collapsible pipeline trace panel with colour-coded entity badges. |
| MK4.7.2 | M | | **Sensitivity classification badge and routing explanation** — Prominent sensitivity badge (PUBLIC green / INTERNAL amber / CONFIDENTIAL orange / RESTRICTED red) on every response. Below the badge, one-line routing explanation: "CONFIDENTIAL → routed to local Ollama (data stays on device)" or "PUBLIC → routed to Claude Sonnet 4 (fastest, $0.003)". Show "Could run locally?" advisor when cloud model was used. |
| MK4.7.3 | L | | **Human-in-the-loop confirmation modal** — Before each LLM call, show the confirmation modal (confirm.tkt already exists). Display: schema profile being sent (not raw data), PII summary from pipeline, entity count, sensitivity classification, target model/provider, estimated cost. Buttons: Approve / Edit prompt / Use local model / Cancel. Configurable: can be disabled in settings for trusted workflows. |
| MK4.7.4 | M | | **Real pipeline stages in console** — Replace simulated `setTimeout` stages with actual pipeline timing from loke's response. Show real stages: Schema Extract → Privacy Filter (N entities, Xms) → Token Optimise (Y% saved) → Route (model, reason) → LLM Call (provider, Xms) → Restore (placeholders replaced). Each stage shows duration and outcome. Failed stages show red with error detail. |
| MK4.7.5 | M | | **Cost and token tracking** — Show token counts (in/out) and cost per request in the pipeline trace. Running session totals in the sidebar: "Session: 12 requests · 4,230 tokens · $0.0127". Compare local vs cloud cost: "This request: $0.003 (Claude) — would be free locally". Monthly savings estimate visible in governance dashboard. |
| MK4.7.6 | S | | **Anonymisation evidence view** — In the detail/debug panel, show before/after: "Original: john.smith@example.com → Sent: [EMAIL_1]". Show each entity with its placeholder. For demo: use the dataset's PII columns (patient_name, medicare_number etc.) to demonstrate real anonymisation. Never show the mapping in the audit trail — only in the user's local session. |
| MK4.7.7 | S | | **Feedback capture** — Thumbs up/down on every response stores to localStorage: `{timestamp, requestId, vote, comment, model, provider}`. Thumbs-down opens lightweight comment box. Show feedback count in settings. Export as JSON for development review. |

## Epic MK4.8: Dashboard & Insight Lab End-to-End

*The Dashboard tab and Insight Lab need to work as complete demo flows — from dataset selection through LLM-guided design to rendered interactive output.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.8.1 | M | | **Dashboard tab Phase 1-2-3 pipeline working** — Dashboard tab's generate flow: Phase 1 (LLM designs dashboard via loke pipeline — handle `anthropic_raw` response format), Phase 2 (local compute resolves queries against loaded dataset rows), Phase 3 (render Chart.js charts). Fix the `extractJSON` → `resolveQueries` → render pipeline end-to-end. Test with each built-in dataset. |
| MK4.8.2 | M | | **Dashboard demo prompts per dataset** — On the Dashboard tab, show dataset-specific dashboard suggestions. Medicare: "Claims by specialty and month", "Cost distribution by state". Water Quality: "pH trends by location", "Alert frequency heatmap". Clicking a suggestion auto-fills and generates. |
| MK4.8.3 | L | | **Insight Lab meaningful results** — Replace generic "Cluster 1/2" labels with LLM-generated descriptions. Flow: (1) Auto-profile dataset columns, (2) Send schema to LLM asking "propose 3 analyses", (3) Run local ML (k-means, z-score, correlation), (4) Send results back to LLM for narrative interpretation, (5) Display with human-readable labels and visualisations. Each cluster shows: label, size, key characteristics, representative rows. |
| MK4.8.4 | S | | **Insight Lab demo configs per dataset** — Pre-configured analysis settings per dataset: Customer Intelligence → k=4 clustering on spend/frequency, Medicare → anomaly detection on benefit_paid, Water Quality → correlation matrix on chemical readings. One-click to run with sensible defaults. |
| MK4.8.5 | M | | **Dashboard export** — Export rendered dashboard as PNG (html2canvas already loaded), JSON DDL (the chart definition), or shareable link (encode DDL in URL hash). Export button on dashboard header. |
| MK4.8.6 | S | | **Dashboard templates** — Save/load dashboard configurations. Store DDL in localStorage with name. Template selector dropdown on dashboard page. Share templates between datasets. |

## Epic MK4.9: Data Experience & Multi-Dataset Workspace

*Transform moke from a single-dataset tool into a project workspace where multiple datasets, analyses, dashboards and conversations are managed as a collection of assets.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| MK4.9.1 | M | | **Data profiler on load** — When a dataset is loaded, automatically profile all columns: detect type (numeric/categorical/date/boolean/text), compute stats (min/max/mean/median/stddev for numeric; cardinality/top-5 for categorical; date range for dates), identify PII columns by name pattern (name, email, phone, ssn, dob, address). Display as a rich schema card with sparklines for numeric distributions. |
| MK4.9.2 | L | | **Project workspace** — Sidebar shows a project asset tree: Datasets (loaded CSVs), Conversations (saved chats), Dashboards (saved DDLs), Insights (saved analysis results), Reports (exported summaries). Click any asset to open it. Assets persist in localStorage. New project / open project / rename. Default project created on first visit. |
| MK4.9.3 | M | | **Multi-dataset directory** — Load multiple datasets into the same project. Dataset directory panel in sidebar shows all loaded datasets with row count, column count, sensitivity badge. Click to switch active dataset. Cross-dataset references in chat: "Compare Medicare claims with Water Quality readings". Upload adds to the directory. |
| MK4.9.4 | S | | **Richer dataset schemas** — Add column descriptions to built-in datasets (e.g., `benefit_paid: "Amount reimbursed by Medicare for this service"`). Show descriptions in schema preview tooltip. Add relationships between datasets in multi-dataset projects (e.g., server_inventory.rack_id links to network_topology.rack_id). |
| MK4.9.5 | M | | **Governance dashboard page** — Wire the governance.tkt page with real data from loke. Show: total requests today, PII entities detected, local vs cloud ratio, cost this session, top triggered privacy rules, model usage breakdown. Pull from `/api/savings` and session-local counters. Refresh on interval. |
| MK4.9.6 | S | | **Settings page improvements** — Show masked API key status (configured/not set with last-4 chars). Test connection button for each provider. Show current routing preference. Session memory toggle. Export/import settings. |

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
| T1.3 | S | | `tests/unit/privacy/test_placeholder_store.tk` — add entry and retrieve by placeholder; retrieve unknown placeholder returns none; duplicate placeholder overwrites; `restore_all` replaces every placeholder in a string; store with zero entries returns text unchanged |
| T1.4 | S | Done | `tests/unit/privacy/test_patterns.tk` — all `pat_*` constants are non-empty strings; `pat_email` contains `@`; `pat_credit_card` contains a digit character class; `pat_au_tfn` and `pat_au_abn` are distinct; none of the patterns is identical to another |
| T1.5 | M | Done | `tests/unit/privacy/test_pipeline.tk` — full pipeline run: input with email → anonymised output does not contain original email → restore returns original; pipeline with no PII leaves text unchanged; pipeline preserves non-PII context around replaced value; chained pipeline (two PII types) restores both; sensitivity escalates correctly from PUBLIC → CONFIDENTIAL on email detection |
| T1.6 | S | Done | `tests/unit/privacy/test_guardian.tk` — `build_system_prompt("")` returns non-empty string; `is_guardian_present` returns true on the built system prompt; `is_guardian_present` returns false on empty string; guardian text contains "GUARDIAN" keyword; custom system prompt is included in built prompt |
| T1.7 | S | | `tests/unit/privacy/test_content.tk` — content type detected correctly for CSV, JSON, markdown, plaintext; content with `<html>` tag detected as HTML; empty string returns a valid (not-crash) result; very long string (1000+ chars) handled without truncation |
| T1.8 | S | | `tests/unit/privacy/test_template.tk` — template with no substitutions returns base string; template with one `{{field}}` substituted; template with multiple fields substituted in order; missing field key leaves placeholder intact; `to_json` on a built template produces valid JSON shape |

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
| Test Suite (T1–T14) | 14 | 53 | 0 |
| **Total** | **55** | **268** | **193** |
