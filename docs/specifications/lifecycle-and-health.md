# Lifecycle and Health Check Specification

**Stories:** F1.6 — Ordered startup and graceful shutdown, F1.7 — Health check system
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke follows a deterministic startup sequence, a structured shutdown procedure, and a continuous health check system. Together these ensure the application reaches a known-good state before serving requests, shuts down without data loss or corruption, and provides ongoing visibility into subsystem readiness.

This specification defines:

- The ordered startup sequence and its failure semantics
- Graceful shutdown: signal handling, request draining, and cleanup
- The health check system: subsystem probes, aggregate endpoint, readiness vs liveness
- Extension points for applications to participate in the lifecycle
- CLI integration for scripting and diagnostics
- Error scenarios and recovery behaviour

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Do the right thing by default.** The startup sequence validates everything before accepting traffic. No requests are served until all critical subsystems are confirmed healthy.
- **Graceful degradation.** Non-critical subsystem failures during startup produce warnings but do not prevent the application from starting. Health checks distinguish between degraded and failed states.
- **Auditable.** Every lifecycle event is logged with structured metadata. Startup timing, shutdown reason, and health state transitions are all observable.
- **Privacy is the foundation.** Health check responses never include sensitive configuration values, connection strings, or credentials.

### 1.2 Requirements Traceability

| Requirement | Coverage |
|-------------|----------|
| R1.4 — Health check system | Sections 4, 5, 6 |
| R1.5 — Ordered startup sequence | Section 2 |
| R1.6 — Graceful shutdown | Section 3 |
| R1.7 — CLI interface | Section 6 |

---

## 2. Startup Sequence

### 2.1 Boot Order

The startup sequence executes in a fixed order. Each step must complete successfully before the next begins. The sequence is not configurable — applications extend it via hooks (section 5) but cannot reorder or remove platform steps.

```
 Step   Phase              Critical?   Description
 ────   ─────              ─────────   ───────────
  1     validate-config    Yes         Load and validate configuration against schema
  2     init-logger        Yes         Initialise structured logger
  3     open-database      Yes         Open SQLite connection, verify integrity
  4     run-migrations     Yes         Execute pending database migrations
  5     load-settings      Yes         Load settings from database into memory
  6     load-locale        No          Load locale files for configured language
  7     register-routes    Yes         Register platform and application routes
  8     start-server       Yes         Bind to configured host:port
  9     run-health-check   No          Execute all registered health probes
 10     log-summary        No          Log startup summary with timing
```

### 2.2 Startup Sequence Diagram

```
┌─────────────────────────────────────────────────────────┐
│                    PROCESS START                         │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
              ┌─────────────────┐
              │ validate-config │──── FAIL ──── exit(10)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │  init-logger    │──── FAIL ──── exit(11)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │ open-database   │──── FAIL ──── exit(12)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │ run-migrations  │──── FAIL ──── exit(13)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │ load-settings   │──── FAIL ──── exit(14)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │  load-locale    │──── FAIL ──── warn, continue with base locale
              └────────┬────────┘
                       │ OK / warned
                       ▼
           ┌────────────────────────┐
           │ onBeforeStart hooks    │──── FAIL ──── exit(15)
           └───────────┬────────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │ register-routes │──── FAIL ──── exit(16)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │  start-server   │──── FAIL ──── exit(17)
              └────────┬────────┘
                       │ OK
                       ▼
              ┌─────────────────┐
              │ run-health-check│──── FAIL ──── warn, mark degraded
              └────────┬────────┘
                       │ OK / warned
                       ▼
           ┌────────────────────────┐
           │ onAfterStart hooks     │──── FAIL ──── warn, mark degraded
           └───────────┬────────────┘
                       │ OK / warned
                       ▼
              ┌─────────────────┐
              │  log-summary    │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     READY       │
              └─────────────────┘
```

### 2.3 Step Definitions

#### Step 1: validate-config

Load configuration from environment files, CLI arguments, and environment variables. Validate all values against the combined Zod schema (platform schema merged with application-provided schema extensions per P2.3). Produce a typed, immutable configuration object. If validation fails, log every validation error and exit immediately — the logger may not be initialised yet, so validation errors are written to stderr.

#### Step 2: init-logger

Initialise the structured JSON logger with the log level and output format specified in configuration. From this point forward, all lifecycle events are logged through the structured logger with a `lifecycle` child logger context.

Log entry:

```json
{
  "level": "info",
  "context": "lifecycle",
  "event": "step_complete",
  "step": "init-logger",
  "step_number": 2,
  "elapsed_ms": 3
}
```

#### Step 3: open-database

Open the SQLite database connection. Create the data directory if it does not exist (R3.6). Enable WAL mode, foreign key enforcement, and the configured busy timeout. Verify database integrity with a `PRAGMA integrity_check` on first open after application update (version change detected).

#### Step 4: run-migrations

Execute pending numbered migrations in order. Each migration runs within its own transaction. Checksum verification is applied to all previously-run migrations — if a historical migration has been tampered with, the startup aborts. Application migration directories (per F6.1) are interleaved with platform migrations by sequence number.

#### Step 5: load-settings

Load the namespaced settings store (F6.7) into memory. Platform settings (`loke.*` prefix) and application settings are loaded together. Missing required settings with defined defaults are initialised to their default values.

#### Step 6: load-locale

Load locale files for the configured language (P4.1). If the configured locale is unavailable, fall back to the base locale (`en`) and log a warning. This step is non-critical — the application can operate with the base locale.

#### Step 7: register-routes

Register all platform API routes under `/api/v1/`. Execute application route registration (P2.1). Assemble the middleware pipeline in enforced order (P1.3). Validate that no route conflicts exist (duplicate method + path combinations).

#### Step 8: start-server

Bind the HTTP server to the configured `host:port`. If the port is already in use, log the conflict and exit. The server begins accepting connections only after this step completes.

#### Step 9: run-health-check

Execute all registered health probes (section 4). This establishes the initial health baseline. Failures at this step are non-critical — they produce warnings and set the aggregate status to `degraded`. The application still starts and begins serving requests.

#### Step 10: log-summary

Log a startup summary including:

```json
{
  "level": "info",
  "context": "lifecycle",
  "event": "startup_complete",
  "status": "ready",
  "total_elapsed_ms": 847,
  "steps": {
    "validate-config": 12,
    "init-logger": 3,
    "open-database": 45,
    "run-migrations": 210,
    "load-settings": 8,
    "load-locale": 15,
    "register-routes": 22,
    "start-server": 18,
    "run-health-check": 502,
    "log-summary": 1
  },
  "server": {
    "host": "localhost",
    "port": 3000,
    "url": "http://localhost:3000"
  },
  "health": {
    "status": "healthy",
    "degraded_subsystems": []
  },
  "warnings": []
}
```

### 2.4 Startup Timing

The non-functional requirement is a total startup time of less than 3 seconds to ready state (section 8, platform requirements). Each step records its own elapsed time. If total startup exceeds 3 seconds, a warning is logged identifying the slowest steps.

### 2.5 Critical vs Non-Critical Steps

| Criticality | Behaviour on failure | Steps |
|-------------|---------------------|-------|
| Critical | Log error, exit immediately with step-specific exit code | validate-config, init-logger, open-database, run-migrations, load-settings, register-routes, start-server |
| Non-critical | Log warning, continue with degraded state | load-locale, run-health-check, log-summary |

Application-registered `onBeforeStart` hooks are critical by default. Application-registered `onAfterStart` hooks are non-critical by default. Applications may override this when registering hooks (section 5.2).

---

## 3. Graceful Shutdown

### 3.1 Signal Handling

loke handles the following process signals:

| Signal | Source | Behaviour |
|--------|--------|-----------|
| `SIGTERM` | Container orchestrator, `kill`, systemd | Begin graceful shutdown |
| `SIGINT` | Ctrl+C in terminal | Begin graceful shutdown |
| `SIGQUIT` | Ctrl+\\ in terminal | Begin graceful shutdown (same as SIGTERM) |
| `SIGHUP` | Terminal hangup | Ignored (process continues running) |

Duplicate signals during an in-progress shutdown are ignored except for a second `SIGINT` or `SIGTERM` received after the drain timeout has expired, which forces an immediate exit with code 1.

### 3.2 Signal Handling Behaviour Matrix

| State | Signal received | Action |
|-------|-----------------|--------|
| Running | SIGTERM | Begin graceful shutdown |
| Running | SIGINT | Begin graceful shutdown |
| Running | SIGHUP | Ignore |
| Shutting down (within timeout) | SIGTERM | Log "shutdown already in progress", ignore |
| Shutting down (within timeout) | SIGINT | Log "shutdown already in progress", ignore |
| Shutting down (timeout expired) | SIGTERM | Force exit(1) |
| Shutting down (timeout expired) | SIGINT | Force exit(1) |
| Starting up (before server) | SIGTERM | Abort startup, exit(130) |
| Starting up (before server) | SIGINT | Abort startup, exit(130) |

### 3.3 Shutdown Sequence

When a shutdown signal is received, the following sequence executes:

```
 Step   Phase                     Timeout    Description
 ────   ─────                     ───────    ───────────
  1     Stop accepting            Immediate  Server stops accepting new connections
  2     onBeforeShutdown hooks    5s each    Application cleanup callbacks
  3     Drain in-flight requests  Remaining  Wait for active requests to complete
  4     Close database            2s         Close SQLite connection cleanly
  5     Flush logs                1s         Ensure all log entries are written
  6     Exit                      Immediate  Process exit with code 0
```

### 3.4 Drain Timeout

The total shutdown timeout is configurable:

| Setting | Key | Type | Default | Range |
|---------|-----|------|---------|-------|
| Shutdown timeout | `loke.shutdown.timeout_ms` | integer | `10000` | 1000–60000 |

The timeout begins when the first shutdown signal is received. All shutdown steps must complete within this window. If the timeout expires before completion:

1. Log a warning listing any still-active connections and incomplete hooks.
2. Force-close all remaining connections.
3. Exit with code 1 (unclean shutdown).

### 3.5 Request Draining

When shutdown begins:

1. The server immediately stops accepting new TCP connections.
2. New requests on existing keep-alive connections receive a `503 Service Unavailable` response with a `Connection: close` header and a `Retry-After: 5` header.
3. In-flight requests are allowed to complete naturally within the remaining drain window.
4. If a request is still in-flight when the drain window expires, the connection is forcibly closed and a warning is logged with the request's correlation ID.

### 3.6 Database Connection Cleanup

Before closing the database connection:

1. Wait for any in-progress write transactions to complete (bounded by drain timeout).
2. Run `PRAGMA wal_checkpoint(TRUNCATE)` to ensure WAL is flushed.
3. Close the connection.

If the checkpoint or close fails, log the error but continue with shutdown. Database corruption recovery is handled on the next startup via integrity check.

### 3.7 Log Flushing

All buffered log entries are flushed to their configured outputs (file, stdout). The flush operation is bounded by a 1-second internal timeout. If flushing takes longer, the remaining entries are lost and a final stderr message records the number of dropped log entries.

### 3.8 Shutdown Logging

The shutdown sequence logs:

```json
{
  "level": "info",
  "context": "lifecycle",
  "event": "shutdown_initiated",
  "signal": "SIGTERM",
  "timeout_ms": 10000,
  "active_connections": 3,
  "in_flight_requests": 1
}
```

On completion:

```json
{
  "level": "info",
  "context": "lifecycle",
  "event": "shutdown_complete",
  "total_elapsed_ms": 1250,
  "drained_requests": 1,
  "forced_closes": 0,
  "exit_code": 0
}
```

---

## 4. Health Check System

### 4.1 Health Model

The health system distinguishes between two probe types:

| Probe type | Purpose | Failure meaning |
|------------|---------|-----------------|
| **Liveness** | Is the process running and able to respond? | Process should be restarted |
| **Readiness** | Is the application ready to serve user requests? | Traffic should not be routed to this instance |

In loke's local-first context (single process, single user), both probes serve diagnostics and CLI tooling rather than orchestrator routing. However, the distinction is maintained for correctness and forward compatibility.

### 4.2 Subsystem Probes

Each subsystem registers a health probe that returns a status and optional metadata. The platform ships with the following built-in probes:

| Probe | Subsystem | Check | Critical | Timeout |
|-------|-----------|-------|----------|---------|
| `database` | SQLite | Execute `SELECT 1`, verify WAL mode active | Yes | 1000ms |
| `ollama` | Local models | HTTP GET to Ollama API `/api/version` | No | 3000ms |
| `providers` | LLM providers | Verify API key presence and format per configured provider | No | 2000ms |
| `mcp_servers` | MCP | Ping each configured MCP server | No | 3000ms |
| `companion_devices` | Companion | Heartbeat check on paired devices | No | 5000ms |

**Critical probes** affect the aggregate `readiness` status. If any critical probe fails, the application reports as not ready. **Non-critical probes** can fail without affecting readiness — they only affect the aggregate `status` field (healthy vs degraded).

### 4.3 Probe Status Values

Each probe returns one of three status values:

| Status | Meaning |
|--------|---------|
| `healthy` | Subsystem is functioning normally |
| `degraded` | Subsystem is partially functional or slow (responded but with warnings) |
| `unhealthy` | Subsystem is not functional (failed to respond or returned an error) |

### 4.4 Aggregate Status

The aggregate status is derived from individual probe results:

| Condition | Aggregate status |
|-----------|-----------------|
| All probes healthy | `healthy` |
| All critical probes healthy, one or more non-critical probes degraded or unhealthy | `degraded` |
| Any critical probe degraded | `degraded` |
| Any critical probe unhealthy | `unhealthy` |

### 4.5 Health Endpoint

The health system exposes a single aggregate endpoint:

```
GET /health
```

This endpoint is not versioned (not under `/api/v1/`) because it is infrastructure, not application API. It is exempt from authentication middleware.

#### Response: healthy

```
HTTP/1.1 200 OK
Content-Type: application/json
Cache-Control: no-store
```

```json
{
  "status": "healthy",
  "ready": true,
  "uptime_seconds": 3847,
  "version": "0.2.0",
  "timestamp": "2026-04-05T10:23:45.123Z",
  "probes": {
    "database": {
      "status": "healthy",
      "latency_ms": 2,
      "message": null
    },
    "ollama": {
      "status": "healthy",
      "latency_ms": 45,
      "message": "v0.6.2"
    },
    "providers": {
      "status": "healthy",
      "latency_ms": 1,
      "message": "2 providers configured"
    },
    "mcp_servers": {
      "status": "healthy",
      "latency_ms": 120,
      "message": "1 server connected"
    },
    "companion_devices": {
      "status": "healthy",
      "latency_ms": 15,
      "message": "0 devices paired"
    }
  }
}
```

#### Response: degraded

```
HTTP/1.1 200 OK
```

```json
{
  "status": "degraded",
  "ready": true,
  "uptime_seconds": 3847,
  "version": "0.2.0",
  "timestamp": "2026-04-05T10:23:45.123Z",
  "probes": {
    "database": {
      "status": "healthy",
      "latency_ms": 2,
      "message": null
    },
    "ollama": {
      "status": "unhealthy",
      "latency_ms": 3001,
      "message": "Connection refused at localhost:11434"
    }
  }
}
```

The HTTP status code is always `200` when the process is alive and able to respond. The `status` field in the body communicates health. This follows the convention that the liveness probe (HTTP-level) and the readiness probe (body-level) are distinct:

| Aggregate status | HTTP status | `ready` field |
|------------------|-------------|---------------|
| `healthy` | 200 | `true` |
| `degraded` | 200 | `true` (if only non-critical probes are degraded/unhealthy) |
| `degraded` | 200 | `false` (if any critical probe is degraded) |
| `unhealthy` | 200 | `false` |
| Process not responding | No response (connection refused) | N/A |

A `503` is only returned during shutdown (section 3.5), not for health degradation.

### 4.6 Health Check Response JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["status", "ready", "uptime_seconds", "version", "timestamp", "probes"],
  "additionalProperties": false,
  "properties": {
    "status": {
      "type": "string",
      "enum": ["healthy", "degraded", "unhealthy"],
      "description": "Aggregate health status"
    },
    "ready": {
      "type": "boolean",
      "description": "Whether the application is ready to serve user requests"
    },
    "uptime_seconds": {
      "type": "integer",
      "minimum": 0,
      "description": "Seconds since the application reached ready state"
    },
    "version": {
      "type": "string",
      "description": "Application version (semver)"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "description": "ISO 8601 timestamp of this health check"
    },
    "probes": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["status", "latency_ms", "message"],
        "additionalProperties": false,
        "properties": {
          "status": {
            "type": "string",
            "enum": ["healthy", "degraded", "unhealthy"]
          },
          "latency_ms": {
            "type": "integer",
            "minimum": 0,
            "description": "Time taken to execute the probe in milliseconds"
          },
          "message": {
            "type": ["string", "null"],
            "description": "Human-readable status detail or error message"
          }
        }
      }
    }
  }
}
```

### 4.7 Probe Execution

Health probes are executed:

- **On startup** — step 9 of the boot sequence (section 2.1)
- **On demand** — when the `/health` endpoint is requested
- **On demand** — when the `loke health` CLI command is run

Probes are executed concurrently with individual timeouts (section 4.2). A probe that exceeds its timeout is reported as `unhealthy` with a message indicating the timeout.

Probes are not executed on a background schedule. There is no periodic health polling. This is a local-first single-process application — health is checked when asked, not speculatively.

### 4.8 Security Considerations

The health endpoint does not expose:

- Connection strings, file paths, or database locations
- API keys, tokens, or credentials (even partially masked)
- Hostnames or IP addresses of configured providers
- Internal error stack traces

The `message` field in each probe result contains only safe diagnostic text: version strings, connection counts, and generic error descriptions (e.g. "Connection refused" not "Connection refused at https://api.openai.com/v1 with key sk-...").

---

## 5. Application Extension

### 5.1 Custom Health Checks

Applications register custom health probes via the plugin registration API (P2.1):

```typescript
interface HealthProbe {
  /** Unique probe name. Must match ^[a-z][a-z0-9_]{0,63}$. */
  name: string;

  /** Human-readable description for CLI output. */
  description: string;

  /** Whether failure affects readiness. Default: false. */
  critical: boolean;

  /** Maximum time to wait for this probe, in milliseconds. Default: 3000. */
  timeout_ms: number;

  /** The check function. Must resolve within timeout_ms. */
  check: () => Promise<HealthProbeResult>;
}

interface HealthProbeResult {
  status: "healthy" | "degraded" | "unhealthy";
  message: string | null;
}
```

Registration:

```typescript
app.registerHealthProbe({
  name: "crm_connection",
  description: "CRM API connectivity",
  critical: false,
  timeout_ms: 5000,
  check: async () => {
    const ok = await crmClient.ping();
    return {
      status: ok ? "healthy" : "unhealthy",
      message: ok ? "Connected" : "CRM API unreachable",
    };
  },
});
```

Application probes appear alongside platform probes in the `/health` response and `loke health` CLI output. Probe names must be unique — registering a probe with a name that conflicts with a platform probe or another application probe causes a startup error.

### 5.2 Custom Startup Steps

Applications register startup hooks via the lifecycle hook API (P2.2):

```typescript
interface LifecycleHook {
  /** Unique hook name for logging and diagnostics. */
  name: string;

  /** When to run: before server start or after. */
  phase: "onBeforeStart" | "onAfterStart";

  /**
   * Whether failure should abort startup.
   * Default: true for onBeforeStart, false for onAfterStart.
   */
  critical: boolean;

  /** Maximum execution time in milliseconds. Default: 10000. */
  timeout_ms: number;

  /** The hook function. */
  execute: () => Promise<void>;
}
```

Registration:

```typescript
app.registerLifecycleHook({
  name: "seed-default-templates",
  phase: "onBeforeStart",
  critical: true,
  timeout_ms: 5000,
  execute: async () => {
    await templateStore.seedDefaults();
  },
});
```

`onBeforeStart` hooks execute between `load-locale` and `register-routes` (see diagram in section 2.2). `onAfterStart` hooks execute between `run-health-check` and `log-summary`.

Multiple hooks in the same phase execute in registration order. If a critical hook fails, the startup aborts with exit code 15 (for `onBeforeStart`) or logs a degraded warning (for `onAfterStart`).

### 5.3 Custom Shutdown Cleanup

Applications register shutdown hooks via the `onBeforeShutdown` callback (P2.2):

```typescript
app.registerLifecycleHook({
  name: "flush-sync-queue",
  phase: "onBeforeShutdown",
  critical: false,
  timeout_ms: 5000,
  execute: async () => {
    await syncQueue.flushPending();
  },
});
```

Shutdown hooks execute after the server stops accepting connections and before request draining (step 2 of the shutdown sequence, section 3.3). Each hook has an individual timeout. A hook that exceeds its timeout is logged as a warning and skipped — shutdown continues with the remaining steps.

Shutdown hooks execute in reverse registration order (last registered, first executed) to respect dependency ordering.

---

## 6. CLI Integration

### 6.1 `loke health` Command

```
loke health [--json] [--probe <name>]
```

Connects to the running loke instance and retrieves health status. If no instance is running, attempts a cold health check by executing probes directly (database and configuration only — no server-dependent probes).

**Options:**

| Flag | Description |
|------|-------------|
| `--json` | Output raw JSON response (default is human-readable table) |
| `--probe <name>` | Check a single probe by name |

**Human-readable output:**

```
loke health check — v0.2.0
Uptime: 1h 4m 7s

  database           healthy     2ms
  ollama             healthy    45ms   v0.6.2
  providers          healthy     1ms   2 providers configured
  mcp_servers        healthy   120ms   1 server connected
  companion_devices  healthy    15ms   0 devices paired

Status: healthy
Ready:  yes
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| 0 | All probes healthy |
| 1 | One or more probes unhealthy or degraded |
| 2 | Could not connect to loke instance and cold check failed |

### 6.2 `loke doctor` Integration

The `loke doctor` command (A2.5) includes health checks as part of its broader diagnostic sweep. `loke doctor` calls the same health probe infrastructure but adds additional checks not part of the runtime health system:

- Configuration file syntax and schema validation
- File system permissions on data directories
- Port availability
- Ollama installation and model availability
- Node.js version compatibility
- Disk space for database and logs

The health probe results are included in `loke doctor` output under a "Runtime Health" section.

### 6.3 Exit Codes for Scripting

All lifecycle-related exit codes are documented for use in shell scripts, CI pipelines, and monitoring:

| Code | Meaning | Context |
|------|---------|---------|
| 0 | Clean exit | Normal shutdown, healthy health check |
| 1 | General error / unclean shutdown | Shutdown timeout, unhealthy health check, unhandled error |
| 2 | CLI usage error | Invalid arguments, connection failure |
| 10 | Configuration validation failed | Startup step 1 |
| 11 | Logger initialisation failed | Startup step 2 |
| 12 | Database open failed | Startup step 3 |
| 13 | Migration failed | Startup step 4 |
| 14 | Settings load failed | Startup step 5 |
| 15 | Application startup hook failed | onBeforeStart hook |
| 16 | Route registration failed | Startup step 7 |
| 17 | Server bind failed | Startup step 8 |
| 130 | Interrupted during startup | SIGINT/SIGTERM received before ready |

Exit codes 10–17 map directly to startup steps for unambiguous diagnosis. Scripts can check the exit code to determine which step failed without parsing log output:

```bash
loke start
case $? in
  0)  echo "Running" ;;
  12) echo "Database problem — check file permissions" ;;
  13) echo "Migration failed — check migration files" ;;
  17) echo "Port in use — check for other processes" ;;
  *)  echo "Startup failed with code $?" ;;
esac
```

---

## 7. Error Scenarios

### 7.1 Startup Failure at Each Step

| Step | Failure example | Behaviour |
|------|-----------------|-----------|
| validate-config | Missing required field, invalid port number, malformed env file | All validation errors written to stderr (logger not yet available). Exit code 10. |
| init-logger | Log directory not writable, invalid log level | Error to stderr. Exit code 11. |
| open-database | Database file locked by another process, corrupt file, directory not creatable | Logged error. Exit code 12. |
| run-migrations | Checksum mismatch on historical migration, SQL error in new migration | Logged error with migration number and name. Transaction rolled back for the failing migration. Exit code 13. |
| load-settings | Settings table missing (should not happen after successful migrations) | Logged error. Exit code 14. |
| load-locale | Locale file missing for configured language | Warning logged. Falls back to `en` base locale. Startup continues. |
| register-routes | Duplicate route conflict, invalid route pattern | Logged error identifying the conflicting routes. Exit code 16. |
| start-server | Port in use (`EADDRINUSE`), permission denied on privileged port | Logged error with the specific port and conflicting process if detectable. Exit code 17. |
| run-health-check | Database probe fails, Ollama not running | Warning logged per failing probe. Aggregate status set to `degraded`. Startup continues. |

### 7.2 Health Check Failures During Operation

When a health probe fails during normal operation (on a `/health` request or `loke health` CLI call):

- The probe's status is reported as `unhealthy` or `degraded` in the response.
- If a critical probe fails, `ready` is set to `false`.
- No automatic recovery action is taken. loke reports state; it does not attempt to restart subsystems.
- The failure is logged once per state transition (healthy to unhealthy, unhealthy back to healthy) to avoid log flooding.

### 7.3 Shutdown Timeout Exceeded

When the shutdown timeout expires before all steps complete:

1. All remaining shutdown hooks are cancelled.
2. In-flight request connections are forcibly terminated.
3. The database connection is forcibly closed (no WAL checkpoint).
4. A warning is logged listing: incomplete hooks, killed requests (by correlation ID), and whether the database was cleanly closed.
5. The process exits with code 1.

On the next startup, the database integrity check (step 3) will detect any WAL inconsistency and recover automatically (SQLite's built-in recovery mechanism).

### 7.4 Repeated Signal During Shutdown

If a second termination signal is received while shutdown is in progress and within the timeout window, it is ignored with a log message. If a second signal arrives after the timeout has expired, the process exits immediately with code 1.

---

## 8. Configuration Reference

All configuration keys for lifecycle and health:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `loke.shutdown.timeout_ms` | integer | `10000` | Total time allowed for graceful shutdown (1000–60000) |
| `loke.health.probe_timeout_ms` | integer | `3000` | Default timeout for individual health probes (500–30000) |
| `loke.health.database.timeout_ms` | integer | `1000` | Timeout for database probe |
| `loke.health.ollama.timeout_ms` | integer | `3000` | Timeout for Ollama probe |
| `loke.health.ollama.url` | string | `http://localhost:11434` | Ollama API base URL |
| `loke.health.providers.timeout_ms` | integer | `2000` | Timeout for provider probe |
| `loke.health.mcp_servers.timeout_ms` | integer | `3000` | Timeout for MCP server probe |
| `loke.health.companion_devices.timeout_ms` | integer | `5000` | Timeout for companion device probe |
| `loke.startup.integrity_check` | boolean | `true` | Run database integrity check on version change |
