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

### Browser Mode (Desktop Workspace)

An ooke native binary with web view where users can browse, interact with web apps, process data, and prompt LLMs from a single location. Web page content is sandboxed — data read from within a webpage never goes directly to an LLM. All data passes through the local intelligence layer first, where sensitive information is identified, anonymised, or blocked before any external transmission.

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

## What's Built

The core engine, platform layer, and application modes are implemented. The table below shows what exists today.

### Foundation (Core Engine)

| Component | Status | Description |
|-----------|--------|-------------|
| **Privacy & Anonymisation Pipeline** | Done | Multi-layer PII detection (regex, NLP, SLM NER, Presidio), reversible placeholder mapping with SQLCipher, guardian system prompt injection, privacy pipeline orchestrator with dry-run and visual diff |
| **Token Optimisation** | Done | TOON serialiser/deserialiser (30-60% savings), LLMLingua compression (5-20x), semantic caching (73% on cache hits), token budget manager with daily/weekly/monthly limits |
| **LLM Router** | Done | Semantic intent classifier (<10ms), sensitivity scorer, model selection engine (cheapest-adequate/fastest/best-quality/local-first), RouteLLM integration, latency tolerance routing, model size escalation with user consent |
| **Tiered Inference Engine** | Done | Three tiers: Interactive (25-55 tok/s), Considered (5-15 tok/s), Background (0.5-5 tok/s); hardware-aware model recommendations; disk-streaming inference for extreme offload; overnight batch processing |
| **Local Model Integration** | Done | Ollama service manager, MLX backend for Apple Silicon, native inference via ooke bindings, model capability registry, background inference queue |
| **Storage & Audit** | Done | SQLite + SQLCipher with WAL mode, append-only audit trail with hash chain, vector store, secure ephemeral storage, backup/restore, sync queue, namespaced settings |
| **MCP Framework** | Done | MCP client and server in toke, MCP broker for intermediary routing with per-server permissions, toke MCP server (compress/decompress/template/analyse), local MCP server discovery via mDNS |
| **Companion Device Support** | Done | mDNS discovery and pairing, TLS 1.3 mutual auth secure channels, remote model execution, Exo distributed inference (GPL boundary maintained) |
| **Model Evaluation** | Done | Local benchmarking suite, A/B comparison testing, "Could this run locally?" advisor, workload-specific scoring |

### Accountable AI Systems

| Component | Status | Description |
|-----------|--------|-------------|
| **AI Governance Gateway** | Done | Single mandatory entry point for all AI interactions; risk classification (Low/Medium/High); policy enforcement; kill switches (global/per-provider/per-use-case/per-agent); accountability and ownership registry |
| **Transparency & Explainability** | Done | Decision trace system capturing full pipeline state; "Why this output?" local explanation generator; AI content disclosure markers |
| **Operational Monitoring** | Done | Output quality monitoring with hallucination/coherence/relevance scoring; incident management workflow with severity levels and post-incident review |
| **Metrics & Dashboards** | Done | Governance health dashboard, value realisation dashboard, provider performance scorecard, regulatory compliance reporting, cost forecasting, inference tier utilisation dashboard |

### Agents & Memory

| Component | Status | Description |
|-----------|--------|-------------|
| **Agent Framework** | Done | YAML/TOML agent definitions; cron/file/webhook/MCP triggers; sandbox execution with permission enforcement; agent-to-agent communication; overnight batch processing |
| **Memory Palace** | Done | Wing/Hall/Room/Closet/Drawer hierarchy; verbatim conversation storage; semantic search (<500ms for 100K drawers); automatic context enrichment; knowledge graph with temporal awareness; agent diaries. Adapted from the [MemPalace](https://github.com/milla-jovovich/mempalace) architecture (MIT) for local-first use |
| **AAAK Shorthand** | Done | 5-30x compression for memory/context; layered context loading (L0-L3); prompt shorthand expansion; memory mining from external sources; memory MCP server |
| **Feedback System** | Done | Thumbs up/down on every interaction; feedback-driven learning loops |

### Platform Layer

| Component | Status | Description |
|-----------|--------|-------------|
| **HTTP Server** | Done | Configurable host:port, versioned API routing, composable middleware pipeline, security hardening (CSP, HSTS, rate limiting) |
| **Extensibility** | Done | Plugin registration system, lifecycle hooks, extensible config, anonymisation pattern registration, privacy pipeline hooks, custom provider registration, governance rule hooks |
| **UI Platform** | Done | Design tokens, dark mode/theming, component primitives, application shell, client-side router, navigation, notifications, settings UI |
| **Internationalisation** | Done | Translation function with interpolation/pluralisation, locale file structure, layout accommodation for text expansion |
| **Integration Framework** | Done | Adapter interface with retry/circuit-breaking, OAuth 2.0 support, base HTTP client, input sanitisation |
| **Error Handling** | Done | Server/client/API error handling with correlation IDs, structured error responses, no stack traces leaked |

### Application Layer

| Component | Status | Description |
|-----------|--------|-------------|
| **Browser Mode** | Done | Tab/navigation management, webpage content extraction with privacy filtering, chat/LLM interaction panel, dashboard persistence, web privacy metadata detection |
| **Terminal Mode** | Done | Direct prompting (`loke ask`), coding LLM proxy mode, local compute preprocessing for code, multi-session management, environment integration (`loke init`, `loke doctor`) |
| **Desktop Distribution** | Done | ooke packaging (DMG/NSIS), code signing and notarization, auto-update with stable/beta channels, portable CLI binary, per-user proxy configuration, port conflict detection |

### Cross-Cutting

| Component | Status | Description |
|-----------|--------|-------------|
| **Documentation** | Done | Project documentation site, contribution framework, security policy, architecture document, threat model, security audit checklist |
| **Research** | Done | Peer-reviewed research proposal, TOON benchmark publication |

## What's Next

These features are specified but not yet implemented — the user-facing experience layer.

| Feature | Status | Description |
|---------|--------|-------------|
| **Policy Loader & Regulatory Defaults** | Spec done | YAML/TOML policy format, enterprise URL fetch, regional defaults (GDPR, AU Privacy Act, HIPAA, CCPA, UK GDPR, Singapore PDPA) |
| **Compliance Feedback Loop** | Spec done | Response scanning for compliance violations, warning UI, require-confirmation mode |
| **Audit Reporting & Export** | Spec done | PDF/CSV/JSON reports, time ranges, templates, scheduled generation |
| **First-Run Setup Wizard** | Spec done | Hardware check, Ollama install, provider config, privacy presets, test interaction |
| **Pipeline Visibility Panel** | Spec done | Real-time pipeline stage display, expandable details |
| **Savings Dashboard** | Spec done | Tokens saved, cost saved, PII intercepted, local ratio, trends |
| **Prompt Approval Workflow** | Spec done | Pre-send display, approve/edit/cancel for beta users |
| **Issue Reporting Form** | Spec done | In-app structured issue reporting with privacy pipeline |

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

## Platform Support

- **macOS** — primary platform (Apple Silicon optimised)
- **Windows** — planned

## Project Structure

```
packages/
├── core/              # Shared core engine (privacy, router, optimizer, cache, storage, audit,
│                      #   governance gateway, agent framework, memory palace)
├── browser/           # ooke native binary with web view (browser mode)
├── cli/               # Terminal mode and coding LLM proxy
├── moke/              # Conceptual demo of loke's privacy pipeline (ooke application)
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
