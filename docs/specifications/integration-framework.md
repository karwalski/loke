# Integration Framework Specification

**Epic:** P5 — Integration Framework
**Stories:** P5.1, P5.2, P5.3, P5.4
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke provides reusable primitives for connecting to external services. The integration framework handles the concerns common to every external connection — authentication, retry, circuit-breaking, timeout, and health checking — so that application-specific adapters can focus on domain logic.

This specification defines:

- The integration adapter interface (TypeScript contract for all external service connections)
- OAuth 2.0 authorisation code grant with PKCE, token storage, and automatic refresh
- A base HTTP client with timeout, retry, circuit-breaking, and rate limit awareness
- Input sanitisation utilities for HTML, SQL, log injection, and schema validation

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Graceful degradation.** Every external integration is optional. The application works offline, without AI, without calendar sync, without cloud backup. Features degrade; the application does not break.
- **Privacy is the foundation.** The HTTP client logs headers but never request or response bodies. OAuth tokens are stored in the OS credential store, never in plaintext.
- **Extensible.** Applications implement the adapter interface for their own services. The framework provides the infrastructure; the application provides the domain logic.
- **Auditable.** Connection state changes, authentication events, and circuit breaker transitions are logged with correlation IDs.

### 1.2 Requirements Traceability

| Requirement | Story |
|-------------|-------|
| R8.1 — Integration adapter interface | P5.1 |
| R8.2 — OAuth 2.0 support | P5.2 |
| R8.6 — External API client utilities | P5.3 |
| R12.2 — Input sanitisation | P5.4 |

---

## 2. Integration Adapter Interface

Every external service connection implements the `IntegrationAdapter` interface. This provides a uniform contract for lifecycle management, health monitoring, and error handling across all integrations — LLM providers, calendar services, backup destinations, and any application-defined service.

### 2.1 TypeScript Interface

```typescript
/**
 * Standard contract for all external service integrations.
 * Applications implement this interface for each service they connect to.
 */
interface IntegrationAdapter<TConfig extends AdapterConfig = AdapterConfig> {
  /** Unique identifier for this adapter instance (e.g. "microsoft-graph", "anthropic"). */
  readonly id: string;

  /** Human-readable display name (e.g. "Microsoft Graph", "Anthropic Claude"). */
  readonly displayName: string;

  /** Current connection state. */
  readonly state: AdapterState;

  /**
   * Initialise the adapter and establish a connection to the external service.
   * Must be idempotent — calling connect() on an already-connected adapter is a no-op.
   *
   * @throws AdapterConnectionError if the connection cannot be established
   *         after exhausting retry attempts.
   */
  connect(): Promise<void>;

  /**
   * Gracefully disconnect from the external service.
   * Releases resources, closes connections, cancels pending requests.
   * Must be idempotent — calling disconnect() on a disconnected adapter is a no-op.
   */
  disconnect(): Promise<void>;

  /**
   * Probe the external service and report health status.
   * Must complete within the configured health check timeout.
   * Must not throw — returns a health result indicating status.
   */
  healthCheck(): Promise<HealthCheckResult>;

  /**
   * The adapter's configuration, validated at construction time.
   */
  readonly config: TConfig;
}

/** Base configuration shared by all adapters. */
interface AdapterConfig {
  /** Maximum time in milliseconds to wait for a connection to be established. */
  connectTimeoutMs: number;

  /** Maximum time in milliseconds to wait for a single request to complete. */
  requestTimeoutMs: number;

  /** Maximum number of retry attempts for transient failures. */
  maxRetries: number;

  /** Base delay in milliseconds for exponential backoff. */
  retryBaseDelayMs: number;

  /** Maximum delay in milliseconds for exponential backoff. */
  retryMaxDelayMs: number;

  /** Number of consecutive failures before the circuit breaker opens. */
  circuitBreakerThreshold: number;

  /** Time in milliseconds before a tripped circuit breaker enters half-open state. */
  circuitBreakerCooldownMs: number;

  /** Maximum time in milliseconds for a health check probe. */
  healthCheckTimeoutMs: number;
}

/** Adapter connection states. */
type AdapterState =
  | "disconnected"   // Not connected. Initial state.
  | "connecting"     // Connection attempt in progress.
  | "connected"      // Connected and healthy.
  | "degraded"       // Connected but experiencing errors (circuit breaker half-open).
  | "unavailable"    // Circuit breaker open. Requests are rejected without attempting.
  | "disconnecting"; // Graceful disconnect in progress.

/** Result of a health check probe. */
interface HealthCheckResult {
  /** Whether the service is healthy. */
  healthy: boolean;

  /** Human-readable status message. */
  message: string;

  /** Time taken for the health check in milliseconds. */
  latencyMs: number;

  /** Optional metadata (e.g. service version, region, rate limit remaining). */
  metadata?: Record<string, string | number | boolean>;
}
```

### 2.2 Adapter State Machine

```
                          connect()
  ┌──────────────┐  ──────────────────>  ┌──────────────┐
  │ disconnected │                       │  connecting   │
  └──────────────┘  <──────────────────  └──────────────┘
        ^              connection failed        │
        │              (retries exhausted)      │ connection
        │                                      │ succeeded
        │                                      v
        │          disconnect()          ┌──────────────┐
        │  <───────────────────────────  │  connected   │
        │                                └──────────────┘
        │                                  │         ^
        │                   failures       │         │ health check
        │                   exceed         │         │ passes
        │                   threshold      v         │
        │          disconnect()          ┌──────────────┐
        │  <───────────────────────────  │ unavailable  │
        │                                └──────────────┘
        │                                  │         ^
        │                   cooldown       │         │ probe
        │                   expires        │         │ fails
        │                                  v         │
        │          disconnect()          ┌──────────────┐
        └──────────────────────────────  │  degraded    │
                                         └──────────────┘
```

State transitions:

| From | To | Trigger |
|------|----|---------|
| `disconnected` | `connecting` | `connect()` called |
| `connecting` | `connected` | Connection established successfully |
| `connecting` | `disconnected` | Connection failed after all retries |
| `connected` | `unavailable` | Consecutive failures exceed `circuitBreakerThreshold` |
| `unavailable` | `degraded` | `circuitBreakerCooldownMs` elapsed; next request is a probe |
| `degraded` | `connected` | Probe request succeeds |
| `degraded` | `unavailable` | Probe request fails |
| Any state | `disconnecting` | `disconnect()` called |
| `disconnecting` | `disconnected` | Disconnect complete |

### 2.3 Health Check Integration

Adapters register with the platform health check system (F1.7). The aggregate health endpoint includes each registered adapter:

```json
{
  "status": "degraded",
  "subsystems": {
    "database": { "healthy": true, "latencyMs": 2 },
    "microsoft-graph": { "healthy": false, "message": "Circuit breaker open", "latencyMs": 0 },
    "anthropic": { "healthy": true, "latencyMs": 145 }
  }
}
```

### 2.4 Default Configuration Values

| Field | Default | Notes |
|-------|---------|-------|
| `connectTimeoutMs` | `10000` (10s) | |
| `requestTimeoutMs` | `30000` (30s) | |
| `maxRetries` | `3` | |
| `retryBaseDelayMs` | `1000` (1s) | |
| `retryMaxDelayMs` | `30000` (30s) | |
| `circuitBreakerThreshold` | `5` | |
| `circuitBreakerCooldownMs` | `60000` (60s) | |
| `healthCheckTimeoutMs` | `5000` (5s) | |

---

## 3. OAuth 2.0 Support

loke provides a reusable OAuth 2.0 authorisation code grant flow with PKCE (Proof Key for Code Exchange). Any integration adapter that needs OAuth can use this module rather than implementing its own flow.

### 3.1 Supported Grant Type

**Authorisation code grant with PKCE** (RFC 7636). This is the recommended flow for native/desktop applications. The implicit grant and resource owner password grant are not supported.

### 3.2 OAuth Flow

```
 ┌──────────┐                                      ┌───────────────┐
 │  loke    │                                      │  Auth Server  │
 │  (local) │                                      │  (external)   │
 └────┬─────┘                                      └───────┬───────┘
      │                                                    │
      │  1. Generate code_verifier (random 43-128 chars)   │
      │  2. Compute code_challenge = BASE64URL(SHA256(     │
      │     code_verifier))                                │
      │  3. Generate state (random, CSRF protection)       │
      │                                                    │
      │  4. Open browser to authorise URL                  │
      │  ─────────────────────────────────────────────────>│
      │     GET /authorize                                 │
      │       ?response_type=code                          │
      │       &client_id=...                               │
      │       &redirect_uri=http://localhost:{port}/callback│
      │       &scope=...                                   │
      │       &state={state}                               │
      │       &code_challenge={code_challenge}             │
      │       &code_challenge_method=S256                  │
      │                                                    │
      │                        5. User authenticates       │
      │                           and consents             │
      │                                                    │
      │  6. Redirect to localhost with authorisation code  │
      │  <─────────────────────────────────────────────────│
      │     GET /callback?code={code}&state={state}        │
      │                                                    │
      │  7. Verify state matches                           │
      │  8. Exchange code for tokens                       │
      │  ─────────────────────────────────────────────────>│
      │     POST /token                                    │
      │       grant_type=authorization_code                │
      │       &code={code}                                 │
      │       &redirect_uri=...                            │
      │       &client_id=...                               │
      │       &code_verifier={code_verifier}               │
      │                                                    │
      │  9. Receive tokens                                 │
      │  <─────────────────────────────────────────────────│
      │     { access_token, refresh_token, expires_in }    │
      │                                                    │
      │  10. Store tokens in OS keychain                   │
      │  11. Close temporary HTTP listener                 │
      │                                                    │
```

### 3.3 Token Storage

Tokens are stored in the OS credential store, never in plaintext files:

| Platform | Store | Library |
|----------|-------|---------|
| macOS | Keychain | `keytar` or `@aspect-build/macos-keychain` |
| Windows | Windows Credential Manager | `keytar` |
| Linux | libsecret (GNOME Keyring / KWallet) | `keytar` |

Storage schema:

| Key | Value |
|-----|-------|
| `loke.oauth.{adapter_id}.access_token` | The access token |
| `loke.oauth.{adapter_id}.refresh_token` | The refresh token |
| `loke.oauth.{adapter_id}.expires_at` | ISO 8601 timestamp of access token expiry |
| `loke.oauth.{adapter_id}.scope` | Granted scopes (space-separated) |

### 3.4 Token Lifecycle

```typescript
/**
 * OAuth 2.0 token manager. One instance per adapter that uses OAuth.
 */
interface OAuthTokenManager {
  /**
   * Initiate the authorisation code flow.
   * Opens the user's browser, starts a temporary local HTTP listener for the callback,
   * exchanges the code for tokens, and stores them in the OS keychain.
   *
   * @throws OAuthError if the flow fails (user denied, network error, invalid response)
   */
  authorise(config: OAuthConfig): Promise<OAuthTokenSet>;

  /**
   * Get a valid access token. Refreshes automatically if expired or about to expire.
   * Returns null if no tokens are stored (user has not authorised).
   *
   * @throws OAuthError if refresh fails and no valid token is available
   */
  getAccessToken(): Promise<string | null>;

  /**
   * Revoke all stored tokens and remove them from the keychain.
   */
  revoke(): Promise<void>;

  /**
   * Check whether valid tokens exist (authorised and not permanently expired).
   */
  isAuthorised(): Promise<boolean>;
}

interface OAuthConfig {
  /** OAuth client ID (registered with the provider). */
  clientId: string;

  /** Authorisation endpoint URL. */
  authoriseUrl: string;

  /** Token endpoint URL. */
  tokenUrl: string;

  /** Requested scopes. */
  scopes: string[];

  /** Optional: revocation endpoint URL. */
  revokeUrl?: string;

  /** Port for the localhost callback listener. Default: dynamically assigned. */
  callbackPort?: number;
}

interface OAuthTokenSet {
  accessToken: string;
  refreshToken: string | null;
  expiresAt: Date;
  scopes: string[];
}
```

### 3.5 Automatic Refresh

The token manager refreshes the access token automatically:

1. When `getAccessToken()` is called and the stored token expires within 5 minutes (the refresh buffer).
2. A single refresh attempt is made using the stored refresh token.
3. If the refresh succeeds, the new tokens replace the old ones in the keychain.
4. If the refresh fails with a `4xx` error (invalid grant), the stored tokens are cleared and `getAccessToken()` returns `null`. The adapter transitions to `disconnected` state and the user must re-authorise.
5. If the refresh fails with a transient error (network, 5xx), the stale access token is returned if it has not yet expired. A warning is logged.

### 3.6 Security Considerations

- **PKCE is mandatory.** The `code_challenge_method` is always `S256`. The `plain` method is not supported.
- **State parameter is mandatory.** A cryptographically random state is generated for every authorisation request and verified on callback. Mismatched state values cause the flow to fail.
- **Redirect URI is always localhost.** The callback listener runs on `http://localhost:{port}/callback`. No external redirect URIs.
- **Temporary listener.** The localhost HTTP listener starts immediately before opening the browser and shuts down immediately after receiving the callback (or after a 120-second timeout).
- **No client secrets.** Public clients (native apps) do not use client secrets. PKCE replaces the client secret for code exchange security.

---

## 4. Base HTTP Client

The base HTTP client provides the infrastructure layer for all outbound HTTP requests. All integration adapters use this client rather than calling `fetch()` directly.

### 4.1 Configuration

```typescript
interface HttpClientConfig {
  /** Base URL for all requests (e.g. "https://api.example.com/v1"). */
  baseUrl: string;

  /** Default request timeout in milliseconds. Per-request override available. */
  timeoutMs: number;

  /** Maximum number of retry attempts for retryable failures. */
  maxRetries: number;

  /** Base delay in milliseconds for exponential backoff. */
  retryBaseDelayMs: number;

  /** Maximum delay in milliseconds for exponential backoff cap. */
  retryMaxDelayMs: number;

  /** Number of consecutive failures before the circuit breaker opens. */
  circuitBreakerThreshold: number;

  /** Time in milliseconds before a tripped circuit breaker enters half-open. */
  circuitBreakerCooldownMs: number;

  /** Default headers applied to every request. */
  defaultHeaders?: Record<string, string>;

  /** Optional: function to provide an Authorization header (e.g. from OAuthTokenManager). */
  authProvider?: () => Promise<string | null>;
}
```

### 4.2 Retry with Exponential Backoff

Retries are attempted for transient failures only:

| Retryable | Not retryable |
|-----------|---------------|
| Network errors (ECONNREFUSED, ECONNRESET, ETIMEDOUT) | 4xx responses (except 429) |
| 5xx responses (500, 502, 503, 504) | 400 Bad Request |
| 429 Too Many Requests (with Retry-After) | 401 Unauthorised |
| Request timeout | 403 Forbidden |
| | 404 Not Found |
| | 409 Conflict |

#### 4.2.1 Backoff Formula

```
delay = min(retryBaseDelayMs * 2^(attempt - 1) + jitter, retryMaxDelayMs)
```

Where:

- `attempt` is 1-indexed (first retry is attempt 1).
- `jitter` is a random value between 0 and `retryBaseDelayMs` (full jitter). This prevents thundering herd when multiple clients retry simultaneously.
- The delay is capped at `retryMaxDelayMs`.

Example with `retryBaseDelayMs = 1000` and `retryMaxDelayMs = 30000`:

| Attempt | Base delay | Range with jitter |
|---------|------------|-------------------|
| 1 | 1000ms | 1000-2000ms |
| 2 | 2000ms | 2000-3000ms |
| 3 | 4000ms | 4000-5000ms |
| 4 | 8000ms | 8000-9000ms |
| 5 | 16000ms | 16000-17000ms |
| 6 | 30000ms (capped) | 30000-31000ms |

#### 4.2.2 Retry-After Awareness

When a 429 or 503 response includes a `Retry-After` header, the client respects it:

- If `Retry-After` is a number of seconds, the client waits that long before the next attempt.
- If `Retry-After` is an HTTP-date, the client computes the delay from now.
- The `Retry-After` value overrides the exponential backoff calculation for that attempt.
- If the `Retry-After` value exceeds `retryMaxDelayMs`, the client waits for the `Retry-After` duration anyway (the server's instruction takes precedence over the local cap).

### 4.3 Circuit Breaker

The circuit breaker prevents repeated requests to a service that is down, reducing latency for the caller and load on the failing service.

#### 4.3.1 State Machine

```
                    failure count
                    exceeds threshold
  ┌────────┐  ─────────────────────────>  ┌────────┐
  │ CLOSED │                              │  OPEN  │
  └────────┘  <─────────────────────────  └────────┘
       ^         probe succeeds                │
       │                                       │ cooldown
       │         probe fails                   │ expires
       │      ┌──────────────┐                 │
       │      │              v                 v
       │      │         ┌───────────┐
       └──────┘         │ HALF-OPEN │
                        └───────────┘
```

| State | Behaviour |
|-------|-----------|
| **CLOSED** | Normal operation. Requests pass through. Consecutive failure count is tracked. |
| **OPEN** | All requests are immediately rejected with a `CircuitBreakerOpenError` without making a network call. The adapter state is `unavailable`. |
| **HALF-OPEN** | A single probe request is allowed through. If it succeeds, the breaker transitions to CLOSED and the failure count resets. If it fails, the breaker returns to OPEN and the cooldown timer restarts. |

#### 4.3.2 Failure Counting

- Only responses classified as retryable failures (section 4.2) increment the failure counter.
- A successful response resets the failure counter to zero.
- The failure counter is per-client-instance (not global).

### 4.4 Request and Response Logging

The HTTP client logs every request and response at `debug` level:

**Logged (headers only):**

- Request: method, URL, non-sensitive headers (Content-Type, Accept, User-Agent, X-Request-ID)
- Response: status code, non-sensitive headers (Content-Type, X-RateLimit-Remaining, Retry-After)
- Duration in milliseconds
- Retry attempt number (if retrying)
- Circuit breaker state transitions

**Never logged:**

- Request bodies (may contain user data)
- Response bodies (may contain user data)
- Authorization header values (tokens, API keys)
- Cookie values

Sensitive headers are redacted in log output:

```
Authorization: [REDACTED]
X-Api-Key: [REDACTED]
Cookie: [REDACTED]
Set-Cookie: [REDACTED]
```

---

## 5. Input Sanitisation Utilities

loke provides a set of sanitisation functions that all platform code and applications should use. These are defence-in-depth measures — they supplement, not replace, the primary defences (parameterised queries, Content Security Policy, structured logging).

### 5.1 Function Signatures

```typescript
/**
 * Strip all HTML tags from a string. Returns plain text.
 * Handles nested tags, self-closing tags, HTML comments, and script/style blocks.
 * Does not decode HTML entities (use a separate decoder if needed).
 *
 * @param input - The string that may contain HTML
 * @returns The string with all HTML tags removed
 */
function stripHtml(input: string): string;

/**
 * Escape special SQL characters as a defence-in-depth supplement
 * to parameterised queries. This is NOT a substitute for parameterised
 * queries — it is an additional safety net for values that pass through
 * logging, display, or other non-query paths.
 *
 * Escapes: ' -> '' , \ -> \\ , NUL -> (removed)
 *
 * @param input - The string to escape
 * @returns The escaped string
 */
function escapeSql(input: string): string;

/**
 * Prevent log injection by removing or escaping control characters
 * that could forge log entries or corrupt log parsers.
 *
 * Removes/escapes: newlines (\n, \r), tabs (\t), null bytes,
 * ANSI escape sequences, Unicode bidirectional override characters.
 *
 * @param input - The string to sanitise for safe log inclusion
 * @returns The sanitised string
 */
function sanitiseForLog(input: string): string;

/**
 * Validate input against a Zod schema and strip unknown properties.
 * Returns the validated, stripped object or throws a ValidationError
 * with structured details of all validation failures.
 *
 * Uses Zod's .strict() parsing internally — unknown properties are
 * silently removed, not rejected.
 *
 * @param schema - The Zod schema to validate against
 * @param input - The input data to validate
 * @returns The validated, type-safe object with unknown properties stripped
 * @throws ValidationError with structured field-level error details
 */
function validateAndStrip<T>(schema: ZodSchema<T>, input: unknown): T;
```

### 5.2 HTML Stripping

The `stripHtml` function removes all HTML markup, leaving only text content:

```typescript
stripHtml("<p>Hello <b>world</b></p>");
// => "Hello world"

stripHtml('<script>alert("xss")</script>Safe text');
// => "Safe text"

stripHtml("<!-- comment -->Visible");
// => "Visible"

stripHtml("No HTML here");
// => "No HTML here"
```

Implementation notes:

- Uses a parser-based approach, not regex. Regex-based HTML stripping is unreliable for malformed markup.
- Removes content within `<script>` and `<style>` blocks entirely (not just the tags).
- Preserves whitespace that was between tags as a single space.
- Returns the input unchanged if no HTML is detected.

### 5.3 SQL Escape

The `escapeSql` function is a supplementary defence, not a primary one:

```typescript
escapeSql("O'Brien");
// => "O''Brien"

escapeSql("value\\with\\backslashes");
// => "value\\\\with\\\\backslashes"

escapeSql("normal text");
// => "normal text"
```

This function exists for cases where a value is used in a context other than a parameterised query — for example, when displaying a value in an error message that might be interpolated into SQL by a downstream system. All direct database queries in loke use parameterised queries (R3.7).

### 5.4 Log Injection Prevention

The `sanitiseForLog` function prevents attackers from forging log entries:

```typescript
sanitiseForLog("Normal log message");
// => "Normal log message"

sanitiseForLog("Legit entry\n[ERROR] Forged entry");
// => "Legit entry [ERROR] Forged entry"

sanitiseForLog("User input with \x1b[31mANSI\x1b[0m codes");
// => "User input with ANSI codes"

sanitiseForLog("Contains\x00null\x00bytes");
// => "Containsnullbytes"
```

Characters handled:

| Character | Treatment |
|-----------|-----------|
| `\n` (newline) | Replaced with space |
| `\r` (carriage return) | Removed |
| `\t` (tab) | Replaced with space |
| `\x00` (null byte) | Removed |
| ANSI escape sequences (`\x1b[...`) | Removed |
| Unicode BiDi overrides (U+202A-U+202E, U+2066-U+2069) | Removed |

### 5.5 Schema Validation with Unknown Stripping

The `validateAndStrip` function combines Zod schema validation with automatic removal of unexpected properties:

```typescript
import { z } from "zod";

const UserInput = z.object({
  name: z.string().min(1).max(200),
  email: z.string().email(),
  age: z.number().int().min(0).max(150),
});

// Valid input with extra properties
validateAndStrip(UserInput, {
  name: "Alice",
  email: "alice@example.com",
  age: 30,
  __proto__: { admin: true },   // stripped
  constructor: "evil",           // stripped
  extraField: "ignored",         // stripped
});
// => { name: "Alice", email: "alice@example.com", age: 30 }

// Invalid input
validateAndStrip(UserInput, { name: "", email: "not-an-email" });
// throws ValidationError with:
// [
//   { field: "name", message: "String must contain at least 1 character(s)" },
//   { field: "email", message: "Invalid email" },
//   { field: "age", message: "Required" },
// ]
```

This function is used by the request validation middleware (P1.4) and should be used by application code whenever processing external input.

---

## 6. Integration with Other Platform Systems

### 6.1 Startup and Shutdown

During the startup sequence (F1.6), adapters that are configured for auto-connect are initialised after the server starts. Adapter initialisation is non-blocking — a failing adapter does not prevent the server from starting.

During graceful shutdown (F1.6), all connected adapters receive `disconnect()`. The shutdown sequence waits up to the configured timeout for adapters to complete in-flight requests before forcing closure.

### 6.2 Plugin Registration

Applications register their adapters during plugin registration (P2.1):

```typescript
// In application plugin setup
plugin.registerAdapter(new CalendarAdapter(calendarConfig));
plugin.registerAdapter(new CrmAdapter(crmConfig));
```

Registered adapters are automatically:

- Included in the health check endpoint (F1.7)
- Disconnected during graceful shutdown
- Displayed in the settings UI integration status section (P3.9)

### 6.3 Offline Queueing

When an adapter's circuit breaker is open, write operations can be queued via the persistent sync queue (F6.6). The queue replays operations when the adapter transitions back to `connected` state. Applications configure which operations are queueable during adapter registration.

### 6.4 Credential Storage

OAuth tokens are stored via the same credential store abstraction used by the configuration system (F1.5). API keys configured in application settings are stored in the OS keychain, not in plaintext configuration files.

### 6.5 Error Handling

Adapter errors are wrapped in typed error classes that integrate with the error handling framework (P6):

```typescript
class AdapterConnectionError extends Error {
  constructor(
    public readonly adapterId: string,
    public readonly cause: Error,
    public readonly retriesAttempted: number,
  ) {
    super(`Adapter "${adapterId}" connection failed after ${retriesAttempted} attempts`);
  }
}

class CircuitBreakerOpenError extends Error {
  constructor(
    public readonly adapterId: string,
    public readonly cooldownRemainingMs: number,
  ) {
    super(`Adapter "${adapterId}" circuit breaker is open`);
  }
}

class OAuthError extends Error {
  constructor(
    public readonly adapterId: string,
    public readonly oauthErrorCode: string,
    public readonly oauthErrorDescription?: string,
  ) {
    super(`OAuth error for "${adapterId}": ${oauthErrorCode}`);
  }
}
```

---

## 7. Testing

### 7.1 Adapter Test Utilities

The test utilities package (X4.1) provides helpers for testing adapters:

```typescript
// Create a mock HTTP server for adapter tests
const mockServer = createMockServer({
  "GET /api/health": { status: 200, body: { ok: true } },
  "POST /api/data": { status: 500 },  // simulate failure
});

// Create an adapter with the mock server's URL
const adapter = new MyAdapter({ ...config, baseUrl: mockServer.url });
await adapter.connect();

// Assert circuit breaker behaviour
await expectCircuitBreakerOpen(adapter, { afterFailures: 5 });
```

### 7.2 Circuit Breaker Testing

The circuit breaker implementation is tested with deterministic timing (no real timers in tests):

- Verify CLOSED -> OPEN transition after N failures.
- Verify OPEN -> HALF-OPEN transition after cooldown.
- Verify HALF-OPEN -> CLOSED on probe success.
- Verify HALF-OPEN -> OPEN on probe failure.
- Verify failure counter resets on success.

### 7.3 OAuth Flow Testing

The OAuth module is tested with a mock authorisation server:

- Verify PKCE challenge/verifier generation and validation.
- Verify state parameter is checked.
- Verify token exchange and storage.
- Verify automatic refresh on expiry.
- Verify revocation clears stored tokens.
- Verify handling of denied consent, expired codes, and invalid grants.

---

## 8. Security Considerations

- **No body logging.** The HTTP client never logs request or response bodies. Headers that may contain tokens are redacted.
- **PKCE is mandatory.** OAuth flows without PKCE are not supported. This prevents authorisation code interception attacks.
- **OS keychain for tokens.** OAuth tokens and API keys are never stored in plaintext files, environment variables, or the application database.
- **Input sanitisation is defence-in-depth.** The sanitisation functions supplement primary defences (parameterised queries, CSP, structured logging). They do not replace them.
- **Circuit breaker prevents abuse.** When a service is unavailable, the circuit breaker prevents loke from flooding it with requests, which could be interpreted as a denial-of-service attack.
- **Timeout enforcement.** Every outbound request has a timeout. No request can hang indefinitely.
