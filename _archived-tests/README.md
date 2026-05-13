# Archived Tests

These test files were archived on 2026-05-11 during the toke v3 migration.

## Why archived

The v3 migration converted all 562 source files to valid toke v3 syntax, but these test files cannot compile or run because:

1. **Linker gap** — toke's compiler links `tk_web_glue.o` on every build, requiring ooke's db/collections C libraries. A standalone compilation mode is needed in toke before test binaries can be produced.
2. **Broken imports** — test files reference modules via `i=alias:module.path;` that the compiler cannot resolve without a full project-aware module resolver.
3. **Legacy test framework** — some files reference `t.test("name"){ body }` block syntax that doesn't exist in v3.

## What's here

- `loke/unit/` — 148 unit test files across 30 categories (privacy, memory, governance, storage, models, agents, auth, MCP, optimiser, router, CLI, companion, platform, etc.)
- `loke/integration/` — 7 integration test files (health API, pipeline API, MCP roundtrip)
- `loke/e2e/` — 1 end-to-end test file
- `moke/tests/` — 14 moke-specific test files (feedback, memory, pipeline panel, governance, cost comparison, etc.)

## Companion files

The `.tkc.md` companion files alongside each test file document the intended test behaviour. These serve as specifications for writing the replacement test suite (Epic X4b).

## Replacement

New test suites are being written under `tests/` (loke) and `packages/moke/tests/` (moke) as part of Epic X4b in `docs/epics-and-stories.md`.
