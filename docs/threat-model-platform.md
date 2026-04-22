# loke Threat Model — Platform Layer

**Version:** 1.0
**Date:** 2026-04-22
**Parent document:** `docs/threat-model.md`
**Scope:** Platform layer (P1–P6, X3, X4) threat analysis and mitigations

---

## Table of Contents

1. [HTTP Server Attack Surface](#1-http-server-attack-surface)
2. [Plugin System Trust](#2-plugin-system-trust)
3. [OAuth Token Handling](#3-oauth-token-handling)
4. [i18n Injection](#4-i18n-injection)
5. [Middleware Bypass](#5-middleware-bypass)
6. [Platform Layer Trust Boundaries](#6-platform-layer-trust-boundaries)

---

## 1. HTTP Server Attack Surface

The platform HTTP server (P1) listens on `127.0.0.1:11430` (API) and `127.0.0.1:11431` (proxy). It is served by ooke's native HTTP binding.

### Threat: Cross-origin request forgery from a malicious web page

A page loaded in the user's browser could make requests to `127.0.0.1:11430` and trigger AI calls or read sensitive data.

**Mitigation:** CORS is restricted to localhost-only origins in the P1.3 CORS middleware. The `Origin` header is checked on every non-safe request. Requests from non-localhost origins are rejected with HTTP 403 before reaching any route handler.

### Threat: Denial of service via request flooding from local process

A misbehaving local process (e.g. a malicious plugin, a runaway script) could flood the API server and degrade service.

**Mitigation:** Per-route rate limiting is enforced by the P1.5 security middleware. Default limit: 100 requests per minute per client identifier. Limits are configurable per route. Requests exceeding the limit receive HTTP 429.

### Threat: Content injection via HTTP response headers

A compromised response from a cloud LLM could contain header injection characters that alter the browser's security context.

**Mitigation:** All responses include mandatory security headers set by P1.5: `Content-Security-Policy`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`, and `Permissions-Policy`. The CSP restricts script, style, image, font, and connect sources to `'self'` with `frame-ancestors 'none'`.

### Threat: External network binding misconfiguration

An operator misconfigures loke to bind to `0.0.0.0`, exposing the API to the local network or internet.

**Mitigation:** The server binds to `127.0.0.1` by default. Changing the bind address requires explicit configuration and logs a `WARN: HTTP server binding to non-loopback address` warning at startup. External binding is not supported in the default ooke.toml.

---

## 2. Plugin System Trust

Plugins run in the same ooke native binary process as the core engine. There is no process-level sandbox between plugin code and core code at the toke/ooke level.

### Threat: Malicious plugin exfiltrates PII

A plugin registered at the `privacy.after` hook receives the anonymised prompt (placeholders, not originals). A plugin registered at `privacy.before` receives the raw prompt before anonymisation.

**Trust model:** All installed plugins are trusted. The plugin registry does not sandbox plugins. Plugin installation requires explicit user action (adding to `ooke.toml` and restarting). The user is solely responsible for the plugins they install.

**Mitigation:** The plugin contract (P2.5) documents that `privacy.before` hooks receive raw prompts. Plugin authors are advised to treat raw prompts as sensitive and not log or transmit them. Future versions of ooke may introduce a native sandbox binding for plugin isolation; that capability is tracked as a future enhancement.

**Residual risk:** A malicious plugin with `privacy.before` registration can read raw prompt content. Users should only install plugins from trusted sources.

### Threat: Plugin conflicts corrupt pipeline state

Two plugins registered at the same insertion point produce conflicting mutations.

**Mitigation:** The plugin registry validates hook names at registration time (P2.1). Named insertion points are validated. Hooks execute in registration order; a hook's output is the next hook's input. Hook execution errors are caught, logged, and cause the affected hook to be skipped — they do not halt the pipeline.

### Future mitigation

ooke sandbox binding (tracked separately) will provide process-level isolation for plugin execution. When available, plugins will be downgraded from trusted to partially trusted and will communicate with the core engine via IPC.

---

## 3. OAuth Token Handling

The integration framework (P5) supports OAuth 2.0 flows for external service adapters (Google Drive, Slack, Jira, etc.).

### Threat: Token theft via log exposure

An OAuth access token is accidentally logged at debug level when an integration adapter records its request headers.

**Mitigation:** Tokens are never passed as strings through the logging layer. The `prevent_log_injection` utility in P5.4 sanitises values before logging. Token values are fetched from the OS keychain immediately before use and held in memory only for the duration of the HTTP call. The adapter framework (P5) does not log Authorization headers.

### Threat: Token use after expiry

A cached token is used to make an API call after it has expired, triggering a 401 that leaks the token value in an error log.

**Mitigation:** Token expiry is checked before every use (F1.5 / P5.2). Expired tokens trigger a silent refresh via the stored refresh token. If refresh fails, the user is prompted to re-authenticate. The 401 response body is never logged.

### Threat: Token stored in application database rather than keychain

A developer accidentally stores a token in the SQLite database without encryption.

**Mitigation:** The integration framework stores tokens in the OS keychain only (P5.2 / F1.5). The SQLite schema contains no token columns. Code review checklist (security-checklist-platform.md) includes a verification step.

---

## 4. i18n Injection

The internationalisation system (P4) renders locale strings into HTML templates.

### Threat: Stored XSS via malicious locale file

An attacker supplies a locale file containing `<script>` tags in translation values. When rendered into the UI, the script executes.

**Mitigation:** All locale string values are passed through the `t()` function in P4.1. Values interpolated into HTML output are passed through `strip_html()` from P5.4 before rendering. The `t()` function does not evaluate interpolated values as HTML.

### Threat: Injection via interpolation parameter

A user-supplied value is interpolated into a locale string using string concatenation rather than the `{{param}}` placeholder syntax, bypassing HTML escaping.

**Mitigation:** The `t_params()` function in P4.1 uses `{{0}}`, `{{1}}`, etc. placeholder syntax. Interpolated values are substituted after HTML escaping. Direct string concatenation with user-supplied values in UI code is a code review violation — the security checklist (X1.6) includes a verification step.

### Threat: Locale code injection

A user-supplied locale code is used in a log message without sanitisation, enabling log injection.

**Mitigation:** Locale codes are validated against the registered locale list before use. The `set_locale()` function rejects unknown codes. Locale codes are alphanumeric with hyphens only (e.g. `en-AU`).

---

## 5. Middleware Bypass

The P1 middleware stack enforces authentication, CORS, rate limiting, and security headers. If the stack order is violated, protections may be bypassed.

### Threat: Auth bypass by inserting a route before the auth middleware

A plugin or misconfigured route handler is registered before the auth middleware and responds to requests without authentication.

**Mitigation:** Middleware execution order is enforced by the P1.2 middleware stack. Named insertion points (`before_auth`, `after_auth`, `before_route`, `after_route`) are validated at registration. Plugins may only register handlers at documented insertion points; they cannot prepend handlers before the security middleware tier. The middleware order is: CORS → rate limit → security headers → auth → route handlers.

### Threat: Security headers stripped by a middleware that modifies the response

A middleware modifies the HTTP response and accidentally removes security headers set by P1.5.

**Mitigation:** Security headers are set as the final step before flushing the response, after all middleware has run. Response-modifying middleware cannot run after the security header step.

---

## 6. Platform Layer Trust Boundaries

The platform layer introduces the following new trust boundaries beyond those documented in the parent threat model.

| Boundary | Description | Trust | Mitigation |
|----------|-------------|-------|------------|
| Plugin boundary | Plugin code executes in the same process as the core engine | Trusted (installed by user) | Plugin manifest validation; hook isolation; future: ooke sandbox |
| HTTP server boundary | Requests arrive from localhost clients (browser UI, CLI, coding tools) | Partially trusted (localhost) | CORS; rate limiting; auth middleware; security headers |
| Integration adapter boundary | Adapters call external services (OAuth providers, cloud APIs) via HTTP | Untrusted (external) | Token expiry checks; keychain storage; circuit breaker; response sanitisation |
| Locale file boundary | Locale files are loaded from disk and rendered into HTML | Partially trusted (local files) | HTML escaping of all interpolated values; locale code validation |
| OAuth provider boundary | OAuth 2.0 flows redirect through external identity providers | Untrusted (external) | State parameter CSRF protection; PKCE where supported; token stored in keychain |
