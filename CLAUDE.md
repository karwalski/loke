# loke — Claude Code Context

## Project Overview

loke is a locally-run intelligence layer between users and external LLMs. It intercepts, anonymises, optimises, and routes LLM traffic. The mission is to keep people "between the lines" — regulatory, organisational, cost, and ethical.

## Tech Stack

- **Language:** toke (compiles to native binary via ooke)
- **Framework:** ooke ([github.com/karwalski/ooke](https://github.com/karwalski/ooke)) — lightweight CMS and web application framework, compiles to a single native binary with no external runtime dependencies
- **Build System:** ooke (`ooke.toml`) — replaces pnpm/TypeScript monorepo
- **App Shell:** ooke native binary with web view (browser mode) — replaces Electron
- **Platform:** macOS first, Windows planned
- **License:** Apache 2.0

> **Note:** ooke is in Phase 1 development. Foundation layer work is on hold pending ooke readiness. See `docs/epics-and-stories.md` Foundation layer for detail.

## Project Structure

```
src/                   # toke source files
├── core/              # Shared engine: privacy, router, optimizer, cache, storage, audit,
│                      #   governance gateway, agent framework, memory palace
├── browser/           # Browser mode (ooke web view shell)
├── cli/               # Terminal mode and coding LLM proxy
├── mcp-toke/          # toke MCP server
├── mcp-broker/        # MCP broker for intermediary routing
└── shared/            # Shared types, utilities, configuration
ooke.toml              # ooke project configuration
```

## Key Commands

*(Will be confirmed once ooke build system is stable)*

```bash
ooke dev               # Start development server
ooke build             # Production build — single native binary output
ooke test              # Run toke test suite
ooke lint              # Lint toke source
```

## Code Conventions

- Files/dirs: `kebab-case`
- British English in user-facing strings (anonymise, optimise)
- Conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- No GPL dependencies in core (Exo is a separate process via REST API)
- Every code path in this repository that reaches an external provider must traverse the privacy filter. This is a contributor invariant enforced by review, not a property of the language or the machine

## Architecture

The core engine (privacy, router, optimiser, MCP) is mode-agnostic — shared between browser mode and CLI mode. Implemented in toke, hosted on ooke.

Two data paths, and the distinction matters when writing code:

1. **No-custody (intended primary, epic NC1, not yet built):** schema profile + intent out → the model returns an executable artifact → loke validates it and executes it locally against data that never leaves the device.
2. **Redact and forward (what runs today):** privacy filter → token optimiser → router → provider → response restoration.

Path 2 is a fallback, not the destination. Do not describe it as loke's architecture in user-facing
text, and do not present the no-custody flow as novel — it is standard practice in text-to-SQL and
ships in several commercial products. loke's contribution is treating it as a security control with a
threat model, artifact validation and an audit obligation. See `docs/research/disclosure-measurement-findings.md`.

External integrations (Ollama, Presidio, LLMLingua, RouteLLM) are all called via REST and remain language-agnostic.

## Important Constraints

- Privacy is the product — any data leak is P0
- **Figures:** `docs/metrics-baseline.md` is the only place this project publishes numbers from, and it
  has precedence over every other page. Do not restate a figure from elsewhere; cite that file. Do not
  add a figure without a measurement behind it
- **Claims:** before writing any capability claim, check it against `docs/claims.md` and the nine
  things the project must not claim in `docs/research/disclosure-measurement-findings.md` §8
- Never add a code path that reaches an external provider without traversing the privacy filter. Never make the filter fail open — if no detection layer is healthy, fail the request
- Never log PII, even at debug level
- Local-first: system must function with no network
- Feedback (thumbs up/down) is a first-class feature on every interaction
- Warnings must be earned — don't cry wolf
- The user is the authority — loke advises, user decides

## Key Documents

- `docs/design-principles.md` — Human-centred design principles
- `docs/epics-and-stories.md` — Full epic and story breakdown (Foundation on hold pending ooke)
- `docs/architecture.md` — Layered architecture, runtime modes, pipeline data flow
- `CONTRIBUTING.md` — Development setup and coding standards
