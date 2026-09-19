# loke

[![CI](https://github.com/karwalski/loke/actions/workflows/ci.yml/badge.svg)](https://github.com/karwalski/loke/actions/workflows/ci.yml)

A locally-run intelligence layer that sits between users, their data, and external LLMs — reducing
what is disclosed to them, reducing what is spent on them, and keeping the data itself on the user's
device.

Each of those is meant as a measurable claim rather than a slogan. What they mean precisely, and what
has actually been measured, is in [docs/metrics-baseline.md](docs/metrics-baseline.md) — the only
place this project publishes figures from. Where a number has no measurement behind it, it is named
there and not restated.

## What is loke?

loke is an open-source desktop tool that sits between your tools and external language models. Traffic
you route through it is inspected, minimised and logged before it leaves the machine. It combines a
disclosure-minimising pipeline, intelligent routing, AI governance controls, lightweight agents,
persistent cross-session memory, and governance dashboards in a single local-first application.

**The primary path sends the shape of the data, not the data.** For analysis work, loke sends column
names, types and cardinality plus your question, receives back an executable specification, and runs
it locally against data that never leaves the device.

This data flow is **not novel, and loke does not claim it is.** It is how every text-to-SQL benchmark
has always worked, and it ships today in Vanna, WrenAI, Snowflake Cortex Analyst and Databricks Genie.
It is a published pattern. What those systems do not do is treat it as a *security control*: they have
no threat model, no artifact validation, no injection resistance and no audit obligation. loke's
contribution is the enforcement around the data flow, not the data flow.

Two things loke will not claim about it:

- **Not "low leakage".** A schema is itself worth attacking — published work reconstructs table names
  from a deployed system at F1 up to 0.99, and schemas encode business logic, regulatory scope and
  sometimes values in column names. The honest claim is **bounded and auditable** disclosure: what
  leaves is O(schema) rather than O(data), it is declared, and you can review the exact bytes.
- **Not "the model never receives data".** That is true at the byte level and not necessarily at the
  information level. A returned query is itself a channel: an adversary able to shape queries and
  observe results across several turns can extract values a piece at a time without ever being sent a
  row. loke treats bounding that channel as an open problem, tracked in the backlog, rather than as
  solved.

Redaction remains available as a labelled fallback for prose tasks. It is not presented as a
guarantee: peer-reviewed work establishes that models infer and re-identify obscured entities from
surrounding context, so removing names reduces disclosure without preventing identification. See
[docs/research/disclosure-measurement-findings.md](docs/research/disclosure-measurement-findings.md)
for the evidence base and for what loke must not claim.

```
PRIMARY PATH — no custody                 FALLBACK PATH — redact and send
                                          (labelled, logged, residual risk stated)
User Input + local data                   User Input
    |                                         |
    v                                         v
Schema profile                            Privacy Filter (regex + NER + Presidio)
(names, types, cardinality,                   |
 null-rate — no values)                       v
    |                                     Token Optimiser (TOON + LLMLingua)
    v                                         |
Router -> LLM Provider                        v
    |                                     Router -> LLM Provider
    v                                         |
Executable artifact                           v
    |                                     Response Restoration
    v                                     (placeholders -> original values)
Local execution against                       |
data that never left                          v
    |                                     User Output
    v
User Output
```

On the primary path no data row reaches the provider, so there is nothing to restore and nothing to
re-identify. On the fallback path the provider receives redacted text, which reduces disclosure
without preventing identification.


### Core Philosophy

1. **Local first.** Processing, filtering, anonymisation, and lightweight inference happen on-device before anything leaves the machine.
2. **Send less, get more.** On the primary path external models receive a schema profile and an intent, not the data. On the fallback path they receive compressed, redacted text, and the residual risk of that is stated rather than waved away.
3. **The user stays in control.** Every outbound prompt routed through loke is visible, auditable and
   interruptible. Disclosure minimisation is the default.

**What loke does not claim.** It is not an unbypassable chokepoint. Applications must be configured to
route through it, anything addressed elsewhere never reaches it, and loke ships a flag that disables
the pipeline outright. Every network enforcement point has documented bypass paths, and loke's are
enumerated and tested rather than denied. The defensible claim is that *when traffic is in path*,
enforcement is ordered, recorded and inspectable.

### Design Principles

- **The user is the authority.** loke advises; the user decides.
- **Feedback is a first-class feature.** Thumbs up/down on every interaction.
- **Do the right thing by default.** Anonymise, local-first, most restrictive regulation.
- **Warnings must be earned.** Only surface actionable, meaningful information.
- **Complexity is available, not imposed.** Simple by default, progressive disclosure for internals.
- **Speed is a feature.** Targets, not measurements: pipeline overhead under 1 second, intent classification under 10ms. Neither is currently benchmarked — see [docs/metrics-baseline.md](docs/metrics-baseline.md).
- **Privacy is not a feature — it's the foundation.** Privacy failures are severity-1 incidents.

See [docs/design-principles.md](docs/design-principles.md) for the full design principles document.

---

## Features

### Privacy & Anonymisation

Multi-layer PII detection, reversible placeholder mapping, guardian prompt injection, and
per-entity-type layer routing. Every code path in this repository that sends a prompt to an external
provider routes it through the filter first; that is a contributor invariant enforced by review, not a
property of the host.

> **Status of the multi-layer composition:** the consensus, layer-config, layer-health,
> entity-routing and per-layer-metrics modules are written but **not currently wired** into the
> pipeline orchestrator, which uses its own de-duplication. The four named consensus strategies are
> not yet implemented — the strategy argument is accepted and ignored. Tracked as AD1.7.

- **Regex detector** — 10 patterns (email, phone, credit card, TFN, SSN, IP, API key)
- **Local NER** — SLM-based entity recognition via Ollama
- **Presidio** — 180+ entity types via optional Python sidecar
- **Privacy Filter sidecar** — OpenAI Privacy Filter model (1.5B params)
- **OS keychain** — API keys stored in macOS Keychain, never in plaintext
- **Log redaction** — all log output auto-redacted for PII before writing
- **Database encryption** — *not currently active.* The encryption key is generated and stored in the
  OS keychain correctly, but the toolchain links plain SQLite, which silently ignores the
  encryption pragma and reports success. The database is therefore **plaintext on disk**; rely on
  full-disk encryption. loke's own compliance check already reports this. Tracked as X8.

### Token Optimisation

Mechanisms implemented; **no combined figure is published, because none has been measured.**
Previously-quoted reduction, compression and cache-hit percentages had no benchmark behind them and
are withdrawn. They will return only as measurements with their tokenizer, their workload and their N,
recorded in [docs/metrics-baseline.md](docs/metrics-baseline.md).

- **TOON format** — a token-efficient serialisation for structured data. The only saving currently
  computed in code is a *character-length* ratio, not a token count
- **LLMLingua compression** — client implemented; requires a sidecar service this repository does not
  bundle, so it is inert out of the box
- **Semantic caching** — real vector-similarity lookup at a 0.92 threshold. Hit rate depends entirely
  on the workload and has never been measured here
- **Local routing** — a task handled on-device costs nothing in API tokens

The methodology for measuring all of this is already written, in
[docs/research/toon-benchmark-methodology.md](docs/research/toon-benchmark-methodology.md). It has not
yet been executed. Tracked as VM1.

### Intelligent Routing

Intent classification driving sensitivity- and latency-aware model selection, with three inference
tiers: Interactive, Considered, Background.

> The classifier is a keyword and pattern cascade, not an embedding model — deliberately cheap, and
> described that way rather than as semantic. No latency measurement is published. The four named
> selection strategies (cheapest-adequate, fastest, best-quality, local-first) are **not
> implemented**; one fixed selection path exists. Tracked as X8 and CV-series stories.

### Governance & Compliance

Kill switch (global/per-provider/per-agent), an append-only interaction ledger, risk classification,
graduated warnings (info/advisory/caution/block), regulatory policy presets (GDPR, HIPAA, AU Privacy
Act, CCPA), and report generation.

> **The audit trail is not currently tamper-evident.** The stored digest is a concatenation of two
> non-secret fields rather than a cryptographic hash, it does not incorporate the previous record, and
> no verification routine exists. Timestamps are also not currently written correctly. What the ledger
> records is a per-interaction usage and cost account — not evidence that a control operated over a
> period. Tracked as GA5.
>
> The presets are policy definitions loke ships. They do not make a deployment compliant with any
> regulation, and loke does not claim they do.

### Agents & Memory

YAML/TOML agent definitions, capability-scoped execution with path, tool and cost limits, and
overnight batch processing. Memory palace with cross-session search, AAAK shorthand compression, a
knowledge graph, and a memory MCP server.

> Scheduling currently recognises three fixed schedules rather than general cron expressions, and
> webhook and MCP event triggers are not fired by the scheduler. Memory search is keyword matching
> over an index table, not embedding-based retrieval — it is not described as semantic. No retrieval
> latency or compression ratio is published, because neither has been measured. Agent execution is
> capability-scoped, not process-isolated.

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
