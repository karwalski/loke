# loke

[![CI](https://github.com/karwalski/loke/actions/workflows/ci.yml/badge.svg)](https://github.com/karwalski/loke/actions/workflows/ci.yml)

A locally-run intelligence layer that sits between users, their data, and external LLMs — minimising token spend, maximising privacy, and keeping sensitive data where it belongs: on the user's device.

## What is loke?

loke is an open-source desktop tool that intercepts, anonymises, optimises, and routes all LLM traffic before it leaves your machine. It combines a privacy pipeline, intelligent routing, AI governance controls, lightweight agents, persistent cross-session memory, and governance dashboards in a single local-first application.

```
User Input
    ↓
Privacy Filter (regex + NER + Presidio)
    ↓
Token Optimiser (TOON + LLMLingua)
    ↓
Router (sensitivity × cost × latency × capability)
    ↓
LLM Provider (local Ollama or cloud API)
    ↓
Response Restoration (placeholders → original values)
    ↓
User Output
```

### Core Philosophy

1. **Local first.** Processing, filtering, anonymisation, and lightweight inference happen on-device before anything leaves the machine.
2. **Send less, get more.** External LLMs receive only what they need — compressed, anonymised, and structured — never raw documents or datasets.
3. **The user stays in control.** Every outbound prompt is visible, auditable, and interruptible. Privacy is the default, not an opt-in.

### Design Principles

- **The user is the authority.** loke advises; the user decides.
- **Feedback is a first-class feature.** Thumbs up/down on every interaction.
- **Do the right thing by default.** Anonymise, local-first, most restrictive regulation.
- **Warnings must be earned.** Only surface actionable, meaningful information.
- **Complexity is available, not imposed.** Simple by default, progressive disclosure for internals.
- **Speed is a feature.** Pipeline overhead < 1 second. Intent classification < 10ms.
- **Privacy is not a feature — it's the foundation.** Privacy failures are severity-1 incidents.

See [docs/design-principles.md](docs/design-principles.md) for the full design principles document.

---

## Features

### Privacy & Anonymisation

Multi-layer PII detection with 4 consensus strategies, reversible placeholder mapping, guardian prompt injection, and per-entity-type layer routing. All outbound data passes through the privacy filter — no exceptions.

- **Regex detector** — 10 patterns (email, phone, credit card, TFN, SSN, IP, API key)
- **Local NER** — SLM-based entity recognition via Ollama
- **Presidio** — 180+ entity types via optional Python sidecar
- **Privacy Filter sidecar** — OpenAI Privacy Filter model (1.5B params)
- **OS keychain** — API keys stored in macOS Keychain, never in plaintext
- **Log redaction** — all log output auto-redacted for PII before writing
- **SQLCipher** — database encrypted at rest with keychain-derived key

### Token Optimisation

Combined target: **60–80% token reduction**.

- **TOON format** — 30–60% savings on structured data
- **LLMLingua compression** — up to 20x on natural language prompts
- **Semantic caching** — up to 73% on cache hits (vector-store backed)
- **Local routing** — 100% savings when tasks are handled on-device

### Intelligent Routing

Semantic intent classifier (< 10ms) with sensitivity × cost × latency × capability model selection. Strategies: cheapest-adequate, fastest, best-quality, local-first. Three inference tiers: Interactive, Considered, Background.

### Governance & Compliance

Kill switch (global/per-provider/per-agent), tamper-proof audit trail with hash chain, risk classification, graduated warnings (info/advisory/caution/block), regulatory presets (GDPR, HIPAA, AU Privacy Act), compliance reporting.

### Agents & Memory

YAML/TOML agent definitions with cron/webhook/MCP triggers, sandboxed execution, overnight batch processing. Memory palace with semantic search (< 500ms for 100K entries), AAAK shorthand (5–30x compression), knowledge graph, memory MCP server.

### MCP Framework

toke MCP server + broker with per-server permissions, privacy pipeline on all tool call data, audit trail on every invocation.

> **Full feature details:** [docs/features-loke.md](docs/features-loke.md)

---

## moke — Demo Application

moke is a data analysis demo that exercises loke's privacy pipeline, governance controls, and LLM integration end-to-end. It serves as a reference implementation and the primary demo for loke's capabilities.

### What moke demonstrates

| Feature | How |
|---------|-----|
| Privacy pipeline | Confirm modal shows raw vs anonymised data side-by-side with PII entity chips |
| Sensitivity classification | Colour-coded badges (PUBLIC/CONFIDENTIAL/RESTRICTED) with "why?" tooltips |
| Pipeline transparency | Collapsible console logging each stage with timestamps |
| Kill switch | Governance page toggle blocks all LLM traffic with pulsing banner |
| Feedback | Thumbs up/down on every response with optional comment on thumbs-down |
| Cost tracking | Pre-send token/cost estimation, session stats, savings vs cloud |
| Graduated warnings | 4-level system: info → advisory → caution → block |
| Client-side ML | K-Means, Z-Score, IQR, Pearson correlation — zero data egress |

### Demo datasets

9 Australian-themed datasets with embedded analysis patterns:

- **IT Operations** — 200 servers, 10K metrics, 500 incidents, 300 changes, 2K app performance, 48 asset/cost records
- **Government** — 500 Medicare claims, 200 water quality readings, ABS employment
- **Customer Intelligence** — 1,000 customers with whale/at-risk/growth/dormant clusters

### Pages

Analysis Chat (26-detector type engine) · Dashboard (3-phase LLM + local compute + Chart.js) · Insight Lab (client-side ML) · Governance · Upload · API Connections · Memory Palace · MCP Tools · Settings · Presentation Mode

> **Full feature details:** [docs/features-moke.md](docs/features-moke.md)

---

## Operating Modes

### Browser Mode

ooke native binary with web view. Tab management, chat interface, dashboard persistence. All data passes through the local intelligence layer before external transmission.

### Terminal Mode (CLI)

```
$ loke claude-code "refactor this module"
    ├── 1. Local SLM summarises codebase context
    ├── 2. PII/proprietary code patterns anonymised
    ├── 3. Prompt compressed via LLMLingua + TOON
    ├── 4. Router selects: local model OR cloud LLM
    ├── 5. If cloud: anonymised compressed prompt sent
    ├── 6. Response received, placeholders restored
    └── 7. Result displayed with full audit log
```

### Proxy Mode

HTTP proxy on port 11431 that intercepts outbound requests to cloud LLM APIs and transparently routes through the full privacy pipeline.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | [toke](https://tokelang.dev) — compiles to native binary |
| Framework | [ooke](https://github.com/karwalski/ooke) — single binary, no runtime dependencies |
| Local models | Ollama (REST), MLX (Apple Silicon), native inference |
| Storage | SQLite + SQLCipher, vector store (ooke native bindings) |
| Privacy | Regex (toke), SLM NER (Ollama), Presidio (Python sidecar) |
| Compression | TOON (toke), LLMLingua (Python sidecar) |
| MCP | toke implementation of MCP protocol |

**Platform:** macOS (primary, Apple Silicon optimised) · Windows (planned)

---

## Project Structure

```
packages/
├── core/              # Shared core engine (privacy, router, optimiser, cache,
│                      #   storage, audit, governance, agents, memory)
├── browser/           # ooke native binary with web view (browser mode)
├── cli/               # Terminal mode and coding LLM proxy
├── moke/              # Data analysis demo application
├── mcp-toke/          # toke MCP server
├── mcp-broker/        # MCP broker for intermediary routing
└── shared/            # Shared types, utilities, and configuration
tests/
├── unit/              # Unit tests by subsystem (120 test files)
├── integration/       # End-to-end pipeline tests
docs/                  # Architecture, design principles, epics, features
scripts/               # Build and test scripts
```

## Quick Start

```bash
# Build loke
cd loke && ./scripts/build_loke.sh

# Start loke (port 11430)
cd packages/browser && ./build/loke . &

# Start moke (port 11432)
cd packages/moke && ooke-toke serve . &

# Run tests
./scripts/run_tests.sh
```

## Key Documents

- [Design Principles](docs/design-principles.md) — Human-centred design philosophy
- [Architecture](docs/architecture.md) — Layered architecture, runtime modes, pipeline data flow
- [loke Features](docs/features-loke.md) — Complete loke feature inventory
- [moke Features](docs/features-moke.md) — Complete moke feature inventory
- [Epics & Stories](docs/epics-and-stories.md) — Full backlog with completion status
- [Privacy Filters](docs/privacy-filters.md) — Multi-layer privacy filter architecture
- [Test Coverage](docs/test-coverage.md) — Module coverage map (120 test files, 35% coverage)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and contribution guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

**Note:** Exo (GPL-3.0), used for distributed inference, runs as a separate process communicating via network API to maintain the license boundary. It is never linked into loke.
