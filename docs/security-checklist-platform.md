# Security Audit Checklist — Platform Layer

**Purpose:** Platform-layer security verification. Run this checklist alongside the base `security-audit-checklist.md` before every release that includes platform layer changes. Every item must pass or have a documented exception with an assigned owner and remediation date.

**Last reviewed:** 2026-04-22
**Review cadence:** Quarterly (next review: 2026-07-22)
**Parent document:** `docs/security-audit-checklist.md`
**Related threat model:** `docs/threat-model-platform.md`

---

## How to Use This Checklist

1. Create a GitHub issue from the `security-audit` issue template for each release.
2. Assign a reviewer for the platform layer — the reviewer must not be the author of the code under review.
3. Check each item. Record pass / fail / NA and any notes.
4. All items must pass before the platform layer ships. Non-passing items require a tracking issue before release.

---

## HTTP Hardening

- [ ] CSP header configured in P1.5 `default_config()`: `default-src 'self'`, no `unsafe-eval`, `frame-ancestors 'none'`
- [ ] `X-Content-Type-Options: nosniff` present on all responses
- [ ] `X-Frame-Options: DENY` present on all responses
- [ ] `Referrer-Policy: strict-origin-when-cross-origin` present on all responses
- [ ] `Permissions-Policy` disables camera, microphone, geolocation, payment, and USB
- [ ] HTTP server binds to `127.0.0.1` by default; non-loopback binding logs a startup warning

## CORS

- [ ] CORS restricted to localhost-only origins in P1.3 middleware
- [ ] Non-localhost `Origin` headers rejected with HTTP 403
- [ ] `Access-Control-Allow-Origin` is never set to `*`

## Rate Limiting

- [ ] Per-route rate limits configured in P1.5 `check_rate_limit`
- [ ] Default limit is 100 requests per minute per client identifier
- [ ] Rate-limited requests return HTTP 429 with no sensitive information in the response body

## Plugin Sandboxing

- [ ] All registered plugins reviewed before install; only plugins from trusted sources installed
- [ ] Plugin manifests validated by `plugin.registry.register` at registration time
- [ ] Plugins registered at `privacy.before` hooks documented and reviewed for PII handling
- [ ] Hook execution errors are caught and logged; they do not halt the pipeline

## OAuth

- [ ] OAuth token storage verified as OS keychain only (P5.2 / F1.5); no token columns in SQLite schema
- [ ] No OAuth token appears in any log output at any log level
- [ ] Token expiry checked before every use; expired tokens trigger silent refresh
- [ ] OAuth state parameter used for CSRF protection; PKCE used where the provider supports it

## Input Sanitisation

- [ ] P5.4 `sanitise_unknown_props` applied to all external JSON bodies before processing
- [ ] `strip_html` applied to all user-supplied values rendered into HTML output
- [ ] `clamp_length` applied to all user-supplied string fields stored in the database

## SQL

- [ ] Parameterised queries only in all F6.1 database access; no string concatenation in SQL
- [ ] `sql_escape` is used only as a supplementary safeguard — parameterised queries remain mandatory
- [ ] No raw user input concatenated into any SQL string anywhere in the codebase

## Log Injection

- [ ] `prevent_log_injection` from P5.4 applied to all user-supplied values written to logs
- [ ] Locale codes validated before being written to logs
- [ ] Integration adapter request/response bodies are not logged (headers only at debug level, with Authorization stripped)

## Secrets

- [ ] No API keys in source code or configuration files committed to the repository
- [ ] No API keys in any log output at any log level
- [ ] OS keychain storage verified for all API keys and OAuth tokens (F1.5)
- [ ] `ooke audit` (dependency audit) reports zero critical or high vulnerabilities

## Audit

- [ ] All AI calls logged in F6.2 audit trail: timestamp, correlation ID, provider, model, token counts, cost, governance decision
- [ ] No prompt content written to the audit trail
- [ ] No PII placeholder mappings written to the audit trail
- [ ] Audit trail is append-only; no delete or update operations on audit records

## Kill Switch

- [ ] `G1.6 kill_switch.is_global_active()` checked before every AI call in the router
- [ ] Kill switch activation blocks all outbound AI requests immediately
- [ ] Kill switch state is persisted across restarts
- [ ] Kill switch activation and deactivation events are written to the audit trail
