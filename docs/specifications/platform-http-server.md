# Platform HTTP Server — Specification

**Epic:** P1 — Platform HTTP Server
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-04-05

---

## 1. Overview

loke runs a local HTTP server that serves the browser-based UI, exposes versioned API endpoints, and provides a composable middleware pipeline that applications can extend. The server is the entry point for all client-server interaction in both standalone and Electron modes.

This specification defines:

- HTTP server lifecycle and configuration (P1.1)
- Versioned API routing and plugin-based route registration (P1.2)
- Composable middleware pipeline with enforced order and named insertion points (P1.3)
- Standard response envelopes and request validation (P1.4)
- Security hardening: headers, rate limiting, HSTS (P1.5)

### 1.1 Design Alignment

This specification follows the loke design principles:

- **Local-first.** The server binds to `localhost` by default. External network access is opt-in, never the default.
- **Privacy is the foundation.** Security headers, CORS restrictions, and rate limiting are enforced by the platform, not left to application authors.
- **Extensible.** Applications register routes, middleware, and validation schemas through well-defined APIs — without forking or patching platform code.
- **Do the right thing by default.** The middleware pipeline ships with a secure, sensible order. Applications insert behaviour at named points rather than replacing the stack.

---

## 2. HTTP Server Core (P1.1)

### 2.1 Server Configuration

The server is configured through loke's hierarchical configuration system (F1.5). All values have secure defaults.

```typescript
// In the server configuration module (Zod schema)
const serverConfigSchema = z.object({
  host: z.string().default('localhost'),
  port: z.number().int().min(1).max(65535).default(3000),
  tls: z.object({
    enabled: z.boolean().default(false),
    cert: z.string().optional(),   // path to PEM certificate
    key: z.string().optional(),    // path to PEM private key
  }).default({}),
  staticDir: z.string().default('./client/dist'),
  requestTimeout: z.number().int().min(1000).max(300000).default(30000), // ms
  maxBodySize: z.string().default('1mb'),
  shutdownTimeout: z.number().int().min(1000).max(30000).default(10000), // ms
});
```

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `host` | string | `"localhost"` | Bind address. `localhost` restricts to loopback. `0.0.0.0` opens to network (requires explicit opt-in). |
| `port` | number | `3000` | TCP port. Must be 1-65535. |
| `tls.enabled` | boolean | `false` | Enable TLS for local use. Not required for localhost. |
| `tls.cert` | string | — | Path to PEM certificate file. Required when TLS is enabled. |
| `tls.key` | string | — | Path to PEM private key file. Required when TLS is enabled. |
| `staticDir` | string | `"./client/dist"` | Directory to serve as static assets. Relative to project root. |
| `requestTimeout` | number | `30000` | Request timeout in milliseconds. Range 1000-300000. |
| `maxBodySize` | string | `"1mb"` | Maximum request body size. Accepts units: `b`, `kb`, `mb`. |
| `shutdownTimeout` | number | `10000` | Time in ms to wait for in-flight requests during graceful shutdown. |

### 2.2 Static File Serving

The server serves the contents of `staticDir` as static assets at the root path (`/`).

**Rules:**

1. Files are served with appropriate `Content-Type` headers derived from file extension.
2. Cache headers are set for immutable assets (files with content hashes in the filename): `Cache-Control: public, max-age=31536000, immutable`.
3. Non-hashed assets use `Cache-Control: no-cache` to ensure freshness during development.
4. Directory listing is disabled. Requests for directories return 404.

### 2.3 SPA Fallback

For single-page applications, requests that do not match a static file or an API route are served `index.html` from the static directory. This enables client-side routing.

**Fallback rules:**

1. The request method is `GET`.
2. The `Accept` header includes `text/html`.
3. The request path does not start with `/api/`.
4. The request path does not match an existing static file.
5. The request path does not match a known file extension for non-HTML assets (`.js`, `.css`, `.json`, `.map`, `.ico`, `.png`, `.jpg`, `.svg`, `.woff`, `.woff2`).

When all five conditions are met, the server responds with the contents of `index.html` and a 200 status.

### 2.4 Server Lifecycle

The server participates in the ordered startup sequence (F1.6):

```
config → logger → database → migrations → settings → locale → routes → SERVER → health check → summary
```

**Startup:**

1. Create the HTTP server instance (or HTTPS if TLS is configured).
2. Attach the middleware pipeline and registered routes.
3. Begin listening on `host:port`.
4. Log: `Server listening on http(s)://{host}:{port}`.
5. If the port is in use, log the error and exit with code 1. Do not retry on an adjacent port.

**Shutdown (triggered by SIGTERM, SIGINT, or programmatic call):**

1. Stop accepting new connections.
2. Wait for in-flight requests to complete, up to `shutdownTimeout`.
3. Force-close any remaining connections after the timeout.
4. Log: `Server shut down ({n} requests drained, {m} force-closed)`.

---

## 3. Versioned API Routing (P1.2)

### 3.1 Route Prefix

All API routes are served under a versioned prefix:

```
/api/v1/...
```

The version prefix is a path segment, not a header or query parameter. When a breaking API change is required in the future, a new version prefix (`/api/v2/`) is introduced alongside the existing one.

### 3.2 Route Registration API

Routes are registered through the plugin system (P2.1). Each application or module registers its routes by providing a route definition array to the platform.

```typescript
interface RouteDefinition {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;                          // relative to the namespace prefix
  handler: RouteHandler;
  validation?: {
    params?: ZodSchema;
    query?: ZodSchema;
    body?: ZodSchema;
  };
  middleware?: MiddlewareFunction[];      // route-specific middleware
  rateLimit?: RateLimitConfig;           // per-route override (see Section 6)
  description?: string;                  // for debug mode route listing
}

interface RouteRegistration {
  namespace: string;                     // e.g. 'health', 'settings', or app-specific like 'calendar'
  routes: RouteDefinition[];
}

type RouteHandler = (ctx: RequestContext) => Promise<Response>;
```

**Example — platform health routes:**

```typescript
const healthRoutes: RouteRegistration = {
  namespace: 'health',
  routes: [
    {
      method: 'GET',
      path: '/',                         // resolves to /api/v1/health/
      handler: getHealthStatus,
      description: 'Aggregate health check',
    },
    {
      method: 'GET',
      path: '/ready',                    // resolves to /api/v1/health/ready
      handler: getReadinessProbe,
      description: 'Readiness probe',
    },
  ],
};
```

**Example — application routes:**

```typescript
const calendarRoutes: RouteRegistration = {
  namespace: 'calendar',
  routes: [
    {
      method: 'GET',
      path: '/events',                   // resolves to /api/v1/calendar/events
      handler: listEvents,
      validation: {
        query: z.object({
          from: z.string().datetime(),
          to: z.string().datetime(),
          limit: z.coerce.number().int().min(1).max(100).default(20),
        }),
      },
      description: 'List calendar events',
    },
  ],
};
```

### 3.3 Namespace Rules

| Rule | Description |
|------|-------------|
| Platform namespaces are reserved | `health`, `settings`, `auth`, `audit`, `notifications`, `errors` are reserved for platform use. Applications must not register routes under these namespaces. |
| Application namespaces are unique | Each application registers under its own namespace. Collisions are detected at startup and cause a fatal error. |
| Namespace format | Lowercase alphanumeric and hyphens. Must match `^[a-z][a-z0-9-]{0,31}$`. |
| Path parameters | Standard colon syntax: `/events/:id`. Validated via the `params` schema if provided. |

### 3.4 Route Resolution Order

1. Exact static path match.
2. Parameterised path match (left-to-right, first registered wins).
3. 404 — no matching route.

Route resolution is deterministic. Registration order within a namespace matters for ambiguous parameterised paths. The platform logs a warning at startup if two routes in the same namespace have ambiguous overlap.

---

## 4. Middleware Pipeline (P1.3)

### 4.1 Enforced Middleware Order

The platform defines a fixed middleware pipeline. Every request passes through these stages in order. Applications cannot reorder or remove platform middleware — they can only insert additional middleware at named insertion points.

```
Request
  │
  ├─ 1. Request ID             Generate unique request ID (UUID v4), attach to context
  │
  ├─ 2. Request logging         Log method, path, request ID; log response status on completion
  │
  ├─ 3. Security headers        Attach all security response headers (see Section 6)
  │
  ├─ 4. CORS                    Validate Origin; reject non-localhost origins
  │
  ├─ 5. Rate limiting           Check per-route and global rate limits; respond 429 if exceeded
  │
  ├─ ◆ INSERTION POINT: pre-auth    (applications insert middleware here)
  │
  ├─ 6. Body parsing            Parse JSON body; enforce maxBodySize; reject malformed JSON
  │
  ├─ 7. Request timeout         Start timeout timer; abort with 408 if exceeded
  │
  ├─ 8. Authentication          Pluggable auth middleware (no-op by default; applications provide)
  │
  ├─ ◆ INSERTION POINT: post-auth   (applications insert middleware here)
  │
  ├─ 9. Validation              Validate params, query, body against route's Zod schemas
  │
  ├─ ◆ INSERTION POINT: pre-handler  (applications insert middleware here)
  │
  ├─ 10. Route handler           Execute the matched route handler
  │
  ├─ ◆ INSERTION POINT: post-handler (applications insert middleware here)
  │
  └─ 11. Error handling          Catch unhandled errors; format error response (see P6.1)
```

### 4.2 Named Insertion Points

Applications register middleware at named insertion points. Each insertion point has a defined position in the pipeline and a clear contract for what the middleware can expect.

```typescript
interface MiddlewareRegistration {
  insertionPoint: 'pre-auth' | 'post-auth' | 'pre-handler' | 'post-handler';
  name: string;                  // unique name for debugging and logging
  middleware: MiddlewareFunction;
  order?: number;                // relative order within the insertion point (default 0)
}

type MiddlewareFunction = (
  ctx: RequestContext,
  next: () => Promise<void>,
) => Promise<void>;
```

| Insertion point | When to use | Available context |
|-----------------|-------------|-------------------|
| `pre-auth` | Middleware that must run before authentication — e.g. request transformation, custom CORS overrides for specific paths. | Request ID, parsed URL, raw headers. Body is not yet parsed. |
| `post-auth` | Middleware that needs the authenticated identity — e.g. authorisation checks, tenant scoping, user-specific rate limiting. | Everything from pre-auth plus the authenticated identity (if any). Body is parsed. |
| `pre-handler` | Middleware that runs after validation but before the handler — e.g. caching, request enrichment, context injection. | Everything from post-auth plus validated params/query/body. |
| `post-handler` | Middleware that runs after the handler — e.g. response transformation, response logging, analytics. | Full response from the handler. |

### 4.3 Middleware Ordering Within Insertion Points

When multiple middleware are registered at the same insertion point, they execute in order of their `order` field (ascending). Middleware with the same `order` value execute in registration order.

```typescript
// Example: application registers two post-auth middleware
app.registerMiddleware({
  insertionPoint: 'post-auth',
  name: 'tenant-scoping',
  middleware: tenantScopingMiddleware,
  order: 10,
});

app.registerMiddleware({
  insertionPoint: 'post-auth',
  name: 'feature-flags',
  middleware: featureFlagMiddleware,
  order: 20,
});
// tenant-scoping runs first, then feature-flags
```

### 4.4 Request Context

The `RequestContext` is the single object passed through the middleware chain. It accumulates state as it passes through each stage.

```typescript
interface RequestContext {
  // Set by platform middleware — read-only for applications
  readonly requestId: string;            // UUID v4, set by request ID middleware
  readonly method: string;
  readonly path: string;
  readonly url: URL;
  readonly headers: Readonly<Record<string, string>>;
  readonly startTime: number;            // performance.now() timestamp

  // Set by body parser
  readonly rawBody: Buffer | undefined;
  readonly body: unknown;                // parsed JSON, or undefined

  // Set by auth middleware
  readonly identity: Identity | null;    // null if no auth configured or anonymous

  // Set by validation middleware
  readonly validated: {
    params: Record<string, unknown>;
    query: Record<string, unknown>;
    body: unknown;
  };

  // Mutable state for middleware and handlers
  state: Record<string, unknown>;        // application-specific per-request state

  // Response helpers
  respond(status: number, body: unknown, headers?: Record<string, string>): void;
}
```

---

## 5. Response Envelopes and Validation (P1.4)

### 5.1 Standard Response Shapes

All API responses use one of three envelope shapes. Applications use platform helper functions to construct responses — they do not invent their own formats.

#### 5.1.1 Success Response

```typescript
interface SuccessResponse<T> {
  data: T;
  meta?: Record<string, unknown>;       // optional metadata (timing, cache status, etc.)
}
```

```json
{
  "data": {
    "id": "evt_20260405_001",
    "title": "Sprint planning",
    "start": "2026-04-05T09:00:00Z"
  }
}
```

#### 5.1.2 Error Response

```typescript
interface ErrorResponse {
  error: {
    code: string;                        // machine-readable error code (see P6.1)
    message: string;                     // human-readable message (i18n key or English fallback)
    requestId: string;                   // correlation ID for log lookup
    details?: ValidationError[];         // present only for validation errors (400)
  };
}

interface ValidationError {
  field: string;                         // JSON path to the invalid field (e.g. "body.email")
  code: string;                         // validation error code (e.g. "invalid_format", "required")
  message: string;                      // human-readable description
  expected?: string;                    // what was expected (e.g. "string matching email format")
  received?: string;                    // what was received (e.g. "not-an-email")
}
```

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "requestId": "req_a1b2c3d4",
    "details": [
      {
        "field": "body.email",
        "code": "invalid_format",
        "message": "Must be a valid email address",
        "expected": "string matching email format",
        "received": "not-an-email"
      },
      {
        "field": "query.limit",
        "code": "too_large",
        "message": "Must be at most 100",
        "expected": "number <= 100",
        "received": "500"
      }
    ]
  }
}
```

#### 5.1.3 Paginated Response

```typescript
interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    total: number;                       // total items matching the query
    limit: number;                       // items per page
    offset: number;                      // current offset
    hasMore: boolean;                    // convenience flag: offset + limit < total
  };
  meta?: Record<string, unknown>;
}
```

```json
{
  "data": [
    { "id": "evt_001", "title": "Sprint planning" },
    { "id": "evt_002", "title": "Retrospective" }
  ],
  "pagination": {
    "total": 47,
    "limit": 20,
    "offset": 0,
    "hasMore": true
  }
}
```

### 5.2 Response Helper Functions

The platform provides helper functions that construct responses with the correct shape and HTTP status:

```typescript
// Success responses
function ok<T>(data: T, meta?: Record<string, unknown>): SuccessResponse<T>;
function created<T>(data: T, meta?: Record<string, unknown>): SuccessResponse<T>;
function noContent(): void;

// Paginated responses
function paginated<T>(
  data: T[],
  total: number,
  limit: number,
  offset: number,
  meta?: Record<string, unknown>,
): PaginatedResponse<T>;

// Error responses (see also P6.1 for the full error helper API)
function badRequest(message: string, details?: ValidationError[]): ErrorResponse;
function unauthorized(message?: string): ErrorResponse;
function forbidden(message?: string): ErrorResponse;
function notFound(message?: string): ErrorResponse;
function conflict(message?: string): ErrorResponse;
function tooManyRequests(retryAfter: number): ErrorResponse;
function internalError(requestId: string): ErrorResponse;
```

### 5.3 Request Validation

The validation middleware (pipeline stage 9) validates incoming requests against the Zod schemas defined on the matched route.

**Validation targets:**

| Target | Source | When validated |
|--------|--------|----------------|
| `params` | URL path parameters (`:id`) | Always, if schema provided |
| `query` | URL query string | Always, if schema provided |
| `body` | Parsed JSON body | Only for POST, PUT, PATCH; if schema provided |

**Validation behaviour:**

1. If a schema is provided and validation fails, the middleware responds with a 400 status and an `ErrorResponse` containing structured `ValidationError` details.
2. Unknown properties in the body are stripped (Zod `.strip()` mode) unless the schema explicitly uses `.passthrough()`.
3. Query parameters are coerced to their target types (strings to numbers, booleans) using Zod's `.coerce` transforms.
4. Validated values replace the raw values on `ctx.validated`. Handlers access validated data, never raw input.
5. If no schema is provided for a target, that target is not validated and `ctx.validated` contains the raw parsed values.

---

## 6. Security Hardening (P1.5)

### 6.1 Security Headers

The security headers middleware (pipeline stage 3) attaches the following headers to every response:

| Header | Value | Notes |
|--------|-------|-------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'` | Restrictive default. `'unsafe-inline'` for styles only — required for design token injection. Applications can request CSP amendments through config. |
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing. |
| `X-Frame-Options` | `DENY` | Prevents framing. Redundant with `frame-ancestors 'none'` in CSP but included for older browsers. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Sends origin on cross-origin requests, full URL on same-origin. |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=()` | Disables browser APIs not needed by loke. Applications can amend via config. |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains` | **Only when TLS is enabled.** Not sent over plain HTTP. |
| `X-Request-Id` | `{requestId}` | The correlation ID for this request. Useful for client-side error reporting. |

### 6.2 CSP Configuration

Applications can amend the Content-Security-Policy by declaring additional source directives in their configuration:

```typescript
const cspAmendments = z.object({
  scriptSrc: z.array(z.string()).optional(),   // additional script sources
  styleSrc: z.array(z.string()).optional(),    // additional style sources
  connectSrc: z.array(z.string()).optional(),  // additional connect sources
  imgSrc: z.array(z.string()).optional(),      // additional image sources
}).default({});
```

Amendments are merged with the platform defaults. Applications cannot remove platform directives — only add sources.

### 6.3 CORS Policy

CORS middleware (pipeline stage 4) enforces localhost-only access:

- **Allowed origins:** `http://localhost:*`, `https://localhost:*`, `http://127.0.0.1:*`, `https://127.0.0.1:*`, `http://[::1]:*`, `https://[::1]:*`.
- **Allowed methods:** `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`.
- **Allowed headers:** `Content-Type`, `Authorization`, `X-Request-Id`.
- **Credentials:** Allowed (`Access-Control-Allow-Credentials: true`).
- **Preflight cache:** `Access-Control-Max-Age: 86400` (24 hours).

Requests from non-localhost origins receive a 403 response with no CORS headers.

### 6.4 Rate Limiting

Rate limiting is implemented as an in-memory token bucket, suitable for loke's single-user local model.

**Global defaults:**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `windowMs` | `60000` (1 minute) | Time window for rate counting. |
| `maxRequests` | `100` | Maximum requests per window. |
| `message` | `"Rate limit exceeded"` | 429 response message. |

**Per-route overrides:**

Routes can specify their own rate limit configuration via the `rateLimit` field on `RouteDefinition`:

```typescript
interface RateLimitConfig {
  windowMs: number;
  maxRequests: number;
  message?: string;
}
```

**Example — tighter limit on error reporting endpoint:**

```typescript
{
  method: 'POST',
  path: '/report',
  handler: reportClientError,
  rateLimit: {
    windowMs: 60000,
    maxRequests: 10,
    message: 'Error reporting rate limit exceeded',
  },
}
```

**429 response:**

When the rate limit is exceeded, the server responds with:

- HTTP status `429 Too Many Requests`.
- `Retry-After` header with the number of seconds until the window resets.
- Standard error envelope: `{ error: { code: "RATE_LIMIT_EXCEEDED", message: "...", requestId: "..." } }`.

### 6.5 Additional Security Measures

| Measure | Implementation |
|---------|---------------|
| **Body size limit** | Enforced by body parser middleware (stage 6). Requests exceeding `maxBodySize` receive 413 (Payload Too Large). |
| **JSON-only API** | The API accepts only `Content-Type: application/json` for request bodies. Other content types receive 415 (Unsupported Media Type). |
| **No directory traversal** | Static file serving resolves paths relative to `staticDir` and rejects any path containing `..` or absolute paths. |
| **No server version disclosure** | The `Server` response header is not set. No version information is exposed in headers or error messages. |
| **Request timeout** | Enforced by timeout middleware (stage 7). Requests exceeding `requestTimeout` receive 408 (Request Timeout). |

---

## 7. Configuration Examples

### 7.1 Minimal Configuration (Defaults)

```yaml
# No server config needed — all defaults apply
# Server binds to localhost:3000, serves ./client/dist, no TLS
```

### 7.2 Custom Port with TLS

```yaml
server:
  host: "localhost"
  port: 8443
  tls:
    enabled: true
    cert: "./certs/localhost.pem"
    key: "./certs/localhost-key.pem"
  requestTimeout: 60000
  maxBodySize: "5mb"
```

### 7.3 Application Route Registration (Full Example)

```typescript
import { definePlugin } from '@loke/core';
import { z } from 'zod';

export default definePlugin({
  name: 'my-app',
  routes: {
    namespace: 'my-app',
    routes: [
      {
        method: 'GET',
        path: '/items',
        handler: async (ctx) => {
          const { limit, offset } = ctx.validated.query;
          const { items, total } = await getItems(limit, offset);
          ctx.respond(200, paginated(items, total, limit, offset));
        },
        validation: {
          query: z.object({
            limit: z.coerce.number().int().min(1).max(100).default(20),
            offset: z.coerce.number().int().min(0).default(0),
          }),
        },
        description: 'List items with pagination',
      },
      {
        method: 'POST',
        path: '/items',
        handler: async (ctx) => {
          const item = await createItem(ctx.validated.body);
          ctx.respond(201, created(item));
        },
        validation: {
          body: z.object({
            title: z.string().min(1).max(200),
            description: z.string().max(2000).optional(),
          }),
        },
        description: 'Create an item',
      },
    ],
  },
  middleware: [
    {
      insertionPoint: 'post-auth',
      name: 'my-app-context',
      middleware: async (ctx, next) => {
        ctx.state.appContext = await loadAppContext(ctx.identity);
        await next();
      },
      order: 10,
    },
  ],
});
```

---

## 8. Error Handling Integration

The HTTP server delegates all error handling to the Error Handling Framework (P6). Specifically:

- **Unhandled errors** in route handlers or middleware are caught by the error handling middleware (pipeline stage 11) and formatted as standard error responses. See the Error Handling specification for the complete error response shape, error code registry, and correlation ID flow.
- **Validation errors** (400) are produced by the validation middleware (pipeline stage 9) using the `ValidationError` structure defined in Section 5.1.2.
- **Rate limit errors** (429) are produced by the rate limiting middleware with `Retry-After` headers.
- **Timeout errors** (408) are produced by the timeout middleware.

The server never exposes stack traces, internal paths, or implementation details in any error response.

---

## 9. Relationship to Other Specifications

| Specification | Relationship |
|---------------|-------------|
| **Error Handling (P6)** | The server's error handling middleware delegates to P6. The error response shape defined here (Section 5.1.2) is the canonical shape used by P6.1. |
| **Plugin System (P2)** | Route and middleware registration is performed through the plugin API defined in P2.1. This spec defines the shapes; P2 defines the registration lifecycle. |
| **Health Checks (F1.7)** | The health check endpoints (`/api/v1/health/`) are platform routes registered by F1.7, using the route registration API defined here. |
| **Startup/Shutdown (F1.6)** | The server lifecycle (Section 2.4) is one step in the ordered startup sequence defined by F1.6. |
| **Configuration (F1.5)** | Server configuration (Section 2.1) is a module within the hierarchical config system defined by F1.5. |

---

## 10. Testing Considerations

| Area | Test approach |
|------|---------------|
| Static file serving | Integration test: start server, request known files, verify content type and caching headers. |
| SPA fallback | Integration test: request non-existent HTML path, verify `index.html` is returned. Request `.js` path, verify 404. |
| Route registration | Unit test: register routes, verify resolution. Test namespace collision detection. |
| Middleware pipeline | Integration test: register middleware at each insertion point, verify execution order via side effects. |
| Validation | Unit test: provide valid and invalid payloads against schemas, verify 200 vs 400 responses with correct `ValidationError` details. |
| Security headers | Integration test: make a request, verify all expected headers are present with correct values. |
| CORS | Integration test: send requests with localhost and non-localhost `Origin` headers, verify accept/reject. |
| Rate limiting | Integration test: send requests exceeding the limit, verify 429 with `Retry-After`. |
| Graceful shutdown | Integration test: start long-running request, trigger shutdown, verify request completes and server exits cleanly. |
