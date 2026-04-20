# loke Architecture

**Version:** 0.2.0
**Last updated:** 2026-04-08
**Status:** Living document

> **Implementation dependency:** loke is written in toke and built on **ooke** ([github.com/karwalski/ooke](https://github.com/karwalski/ooke)) — a web application framework written in toke that compiles to a single native binary with no external runtime dependencies. References to TypeScript, pnpm, Electron, and Node.js in this document reflect the original design intent; the implementation language is toke and the runtime is ooke. Foundation layer development is on hold pending ooke Phase 1 completion.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Layered Architecture](#2-layered-architecture)
3. [Runtime Modes](#3-runtime-modes)
4. [Pipeline Data Flow](#4-pipeline-data-flow)
5. [Package Structure](#5-package-structure)
6. [Extension Point Map](#6-extension-point-map)
7. [Storage Model](#7-storage-model)
8. [Security Boundaries](#8-security-boundaries)
9. [Deployment Model](#9-deployment-model)
10. [Key Constraints](#10-key-constraints)
11. [Technology Decisions](#11-technology-decisions)

---

## 1. System Overview

loke is a locally-run intelligence layer that sits between users and external large language models. It intercepts outbound prompts, scans them for personally identifiable information through a multi-layer privacy pipeline, anonymises detected PII with reversible placeholders, compresses tokens for cost reduction, and routes requests to the best available model based on sensitivity, complexity, cost, and user preference. Responses are de-anonymised before being returned to the user. Everything runs on the user's device. No data leaves the machine without passing through the privacy pipeline. No cloud service is required for core functionality.

loke is structured as three layers. The **Foundation layer** contains the core engine shared by all modes: privacy pipeline, LLM router, token optimiser, storage, MCP framework, and companion device support — implemented in toke, hosted on ooke. The **Platform layer** provides the infrastructure that applications build on: HTTP server (served by ooke), extensibility system, UI shell, internationalisation, integration framework, and error handling. The **Application layer** delivers user-facing modes: browser mode (ooke native binary with web view), terminal mode (CLI and coding LLM proxy), the policy engine, onboarding, and feedback systems.

---

## 2. Layered Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       APPLICATION LAYER                             │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Browser Mode  │  │ Terminal Mode │  │ Policy & Compliance      │  │
│  │ (A1)         │  │ (A2)         │  │ Engine (A3)              │  │
│  │              │  │              │  │                          │  │
│  │ Tabs, nav,   │  │ CLI prompts, │  │ Policy loader, regional  │  │
│  │ chat panel,  │  │ coding proxy,│  │ defaults, compliance     │  │
│  │ web extract, │  │ multi-session│  │ feedback, audit export   │  │
│  │ dashboards   │  │ management   │  │                          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐  │
│  │ Onboarding & UX (A4)     │  │ Feedback & Reporting (A5)      │  │
│  │                          │  │                                │  │
│  │ Setup wizard, pipeline   │  │ Issue reporting, AI-assisted   │  │
│  │ visibility, savings      │  │ drafting, version check,       │  │
│  │ dashboard, prompt        │  │ update notifications           │  │
│  │ approval workflow        │  │                                │  │
│  └──────────────────────────┘  └────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                        PLATFORM LAYER                               │
│                                                                     │
│  ┌─────────────┐ ┌──────────────┐ ┌─────────────┐ ┌────────────┐  │
│  │ HTTP Server  │ │ Extensibility│ │ UI Platform  │ │ i18n       │  │
│  │ (P1)        │ │ (P2)        │ │ (P3)        │ │ (P4)       │  │
│  │             │ │             │ │             │ │            │  │
│  │ localhost   │ │ Plugin reg, │ │ Design      │ │ t() func,  │  │
│  │ server,     │ │ startup/    │ │ tokens,     │ │ locale     │  │
│  │ versioned   │ │ shutdown    │ │ theming,    │ │ files,     │  │
│  │ API routes, │ │ hooks,      │ │ components, │ │ plurals,   │  │
│  │ middleware,  │ │ config ext, │ │ app shell,  │ │ Intl APIs  │  │
│  │ validation,  │ │ anon        │ │ router,     │ │            │  │
│  │ security    │ │ patterns    │ │ nav, notif  │ │            │  │
│  └─────────────┘ └──────────────┘ └─────────────┘ └────────────┘  │
│                                                                     │
│  ┌──────────────────────────┐  ┌────────────────────────────────┐  │
│  │ Integration Framework    │  │ Error Handling (P6)             │  │
│  │ (P5)                    │  │                                │  │
│  │ Adapter interface,       │  │ Server catch-all, client       │  │
│  │ OAuth 2.0, HTTP client, │  │ error handlers, API client     │  │
│  │ input sanitisation       │  │ wrapper, correlation IDs       │  │
│  └──────────────────────────┘  └────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│                       FOUNDATION LAYER                              │
│                                                                     │
│  ┌────────────┐ ┌──────────┐ ┌────────────┐ ┌───────────────────┐  │
│  │ Privacy    │ │ LLM      │ │ Token      │ │ Storage & Audit   │  │
│  │ Pipeline   │ │ Router   │ │ Optimiser  │ │ (F6)             │  │
│  │ (F3)      │ │ (F5)    │ │ (F4)      │ │                   │  │
│  │           │ │          │ │            │ │ SQLCipher, vector │  │
│  │ Regex,    │ │ Intent,  │ │ TOON,      │ │ store, ephemeral, │  │
│  │ NLP NER,  │ │ sensitiv-│ │ LLMLingua, │ │ keychain, audit,  │  │
│  │ SLM NER,  │ │ ity,     │ │ semantic   │ │ settings, sync    │  │
│  │ Presidio, │ │ model    │ │ cache,     │ │ queue, backup     │  │
│  │ mapping,  │ │ select,  │ │ budget     │ │                   │  │
│  │ guardian,  │ │ provider │ │            │ │                   │  │
│  │ templates  │ │ adapters │ │            │ │                   │  │
│  └────────────┘ └──────────┘ └────────────┘ └───────────────────┘  │
│                                                                     │
│  ┌────────────────────┐ ┌──────────────┐ ┌──────────────────────┐  │
│  │ Local Models (F2)  │ │ MCP          │ │ Companion Devices    │  │
│  │                    │ │ Framework    │ │ (F8)                │  │
│  │ Ollama, MLX,       │ │ (F7)        │ │                      │  │
│  │ @electron/llm,     │ │              │ │ Discovery, pairing,  │  │
│  │ Transformers.js,   │ │ Client,      │ │ TLS 1.3, remote     │  │
│  │ model registry     │ │ server host, │ │ inference, Exo       │  │
│  │                    │ │ broker, toke │ │ distributed cluster  │  │
│  └────────────────────┘ └──────────────┘ └──────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Infrastructure: Config (F1.5), Logging (F1.3), Startup/     │   │
│  │ Shutdown (F1.6), Health Checks (F1.7), Build System (F1.1)  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Layer responsibilities

**Foundation.** The core engine that all modes share. Contains no UI, no HTTP server, no mode-specific logic. Any component that touches raw user data, runs inference, or manages persistent storage lives here. The Foundation layer is the highest-trust zone in the system.

**Platform.** Infrastructure and extension points that make loke a platform applications can build on. Provides the HTTP server, plugin registration, UI shell, theming, i18n, integration adapters, and error handling. Applications use Platform primitives rather than building their own. The Platform layer never touches raw PII directly; it delegates to Foundation.

**Application.** User-facing modes and experiences. Browser mode, terminal mode, the policy engine, onboarding flows, and feedback systems are all Application layer concerns. Applications consume Foundation capabilities through Platform extension points. Third-party applications can be built on the Platform layer without forking the core.

---

## 3. Runtime Modes

loke runs in three modes. All three share the same Foundation layer core engine. The mode determines how the user interacts with loke and which Application layer components are active.

```
                    ┌──────────────────────┐
                    │   Foundation Core    │
                    │   (privacy, router,  │
                    │    optimiser, store,  │
                    │    MCP, companion)   │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
     ┌────────────────┐ ┌────────────┐ ┌────────────────┐
     │ Browser Mode   │ │ Terminal   │ │ Platform Mode  │
     │ (Electron)     │ │ Mode (CLI) │ │ (HTTP Server)  │
     └────────────────┘ └────────────┘ └────────────────┘
```

### Browser mode (Electron)

The Electron desktop application with a Chromium-based workspace. Provides tabbed browsing, webpage content extraction with privacy filtering, a dockable chat panel for LLM interaction, dashboard persistence, and web privacy metadata detection. The Electron main process hosts the Foundation core and Platform server; the renderer process is sandboxed and communicates via a restricted IPC bridge (`contextBridge`).

**When used:** Interactive desktop use. Users who want a visual workspace with browsing, chat, pipeline visibility, and savings dashboards.

**Package:** `packages/browser`

### Terminal mode (CLI)

The command-line interface for direct prompting (`loke ask`) and coding LLM proxy mode (`loke proxy claude-code`). In proxy mode, loke intercepts HTTP traffic between a coding LLM CLI (Claude Code, Codex, Gemini CLI) and cloud APIs, passing all traffic through the privacy pipeline transparently. Supports streaming, dry-run, stdin piping, and multi-session management.

**When used:** Developer workflows. Coding with LLM assistants where privacy filtering must happen without switching to a separate application.

**Package:** `packages/cli`

### Platform mode (HTTP server)

The local web server running standalone, without Electron or CLI wrappers. Serves the Platform UI shell and API at `localhost:3000` (configurable). Third-party applications built on loke use this mode, extending it with their own routes, views, middleware, and domain logic through the plugin system.

**When used:** When loke is the platform for another application, or when running loke as a headless service. Also the runtime underlying browser mode (the Electron shell wraps this server).

**Package:** `packages/core` + `packages/shared` (Platform layer packages would be added as the platform matures)

### Shared core

All three modes instantiate the same Foundation core. The privacy pipeline, LLM router, token optimiser, storage layer, MCP framework, and companion device support are mode-agnostic. Mode-specific code is confined to its own package. The dependency direction is always inward: Application depends on Platform depends on Foundation. Foundation never imports from Platform or Application.

---

## 4. Pipeline Data Flow

Every interaction with an external LLM passes through a fixed-sequence pipeline. No stage can be skipped or reordered. This is the core architectural invariant.

```
┌──────────────────────────────────────────────────────────────────────┐
│                        OUTBOUND PATH                                 │
│                                                                      │
│  ┌───────────┐    ┌──────────────────┐    ┌───────────────────────┐  │
│  │           │    │                  │    │                       │  │
│  │  User     │───►│  Privacy Scan    │───►│  Anonymisation        │  │
│  │  Input    │    │  (4-layer)       │    │                       │  │
│  │           │    │                  │    │                       │  │
│  └───────────┘    └──────────────────┘    └───────────┬───────────┘  │
│                                                       │              │
│                                                       ▼              │
│  ┌───────────────────────┐    ┌──────────────────────────────────┐   │
│  │                       │    │                                  │   │
│  │  Template Assembly    │◄───│  Token Optimisation              │   │
│  │  + Guardian Injection │    │  (TOON + LLMLingua + cache)     │   │
│  │                       │    │                                  │   │
│  └───────────┬───────────┘    └──────────────────────────────────┘   │
│              │                                                       │
│              ▼                                                       │
│  ┌───────────────────────┐    ┌──────────────────────────────────┐   │
│  │                       │    │                                  │   │
│  │  Pre-flight Scan      │───►│  Routing Decision               │   │
│  │  (final safety gate)  │    │  (local / companion / cloud)    │   │
│  │                       │    │                                  │   │
│  └───────────────────────┘    └───────────────┬──────────────────┘   │
│                                                │                     │
│                                                ▼                     │
│                                       ┌────────────────┐             │
│                                       │  LLM Call      │             │
│                                       │  (streaming)   │             │
│                                       └────────┬───────┘             │
│                                                │                     │
├────────────────────────────────────────────────┼─────────────────────┤
│                        INBOUND PATH            │                     │
│                                                ▼                     │
│  ┌───────────────────────┐    ┌──────────────────────────────────┐   │
│  │                       │    │                                  │   │
│  │  Response Scan        │◄───│  LLM Response                   │   │
│  │  (compliance check)   │    │                                  │   │
│  │                       │    │                                  │   │
│  └───────────┬───────────┘    └──────────────────────────────────┘   │
│              │                                                       │
│              ▼                                                       │
│  ┌───────────────────────┐    ┌──────────────────────────────────┐   │
│  │                       │    │                                  │   │
│  │  De-anonymisation     │───►│  Output to User                 │   │
│  │  (placeholder reversal│    │                                  │   │
│  │   from mapping table) │    │                                  │   │
│  └───────────────────────┘    └──────────────────────────────────┘   │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │  Audit Log (metadata only — recorded at every stage)         │    │
│  └──────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────┘
```

### Stage descriptions

**1. User Input.** Raw text from the user, which may contain PII, proprietary data, credentials, or other sensitive content. Exists only in memory. Never written to disk in cleartext. Never logged.

**2. Privacy Scan (4-layer).** Four detection layers run in sequence, each adding to the set of identified entities:

| Layer | Technology | Speed | Coverage |
|-------|-----------|-------|----------|
| Regex | Pattern matching (emails, phones, SSNs, credit cards, IPs, AU TFNs/ABNs) | 10 MB/s | High precision, limited to known formats |
| NLP NER | Local SLM via Ollama REST (names, places, organisations) | Variable | Contextual — replaces compromise.js (JS-only library, not applicable in toke/ooke) |
| SLM NER | Local small language model | Variable | Context-aware ("my boss John" vs "John Deere") |
| Presidio | Microsoft Presidio (180+ entity types, optional Docker sidecar) | Variable | Broadest coverage, optional dependency |

Layers are additive. Conflicts are resolved by highest-confidence detection. Duplicate detections are merged.

**3. Anonymisation.** Detected PII entities are replaced with opaque placeholders (`$c1`, `$l2`, `$p3`). The placeholder-to-real-value mapping is stored in an encrypted local mapping table (AES-256-GCM). Mappings are never transmitted and never serialised in cleartext. Applications can register additional entity types and detection patterns via the Platform extensibility layer.

**4. Token Optimisation.** The anonymised prompt is compressed to reduce token consumption:
- TOON serialisation (30-60% savings for structured data)
- LLMLingua prompt compression (5-20x for natural language)
- Semantic cache check (LanceDB vector similarity, returns cached response if above threshold)
- Token budget validation (pre-flight estimate, enforce daily/weekly/monthly limits)

**5. Template Assembly + Guardian Injection.** The anonymised, compressed data is injected into a versioned prompt template. The guardian system prompt is injected into every LLM call. The guardian is non-bypassable and instructs the model to refuse to process identifiable data. Templates are version-controlled files, never runtime strings.

**6. Pre-flight Scan.** A final safety gate runs regex patterns and optionally a local SLM against the fully assembled prompt. If any restricted data is detected that survived anonymisation, the call is blocked and logged. This is the last line of defence before data leaves the device.

**7. Routing Decision.** The LLM router selects the target based on:
- Sensitivity score (PUBLIC / INTERNAL / CONFIDENTIAL / RESTRICTED)
- Intent classification (< 10 ms, embedding-based)
- Model capabilities, cost, speed, and user preference
- Local-first bias: if a local model can handle the task, use it
- Fallback chains for availability

Routes to one of: local SLM (on-device), companion device (encrypted LAN channel), or cloud LLM API (HTTPS, anonymised data only).

**8. LLM Call.** The request is sent to the selected model with streaming support. For local models, data never leaves the device. For companion devices, data crosses an encrypted TLS 1.3 channel on the local network. For cloud APIs, only anonymised and compressed data is transmitted.

**9. Response Scan.** The LLM response is scanned for compliance. The compliance feedback loop checks for policy violations, PII that may have been generated by the model, and content that requires user confirmation before display.

**10. De-anonymisation.** Placeholders in the response are replaced with the original values from the encrypted mapping table. De-anonymised data exists only in local memory. It is never transmitted and never logged.

**11. Output to User.** The restored response is rendered to the user with the original PII in place. The pipeline visibility panel (if enabled) shows what happened at each stage.

**12. Audit Log.** Every pipeline execution is recorded: timestamp, template ID, prompt hash (SHA-256), response hash, pre-flight result, guardian result, provider, model, token counts, duration, routing decision, and any errors. Content is never logged. Only hashes and metadata.

---

## 5. Package Structure

```
packages/
├── core/              # Foundation layer: the shared engine
│   ├── privacy/       # Privacy pipeline (4-layer scan, anonymisation, mapping, guardian)
│   ├── router/        # LLM router (intent classifier, sensitivity scorer, model selector)
│   ├── optimiser/     # Token optimisation (TOON, LLMLingua, semantic cache, budget)
│   ├── storage/       # SQLCipher database, migrations, data access layer, audit trail
│   ├── models/        # Local model management (Ollama, MLX, model registry)
│   ├── mcp/           # MCP client, server hosting, broker logic
│   ├── companion/     # Companion device discovery, pairing, encrypted channel
│   ├── policy/        # Policy loader, merge engine, compliance enforcement
│   └── config/        # Configuration management, secrets, health checks, lifecycle
│
├── browser/           # Application layer: Electron desktop application
│   ├── main/          # Electron main process (window management, IPC, tray)
│   ├── renderer/      # Chromium renderer (tabs, chat panel, web extraction)
│   └── preload/       # Context bridge (restricted IPC surface)
│
├── cli/               # Application layer: terminal mode
│   ├── commands/      # CLI commands (ask, proxy, init, doctor)
│   ├── proxy/         # HTTP proxy for coding LLM interception
│   └── sessions/      # Multi-session management
│
├── mcp-toke/          # Foundation layer: toke MCP server
│                      # Tools: compress, decompress, template, analyse
│                      # Backend: TOON + LLMLingua
│
├── mcp-broker/        # Foundation layer: MCP broker for intermediary routing
│                      # Local/companion/cloud routing, policy enforcement, audit
│
└── shared/            # Cross-cutting: shared types, utilities, configuration
    ├── types/         # TypeScript type definitions shared across packages
    ├── utils/         # Common utility functions
    ├── validation/    # Zod schemas for shared data structures
    └── constants/     # Shared constants and enums
```

### Dependency graph

```
    browser ──────────┐
                      │
    cli ──────────────┤
                      ▼
                    core ──────► shared
                      ▲
    mcp-toke ─────────┤
                      │
    mcp-broker ───────┘
```

**Rules:**
- `shared` has no internal dependencies. It is a leaf package.
- `core` depends only on `shared`.
- `browser`, `cli`, `mcp-toke`, and `mcp-broker` depend on `core` and `shared`.
- `browser` and `cli` never depend on each other.
- No circular dependencies. The dependency direction is always: Application/MCP -> Foundation -> Shared.

### What each package owns

| Package | Owns | Does not own |
|---------|------|-------------|
| `core` | Privacy pipeline, LLM router, token optimiser, storage schema, audit trail, model management, MCP client/server, companion protocol, policy engine, configuration, health checks, startup/shutdown lifecycle | UI, HTTP server, CLI commands, Electron shell |
| `browser` | Electron window management, tab system, chat panel, web content extraction, dashboard rendering, browser-mode onboarding | Privacy logic, routing logic, storage schema, anything that terminal mode also needs |
| `cli` | CLI command parsing, proxy server, session management, terminal output formatting, CLI-mode onboarding | Privacy logic, routing logic, storage schema, anything that browser mode also needs |
| `mcp-toke` | toke MCP server tools (compress, decompress, template, analyse) | General MCP protocol, broker routing |
| `mcp-broker` | MCP intermediary routing, server discovery, policy enforcement on MCP calls | Individual MCP tool implementations |
| `shared` | TypeScript types, Zod schemas, utility functions, constants | Business logic, I/O, side effects |

---

## 6. Extension Point Map

The following table lists every pluggable surface in loke. Applications extend loke by registering at these points through the Platform extensibility system (Epic P2). All registration happens through a single plugin registration API.

| Extension Point | Mechanism | Layer | What It Enables |
|----------------|-----------|-------|-----------------|
| **Routes** | Plugin registration function, namespaced under app prefix | Platform (P1.2) | Applications add their own API endpoints |
| **Middleware** | Ordered middleware array with named insertion points (before-auth, after-validation, etc.) | Platform (P1.3) | Applications inject request processing at defined positions |
| **Health checks** | Registration function, probes appear in aggregate health endpoint | Foundation (F1.7) | Applications register subsystem health probes |
| **Settings sections** | UI extension point in settings view | Platform (P3.9) | Applications add their own settings panels |
| **Configuration modules** | Extended Zod schema + additional env variables, validated at startup | Platform (P2.3) | Applications define domain-specific config sections |
| **Navigation items** | Data array provided to nav component (icons, badges, active state) | Platform (P3.7) | Applications define their own navigation structure |
| **Views / client routes** | Route definition array provided to hash-based client router | Platform (P3.6) | Applications define their own views and route mappings |
| **Anonymisation patterns** | Entity type + detection regex + confidence weight registration | Platform (P2.4) | Applications define domain-specific sensitive data patterns |
| **Prompt templates** | Template files in a configurable directory | Foundation (F3.7) | Applications provide domain-specific LLM prompt templates |
| **LLM providers** | Adapter interface implementation (connect, health, chat, stream) | Foundation (F5.4) | Community adds new LLM provider adapters |
| **Integration adapters** | Standard adapter interface (connect, disconnect, health, domain methods) | Platform (P5.1) | Applications connect to external services with retry/circuit-breaking |
| **Backup destinations** | Destination interface (write, list, delete) | Foundation (F6.5) | Local path or mounted cloud directory |
| **Locale files** | JSON files in `locales/` directory, namespaced keys | Platform (P4.2) | Community contributes translations |
| **Theme tokens** | CSS custom property overrides | Platform (P3.1) | Applications apply their own branding |
| **Startup hooks** | `onBeforeStart`, `onAfterStart` callbacks | Platform (P2.2) | Applications run custom init logic during boot sequence |
| **Shutdown hooks** | `onBeforeShutdown` callback | Platform (P2.2) | Applications clean up resources during graceful shutdown |
| **Database migrations** | Numbered migration files in a configurable directory | Foundation (F6.1) | Applications add tables and indexes alongside platform migrations |
| **Settings store** | Namespaced key prefixes (`loke.*` for platform, app prefix for application) | Foundation (F6.7) | Applications store typed settings without collision |

---

## 7. Storage Model

loke uses five distinct storage mechanisms, each suited to different data characteristics and security requirements.

```
┌────────────────────────────────────────────────────────────────────┐
│                        Storage Architecture                        │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────┐  ┌─────────────────┐  │
│  │ SQLite (SQLCipher)│  │ Vector Store     │  │ Ephemeral Store │  │
│  │                  │  │ (LanceDB)        │  │ (mlock)        │  │
│  │ Conversations    │  │                  │  │                 │  │
│  │ Audit trail      │  │ Semantic cache   │  │ PII mappings    │  │
│  │ PII mappings     │  │ Routing examples │  │ (active session)│  │
│  │ Settings         │  │ Prompt           │  │ Decrypted keys  │  │
│  │ Sync queue       │  │ embeddings       │  │ Raw user input  │  │
│  │ Migrations       │  │                  │  │                 │  │
│  │ Notifications    │  │                  │  │ (never on disk, │  │
│  │                  │  │                  │  │  auto-wipe)     │  │
│  └──────────────────┘  └──────────────────┘  └─────────────────┘  │
│                                                                    │
│  ┌──────────────────┐  ┌──────────────────────────────────────┐   │
│  │ OS Keychain      │  │ Settings Store                       │   │
│  │                  │  │                                      │   │
│  │ API keys         │  │ Namespaced key-value store           │   │
│  │ OAuth tokens     │  │ Types: string, number, boolean, JSON │   │
│  │ Encryption key   │  │ Categories for grouping              │   │
│  │ Companion certs  │  │ Platform prefix: loke.*              │   │
│  │                  │  │ App prefix: configurable             │   │
│  └──────────────────┘  └──────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

### SQLite (SQLCipher)

The primary persistent store. Encrypted at rest via SQLCipher (AES-256-CBC). WAL mode for concurrent reads. Foreign keys enforced. Parameterised queries only — no string concatenation for SQL anywhere.

**What lives here:**
- Audit trail (append-only, hash-chained, tamper-detected; metadata only, never content)
- PII placeholder mappings (encrypted, relationally consistent)
- Settings (typed key-value with namespace prefixes)
- Sync queue (persistent outbound writes with retry/backoff)
- Notifications (stored for the notification panel)
- Application-defined tables (via migration extension point)

**Migration system:** Numbered, ordered, checksummed. Per-migration transactions. Rollback on failure. Tamper detection on historical migrations. Applications add their own migration directories.

**Backup:** Consistent snapshot via `VACUUM INTO`. Timestamped naming. Configurable retention. Configurable destination (local path or mounted cloud directory). Scheduled or manual.

### Vector store (LanceDB)

Embedded vector database for semantic operations. No separate server process.

**What lives here:**
- Semantic cache (prompt embeddings with similarity-based lookup, configurable threshold and TTL)
- Routing examples (embedding-based intent classification training data)
- Prompt embeddings for deduplication

### Ephemeral storage (mlock)

Memory-locked storage that is never written to disk. Used for data that must not survive process termination.

**What lives here:**
- Active PII mappings during a session (copied from encrypted SQLite, held in memory)
- Decrypted API keys during use
- Raw user input before anonymisation
- De-anonymised responses before display

**Properties:** `mlock` prevents swap-out. Secure wipe (overwrite with zeros) on release. Auto-expiry after configurable timeout. Process termination destroys all ephemeral data.

### OS keychain

The operating system's credential store (macOS Keychain, Windows Credential Manager). Used for secrets that must persist across restarts but must not exist in plaintext files.

**What lives here:**
- LLM provider API keys (OpenAI, Anthropic, Google, etc.)
- OAuth 2.0 tokens (access and refresh)
- SQLCipher database encryption key
- Companion device TLS certificates
- Any application-registered credentials

### Settings store

A typed key-value store within SQLite, exposed through a dedicated API.

**What lives here:**
- Appearance preferences (theme, language, timezone)
- Feature flags and user preferences
- Integration connection status
- Application-specific settings (namespaced to avoid collision)

---

## 8. Security Boundaries

loke defines five trust boundaries. The security model assumes that any data crossing an outward boundary must be protected, and any data arriving from an outward boundary must be validated.

```
┌───────────────────────────────────────────────────────────────────┐
│  BOUNDARY A: User's Device                                        │
│  Everything running locally. Data here is under user control.     │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  BOUNDARY B: loke Core Engine                                │  │
│  │  Highest-trust zone. Has access to unencrypted PII,          │  │
│  │  mapping tables, credentials. A compromise here is a         │  │
│  │  full compromise of user data.                               │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  BOUNDARY E: Electron Renderer                               │  │
│  │  Sandboxed Chromium process. Web content is untrusted.       │  │
│  │  Communicates with main process only via contextBridge IPC.  │  │
│  │  A renderer compromise must not grant core engine access.    │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
         │                                    │
         ▼                                    ▼
┌─────────────────────┐           ┌──────────────────────────────┐
│  BOUNDARY C:         │           │  BOUNDARY D: Internet         │
│  Local Network       │           │  (Untrusted)                 │
│                      │           │                              │
│  Companion devices.  │           │  Cloud LLM APIs.             │
│  Partially trusted   │           │  Cloud MCP servers.          │
│  after explicit      │           │  Enterprise policy endpoint. │
│  pairing. TLS 1.3    │           │                              │
│  mutual auth.        │           │  No raw PII crosses this     │
│                      │           │  boundary. Ever.             │
└─────────────────────┘           └──────────────────────────────┘
```

### What stays local (Boundary A/B)

- Raw user input (in-memory only)
- PII mapping tables (encrypted on disk, decrypted in mlock memory)
- Audit trail (encrypted SQLite, metadata only)
- Conversation history
- All credentials (OS keychain)
- Policy files (local copies)
- De-anonymised responses (in-memory only)

### What crosses the network

| Data | Destination | Protection |
|------|------------|------------|
| Anonymised, compressed prompts | Cloud LLM APIs (Boundary D) | HTTPS, no PII, pre-flight scanned |
| Anonymised MCP tool calls | Cloud MCP servers (Boundary D) | HTTPS, privacy-filtered both directions |
| Anonymised prompts for companion inference | Companion device (Boundary C) | TLS 1.3 mutual auth, certificate pinning |
| Policy fetch request | Enterprise policy server (Boundary D) | HTTPS, bearer/mTLS/OAuth2 auth |
| Version check request | Update endpoint (Boundary D) | HTTPS, no user data transmitted |
| Audit metadata export (optional) | SIEM (Boundary D) | HTTPS, metadata only, user-initiated |

### What is encrypted

| Data | At rest | In transit | Key storage |
|------|---------|-----------|-------------|
| SQLite database | SQLCipher (AES-256-CBC) | N/A (local file) | OS keychain |
| PII mapping table | AES-256-GCM within SQLCipher | Never transmitted | OS keychain |
| API keys | OS keychain (OS-managed encryption) | N/A | OS keychain |
| Companion channel | N/A | TLS 1.3 mutual auth | Pinned certificates |
| Cloud LLM requests | N/A | HTTPS (TLS 1.2+) | Provider-managed |

### Electron process isolation

- **Main process:** Runs the Foundation core, has full Node.js access, manages the database, credentials, and privacy pipeline. Trusted.
- **Renderer process:** Sandboxed Chromium. No direct Node.js access. Cannot access the filesystem, database, or credentials. Communicates with main process exclusively through `contextBridge` with a restricted, explicitly defined API surface.
- **Preload script:** The only code that runs in both contexts. Exposes a minimal API to the renderer. Every IPC channel is whitelisted.

### MCP broker boundaries

The MCP broker applies the privacy pipeline to all data flowing through it:
- Tool call arguments are scanned and anonymised before being sent to cloud MCP servers.
- Tool call results from cloud servers are treated as untrusted input and validated.
- Local MCP servers execute on-device; their results still pass through the privacy pipeline before being returned to the LLM.
- The broker maintains a whitelist of approved MCP servers. Unapproved servers are rejected.

### Companion device TLS

- Discovery via mDNS/Bonjour on the local network.
- Pairing requires explicit user approval with confirmation codes.
- Communication channel: TLS 1.3 with mutual authentication and certificate pinning.
- Heartbeat monitoring for connection health.
- Data sent to companion devices passes through the privacy pipeline (anonymised before transmission).

### Plugin sandboxing

Plugins registered through the Platform extensibility system (P2) operate within defined boundaries:
- Plugins register routes, middleware, health checks, and settings sections through a controlled API.
- Plugins cannot access the database directly; they use the data access layer.
- Plugin-registered middleware runs at named insertion points in the middleware pipeline, not at arbitrary positions.
- Plugin configuration is validated against Zod schemas at startup. Invalid config fails fast.

---

## 9. Deployment Model

loke is local-first. There is no cloud service to deploy, no SaaS backend, no account to create. The user installs loke on their device and it works.

### Local installation

- **macOS:** Electron app bundle (browser mode) or npm global install (CLI mode). macOS-first; Apple Silicon optimised via MLX.
- **Windows:** Planned. Electron app + CLI.
- **Linux:** CLI mode. Electron app where supported.

### No cloud dependency

The entire system functions with no network connectivity:
- Local SLM inference via Ollama or MLX (no cloud LLM needed).
- Local MCP servers (no cloud MCP needed).
- SQLite storage (no remote database).
- Policies cached locally (no enterprise server needed after initial fetch).
- Features degrade gracefully when network is unavailable; the application does not break.

### Companion device offload

For users with a high-power device on their local network (Mac Mini, Mac Studio), loke can offload model inference:
- Companion device runs Ollama, MLX, or an Exo distributed cluster.
- Discovery and pairing happen over the local network.
- All communication is encrypted (TLS 1.3 mutual auth).
- Data sent to the companion passes through the privacy pipeline.
- The Exo integration (GPL-3.0) is isolated behind a REST API boundary to maintain Apache 2.0 compatibility.

### Enterprise policy fetch

Organisations can distribute policies to loke installations:
- Enterprise policy files fetched from a configurable URL on startup.
- Authentication via bearer token, mTLS, or OAuth 2.0.
- Refresh interval configurable (default 300 seconds).
- MDM delivery supported (macOS configuration profiles, Windows Group Policy/Intune, Linux config management).
- MDM-delivered policies take precedence over URL-fetched policies.
- loke can be configured to refuse to start without a valid enterprise policy (`required: true`).

---

## 10. Key Constraints

These constraints are non-negotiable. They inform every architectural and implementation decision.

**Privacy is P0.** Any data leak is a critical severity incident. The privacy pipeline is the core architectural invariant. No outbound data bypasses it. No shortcut exists. This is not a feature; it is the foundation.

**No PII in logs.** Not at debug level, not at trace level, not in crash reports, not in audit trails. Audit logs store hashes and metadata. Structured logging auto-redacts sensitive fields. Ephemeral data is wiped on release.

**No GPL in core.** loke is Apache 2.0. GPL dependencies (e.g. Exo) are isolated behind process boundaries and accessed via REST API only. No GPL code is linked into core packages.

**Local-first.** The system must function with no network connectivity. Cloud services are optional enhancements, not requirements. Features degrade; the application does not break.

**The user is the authority.** loke advises; the user decides. Every warning includes what is happening, why it matters, and what the user can do. The only exception is enterprise hard blocks, which still explain themselves and provide an escalation path.

**Feedback is first-class.** Thumbs up/down on every LLM response, routing decision, anonymisation result, warning, and compression result. Thumbs down invites a comment. Feedback feeds into the development pipeline.

**Warnings must be earned.** Every warning costs user trust and attention. Graduated severity (info, advisory, warning, block). Warnings must be actionable, consequential, and timely. Do not cry wolf.

**Speed matters.** Pipeline overhead < 1 second for typical prompts. Intent classification < 10 ms. UI interactions < 100 ms. Privacy and optimisation are meaningless if users bypass the tool because it is slow.

---

## 11. Technology Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Language | TypeScript (strict mode, ESM only) | Type safety, ecosystem, shared language across all packages |
| Package manager | pnpm (workspaces) | Monorepo support, strict dependency resolution, disk efficiency |
| Test runner | Vitest | Fast, TypeScript-native, ESM-first, compatible with Vite ecosystem |
| Linter | ESLint (flat config) | Standard, extensible, flat config is the modern ESLint format |
| Formatter | Prettier | Consistent formatting without debate |
| Validation | Zod | TypeScript-native schema validation, runtime + compile-time safety |
| App shell | Electron | Chromium rendering + Node.js backend in one process, required for browser mode |
| Database | SQLite via SQLCipher | Zero-config, local-first, encrypted at rest, WAL for concurrency |
| Vector store | LanceDB | Embedded (no server process), columnar, fast similarity search |
| Local inference | Ollama, MLX, @electron/llm, Transformers.js | Multiple backends for different hardware and runtime contexts |
| MCP protocol | Model Context Protocol | Standard protocol for LLM tool use, growing ecosystem |
| Naming | kebab-case files, PascalCase types, camelCase functions, SCREAMING_SNAKE_CASE constants | Consistent, conventional, unambiguous |
| Language style | British English in user-facing strings | Project convention (anonymise, optimise, colour) |
| Commits | Conventional commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`) | Automatable changelogs, clear intent |
| License | Apache 2.0 | Permissive, patent grant, compatible with enterprise use |
| Platform | macOS first, Windows planned | Apple Silicon optimisation via MLX is a significant advantage |

---

## Appendix: Document Cross-References

| Document | Path | Relationship to this document |
|----------|------|-------------------------------|
| Design Principles | `docs/design-principles.md` | The "why" behind architectural decisions |
| Epics & Stories | `docs/epics-and-stories.md` | Implementation backlog mapped to this architecture |
| Threat Model | `docs/threat-model.md` | Detailed threat analysis of the boundaries described here |
| Policy Format Spec | `docs/specifications/policy-format.md` | Specification for the policy engine referenced in the pipeline |
| Platform Requirements | External: `alt-project-requirements.md` | Source requirements that drove the layered model |
| CLAUDE.md | `CLAUDE.md` | Quick-reference tech stack and conventions for development |
