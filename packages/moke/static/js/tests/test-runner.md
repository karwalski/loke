# MK9 JavaScript Utility Test Runner

## Overview

Self-contained browser-based test harness for the 9 MK9 JavaScript utility modules used by moke. Tests core parsing, transformation, and utility functions without requiring any build tools or external dependencies.

## Modules tested

1. **json-parser.js** (MokeJsonParser) -- JSON structure detection, flattening, pagination
2. **graphql-source.js** (MokeGraphQL) -- query building, response conversion, localStorage persistence
3. **openapi-discovery.js** (MokeOpenAPI) -- version detection, $ref resolution, example generation, YAML parsing
4. **auth-methods.js** (MokeAuth) -- auth application (Bearer, Basic, API key), value masking
5. **api-cache.js** (MokeApiCache) -- cache set/get, expiry, pruning, deterministic keys
6. **rate-limiter.js** (MokeRateLimiter) -- exponential backoff, Retry-After parsing, host extraction
7. **url-import.js** (MokeUrlImport) -- delimiter detection, CSV parsing, URL normalisation
8. **connection-manager.js** (MokeConnectionManager) -- CRUD, health status, secret stripping on export
9. **datagov-source.js** (MokeDataGov) -- CSV parsing, suggested datasets

## How to run

Open the test runner HTML file directly in a browser:

```
open packages/moke/static/js/tests/test-runner.html
```

Or from the project root:

```
open file://$(pwd)/packages/moke/static/js/tests/test-runner.html
```

The page will:
- Load all 9 JS modules via script tags
- Run all tests synchronously on page load
- Display a pass/fail summary with colour coding
- Log results to the browser console

No server, build step, or npm install is required.

## Interpreting results

- **Green banner** -- all tests passed
- **Red banner** -- one or more tests failed; failed tests are listed with expected vs actual values
- Check the browser console for structured output suitable for scripting
