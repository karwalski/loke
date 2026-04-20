# loke

A locally-run intelligence layer that sits between users, their data, and external LLMs — minimising token spend, maximising privacy, and keeping sensitive data where it belongs: on the user's device.

## What is loke?

loke is an open-source desktop tool that intercepts, anonymises, optimises, and routes all LLM traffic before it leaves your machine. It works as a personal privacy proxy, local intelligence layer, and unified workspace — whether you're browsing the web, writing code, or processing data.

loke helps people stay between the lines — regulatory, organisational, cost, and ethical — so they can focus on the work that matters to them. It combines a privacy pipeline, intelligent routing, AI governance controls, lightweight agents, persistent cross-session memory, and governance dashboards in a single local-first application.

### Core Philosophy

1. **Local first.** Processing, filtering, anonymisation, and lightweight inference happen on-device before anything leaves the machine.
2. **Send less, get more.** External LLMs receive only what they need — compressed, anonymised, and structured — never raw documents or datasets.
3. **The user stays in control.** Every outbound prompt is visible, auditable, and interruptible. Privacy is the default, not an opt-in.

### Design Principles

- **The user is the authority.** loke advises; the user decides. Every warning includes what's happening, why it matters, and what the user can do about it.
- **Feedback is a first-class feature.** Thumbs up/down on every interaction. Feedback flows directly into the development pipeline.
- **Do the right thing by default.** Anonymise by default. Local-first by default. Most restrictive regulation by default. Cautious on cost by default.
- **Warnings must be earned.** Every warning costs trust and attention. Only surface actionable, meaningful information as interruptions.
- **Complexity is available, not imposed.** Simple by default, with progressive disclosure for those who want to understand the internals.
- **Speed is a feature.** Pipeline overhead < 1 second. Intent classification < 10ms. If it's slow, users will bypass it.
- **Privacy is not a feature — it's the foundation.** Privacy failures are severity-1 incidents. No trade-offs against convenience.

See [docs/design-principles.md](docs/design-principles.md) for the full design principles document.

## Operating Modes

### Browser Mode (Chromium Workspace)

A Chromium-based desktop application where users can browse, interact with web apps, process data, and prompt LLMs from a single location. Web page content is sandboxed — data read from within a webpage never goes directly to an LLM. All data passes through the local intelligence layer first, where sensitive information is identified, anonymised, or blocked before any external transmission.

### Terminal Mode (CLI / Coding Interface)

A command-line interface that channels coding LLM interactions through loke's local processing pipeline. loke sits between the user and coding-focused LLMs (Claude Code, OpenAI Codex CLI, Gemini CLI, and others), providing the same privacy, optimisation, and routing benefits to developer workflows.

```
# Without loke — direct to cloud
$ claude-code "refactor this module"

# With loke — processed locally first
$ loke claude-code "refactor this module"
    ├── 1. Local SLM summarises codebase context
    ├── 2. PII/proprietary code patterns anonymised
    ├── 3. Prompt compressed via LLMLingua + TOON
    ├── 4. Router selects: local model OR cloud LLM
    ├── 5. If cloud: anonymised compressed prompt sent
    ├── 6. Response received, placeholders restored
    └── 7. Result displayed with full audit log
```

## Key Components

| Component | Purpose |
|-----------|---------|
| **Local Intelligence Layer** | On-device SLM for summarisation, NER, intent classification, and simple tasks |
| **Privacy & Anonymisation** | Multi-layer PII detection (regex, NLP, SLM NER, Presidio) with reversible anonymisation |
| **Token Optimisation Pipeline** | TOON format + LLMLingua compression + semantic caching + toke encoding |
| **LLM Router** | Routes requests by sensitivity, complexity, cost, speed, and user preference |
| **AI Governance Gateway** | Single mandatory entry point for all AI interactions — risk classification, policy enforcement, accountability, and kill switches |
| **Agent Framework** | Lightweight scheduled/triggered agents with declared permissions, sandbox execution, and full governance coverage |
| **Memory Palace** | Persistent cross-session memory in a structured palace (wings, halls, rooms); semantic search; AAAK-compressed context loading |
| **MCP Integration** | First-class MCP host and client — includes toke MCP server, memory MCP server, and MCP broker for tool use across local, companion, and cloud boundaries |
| **Policy & Compliance Engine** | Enterprise policy enforcement, audit trails, regulatory compliance reporting, and governance dashboards |
| **Companion Device Support** | Offload heavy inference to nearby high-power devices over encrypted connections |
| **Feedback System** | Thumbs up/down on every interaction; feedback-driven learning loops; routes directly into the development pipeline |

## Token Savings

loke layers multiple optimisation strategies for a combined target of **60-80% token reduction**:

- **TOON format** — 30-60% savings on structured data
- **LLMLingua compression** — up to 20x on natural language prompts
- **Semantic caching** — up to 73% on cache hits
- **Template reuse** — 80-90% on repeated tasks
- **Local routing** — 100% savings when tasks are handled entirely on-device

## Technology Stack

- **Language:** toke — compiles to native binary via ooke
- **Framework:** [ooke](https://github.com/karwalski/ooke) — lightweight CMS and web application framework; single native binary, no external runtime dependencies
- **App Shell:** ooke native binary with web view (browser mode)
- **Local Models:** Ollama (REST, language-agnostic), MLX (Apple Silicon), native inference via ooke bindings
- **Storage:** SQLite + SQLCipher via ooke native bindings, vector store via ooke native bindings
- **Privacy:** Regex PII detector (toke), SLM NER (local models via Ollama), Microsoft Presidio (Python sidecar, REST)
- **Compression:** TOON (toke implementation), LLMLingua (Python sidecar, REST)
- **Routing:** RouteLLM signal integration (REST), semantic intent classifier (local model)
- **MCP:** toke implementation of MCP protocol (language-agnostic specification)

> **Note:** Foundation layer development is on hold pending ooke Phase 1 completion. See `docs/epics-and-stories.md` for detail.

## Platform Support

- **macOS** — primary platform (Apple Silicon optimised)
- **Windows** — planned

## Project Structure

```
packages/
├── core/              # Shared core engine (privacy, router, optimizer, cache, storage, audit,
│                      #   governance gateway, agent framework, memory palace)
├── browser/           # Electron/Chromium workspace mode
├── cli/               # Terminal mode and coding LLM proxy
├── mcp-toke/          # toke MCP server (compress, decompress, template, analyse)
├── mcp-broker/        # MCP broker for intermediary routing
└── shared/            # Shared types, utilities, and configuration
tests/
├── unit/
├── integration/
└── e2e/
docs/                  # Architecture docs, ADRs, design principles, epics, specifications
scripts/               # Build, release, and development scripts
```

## Relationship to toke and ooke

loke is part of the [toke ecosystem](https://tokelang.dev). toke is a programming language and compressed communication format designed for minimal token consumption when communicating with LLMs. loke is **written in toke** and built on **ooke** — a web application framework written in toke that compiles to a single native binary with no external runtime dependencies ("toke on ooke — build light, ship fast").

loke uses TOON and LLMLingua for token optimisation and provides a toke MCP server accessible to any connected LLM client.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, coding standards, and contribution guidelines.

## MVP Philosophy

The MVP exists to learn, not to ship a finished product. Every design decision is a hypothesis tested with real users. No feature is sacred — everything is revisable. See [docs/design-principles.md](docs/design-principles.md) for the full approach.

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

**Note:** Exo (GPL-3.0), used for distributed inference, runs as a separate process communicating via network API to maintain the license boundary. It is never linked into loke.
