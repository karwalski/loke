# loke — Feature Document

**Version:** 0.2.1
**Generated:** 2026-05-20 · **Revised:** 2026-09-19
**License:** Apache 2.0

loke is a locally-run intelligence layer between users and external LLMs. It intercepts, anonymises, optimises, and routes LLM traffic. The mission is to keep people "between the lines" — regulatory, organisational, cost, and ethical.

> **This is a feature inventory, and a listing here is not evidence that a feature is wired.** Several
> modules described below compile and are unreachable from any request path. Each such case carries an
> inline note naming what is actually true and the story that would fix it; the full mapping of claim →
> code → proof is [claims.md](claims.md). **No figure in this document is a measurement.** Figures come
> only from [metrics-baseline.md](metrics-baseline.md), which currently publishes none and names the ones
> that have been withdrawn.

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

Multi-layer detection system applied to outbound data on the fallback path before it reaches an external LLM.
It reduces what is disclosed; it does not ensure that everything sensitive is found — see
[threat-model.md](threat-model.md) §10.6 and [architecture.md](architecture.md) §4.2.

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

> **The multi-layer composition above is written but not wired.** Ten Epic F3b modules —
> `consensus.tk`, `entity_routing.tk`, `layer_health.tk`, `layer_config.tk`, `filter_registry.tk`,
> `filter_metrics.tk`, `evaluation.tk`, `org_policy.tk`, `sidecar_client.tk` and `template.tk` — have
> **zero importers**. `pipeline.tk:8-13` imports regex, Presidio and NER by name in a fixed order and
> de-duplicates overlaps itself.
>
> Specifically: the four consensus strategies are **not implemented** —
> `consensus.tk:24-38` accepts a `strategy` argument, ignores it, and marks every detection `mask`;
> `strategyname()` at `:42` returns the four names as display strings only. No entity-routing or
> layer-priority configuration is read. No HEALTHY/DEGRADED status is aggregated — degradation happens
> via each layer's own `isavailable()`. `Evaluation Mode` has no invocation point (there is no
> `loke privacy evaluate` command) and no labelled corpus to run against (**AD1.1**). No per-layer
> metrics are recorded. And nothing calls the sidecar client, so the privacy-filter sidecar — which does
> run a real published model — is not reachable from loke; the browser route talks to port 11435 over
> raw HTTP instead. The sidecar's declared `confidence_threshold` is never applied, so there is no
> operating point to tune (**AD1.4**).
>
> Wiring these or withdrawing the claim is **AD1.7**. Recorded as B1–B10 in [claims.md](claims.md).

**Pipeline Orchestrator** (`core/privacy/pipeline.tk`): Sequences all layers, deduplicates overlapping detections, escalates sensitivity classification (PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED), generates reversible placeholders, injects guardian prompt.

> **The browser request path does not use this orchestrator, and the GA1 completion claim does not
> hold.** The route registered for `/api/pipeline` is `packages/browser/pages/api/pipeline.tk`
> (`packages/browser/src/_handlers.tk:34-35,129`), which imports only `std.http`, `std.str`, `std.json`
> and `std.file`. It calls the sidecar on port 11435 directly and, when the sidecar does not answer,
> falls through to five literal `str.contains` checks (`:36-41`) that increment an entity counter
> **without altering the text** — then posts that unaltered text to `api.anthropic.com` (`:56`) or Ollama
> (`:62`) while still returning an `entities_found` count and a `sensitivity` label. None of the nine
> capabilities listed for that path previously — full detection stack, response restoration, kill-switch
> check, audit logging, token optimisation, semantic cache, routing, governance policy evaluation — is
> present on it. The only browser file importing `core.privacy.pipeline`,
> `packages/browser/extensions/core.tk:5`, is reached solely from `pages/installer.tk`.
>
> The orchestrator's real consumers are the CLI proxy (`packages/cli/src/proxy.tk:9`), the MCP broker
> (`packages/mcp-broker/src/proxy.tk:8`), the MCP server (`packages/mcp-toke/src/tools.tk:8`), the agent
> executor and the response scanner. Failing closed instead of open is **NC1.9**; the bypass corpus that
> would catch this in CI is **AD1.6**. Recorded as A11, A13 and K6 in [claims.md](claims.md).

**Placeholder System** (`core/privacy/placeholder.tk`): Generates `[ENTITY_TYPE_N]` tokens (e.g.
`[EMAIL_1]`, `[PERSON_2]`). Stores original → placeholder mapping. Restores placeholders in LLM responses
to original values.

> **Tokens are neither consistent across prompts nor currently collision-free.** The index passed to
> `makeplaceholder(entitytype, index)` is the length of the whole entity array, so it is ordinal within a
> single request and shared across entity types: the same value gets a different token in a different
> prompt. Separately, both NER layers return a hardcoded constant — `"[" + label + "_NER_1]"` — so every
> `PERSON` in a prompt collapses to `[PERSON_NER_1]` and restoration can substitute the wrong person's
> name. Fixing the collision is **PL1.1**; deciding the scoping policy deliberately is **PL1.3**. Restore
> also has an off-by-one: the loop bound at `placeholder.tk:46` is `i>len` where valid indices end at
> `len-1`, so it reads one index past the end of the entry array (**PL1.2**).

**Evaluation Mode** (`core/privacy/evaluation.tk`): Measures layer quality against labelled datasets — precision, recall, F1 score per layer. *(Unwired — see the F3b note above.)*

**Metrics** (`core/privacy/filter_metrics.tk`): Tracks detection count, processing time, average confidence, and entity counts per layer. *(Unwired — see the F3b note above.)*

---

### Token Optimisation

| Component | Module | Savings | Description |
|-----------|--------|---------|-------------|
| TOON serialiser | `core/optimiser/toon.tk` | not measured | Converts JSON to compact TOON format with type detection and abbreviation. The saving computed in code is a character-length ratio, not a token count |
| LLMLingua | `core/optimiser/llmlingua.tk` | not measured | REST client for adaptive prompt compression. **The sidecar is not bundled**, so this path is inert out of the box |
| Semantic cache | `core/optimiser/cache.tk` | not measured | Vector-store backed prompt cache — embedding similarity (0.92 threshold), 24h TTL, auto-eviction. Hit rate depends entirely on the workload |
| Token budget | `core/optimiser/budget.tk` | — | Daily/weekly/monthly limits with pre-flight cost estimates |

**No combined figure is published.** The previously-quoted 60–80% had no benchmark behind it and is
withdrawn — see [metrics-baseline.md](metrics-baseline.md). The methodology to measure it is written in
[research/toon-benchmark-methodology.md](research/toon-benchmark-methodology.md) and not yet executed
(VM1.7).

---

### LLM Router

**Intent Classification** (`core/router/intent.tk`): Keyword and pattern cascade. Categories: chat, code generation, code review, summarisation, classification, NER, embedding, data analysis.

> **Not an embedding model, and not timed.** `intent.tk:55-67` is a cascade of `str.contains` substring
> checks returning a literal `method:"keyword"`. It is deliberately cheap and is described that way
> rather than as semantic. The latency figure previously quoted here is withdrawn — no timing test exists
> anywhere in the tree, and `std.test` cannot record a number in the first place (**VM1.1**). See
> [metrics-baseline.md](metrics-baseline.md).

**Sensitivity Scoring** (`core/router/sensitivity.tk`): Derives PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED from PII detection and content analysis.

**Model Selection** (`core/router/selector.tk`):
- Decision factors: task type, sensitivity, latency tolerance, cost constraints, model tier
- Model registry: Ollama, Anthropic (Claude), OpenAI (GPT-4o), Google (Gemini), Mistral, OpenRouter, local inference
- Context windows: Claude (200K), GPT-4o (128K), Qwen-72B (128K), Qwen-7B (32K)

> **The four named selection strategies do not exist.** `cheapest-adequate`, `fastest`, `best-quality`
> and `local-first` were listed here and score **zero matches** across `packages/` and `src/`. One fixed
> selection path exists in `selector.tk`; there is nothing to configure and nothing to select between.
> Story F5.3 is marked Done in the backlog and should be reopened. Recorded as D3 in
> [claims.md](claims.md).

**Latency Tolerance** (`core/router/latency_router.tk`): three tiers — `interactive`, `considered`,
`background` (`:18-49`). Unlocks larger models for non-urgent tasks.

> The per-tier latency budgets are declarations in the constraint constructors, not measurements. Nothing
> has been timed on target hardware, and there is no Apple Silicon test machine (**VM1.4**). The tiers
> were previously named "instant / patient / background" here, which matches neither the code nor the
> README.

**RouteLLM Integration**: REST client for external cost-signal routing (`core/router/routellm.tk`).

> **Unwired, and the figures are withdrawn.** `routellm.tk` has **zero importers** — nothing queries it.
> The cost-reduction and quality-retention percentages previously quoted here were a third-party result
> repeated with no citation, no workload and no definition of the quality metric; they are withdrawn in
> [metrics-baseline.md](metrics-baseline.md). Recorded as D6 in [claims.md](claims.md).

---

### Storage & Audit

**Database** (`core/storage/db.tk`): SQLite via ooke native bindings. WAL mode, numbered migrations,
parameterised queries (no string concatenation).

> **Encryption at rest is not currently active.** A 32-byte key is generated and stored in the OS
> keychain correctly, but the toolchain links plain SQLite, which silently ignores the encryption
> pragma and returns success — which the calling code maps to a successful result. The database is
> therefore **plaintext on disk**; rely on full-disk encryption. loke's own compliance check already
> reports this state. Tracked as X8.

**OS Keychain Integration** (`core/storage/keychain.tk`, `core/config/keychain.tk`): API keys and secrets stored in the OS keychain via Security framework bindings (GA2.1). Keys are fetched per-request with expiry validation, never written to disk, and never appear in log output.

**Audit Trail** (`core/storage/audit.tk`): One row per AI call is specified. Records: event type, use
case, model, provider, sensitivity, risk tier, token counts in and out, cost, duration, correlation ID.
Never stores prompt/response content or placeholder values.

> **No row is currently written, and the GA1.4 wiring claim does not hold.** `logevent` (`audit.tk:27`)
> holds the only `INSERT` into `audit_log` in the tree and **has no callers**; the module's only importer
> is the report engine, which reads. No browser, CLI, proxy, broker or agent path calls it, and
> `packages/browser/extensions/core.tk:61` returns `0` for the audit store rather than opening one. The
> table is empty, so the scorecard, the monitoring trends and the report engine below all read nothing.
> Tracked as **GA5** and **DA1**; recorded as E4 in [claims.md](claims.md).

> **Even once written, this is a per-interaction usage and cost ledger, not evidence that the privacy control operated.**
> Five fields an assessor would look for are **not** recorded: the policy decision, detected-entity
> detail, which detection layer fired, the approval or override outcome, and kill-switch state. They
> exist only on the `$decisiontrace` structure in `core/governance/trace.tk`, which has no table and no
> insert — `complete()` writes one log line and discards it (GA5.5).
>
> Excluding prompt content and placeholder values is a deliberate privacy choice and it is kept. The
> consequence, stated rather than left implicit: with neither the content nor the decision recorded, the
> trail cannot show that anything was detected or masked on a given request.
>
> It is also not yet tamper-evident or time-ordered. `created_at` receives the string literal `'now()'`,
> so every row carries the same seven characters and there is no time basis (GA5.1); the stored digest is
> a concatenation of two non-secret fields and does not incorporate the previous row, so nothing chains
> (GA5.2) and no verifier exists (GA5.3); and nothing enforces append-only — ordinary `DELETE` and
> `UPDATE` on `audit_log` are unrestricted (GA5.9).
>
> So: *design* effectiveness — the control is present and specified — is established by reading the code
> and [architecture.md](architecture.md) §7. *Operating* effectiveness — the control ran as specified
> throughout a period — is what this ledger does **not** evidence, and without a time basis there is no
> period for it to evidence. Do not present it as the latter.

**Log Redaction** (`core/privacy/logsanitiser.tk`): All log output passes through an auto-redaction filter (GA2.4). Emails, phone numbers, API keys, authorization tokens, passwords, and other sensitive values are replaced with `[REDACTED]` before reaching any log destination. Debug mode is subject to the same redaction rules as production.

**Settings Store** (`core/storage/settings.tk`): Namespaced typed key-value (string, int, bool, float, JSON).

**Vector Store**: ooke native bindings for semantic cache and memory palace.

**Ephemeral Store**: In-memory key-value with auto-expiry, no disk serialisation. Scoped per-session.

---

### Governance Gateway

**Policy Engine** (`core/governance/policy.tk`): Risk classification (low/medium/high) based on sensitivity × use case risk × cost. Decisions: allow, allow-with-warning, require-approval. Controls escalate with risk: anonymisation → audit logging → guardian prompt → human preview → cost confirmation → explainability trace.

**Kill Switch** (`core/governance/kill_switch.tk`): Global, per-provider, per-use-case, per-agent scope. Engage with reason and auto-release time. Persisted to settings with chain-of-custody metadata. Checked before every AI call.

**Use Case Registry** (`core/governance/types.tk`): Built-in categories: chat-completion, code-generation, code-review, summarisation, data-analysis, translation, classification, agent-task, mcp-tool-call. Schema: ID, name, risk level, purpose, approved models, owner.

**Decision Trace** (`core/governance/trace.tk`): A seventeen-field structure describing the full pipeline
path — original input, PII detected, anonymisation applied, compression, risk classification, policy
decisions, model selected (with reason), prompt sent, response received, de-anonymisation. **It is not
persisted:** there is no table, no insert and no caller; `complete()` writes a single log line and discards
the structure. Persisting it, and adding its fields to the audit record, is story **GA5.5**.

**Monitoring** (`core/governance/monitoring.tk`): Incident types: PII leakage suspected, policy violation, quality degradation, provider outage, cost overrun, agent misbehaviour, security concern. Severity levels, post-incident review templates, trend tracking.

**Scorecard** (`core/governance/scorecard.tk`): Privacy %, compliance violations, risk tier breakdown, ownership coverage, open incidents. Trend charts (7d/30d/90d), drill-down.

> **Every figure it produces is currently zero or empty.** Its inputs are the audit trail, which is never
> written (above), and the metrics tables, which are stubbed — `core/audit/metrics.tk:37-88` returns
> zero-filled structs from every function and `export()` returns `""`, while
> `core/metrics/collector.tk:59,96` reads and writes a `metrics_raw` table that no migration creates and
> that nothing calls `record` on. The compliance checks it surfaces are hardcoded: `core/governance/compliance.tk:42-56`
> and `:82-90` assert `PASS` on the privacy and audit controls without querying the store — including
> asserting that the audit trail is complete. Tracked as **DA1.2**, **DA1.3**, **DA1.6**, **GA5.7**;
> recorded as E9, E12, F1 and F2 in [claims.md](claims.md).

---

### Agent Framework

**Agent Definition** (`core/agents/`): YAML/TOML format with name, schedule/trigger, model preference, risk level, permissions, max cost per run, owner. Auto-registered in governance use case registry.

**Scheduling & Triggers**: Cron schedules, file change triggers, webhook triggers, MCP event triggers. Manual via `loke agents run` or UI. Chained execution with circular dependency detection.

> **Nothing fires automatically.** `core/agents/scheduler.tk:21-30` matches three literal strings by exact
> equality — `"0 * * * *"`, `"0 2 * * *"`, `"0 2 * * 0"` — and reports "unrecognised cron pattern" for
> anything else. There is no cron parser. Worse, `checkcron` ignores the current time and `checkdue`
> discards its `currenttimeepoch` argument, so a matching literal reports `shouldrun:true` on *every*
> check rather than at its scheduled time. File-change, webhook and MCP-event triggers (`:36-40`) all
> return a fixed `shouldrun:false`; no watcher or event source exists. Chain execution is modelled but
> unreachable for the same reason. Recorded as G2–G5 in [claims.md](claims.md).

**Execution Sandbox**: Permission enforcement (file access restricted to declared paths), cost limit enforcement with pause-and-alert, configurable time limit (default 5 min). All governance controls apply.

**Templates**: Daily digest, code review assistant, expense categoriser, meeting prep, documentation updater, security scanner.

**Overnight Batch**: Low-power mode 11pm–7am (configurable), full resource allocation, morning digest.

---

### Memory Palace

**Palace Structure** (`core/memory/palace.tk`): Wings → Halls → Rooms → Closets (AAAK summaries) → Drawers (verbatim) → Tunnels (cross-links). Storage: SQLite + vector store.

**Search** (`core/memory/search.tk`): Keyword matching over a weighted index table. Scoped by wing/hall.

> **Not semantic, and not timed.** `search.tk:104-130` issues
> `SELECT drawer_id, SUM(weight) … WHERE keyword LIKE ?` against `memory_index` — keyword prefix matching,
> no embeddings, no vector store, despite the module being described as semantic search elsewhere. The
> latency figure previously quoted here is withdrawn: no benchmark exists and no hardware was specified,
> and the figure would not describe this implementation even if it had been measured. See
> [metrics-baseline.md](metrics-baseline.md). Recorded as H3 and H4 in [claims.md](claims.md).

**Automatic Context Enrichment**: Before every LLM call, search palace for relevant memories. Top-N included as AAAK context. Anonymised before cloud LLMs.

**Knowledge Graph** (`core/memory/graph.tk`): Entity extraction, relationship mapping, temporal validity windows, contradiction detection, graph visualisation.

**AAAK Shorthand** (`core/memory/aaak.tk`): Natural language → compressed shorthand. Readable by any LLM without decoder. Layered context loading (L0 → L3: deep memory via search).

> The compression ratio previously quoted here was a design target and is withdrawn — see
> [metrics-baseline.md](metrics-baseline.md). Measuring it needs the numeric result sink that does not yet
> exist (**VM1.1**, **VM1.7**). The "L0: 20 tokens" figure is likewise a design budget, not a measurement.

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
| `/api/savings` | GET/POST | Token savings dashboard data — **currently serves zeros**, see below |
| `/api/approve` | POST | Approval workflow |
| `/api/tabs` | GET/POST | Browser tab management |

**Security**: CSP headers, HSTS, rate limiting, no stack traces leaked. CORS restricted to localhost origins.

> **`/api/savings` returns zeros.** Every function in `core/audit/metrics.tk:37-88` returns a zero-filled
> struct or an empty array and `export()` returns `""`. `core/metrics/collector.tk:59,96` reads and writes
> a `metrics_raw` table that no migration creates, and nothing calls `collector.record`. Replacing the
> stubbed module is **DA1.6**; creating the table and wiring the collector are **DA1.2** and **DA1.3**.
> Recorded as F1 and F2 in [claims.md](claims.md).
>
> **`/api/pipeline` does not use the core pipeline** — see the Pipeline Orchestrator note above (A13).

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

> **Only `loke doctor` and `loke proxy` do real work.** A fully wired `ask` implementation exists at
> `cli/src/ask.tk:114-179` — privacy filter, router, dispatcher, audit stage — and **nothing imports it**.
> The command the user reaches is `cli/src/main.tk:11-15`, dispatched at `:90`, which prints the prompt
> and "Pipeline not yet connected — use browser mode for full pipeline". `loke pipeline` (`:16-26`) prints
> seven stage names each labelled "pending" and executes none of them. `loke queue list`, `queue cancel`,
> `memory search`, `agents list` and `overnight status` (`:27-53`) all return fixed strings; two of them —
> "No jobs in queue" and "No agents registered" — are indistinguishable from a real empty result, so the
> CLI reports success while doing nothing. Recorded as K2–K4 in [claims.md](claims.md).

### MCP Framework

**MCP Server** (`mcp-toke/src/server.tk`): Port 11435. Tools: compress, decompress, template, analyse.

**MCP Broker** (`mcp-broker/src/server.tk`): Port 11436. Connects local MCP servers. Per-server permissions (tool allowlist/denylist, max-cost, require-approval). Privacy pipeline on all tool call data.

> **There is no audit trail on broker invocations.** No file under `packages/mcp-broker/src/` or
> `packages/mcp-toke/src/` imports any audit module, so nothing is recorded — and there would be nothing
> to record into, since the trail is never written at all (see Audit Trail above). The permissions and
> privacy claims do hold: `permissions.tk:25-56,206` enforces the allowlist, and
> `proxy.tk:62` anonymises outbound tool arguments while `:33` restores inbound responses. Note the
> asymmetry — an outbound privacy failure fails closed (`:58`), an inbound restore failure fails open with
> a warning (`:28-29`). Recorded as I1–I3 in [claims.md](claims.md).

### Desktop Distribution

DMG (macOS), NSIS (Windows). Code signing and notarisation. Auto-update via GitHub Releases. Portable CLI binary.

---

## Build & Test

**Build**: `./scripts/build_loke.sh` — compiles all toke modules to LLVM IR, links to 1.5MB arm64 native binary.

**Tests**: `./scripts/run_tests.sh` — discovers `test_*.tk` files, compiles and runs each, reports
pass/fail. 86 test files across privacy, memory, governance, storage, models, providers, agents, MCP, CLI
and optimiser.

> **Most of those files do not test production code.** 54 of the 86 carry an explicit
> `(* --- stub … *)` marker and re-declare the module under test instead of importing it; 12 import
> production modules, reaching 22 distinct ones. Discovery also excludes `*/test_harness*`
> (`scripts/run_tests.sh:25`), which silently removes `core/privacy/test_harness.tk` — the only harness
> able to score detection quality — from every run (**AD1.8**). See
> [test-coverage.md](test-coverage.md), which states both figures and what each means.

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

> **These are preset definitions loke ships, not enforced configurations, and they do not make a
> deployment compliant with any regulation.** The Consensus column names a strategy that is not
> implemented (see the F3b note above), and the Thresholds column names confidence floors that no code
> reads — the sidecar ignores its own threshold and the layer-config module has no importers. The
> presets themselves exist at `core/policy/presets/{gdpr,hipaa,au-privacy,ccpa}.tk` and are real policy
> definitions; what is not real is the machinery that would apply the Consensus and Thresholds columns.
> Rewording "makes you compliant" to "ships a preset for" across the project is **RG1.4**; withdrawing the
> absolutes is **RG1.5**. Recorded as B1 and E3 in [claims.md](claims.md).

---

## Performance Targets

> **These are design targets, and not one of them has been measured.** Four of the five were previously
> published as achieved figures and are withdrawn in
> [metrics-baseline.md](metrics-baseline.md#withdrawn-figures); they are retained here only as the budgets
> the design aims at. No timing test exists anywhere in the tree, and `std.test` exposes three
> string-comparison assertions and cannot record a value, so a test cannot publish a number even if one
> were taken (**VM1.1**). Two of the targets also describe implementations that no longer match the
> description — intent classification is a keyword cascade and memory search is keyword matching. Do not
> quote any row below as a result.

| Metric | Target | Measured |
|--------|--------|----------|
| Pipeline overhead (anonymise + compress + route) | < 1 second | never |
| Intent classification | < 10ms | never |
| First response token streaming | < 2 seconds after pipeline | never |
| UI interactions | < 100ms | never |
| Memory search (100K drawers) | < 500ms | never |

---

## GA Epics — Completed

The following GA (General Availability) epics have been completed, bringing all core engine features into active use across browser and CLI modes:

- **GA1: Pipeline Integration** (GA1.1-GA1.9) — **This epic should be reopened.** It was marked complete
  on the claim that the privacy pipeline, response restoration, kill switch, audit logging, token
  optimisation, semantic cache, router and governance policy are all wired into the browser handler. None
  of the eight is reachable from the route the browser actually serves
  (`packages/browser/pages/api/pipeline.tk`, registered at `packages/browser/src/_handlers.tk:129`), and
  the audit trail is not written from anywhere at all. See the Pipeline Orchestrator and Audit Trail notes
  above, and A13/E4 in [claims.md](claims.md). Tracked as **NC1.3**, **NC1.9**, **AD1.6**, **GA5**, **DA1**.
- **GA2: Security Hardening** (GA2.1-GA2.5) — API keys migrated to OS keychain, auto-redaction on all log output, localhost-only HTTP binding enforced. Two items in this epic did not hold: database encryption is not active (above), and the source licence headers were subsequently removed wholesale by a migration script. Attribution is via `LICENSE` and `NOTICE`.
- **GA3: UX Alignment** (GA3.1-GA3.7) — Full accessibility overhaul with ARIA labels, graduated 4-level warning system, simple/advanced view toggle, pre-send cost estimation, cancel in-flight requests, feedback comments on thumbs-down, sensitivity explanation tooltips.
