# loke Architecture

**Version:** 0.3.1
**Last updated:** 2026-09-19
**Status:** Living document

> **This document describes the intended architecture, not uniformly the implemented one.** Where a
> component is specified here but not wired, or wired differently, the discrepancy is recorded against
> a story in [claims.md](claims.md). Figures come only from
> [metrics-baseline.md](metrics-baseline.md); this document publishes none of its own.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Layered Architecture](#2-layered-architecture)
3. [Runtime Modes](#3-runtime-modes)
4. [Pipeline Data Flow](#4-pipeline-data-flow)
5. [Package Structure](#5-package-structure)
6. [Extension Points](#6-extension-points)
7. [Storage Model](#7-storage-model)
8. [Security Boundaries](#8-security-boundaries)
9. [Deployment Model](#9-deployment-model)

---

## 1. Overview

loke is a local-first privacy proxy implemented in toke on ooke. It sits between users and external
large language models. Its primary path sends a schema profile and the user's intent and executes the
returned artifact locally, so no data row is transmitted; its fallback path redacts personally
identifiable information with reversible placeholders and transmits the redacted text. Both paths
compress tokens and route to the best available model, and responses are restored before being returned
to the user. Everything runs on the user's device, and no cloud service is required for core
functionality. See [§4](#4-pipeline-data-flow) for the two paths and [§8](#8-security-boundaries) for
what "passes through the privacy filter" does and does not mean — loke sees only traffic addressed to
it, and is not a chokepoint on the machine.

loke is built on **ooke** ([github.com/karwalski/ooke](https://github.com/karwalski/ooke)) — a lightweight web application framework written in toke that compiles to a single native binary with no external runtime dependencies. All loke source is written in toke; there is no TypeScript, Node.js, or Electron dependency.

---

## 2. Layered Architecture

loke is structured in four layers. Each layer builds on the one below it and exposes a stable interface to the layer above.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         MOKE DEMO LAYER                             │
│                                                                     │
│  packages/moke/ — reference application demonstrating platform APIs │
│  Used for integration testing and as a template for new applications│
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                            │
│                                                                     │
│  Browser mode  │  CLI mode  │  Policy engine  │  Onboarding / UX   │
│  Feedback      │  MCP toke  │  MCP broker     │                     │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                         PLATFORM LAYER                              │
│                                                                     │
│  HTTP server   │  Plugin system  │  UI shell      │  i18n           │
│  Integration   │  Error handling │  Accessibility │  Testing / DX   │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                        FOUNDATION LAYER                             │
│                                                                     │
│  Privacy pipeline  │  Token optimiser  │  Router    │  Cache        │
│  Storage / audit   │  Governance       │  Agents    │  Memory palace│
└─────────────────────────────────────────────────────────────────────┘
```

### Foundation Layer

The core engine shared by all runtime modes. Contains the privacy pipeline (regex, NLP, SLM NER, Presidio), token optimisation (TOON, LLMLingua), LLM router, semantic cache, SQLite storage, audit trail, governance gateway, agent framework, and memory palace. Implemented entirely in toke; no external runtime is required.

### Platform Layer

The extensibility, UI, and infrastructure layer that application modes build on. Provides the ooke-hosted HTTP server, plugin registry and lifecycle, UI shell and component tokens, internationalisation, integration adapter framework, error handling, accessibility utilities, and testing/DX tools.

### Application Layer

User-facing modes and interfaces: browser mode (ooke native binary with web view), terminal mode (CLI and coding LLM proxy), policy and compliance engine, onboarding wizard, savings dashboard, feedback and reporting, and the MCP toke/broker servers.

### Moke Demo Layer

`packages/moke/` — a minimal reference application that exercises the platform APIs end-to-end. Used in integration tests and as a scaffold template.

---

## 3. Runtime Modes

### CLI Mode

loke starts an HTTP API on **port 11430**. The CLI (`loke`) communicates with this server. Configuration is loaded from `ooke.toml` plus environment overrides. Structured logging with correlation IDs; all sensitive fields are auto-redacted. `loke proxy` subcommand enables transparent proxy mode for coding LLM traffic.

### Browser Mode

loke runs as an ooke native binary hosting a web view. The web view renders the browser-mode UI served locally. Window management and IPC are handled by ooke's native web view bindings. Multi-platform: macOS first, Windows planned.

### Proxy Mode

An HTTP proxy listener on **port 11431** handles outbound requests destined for cloud LLM APIs
(Anthropic, OpenAI, Google, etc.), passing them through the fallback redaction path ([§4.2](#42-fallback-path--redact-and-forward-explicitly-a-fallback))
before forwarding. It is not a transparent interceptor: coding tools (Claude Code, Codex, Gemini CLI) must
be configured to point at `http://127.0.0.1:11431`, and anything addressed elsewhere never reaches it
(AD1.6).

---

## 4. Pipeline Data Flow

loke has **two** outbound paths, and they are not equivalent.

- **§4.1 — the no-custody path is primary.** A schema profile and the user's intent go out; an
  executable artifact comes back; the artifact is validated and then executed locally against data that
  never leaves the device.
- **§4.2 — the redaction path is a labelled fallback**, kept for work that genuinely needs prose. It
  transmits redacted text, which is a reduction in what is disclosed and not a prevention of
  identification.

Two things must be said before the diagrams, because both are easy to overclaim.

> **The no-custody data flow is not novel, and is not presented here as novel.** Handing a model a
> schema and executing the returned query locally is the default implementation of the whole text-to-SQL
> field — it is how BIRD, Spider and Spider 2.0 are scored — and it ships commercially today in
> Vanna.AI, WrenAI, Snowflake Cortex Analyst and Databricks Genie. Those products get the data flow
> right and make no security claim about it: no threat model, no artifact validation, no provenance.
> What loke does differently is treat that data flow as a **security control** — with a stated threat
> model, a closed non-Turing-complete artifact grammar validated before execution, a provenance state on
> every rendered value, and an audit obligation. The control is the contribution; the data flow is table
> stakes. See [research/disclosure-measurement-findings.md](research/disclosure-measurement-findings.md)
> §10 and §12.

> **Neither path supports the claim that the model receives no information.** A returned artifact is
> itself a channel. An adversary — or a compromised model — able to shape queries and observe results
> across several turns can extract cell values a piece at a time, including by binary search, without
> ever being sent a row. "The model never receives data" is therefore true at the byte level and not
> necessarily true at the information level, and **no published benchmark tests this**
> ([findings §11](research/disclosure-measurement-findings.md)). This is stated as an open problem
> rather than argued away. Bounding it — per-session limits on result cardinality, detection of
> value-probing query sequences, and disclosure accounting that counts *results returned to the model*
> as well as bytes sent — is story **NC1.10**. Until it is bounded, the no-custody claim travels with
> this limitation attached.

### 4.1 Primary path — no custody

```
User question + local dataset
    │
    ▼
┌───────────────────────────┐
│ Schema Profile (NC1.2)    │  Column names, inferred types, cardinality,
│  no values leave          │  null-rate, row count — and nothing else
└───────────┬───────────────┘
            │ schema profile + intent          ── this is what crosses the boundary ──
            ▼
┌───────────────────────────┐
│    Router (F5)            │  Sensitivity × cost × latency × capability
│  local or cloud model     │  Checks semantic cache before forwarding
└───────────┬───────────────┘
            │
            ▼
┌───────────────────────────┐
│   LLM Provider            │  Ollama (local) or cloud API
└───────────┬───────────────┘
            │ executable artifact (closed op set, no free-form code)
            ▼
┌───────────────────────────┐
│ Artifact Validation       │  Reject anything outside the NC1.1 grammar.
│  (NC1.1)                  │  toke exposes no sandboxing primitive, so a
└───────────┬───────────────┘  closed op set is the only safe design
            │ validated artifact
            ▼
┌───────────────────────────┐
│ Local Execution (NC1.7)   │  Runs against on-device data. Every card carries
│  data stays on device     │  resolved / unresolved / no-data provenance (NC1.6)
└───────────┬───────────────┘
            │
            ▼
        User Output
```

What is transmitted on this path is O(schema), not O(data), and it is declared and reviewable. It is
not "low leakage": schemas encode business logic and regulatory scope, and published work reconstructs
table names from a deployed text-to-SQL system at high accuracy. The supportable framing is **bounded
and auditable**, with the exact bytes inspectable — not minimal.

**Implementation status.** This is the specified primary path, not yet the shipped one. Today the
profile emitters embed real sample values and real min/max/mean (NC1.2), the Insight Lab's proposal path
never executes because client and server disagree on the request contract (NC1.3), the dashboard path
sends no schema at all (NC1.4), and the local query engine has no production caller (NC1.7). Read §4.1
as the target the NC1 stories are moving to, and §4.2 as what runs now.

### 4.2 Fallback path — redact and forward (explicitly a fallback)

For work that genuinely needs prose rather than a query, text is redacted and transmitted. Selecting
this path is meant to be an explicit, recorded decision rather than the default (NC1.8).

```
User Input
    │
    ▼
┌───────────────────────┐
│  Privacy Filter (F3)  │  Regex + NER layers + Presidio (optional sidecar)
│  PII → placeholders   │  Reversible mapping in local SQLite
└───────────┬───────────┘
            │ redacted prompt
            ▼
┌───────────────────────┐
│ Token Optimiser (F4)  │  TOON serialisation + LLMLingua compression
│  no figure published  │  (see metrics-baseline.md)
└───────────┬───────────┘
            │ compressed prompt
            ▼
┌───────────────────────┐
│    Router (F5)        │  Sensitivity × cost × latency × capability
│  local or cloud model │  Checks semantic cache before forwarding
└───────────┬───────────┘
            │ routed request
            ▼
┌───────────────────────┐
│   LLM Provider        │  Ollama (local) or cloud API via proxy
└───────────┬───────────┘
            │ raw response
            ▼
┌───────────────────────┐
│ Response Restoration  │  Replace placeholders with original values
└───────────┬───────────┘
            │ restored response
            ▼
        User Output
```

> **Residual risk on the fallback path, stated rather than implied.** Redacted text *is* transmitted.
> Redaction reduces disclosure; it does not prevent identification. Published work shows pretrained
> models inferring personal attributes from free text at high accuracy, and this project's own threat
> model states that no combination of detection layers guarantees complete detection
> ([threat-model.md](threat-model.md) §10.6) — so the residual on this path is *undetected entities plus
> inference from what remains*. There is no recall measurement against a labelled corpus yet (AD1.1).
> Two defects compound it today: the detection stack fails **open** — when the sidecar is unavailable
> the pipeline falls back to five substring checks and still transmits (NC1.9) — and the two NER layers
> emit a constant token per entity type, so multiple same-type entities collapse to one placeholder and
> restoration can substitute the wrong value (PL1.1).

> **loke is not a chokepoint on either path.** Applications must be configured to route through it,
> anything addressed elsewhere never reaches it, and a flag exists to disable the pipeline. Six classes
> of bypass are enumerated and testable (AD1.6). The supportable claim is that *when traffic is in
> path*, enforcement is ordered, recorded and inspectable. See §8.

**No token or cost figures are published from this document.**
[metrics-baseline.md](metrics-baseline.md) is the only source of figures, and it currently publishes
none; the previously-quoted 60–80% token reduction is withdrawn there.

---

## 5. Package Structure

```
src/
├── core/
│   ├── privacy/          # F3 — Privacy pipeline (regex, NLP, SLM NER, Presidio, orchestrator)
│   ├── router/           # F5 — LLM router and model registry
│   ├── optimiser/        # F4 — Token optimisation (TOON, LLMLingua, profiler)
│   ├── cache/            # Semantic cache
│   ├── storage/          # F6 — SQLite, migrations (encryption inert — X8)
│   ├── audit/            # F6.2 — Audit trail
│   ├── governance/       # G1–G4 — Policy engine, kill switch, spend caps, dashboards
│   ├── agent/            # AG1–AG3 — Agent framework, memory palace
│   └── memory/           # Memory palace (episodic + semantic)
├── browser/              # A1 — Browser mode shell, tabs, navigation, chat panel
├── cli/                  # A2 — CLI mode, coding LLM proxy
├── mcp-toke/             # MCP toke server (exposes loke tools as MCP)
├── mcp-broker/           # MCP broker (routes tool calls to local/cloud MCP servers)
├── platform/
│   ├── http/             # P1 — HTTP server, router, middleware, security, response
│   ├── plugin/           # P2 — Plugin registry, lifecycle, config, contracts
│   ├── ui/               # P3 — UI shell, tokens, theme, components, navigation
│   ├── i18n/             # P4 — Translator, locales, layout
│   ├── integration/      # P5 — Adapter interface, OAuth, HTTP client, sanitise
│   ├── error/            # P6 — Server error, client error, API client
│   ├── a11y/             # X3 — Accessibility: semantic, keyboard, focus, live regions, colour, testing
│   └── testing/          # X4 — Test utilities, quality gate, watch, scaffold, debug
└── shared/               # Shared types, utilities, configuration
packages/
└── moke/                 # Reference demo application
```

---

## 6. Extension Points

### P2.6 — Privacy Pipeline Hooks

Plugins may register handlers for the `privacy.before` and `privacy.after` insertion points. Handlers receive the prompt and may append additional entity detections. They cannot suppress built-in detection layers. Registered via `plugin.registry.register_hook`.

### P2.7 — Custom Providers

Plugins may register custom LLM provider adapters by implementing the `$provider_adapter` contract (connect / send / health). Registered providers are available in the F5 router alongside built-in providers. Provider identity is validated at registration time.

### P2.8 — Governance Rule Hooks

Plugins may register custom governance rule evaluators for the `governance.evaluate` insertion point. Rule evaluators receive the classified request and return a `$rule_decision` (allow / warn / block). Built-in rules always run first; plugin rules run after and may only further restrict, not relax, built-in decisions.

### P2.1 — Plugin Registration

All plugins register via `plugin.registry.register(name, version, hooks)`. Registration validates the plugin manifest, checks for name conflicts, and logs the registration event to the audit trail. Plugins are loaded in the order declared in `ooke.toml`.

---

## 7. Storage Model

### SQLite (F6.1)

Primary persistent store. Schema managed by versioned migrations in `src/core/storage/migrations/`. All
queries use parameterised statements — no string concatenation.

> **Encryption at rest is not currently active.** A 32-byte key is generated and held in the OS keychain
> correctly, but the toolchain links plain SQLite, which silently ignores the encryption pragma and
> returns success — which the calling code maps to a successful result. The database, including the
> placeholder mapping table, is therefore **plaintext on disk**; rely on full-disk encryption. Tracked
> as X8, and recorded in [metrics-baseline.md](metrics-baseline.md).

### Vector Store (F6.3)

Embedding vectors for the semantic cache and memory palace. Backed by ooke's native vector store binding. Stored in `~/.loke/vector.db`. Used by the F4 semantic cache to detect near-duplicate prompts and by the AG3 memory palace for episodic recall.

### Ephemeral Store (F6.4)

In-memory key-value store for session state, rate-limit counters, and circuit-breaker state. Not persisted across restarts. Scoped per-session to prevent cross-session data leakage.

### Audit Trail (F6.2)

One row per AI call is specified, exportable as CSV or JSON.

> **No row is currently written.** `core.storage.audit::logevent` holds the only `INSERT` into
> `audit_log` in the tree and **has no callers**; the module's sole importer is the report engine, which
> reads. The browser route never opens an audit store (`packages/browser/extensions/core.tk:61` —
> `getauditstore()` returns `0`), and no CLI, proxy, broker or agent path calls `logevent` either. So the
> limits described below — no time basis, no chain, no policy decision — are downstream of a more basic
> one: the table is empty. The claim that the trail is "wired into every browser and CLI request path"
> does not hold. Tracked as **GA5** and **DA1**; recorded as E4 in [claims.md](claims.md).

**Specified per interaction:** event type, use case, model, provider, sensitivity, risk tier, token
counts in and out, cost, duration, correlation ID.

**Not captured:** the policy decision, detected-entity detail, which detection layer fired, the approval
or override outcome, and kill-switch state. Those five fields exist only on the `$decisiontrace`
structure in `core/governance/trace.tk`, which has no table and no insert — `complete()` writes a single
log line and discards the structure. Persisting it is story **GA5.5**.

> **Even once written, what this record evidences and what it does not.** The trail deliberately excludes prompt content
> and placeholder values. That is a defensible privacy choice and it is kept — but it has a consequence
> worth stating rather than leaving implicit: **the trail cannot evidence that the privacy control
> operated**, because it records nothing about what was detected, which layer detected it, or what the
> policy engine decided.
>
> Two further limits apply today. Timestamps are not written correctly — `created_at` receives the
> string literal `'now()'`, so every row carries the same seven characters and there is no orderable
> time basis (**GA5.1**). And the trail is not tamper-evident: the stored digest is a concatenation of
> two non-secret fields, `prev_hash` is stored but is not an input to it, so nothing chains, and no
> verifier exists (**GA5.2**, **GA5.3**).
>
> What the record therefore is: a **per-interaction usage and cost ledger**. An assessor distinguishes
> *design effectiveness* — the control is present and correctly specified at a point in time, which is
> established by inspecting the code and this document — from *operating effectiveness* — the control ran
> as specified throughout a period. This ledger is **not** evidence of operating effectiveness, and
> without a time basis there is no period for it to be evidence over. It must not be described as an
> audit trail that demonstrates the privacy control worked. GA5.1, GA5.2, GA5.3 and GA5.5 are what would
> change that.

---

## 8. Security Boundaries

- **All outbound data passes through the privacy filter.** No path through this codebase sends a prompt
  to an external provider without traversing F3. This is a **contributor invariant enforced by review**,
  not a property of the language or the host: nothing prevents a direct HTTP call being written, and
  loke ships a flag that disables the pipeline. It is also not a property of the *machine* — loke sees
  only traffic addressed to it. Six classes of bypass are enumerated and testable (AD1.6). And
  *traversing* F3 is not the same as F3 having masked anything: on the fallback path the detection stack
  can currently fail open and transmit unmodified text (NC1.9).
- **Structured PII is redacted from logs.** All log output passes through the auto-redaction filter
  (F1.3 / GA2.4), and debug mode is subject to the same rules as production. Its scope is the regex
  pattern set plus a sensitive-key list, so it removes emails, phone numbers, card numbers, API keys and
  authorisation values — it does **not** remove free-text PII such as person names, which no pattern
  matches. "No PII in logs" is the goal; what is enforced is pattern-based redaction.
- **Local-first.** Core functionality requires no network. Ollama, Presidio, and LLMLingua are optional; loke degrades gracefully when they are unavailable.
- **Kill switch (G1.6).** When active, outbound AI requests are blocked immediately and the user is
  shown an explanation. "Checked before every AI call" holds for calls routed through the governance
  gateway (`core/governance/gateway.tk`) and for moke's own check; it is not structurally enforced on
  every provider dispatch — the browser route does not check it at all (E4/A13 in
  [claims.md](claims.md)). Same class of gap as the first bullet: AD1.6.
- **OS keychain for secrets.** API keys and OAuth tokens are stored in the OS keychain (F1.5 / P5.2). They are never written to disk, never appear in logs, and are fetched per-request with expiry validation.
- **Localhost-only HTTP server.** The HTTP server (port 11430) binds to `127.0.0.1` by default. CORS is restricted to localhost origins. External binding requires explicit configuration and is logged as a warning.

---

## 9. Deployment Model

- **Single ooke native binary.** `ooke build` produces a self-contained binary for the target platform. No external runtime (Node.js, Python, JVM) is required on the user's machine.
- **Ollama REST for local models.** Ollama is called via its REST API. loke manages the Ollama process lifecycle but does not bundle Ollama — it must be installed separately.
- **Presidio as optional Python sidecar.** The Presidio integration adapter calls a locally-running Presidio server via REST. If Presidio is not running, the regex and NER layers remain — they cover fewer entity types at lower precision, not the same set. **loke does not start Presidio, and does not bundle it** — the user must run it. No auto-detection or subprocess launch exists.
- **LLMLingua as optional Python sidecar.** Same pattern as Presidio — local REST call, graceful degradation to TOON-only compression if unavailable.
- **No data leaves the device during local inference.** When routing to local models, all inference is
  on-device. Cloud routing is an explicit user opt-in with per-request confirmation available. On the
  primary path a schema profile and the user's intent still cross the boundary when a cloud model is
  selected; on the fallback path redacted text does. See [§4](#4-pipeline-data-flow), and
  [metrics-baseline.md](metrics-baseline.md) for the scoped version of the "keeping the data on the
  device" claim.
