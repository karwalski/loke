# Platform Extensibility Specification

**Epic:** P2 — Platform Extensibility
**Stories:** P2.1, P2.2, P2.3, P2.4, P2.5
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke is a platform that applications extend without forking the core. The extensibility system provides a single registration API through which applications declare routes, middleware, health checks, navigation items, settings sections, views, anonymisation patterns, configuration schemas, and lifecycle hooks.

This specification defines:

- The plugin manifest and registration interface
- The complete set of extension points and their mechanisms
- Startup and shutdown hook lifecycle
- Extensible configuration via Zod schema merging
- Anonymisation pattern registration and hot-reload
- Versioning, compatibility guarantees, and breaking change policy

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Extensible.** The platform defines extension points so applications add domain-specific behaviour without forking the core.
- **Do the right thing by default.** Extension points have safe defaults. A plugin that registers nothing is valid.
- **Privacy is the foundation.** Plugins cannot bypass the privacy pipeline. Anonymisation patterns are additive — plugins can broaden detection but cannot suppress platform-level detections.
- **Graceful degradation.** A plugin that fails to load does not bring down the platform. The system starts without it and reports the failure clearly.

---

## 2. Plugin Manifest

Every loke plugin is a TypeScript module that exports a manifest object conforming to the `LokePlugin` interface. The manifest declares what the plugin provides; the platform calls the declared functions at the appropriate lifecycle points.

### 2.1 TypeScript Interface

```typescript
import { type z } from 'zod';

/**
 * The single registration interface for loke plugins.
 * All fields are optional — a plugin declares only what it needs.
 */
export interface LokePlugin {
  /** Unique plugin identifier. Must match ^[a-z][a-z0-9-]{0,63}$. */
  readonly id: string;

  /** Human-readable display name. Max 100 characters. */
  readonly name: string;

  /** Plugin version. Semver string (e.g. "1.0.0"). */
  readonly version: string;

  /**
   * Minimum loke extension API version this plugin requires.
   * Semver range (e.g. "^1.0.0"). The platform rejects the plugin
   * if the current API version does not satisfy this range.
   */
  readonly lokeApiVersion: string;

  /** Optional human-readable description. Max 500 characters. */
  readonly description?: string;

  /** Optional author or maintainer. */
  readonly author?: string;

  /** Optional license identifier (SPDX). */
  readonly license?: string;

  // ── Extension points ──────────────────────────────────────────

  /** API route definitions. Registered under /api/v1/<plugin.id>/. */
  readonly routes?: PluginRoute[];

  /** Middleware to inject at named insertion points. */
  readonly middleware?: PluginMiddleware[];

  /** Health check probes added to the aggregate health endpoint. */
  readonly healthChecks?: PluginHealthCheck[];

  /** Navigation items added to the sidebar. */
  readonly navigation?: PluginNavigationItem[];

  /** Settings sections added to the settings view. */
  readonly settingsSection?: PluginSettingsSection;

  /** Client-side view/route definitions. */
  readonly views?: PluginView[];

  /** Database migration directory (absolute or relative to plugin root). */
  readonly migrationDirectory?: string;

  /** Locale file directory for i18n strings. */
  readonly localeDirectory?: string;

  /** Prompt template directory. */
  readonly templateDirectory?: string;

  /** CSS custom property overrides for theming. */
  readonly themeTokens?: Record<string, string>;

  /** Anonymisation pattern definitions. */
  readonly anonymisationPatterns?: AnonymisationPattern[];

  /** Zod schema extension for configuration. */
  readonly configSchema?: z.ZodObject<z.ZodRawShape>;

  /** Environment variable prefix for this plugin's config. */
  readonly configEnvPrefix?: string;

  // ── Lifecycle hooks ───────────────────────────────────────────

  /**
   * Called before the platform startup sequence begins.
   * Use for early initialisation (e.g. setting up external connections).
   * Must resolve within the configured timeout or the plugin is skipped.
   */
  readonly onBeforeStart?: (context: PluginContext) => Promise<void>;

  /**
   * Called after the platform has fully started (server listening,
   * health checks passing). Use for post-startup tasks.
   */
  readonly onAfterStart?: (context: PluginContext) => Promise<void>;

  /**
   * Called when the platform begins graceful shutdown.
   * Use for resource cleanup. Must resolve within the configured timeout.
   */
  readonly onBeforeShutdown?: (context: PluginContext) => Promise<void>;
}
```

### 2.2 Supporting Types

```typescript
/** Context passed to lifecycle hooks and health checks. */
export interface PluginContext {
  /** The plugin's validated configuration (typed by configSchema). */
  readonly config: Readonly<Record<string, unknown>>;

  /** Platform logger scoped to this plugin. */
  readonly logger: PluginLogger;

  /** Read-only access to platform settings. */
  readonly settings: SettingsReader;

  /** Database access scoped to this plugin's tables. */
  readonly database: PluginDatabase;

  /** Translation function scoped to this plugin's namespace. */
  readonly t: (key: string, params?: Record<string, string | number>) => string;
}

/** A single API route definition. */
export interface PluginRoute {
  /** HTTP method. */
  readonly method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

  /**
   * Path relative to the plugin namespace.
   * e.g. "/meetings" registers as /api/v1/<plugin.id>/meetings.
   * Supports path parameters: "/meetings/:id".
   */
  readonly path: string;

  /** Zod schema for request validation. */
  readonly validation?: {
    readonly params?: z.ZodType;
    readonly query?: z.ZodType;
    readonly body?: z.ZodType;
  };

  /** Route handler function. */
  readonly handler: RouteHandler;
}

/** Middleware injection at a named insertion point. */
export interface PluginMiddleware {
  /**
   * Named insertion point in the platform middleware pipeline.
   * See section 3.2 for the complete list.
   */
  readonly insertionPoint: MiddlewareInsertionPoint;

  /** Human-readable name for logging and diagnostics. */
  readonly name: string;

  /** The middleware function. */
  readonly handler: MiddlewareHandler;
}

export type MiddlewareInsertionPoint =
  | 'beforeAuth'
  | 'afterAuth'
  | 'beforeValidation'
  | 'afterValidation'
  | 'beforeHandler'
  | 'afterHandler';

/** Health check probe. */
export interface PluginHealthCheck {
  /** Unique name for this probe. Displayed in health endpoint. */
  readonly name: string;

  /** Check function. Resolves with status. */
  readonly check: (context: PluginContext) => Promise<HealthCheckResult>;

  /** How often to run this check (milliseconds). Default: 30000. */
  readonly intervalMs?: number;
}

export interface HealthCheckResult {
  readonly status: 'healthy' | 'degraded' | 'unhealthy';
  readonly message?: string;
  readonly metadata?: Record<string, unknown>;
}

/** Sidebar navigation item. */
export interface PluginNavigationItem {
  /** Unique identifier. */
  readonly id: string;

  /** Display label (or i18n key). */
  readonly label: string;

  /** Icon identifier from the platform icon set. */
  readonly icon?: string;

  /** Client-side route path to navigate to. */
  readonly route: string;

  /** Sort order. Lower numbers appear first. Default: 100. */
  readonly order?: number;

  /** Optional badge (e.g. unread count). */
  readonly badge?: () => number | string | undefined;
}

/** Settings section added to the settings view. */
export interface PluginSettingsSection {
  /** Section label (or i18n key). */
  readonly label: string;

  /** Icon identifier. */
  readonly icon?: string;

  /** Sort order within the settings view. Default: 100. */
  readonly order?: number;

  /** Client-side route path for the settings section. */
  readonly route: string;
}

/** Client-side view definition. */
export interface PluginView {
  /** Route path (hash-based). */
  readonly path: string;

  /** Document title when this view is active (or i18n key). */
  readonly title: string;

  /**
   * Path to the HTML template or JavaScript module that renders
   * this view. Relative to the plugin's client directory.
   */
  readonly component: string;
}

/** Anonymisation pattern definition. See section 6. */
export interface AnonymisationPattern {
  /** Entity type identifier. Must match ^[a-z][a-z0-9_]{0,63}$. */
  readonly entityType: string;

  /** Human-readable label for the entity type. */
  readonly label: string;

  /** Detection regex. Applied against text to find matches. */
  readonly regex: RegExp;

  /**
   * Confidence weight (0.0 to 1.0). Higher values mean the regex
   * is more likely to produce true positives. Used by the pipeline
   * to rank detections when multiple patterns match the same span.
   */
  readonly confidence: number;

  /**
   * Optional validation function for matches. Called after regex
   * match to reduce false positives (e.g. Luhn check for card numbers).
   */
  readonly validate?: (match: string) => boolean;

  /** Placeholder type abbreviation (1-3 chars). Used in $t$n format. */
  readonly placeholderPrefix: string;

  /** Optional description explaining what this pattern detects. */
  readonly description?: string;
}
```

---

## 3. Extension Points

The following table lists every extension point the platform exposes. Each extension point is identified by its mechanism, what it enables, and which story it traces to.

| Extension Point | Mechanism | What It Enables | Story |
|---|---|---|---|
| **Routes** | `LokePlugin.routes[]` — route definitions registered under `/api/v1/<plugin.id>/` | Applications add their own API endpoints under their own namespace. | P2.1 |
| **Middleware** | `LokePlugin.middleware[]` — handlers injected at named insertion points | Applications inject middleware at defined positions in the pipeline. | P2.1 |
| **Health checks** | `LokePlugin.healthChecks[]` — probe functions called on interval | Applications register subsystem health checks that appear in the aggregate health endpoint. | P2.1 |
| **Navigation items** | `LokePlugin.navigation[]` — data-driven sidebar items | Applications define their own navigation structure, icons, badges, and ordering. | P2.1 |
| **Settings sections** | `LokePlugin.settingsSection` — settings view extension | Applications add their own settings panels alongside platform settings. | P2.1 |
| **Views / routes** | `LokePlugin.views[]` — client-side route definitions | Applications define their own views and route mappings. | P2.1 |
| **Database migrations** | `LokePlugin.migrationDirectory` — path to numbered migration files | Applications add tables, indexes, and seed data alongside platform migrations. | P2.1 |
| **Locale files** | `LokePlugin.localeDirectory` — path to JSON locale files | Applications provide translations under their own i18n namespace. | P2.1 |
| **Prompt templates** | `LokePlugin.templateDirectory` — path to versioned template files | Applications provide their own LLM prompt templates. | P2.1 |
| **Theme tokens** | `LokePlugin.themeTokens` — CSS custom property overrides | Applications apply their own branding by overriding design tokens. | P2.1 |
| **Startup hooks** | `LokePlugin.onBeforeStart`, `onAfterStart` callbacks | Applications run custom initialisation logic within the platform lifecycle. | P2.2 |
| **Shutdown hooks** | `LokePlugin.onBeforeShutdown` callback | Applications clean up resources during graceful shutdown. | P2.2 |
| **Configuration** | `LokePlugin.configSchema` — Zod schema extension | Applications define domain-specific config sections, validated at startup. | P2.3 |
| **Config env vars** | `LokePlugin.configEnvPrefix` — environment variable prefix | Applications use their own env var namespace for configuration. | P2.3 |
| **Anonymisation patterns** | `LokePlugin.anonymisationPatterns[]` — entity type + regex + confidence | Applications define what constitutes sensitive data in their domain. | P2.4 |
| **Settings store** | Namespaced key prefixes (`<plugin.id>.*`) | Applications store settings without colliding with platform keys. | P2.1 |
| **LLM providers** | Adapter interface implementation (via `PluginRoute` or standalone adapter) | Community can add new LLM provider adapters. | P2.5 |
| **Integration adapters** | Standard adapter interface (connect, disconnect, health, domain methods) | Community can add adapters for external services. | P2.5 |

---

## 4. Plugin Registration

### 4.1 Registration API

Plugins are registered during the platform bootstrap phase, before the startup sequence begins. The platform exposes a single function:

```typescript
/**
 * Register a plugin with the platform.
 * Called during the bootstrap phase, before startup.
 * Throws if the plugin manifest is invalid or conflicts with
 * an already-registered plugin.
 */
function registerPlugin(plugin: LokePlugin): void;
```

### 4.2 Registration Sequence

1. The platform loads its own configuration and initialises the logger.
2. The platform scans the configured plugin directories for modules exporting `LokePlugin`.
3. For each discovered plugin, in dependency order:
   a. Validate the manifest (id format, required fields, `lokeApiVersion` compatibility).
   b. Validate that the plugin id does not conflict with an already-registered plugin.
   c. Merge the plugin's `configSchema` into the platform schema (section 5).
   d. Register routes under the plugin's namespace.
   e. Register middleware at declared insertion points.
   f. Register health check probes.
   g. Register navigation items, settings sections, and views.
   h. Queue migration directories for execution.
   i. Queue locale directories for loading.
   j. Merge anonymisation patterns into the pipeline (section 6).
   k. Apply theme token overrides.
4. The startup sequence begins (section 4.3).

### 4.3 Plugin Discovery

Plugins are discovered from two sources:

| Source | Description |
|--------|-------------|
| **Plugin directories** | Configured in platform config as `plugins.directories` (array of paths). Each directory is scanned for modules exporting a `LokePlugin` default export. |
| **Explicit registration** | Application code calls `registerPlugin()` directly during bootstrap. This is the primary mechanism for the host application's own plugin. |

### 4.4 Validation Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `id` format | Error | Must match `^[a-z][a-z0-9-]{0,63}$`. |
| `id` uniqueness | Error | No two registered plugins may share an id. |
| `name` present | Error | Required field. Max 100 characters. |
| `version` format | Error | Must be a valid semver string. |
| `lokeApiVersion` satisfied | Error | The platform's current extension API version must satisfy the declared range. |
| Route path conflicts | Error | No two plugins may register the same method + path combination. |
| Middleware insertion point valid | Error | Must be one of the defined insertion points. |
| Navigation id uniqueness | Warning | Duplicate navigation ids are logged; the first registration wins. |
| `configEnvPrefix` uniqueness | Error | No two plugins may share an env prefix. |
| Anonymisation `entityType` uniqueness | Error | No two plugins may register the same entity type. Platform-defined entity types cannot be overridden. |

### 4.5 Registration Errors

When a plugin fails validation:

1. The error is logged with the plugin id, the failing rule, and a human-readable message.
2. The plugin is not registered. No partial registration occurs.
3. If the plugin is marked as `required` in platform config (`plugins.required: ["plugin-id"]`), the platform refuses to start.
4. If the plugin is optional (default), the platform starts without it and reports the failure in the health endpoint.

---

## 5. Startup and Shutdown Hooks

### 5.1 Hook Lifecycle

Plugins participate in the platform lifecycle through three hooks: `onBeforeStart`, `onAfterStart`, and `onBeforeShutdown`. The following diagram shows where these hooks execute within the platform startup and shutdown sequences.

```
STARTUP SEQUENCE
================

  Platform bootstrap
  │
  ├─ Load platform config
  ├─ Initialise logger
  ├─ Discover and validate plugins
  ├─ Merge plugin config schemas
  ├─ Validate merged config
  │
  ▼
┌─────────────────────────────────────────────────┐
│  onBeforeStart hooks (all plugins, in order)    │
│                                                 │
│    Plugin A.onBeforeStart()  ──► resolve/reject │
│    Plugin B.onBeforeStart()  ──► resolve/reject │
│    Plugin C.onBeforeStart()  ──► resolve/reject │
│                                                 │
│  Execution: sequential, in registration order   │
│  Timeout: configurable per plugin (default 10s) │
└─────────────────────────────────────────────────┘
  │
  ▼
  Platform startup sequence
  │
  ├─ Open database
  ├─ Run platform migrations
  ├─ Run plugin migrations (in registration order)
  ├─ Load settings
  ├─ Load locale files (platform + plugin)
  ├─ Register routes (platform + plugin)
  ├─ Start HTTP server
  ├─ Run health checks
  ├─ Log startup summary
  │
  ▼
┌─────────────────────────────────────────────────┐
│  onAfterStart hooks (all plugins, in order)     │
│                                                 │
│    Plugin A.onAfterStart()  ──► resolve/reject  │
│    Plugin B.onAfterStart()  ──► resolve/reject  │
│    Plugin C.onAfterStart()  ──► resolve/reject  │
│                                                 │
│  Execution: sequential, in registration order   │
│  Timeout: configurable per plugin (default 10s) │
└─────────────────────────────────────────────────┘
  │
  ▼
  Platform ready (accepting requests)


SHUTDOWN SEQUENCE
=================

  Signal received (SIGTERM / SIGINT) or shutdown requested
  │
  ├─ Stop accepting new requests
  ├─ Drain in-flight requests (configurable timeout)
  │
  ▼
┌─────────────────────────────────────────────────┐
│  onBeforeShutdown hooks (reverse order)         │
│                                                 │
│    Plugin C.onBeforeShutdown()  ──► resolve     │
│    Plugin B.onBeforeShutdown()  ──► resolve     │
│    Plugin A.onBeforeShutdown()  ──► resolve     │
│                                                 │
│  Execution: sequential, reverse registration    │
│  Timeout: configurable per plugin (default 10s) │
└─────────────────────────────────────────────────┘
  │
  ▼
  Platform shutdown
  │
  ├─ Close database connections
  ├─ Flush logs
  ├─ Exit
```

### 5.2 Execution Order

| Hook | Order | Rationale |
|------|-------|-----------|
| `onBeforeStart` | Registration order (first registered, first called) | Earlier plugins initialise first; later plugins may depend on them. |
| `onAfterStart` | Registration order | Consistent with startup. |
| `onBeforeShutdown` | Reverse registration order (last registered, first called) | Resources are released in the opposite order to acquisition, preventing dependency issues. |

### 5.3 Timeout

Each hook invocation has a configurable timeout:

| Setting | Default | Description |
|---------|---------|-------------|
| `plugins.hooks.beforeStartTimeoutMs` | `10000` | Maximum time for a single `onBeforeStart` hook. |
| `plugins.hooks.afterStartTimeoutMs` | `10000` | Maximum time for a single `onAfterStart` hook. |
| `plugins.hooks.beforeShutdownTimeoutMs` | `10000` | Maximum time for a single `onBeforeShutdown` hook. |

If a hook does not resolve within its timeout, the platform:

1. Logs a warning: `Plugin "<id>" hook "<hook>" timed out after <timeout>ms`.
2. Moves to the next hook. The timed-out hook's promise is abandoned (not cancelled — there is no cancellation mechanism in JavaScript promises, but the platform no longer awaits it).
3. For `onBeforeStart`: the plugin is marked as degraded. Its health check reports `degraded` until the hook eventually resolves (if ever). The platform continues startup.
4. For `onBeforeShutdown`: the platform continues shutdown. Dangling resources are the plugin's responsibility.

### 5.4 Error Handling

If a hook rejects (throws):

| Hook | Behaviour |
|------|-----------|
| `onBeforeStart` | Error is logged. Plugin is marked as `failed`. If the plugin is in `plugins.required`, the platform aborts startup with a clear error message. Otherwise, the platform continues without the plugin. |
| `onAfterStart` | Error is logged. Plugin is marked as `degraded`. Platform continues. The error is reported in the health endpoint. |
| `onBeforeShutdown` | Error is logged. Platform continues shutdown. Shutdown must not be blocked by plugin errors. |

---

## 6. Extensible Configuration

### 6.1 Schema Extension

The platform configuration uses Zod schemas. Plugins extend the base schema by providing a `configSchema` in their manifest. The platform merges all plugin schemas into a single validation schema at startup.

```typescript
import { z } from 'zod';

// Platform base configuration schema (simplified)
const platformConfigSchema = z.object({
  server: z.object({
    host: z.string().default('localhost'),
    port: z.number().default(3000),
  }),
  database: z.object({
    path: z.string().default('./data/loke.db'),
  }),
  logging: z.object({
    level: z.enum(['debug', 'info', 'warn', 'error']).default('info'),
  }),
  plugins: z.object({
    directories: z.array(z.string()).default([]),
    required: z.array(z.string()).default([]),
    hooks: z.object({
      beforeStartTimeoutMs: z.number().default(10000),
      afterStartTimeoutMs: z.number().default(10000),
      beforeShutdownTimeoutMs: z.number().default(10000),
    }).default({}),
  }).default({}),
});
```

### 6.2 Plugin Config Schema Example

A calendar application plugin extends the base config with its own section:

```typescript
import { z } from 'zod';
import { type LokePlugin } from '@loke/core';

const calendarConfigSchema = z.object({
  calendar: z.object({
    provider: z.enum(['microsoft', 'google']).default('microsoft'),
    syncIntervalMs: z.number().min(30000).default(300000),
    maxEventsPerSync: z.number().min(10).max(1000).default(100),
    workingHours: z.object({
      start: z.string().regex(/^\d{2}:\d{2}$/).default('09:00'),
      end: z.string().regex(/^\d{2}:\d{2}$/).default('17:00'),
    }).default({}),
  }),
});

const calendarPlugin: LokePlugin = {
  id: 'calendar',
  name: 'Calendar Integration',
  version: '1.0.0',
  lokeApiVersion: '^1.0.0',
  configSchema: calendarConfigSchema,
  configEnvPrefix: 'CALENDAR',
  // ...
};
```

### 6.3 Merge Algorithm

The platform merges plugin config schemas using Zod's `.merge()`:

```typescript
// Pseudocode for schema merge during bootstrap
let mergedSchema = platformConfigSchema;

for (const plugin of registeredPlugins) {
  if (plugin.configSchema) {
    // Each plugin's schema is nested under the plugin's id
    // to prevent key collisions.
    const namespacedSchema = z.object({
      [plugin.id]: plugin.configSchema.shape[
        Object.keys(plugin.configSchema.shape)[0]
      ]
        ? plugin.configSchema
        : z.object({}),
    });
    mergedSchema = mergedSchema.merge(namespacedSchema);
  }
}
```

The effective schema is the platform base schema extended with each plugin's schema nested under the plugin's id as a top-level key. This guarantees no key collisions between plugins or between plugins and the platform.

### 6.4 Environment Variable Mapping

Plugin configuration can be set via environment variables. The naming convention is:

```
LOKE_<PLUGIN_ENV_PREFIX>_<FIELD_PATH>
```

Where `<PLUGIN_ENV_PREFIX>` is the `configEnvPrefix` from the manifest (uppercased) and `<FIELD_PATH>` is the flattened, uppercased, underscore-separated path to the field.

Example for the calendar plugin above:

| Env Variable | Config Path | Description |
|---|---|---|
| `LOKE_CALENDAR_PROVIDER` | `calendar.provider` | Calendar provider |
| `LOKE_CALENDAR_SYNC_INTERVAL_MS` | `calendar.syncIntervalMs` | Sync interval |
| `LOKE_CALENDAR_MAX_EVENTS_PER_SYNC` | `calendar.maxEventsPerSync` | Max events |
| `LOKE_CALENDAR_WORKING_HOURS_START` | `calendar.workingHours.start` | Start of working hours |
| `LOKE_CALENDAR_WORKING_HOURS_END` | `calendar.workingHours.end` | End of working hours |

### 6.5 Validation at Startup

Configuration validation runs during bootstrap, before any hooks execute:

1. Load raw config from environment files, env vars, and CLI flags.
2. Merge all plugin config schemas into the platform schema.
3. Parse the raw config against the merged schema.
4. If validation fails, the platform logs every validation error (field path, expected type, received value) and refuses to start. This is a hard failure — there is no graceful degradation for invalid configuration.
5. The validated config is frozen (`Object.freeze`, deep) and exposed as a typed, immutable object.

### 6.6 Config Precedence

Config values are resolved in this order (highest precedence first):

1. CLI flags (`--server.port 4000`)
2. Environment variables (`LOKE_SERVER_PORT=4000`)
3. Environment file (`.env`, `.env.local`)
4. Config file (`loke.config.yaml`)
5. Schema defaults

---

## 7. Anonymisation Pattern Registration

### 7.1 Registration

Plugins register anonymisation patterns in their manifest via the `anonymisationPatterns` array. Each pattern defines an entity type, a detection regex, a confidence weight, and an optional validation function.

### 7.2 Example: Domain-Specific Patterns

A CRM application registers patterns for its domain-specific sensitive data:

```typescript
import { type LokePlugin, type AnonymisationPattern } from '@loke/core';

const crmPatterns: AnonymisationPattern[] = [
  {
    entityType: 'crm_account_id',
    label: 'CRM Account ID',
    regex: /\bACC-[0-9]{6,10}\b/g,
    confidence: 0.95,
    placeholderPrefix: 'ac',
    description: 'Internal CRM account identifiers (ACC-NNNNNN format)',
  },
  {
    entityType: 'crm_deal_id',
    label: 'CRM Deal ID',
    regex: /\bDEAL-[0-9]{4,8}\b/g,
    confidence: 0.95,
    placeholderPrefix: 'dl',
    description: 'Internal CRM deal identifiers (DEAL-NNNN format)',
  },
  {
    entityType: 'internal_hostname',
    label: 'Internal Hostname',
    regex: /\b[a-z][a-z0-9-]{1,30}\.(corp|internal|local)\.[a-z]{2,6}\b/gi,
    confidence: 0.80,
    placeholderPrefix: 'hn',
    description: 'Internal network hostnames (.corp, .internal, .local domains)',
  },
  {
    entityType: 'salesforce_id',
    label: 'Salesforce Record ID',
    regex: /\b[0-9a-zA-Z]{15}(?:[0-9a-zA-Z]{3})?\b/g,
    confidence: 0.60,
    validate: (match: string) => {
      // Salesforce IDs start with specific 3-char prefixes
      const validPrefixes = ['001', '003', '005', '006', '00Q', '00T'];
      return validPrefixes.some((p) => match.startsWith(p));
    },
    placeholderPrefix: 'sf',
    description: 'Salesforce 15 or 18-character record IDs',
  },
];

const crmPlugin: LokePlugin = {
  id: 'crm',
  name: 'CRM Integration',
  version: '1.0.0',
  lokeApiVersion: '^1.0.0',
  anonymisationPatterns: crmPatterns,
  // ...
};
```

### 7.3 Pipeline Integration

Plugin-registered patterns are merged into the privacy pipeline's regex detection layer:

1. **At startup:** After all plugins are registered, the platform collects all `anonymisationPatterns` from all plugins and the platform's built-in patterns into a single ordered list.
2. **Ordering:** Platform patterns run first. Plugin patterns run after, ordered by registration order. Within a plugin, patterns run in array order.
3. **Conflict resolution:** When multiple patterns match the same text span, the match with the highest confidence wins. If confidence is equal, the platform pattern wins. If both are plugin patterns with equal confidence, the first-registered plugin's pattern wins.
4. **Additive only:** Plugins can add patterns but cannot remove or disable platform-defined patterns. This ensures the base privacy guarantees are never weakened by a plugin.

### 7.4 Hot-Reload

Anonymisation patterns support hot-reload without restarting the platform:

1. When a plugin's source files change (detected by filesystem watcher in development mode), the platform reloads the plugin's `anonymisationPatterns`.
2. The new patterns are validated (regex compiles, confidence in range, entity type format valid).
3. If validation passes, the merged pattern list is rebuilt and takes effect for the next pipeline invocation.
4. If validation fails, the previous patterns remain in effect and the error is logged.
5. In-flight requests always complete with the pattern set that was active when they entered the pipeline.

### 7.5 Pattern Validation Rules

| Rule | Severity | Description |
|------|----------|-------------|
| `entityType` format | Error | Must match `^[a-z][a-z0-9_]{0,63}$`. |
| `entityType` uniqueness | Error | Must not collide with platform entity types or other plugin entity types. |
| `confidence` range | Error | Must be in [0.0, 1.0]. |
| `regex` compiles | Error | Must be a valid `RegExp`. |
| `regex` global flag | Warning | Should have the `g` flag for full-text scanning. Non-global patterns only match the first occurrence. |
| `placeholderPrefix` format | Error | Must be 1-3 lowercase ASCII letters. Must be unique across all patterns. |
| `placeholderPrefix` uniqueness | Error | Must not collide with platform placeholder prefixes or other plugin prefixes. |
| `validate` is function | Error | If provided, must be a synchronous function. |

---

## 8. Extension Point Contracts

### 8.1 API Versioning

The loke extension API is versioned independently of the platform release version. The extension API version tracks the stability of the interfaces plugins depend on.

| Version component | Meaning |
|---|---|
| **Major** (e.g. `1.x.x` to `2.0.0`) | Breaking change to an extension point interface. Existing plugins may not work without modification. |
| **Minor** (e.g. `1.0.x` to `1.1.0`) | New extension point or new optional field on an existing interface. Existing plugins continue to work. |
| **Patch** (e.g. `1.0.0` to `1.0.1`) | Bug fix in extension point behaviour. No interface changes. |

### 8.2 Compatibility Matrix

The platform evaluates each plugin's `lokeApiVersion` range against the current extension API version using standard semver range matching:

| Plugin declares | Platform provides | Result |
|---|---|---|
| `^1.0.0` | `1.0.0` | Accepted |
| `^1.0.0` | `1.3.0` | Accepted (minor updates are backwards-compatible) |
| `^1.0.0` | `2.0.0` | Rejected (major version mismatch) |
| `>=1.0.0 <1.5.0` | `1.4.0` | Accepted |
| `>=1.0.0 <1.5.0` | `1.5.0` | Rejected |

When a plugin is rejected due to version mismatch, the error message includes:

- The plugin's declared range.
- The platform's current extension API version.
- A link to the migration guide for the relevant major version.

### 8.3 Semver Guarantees

The following guarantees hold for each extension API major version:

| Guarantee | Description |
|---|---|
| **Interface stability** | No fields are removed or renamed on `LokePlugin`, `PluginContext`, or any supporting type. |
| **Behavioural stability** | Hook execution order, timeout semantics, and error handling behaviour do not change. |
| **Route namespace stability** | The `/api/v1/<plugin.id>/` namespace prefix does not change within a major version. |
| **Config schema compatibility** | Merged config structure does not change in ways that invalidate existing plugin schemas. |
| **Pattern pipeline ordering** | Platform patterns always run before plugin patterns. Conflict resolution rules do not change. |

### 8.4 Breaking Change Policy

When a breaking change to an extension point is necessary:

1. **Announce.** The change is announced at least one minor release in advance. The announcement includes the rationale and the migration path.
2. **Deprecate.** The old interface is marked `@deprecated` with a JSDoc comment explaining the replacement. Deprecated interfaces continue to work for one full major version cycle.
3. **Migration guide.** A migration guide is published that explains:
   - What changed and why.
   - Step-by-step instructions for updating plugins.
   - Before/after code examples.
   - Automated codemods where feasible.
4. **Major release.** The deprecated interface is removed in the next major version.
5. **Support window.** The previous major version receives security fixes for 12 months after the new major version is released. No new features are backported.

### 8.5 Stability Tiers

Extension points are classified into stability tiers to set expectations:

| Tier | Meaning | Extension Points |
|---|---|---|
| **Stable** | Covered by full semver guarantees. Breaking changes only in major versions with migration guides. | `routes`, `middleware`, `healthChecks`, `configSchema`, `anonymisationPatterns`, `onBeforeStart`, `onAfterStart`, `onBeforeShutdown` |
| **Provisional** | Interface may change in minor versions during the `0.x` development phase. Stabilises when the platform reaches `1.0.0`. | `navigation`, `settingsSection`, `views`, `themeTokens` |
| **Experimental** | May change at any time. Not recommended for production plugins. | None currently. New extension points start here. |

---

## 9. Middleware Insertion Points

### 9.1 Pipeline Order

The platform middleware pipeline executes in a fixed order. Plugins inject middleware at named insertion points within this pipeline:

```
Request arrives
│
├─ [platform] Request ID assignment
├─ [platform] Request logging
├─ [platform] CORS (localhost only)
├─ [platform] Body size limit
├─ [platform] Request timeout
│
├─── beforeAuth ──────────── (plugin insertion point)
│
├─ [platform] Authentication (pluggable)
│
├─── afterAuth ───────────── (plugin insertion point)
│
├─── beforeValidation ────── (plugin insertion point)
│
├─ [platform] Request validation (Zod schema)
│
├─── afterValidation ─────── (plugin insertion point)
│
├─── beforeHandler ───────── (plugin insertion point)
│
├─ [route handler]
│
├─── afterHandler ────────── (plugin insertion point)
│
├─ [platform] Error handling
│
Response sent
```

### 9.2 Insertion Point Semantics

| Insertion Point | Typical Use |
|---|---|
| `beforeAuth` | Custom auth schemes, request transformation, early request rejection. |
| `afterAuth` | Authorisation checks that depend on the authenticated identity. |
| `beforeValidation` | Request body transformation before schema validation. |
| `afterValidation` | Business-rule validation that depends on the parsed request body. |
| `beforeHandler` | Request enrichment, audit logging, feature flags. |
| `afterHandler` | Response transformation, additional logging, metrics collection. |

### 9.3 Multiple Plugins at the Same Insertion Point

When multiple plugins inject middleware at the same insertion point, they execute in plugin registration order. Within a single plugin, middleware at the same insertion point executes in array order.

---

## 10. Database Migration Directories

### 10.1 Migration File Naming

Plugin migrations follow the same conventions as platform migrations:

```
<sequence>_<description>.sql
```

Where `<sequence>` is a zero-padded integer (e.g. `001`, `002`). Plugin migrations are namespaced by plugin id in the migration tracking table to prevent sequence collisions between plugins.

### 10.2 Execution Order

1. Platform migrations run first, in sequence order.
2. Plugin migrations run after, in plugin registration order.
3. Within a plugin, migrations run in sequence order.
4. Each migration runs in its own transaction. Failure rolls back that migration only.

---

## 11. Security Considerations

### 11.1 Plugin Trust

Plugins run in the same Node.js process as the platform. There is no sandboxing. Plugin code has full access to the platform's memory, database, and filesystem. This is an intentional design choice — loke is a local-first application where the user controls what is installed.

Mitigations:

- Plugins are installed by the user or system administrator, not downloaded automatically.
- Plugin source is inspectable (loke requires open-source plugins for the official registry).
- The `lokeApiVersion` check prevents running plugins built for a different platform version.
- Routes are namespaced, preventing plugins from shadowing platform endpoints.
- Anonymisation patterns are additive only — a plugin cannot weaken privacy protections.

### 11.2 Configuration Isolation

Plugin configurations are namespaced under the plugin id. A plugin cannot read or modify another plugin's configuration or the platform's configuration at runtime. The `PluginContext.config` object contains only the requesting plugin's validated config section.

### 11.3 Database Isolation

Plugin migrations run in a shared database but are tracked separately. Plugins should prefix their table names with their plugin id (e.g. `crm_accounts`, `crm_deals`) to avoid collisions. The platform does not enforce table name prefixes but documents this as a strong convention.

---

## 12. Example: Complete Plugin

The following example demonstrates a minimal but complete plugin that uses most extension points:

```typescript
import { z } from 'zod';
import { type LokePlugin } from '@loke/core';

const plugin: LokePlugin = {
  id: 'acme-crm',
  name: 'Acme CRM Integration',
  version: '1.2.0',
  lokeApiVersion: '^1.0.0',
  description: 'Integrates loke with the Acme CRM platform',
  author: 'Acme Corp',
  license: 'Apache-2.0',

  // Configuration
  configSchema: z.object({
    'acme-crm': z.object({
      apiUrl: z.string().url(),
      syncIntervalMs: z.number().min(30000).default(300000),
    }),
  }),
  configEnvPrefix: 'ACME_CRM',

  // Routes
  routes: [
    {
      method: 'GET',
      path: '/accounts',
      handler: async (req, res) => {
        // Registered as GET /api/v1/acme-crm/accounts
        const accounts = await listAccounts();
        res.json({ data: accounts });
      },
    },
    {
      method: 'GET',
      path: '/accounts/:id',
      validation: {
        params: z.object({ id: z.string().regex(/^ACC-\d{6,10}$/) }),
      },
      handler: async (req, res) => {
        const account = await getAccount(req.params.id);
        res.json({ data: account });
      },
    },
  ],

  // Middleware
  middleware: [
    {
      insertionPoint: 'afterAuth',
      name: 'acme-crm-tenant-resolver',
      handler: async (req, res, next) => {
        // Resolve tenant from auth context
        req.tenant = await resolveTenant(req.auth);
        next();
      },
    },
  ],

  // Health checks
  healthChecks: [
    {
      name: 'acme-crm-api',
      check: async (context) => {
        try {
          await fetch(`${context.config['acme-crm'].apiUrl}/health`);
          return { status: 'healthy' };
        } catch {
          return { status: 'unhealthy', message: 'CRM API unreachable' };
        }
      },
      intervalMs: 60000,
    },
  ],

  // Navigation
  navigation: [
    { id: 'crm-accounts', label: 'crm.nav.accounts', icon: 'users', route: '/crm/accounts', order: 10 },
    { id: 'crm-deals', label: 'crm.nav.deals', icon: 'briefcase', route: '/crm/deals', order: 20 },
  ],

  // Settings
  settingsSection: {
    label: 'crm.settings.title',
    icon: 'database',
    order: 50,
    route: '/settings/crm',
  },

  // Views
  views: [
    { path: '/crm/accounts', title: 'crm.views.accounts', component: './views/accounts.js' },
    { path: '/crm/accounts/:id', title: 'crm.views.account-detail', component: './views/account-detail.js' },
    { path: '/crm/deals', title: 'crm.views.deals', component: './views/deals.js' },
    { path: '/settings/crm', title: 'crm.views.settings', component: './views/settings.js' },
  ],

  // Database migrations
  migrationDirectory: './migrations',

  // Locale files
  localeDirectory: './locales',

  // Anonymisation patterns
  anonymisationPatterns: [
    {
      entityType: 'crm_account_id',
      label: 'CRM Account ID',
      regex: /\bACC-[0-9]{6,10}\b/g,
      confidence: 0.95,
      placeholderPrefix: 'ac',
      description: 'Internal CRM account identifiers',
    },
    {
      entityType: 'crm_deal_id',
      label: 'CRM Deal ID',
      regex: /\bDEAL-[0-9]{4,8}\b/g,
      confidence: 0.95,
      placeholderPrefix: 'dl',
      description: 'Internal CRM deal identifiers',
    },
  ],

  // Lifecycle hooks
  onBeforeStart: async (context) => {
    context.logger.info('Initialising CRM connection');
    await initCrmConnection(context.config['acme-crm'].apiUrl);
  },

  onAfterStart: async (context) => {
    context.logger.info('Starting CRM sync scheduler');
    startSyncScheduler(context.config['acme-crm'].syncIntervalMs);
  },

  onBeforeShutdown: async (context) => {
    context.logger.info('Stopping CRM sync and closing connection');
    stopSyncScheduler();
    await closeCrmConnection();
  },
};

export default plugin;
```

---

## 13. CLI Commands

The platform provides CLI commands for plugin management and diagnostics:

```bash
# List registered plugins and their status
loke plugin list

# Show details for a specific plugin
loke plugin info <plugin-id>

# Validate a plugin manifest without loading it
loke plugin validate <path-to-plugin>

# Show the merged configuration schema (platform + all plugins)
loke config schema

# Show the effective configuration with provenance
loke config show

# Show all registered anonymisation patterns
loke privacy patterns

# Show the current extension API version
loke api-version
```

---

## 14. Future Considerations

The following are not in scope for the initial implementation but are anticipated:

- **Plugin dependencies.** Plugins declaring dependencies on other plugins, with automatic load ordering.
- **Plugin sandboxing.** Running plugins in isolated V8 contexts or worker threads for security-sensitive deployments.
- **Remote plugin registry.** A curated registry of community plugins, with signature verification and compatibility metadata.
- **Dynamic plugin loading.** Loading and unloading plugins at runtime without restarting the platform.
- **Inter-plugin communication.** A typed event bus for plugins to communicate without direct coupling.
