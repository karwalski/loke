# loke Architecture

**Version:** 0.3.0
**Last updated:** 2026-04-22
**Status:** Living document

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

loke is a local-first privacy proxy implemented in toke on ooke. It sits between users and external large language models, intercepting outbound prompts, anonymising personally identifiable information with reversible placeholders, compressing tokens for cost reduction, and routing requests to the best available model. Responses are de-anonymised before being returned to the user. Everything runs on the user's device. No data leaves the machine without passing through the privacy filter. No cloud service is required for core functionality.

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

An HTTP proxy listener on **port 11431** intercepts outbound requests destined for cloud LLM APIs (Anthropic, OpenAI, Google, etc.). Traffic is transparently passed through the full privacy pipeline before forwarding. Used by coding tools (Claude Code, Codex, Gemini CLI) configured to point at `http://127.0.0.1:11431`.

---

## 4. Pipeline Data Flow

All user input — whether submitted via the browser UI, CLI, or intercepted by the proxy — travels through the same pipeline before leaving the device.

```
User Input
    │
    ▼
┌───────────────────────┐
│  Privacy Filter (F3)  │  Regex + NLP NER + SLM NER + Presidio
│  PII → placeholders   │  Reversible mapping stored in SQLCipher
└───────────┬───────────┘
            │ anonymised prompt
            ▼
┌───────────────────────┐
│ Token Optimiser (F4)  │  TOON serialisation + LLMLingua compression
│  60–80% token savings │
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

---

## 5. Package Structure

```
src/
├── core/
│   ├── privacy/          # F3 — Privacy pipeline (regex, NLP, SLM NER, Presidio, orchestrator)
│   ├── router/           # F5 — LLM router and model registry
│   ├── optimiser/        # F4 — Token optimisation (TOON, LLMLingua, profiler)
│   ├── cache/            # Semantic cache
│   ├── storage/          # F6 — SQLite + SQLCipher, migrations
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

### SQLite + SQLCipher (F6.1)

Primary persistent store. All tables encrypted at rest via SQLCipher using a key derived from the OS keychain secret. Schema managed by versioned migrations in `src/core/storage/migrations/`. All queries use parameterised statements — no string concatenation.

### Vector Store (F6.3)

Embedding vectors for the semantic cache and memory palace. Backed by ooke's native vector store binding. Stored in `~/.loke/vector.db`. Used by the F4 semantic cache to detect near-duplicate prompts and by the AG3 memory palace for episodic recall.

### Ephemeral Store (F6.4)

In-memory key-value store for session state, rate-limit counters, and circuit-breaker state. Not persisted across restarts. Scoped per-session to prevent cross-session data leakage.

### Audit Trail (F6.2)

Append-only log of all AI calls: timestamp, correlation ID, provider, model, token counts, cost, governance decision, and pipeline stage timings. Prompt content and PII placeholders are never written to the audit trail. Exportable as CSV or JSON for compliance reporting.

---

## 8. Security Boundaries

- **All outbound data passes through the privacy filter.** No path through the codebase sends a prompt to an external provider without traversing F3. This invariant is enforced by the router — direct provider calls are not possible.
- **No PII in logs.** All log output passes through the auto-redaction filter configured in F1.3. Debug mode is subject to the same redaction rules as production logging.
- **Local-first.** Core functionality requires no network. Ollama, Presidio, and LLMLingua are optional; loke degrades gracefully when they are unavailable.
- **Kill switch (G1.6).** `kill_switch.is_global_active()` is checked before every AI call. When active, all outbound AI requests are blocked immediately and the user is shown an explanation.
- **OS keychain for secrets.** API keys and OAuth tokens are stored in the OS keychain (F1.5 / P5.2). They are never written to disk, never appear in logs, and are fetched per-request with expiry validation.
- **Localhost-only HTTP server.** The HTTP server (port 11430) binds to `127.0.0.1` by default. CORS is restricted to localhost origins. External binding requires explicit configuration and is logged as a warning.

---

## 9. Deployment Model

- **Single ooke native binary.** `ooke build` produces a self-contained binary for the target platform. No external runtime (Node.js, Python, JVM) is required on the user's machine.
- **Ollama REST for local models.** Ollama is called via its REST API. loke manages the Ollama process lifecycle but does not bundle Ollama — it must be installed separately.
- **Presidio as optional Python sidecar.** The Presidio integration adapter calls a locally-running Presidio server via REST. If Presidio is not running, the SLM NER layer covers the same entity types at lower precision. loke starts Presidio automatically if a compatible Python environment is detected.
- **LLMLingua as optional Python sidecar.** Same pattern as Presidio — local REST call, graceful degradation to TOON-only compression if unavailable.
- **No data leaves the device during inference.** When routing to local models, all inference is on-device. Cloud routing is an explicit user opt-in with per-request confirmation available.
