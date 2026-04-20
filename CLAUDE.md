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
- All outbound data passes through privacy filter — no exceptions

## Architecture

The core engine (privacy, router, optimiser, MCP) is mode-agnostic — shared between browser mode and CLI mode. Data flows through a composable pipeline: privacy filter → token optimiser → router → LLM → response restoration. Implemented in toke, hosted on ooke.

External integrations (Ollama, Presidio, LLMLingua, RouteLLM) are all called via REST and remain language-agnostic.

## Important Constraints

- Privacy is the product — any data leak is P0
- All outbound data must pass through the privacy filter — no shortcuts
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
