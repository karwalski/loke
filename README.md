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

**The intended primary path sends the shape of the data, not the data.** For analysis work, loke is
designed to send column names, types and cardinality plus your question, receive back an executable
specification, and run it locally against data that never leaves the device.

> **This path is specified, not shipped.** Epic NC1 has not been started. Today the schema profile
> builders embed real sample values, the local execution engine has no production caller, and the one
> code path that does send only column names never fires because of a payload contract mismatch. What
> runs today is the redaction fallback below. Do not read the next paragraphs as a description of
> current behaviour.

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

Redaction is what runs today, and it is not presented as a guarantee: peer-reviewed work establishes
that models infer and re-identify obscured entities from surrounding context, so removing names
reduces disclosure without preventing identification. See
[docs/research/disclosure-measurement-findings.md](docs/research/disclosure-measurement-findings.md)
for the evidence base and for what loke must not claim.

> **The filter currently fails open, and this is the most serious defect in the project.** In
> `packages/browser/pages/api/pipeline.tk`, if the detection sidecar does not answer, the fallback
> branch increments a counter from five substring checks and **never reassigns the anonymised text** —
> so the original, unmodified prompt is sent to the provider. A filter that fails open is worse than
> no filter, because the user believes one ran. Tracked as NC1.9.

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
route through it, and anything addressed elsewhere never reaches it — there is no interception in the
codebase: no certificate authority, no proxy auto-configuration, no packet filtering. Six classes of
bypass are enumerated and independently testable in
[docs/specifications/enforcement-bypass-corpus.md](docs/specifications/enforcement-bypass-corpus.md);
two of them cannot be closed by any network control. The defensible claim is that *when traffic is in
path*, enforcement is ordered, recorded and inspectable — and that claim is weakened today by the
fail-open defect above.

loke's help text also advertises a privacy-off mode. No argument parsing for it exists, so it is not
currently a working bypass — but a help string offering something the code does not do is its own
defect.

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

Multi-layer PII detection, reversible placeholder mapping and guardian prompt injection. Routing a
prompt through the filter before it leaves is a contributor invariant enforced by review, not a
property of the host.

> **That invariant does not currently hold on the browser path.** The route the browser serves for
> `/api/pipeline` does not invoke the core privacy pipeline at all: it calls the privacy-filter sidecar
> on port 11435 directly and, when the sidecar does not answer, falls through to five literal
> column-name checks that count entities **without altering the text**, then forwards that unaltered
> text to the provider while still reporting an entity count and a sensitivity label. There is no
> restore step, kill-switch check, audit write, optimiser, cache or policy evaluation on that route. The
> CLI proxy, the MCP broker, the MCP server and the agent executor do use the core pipeline. Failing
> closed is tracked as NC1.9, the bypass corpus that would catch it in CI as AD1.6, and epic GA1 needs
> reopening. See [docs/claims.md](docs/claims.md) A13.

> **Status of the multi-layer composition:** the consensus, layer-config, layer-health,
> entity-routing, filter-registry, org-policy, evaluation, per-layer-metrics and sidecar-client modules
> are written but **not currently wired** into the pipeline orchestrator, which uses its own
> de-duplication. Ten Epic F3b modules have zero importers. The four named consensus strategies are not
> implemented — the strategy argument is accepted and ignored — and no entity-type routing
> configuration is read. Tracked as AD1.7.

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
> implemented** — they score zero matches anywhere in the tree; one fixed selection path exists. Story
> F5.3 is marked Done in the backlog and should be reopened. The RouteLLM cost-signal client is also
> unwired: it has zero importers, and the cost and quality figures once quoted for it were a
> third-party result repeated without citation and are withdrawn. See
> [docs/claims.md](docs/claims.md) D1–D6.

### Governance & Compliance

Kill switch (global/per-provider/per-agent), an append-only interaction ledger, risk classification,
graduated warnings (info/advisory/caution/block), regulatory policy presets (GDPR, HIPAA, AU Privacy
Act, CCPA), and report generation.

> **The interaction ledger is not currently written.** The one function that inserts into `audit_log`
> has no callers anywhere in the tree, the browser route never opens an audit store, and the table's
> only reader is the report engine. So the ledger is empty, and everything downstream of it — report
> generation, the compliance checks, the governance scorecard — reads nothing. The report engine would
> fail regardless: its queries select two columns the table does not have. The compliance checks return
> a hardcoded `PASS` on the privacy and audit controls without querying anything, including asserting
> that the audit trail is complete. Tracked as GA5 and DA1; see [docs/claims.md](docs/claims.md) E4–E9.

> **And once written it would not be tamper-evident.** The stored digest is a concatenation of two
> non-secret fields rather than a cryptographic hash, it does not incorporate the previous record, and
> no verification routine exists. Timestamps are not written correctly either — the insert stores the
> literal text `now()`, so there is no time basis and therefore no period to evidence. What the ledger
> is designed to record is a per-interaction usage and cost account — not evidence that a control
> operated over a period. Tracked as GA5.
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

toke MCP server + broker with per-server permissions and the privacy pipeline on all tool call data.

> **There is no audit trail on MCP invocations.** No file in the broker or the MCP server imports any
> audit module, so nothing is recorded — and per the Governance note above, there would be nothing to
> record into. The permissions and privacy claims do hold: the broker enforces its tool allowlist,
> anonymises outbound tool arguments and restores inbound responses. Note the asymmetry — an outbound
> privacy failure fails closed, an inbound restore failure fails open with a warning. Tracked as GA5 and
> DA1; see [docs/claims.md](docs/claims.md) I1–I3.

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
| Cost tracking | Pre-send token/cost estimation, session stats, estimated savings vs cloud |
| Graduated warnings | 4-level system: info → advisory → caution → block |
| Client-side ML | K-Means, Z-Score, IQR, Pearson correlation — zero data egress |

> Two rows need qualifying. **Privacy pipeline** demonstrates the privacy-filter sidecar rather than
> loke's core pipeline, and it fails open — with the sidecar down, the confirmation modal can report
> anonymisation that did not happen (see the Privacy note above, NC1.9). **Cost tracking** is real
> arithmetic over per-session estimates computed from a character-derived token count against a modelled
> cloud price; it is not a measured saving and no figure from it is publishable — see
> [docs/metrics-baseline.md](docs/metrics-baseline.md). The governance dashboard's risk breakdown,
> request log and privacy score are likewise scoped to the current browser session and reset on reload.

### Demo datasets

15 Australian-themed datasets with embedded analysis patterns:

- **IT Operations (6)** — 200 servers, 10K metrics, 500 incidents, 300 changes, 2K app performance, 48 asset/cost records
- **Government & public sector (6)** — 500 Medicare claims, 200 water quality readings, ABS employment, NSW public schools, Opal card journeys, property transactions
- **Customer intelligence (3)** — 1,000 customers with whale/at-risk/growth/dormant clusters, plus Wattle & Co users and orders

### Pages

Analysis Chat (26-detector type engine) · Dashboard (3-phase LLM + local compute + Chart.js) · Insight Lab (client-side ML) · Governance · Upload · API Connections · Memory Palace · MCP Tools · Settings · Presentation Mode

> **Full feature details:** [docs/features-moke.md](docs/features-moke.md)

---

## Operating Modes

### Browser Mode

ooke native binary with web view. Tab management, chat interface, dashboard persistence. All data passes through the local intelligence layer before external transmission.

### Terminal Mode (CLI)

```
$ loke claude-code "refactor this module"      # intended flow
    ├── 1. Local SLM summarises codebase context
    ├── 2. PII/proprietary code patterns anonymised
    ├── 3. Prompt compressed via LLMLingua + TOON
    ├── 4. Router selects: local model OR cloud LLM
    ├── 5. If cloud: anonymised compressed prompt sent
    ├── 6. Response received, placeholders restored
    └── 7. Result displayed with full audit log
```

> **That is the intended flow, not what the CLI does today.** `loke pipeline` prints those stage names
> with every one labelled "pending" and executes none of them. `loke ask` prints "Pipeline not yet
> connected — use browser mode for full pipeline", even though a fully wired implementation exists in
> the tree that nothing imports. `loke queue list`, `queue cancel`, `memory search`, `agents list` and
> `overnight status` return fixed strings; two of them read as legitimate empty results. Only
> `loke doctor` and `loke proxy` do real work — the proxy is wired to the core pipeline. See
> [docs/claims.md](docs/claims.md) K2–K5.

### Proxy Mode

HTTP proxy on port 11431 that handles outbound requests to cloud LLM APIs and routes them through the
full privacy pipeline. It is not a transparent interceptor: tools must be configured to point at
`http://127.0.0.1:11431`, and anything addressed elsewhere never reaches it.

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Language | [toke](https://tokelang.dev) — compiles to native binary |
| Framework | [ooke](https://github.com/karwalski/ooke) — single binary, no runtime dependencies |
| Local models | Ollama (REST), MLX (Apple Silicon — see below), native inference |
| Storage | SQLite (encryption inert — see above), vector store (ooke native bindings) |
| Privacy | Regex (toke), SLM NER (Ollama), Presidio (Python sidecar) |
| Compression | TOON (toke), LLMLingua (Python sidecar) |
| MCP | toke implementation of MCP protocol |

**Platform:** macOS (primary) · Windows (planned)

> **No Apple Silicon claim in this table has been executed.** Epic F2 — the MLX backend, native
> in-process inference, the tiered inference engine, hardware-aware recommendations and disk-streaming
> offload — is marked Done in the backlog and has **never run on target hardware**: there is no Apple
> Silicon test machine. The MLX module also has zero importers, and its `generate()` shadows its own
> result binding inside the loop, so it would return an empty string if it were called. Read "Apple
> Silicon optimised" as a design intent. Containerising the harness so figures become reproducible is
> VM1.4; see [docs/claims.md](docs/claims.md) J1–J5.

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
├── unit/              # Unit tests by subsystem (86 test files; see coverage caveat)
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
- [Claims Register](docs/claims.md) — Every externally-visible claim mapped to code and proof
- [Metrics Baseline](docs/metrics-baseline.md) — The only source of published figures
- [Test Coverage](docs/test-coverage.md) — Module coverage map (86 test files; 35.5% have a test file, about 5% are actually exercised)

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and contribution guidelines.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

**Note:** Exo (GPL-3.0), used for distributed inference, runs as a separate process communicating via network API to maintain the license boundary. It is never linked into loke.
