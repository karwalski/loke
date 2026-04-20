# Testing & Developer Experience Specification

**Epic:** X4 — Testing & Developer Experience
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke provides shared test infrastructure, quality gates, and developer tooling that both the platform and applications use. The goal is to eliminate boilerplate, enforce consistency, and make the fast path the correct path.

This specification defines:

- Test utilities for databases, servers, configuration, and integration mocks
- Quality gate script (single-command pipeline from lint to build)
- Watch mode for development (server restart + client reload)
- Scaffold generator for common boilerplate (migrations, routes, adapters, locales)
- Debug mode for request inspection, query logging, pipeline tracing, and route matching

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Do the right thing by default.** Test utilities configure themselves correctly. The quality gate runs everything in the right order. Scaffold generators produce code that passes all checks on first run.
- **Speed is a feature.** Watch mode and fast test execution are non-negotiable. A slow feedback loop kills productivity.
- **Feedback is first-class.** Debug mode makes the system's internal behaviour visible. Developers should never have to guess why a request was routed a particular way.
- **Privacy is the foundation.** Debug mode never logs PII, even when inspecting request payloads. Debug output passes through the same redaction filters as production logging.

---

## 2. Test Utilities

### 2.1 In-Memory Test Database

The platform provides a factory function for creating isolated, in-memory SQLite databases pre-loaded with the platform schema. Each test gets its own database — no shared state between tests.

```typescript
import { createTestDatabase } from '@loke/shared/test-utils';

describe('conversation storage', () => {
  it('stores and retrieves a conversation', async () => {
    const db = await createTestDatabase();

    // Database is fully migrated and ready to use
    await db.run(
      'INSERT INTO conversations (id, title) VALUES (?, ?)',
      ['conv-1', 'Test conversation']
    );

    const row = await db.get(
      'SELECT * FROM conversations WHERE id = ?',
      ['conv-1']
    );
    expect(row.title).toBe('Test conversation');

    // Cleanup is automatic — in-memory DB is discarded when `db` goes out of scope
    await db.close();
  });
});
```

**`createTestDatabase` options:**

```typescript
interface TestDatabaseOptions {
  /** Additional migration directories to run after platform migrations. */
  migrationDirs?: string[];

  /** Seed data to insert after migrations. */
  seeds?: Array<{ table: string; rows: Record<string, unknown>[] }>;

  /** Whether to enable WAL mode. Default: false (in-memory). */
  walMode?: boolean;
}

async function createTestDatabase(
  options?: TestDatabaseOptions
): Promise<TestDatabase>;
```

The `TestDatabase` type extends the platform's standard database interface with no additional methods — it is a real database, not a mock. The only difference is that it uses `:memory:` as the path and runs migrations on creation.

### 2.2 Test Server

The platform provides a factory for creating a fully configured HTTP server instance bound to an ephemeral port. The server is identical to a production server except for the port and configuration overrides.

```typescript
import { createTestServer } from '@loke/shared/test-utils';

describe('API routes', () => {
  let server: TestServer;

  beforeAll(async () => {
    server = await createTestServer({
      configOverrides: {
        features: { telemetry: false },
      },
    });
  });

  afterAll(async () => {
    await server.close();
  });

  it('returns health status', async () => {
    const response = await server.request('GET', '/api/v1/health');
    expect(response.status).toBe(200);
    expect(response.body.status).toBe('ok');
  });

  it('validates request body', async () => {
    const response = await server.request('POST', '/api/v1/settings', {
      body: { key: '', value: 'test' },
    });
    expect(response.status).toBe(400);
    expect(response.body.error.code).toBe('VALIDATION_ERROR');
  });
});
```

**`createTestServer` options:**

```typescript
interface TestServerOptions {
  /** Configuration overrides merged on top of test defaults. */
  configOverrides?: Partial<AppConfig>;

  /** Additional route registrations. */
  routes?: RouteDefinition[];

  /** Additional middleware. */
  middleware?: MiddlewareDefinition[];

  /** Pre-populated test database. If omitted, a fresh in-memory database is created. */
  database?: TestDatabase;
}

interface TestServer {
  /** The base URL of the running server (e.g. "http://localhost:54321"). */
  baseUrl: string;

  /** The port the server is listening on. */
  port: number;

  /** Make a request to the test server. */
  request(
    method: string,
    path: string,
    options?: { body?: unknown; headers?: Record<string, string> }
  ): Promise<TestResponse>;

  /** Access the underlying database for assertions. */
  database: TestDatabase;

  /** Shut down the server and clean up. */
  close(): Promise<void>;
}
```

### 2.3 Test Configuration

The platform provides a configuration generator that produces valid configuration objects with sensible test defaults. All values are overridable.

```typescript
import { createTestConfig } from '@loke/shared/test-utils';

const config = createTestConfig({
  server: { port: 0 },  // 0 = ephemeral port
  database: { path: ':memory:' },
  logging: { level: 'silent' },
});
```

The generated configuration passes the same Zod schema validation as production configuration. If an override produces an invalid configuration, the function throws immediately with a descriptive error — not at test runtime when the config is used.

### 2.4 Integration Mocks

The platform provides mock implementations of the integration adapter interface (P5.1) for use in tests. Mocks record all calls and allow pre-configured responses.

```typescript
import { createMockAdapter } from '@loke/shared/test-utils';

const mockLlm = createMockAdapter('llm', {
  responses: {
    complete: {
      text: 'The anonymised response from the mock LLM.',
      tokens: { prompt: 100, completion: 50 },
    },
  },
});

// Use the mock in place of a real adapter
const result = await mockLlm.complete({ prompt: 'test prompt' });
expect(result.text).toBe('The anonymised response from the mock LLM.');

// Assert the adapter was called correctly
expect(mockLlm.calls).toHaveLength(1);
expect(mockLlm.calls[0].method).toBe('complete');
expect(mockLlm.calls[0].args.prompt).toBe('test prompt');

// Simulate failure
mockLlm.setNextResponse('complete', { error: 'Connection refused' });
```

**Available mock adapters:**

| Adapter | Mock Name | Key Methods |
|---------|-----------|-------------|
| LLM provider | `createMockAdapter('llm')` | `complete`, `stream`, `embed` |
| HTTP client | `createMockAdapter('http')` | `get`, `post`, `put`, `delete` |
| Credential store | `createMockAdapter('credentials')` | `get`, `set`, `delete` |
| Health check | `createMockAdapter('health')` | `check` |

All mock adapters implement the same interface as their real counterparts. Passing a mock where a real adapter is expected requires no special handling — they are type-compatible.

---

## 3. Quality Gate Script

### 3.1 Purpose

The quality gate is a single command that validates the entire codebase. It is used as:

1. A pre-push Git hook (runs automatically before `git push`).
2. The CI pipeline gate (runs on every pull request and merge to main).
3. A manual developer check (`pnpm gate`).

### 3.2 Execution Flow

```
┌─────────┐    ┌──────────────┐    ┌──────────────────┐    ┌────────────┐
│  Lint   │───→│ Format Check │───→│ Dependency Audit │───→│ Unit Tests │
└─────────┘    └──────────────┘    └──────────────────┘    └────────────┘
                                                                  │
                                                                  ▼
┌─────────┐    ┌────────────┐    ┌───────────────────┐    ┌──────────────────┐
│  Build  │←───│ a11y Tests │←───│ Integration Tests │←───│                  │
└─────────┘    └────────────┘    └───────────────────┘    └──────────────────┘
```

| Step | Command | Failure Behaviour |
|------|---------|-------------------|
| **1. Lint** | `eslint .` | Fail immediately. No point checking formatting if code has lint errors. |
| **2. Format check** | `prettier --check .` | Fail immediately. Suggest `pnpm format` to fix. |
| **3. Dependency audit** | `pnpm audit --audit-level=high` | Fail on high or critical vulnerabilities. Advisory and moderate are logged as warnings. |
| **4. Unit tests** | `vitest run --coverage` | Fail if any test fails or coverage drops below configured threshold. |
| **5. Integration tests** | `vitest run --config vitest.integration.config.ts` | Fail if any test fails. Integration tests may include a11y checks on rendered components. |
| **6. a11y tests** | `vitest run --config vitest.a11y.config.ts` | Fail on any axe-core violation. Zero-violation policy. |
| **7. Build** | `pnpm build` | Fail if TypeScript compilation or bundling fails. This catches type errors not caught by the editor. |

### 3.3 Script Interface

```bash
# Run the full gate
pnpm gate

# Run a specific step (for debugging a failure)
pnpm gate --step lint
pnpm gate --step format
pnpm gate --step audit
pnpm gate --step unit
pnpm gate --step integration
pnpm gate --step a11y
pnpm gate --step build

# Run from a specific step onwards (skip earlier steps)
pnpm gate --from unit

# Show timing breakdown
pnpm gate --timing
```

### 3.4 Output Format

The gate prints a summary line for each step:

```
[✓] Lint                  0 errors, 0 warnings                    1.2s
[✓] Format check          All files formatted                     0.8s
[✓] Dependency audit       0 high/critical, 2 moderate            0.3s
[✓] Unit tests            142 passed, 0 failed (87% coverage)     4.1s
[✓] Integration tests      38 passed, 0 failed                    6.2s
[✓] a11y tests             24 passed, 0 violations                1.8s
[✓] Build                 TypeScript compiled, bundle created      3.4s
─────────────────────────────────────────────────────────────────────────
Gate passed                                                       17.8s
```

On failure:

```
[✓] Lint                  0 errors, 0 warnings                    1.2s
[✓] Format check          All files formatted                     0.8s
[✓] Dependency audit       0 high/critical, 2 moderate            0.3s
[✗] Unit tests            140 passed, 2 failed (86% coverage)     3.9s

    FAIL  src/privacy/regex-detector.test.ts > detects AU TFN
      Expected: 1 entity found
      Received: 0 entities found

    FAIL  src/router/intent-classifier.test.ts > classifies code generation
      Expected: "code_generation"
      Received: "analysis"

Gate FAILED at step: unit tests
```

The gate stops at the first failing step. Subsequent steps are not run.

### 3.5 Coverage Thresholds

The quality gate enforces minimum coverage thresholds configured in the Vitest configuration:

| Scope | Threshold | Rationale |
|-------|-----------|-----------|
| Statements | 80% | General coverage floor |
| Branches | 75% | Ensures conditional logic is tested |
| Functions | 80% | Ensures exported functions are tested |
| Lines | 80% | Consistent with statement coverage |
| Privacy pipeline | 100% | Privacy is the product — no untested paths |

These thresholds are enforced globally. Individual packages may set higher thresholds by overriding in their own Vitest config.

---

## 4. Watch Mode

### 4.1 Purpose

Watch mode provides instant feedback during development. When a file changes, the relevant process restarts or reloads automatically.

### 4.2 Behaviour

| File Change | Action | Mechanism |
|-------------|--------|-----------|
| Server source (`packages/*/src/**/*.ts`) | Restart the server process | Process kill + restart via `tsx watch` |
| Client source (`packages/*/client/**/*.{ts,js,css,html}`) | Reload the browser page | Lightweight file watcher + WebSocket notification to client |
| Shared types (`packages/shared/src/**/*.ts`) | Restart server + reload client | Both actions triggered |
| Test files (`**/*.test.ts`) | Re-run the changed test file | `vitest --watch` (Vitest's built-in watcher) |
| Configuration files (`*.config.ts`, `.env*`) | Restart server | Full restart to re-validate config |
| Migration files (`**/migrations/**`) | Log a warning (no auto-run) | Migrations are not auto-executed; developer must run manually |
| Locale files (`**/locales/**/*.json`) | Reload client | Locale files are re-fetched by the client |

### 4.3 Interface

```bash
# Start watch mode (server + client)
pnpm dev

# Start watch mode for server only
pnpm dev:server

# Start watch mode for client only
pnpm dev:client

# Start test watcher
pnpm test:watch
```

### 4.4 Client Reload Mechanism

The development server injects a lightweight WebSocket client into the HTML page during development (never in production builds). When the file watcher detects a change:

1. The watcher sends a `reload` message over the WebSocket.
2. The client receives the message and calls `window.location.reload()`.

This is a full-page reload, not hot module replacement (HMR). Full reload is chosen over HMR for simplicity and reliability — the platform uses vanilla TypeScript and CSS, not a framework that benefits from HMR's state preservation.

### 4.5 Performance

| Metric | Target |
|--------|--------|
| Server restart after file change | < 2 seconds |
| Client reload notification delivery | < 100ms after file write |
| Test re-run after file change | < 1 second to start |
| File watcher memory overhead | < 20MB RSS |

The file watcher uses native OS file system events (FSEvents on macOS, inotify on Linux) via chokidar or equivalent. Polling is not used.

---

## 5. Scaffold Generator

### 5.1 Purpose

The scaffold generator creates boilerplate files for common development tasks. Generated files follow all project conventions (naming, structure, imports, TypeScript types) and pass the quality gate without modification.

### 5.2 Command Reference

```bash
loke generate <type> <name> [options]
```

| Type | Command | What It Creates |
|------|---------|-----------------|
| **migration** | `loke generate migration <name>` | Numbered migration file |
| **route** | `loke generate route <name>` | Route handler, validation schema, test file |
| **adapter** | `loke generate adapter <name>` | Integration adapter, mock, test file |
| **locale** | `loke generate locale <language-code>` | Locale JSON file with all platform keys |

#### 5.2.1 Migration Generator

```bash
loke generate migration add-user-preferences
```

Creates:

```
packages/core/src/database/migrations/
  0004-add-user-preferences.ts
```

The migration number is automatically assigned as the next sequential number. The file contains up and down functions with placeholder SQL:

```typescript
import type { Database } from '../types.js';

export async function up(db: Database): Promise<void> {
  await db.run(`
    -- TODO: Add migration SQL
    CREATE TABLE IF NOT EXISTS user_preferences (
      id TEXT PRIMARY KEY,
      created_at TEXT NOT NULL DEFAULT (datetime('now'))
    )
  `);
}

export async function down(db: Database): Promise<void> {
  await db.run(`
    -- TODO: Add rollback SQL
    DROP TABLE IF EXISTS user_preferences
  `);
}
```

#### 5.2.2 Route Generator

```bash
loke generate route user-preferences
```

Creates:

```
packages/core/src/routes/
  user-preferences.ts          # Route handler
  user-preferences.schema.ts   # Zod validation schemas
  user-preferences.test.ts     # Test file with test server setup
```

**Route handler template:**

```typescript
import type { RouteDefinition } from '../types.js';
import { schema } from './user-preferences.schema.js';

export const userPreferencesRoutes: RouteDefinition[] = [
  {
    method: 'GET',
    path: '/api/v1/user-preferences',
    handler: async (req, res) => {
      // TODO: Implement
      res.json({ data: [] });
    },
  },
  {
    method: 'POST',
    path: '/api/v1/user-preferences',
    validation: schema.create,
    handler: async (req, res) => {
      // TODO: Implement
      res.status(201).json({ data: req.body });
    },
  },
];
```

**Test file template:**

```typescript
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { createTestServer, type TestServer } from '@loke/shared/test-utils';
import { userPreferencesRoutes } from './user-preferences.js';

describe('user-preferences routes', () => {
  let server: TestServer;

  beforeAll(async () => {
    server = await createTestServer({ routes: userPreferencesRoutes });
  });

  afterAll(async () => {
    await server.close();
  });

  it('GET /api/v1/user-preferences returns 200', async () => {
    const response = await server.request('GET', '/api/v1/user-preferences');
    expect(response.status).toBe(200);
  });
});
```

#### 5.2.3 Adapter Generator

```bash
loke generate adapter calendar-provider
```

Creates:

```
packages/core/src/integrations/
  calendar-provider.ts         # Adapter implementation
  calendar-provider.mock.ts    # Mock implementation for tests
  calendar-provider.test.ts    # Test file
```

**Adapter template:**

```typescript
import type { IntegrationAdapter } from '../types.js';

export interface CalendarProviderAdapter extends IntegrationAdapter {
  // TODO: Define domain-specific methods
}

export function createCalendarProviderAdapter(
  config: CalendarProviderConfig
): CalendarProviderAdapter {
  return {
    name: 'calendar-provider',

    async connect(): Promise<void> {
      // TODO: Implement connection logic
    },

    async disconnect(): Promise<void> {
      // TODO: Implement disconnection logic
    },

    async healthCheck(): Promise<{ healthy: boolean; message?: string }> {
      // TODO: Implement health check
      return { healthy: true };
    },
  };
}
```

**Mock template:**

```typescript
import { createMockAdapter } from '@loke/shared/test-utils';

export function createMockCalendarProvider() {
  return createMockAdapter('calendar-provider', {
    responses: {
      connect: undefined,
      disconnect: undefined,
      healthCheck: { healthy: true },
    },
  });
}
```

#### 5.2.4 Locale Generator

```bash
loke generate locale fr
```

Creates:

```
packages/shared/locales/
  fr.json
```

The generated file contains all platform keys from `en.json` with values set to the English text prefixed with `[fr]` as a visual marker for untranslated strings:

```json
{
  "loke.nav.settings": "[fr] Settings",
  "loke.nav.dashboard": "[fr] Dashboard",
  "loke.settings.appearance": "[fr] Appearance",
  "loke.settings.language": "[fr] Language"
}
```

This ensures the file is structurally valid and the application is usable before any translations are provided. Translators replace the prefixed strings with actual translations.

### 5.3 Generator Conventions

1. All generated files are formatted with Prettier before being written.
2. The generator refuses to overwrite existing files. Use `--force` to override.
3. Names are normalised to kebab-case for file names and camelCase/PascalCase for code identifiers, following the project's naming conventions.
4. After generation, the generator prints the created file paths and any manual steps required:

```
Created:
  packages/core/src/routes/user-preferences.ts
  packages/core/src/routes/user-preferences.schema.ts
  packages/core/src/routes/user-preferences.test.ts

Next steps:
  1. Register the route in packages/core/src/routes/index.ts
  2. Implement the handler logic
  3. Run: pnpm test -- user-preferences
```

---

## 6. Debug Mode

### 6.1 Purpose

Debug mode exposes internal system behaviour that is hidden in normal operation. It is a developer tool — never enabled in production.

### 6.2 Activation

Debug mode is activated via configuration or environment variable:

```bash
# Via environment variable
LOKE_DEBUG=true pnpm dev

# Via configuration file
# config.yaml
debug:
  enabled: true
  request_inspection: true
  query_logging: true
  pipeline_tracing: true
  route_matching: true
```

Individual debug features can be toggled independently. Setting `LOKE_DEBUG=true` enables all features. Setting `debug.enabled: true` in configuration enables all features unless individual features are explicitly set to `false`.

### 6.3 Safety

Debug mode enforces the same privacy constraints as production:

1. **PII redaction.** All debug output passes through the same log redaction filters. PII is never logged, even in debug mode.
2. **Production guard.** If `NODE_ENV=production`, debug mode refuses to activate and logs a warning: "Debug mode cannot be enabled in production. Set NODE_ENV to 'development' or 'test'."
3. **No persistence.** Debug output is written to stdout/stderr only. It is not stored in the database, not written to log files, and not included in audit trails.

### 6.4 Request Inspection

When enabled, every HTTP request and response is logged with full detail (excluding PII):

```
─── REQUEST ───────────────────────────────────────────────────────────────
  ID:       req-a1b2c3d4
  Method:   POST
  Path:     /api/v1/conversations
  Headers:  Content-Type: application/json
            Accept: application/json
            X-Request-ID: req-a1b2c3d4
  Body:     { "title": "New conversation", "model": "claude-sonnet-4" }
  Size:     67 bytes

─── RESPONSE ──────────────────────────────────────────────────────────────
  ID:       req-a1b2c3d4
  Status:   201 Created
  Headers:  Content-Type: application/json
            X-Request-ID: req-a1b2c3d4
  Body:     { "data": { "id": "conv-x7y8z9", "title": "New conversation" } }
  Size:     82 bytes
  Duration: 12ms
```

Bodies larger than 4KB are truncated with `... (truncated, 12,340 bytes total)`. Binary bodies show `(binary, 45,678 bytes)`.

### 6.5 Database Query Logging

When enabled, every database query is logged with its parameters, execution time, and row count:

```
─── QUERY ─────────────────────────────────────────────────────────────────
  SQL:      SELECT * FROM conversations WHERE id = ? AND deleted_at IS NULL
  Params:   ["conv-x7y8z9"]
  Duration: 0.8ms
  Rows:     1
```

```
─── QUERY ─────────────────────────────────────────────────────────────────
  SQL:      INSERT INTO audit_log (id, timestamp, template_id, prompt_hash, ...)
            VALUES (?, ?, ?, ?, ...)
  Params:   ["audit-123", "2026-04-05T10:30:00Z", "summarise-v2", "sha256:abc...", ...]
  Duration: 1.2ms
  Rows:     1 (affected)
```

**Slow query highlighting:** Queries exceeding 50ms are logged with a `[SLOW]` prefix and highlighted in yellow in terminal output.

### 6.6 Pipeline Stage Tracing

When enabled, the privacy pipeline logs detailed trace information for every stage:

```
─── PIPELINE TRACE ────────────────────────────────────────────────────────
  Request:  req-a1b2c3d4

  [1/9] Input                                                        0.1ms
        Source: chat | Content: text | Tokens (est): 340

  [2/9] Privacy Scan                                                 11.8ms
        Layers: regex (2.1ms), nlp (5.4ms), slm_ner (4.3ms)
        Entities: 7 found
          email_address     ×3  confidence: 0.99  layer: regex
          person_name       ×2  confidence: 0.87  layer: nlp, slm_ner
          phone_number      ×1  confidence: 0.95  layer: regex
          street_address    ×1  confidence: 0.72  layer: slm_ner

  [3/9] Anonymisation                                                 2.4ms
        Anonymised: 6 | Skipped: 1 (below threshold)
        Mappings: $e1, $e2, $e3, $p1, $p2, [PHONE]

  [4/9] Token Optimisation                                            7.6ms
        1,240 → 720 tokens (42% saved)
        Methods: TOON (21%), LLMLingua (27%)
        Cache: miss (similarity: 0.62)

  [5/9] Routing                                                       1.9ms
        Strategy: cheapest-adequate
        Sensitivity: confidential
        Intent: code_generation (0.94)
        Selected: claude-sonnet-4 via anthropic
        Reason: Meets capability threshold; lowest cost for task type
        Fallback: qwen3-32b (ollama) → gpt-4o-mini (openai)

  [6/9] LLM Call                                                   1,820.0ms
        Provider: anthropic | Model: claude-sonnet-4
        Tokens: 720 sent, 340 received
        First token: 210ms | Cost: $0.004 USD
        Streaming: yes | Stop: end_turn

  [7/9] Response Scan                                                 0.9ms
        Result: clean (0 violations)

  [8/9] De-anonymisation                                              0.7ms
        Restored: 5 | Unmatched: 0

  [9/9] Output                                                        0.1ms
        Characters: 1,240 | Tokens (est): 340

  ─── SUMMARY ───────────────────────────────────────────────────────────
  Total: 1,845.5ms | Overhead: 25.5ms (1.4%)
```

### 6.7 Route Matching Details

When enabled, the router logs how it resolved each incoming request to a handler:

```
─── ROUTE MATCH ───────────────────────────────────────────────────────────
  Method:   GET
  Path:     /api/v1/conversations/conv-x7y8z9/messages
  Matched:  /api/v1/conversations/:id/messages
  Params:   { "id": "conv-x7y8z9" }
  Handler:  getConversationMessages
  Middleware: [requestId, logging, cors, bodyLimit, timeout, validation]
```

When no route matches:

```
─── ROUTE MATCH ───────────────────────────────────────────────────────────
  Method:   GET
  Path:     /api/v1/converstions
  Matched:  (none)
  Candidates checked:
    /api/v1/conversations          (method match, path mismatch)
    /api/v1/conversations/:id      (method match, path mismatch)
  Result:   404 Not Found
  Hint:     Did you mean /api/v1/conversations?
```

The route matcher includes a Levenshtein distance check against registered routes when no match is found, and suggests the closest match if the edit distance is 3 or fewer characters.

### 6.8 Debug Output Configuration

| Option | Default (when debug enabled) | Description |
|--------|------------------------------|-------------|
| `debug.request_inspection` | `true` | Log request/response details |
| `debug.query_logging` | `true` | Log database queries |
| `debug.pipeline_tracing` | `true` | Log pipeline stage traces |
| `debug.route_matching` | `true` | Log route resolution details |
| `debug.slow_query_threshold_ms` | `50` | Threshold for slow query highlighting |
| `debug.body_truncate_bytes` | `4096` | Max body size before truncation in request logs |
| `debug.colour` | `true` | Use ANSI colour codes in terminal output |

---

## 7. Performance Requirements

| Requirement | Target |
|-------------|--------|
| Quality gate total execution | < 60 seconds for the full platform |
| Watch mode restart latency | < 2 seconds from file save to server ready |
| Scaffold generator execution | < 1 second per command |
| Debug mode logging overhead | < 5ms per request (negligible vs. pipeline time) |
| Test database creation | < 100ms (including migrations) |
| Test server creation | < 500ms (including database, config, route registration) |

Debug mode overhead must not measurably affect request latency or pipeline behaviour. All debug logging is asynchronous — it does not block the request/response cycle.
