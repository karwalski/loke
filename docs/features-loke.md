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
| Regex | `core/privacy/regex.tk` | 22 deterministic patterns: email, phone (AU/US), credit card, IP, TFN/ABN, SSN, URL, API key, Medicare, National Insurance number, GB driver number, and (only after their label) BSB, bank account, CRN, passport, driver licence, super member number, NHS number, sort code, NRIC/FIN | 0.60–0.99 |
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
| `confidence-weighted` | Mean of each layer's confidence meets `privacy.consensus_threshold` (default 0.5) | Tuned deployments with measured layers |

Set with `privacy.consensus_strategy` in `config.toml`; an empty or unrecognised name is applied as
`most-restrictive`. The voters are the layers that completed a scan of the text. Every strategy but
`most-restrictive` can leave something a layer detected unmasked.

**Entity Routing** (`core/privacy/entity_routing.tk`): `[[privacy.entity_routing]]` in config.toml names, per entity type, the layers whose detections of it are accepted, with fallback layers for when those are unavailable. Nothing is routed by default, and the regex layer's detections are never dropped by a route.

**Layer Health** (`core/privacy/layer_health.tk`): Monitors availability of each layer. System degrades gracefully — remains operational with at least one layer available. Reports HEALTHY or DEGRADED status.

> **What of the multi-layer composition is wired (F3b.11, verified against the code 2026-10-06).**
> `pipeline.run` runs its layers from `filter_registry.tk` (F3b.1), each through `layer_health.tk`
> (F3b.6); `sidecar_client.tk` is the privacy-filter layer when `privacy.privacy_filter = true`
> (F3b.3). It applies `[[privacy.layers]]` (`layer_config.tk`, F3b.2) and
> `[[privacy.entity_routing]]` (`entity_routing.tk`, F3b.5) from `config.toml`, resolves overlaps
> under `privacy.consensus_strategy` (`consensus.tk`, F3b.4) and records per-layer metrics
> (`filter_metrics.tk`, F3b.10). `loke privacy evaluate` runs every layer side by side and scores
> them against a labelled file (`comparison.tk`, `evaluation.tk`, F3b.9). An organisation policy, `~/.loke/loke.policy.json` (`org_policy.tk`, F3b.8), is applied over `config.toml` on every run (required and banned layers, a minimum layer count, a most-restrictive consensus floor, a maximum confidence threshold), only ever making privacy stricter; it is not distributed by the compliance engine and the user can delete it.
> A token-classification model registered with `loke privacy add-model` (`model_registry.tk`, F3b.7) is a further layer, served by the privacy-filter sidecar, its labels mapped to loke's entity types; it can only add to what is masked; the settings page adds, edits and removes registrations, and `detection_layers` names it (no ONNX). Not wired: `template.tk` has no importer.
> `mcp-broker` and the agent executor build the default registry and read none of the `config.toml` settings, though they do apply the organisation policy.
> Detail, with the test behind each statement: [privacy-filters.md](privacy-filters.md). Recorded as
> B1–B10 in [claims.md](claims.md).

**Pipeline Orchestrator** (`core/privacy/pipeline.tk`): Sequences all layers, deduplicates overlapping detections, escalates sensitivity classification (PUBLIC → INTERNAL → CONFIDENTIAL → RESTRICTED), generates reversible placeholders, injects guardian prompt.

> **The browser request path uses this orchestrator (GA1.1, GA1.10, NC1.9; checked against the code
> 2026-10-06, F3b.11).** `POST /api/pipeline` (`packages/browser/pages/api/pipeline.tk`) scans the text
> and any `system_prompt` with `core.privacy.systemprompt.runforward` and refuses with 503 when
> `pipeline.issafetoforward` is false; it also calls the kill switch, governance policy, audit,
> optimiser, cache, router and response restoration. Other consumers: the CLI (`ask`, `proxy`,
> `privacy evaluate`), the MCP broker, the MCP server and the agent executor. Claims A11, A13 and K6 in
> [claims.md](claims.md) predate this and are to be re-verified (GA1.11).

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

**Evaluation Mode** (`core/privacy/evaluation.tk`): Measures layer quality against labelled datasets — precision, recall, F1 score per layer. Invoked by `loke privacy evaluate --file <file>`, which reads the corpus JSONL or a `[{text, entities: [{start, end, type}]}]` JSON array (F3b.9). loke's `/evaluate` page shows each layer's detections on a sample text side by side (`POST /api/evaluate`), without values, with the detections entity routing did not accept, and scores a labelled file of either format per layer.

**Metrics** (`core/privacy/filter_metrics.tk`): Records, for each request, every layer's detection and accepted counts, counts and confidences by entity type, and measured time, with the consensus outcome; returned by `/api/pipeline` and bound into the audit hash chain (F3b.10). moke's governance page shows their aggregates (detections by layer per day and by entity type, agreement rate between layers, scan latency p50/p95/p99 by layer) from `GET /api/layermetrics`, over a selectable window (24 hours, 7 days, 30 days, all time); no MCP surface.

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

> **Strategies: four named selection strategies exist** (F5.3): `cheapest-adequate`, `fastest`,
> `best-quality` and `local-first`, in `core/router/strategy.tk`, each a comparator over one shared
> eligibility filter, selected by name (`[routing] strategy`; `routing.strategy` on the browser route).
> They rank the models already permitted; the adequacy floor is a fixed constant, not a measured quality
> threshold. Recorded as D3 in [claims.md](claims.md).

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
case, model, provider, sensitivity, risk tier, token counts in and out, cost, duration, correlation ID,
and the time of the insert in epoch milliseconds. Never stores prompt/response content or placeholder values.

> **Requests are recorded on the browser route only (GA1.4).** `/api/pipeline` calls `audit.insertevent`
> for a dispatch and its outcome, a privacy refusal, an approval hold and a kill-switch refusal
> (`tests/integration/test_audit_trail_e2e.tk`; counted over the built binary by `scripts/smoke_e2e.sh`).
> The CLI proxy, the broker and the MCP server record no request; a kill-switch change is recorded from
> any caller, `loke killswitch` included. Triggers reject `UPDATE` and `DELETE` on `audit_log` (GA5.9).
> Tracked as **GA5** and **DA1**; recorded as E4 in [claims.md](claims.md).

> **Where it is written, this is a per-interaction usage and cost ledger; the decision is kept beside it.**
> The five fields an assessor looks for — the policy decision, detected-entity types and counts, which
> detection layers scanned, the approval outcome and kill-switch state — are not in `audit_log`. Since
> GA5.5 the browser route persists them per outcome in a `decision_trace` table (`core/governance/trace.tk`,
> `tests/integration/test_decision_trace.tk`); that table is not append-only and not in the hash chain.
>
> Excluding prompt content and placeholder values is a deliberate privacy choice and it is kept. The
> consequence, stated rather than left implicit: the records show what was detected and decided on a
> request, not that the masking that followed was complete.
>
> It is a hash chain for tamper detection, within a stated limit. Each row's digest is sha256 over the
> previous row's hash and every field (GA5.2); `loke audit verify` names the first row whose fields, hash
> or predecessor no longer match (GA5.3), which `test_audit_trail_e2e.tk` and `scripts/smoke_e2e.sh` show
> on an edited field, an edited hash and a deleted row. The limit: the chain is unkeyed and unanchored, so
> someone who can write the file can rewrite a row and recompute every hash after it undetected.
>
> So: *design* effectiveness — the control is present and specified — is established by reading the code
> and [architecture.md](architecture.md) §7. *Operating* effectiveness — the control ran as specified
> throughout a period — is what this ledger does **not** evidence: rows carry the host clock's time, but
> only one route writes them and nothing attests the clock. Do not present it as the latter.

**Log Redaction** (`core/privacy/logsanitiser.tk`): All log output passes through an auto-redaction filter (GA2.4). Emails, phone numbers, API keys, authorization tokens, passwords, and other sensitive values are replaced with `[REDACTED]` before reaching any log destination. Debug mode is subject to the same redaction rules as production.

**Settings Store** (`core/storage/settings.tk`): Namespaced typed key-value (string, int, bool, float, JSON).

**Vector Store**: ooke native bindings for semantic cache and memory palace.

**Ephemeral Store**: In-memory key-value with auto-expiry, no disk serialisation. Scoped per-session.

---

### Governance Gateway

**Policy Engine** (`core/governance/policy.tk`): Risk classification (low/medium/high) based on sensitivity × use case risk × cost. Decisions: allow, allow-with-warning, require-approval. Controls escalate with risk: anonymisation → audit logging → guardian prompt → human preview → cost confirmation → explainability trace.

**Kill Switch** (`core/governance/kill_switch.tk`): Global, per-provider, per-use-case, per-agent scope. Engage with reason and auto-release time. Persisted to settings with chain-of-custody metadata. Checked before every AI call.

**Use Case Registry** (`core/governance/types.tk`): Built-in categories: chat-completion, code-generation, code-review, summarisation, data-analysis, translation, classification, agent-task, mcp-tool-call. Schema: ID, name, risk level, purpose, approved models, owner.

**Decision Trace** (`core/governance/trace.tk`): A structure describing the pipeline path — original
input, PII detected, anonymisation, compression, risk classification, policy decision, model, provider,
prompt sent, response received, de-anonymisation. **What is persisted is the decision, not the path**
(GA5.5): the browser route writes one `decision_trace` row per outcome with the policy decision, risk tier, entity types and counts, layers scanned
and skipped, approval outcome and kill-switch state. Input, prompt, response and output are excluded by design; the compression and de-anonymisation flags are never set.

**Monitoring** (`core/governance/monitoring.tk`, `core/governance/incidents.tk`): an incident register with P0–P3 severity levels, open/investigating/resolved status and a post-incident review template, and a per-model thumbs-up trend over a window of days. No incident types are defined (an incident carries a free title), and no request path, command or page calls either module.

**Scorecard** (`core/governance/scorecard.tk`, `core/governance/dashboard.tk`): a per-provider scorecard (requests, latency, error rate, cost) and a governance scorecard over a period (privacy coverage, local routing ratio, cost, open incidents, audit chain integrity), both derived from the audit trail. Compliance violations, a risk tier breakdown, ownership coverage, trend charts and drill-down are not built.

> **Its figures are only what the trail holds, and nothing shows them yet.** Its inputs are the audit trail,
> which records the browser route's requests only (above); no command or page imports either scorecard.
> `metrics_raw` has been created since DA1.2, and `/api/pipeline` writes a row per dispatch since DA1.3. Since DA1.6,
> `core/audit/metrics.tk` aggregates the table, but nothing on this page reads it yet (DA1.5). The compliance checks in `core/governance/compliance.tk`
> read the store: an empty trail fails, the chain is verified and the append-only triggers are read back;
> the two privacy rows say `ASSERTED`, not `PASS`. No command or page runs them either. Tracked as **DA1.5**,
> **GA5.7**; recorded as E9, E12, F1 and F2 in [claims.md](claims.md).

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

Port 11430. Localhost-only: the server binds to `127.0.0.1` by default (`[server] host` in `ooke.toml`), and `scripts/smoke_e2e.sh` asserts with lsof that the running listener is on `127.0.0.1` only (GA2.5). ooke native binary serving both API endpoints and UI pages.

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

> **`/api/savings` returns zeros.** The endpoint returns a fixed string and reads nothing. The data now
> exists: `/api/pipeline` writes a `metrics_raw` row per dispatch and per cache hit (DA1.3), and
> `core/audit/metrics.tk` aggregates it (DA1.6). The endpoint does not call either. Wiring it is
> **DA1.5**. Recorded as F1 and F2 in [claims.md](claims.md).
>
> **`/api/pipeline` runs the core pipeline** — see the Pipeline Orchestrator note above (A13).

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

**MCP Server** (`mcp-toke/src/server.tk`): Port 11460. Tools: compress, decompress, template, analyse.

**MCP Broker** (`mcp-broker/src/server.tk`): Port 11436. Connects local MCP servers. Per-server permissions (tool allowlist/denylist, max-cost, require-approval). Privacy pipeline on all tool call data.

> **There is no audit trail on broker invocations.** No file under `packages/mcp-broker/src/` or
> `packages/mcp-toke/src/` imports any audit module, so nothing is recorded: only the browser route
> records requests in the trail (see Audit Trail above). The permissions and
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

- **GA1: Pipeline Integration** (GA1.1-GA1.10) — the privacy pipeline, response restoration, kill switch,
  audit logging, token optimisation, semantic cache, router and governance policy are called from the
  route the browser serves (`packages/browser/pages/api/pipeline.tk`, registered at
  `packages/browser/src/_handlers.tk:132`). An earlier mechanical sweep deleted six of those calls; GA1.10
  restored them. The cache is a miss unless its embedding model is installed. Re-verified 2026-10-07
  (GA1.11): see the Pipeline Orchestrator note above and A13/K6 in [claims.md](claims.md), which name the
  smokes and tests behind each call. The audit trail's own limits are in the Audit Trail notes above.
- **GA2: Security Hardening** (GA2.1-GA2.5) — API keys saved through settings go to the OS keychain (keys already in `settings.json` are not migrated, GA2.1), auto-redaction on all log output, and localhost-only binding is intended but not enforced (GA2.5, T-43). Two items in this epic did not hold: database encryption is not active (above), and the source licence headers were subsequently removed wholesale by a migration script. Attribution is via `LICENSE` and `NOTICE`.
- **GA3: UX Alignment** (GA3.1-GA3.7) — Full accessibility overhaul with ARIA labels, graduated 4-level warning system, simple/advanced view toggle, pre-send cost estimation, cancel in-flight requests, feedback comments on thumbs-down, sensitivity explanation tooltips.
