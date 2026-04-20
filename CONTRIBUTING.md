# Contributing to loke

Thank you for your interest in contributing to loke. This document covers how to report issues, propose features, submit pull requests, development setup, coding standards, and contribution guidelines.

## Reporting Issues

If you find a bug, please open an issue using the **Bug Report** template on [GitHub Issues](https://github.com/karwalski/loke/issues). Include:

- A clear, descriptive title
- Steps to reproduce the problem
- Expected versus actual behaviour
- Your environment (OS version, Node.js version, pnpm version)
- Relevant logs or screenshots

**Security vulnerabilities** must not be reported via public issues. See [SECURITY.md](SECURITY.md) or use GitHub's private vulnerability reporting feature. We take security seriously — privacy is the product.

## Proposing Features

Feature requests are welcome. Use the **Feature Request** template on [GitHub Issues](https://github.com/karwalski/loke/issues). A good feature proposal includes:

- The problem you are trying to solve
- How the feature would work from a user's perspective
- Why existing functionality does not address the need
- Any relevant prior art or references

For significant changes to loke's architecture or public API, we use an RFC process. See [GOVERNANCE.md](GOVERNANCE.md) for details.

## Submitting Pull Requests

1. **Fork and branch.** Fork the repository and create a branch from `main`. Use the naming convention: `feat/description`, `fix/description`, `docs/description`, or `refactor/description`.
2. **Make your changes.** Follow the coding standards below. Keep your PR focused on a single feature or fix.
3. **Write tests.** All new functionality must include tests. Bug fixes should include a test that reproduces the original issue.
4. **Run checks locally.** Before pushing, run `pnpm lint`, `pnpm format --check`, and `pnpm test` to catch issues early.
5. **Sign your commits (DCO).** We use the [Developer Certificate of Origin](https://developercertificate.org/) instead of a separate CLA. Add a `Signed-off-by` line to every commit message by using `git commit -s`. This certifies that you have the right to submit the contribution under the project's Apache 2.0 licence.
6. **Open a pull request.** Fill in the PR template. Describe what changed, why, how you tested it, and whether there are breaking changes.
7. **Respond to review.** A maintainer will review your PR. Be prepared to make changes. All CI checks must pass and at least one approving review is required before merge.

### DCO Sign-Off

Every commit must include a `Signed-off-by` trailer matching the commit author:

```
Signed-off-by: Your Name <your.email@example.com>
```

Use `git commit -s` to add this automatically. If you have multiple commits, every one must be signed. A CI check will verify this. The DCO is a lightweight alternative to a Contributor Licence Agreement — it simply certifies that you have the legal right to make your contribution and that you agree to the terms of the [Developer Certificate of Origin v1.1](https://developercertificate.org/).

## Apache 2.0 License Headers

All source files (TypeScript, JavaScript, CSS, HTML, shell scripts, configuration files with comment support) must include the following Apache 2.0 licence header at the top of the file:

```typescript
// Copyright 2026 loke contributors
// SPDX-License-Identifier: Apache-2.0
```

For file formats that use a different comment syntax, adapt accordingly:

```html
<!-- Copyright 2026 loke contributors -->
<!-- SPDX-License-Identifier: Apache-2.0 -->
```

```bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
```

The SPDX identifier is the preferred short-form. Do not use the full boilerplate text in individual source files — the full licence text is in the `LICENSE` file at the repository root.

## Development Setup

### Prerequisites

- **Node.js** >= 20 LTS
- **pnpm** >= 9 (package manager)
- **macOS** 14+ (Sonoma or later) with Apple Silicon recommended
- **Git** >= 2.40

### Getting Started

```bash
git clone git@github.com:karwalski/loke.git
cd loke
pnpm install
pnpm dev
```

### Monorepo Structure

The project uses pnpm workspaces with the following packages:

- `packages/core` — shared core engine (privacy, router, optimizer, cache, storage, audit)
- `packages/browser` — Electron/Chromium workspace mode
- `packages/cli` — terminal mode and coding LLM proxy
- `packages/mcp-toke` — toke MCP server
- `packages/mcp-broker` — MCP broker for intermediary routing
- `packages/shared` — shared types, utilities, and configuration

## Coding Standards

### Language and Runtime

- **TypeScript** is the primary language for all source code
- Target **ES2023** with Node.js 20+ APIs
- Strict TypeScript configuration — `strict: true`, no `any` escape hatches without justification
- Use **ESM** (ES Modules) exclusively — no CommonJS

### Style and Formatting

- **Prettier** for formatting — no debates, run it and move on
- **ESLint** with a flat config for linting
- Line length: 100 characters
- Indentation: 2 spaces
- Semicolons: yes
- Quotes: single quotes for code, double quotes for JSX attributes
- Trailing commas: all (ES2017+)

### Naming Conventions

- Files and directories: `kebab-case` (e.g., `privacy-filter.ts`, `token-optimizer/`)
- Types and interfaces: `PascalCase` (e.g., `PrivacyConfig`, `RouterDecision`)
- Functions and variables: `camelCase` (e.g., `anonymisePrompt`, `routeRequest`)
- Constants: `SCREAMING_SNAKE_CASE` for true constants (e.g., `MAX_TOKEN_BUDGET`)
- Enum members: `PascalCase`
- Use British English spelling in user-facing strings (anonymise, optimise, colour) but American English for code identifiers where the ecosystem convention is American (e.g., `color` in CSS)

### Code Organisation

- One exported concept per file where practical
- Co-locate tests with source: `privacy-filter.ts` and `privacy-filter.test.ts` in the same directory, or use the `tests/` tree for integration/e2e tests
- Barrel exports (`index.ts`) at package/module boundaries only — not within internal directories
- Prefer explicit imports over wildcard imports

### Error Handling

- Use typed errors — extend `Error` with specific error classes (e.g., `PrivacyFilterError`, `RouterError`)
- Fail fast at system boundaries; trust internal invariants
- Never swallow errors silently — log or propagate
- Use `Result<T, E>` pattern for operations that are expected to fail (file I/O, network, model inference)

### Testing

- **Vitest** as the test runner
- Unit tests for all core logic — privacy filters, router decisions, token optimisation
- Integration tests for pipeline end-to-end flows
- E2E tests for browser and CLI modes using Playwright (browser) and direct process spawning (CLI)
- Test naming: `describe('PrivacyFilter')` > `it('should anonymise email addresses in plain text')`
- No mocking of internal modules — mock at system boundaries only (network, filesystem, model inference)
- Aim for high coverage on `src/core/` — this is the trust boundary

### Dependencies

- Minimise dependencies — every dependency is an attack surface and a maintenance burden
- Prefer well-maintained, audited packages with permissive licenses (MIT, Apache 2.0, BSD)
- No GPL dependencies in core (the Exo integration will be handled as an optional, clearly separated module)
- Pin exact versions in `package.json` — use `pnpm` lockfile for reproducibility
- Review new dependencies for: license compatibility, maintenance status, bundle size, security history

### Security

- **Privacy is the product** — treat any data leak as a P0 bug
- Never log PII or sensitive data, even at debug level
- All outbound data must pass through the privacy filter — no shortcuts, no bypasses
- Secrets and API keys stored in the OS keychain, never in config files or environment variables in production
- Use `crypto.subtle` / Node.js `crypto` for all cryptographic operations — no custom crypto
- Sanitise all inputs at system boundaries

### Git Workflow

- Branch from `main` for all work
- Branch naming: `feat/description`, `fix/description`, `docs/description`, `refactor/description`
- Commits: conventional commits format — `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
- Keep commits atomic — one logical change per commit
- Squash-merge feature branches to `main`
- Write meaningful commit messages: explain *why*, not just *what*

### Pull Requests

- Keep PRs focused — one feature or fix per PR
- Include a clear description of what changed and why
- All CI checks must pass before merge
- At least one approving review required
- Update relevant documentation alongside code changes

### Documentation

- Code should be self-documenting — use clear names and types over comments
- Add JSDoc comments for public API surfaces
- Architecture decisions recorded as ADRs in `docs/adr/`
- Keep the README focused on getting started; detailed docs go in `docs/`

## Platform Considerations

### macOS First

loke targets macOS as the primary platform. Platform-specific code should be isolated behind clear abstractions so Windows support can be added without refactoring core logic.

- Use `process.platform` checks behind abstraction layers, not inline
- Apple Silicon optimisations (MLX, Metal) go in platform-specific modules
- Test on both Intel and Apple Silicon where possible

### Cross-Platform Path

- Abstract all OS-specific operations (keychain access, file paths, notifications, system tray)
- Use `path.join()` and `path.resolve()` — never hardcode path separators
- Design config and storage paths to follow platform conventions (`~/Library/Application Support/loke` on macOS, `%APPDATA%/loke` on Windows)

## Architecture Principles

- **Core engine is mode-agnostic** — the privacy filter, router, optimizer, and MCP broker work identically whether called from the browser shell or the CLI
- **Pipeline over monolith** — data flows through composable stages, each independently testable
- **Local by default** — the system must function fully (minus cloud LLM calls) with no network connection
- **Auditable** — every decision the system makes (route, filter, cache hit) is logged and inspectable
- **Incremental trust** — start with maximum restriction, let users and admins relax controls explicitly
