# Storage Layer Additions Specification

**Stories:** F6.5 — Database backup and restore, F6.6 — Persistent sync queue, F6.7 — Namespaced settings store
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

The loke storage layer (Epic F6) provides SQLCipher-encrypted SQLite as the persistence foundation. This specification extends that foundation with three capabilities that the platform and applications depend on: database backup and restore, a persistent sync queue for reliable outbound operations, and a namespaced settings store for typed configuration.

This specification defines:

- Backup mechanism, naming, retention, destinations, restore process, and scheduling (F6.5)
- Sync queue schema, enqueue/dequeue API, retry strategy, abandon policy, and monitoring (F6.6)
- Settings store schema, supported types, namespacing, API, change notifications, and defaults (F6.7)

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Local-first.** All three subsystems store data in the local SQLite database. Backups can be written to mounted cloud directories, but the local copy is the source of truth.
- **Privacy is the foundation.** Backups inherit SQLCipher encryption. The sync queue never stores PII in cleartext. Settings values containing secrets are encrypted at rest.
- **Graceful degradation.** If a backup destination is unavailable, the backup is written locally and a warning is emitted. If the sync queue cannot reach an external service, items are retried with backoff. If a settings key is missing, the registered default is returned.
- **The user is the authority.** Backup schedules, retention policies, and settings values are configured by the user. Enterprise policies may set constraints, but the user controls within those bounds.

### 1.2 Dependencies

| Dependency | Story | Description |
|------------|-------|-------------|
| SQLite database schema | F6.1 | SQLCipher encryption, WAL mode, migration framework |
| Audit trail system | F6.2 | Backup and restore events are recorded in the audit trail |
| Health check system | F1.7 | Sync queue depth and settings store health are exposed via health checks |
| Configuration management | F1.5 | Backup schedules and retention policies are loaded from configuration |
| CLI application shell | F1.3 | `loke backup` and `loke restore` commands |

---

# F6.5 — Database Backup and Restore

## 2. Backup Mechanism

### 2.1 VACUUM INTO

Backups use SQLite's `VACUUM INTO` command to produce a consistent, self-contained snapshot of the database file. This approach:

- Creates a complete copy without requiring an exclusive lock on the source database
- Does not interfere with concurrent reads or writes (WAL mode continues operating)
- Produces a compacted file (freed pages are reclaimed, fragmentation is eliminated)
- Preserves SQLCipher encryption — the backup file is encrypted with the same key as the source

**Implementation:**

```sql
VACUUM INTO '/path/to/backup/loke-backup-20260405T143022Z.db';
```

The backup is performed within a single operation. If it fails (disk full, permission error), the partial file is deleted and the error is reported. No partial backups are left on disk.

### 2.2 Pre-Backup Integrity Check

Before initiating a backup, loke runs `PRAGMA integrity_check` on the source database. If the check fails, the backup is aborted and an error is logged to the audit trail. The user is notified that the database may be corrupted and should investigate.

### 2.3 Post-Backup Verification

After the backup file is written, loke:

1. Opens the backup file in read-only mode
2. Runs `PRAGMA integrity_check` on the backup
3. Computes a SHA-256 checksum of the backup file
4. Writes a sidecar metadata file (`{backup_name}.meta.json`) containing the checksum, source database size, backup timestamp, and loke version

If the integrity check fails, the backup file and sidecar are deleted, an error is logged, and the operation is reported as failed.

---

## 3. Naming Convention

### 3.1 File Naming

Backup files follow the pattern:

```
{prefix}-{ISO8601_timestamp}.db
```

| Component | Description | Default |
|-----------|-------------|---------|
| `prefix` | Configurable prefix identifying the backup set | `loke-backup` |
| `ISO8601_timestamp` | UTC timestamp in compact format: `YYYYMMDDTHHmmssZ` | Generated at backup time |

**Examples:**

```
loke-backup-20260405T143022Z.db
loke-backup-20260405T143022Z.meta.json
```

### 3.2 Sidecar Metadata

Each backup has a companion `.meta.json` file:

```json
{
  "backup_version": "1.0",
  "prefix": "loke-backup",
  "timestamp": "2026-04-05T14:30:22Z",
  "source_size_bytes": 52428800,
  "backup_size_bytes": 48234496,
  "checksum": {
    "algorithm": "sha256",
    "value": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  "loke_version": "0.8.0",
  "encrypted": true,
  "integrity_verified": true
}
```

### 3.3 Prefix Configuration

The prefix is configured in the loke configuration file:

```yaml
backup:
  prefix: "loke-backup"       # Default
```

Applications can override the prefix to distinguish their backups (e.g. `myapp-backup`). The prefix must match `^[a-z0-9][a-z0-9._-]{0,63}$`.

---

## 4. Retention Policy

### 4.1 Retention Modes

loke supports two retention modes. Only one may be active at a time.

| Mode | Configuration | Description |
|------|---------------|-------------|
| `max_count` | `backup.retention.max_count` | Keep the N most recent backups. Older backups are pruned. |
| `max_age` | `backup.retention.max_age` | Keep backups younger than the specified duration. Older backups are pruned. |

**Configuration:**

```yaml
backup:
  retention:
    mode: max_count            # max_count | max_age
    max_count: 10              # When mode is max_count
    max_age: "30d"             # When mode is max_age (duration string: Nd, Nw, Nm)
```

### 4.2 Automatic Pruning

Pruning runs automatically after every successful backup. The pruning process:

1. Lists all backup files in the destination directory matching the configured prefix
2. Sorts by timestamp (extracted from the filename)
3. Identifies files that exceed the retention threshold
4. Deletes the backup file and its sidecar metadata file together
5. Logs each deletion to the audit trail

Pruning never deletes the most recent backup, even if it exceeds the max age. At least one backup is always retained.

### 4.3 Defaults

| Setting | Default |
|---------|---------|
| `mode` | `max_count` |
| `max_count` | `5` |
| `max_age` | `30d` |

---

## 5. Backup Destinations

### 5.1 Destination Types

Backups are written to a local filesystem path. Cloud storage services (OneDrive, Google Drive, Dropbox) that sync local directories to the cloud are supported natively — they appear as local paths to loke. No cloud API integration is required.

| Destination | Configuration | Notes |
|-------------|---------------|-------|
| Local directory | Absolute path on the local filesystem | Default: `{data_dir}/backups/` |
| Mounted cloud directory | Path to the synced folder | e.g. `~/OneDrive/loke-backups/`, `~/Google Drive/loke-backups/` |

### 5.2 Destination Configuration

```yaml
backup:
  destination: "~/.loke/backups"     # Default (resolved relative to data directory)
```

The destination directory is created automatically if it does not exist. If creation fails (permissions, invalid path), the backup falls back to the default local path and logs a warning.

### 5.3 Destination Validation

On startup and before each backup, loke validates the destination:

1. **Exists or can be created** — attempt `mkdir -p` equivalent
2. **Writable** — write and delete a temporary file
3. **Sufficient space** — check available disk space against the current database size (warn if less than 2x database size available)

If validation fails, the backup is written to the default local path and a warning is emitted. The backup is never skipped due to a destination issue.

---

## 6. Restore Process

### 6.1 Restore Steps

Restoring a database from backup follows a strict sequence:

1. **Select backup** — user specifies a backup file path or selects from the list of available backups
2. **Validate backup integrity** — open the backup file, run `PRAGMA integrity_check`, verify the SHA-256 checksum against the sidecar metadata
3. **Confirmation prompt** — display backup timestamp, size, and loke version; require explicit confirmation before proceeding (CLI: `--yes` flag to skip; UI: confirmation dialog)
4. **Stop active connections** — drain in-flight requests and close all database connections
5. **Create safety backup** — take a backup of the current database before overwriting (named with `pre-restore-` prefix)
6. **Replace database** — copy the backup file to the database path (atomic rename where the OS supports it)
7. **Run pending migrations** — if the backup is from an older loke version, run any migrations that were added since the backup was taken
8. **Verify restored database** — open the restored database, run `PRAGMA integrity_check`, verify it can be queried
9. **Resume connections** — reopen database connections and resume normal operation
10. **Log event** — record the restore in the audit trail (backup timestamp, source path, checksum, success/failure)

### 6.2 Rollback on Failure

If any step from 6 onwards fails, loke:

1. Restores the safety backup (created in step 5)
2. Reopens database connections
3. Logs the failed restore attempt with the error reason
4. Reports the failure to the user with a clear error message

The safety backup is retained for 24 hours after a successful restore, then pruned.

### 6.3 Version Compatibility

Backups from older loke versions can be restored if the database schema version is within the supported migration range. The migration framework (F6.1) handles schema upgrades. Backups from newer loke versions are rejected with an error indicating the user should upgrade loke first.

---

## 7. SQLCipher Considerations

### 7.1 Encrypted Backups

When SQLCipher encryption is enabled (R12.5), `VACUUM INTO` produces an encrypted backup file using the same encryption key as the source database. The backup is encrypted at rest on disk.

### 7.2 Key Management

- The encryption key is stored in the OS credential store (F1.5), never in plaintext files
- The backup sidecar metadata records `"encrypted": true` but never contains the key
- Restoring an encrypted backup requires the same encryption key that was used to create it
- If the key is unavailable (lost credential store, different machine), the restore fails with a clear error explaining the key requirement

### 7.3 Key Rotation

If the encryption key has been rotated since the backup was taken, the restore process:

1. Attempts to open the backup with the current key
2. If that fails, prompts the user for the original key
3. If the original key is provided, decrypts and re-encrypts with the current key during restore

---

## 8. Scheduling

### 8.1 Cron-Style Schedule

Backups can be scheduled using a cron-style expression in the configuration:

```yaml
backup:
  schedule: "0 2 * * *"         # Daily at 02:00 UTC
  enabled: true                  # Enable/disable scheduled backups
```

The cron expression supports five fields (minute, hour, day-of-month, month, day-of-week) following standard cron syntax. The schedule is evaluated in UTC.

Common presets are provided for convenience:

| Preset | Cron Expression | Description |
|--------|-----------------|-------------|
| `daily` | `0 2 * * *` | Daily at 02:00 UTC |
| `weekly` | `0 2 * * 0` | Weekly on Sunday at 02:00 UTC |
| `hourly` | `0 * * * *` | Every hour on the hour |

**Configuration with preset:**

```yaml
backup:
  schedule: "daily"              # Preset name or cron expression
  enabled: true
```

### 8.2 Scheduler Implementation

The scheduler runs within the loke process. On startup, it calculates the next scheduled backup time and sets a timer. After each backup (scheduled or manual), it recalculates the next time. The scheduler is resilient to missed windows — if loke was not running when a backup was due, it runs the backup at the next startup if more than one interval has elapsed since the last backup.

### 8.3 Manual Trigger

Backups can be triggered manually at any time, independent of the schedule:

- **CLI:** `loke backup` command
- **UI:** Backup button in settings view (P3.9)
- **API:** `POST /api/v1/backup` endpoint

---

## 9. CLI Commands

### 9.1 `loke backup`

Create a database backup.

```bash
loke backup [options]

Options:
  --destination <path>    Override backup destination for this run
  --prefix <prefix>       Override backup prefix for this run
  --no-verify             Skip post-backup integrity verification
  --quiet                 Suppress output except errors
```

**Output (default):**

```
Backup created: loke-backup-20260405T143022Z.db
  Size: 46.0 MB (compacted from 50.0 MB)
  Checksum: e3b0c442...b855
  Destination: /home/user/.loke/backups/
  Encrypted: yes
  Retention: 5 of 5 backups kept (max_count: 5)
```

### 9.2 `loke backup list`

List available backups.

```bash
loke backup list [options]

Options:
  --destination <path>    List backups in a specific directory
  --format <format>       Output format: table (default), json
```

**Output (default):**

```
  #  Timestamp                Size      Encrypted  Verified
  1  2026-04-05T14:30:22Z    46.0 MB   yes        yes
  2  2026-04-04T02:00:00Z    45.8 MB   yes        yes
  3  2026-04-03T02:00:00Z    45.5 MB   yes        yes
```

### 9.3 `loke restore`

Restore a database from backup.

```bash
loke restore <backup_path_or_number> [options]

Options:
  --yes                   Skip confirmation prompt
  --no-migrate            Do not run pending migrations after restore
  --quiet                 Suppress output except errors

Arguments:
  backup_path_or_number   File path to a backup, or a number from `loke backup list`
```

**Output (default):**

```
Restore from: loke-backup-20260405T143022Z.db
  Timestamp: 2026-04-05T14:30:22Z
  Size: 46.0 MB
  Checksum: verified
  Encrypted: yes

This will replace the current database. A safety backup will be created first.
Continue? [y/N] y

  Creating safety backup... done
  Stopping database connections... done
  Restoring database... done
  Running pending migrations (2 new)... done
  Verifying restored database... done
  Resuming connections... done

Restore complete.
```

---

# F6.6 — Persistent Sync Queue

## 10. Queue Schema

### 10.1 Table Definition

The sync queue is stored in a dedicated SQLite table within the loke database.

```sql
CREATE TABLE sync_queue (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  operation     TEXT    NOT NULL,
  payload       TEXT    NOT NULL,
  status        TEXT    NOT NULL DEFAULT 'pending',
  attempts      INTEGER NOT NULL DEFAULT 0,
  max_attempts  INTEGER NOT NULL DEFAULT 5,
  next_retry_at TEXT,                              -- ISO 8601 timestamp, NULL when not scheduled
  error_message TEXT,                              -- Last error, NULL on success
  created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

CREATE INDEX idx_sync_queue_status_next_retry
  ON sync_queue (status, next_retry_at);

CREATE INDEX idx_sync_queue_operation_status
  ON sync_queue (operation, status);
```

### 10.2 Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `id` | INTEGER | Auto-incrementing primary key. Used for ordering and dequeue selection. |
| `operation` | TEXT | Operation type identifier (e.g. `calendar.sync`, `audit.forward`, `backup.upload`). Namespaced to the registering application. |
| `payload` | TEXT | JSON-serialised operation payload. Must be a valid JSON string. |
| `status` | TEXT | Current status: `pending`, `processing`, `completed`, `failed`, `abandoned`. |
| `attempts` | INTEGER | Number of processing attempts so far. |
| `max_attempts` | INTEGER | Maximum attempts before the item is marked abandoned. Configurable per operation type. |
| `next_retry_at` | TEXT | ISO 8601 timestamp of the next retry. NULL for items not awaiting retry. |
| `error_message` | TEXT | Error message from the most recent failed attempt. NULL when no error. |
| `created_at` | TEXT | ISO 8601 timestamp of when the item was enqueued. |
| `updated_at` | TEXT | ISO 8601 timestamp of the last status change. |

### 10.3 Status Transitions

```
pending → processing → completed
                     → failed → pending (retry)
                              → abandoned (max attempts exceeded)
```

| Transition | Trigger |
|------------|---------|
| `pending` → `processing` | Worker picks up the item |
| `processing` → `completed` | Handler returns success |
| `processing` → `failed` | Handler throws or returns error |
| `failed` → `pending` | Retry scheduled (attempts < max_attempts) |
| `failed` → `abandoned` | max_attempts exceeded |

---

## 11. Enqueue API

### 11.1 TypeScript Interface

```typescript
interface SyncQueueEnqueueOptions {
  operation: string;           // Namespaced operation type
  payload: Record<string, unknown>;  // Serialisable payload
  maxAttempts?: number;        // Override default max attempts (default: 5)
}

interface SyncQueueItem {
  id: number;
  operation: string;
  payload: Record<string, unknown>;
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'abandoned';
  attempts: number;
  maxAttempts: number;
  nextRetryAt: string | null;
  errorMessage: string | null;
  createdAt: string;
  updatedAt: string;
}

interface SyncQueue {
  enqueue(options: SyncQueueEnqueueOptions): Promise<SyncQueueItem>;
  getById(id: number): Promise<SyncQueueItem | null>;
  getByOperation(operation: string, status?: string): Promise<SyncQueueItem[]>;
  getDepth(): Promise<Record<string, number>>;   // Count by status
}
```

### 11.2 Enqueue Behaviour

When `enqueue()` is called:

1. Validate the `operation` string matches a registered operation type (see section 12.1)
2. Validate the `payload` is serialisable to JSON (no circular references, no functions, no undefined values)
3. Insert a row with `status = 'pending'`, `attempts = 0`, `next_retry_at = NULL`
4. Return the created `SyncQueueItem`
5. Notify the worker loop that a new item is available (if the worker is idle)

Enqueue is synchronous from the caller's perspective — the item is persisted before the function returns. Processing happens asynchronously.

---

## 12. Dequeue and Processing

### 12.1 Operation Registration

Applications register operation types and their handlers at startup:

```typescript
interface SyncQueueHandler {
  (payload: Record<string, unknown>): Promise<void>;
}

interface SyncQueueOperationConfig {
  operation: string;           // e.g. 'audit.forward'
  handler: SyncQueueHandler;
  maxAttempts?: number;        // Default: 5
  concurrency?: number;        // Default: 1
}

interface SyncQueueRegistry {
  register(config: SyncQueueOperationConfig): void;
  unregister(operation: string): void;
}
```

Only registered operation types can be enqueued. Attempting to enqueue an unregistered operation type throws an error.

### 12.2 Worker Loop

The sync queue worker runs as a background loop within the loke process:

1. **Poll** — query for items where `status = 'pending'` and (`next_retry_at IS NULL` or `next_retry_at <= NOW`), ordered by `id ASC`
2. **Claim** — update `status = 'processing'` and `attempts = attempts + 1` in a single atomic UPDATE with a WHERE clause that includes the current status (optimistic locking)
3. **Dispatch** — invoke the registered handler for the item's operation type
4. **Complete or fail** — on handler success, set `status = 'completed'`; on handler error, set `status = 'failed'` and `error_message` to the error string
5. **Schedule retry or abandon** — if failed and `attempts < max_attempts`, calculate `next_retry_at` and set `status = 'pending'`; if `attempts >= max_attempts`, set `status = 'abandoned'`
6. **Repeat** — return to step 1

The worker polls on a configurable interval (default: 5 seconds) when idle. When notified of a new enqueue (step 5 in section 11.2), it polls immediately.

### 12.3 Concurrency

Each operation type has a configurable concurrency limit (default: 1). The worker respects this limit — it will not claim more items for a given operation type than the configured concurrency allows.

When `concurrency = 1` (default), items of the same operation type are processed strictly in order. When `concurrency > 1`, items may be processed in parallel but enqueue order is preserved within each concurrent slot.

### 12.4 In-Order Guarantee

For a given operation type with `concurrency = 1`, items are processed in FIFO order (ordered by `id`). This guarantee is important for operations where order matters (e.g. sequential API calls that depend on previous results).

When `concurrency > 1`, ordering is best-effort. Applications that require strict ordering must use `concurrency = 1`.

---

## 13. Retry Strategy

### 13.1 Exponential Backoff with Jitter

When an item fails and is eligible for retry, the next retry time is calculated using exponential backoff with full jitter:

```
delay = random(0, min(max_delay, base_delay * multiplier ^ (attempts - 1)))
next_retry_at = now + delay
```

### 13.2 Configuration

```yaml
sync_queue:
  retry:
    base_delay: "1s"           # Base delay for first retry
    max_delay: "5m"            # Maximum delay between retries
    multiplier: 2              # Exponential multiplier
```

### 13.3 Defaults

| Setting | Default |
|---------|---------|
| `base_delay` | `1s` |
| `max_delay` | `5m` |
| `multiplier` | `2` |
| `max_attempts` | `5` |

### 13.4 Retry Schedule Example

With default settings (`base_delay=1s`, `multiplier=2`, `max_delay=5m`), the maximum delay windows are:

| Attempt | Max Delay | Window (with jitter) |
|---------|-----------|----------------------|
| 1 | 1s | 0–1s |
| 2 | 2s | 0–2s |
| 3 | 4s | 0–4s |
| 4 | 8s | 0–8s |
| 5 | 16s | 0–16s |

Actual delays are randomised within the window (full jitter) to avoid thundering herd effects when multiple items fail simultaneously.

---

## 14. Abandon Policy

### 14.1 Abandonment

When an item's `attempts` reaches `max_attempts` and the handler fails, the item is marked `status = 'abandoned'`. Abandoned items are not retried.

### 14.2 Application Callback

Applications can register an abandon callback per operation type:

```typescript
interface SyncQueueOperationConfig {
  // ... existing fields
  onAbandon?: (item: SyncQueueItem) => Promise<void>;
}
```

When an item is abandoned, the `onAbandon` callback is invoked with the full item (including `error_message`). This allows applications to:

- Log the failure to their own systems
- Create a notification for the user (via P3.8)
- Attempt alternative processing

The callback is best-effort — if it throws, the error is logged but the item remains abandoned.

### 14.3 Manual Retry

Abandoned items can be manually retried via the API or CLI:

```bash
loke queue retry <item_id>         # Retry a specific abandoned item
loke queue retry --operation <op>  # Retry all abandoned items for an operation type
```

Manual retry resets `attempts = 0`, `status = 'pending'`, `next_retry_at = NULL`.

---

## 15. Purge Completed

### 15.1 Retention

Completed and abandoned items are retained for a configurable period before being purged:

```yaml
sync_queue:
  purge:
    completed_after: "7d"      # Purge completed items older than 7 days
    abandoned_after: "30d"     # Purge abandoned items older than 30 days
```

### 15.2 Purge Process

Purging runs automatically once per hour (or on startup if more than one hour has elapsed since the last purge). The process:

1. Delete rows where `status = 'completed'` and `updated_at < NOW - completed_after`
2. Delete rows where `status = 'abandoned'` and `updated_at < NOW - abandoned_after`
3. Deletions are batched (1000 rows per transaction) to avoid long-running locks

### 15.3 Defaults

| Setting | Default |
|---------|---------|
| `completed_after` | `7d` |
| `abandoned_after` | `30d` |

---

## 16. Persistence Guarantees

### 16.1 WAL Mode

The sync queue table operates under the same WAL mode as the rest of the loke database (F6.1). This ensures:

- Enqueue operations are durable immediately on return (write-ahead log is flushed)
- Concurrent reads (queue depth queries, health checks) do not block writes
- Crash recovery replays the WAL, so no committed items are lost

### 16.2 Crash and Restart

On startup, the sync queue worker:

1. Recovers any items with `status = 'processing'` — these were in-flight when the process terminated. They are reset to `status = 'pending'` with their attempt count preserved (the attempt is counted as failed).
2. Resumes processing from the oldest pending item.

This ensures that no enqueued item is silently lost due to a crash or restart.

### 16.3 No Duplicate Processing

The atomic claim step (section 12.2) ensures that each item is processed by exactly one worker, even if the worker loop is restarted. The `WHERE status = 'pending'` clause in the UPDATE prevents double-claiming.

---

## 17. Monitoring

### 17.1 Health Check Integration

The sync queue registers a health check (F1.7) that reports:

| Metric | Description | Healthy Threshold |
|--------|-------------|-------------------|
| `queue_depth_pending` | Number of items with `status = 'pending'` | Configurable (default: < 100) |
| `queue_depth_processing` | Number of items with `status = 'processing'` | Informational |
| `queue_depth_failed` | Number of items with `status = 'failed'` awaiting retry | Configurable (default: < 50) |
| `queue_depth_abandoned` | Number of items with `status = 'abandoned'` | Configurable (default: < 10) |
| `oldest_pending_age` | Age of the oldest pending item | Configurable (default: < 1 hour) |
| `retry_rate` | Percentage of items that required at least one retry (rolling 24h) | Informational |
| `abandon_rate` | Percentage of items that were abandoned (rolling 24h) | Configurable (default: < 5%) |

The health check reports `healthy` when all metrics are within thresholds, `degraded` when any metric exceeds its threshold, and `unhealthy` when the worker loop is not running.

### 17.2 CLI Commands

```bash
loke queue status                  # Show queue depth by operation and status
loke queue list [--status <s>]     # List queue items, optionally filtered by status
loke queue retry <id>              # Retry an abandoned item
loke queue purge                   # Manually trigger purge of completed/abandoned items
```

---

# F6.7 — Namespaced Settings Store

## 18. Schema

### 18.1 Table Definition

```sql
CREATE TABLE settings (
  namespace   TEXT    NOT NULL,
  key         TEXT    NOT NULL,
  value_type  TEXT    NOT NULL,
  value       TEXT    NOT NULL,
  category    TEXT,
  updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

  PRIMARY KEY (namespace, key)
);

CREATE INDEX idx_settings_namespace_category
  ON settings (namespace, category);
```

### 18.2 Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `namespace` | TEXT | Dot-separated namespace prefix (e.g. `loke`, `loke.backup`, `myapp`). |
| `key` | TEXT | Setting key within the namespace (e.g. `theme`, `schedule`). |
| `value_type` | TEXT | Data type: `string`, `number`, `boolean`, `json`. |
| `value` | TEXT | The setting value, stored as a string. Numbers are stored as their string representation. Booleans as `"true"` or `"false"`. JSON as the serialised string. |
| `category` | TEXT | Optional grouping for UI display (e.g. `appearance`, `backup`, `privacy`). NULL if uncategorised. |
| `updated_at` | TEXT | ISO 8601 timestamp of the last update. |

---

## 19. Supported Types

### 19.1 Type Definitions

| Type | Storage Format | Validation |
|------|----------------|------------|
| `string` | Stored as-is | Max 65,536 characters. |
| `number` | String representation of a finite number | Must parse as a finite JavaScript number (not NaN, not Infinity). |
| `boolean` | `"true"` or `"false"` | Must be exactly `"true"` or `"false"`. |
| `json` | Serialised JSON string | Must be valid JSON. Max 1 MB when serialised. |

### 19.2 Type Validation on Write

Every `set()` call validates the value against the declared type. If the value does not match the type, the write is rejected with a `TypeError`. The type is determined by:

1. The type declared in the default registration (section 22), if the key has a registered default
2. The `value_type` parameter passed explicitly to `set()`
3. Inference from the JavaScript type of the value (string, number, boolean, or object/array for JSON)

If the inferred type conflicts with a registered default's type, the write is rejected.

---

## 20. Namespacing

### 20.1 Platform Namespace

The `loke` namespace and all `loke.*` sub-namespaces are reserved for the platform. Applications must not write to these namespaces.

**Examples of platform settings:**

| Namespace | Key | Description |
|-----------|-----|-------------|
| `loke` | `theme` | Current theme: `system`, `light`, `dark` |
| `loke` | `locale` | Current locale code (e.g. `en-AU`) |
| `loke` | `timezone` | User's timezone (e.g. `Australia/Sydney`) |
| `loke.backup` | `schedule` | Backup schedule (cron expression or preset) |
| `loke.backup` | `destination` | Backup destination path |
| `loke.backup` | `retention_mode` | Retention mode: `max_count` or `max_age` |

### 20.2 Application Namespace Registration

Applications register their namespace prefix at startup via the plugin system (P2.1):

```typescript
interface SettingsNamespaceConfig {
  namespace: string;           // e.g. 'myapp'
  description?: string;        // Human-readable description
}
```

Registration validates:

- The namespace does not start with `loke` (reserved)
- The namespace has not already been registered by another application
- The namespace matches `^[a-z][a-z0-9_-]{0,31}$`

If validation fails, registration throws and the application fails to start.

### 20.3 Collision Prevention

The primary key `(namespace, key)` prevents key collisions within a namespace. Cross-namespace collisions are impossible by design — each application operates in its own namespace.

Attempting to write to a namespace that has not been registered throws an error. The platform namespace `loke` is always registered.

---

## 21. API

### 21.1 TypeScript Interface

```typescript
interface SettingsStore {
  /**
   * Get a setting value. Returns the typed value, or the registered
   * default if the key does not exist, or undefined if no default.
   */
  get<T>(namespace: string, key: string): Promise<T | undefined>;

  /**
   * Set a setting value. Validates type against registered default
   * if one exists. Creates or updates the row.
   */
  set<T>(namespace: string, key: string, value: T, category?: string): Promise<void>;

  /**
   * Delete a setting. Returns true if the key existed.
   */
  delete(namespace: string, key: string): Promise<boolean>;

  /**
   * List all settings in a namespace, optionally filtered by category.
   */
  list(namespace: string, category?: string): Promise<SettingsEntry[]>;

  /**
   * Bulk get multiple keys from a namespace.
   */
  getMany(namespace: string, keys: string[]): Promise<Record<string, unknown>>;

  /**
   * Bulk set multiple keys in a namespace. Atomic — all or none.
   */
  setMany(namespace: string, entries: SettingsEntry[]): Promise<void>;

  /**
   * Subscribe to changes on a specific key or namespace.
   * Returns an unsubscribe function.
   */
  subscribe(
    namespace: string,
    key: string | '*',
    callback: (event: SettingsChangeEvent) => void
  ): () => void;
}

interface SettingsEntry {
  key: string;
  value: unknown;
  valueType: 'string' | 'number' | 'boolean' | 'json';
  category?: string;
}

interface SettingsChangeEvent {
  namespace: string;
  key: string;
  oldValue: unknown | undefined;
  newValue: unknown;
  valueType: string;
}
```

### 21.2 Bulk Operations

`setMany()` wraps all writes in a single transaction. If any write fails validation, the entire batch is rolled back and an error is thrown listing the invalid entries.

`getMany()` returns a record mapping key names to their typed values. Keys that do not exist return their registered default, or are omitted from the result if no default is registered.

---

## 22. Default Values

### 22.1 Registration

Applications and the platform register default values at startup:

```typescript
interface SettingsDefault {
  namespace: string;
  key: string;
  value: unknown;
  valueType: 'string' | 'number' | 'boolean' | 'json';
  category?: string;
  description?: string;        // Human-readable description for settings UI
}

interface SettingsStore {
  // ... existing methods
  registerDefaults(defaults: SettingsDefault[]): void;
}
```

### 22.2 Behaviour

Defaults are held in memory and are not written to the database until the setting is explicitly set by the user or application. This means:

- `get()` returns the default value when the key has no row in the database
- `list()` includes defaults that have not been overridden, marked with `isDefault: true`
- Calling `set()` with the same value as the default creates a database row (the user has explicitly confirmed the value)
- Calling `delete()` removes the database row, reverting the setting to its default

### 22.3 Default Conflicts

If two calls to `registerDefaults()` provide different defaults for the same `(namespace, key)`, the second registration throws an error. Defaults are immutable once registered.

---

## 23. Change Notifications

### 23.1 Subscribe

`subscribe(namespace, key, callback)` registers a callback that fires whenever the specified setting changes. Passing `'*'` as the key subscribes to all changes within the namespace.

### 23.2 Notification Delivery

Notifications are delivered synchronously after the database write succeeds. The `SettingsChangeEvent` includes:

- The namespace and key that changed
- The old value (or `undefined` if the key did not exist)
- The new value
- The value type

### 23.3 Use Cases

- **Settings UI:** The settings view subscribes to namespace changes and re-renders reactive elements when values change (e.g. theme toggle takes effect immediately)
- **Subsystem reconfiguration:** The backup scheduler subscribes to `loke.backup.schedule` and recalculates the next backup time when the schedule changes
- **Application state:** Applications subscribe to their own namespace to react to configuration changes without polling

### 23.4 Unsubscribe

The `subscribe()` method returns an unsubscribe function. Calling it removes the callback. Callbacks are automatically cleaned up when the settings store is shut down during graceful shutdown (F1.6).

---

## 24. Migration from Previous Configuration

### 24.1 Import Utility

If settings were previously stored in configuration files (e.g. environment variables, YAML files, or JSON config), the platform provides an import utility:

```bash
loke settings import <file_path> [options]

Options:
  --namespace <ns>        Target namespace for imported settings
  --dry-run               Show what would be imported without writing
  --overwrite             Overwrite existing settings (default: skip existing)
  --format <fmt>          Source format: json, yaml, env (auto-detected if omitted)
```

### 24.2 Import Behaviour

The import utility:

1. Reads the source file and parses key-value pairs
2. Maps each value to the appropriate type (string, number, boolean, JSON)
3. Validates each entry against registered defaults (if any) for type compatibility
4. Writes valid entries to the settings store
5. Reports skipped entries (type mismatch, already exists when `--overwrite` is not set)

### 24.3 First-Run Migration

On first startup after upgrading to a version with the settings store, the platform checks for legacy configuration and automatically imports platform settings (with `--namespace loke`). This is a one-time operation, recorded in the settings store itself (`loke.internal.migrated_from_config = true`).

---

## 25. Configuration Summary

All configuration options introduced in this specification, consolidated:

```yaml
backup:
  enabled: true                    # Enable scheduled backups
  schedule: "daily"                # Cron expression or preset
  destination: "~/.loke/backups"   # Backup destination directory
  prefix: "loke-backup"            # Backup filename prefix
  retention:
    mode: max_count                # max_count | max_age
    max_count: 5
    max_age: "30d"

sync_queue:
  poll_interval: "5s"              # Worker poll interval when idle
  retry:
    base_delay: "1s"
    max_delay: "5m"
    multiplier: 2
  purge:
    completed_after: "7d"
    abandoned_after: "30d"
  health:
    max_pending: 100
    max_failed: 50
    max_abandoned: 10
    max_pending_age: "1h"
    max_abandon_rate: 5            # Percentage
```

Settings store configuration is managed through the settings store itself (bootstrapping uses built-in defaults).
