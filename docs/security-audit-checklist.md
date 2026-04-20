# Security Audit Checklist

**Purpose:** Run this checklist before every release. Every item must pass or have a documented exception with an assigned owner and remediation date. No release ships with a failing critical item.

**Last reviewed:** 2026-04-05
**Review cadence:** Quarterly (next review: 2026-07-04)

---

## How to Use This Checklist

1. Create a GitHub issue from the `security-audit` issue template for each release.
2. Assign a reviewer for each section. The reviewer must not be the author of the code under review.
3. Check each item. Record pass/fail/NA and any notes.
4. All critical items (marked with `[CRITICAL]`) must pass. No exceptions.
5. Non-critical items that fail must have a tracking issue created before the release ships.
6. The completed checklist is attached to the release notes as an artefact.

---

## 1. Dependency Audit

- [ ] `npm audit` reports zero critical or high vulnerabilities
- [ ] `npm audit` moderate/low vulnerabilities have been reviewed and either patched, mitigated, or documented as non-applicable
- [ ] All direct dependencies are on their latest patch version within the current minor release
- [ ] No dependencies have been added since the last release without a security review
- [ ] New dependencies have been checked for: maintenance status, known vulnerabilities, licence compatibility (Apache 2.0 compatible), and supply chain risk (typosquatting, maintainer compromise)
- [ ] `npm ls --all` output has been reviewed for unexpected transitive dependencies
- [ ] Lockfile (`package-lock.json`) integrity has been verified — no manual edits, no unresolved conflicts
- [ ] [CRITICAL] No dependencies with known CVEs that affect loke's usage of them remain unpatched
- [ ] Automated CVE scanning (GitHub Dependabot / `npm audit signatures`) is active and configured to alert on new vulnerabilities

### Dependency Audit Automation

The following automated checks run in CI on every pull request and on the `main` branch:

```bash
# Run the full dependency audit
npm audit --audit-level=high

# Check for known vulnerabilities in the dependency tree
# (configured in .github/workflows/security.yml)
npx audit-ci --config audit-ci.json

# Verify lockfile integrity
npm ci --ignore-scripts && npm ls --all > /dev/null
```

---

## 2. Privacy Pipeline

- [ ] [CRITICAL] PII detection test suite passes with 100% of known PII patterns detected across all four layers (regex, compromise.js, SLM NER, Presidio)
- [ ] [CRITICAL] Reversible anonymisation round-trip tests pass — original values are correctly restored from placeholders in all test cases
- [ ] [CRITICAL] Mapping table encryption tests pass — mapping tables are encrypted at rest using the configured encryption key, and plaintext mappings are never written to disk
- [ ] [CRITICAL] No PII appears in any log output (check all log levels: debug, info, warn, error)
- [ ] [CRITICAL] No PII appears in error messages or stack traces sent to any external service
- [ ] PII detection false negative rate is within acceptable bounds (< 0.1% on the standard test corpus)
- [ ] PII detection false positive rate has not regressed from the previous release
- [ ] New PII patterns or entity types added since the last release have corresponding test cases
- [ ] Anonymisation performance meets latency targets (< 500ms for typical prompts)
- [ ] The anonymisation pipeline fails closed — if any layer throws an exception, the request is blocked, not sent through unfiltered

### Privacy Pipeline Test Commands

```bash
# Run the PII detection test suite
npm run test:privacy

# Run the anonymisation round-trip tests
npm run test:anonymisation

# Run the mapping table encryption tests
npm run test:mapping-encryption

# Scan log output for PII patterns (should return zero matches)
npm run test:log-leakage
```

---

## 3. Data Storage and Encryption

- [ ] [CRITICAL] Mapping tables (placeholder-to-real-value) are encrypted at rest using AES-256-GCM or equivalent
- [ ] [CRITICAL] API keys and provider credentials are stored in the OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service) — never in plaintext files
- [ ] [CRITICAL] No secrets (API keys, tokens, credentials) appear in the codebase, configuration templates, or test fixtures
- [ ] SQLite database files (conversations, audit logs) are encrypted at rest when enterprise policy requires it
- [ ] Temporary files created during processing are written to encrypted storage and securely deleted after use
- [ ] IndexedDB data in the Electron renderer is scoped and does not contain PII or credentials
- [ ] Electron `userData` directory permissions are restricted to the current user (no group or world read)
- [ ] Backup and export features do not include credentials or unencrypted mapping tables

---

## 4. Electron / Browser Mode Security

- [ ] [CRITICAL] `contextIsolation` is enabled on all BrowserWindow instances
- [ ] [CRITICAL] `nodeIntegration` is disabled in all renderer processes
- [ ] [CRITICAL] `webSecurity` is not disabled in any production configuration
- [ ] [CRITICAL] `sandbox` is enabled on all renderer processes
- [ ] Content Security Policy (CSP) is configured and blocks inline scripts, eval, and untrusted origins
- [ ] `webview` tags are either unused or have `partition` attributes preventing session sharing
- [ ] All IPC channels use `contextBridge.exposeInMainWorld` with a minimal, typed API surface
- [ ] IPC message handlers validate and sanitise all arguments before processing
- [ ] Navigation is restricted — `will-navigate` and `new-window` events are handled to prevent unexpected navigation
- [ ] Remote module is not used (deprecated and insecure)
- [ ] Electron is on a supported release line with the latest security patches
- [ ] Protocol handlers (`loke://`) validate input and do not allow path traversal or command injection
- [ ] Preload scripts do not expose Node.js primitives to the renderer

---

## 5. MCP Security

- [ ] [CRITICAL] MCP server whitelist is enforced — only explicitly approved servers can be connected
- [ ] [CRITICAL] Data flowing through MCP connections passes through the privacy pipeline in both directions (request and response)
- [ ] [CRITICAL] MCP tool call results are treated as untrusted input and sanitised before rendering or processing
- [ ] MCP server authentication credentials are stored securely (OS keychain, not config files)
- [ ] MCP connection transport is encrypted (TLS for remote, Unix sockets with restricted permissions for local)
- [ ] MCP tool calls are logged in the audit trail with full input/output (after anonymisation)
- [ ] Rate limiting is applied to MCP tool calls to prevent abuse
- [ ] MCP servers cannot access local filesystem paths outside explicitly granted directories
- [ ] The MCP broker validates server identity before routing tool calls
- [ ] Enterprise policy blocks are enforced for MCP — if a policy says "no Slack MCP," the broker refuses the connection

---

## 6. Companion Device Security

- [ ] [CRITICAL] Companion device communication is encrypted end-to-end (TLS 1.3 or WireGuard tunnel)
- [ ] [CRITICAL] Companion device pairing requires explicit user approval with device identity verification
- [ ] [CRITICAL] Host verification runs on the companion device before trust is established (image verification, configuration checks)
- [ ] Companion device certificates are pinned after initial pairing — TOFU (Trust On First Use) model with re-verification on certificate change
- [ ] Data sent to companion devices passes through the same privacy pipeline as data sent to cloud LLMs
- [ ] Companion device sessions have configurable timeout and automatic disconnection on inactivity
- [ ] Enterprise policies apply equally to companion devices — no policy bypass through companion routing
- [ ] Companion device discovery (mDNS/Bonjour) is restricted to the local network and cannot be exploited for device enumeration by external parties

---

## 7. Network and API Security

- [ ] [CRITICAL] All outbound HTTPS connections validate TLS certificates — no certificate pinning bypass, no `NODE_TLS_REJECT_UNAUTHORIZED=0`
- [ ] [CRITICAL] API keys are transmitted only over HTTPS and never logged
- [ ] [CRITICAL] The HTTP proxy (terminal mode) does not forward credentials to unintended destinations
- [ ] Rate limiting is applied to outbound API calls to prevent accidental cost overruns
- [ ] DNS resolution is not vulnerable to rebinding attacks in the Electron context
- [ ] CORS policy is enforced for any local HTTP servers (MCP, Presidio microservice, etc.)
- [ ] The proxy configuration (terminal mode) does not allow open relay behaviour — only configured coding LLM endpoints are proxied
- [ ] WebSocket connections (if any) use WSS and validate origin headers

---

## 8. Input Validation and Injection

- [ ] [CRITICAL] Prompt injection tests pass — adversarial prompts cannot cause loke to exfiltrate data, bypass anonymisation, or execute unintended actions
- [ ] [CRITICAL] LLM responses are treated as untrusted — no response content is executed as code or used in SQL/shell/file operations without sanitisation
- [ ] SQL injection tests pass for all SQLite queries (parameterised queries only, no string concatenation)
- [ ] Path traversal tests pass for all file operations (filesystem MCP, export, import, attachments)
- [ ] Command injection tests pass for all shell invocations (terminal mode, git MCP, script execution)
- [ ] XSS tests pass for all user-generated and LLM-generated content rendered in browser mode
- [ ] Markdown/HTML rendering in the UI sanitises content and does not execute embedded scripts or load external resources
- [ ] Template injection tests pass for toke/TOON template processing

---

## 9. Authentication and Authorisation

- [ ] [CRITICAL] Enterprise policy hard blocks cannot be overridden by the local user without administrator escalation
- [ ] Local application settings are protected against modification by other applications on the system
- [ ] Session tokens (if used for companion device or MCP communication) have appropriate expiry and rotation
- [ ] Audit trail entries are append-only and tamper-evident — a user cannot silently delete or modify their own audit log
- [ ] Multi-user scenarios (shared devices) maintain strict isolation between user profiles

---

## 10. Build and Supply Chain

- [ ] [CRITICAL] CI/CD pipeline uses pinned dependency versions (lockfile, not floating ranges)
- [ ] [CRITICAL] Release binaries are code-signed (macOS notarisation, Windows Authenticode)
- [ ] [CRITICAL] Source maps and debug symbols are not included in production builds
- [ ] Reproducible builds — the same commit produces byte-identical output across clean build environments
- [ ] Build environment is audited — no unexpected tools, scripts, or environment variables
- [ ] GitHub Actions workflows use pinned action versions (SHA, not tags) to prevent supply chain attacks
- [ ] Release assets include checksums (SHA-256) for integrity verification

---

## 11. Logging and Monitoring

- [ ] [CRITICAL] No PII, credentials, or mapping table contents appear in application logs at any log level
- [ ] Audit trail captures all security-relevant events: outbound requests, MCP tool calls, policy violations, companion device connections, configuration changes
- [ ] Log rotation is configured to prevent disk exhaustion
- [ ] Error reporting (if enabled) sends only anonymised, structured error data — no stack traces containing file paths, user data, or environment details
- [ ] Debug logging is disabled in production builds

---

## 12. Documentation and Disclosure

- [ ] SECURITY.md is up to date with current reporting channels and SLAs
- [ ] Known security limitations are documented (e.g., "physical access attacks are out of scope")
- [ ] Changelog for this release includes security-relevant changes with CVE references where applicable
- [ ] Any security advisories issued since the last release have been resolved and disclosed

---

## 13. HTTP Server Hardening

- [ ] [CRITICAL] HTTP server binds to `localhost` (127.0.0.1) by default — not `0.0.0.0` or a network interface address
- [ ] [CRITICAL] If a non-localhost binding is configured, a startup warning is emitted and documented as an explicit opt-in
- [ ] [CRITICAL] Security headers are present on all responses: CSP, X-Content-Type-Options (`nosniff`), X-Frame-Options (`DENY`), Referrer-Policy (`strict-origin-when-cross-origin`), Permissions-Policy
- [ ] [CRITICAL] CORS policy restricts `Access-Control-Allow-Origin` to localhost only — no wildcards
- [ ] Rate limiting is active on all API routes with configurable per-route limits
- [ ] Rate limit responses return HTTP 429 with `Retry-After` header
- [ ] Body size limit middleware is registered at a fixed position before route handlers and cannot be bypassed by plugin-registered routes
- [ ] TLS configuration (if enabled for local use) uses strong cipher suites and TLS 1.2+ only
- [ ] HSTS header is set in production configurations
- [ ] Request timeout middleware is active with a sensible default (no unbounded request processing)
- [ ] Error responses do not expose stack traces, internal paths, or implementation details to the client

### HTTP Server Hardening Test Commands

```bash
# Verify security headers on all responses
npm run test:security-headers

# Test CORS localhost restriction
npm run test:cors

# Test rate limiting returns 429
npm run test:rate-limiting

# Test body size limits reject oversized requests
npm run test:body-limits
```

---

## 14. Plugin System Security

- [ ] [CRITICAL] Plugin route registrations are validated — plugins cannot register routes under the `loke` namespace or shadow platform routes
- [ ] [CRITICAL] Plugin lifecycle hooks (onBeforeStart, onAfterStart, onBeforeShutdown) are wrapped in try-catch and cannot crash the platform
- [ ] [CRITICAL] Plugin-registered anonymisation patterns are validated for regex correctness and confidence weight bounds (no zero or negative weights)
- [ ] Plugin configuration schema extensions cannot weaken existing platform constraints (required fields remain required, enum values are not widened)
- [ ] Plugin hook execution is logged with the registering plugin's identity
- [ ] Plugin-registered middleware is only allowed at documented named insertion points — not before CORS, body size limit, or request ID stages
- [ ] File system access outside the application data directory by plugin code is logged as a security event
- [ ] No plugin has access to raw mapping table contents, encryption keys, or OS credential store entries outside its declared scope
- [ ] Plugin health checks are isolated — a failing plugin health check does not report the overall system as healthy

### Plugin System Test Commands

```bash
# Verify plugin namespace enforcement
npm run test:plugin-namespaces

# Test hook isolation (failing hooks don't crash platform)
npm run test:plugin-hooks

# Test anonymisation pattern validation
npm run test:plugin-patterns
```

---

## 15. OAuth Flow Verification

- [ ] [CRITICAL] All OAuth authorisation code flows use PKCE with S256 challenge method
- [ ] [CRITICAL] State parameter is cryptographically random and validated on callback — requests with missing or mismatched state are rejected
- [ ] [CRITICAL] Access and refresh tokens are stored exclusively in the OS credential store (macOS Keychain, Windows Credential Manager) — never in plaintext files, environment variables, or the SQLite database
- [ ] [CRITICAL] OAuth tokens never appear in log output at any log level (added to automatic redaction list)
- [ ] Refresh token rotation is requested from OAuth providers that support it
- [ ] Access tokens are not cached beyond their expiry time
- [ ] Token refresh failures are handled gracefully — the user is prompted to re-authorise, not shown a raw error
- [ ] Redirect URI uses a loopback address with an ephemeral port — no fixed port that could be pre-bound by a malicious application
- [ ] OAuth error responses from providers are logged (without tokens) for debugging
- [ ] Token revocation is performed on disconnect/logout

### OAuth Flow Test Commands

```bash
# Verify PKCE is enforced on all OAuth flows
npm run test:oauth-pkce

# Verify tokens are stored in OS credential store
npm run test:oauth-storage

# Verify token redaction in log output
npm run test:oauth-log-redaction
```

---

## 16. Input Sanitisation

- [ ] [CRITICAL] HTML stripping utilities remove all tags, attributes, and event handlers from user-provided and external-API-provided strings before DOM insertion
- [ ] [CRITICAL] Log injection prevention is active — newlines, carriage returns, and control characters are stripped or escaped in all values written to log output
- [ ] [CRITICAL] Schema validation with Zod (or equivalent) strips unknown properties from request bodies by default — no unexpected fields pass through
- [ ] SQL queries use parameterised statements exclusively — no string concatenation for SQL anywhere in the platform or application code
- [ ] i18n translation strings are validated at load time — values containing `<script`, `javascript:`, or `on[event]=` patterns are rejected
- [ ] i18n interpolation (`{{name}}`) HTML-escapes all parameter values by default
- [ ] Locale identifiers are sanitised to alphanumeric characters, hyphens, and underscores only — path separators are stripped
- [ ] API response bodies from external integrations are validated against expected schemas before processing

### Input Sanitisation Test Commands

```bash
# Run HTML stripping tests
npm run test:sanitisation

# Run log injection prevention tests
npm run test:log-injection

# Run schema validation tests (unknown property stripping)
npm run test:schema-validation

# Run i18n injection tests
npm run test:i18n-injection
```

---

## 17. Rate Limiting

- [ ] Per-route rate limits are configured for all API endpoints
- [ ] Rate limit defaults are sensible for a single-user local application (not so low as to impede normal use, not so high as to be meaningless)
- [ ] Rate limit exceeded responses return HTTP 429 with a `Retry-After` header
- [ ] Rate limiting cannot be bypassed via `X-Forwarded-For`, `X-Real-IP`, or other header manipulation
- [ ] Rate limit state is stored in-memory (appropriate for single-user local apps) and resets on server restart
- [ ] Rate limit configuration is validated at startup — invalid values (zero, negative, non-numeric) are rejected
- [ ] Plugin-registered routes inherit default rate limits unless explicitly configured otherwise

### Rate Limiting Test Commands

```bash
# Verify 429 responses when limits exceeded
npm run test:rate-limiting

# Verify no bypass via header manipulation
npm run test:rate-limit-bypass

# Verify plugin routes inherit rate limits
npm run test:rate-limit-plugins
```

---

## 18. CSP Policy Verification

- [ ] [CRITICAL] `script-src` is locked to `'self'` — no `'unsafe-inline'`, `'unsafe-eval'`, or wildcard origins
- [ ] [CRITICAL] `style-src` is locked to `'self'` — or `'self'` plus specific trusted origins if a CSS framework requires it (documented exception required)
- [ ] [CRITICAL] `connect-src` is locked to `'self'` plus the explicitly configured LLM provider and integration API origins — no wildcards
- [ ] `default-src` is set to `'none'` or `'self'` as a fallback
- [ ] `img-src` is restricted to `'self'` and `data:` (if inline images are required)
- [ ] `frame-ancestors` is set to `'none'` (equivalent to X-Frame-Options DENY)
- [ ] `object-src` is set to `'none'`
- [ ] `base-uri` is set to `'self'`
- [ ] CSP violations are reported (via `report-uri` or `report-to` if a reporting endpoint is configured)
- [ ] Applications cannot weaken the platform CSP — only tighten it by adding additional restrictions

### CSP Policy Test Commands

```bash
# Verify CSP headers on all responses
npm run test:csp

# Verify no unsafe-inline or unsafe-eval in production builds
npm run test:csp-strict

# Verify connect-src matches configured provider origins
npm run test:csp-connect
```

---

## 19. Integration Adapter Auditing

- [ ] [CRITICAL] Circuit breaker thresholds have been reviewed — failure count and cooldown period are within platform-enforced bounds (minimum cooldown 5s, minimum failure threshold 2)
- [ ] [CRITICAL] Retry backoff is exponential with platform-enforced limits (maximum retry count 10, minimum backoff interval 500ms)
- [ ] [CRITICAL] All adapter HTTP requests have a mandatory timeout (hard cap 120 seconds)
- [ ] Adapters declare their target endpoints at registration time — requests to undeclared endpoints are flagged
- [ ] Credentials are retrieved from the OS credential store at request time by the base HTTP client — adapter code never handles raw credential values
- [ ] Adapter error responses are logged with correlation IDs (without credentials or tokens)
- [ ] Response bodies from external APIs are validated against expected schemas
- [ ] Circuit breaker state transitions (closed -> open -> half-open -> closed) are logged
- [ ] `Retry-After` headers from external APIs are respected — the adapter does not retry before the indicated time
- [ ] Connection pool limits are configured to prevent a single adapter from exhausting platform resources

### Integration Adapter Test Commands

```bash
# Verify circuit breaker thresholds
npm run test:circuit-breaker

# Verify retry backoff configuration
npm run test:retry-backoff

# Verify timeout enforcement
npm run test:adapter-timeout

# Verify credential isolation
npm run test:adapter-credentials
```

---

## Release Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Reviewer 1 (privacy pipeline) | | | |
| Reviewer 2 (Electron/browser) | | | |
| Reviewer 3 (MCP/network) | | | |
| Reviewer 4 (platform: HTTP, plugins, OAuth, i18n) | | | |
| Release owner | | | |

**Release decision:**

- [ ] All CRITICAL items pass
- [ ] All non-critical failures have tracking issues
- [ ] Release is approved for shipping
