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
| F1.2 | L | **Spec done** | Application shell — browser mode (ooke native binary with web view; window management; IPC equivalent; multi-platform Mac + Windows builds — replaces Electron) |
| F1.3 | M | **Done** | Application shell — CLI mode (`loke` command in toke; config loading; structured logging with correlation IDs; auto-redaction of sensitive fields) `[R1.3]` |
| F1.4 | M | **Done** | CI/CD pipeline (GitHub Actions: toke lint, toke test, ooke build, release, licence compliance, dependency vulnerability scanning) `[R12.6]` |
| F1.5 | L | **Spec done** | Configuration and secrets management (hierarchical config via `ooke.toml` + environment overrides, schema validation, OS keychain for API keys, fail-fast on invalid) `[R1.1, R1.2]` |
| F1.6 | M | **Done** | Ordered startup and graceful shutdown (boot sequence: config → logger → database → migrations → settings → routes → server → health check → summary; signal handling, request draining, connection cleanup) `[R1.5, R1.6]` |
| F1.7 | M | **Spec done** | Health check system (subsystem probes for database, integrations, AI services; aggregate status endpoint; readiness probe; applications register custom health checks) `[R1.4]` |

## Epic F2: Local Model Integration

*Enable loke to run small language models locally for privacy filtering, intent classification, summarisation, simple completions, and tiered inference — matching model size to task urgency.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F2.1 | L | **Done** | Ollama service manager (auto-detect, start/stop via REST API, health check, model management — Ollama is language-agnostic, no change to functional requirement) |
| F2.2 | M | **Done** | Model capability registry (capabilities, benchmarks, task-to-model mapping — implemented in toke) |
| F2.3 | L | **Spec done** | MLX backend for Apple Silicon (native toke/ooke bindings or REST bridge to MLX — 8-9% faster than llama.cpp on Apple hardware) |
| F2.4 | M | **Spec done** | Native in-process inference via ooke bindings (replaces @electron/llm — same functional requirement: low-latency local inference without spawning a separate process) |
| F2.5 | M | **Spec done** | Local NER and embeddings (replaces Transformers.js — NER and embedding inference via local SLM through ooke native bindings or Ollama REST) |
| F2.6 | XL | **Done** | Tiered inference engine (three tiers: Interactive — fully in GPU/unified memory, 25–55 tok/s, models up to 10B; Considered — partial GPU offload via Ollama `num_gpu`/llama.cpp `--n-gpu-layers`, 5–15 tok/s, up to 70B quantised; Background — maximum offload with heavy RAM/disk streaming, 0.5–5 tok/s, 70B+ full precision; tier selected by F5 router based on request source, user flag, task classification, and AG1 latency tolerance; progress indicator for Considered and Background; tier benchmarked on first run per model) |
| F2.7 | L | **Done** | Background inference queue (sequential job queue for Background-tier requests; priority: user-initiated > agent-scheduled > evaluation; Interactive always preempts — Background job pauses and resumes; `loke queue list/cancel/prioritise/pause/resume`; persists across restarts; completion notifications; queue metrics fed into G4 dashboards) |
| F2.8 | L | **Spec done** | Hardware-aware model recommendations (profile RAM, GPU VRAM, unified memory, disk type/speed, CPU on first run; per-model viability assessment at each inference tier; recommendations shown in model selector with tier badges; refreshed on hardware change, new model added, or companion device paired; `loke models recommend` CLI; disk space warnings) |
| F2.9 | L | **Spec done** | Disk-streaming inference for extreme offload (Background tier only; load model layers from NVMe sequentially with overlapped I/O prefetch; decompose large model into per-layer shards in `~/.loke/models/shards/`; configurable RAM ceiling; requires NVMe — warns on SATA/HDD; graceful degradation if < 0.1 tok/s; actual tok/s displayed with cloud cost comparison; equivalent of AirLLM layer-by-layer execution via llama.cpp mmap/partial-offload) |

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

## Epic F4: Token Optimisation Pipeline

*Reduce token consumption through format conversion, compression, caching, and serialisation — targeting 60-80% reduction. All implemented in toke on ooke.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F4.1 | L | **Done** | TOON serialiser/deserialiser in toke (30-60% savings over JSON — toke is the natural home for TOON implementation) |
| F4.2 | L | **Done** | Data profiler for schema extraction in toke (CSV, JSON, DB results → compact TOON profiles) |
| F4.3 | L | **Done** | LLMLingua prompt compression (5-20x, Python sidecar via REST or ONNX runtime — interface unchanged) |
| F4.4 | L | **Spec done** | Semantic cache (vector store via ooke native bindings — replaces LanceDB Node.js library; embedding similarity, configurable threshold and TTL) |
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
| F6.2 | L | **Spec done** | Audit trail system (append-only, hash chain, tamper detection, export, SIEM forwarding; metadata only — never stores prompt/response content) `[R3.5, R4.7]` |
| F6.3 | M | **Spec done** | Vector store for semantic operations (via ooke native bindings — replaces LanceDB; prompt cache, routing examples) |
| F6.4 | L | **Spec done** | Secure ephemeral storage (mlock equivalent via ooke, secure wipe, auto-expiry, no disk serialisation) |
| F6.5 | M | **Done** | Database backup and restore (consistent snapshot via SQLite VACUUM INTO, timestamped naming, configurable retention, restore with validation) `[R3.8, R8.5]` — *spec remains valid* |
| F6.6 | M | **Done** | Persistent sync queue (enqueue/dequeue with retry and exponential backoff, survives restarts — implemented in toke) `[R3.4, R8.7]` — *spec remains valid* |
| F6.7 | M | **Done** | Namespaced settings store (typed key-value: string, number, boolean, JSON; `loke.*` prefix + application prefix; get/set/list API — implemented in toke) `[R3.3]` — *spec remains valid* |

## Epic F7: MCP Framework

*Host, connect to, and broker MCP servers with full privacy filtering on all data flows. MCP protocol is language-agnostic; client and server implemented in toke.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F7.1 | L | **Done** | MCP client implementation in toke (tool discovery, invocation, privacy filtering on all data) |
| F7.2 | L | **Done** | MCP server hosting in toke (expose loke.anonymise, loke.compress, etc. to connected LLMs) |
| F7.3 | XL | **⏸ On hold** | MCP broker for intermediary routing in toke (local/companion/cloud, policy enforcement, audit) |
| F7.4 | L | **Done** | toke MCP server in toke (compress, decompress, template, analyse — TOON+LLMLingua backend; toke is the natural implementation language) |
| F7.5 | M | **Spec done** | Local MCP server discovery (mDNS/Bonjour via ooke, explicit approval, companion devices) |

## Epic F8: Companion Device Support

*Extend local compute to nearby high-power devices over secure direct connections. Implemented in toke on ooke.*

> Now unblocked — std.mdns and std.tls bindings are available.

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| F8.1 | L | **Spec done** | Companion device discovery and pairing (mDNS via ooke, confirmation codes, security checks) |
| F8.2 | L | **Spec done** | Secure communication channel (TLS 1.3 mutual auth, certificate pinning, heartbeat — via ooke TLS primitives) |
| F8.3 | XL | **Spec done** | Remote model execution (companion Ollama/Exo via REST, router integration, privacy pipeline applied) |
| F8.4 | L | **Spec done** | Exo distributed inference integration (GPL-3.0 boundary maintained — REST API only, cluster monitoring) |

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
| P1.1 | M | **Spec done** | HTTP server core (configurable host:port, default localhost:3000, optional TLS for local use, serves client directory as static assets with SPA fallback) `[R2.1, R2.2]` |
| P1.2 | L | **Spec done** | Versioned API routing (prefix `/api/v1/`, plugin-based route registration, applications register under own namespace) `[R2.3]` |
| P1.3 | L | **Spec done** | Composable middleware pipeline (enforced order: request ID → logging → CORS localhost-only → body size limit → timeout → auth pluggable → validation → error handling; named insertion points for app middleware) `[R2.4]` |
| P1.4 | M | **Spec done** | Standard response envelopes and request validation (success/error/paginated shapes, Zod schema validation on params/query/body, structured 400 errors) `[R2.5, R2.6]` |
| P1.5 | M | **Spec done** | Security hardening (CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy, HSTS in production, configurable per-route rate limiting with 429 responses) `[R12.1, R12.3]` |

## Epic P2: Platform Extensibility

*Plugin system and extension points so applications add domain-specific behaviour without forking the core.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P2.1 | XL | **Spec done** | Plugin registration system (routes, middleware at named insertion points, health checks, navigation items, settings sections, views — single registration API) `[R2.3, R1.4, Section 6]` |
| P2.2 | M | **Spec done** | Startup and shutdown hooks (onBeforeStart, onAfterStart, onBeforeShutdown callbacks; applications run custom init/cleanup logic within the lifecycle) `[Section 6]` |
| P2.3 | M | **Spec done** | Extensible configuration modules (applications extend base Zod schema with domain-specific sections, additional env variables, validated at startup alongside platform config) `[R1.2, Section 6]` |
| P2.4 | M | **Spec done** | Anonymisation pattern registration (applications register entity types + detection regexes + confidence weights; merged into privacy pipeline at startup; hot-reload supported) `[R4.2, Section 6]` |
| P2.5 | L | **Spec done** | Extension point documentation and contracts (versioned interfaces, semver compatibility guarantees, breaking change policy, migration guides for major versions) `[Section 6]` |
| P2.6 | L | **Done** | Privacy pipeline hook API (applications insert custom stages into the privacy pipeline without forking core; hook slots: `before_ner`, `after_anonymise`, `before_restore`, `after_restore`; each hook receives the current pipeline state and returns a modified state; hooks registered at startup via `pipeline.register_hook(slot; f)`; hook execution order: registration order; errors in hooks are logged and skipped — never crash the pipeline; hooks visible in pipeline console A4.2; used by moke for schema-first and local compute injection) |
| P2.7 | M | **Done** | Custom LLM provider registration (applications register new provider adapters without forking `providers/dispatcher.tk`; adapter interface: `connect():bool`, `generate(prompt;opts):str`, `embed(text):@(f32)`, `health():bool`; registered via `providers.register(id; adapter)`; auto-included in router model registry; appears in model selector UI; capability declarations: streaming, tool-calling, embedding; used by moke to route data-analysis requests to schema-aware custom handler) |
| P2.8 | M | **Done** | Governance rule hook (applications inject custom rule evaluation into the governance gateway; hook receives `$eval_context` before risk classification; returns `?(str)` — `none` to proceed, a string reason to block; registered via `gateway.register_rule_hook(id; f)`; hook outcome logged in audit trail with hook id; used by moke to enforce schema-first protocol — block requests where raw data detected in prompt) |

## Epic P3: UI Platform

*Design tokens, theming, component primitives, and application shell — so applications get accessible, themed UI without building from scratch.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P3.1 | L | **Spec done** | Design token system (CSS custom properties, semantic tokens for colours/spacing/typography/borders/shadows/transitions, neutral default palette, applications override for branding) `[R5.1]` |
| P3.2 | M | **Spec done** | Dark mode and theming (system/light/dark via `data-theme` on root, CSS custom property overrides, OS preference detection in real time, persisted in settings) `[R5.2]` |
| P3.3 | S | **Spec done** | CSS reset and base styles (modern reset, typographic baseline, `:focus-visible` rings, `prefers-reduced-motion` handling, no framework dependency) `[R5.3]` |
| P3.4 | L | **Spec done** | Component primitives CSS (buttons, cards, badges, form elements with all states, tables with responsive scroll, alerts, loading indicators, tooltips — all via tokens, all overridable) `[R5.4]` |
| P3.5 | M | **Spec done** | Application shell (semantic HTML: header, sidebar nav, main content area, responsive sidebar collapse on narrow viewports; applications populate with own items) `[R5.5]` |
| P3.6 | L | **Spec done** | Client-side router (hash-based, route definitions with parameter extraction, 404 fallback, document title updates, screen reader announcements on navigation) `[R5.6]` |
| P3.7 | M | **Spec done** | Navigation component (configurable data-driven items, icons, badges, active state, keyboard arrow-key navigation, compact/expanded modes) `[R5.7]` |
| P3.8 | L | **Spec done** | Notification system (bell with unread count, dropdown panel, toast variants: info/success/warning/error, auto-dismiss, screen reader announcements, stored in local DB, API for applications) `[R5.8]` |
| P3.9 | M | **Spec done** | Base settings UI (appearance toggle, timezone, language, integration status, backup, about/version, update check — applications extend with own sections) `[R5.9]` |

## Epic P4: Internationalisation

*i18n framework so every user-facing string passes through a translation layer from day one.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P4.1 | L | **Spec done** | Translation function and locale loader (`t(key, params?)`, namespaced keys, `{{name}}` interpolation, pluralisation via `_zero/_one/_other` suffixes, fallback to base locale, lazy-loading of additional locales) `[R6.1, R6.3]` |
| P4.2 | M | **Spec done** | Locale file structure (JSON in `locales/`, platform keys prefixed `loke.*`, application keys use own prefix, community-contributed translations) `[R6.2]` |
| P4.3 | M | **Spec done** | Layout accommodation and formatting (30-50% text expansion tolerance, no hardcoded widths, LTR-safe without hardcoding LTR; locale-aware date/time/number via `Intl` APIs, relative time via `Intl.RelativeTimeFormat`) `[R6.4, R6.5, R9.5]` |

## Epic P5: Integration Framework

*Reusable primitives for connecting to external services — authentication, retry, circuit-breaking, offline queuing.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P5.1 | L | **Spec done** | Integration adapter interface (standard contract: connect, disconnect, health check, domain methods; handles auth, retry, timeout, circuit-breaking; applications implement for their own services) `[R8.1]` |
| P5.2 | L | **Spec done** | OAuth 2.0 support (authorisation code grant, token storage in OS credential store, automatic refresh, expiry handling; reusable by any integration needing OAuth) `[R8.2]` |
| P5.3 | M | **Spec done** | Base HTTP client (configurable timeout, retry with exponential backoff, circuit breaker — open after N failures/half-open after cooldown, request/response header logging, `Retry-After` awareness) `[R8.6]` |
| P5.4 | M | **Spec done** | Input sanitisation utilities (HTML stripping, SQL escape supplementary to parameterised queries, log injection prevention, schema validation with unknown property stripping) `[R12.2]` |

## Epic P6: Error Handling Framework

*Consistent error handling across server, client, and API boundaries — no raw errors leak to users.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| P6.1 | M | **Spec done** | Server error handling (global catch for unhandled errors, log with correlation ID, consistent error response shape `{ error: { code, message, requestId } }`, never expose stack traces to client) `[R13.1]` |
| P6.2 | M | **Spec done** | Client error handling (global handlers for uncaught exceptions and unhandled rejections, report to server for logging, user sees toast notification not raw error, rate-limited to prevent floods) `[R13.2]` |
| P6.3 | M | **Spec done** | API client wrapper (handles network errors, timeouts, HTTP error statuses, JSON parse failures; retries on 5xx with configurable attempts; applications use this instead of raw fetch) `[R13.3]` |

---

# APPLICATION LAYER

## Epic A1: Browser Mode — Chromium Workspace

*Browser-based workspace with full privacy protection.*

| Story | Size | Summary |
|-------|------|---------|
| A1.1 | L | Tab and navigation management (tabs, history, bookmarks, keyboard shortcuts) |
| A1.2 | XL | Webpage content extraction with privacy filtering (selection, full page, form data, visual preview) |
| A1.3 | L | Chat interface / LLM interaction panel (dockable, streaming, transparency bar, pre-send preview) |
| A1.4 | L | Dashboard persistence and reuse (template extraction, parameterised re-rendering, token savings) |
| A1.5 | M | Web privacy metadata detection (robots.txt AI directives, data-ai-sensitivity attributes) |

## Epic A2: Terminal Mode — CLI & Coding LLM Proxy

*CLI that channels coding LLM interactions through loke's pipeline.*

| Story | Size | Summary |
|-------|------|---------|
| A2.1 | M | Direct prompting via CLI (`loke ask`, model selection, dry-run, stdin support, streaming) |
| A2.2 | XL | Coding LLM proxy mode (`loke proxy claude-code`, HTTP proxy/wrapper, real-time indicators) |
| A2.3 | L | Local compute preprocessing for code (codebase profiling, proprietary pattern detection, config scrubbing) |
| A2.4 | L | Multi-session terminal management (named sessions, shared/isolated contexts, audit trails) |
| A2.5 | M | Environment integration (`loke init`, shell profile, git hooks, VS Code config, `loke doctor`) |

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

| Story | Size | Summary |
|-------|------|---------|
| A6.1 | M | electron-builder packaging config (DMG for Mac, per-user NSIS for Windows, universal binary, output paths, app metadata — `dev.tokelang.loke`) |
| A6.2 | L | Code signing and notarization (Apple Developer ID + notarization pipeline, Windows EV certificate + timestamping, CI secret wiring) |
| A6.3 | L | Auto-update (electron-updater, startup version check, background download, user-prompted restart via P3.8, stable and beta channels, force-update flag for security releases, channel preference in F6.7) |
| A6.4 | M | Portable CLI binary (Node.js SEA build for `packages/cli`, bundles core + mcp-toke + mcp-broker + shared, single-file Mac/Windows output, GitHub Release attachment) |
| A6.5 | M | Per-user proxy configuration (MCP environment variable injection into shell profiles without admin; system-wide proxy as optional elevated step; runs after A6.6 port confirmation) |
| A6.6 | S | Port conflict detection and resolution (bind default `11430`, auto-select next free port in range, persist in F6.7, surface in first-run wizard A4.1 and `loke doctor` A2.5) |

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
| G1.4 | M | Accountability and ownership registry (business/technical/risk owner per use case; defaults to user for individual installs; owner metadata on every audit event; no use case active without assigned owner; `loke owners list`; changes logged) |
| G1.5 | M | AI justification requirement (new use case registration requires: purpose, why AI vs simpler alternative, expected value, identified risks; built-in justifications pre-written; suggest simpler paths when AI is unnecessary; enterprise sign-off workflow) |
| G1.6 | M | Kill switch and fallback mode (global: `loke kill-switch on` stops all external AI calls; per-provider, per-use-case, per-agent; graceful fallback messaging; persisted across restarts; audit trail; enterprise remote trigger via policy push) |

## Epic G2: Transparency and Explainability

*Make every AI decision explainable after the fact — not just for compliance, but because users deserve to understand what happened with their data.*

| Story | Size | Summary |
|-------|------|---------|
| G2.1 | L | Decision trace system (captures: original input, PII detected, anonymisation applied, compression applied, risk classification, policy decisions, model selected + why, prompt sent, response received, deanonymisation, final output; `loke trace <id>`; JSON export; agentic workflows trace every step; 90-day default retention) **[Done]** |
| G2.2 | L | "Why this output?" explanation generator (right-click → "Explain this" or `loke explain <id>`; generated locally by SLM from decision trace — no cloud call; plain language; source attribution for RAG responses; confidence indicators; thumbs up/down on the explanation) |
| G2.3 | S | AI content disclosure (all AI responses marked with subtle clear indicator; categories: AI-generated/AI-assisted/AI-summarised/AI-translated; disclosure metadata on copy/export; enterprise-configurable; user-configurable visibility) |

## Epic G3: Operational Monitoring and Incident Management

*Treat AI like a production system with failure modes — because it is one.*

| Story | Size | Summary |
|-------|------|---------|
| G3.1 | L | Output quality monitoring (automated checks: hallucination detection, coherence scoring, relevance scoring; thumbs-down rate tracking per model/use case/period; baseline establishment over 30 days; drift detection alerts; provider comparison; feeds G4 dashboards) **[Done]** |
| G3.2 | L | Incident management workflow (types: pii_leakage_suspected, policy_violation, quality_degradation, provider_outage, cost_overrun, agent_misbehaviour, security_concern; auto-created from monitoring or manual; severity: critical/high/medium/low; post-incident review template; `loke incidents list/create/resolve`; trends in G4) |

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
| G4.6 | M | Inference tier utilisation dashboard (per tier: request count and %, average response time, average quality rating from thumbs up/down, models used and frequency, tok/s achieved, cloud API cost comparison; trend charts of tier usage over time; quality comparison for same task types at different tiers; overnight window utilisation; hardware utilisation per tier — GPU%, RAM%, disk I/O; total cost avoided by running large models locally) |

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
| M1.4 | L | Automatic context enrichment (before every LLM call: search palace for relevant memories; top-N included as AAAK context; "Added N memories from palace" disclosure; user can disable; relevance threshold configurable; token budget cap default 2000; enrichment passes through anonymisation before cloud LLMs) |
| M1.5 | XL | Knowledge graph with temporal awareness (entity extraction by local SLM; relationship mapping; temporal validity windows — facts have start/end dates; contradiction detection flags for user review; `loke memory facts "who works on project-alpha?"`; `--as-of` time queries; graph visualisation in browser mode; privacy pipeline on any externally-included graph data) |
| M1.6 | L | Agent memory / diaries (each AG1 agent gets a dedicated palace wing; structured diary entries in AAAK after each run; diary loaded as context on startup; searchable; agent-scoped permissions; diary entries feed into project wings; older entries auto-compressed to closets) |

## Epic M2: AAAK Shorthand Integration

*AAAK is compressed English shorthand readable by any LLM without a decoder — not a programming language, not a binary format. Complementary to TOON (F4.1, structured data) and toke (prompt syntax): AAAK specifically optimises natural-language memory and context loading.*

| Story | Size | Summary |
|-------|------|---------|
| M2.1 | L | AAAK encoder/decoder (encoder: natural language → AAAK; e.g. "Priya manages Driftwood: Kai backend 3yr, Soren frontend, Maya infra" → `TEAM: PRI(lead) \| KAI(backend,3yr) SOR(frontend) MAY(infra)`; decoder: AAAK → natural language for human review; 5–30x compression; lossless for structured facts; works with any LLM; configurable compression level; benchmark token savings; integrates with mcp-toke F7.4) **[Done]** |
| M2.2 | L | Layered context loading (L0 ~20 tokens: identity; L1 ~150 tokens: AAAK palace map; L2 ~500 tokens: AAAK active context for current task; L3 variable: deep memory via M1.3 semantic search; startup loads L0+L1 only; L2 on task identification; L3 on-demand; configurable layer sizes; total budget enforced; progressive disclosure of what's loaded) **[Done]** |
| M2.3 | M | AAAK prompt shorthand (users write shorthand: `refactor auth.module \| extract.jwt.validation → separate.util \| keep.backward.compat`; loke expands locally before pipeline; optional — natural language always works; dots/pipes/arrows syntax; user-defined abbreviations via `loke shorthand add`; expanded version shown in pre-send preview) **[Done]** |
| M2.4 | L | Memory mining from external sources (import: Claude exports, ChatGPT exports, Slack JSON, markdown, code repos; mining modes: projects/conversations/general; privacy pipeline scan on import; local SLM processing only; incremental mining; `loke memory mine <path> --mode <type>`; interruptible and resumable; source attribution on mined content) |
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
| X1.4 | L | **Spec done** | Architecture document (layered model, runtime modes, pipeline data flow, package structure, extension point map, storage model, security boundaries, deployment model) |
| X1.5 | M | **Spec done** | Update threat model for platform layer (HTTP server attack surface, plugin system trust, OAuth token handling, i18n injection, middleware bypass, new trust boundaries) |
| X1.6 | M | **Spec done** | Update security audit checklist for platform layer (HTTP hardening, plugin sandboxing, OAuth flows, input sanitisation, rate limiting, CSP verification) |

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
| X3.1 | M | **Spec done** | Semantic HTML enforcement and ARIA support (all platform components use semantic elements, ARIA roles/states/properties where semantic HTML is insufficient, labels for all form controls) `[R7.1, R7.2]` |
| X3.2 | M | **Spec done** | Keyboard navigation framework (every interactive element reachable via keyboard, tab order follows visual order, arrow keys in composite widgets, Escape closes overlays, no mouse-only interactions) `[R7.3]` |
| X3.3 | M | **Spec done** | Focus management utilities (focus trapping for modals/dialogs, focus restoration on overlay close, programmatic focus on route changes, skip-to-content link as first focusable element) `[R7.4, R7.5]` |
| X3.4 | M | **Spec done** | Screen reader live regions (aria-live utility function for dynamic changes — page loads, notifications, status updates; polite and assertive priority levels) `[R7.6]` |
| X3.5 | S | **Spec done** | Colour independence and motion sensitivity (no colour-only state indicators, WCAG 2.1 AA contrast ratios, `prefers-reduced-motion` respected, no essential info via animation alone) `[R7.7, R7.8]` |
| X3.6 | M | **Spec done** | Automated a11y testing (axe-core integration in test suite, platform components must pass with zero violations, helper function for applications to run a11y checks) `[R7.9]` |

## Epic X4: Testing & Developer Experience

*Test infrastructure, quality gates, and developer tooling that both loke and applications share.*

| Story | Size | Status | Summary |
|-------|------|--------|---------|
| X4.1 | M | **Spec done** | Test utilities (in-memory test databases, test server instances, test config generators, integration mocks — reduce boilerplate for application tests) `[R15.2]` |
| X4.2 | M | **Spec done** | Quality gate script (single command: lint → format check → dependency audit → unit tests → integration tests → a11y tests → build; fails on any step; used as pre-push hook and CI gate) `[R15.5]` |
| X4.3 | S | **Spec done** | Watch mode for development (server restart + client reload on file change, fast feedback loop) `[R16.1]` |
| X4.4 | M | **Spec done** | Scaffold generator CLI (`loke generate migration`, `loke generate route`, `loke generate adapter`, `loke generate locale` — reduces manual boilerplate creation) `[R16.3]` |
| X4.5 | M | **Spec done** | Debug mode (request/response inspection, database query logging, pipeline stage tracing, route matching details — never enabled in production, activated via config flag) `[R16.5]` |

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

---

# SUMMARY

| Layer | Epics | Stories | Done/Spec done |
|-------|-------|---------|----------------|
| Foundation (F1–F9) | 9 | 56 | 55 |
| Platform (P1–P6) | 6 | 32 | 29 |
| Application (A1–A6) | 6 | 27 | 11 |
| Accountable AI (G1–G3) | 3 | 11 | 5 |
| Value & Governance (G4) | 1 | 6 | 5 |
| Agentic AI (AG1) | 1 | 8 | 8 |
| Memory Palace (M1–M2) | 2 | 11 | 7 |
| Cross-cutting (X1–X5, W1) | 6 | 30 | 30 |
| Demo — moke (MK1–MK7) | 7 | 34 | 34 |
| **Total** | **41** | **215** | **187** |
