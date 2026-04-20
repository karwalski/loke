# loke Threat Model

**Version:** 1.1
**Date:** 2026-04-05
**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)
**Review cadence:** Quarterly self-audit; external audit before v1.0 release

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Trust Boundaries](#2-trust-boundaries)
3. [Data Flow Analysis](#3-data-flow-analysis)
4. [Attack Surface Enumeration](#4-attack-surface-enumeration)
5. [STRIDE Threat Analysis](#5-stride-threat-analysis)
6. [Platform Layer Threats](#6-platform-layer-threats)
7. [Threat Catalogue](#7-threat-catalogue)
8. [Risk Assessment Matrix](#8-risk-assessment-matrix)
9. [Mitigations](#9-mitigations)
10. [Residual Risks and Accepted Limitations](#10-residual-risks-and-accepted-limitations)
11. [Review Schedule](#11-review-schedule)

---

## 1. System Overview

loke is a locally-run intelligence layer that sits between users and external LLMs. It processes data on-device — anonymising PII, compressing prompts, routing requests — before anything leaves the user's machine. loke operates in two modes:

- **Browser mode:** Electron-based desktop application with Chromium rendering
- **Terminal mode:** CLI that proxies coding LLM traffic (Claude Code, Codex, Gemini CLI, etc.)

### Core Components

| Component | Role | Trust Level |
|-----------|------|-------------|
| Privacy pipeline (regex, NLP, SLM NER, Presidio) | Multi-layer PII detection and anonymisation | Trusted (local) |
| Mapping table store | Reversible anonymisation lookup (placeholder <-> real value) | Trusted (local, encrypted) |
| Token optimisation pipeline (TOON, LLMLingua, toke) | Prompt compression before transmission | Trusted (local) |
| LLM router | Selects target model (local or cloud) based on sensitivity, cost, complexity | Trusted (local) |
| Local SLM inference (Ollama, MLX, node-llama-cpp) | On-device model execution | Trusted (local) |
| MCP broker | Routes MCP tool calls to local, companion, or cloud servers | Trusted (local) |
| Companion device interface | Encrypted channel to high-power local device | Partially trusted (verified local network) |
| Electron shell (browser mode) | Chromium renderer, Node.js main process | Trusted (local), renderer is sandboxed |
| CLI proxy (terminal mode) | HTTP proxy intercepting coding LLM API traffic | Trusted (local) |
| Cloud LLM APIs | External model providers (Anthropic, OpenAI, Google, etc.) | Untrusted |
| Cloud MCP servers | External tool providers (Google Drive, Slack, Jira, etc.) | Untrusted |
| Web content (browser mode) | Pages loaded in the Chromium renderer | Untrusted |

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     USER'S DEVICE (Trust Boundary A)                │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                 loke Core Engine (Trust Boundary B)           │   │
│  │                                                              │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────────────┐  │   │
│  │  │  Privacy    │  │   Token      │  │    LLM Router       │  │   │
│  │  │  Pipeline   │  │   Optimiser  │  │                     │  │   │
│  │  │  (4 layers) │  │  (TOON,      │  │  ┌──────────────┐  │  │   │
│  │  │            │  │   LLMLingua,  │  │  │ Semantic     │  │  │   │
│  │  │            │  │   toke)       │  │  │ Router       │  │  │   │
│  │  └─────┬──────┘  └──────┬───────┘  │  │ RouteLLM     │  │  │   │
│  │        │                │          │  └──────────────┘  │  │   │
│  │        ▼                ▼          └─────────┬─────────┘  │   │
│  │  ┌───────────────────────────┐               │            │   │
│  │  │    Mapping Table Store    │               │            │   │
│  │  │    (AES-256-GCM encrypted)│               │            │   │
│  │  └───────────────────────────┘               │            │   │
│  │                                              │            │   │
│  │  ┌──────────────┐  ┌────────────────────┐    │            │   │
│  │  │ Audit Trail  │  │ Policy Engine      │    │            │   │
│  │  │ (append-only)│  │ (enterprise rules) │    │            │   │
│  │  └──────────────┘  └────────────────────┘    │            │   │
│  └──────────────────────────────────────────────┼────────────┘   │
│                                                  │                │
│  ┌────────────────┐  ┌───────────────┐           │                │
│  │ Local SLM      │  │ MCP Broker    │◄──────────┤                │
│  │ (Ollama/MLX)   │  │               │           │                │
│  └────────────────┘  └───────┬───────┘           │                │
│                              │                   │                │
│  ┌───────────────────────────┼───────────────────┼────────────┐   │
│  │  Electron Shell / CLI     │                   │            │   │
│  │  (UI + proxy layer)       │                   │            │   │
│  └───────────────────────────┼───────────────────┼────────────┘   │
└──────────────────────────────┼───────────────────┼────────────────┘
                               │                   │
          ┌────────────────────┼───────────────────┼────────────┐
          │    LOCAL NETWORK (Trust Boundary C)     │            │
          │                                        │            │
          │  ┌─────────────────────┐               │            │
          │  │  Companion Device   │               │            │
          │  │  (Mac Mini/Studio)  │               │            │
          │  │  Encrypted channel  │               │            │
          │  └─────────────────────┘               │            │
          └────────────────────────────────────────┼────────────┘
                                                   │
          ┌────────────────────────────────────────┼────────────┐
          │         INTERNET (Trust Boundary D — Untrusted)     │
          │                                        │            │
          │  ┌──────────────┐  ┌──────────────┐    │            │
          │  │ Cloud LLM    │  │ Cloud MCP    │◄───┘            │
          │  │ APIs         │  │ Servers      │                 │
          │  └──────────────┘  └──────────────┘                 │
          └─────────────────────────────────────────────────────┘
```

---

## 2. Trust Boundaries

### Boundary A: User's Device

Everything running on the user's machine. This is the primary trust perimeter. Data inside this boundary is considered under the user's control. Threats at this boundary involve other software on the device, physical access, and malware.

### Boundary B: loke Core Engine

The core processing pipeline within loke. This is the highest-trust zone. Components here have access to unencrypted PII, mapping tables, and credentials. A compromise of any component inside Boundary B is a full compromise of user data.

### Boundary C: Local Network (Companion Devices)

Companion devices on the local network. These are partially trusted after explicit pairing and host verification. Data crossing this boundary must be encrypted and should pass through the privacy pipeline. Threats include network-level attacks, compromised companion devices, and rogue devices on the network.

### Boundary D: Internet (Cloud Providers)

External cloud LLM APIs and cloud MCP servers. Fully untrusted. No raw PII should ever cross this boundary. All data crossing Boundary D must have been anonymised and compressed. Responses from beyond this boundary are treated as untrusted input.

### Boundary E: Electron Renderer (Browser Mode)

The Chromium renderer process is sandboxed and isolated from the Node.js main process. Web content loaded in the renderer is untrusted. Communication between renderer and main process goes through a restricted IPC bridge (`contextBridge`). A renderer compromise should not grant access to the core engine.

### Boundary F: Platform ↔ Plugin

Plugins register routes, middleware, configuration schema extensions, anonymisation patterns, and lifecycle hooks through a controlled registration API. Plugin code runs in the same Node.js process as the platform but is constrained to its declared extension points. A malicious or buggy plugin could inject routes, tamper with middleware ordering, or register overly broad configuration schemas. The platform must validate all plugin registrations before activating them.

### Boundary G: Platform ↔ OAuth Provider

OAuth 2.0 flows cross from the local platform to external authorisation servers. The platform handles authorisation codes, access tokens, and refresh tokens. Tokens are stored in the OS credential store. The authorisation code exchange and token refresh occur over HTTPS but are vulnerable to interception if PKCE is not enforced or if the redirect URI is hijackable. The OAuth provider is semi-trusted — trusted for authentication, untrusted for data content.

### Boundary H: Platform ↔ External API (Integration Adapters)

Integration adapters connect the platform to external services (calendars, conferencing, backup destinations, custom APIs). Each adapter uses the base HTTP client with retry, circuit breaker, and timeout. External APIs are untrusted — responses must be validated and sanitised. A compromised external API could return malicious payloads, and adapter misconfiguration could leak credentials or data.

---

## 3. Data Flow Analysis

### 3.1 Outbound Prompt Flow (Primary Data Path)

```
User input (may contain PII)
    │
    ▼
[1] Privacy Pipeline: Regex scan → NLP NER → SLM NER → Presidio
    │                  PII detected and replaced with placeholders ($c1, $l2, $p3)
    │
    ▼
[2] Mapping Table: Placeholder → real value stored in encrypted local storage
    │
    ▼
[3] Token Optimisation: TOON formatting → LLMLingua compression → toke encoding
    │
    ▼
[4] Router Decision: Local SLM? Companion device? Cloud LLM?
    │
    ├──► [Local] SLM inference on device (no data leaves device)
    │
    ├──► [Companion] Encrypted channel to companion device on local network
    │
    └──► [Cloud] HTTPS to cloud LLM API (anonymised, compressed prompt only)
```

**Critical data at each stage:**

| Stage | Data Present | Sensitivity | Storage |
|-------|-------------|-------------|---------|
| User input | Raw PII, proprietary data | Maximum | In-memory only |
| After anonymisation | Placeholders, no PII | Reduced | In-memory only |
| Mapping table | PII ↔ placeholder mappings | Maximum | Encrypted on disk |
| After compression | Anonymised, compressed prompt | Low | In-memory, then transmitted |
| Audit log | Metadata, anonymised prompts, routing decisions | Medium | Encrypted on disk |

### 3.2 Inbound Response Flow

```
Cloud LLM / Companion / Local SLM response
    │
    ▼
[5] Response contains placeholders ($c1, $l2, $p3)
    │
    ▼
[6] De-anonymisation: Placeholders replaced with real values from mapping table
    │
    ▼
[7] Response rendered to user (with original PII restored)
```

**Risk:** If the LLM hallucinates or fabricates content around placeholders, de-anonymisation may produce incorrect or misleading output. This is a correctness issue, not a privacy issue.

### 3.3 MCP Tool Call Flow

```
LLM requests tool call (e.g., read file, query database)
    │
    ▼
[8] MCP Broker: Check whitelist → Route to server
    │
    ├──► [Local MCP] Execute on device, filter result through privacy pipeline
    │
    ├──► [Companion MCP] Forward to companion device over encrypted channel
    │
    └──► [Cloud MCP] Proxy to cloud server, filter data in both directions
    │
    ▼
[9] Tool result passed through privacy pipeline before returning to LLM
```

### 3.4 Companion Device Communication Flow

```
loke on user's device
    │
    ▼
[10] Discovery: mDNS/Bonjour on local network
    │
    ▼
[11] Pairing: User approves device, host verification runs
    │
    ▼
[12] Encrypted channel established (TLS 1.3 / WireGuard)
    │
    ▼
[13] Data sent: anonymised prompts, model inference requests, MCP tool calls
    │
    ▼
[14] Data received: inference results, tool call results
```

### 3.5 Terminal Mode Proxy Flow

```
Coding LLM CLI (e.g., claude-code, codex)
    │
    ▼
[15] loke HTTP proxy intercepts API request
    │
    ▼
[16] Request body passed through privacy pipeline (anonymise code, strip secrets)
    │
    ▼
[17] Modified request forwarded to cloud LLM API
    │
    ▼
[18] Response intercepted, placeholders restored, returned to coding LLM CLI
```

---

## 4. Attack Surface Enumeration

### 4.1 Local Attack Surfaces

| Surface | Entry Point | Attacker Profile |
|---------|-------------|-----------------|
| Mapping table storage | SQLite database file on disk | Malware, other local applications, forensic recovery |
| Credential storage | OS keychain or config files | Malware, other local applications |
| Electron main process | IPC from renderer, protocol handlers, CLI arguments | Malicious web content (via renderer), local applications |
| Electron renderer | Web content, user-pasted content, LLM-generated HTML/markdown | Malicious websites, prompt injection via LLM responses |
| Local SLM | Model files, configuration | Supply chain attack on model distribution |
| Audit log | SQLite database file on disk | Malware (read sensitive metadata), user (tamper with evidence) |
| CLI proxy | HTTP listener on localhost | Other local applications, local network if misconfigured |
| Presidio microservice | HTTP listener on localhost | Other local applications, local network if misconfigured |
| Configuration files | JSON/YAML on disk | Malware, other local applications |

### 4.2 Network Attack Surfaces

| Surface | Entry Point | Attacker Profile |
|---------|-------------|-----------------|
| Cloud LLM API connections | HTTPS outbound | Network interceptor (corporate proxy, ISP, nation-state) |
| Cloud MCP server connections | HTTPS outbound | Network interceptor, compromised cloud service |
| Companion device channel | Local network (mDNS discovery, encrypted tunnel) | Rogue device on local network, ARP spoofing, compromised companion |
| Companion device discovery | mDNS/Bonjour broadcast | Network eavesdropper, rogue responder |
| Update mechanism | HTTPS to update server | Compromised update server, DNS hijacking |

### 4.3 Platform Layer Attack Surfaces

| Surface | Entry Point | Attacker Profile |
|---------|-------------|-----------------|
| Platform HTTP server | localhost:3000 (configurable host:port) | Other local applications, local network if host binding misconfigured |
| Plugin registration API | Route, middleware, config schema, hook registration | Malicious or buggy plugin code |
| OAuth redirect URI | HTTP callback endpoint during authorisation code grant | Local application hijacking the redirect, network interceptor |
| i18n locale files | JSON files in `locales/` directory | Malicious locale file contribution, supply chain |
| Integration adapter interface | Adapter connect/disconnect/health/domain methods | Compromised external API, adapter impersonation |
| Middleware pipeline | Named insertion points for app-injected middleware | Middleware ordering manipulation, auth bypass |
| Plugin configuration schemas | Zod schema extensions merged at startup | Schema poisoning to weaken validation |
| Rate limiter | Per-route rate limit configuration | Bypass via header manipulation, IP spoofing on non-localhost bindings |

### 4.4 Data-Level Attack Surfaces

| Surface | Risk | Attacker Profile |
|---------|------|-----------------|
| Mapping table contents | Full PII recovery if compromised | Anyone with access to the encrypted database and key |
| Anonymisation bypass | PII sent to cloud LLM undetected | Crafted input designed to evade all four detection layers |
| Prompt injection | LLM manipulated to exfiltrate data via tool calls or crafted responses | Adversarial content in user input, web pages, or MCP tool results |
| LLM response manipulation | Malicious content in LLM responses rendered in the UI | Compromised or adversarial LLM provider |
| Model poisoning | Local SLM produces incorrect PII classifications | Supply chain attack on model weights |
| Semantic cache poisoning | Cached response served for a semantically similar but meaningfully different prompt | Crafted prompts designed to pollute the cache |

---

## 5. STRIDE Threat Analysis

### 5.1 Spoofing

| ID | Threat | Component | Description |
|----|--------|-----------|-------------|
| S-1 | Companion device impersonation | Companion interface | A rogue device on the local network responds to mDNS discovery and impersonates a legitimate companion device, intercepting data sent to it. |
| S-2 | Cloud LLM API spoofing | LLM router | DNS hijacking or network interception redirects API calls to a malicious endpoint that captures anonymised prompts and returns crafted responses. |
| S-3 | MCP server impersonation | MCP broker | A malicious MCP server impersonates a legitimate one (e.g., filesystem MCP) and receives tool calls intended for the real server. |
| S-4 | Update server spoofing | Auto-updater | A spoofed update server pushes a compromised loke binary to users. |
| S-5 | Local process impersonation | CLI proxy | Another process on the user's device binds to the proxy port before loke, intercepting all coding LLM traffic. |

### 5.2 Tampering

| ID | Threat | Component | Description |
|----|--------|-----------|-------------|
| T-1 | Mapping table tampering | Mapping store | Malware modifies the mapping table, causing de-anonymisation to produce incorrect results (e.g., swapping names to attribute actions to the wrong person). |
| T-2 | Audit log tampering | Audit trail | A user or attacker modifies or deletes audit log entries to hide policy violations or data exfiltration. |
| T-3 | Policy configuration tampering | Policy engine | An attacker modifies enterprise policy files on disk, weakening anonymisation requirements or adding cloud providers to the allowlist. |
| T-4 | Model file tampering | Local SLM | An attacker replaces local model files with poisoned versions that intentionally misclassify PII, allowing sensitive data to pass through anonymisation undetected. |
| T-5 | Prompt modification in transit | Companion channel | An attacker with network access modifies prompts or responses in transit between loke and a companion device. |
| T-6 | Cache poisoning | Semantic cache | An attacker crafts prompts that are semantically similar to legitimate queries but have different intent, poisoning the cache so future legitimate queries receive incorrect or malicious responses. |

### 5.3 Repudiation

| ID | Threat | Component | Description |
|----|--------|-----------|-------------|
| R-1 | Audit trail deletion | Audit trail | A user deletes the local audit log to remove evidence of policy violations or data sent to cloud providers. |
| R-2 | Configuration change without logging | Policy engine | An administrator changes enterprise policy without the change being recorded, making it impossible to determine what policy was active at a given time. |
| R-3 | Untraceable data exfiltration | Privacy pipeline | If the privacy pipeline fails silently (no log entry), there is no record that unfiltered data was sent externally. |

### 5.4 Information Disclosure

| ID | Threat | Component | Description | Severity |
|----|--------|-----------|-------------|----------|
| I-1 | PII leakage through anonymisation bypass | Privacy pipeline | Crafted input evades all four PII detection layers, causing raw PII to be sent to a cloud LLM. | Critical |
| I-2 | Mapping table exposure | Mapping store | The encrypted mapping table is exfiltrated, and the encryption key is also obtained (from memory, keychain compromise, or weak key derivation), allowing full PII recovery. | Critical |
| I-3 | MCP data exfiltration | MCP broker | A cloud LLM uses MCP tool calls to read local files, database contents, or other sensitive data, which is then included in LLM responses sent to the cloud. | Critical |
| I-4 | Companion device MITM | Companion interface | An attacker on the local network intercepts communication between loke and a companion device, reading anonymised prompts and inference results. | High |
| I-5 | Prompt injection causing data leak | Privacy pipeline / MCP | An adversarial prompt (injected via web content, MCP tool result, or user input) instructs the LLM to include sensitive data in its response, bypassing anonymisation on the response path. | Critical |
| I-6 | Log file PII leakage | Logging | Debug or error logging inadvertently includes raw PII, mapping table contents, or credentials in log files that may be shared for debugging. | High |
| I-7 | Memory forensics | All components | PII exists in unencrypted form in process memory during processing. A memory dump or swap file could expose this data. | Medium |
| I-8 | Electron renderer data leak | Browser mode | Malicious web content in the renderer exploits an IPC vulnerability to read data from the main process (PII, credentials, mapping tables). | Critical |
| I-9 | Side-channel leakage | Privacy pipeline | The length, timing, or structure of anonymised prompts reveals information about the original content (e.g., the number of PII entities, the approximate length of replaced values). | Low |
| I-10 | API key exposure | Credential storage | API keys stored outside the OS keychain (e.g., in environment variables, config files, or process memory) are accessible to other applications. | High |
| I-11 | Semantic cache information leak | Semantic cache | A user queries the cache with crafted prompts to retrieve responses from another user's session (relevant in shared-device scenarios). | Medium |
| I-12 | Dependency data exfiltration | Third-party libraries | A compromised or malicious dependency exfiltrates data during loke's processing pipeline. | Critical |

### 5.5 Denial of Service

| ID | Threat | Component | Description |
|----|--------|-----------|-------------|
| D-1 | Privacy pipeline resource exhaustion | Privacy pipeline | An extremely large input (e.g., a multi-megabyte document) overwhelms the NLP or SLM NER layers, causing loke to become unresponsive. |
| D-2 | MCP tool call flooding | MCP broker | A cloud LLM issues a large volume of MCP tool calls, exhausting local resources (CPU, memory, disk I/O). |
| D-3 | Companion device saturation | Companion interface | Excessive requests to the companion device saturate its inference capacity, causing timeouts for all queued work. |
| D-4 | Semantic cache exhaustion | Semantic cache | An attacker fills the semantic cache with junk entries, evicting legitimate cached responses and forcing all requests to go to cloud LLMs (increasing cost). |
| D-5 | Local model OOM | Local SLM | Loading a model that exceeds available memory causes system-wide memory pressure and potential crashes. |
| D-6 | Disk exhaustion via audit logs | Audit trail | Unbounded audit log growth fills the disk, causing loke and potentially the entire system to malfunction. |

### 5.6 Elevation of Privilege

| ID | Threat | Component | Description |
|----|--------|-----------|-------------|
| E-1 | Renderer to main process escape | Electron shell | A vulnerability in the Electron IPC bridge or context isolation allows web content in the renderer to execute code in the Node.js main process, gaining full system access. |
| E-2 | MCP server privilege escalation | MCP broker | A cloud MCP server exploits the MCP broker to access local MCP servers it should not have access to (e.g., filesystem MCP), or to bypass the privacy pipeline. |
| E-3 | Policy bypass through companion device | Policy engine | An attacker routes requests through a companion device to bypass enterprise policy blocks that apply only to the primary device. |
| E-4 | Local privilege escalation via proxy | CLI proxy | The HTTP proxy in terminal mode runs with the user's full permissions. An exploit in the proxy could be leveraged for local privilege escalation. |
| E-5 | Prompt injection to tool execution | MCP broker / local SLM | An adversarial prompt convinces the local SLM or cloud LLM to execute MCP tool calls that the user did not intend (e.g., writing files, sending messages, modifying data). |

---

## 6. Platform Layer Threats

The platform layer (epics P1-P6) introduces new attack surfaces not covered by the foundation-layer analysis above. This section analyses threats specific to the HTTP server, plugin system, OAuth handling, i18n framework, and integration adapters.

### 6.1 HTTP Server Attack Surfaces (P1)

| ID | Threat | Description | STRIDE | Likelihood | Impact |
|----|--------|-------------|--------|-----------|--------|
| PL-1 | Localhost binding bypass | The HTTP server is configured to bind to `localhost` by default. If a user or misconfiguration changes the host to `0.0.0.0` or a network interface address, the server becomes accessible from the local network or beyond, exposing all API endpoints to unauthenticated external access. | Information Disclosure, Elevation of Privilege | Medium | Critical |
| PL-2 | Middleware ordering attack | The platform enforces a specific middleware order (request ID -> logging -> CORS -> body size limit -> timeout -> auth -> validation -> error handling). If a plugin injects middleware at a named insertion point that executes before auth or validation, it could bypass security controls. | Elevation of Privilege, Tampering | Low | High |
| PL-3 | Route injection via plugins | A malicious plugin registers routes that shadow platform routes (e.g., `/api/v1/health`, `/api/v1/settings`) and intercepts requests intended for legitimate endpoints. The plugin could return forged data or capture credentials from request bodies. | Spoofing, Tampering | Medium | High |
| PL-4 | Request smuggling | Malformed HTTP requests exploit differences between the platform's HTTP parser and any upstream proxies. In a local-first context this is lower risk, but if TLS termination or a reverse proxy is added, request smuggling could bypass security middleware. | Tampering, Elevation of Privilege | Low | Medium |
| PL-5 | Body size DoS | An attacker (local application or, if host binding is misconfigured, a network client) sends extremely large request bodies to exhaust memory. The body size limit middleware mitigates this, but misconfiguration or a route registered before the body size middleware could be vulnerable. | Denial of Service | Medium | Medium |
| PL-6 | Missing security headers | If CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, or Permissions-Policy headers are missing or misconfigured, the browser-served UI becomes vulnerable to XSS, clickjacking, or MIME-sniffing attacks. | Information Disclosure | Medium | High |

### 6.2 Plugin System Threats (P2)

| ID | Threat | Description | STRIDE | Likelihood | Impact |
|----|--------|-------------|--------|-----------|--------|
| PL-7 | Malicious plugin code | A plugin registers legitimate-looking extension points but includes code that reads mapping tables, credentials, or PII from the platform's in-process memory. Since plugins run in the same Node.js process, there is no process-level isolation. | Information Disclosure | Medium | Critical |
| PL-8 | Hook injection | A plugin registers `onBeforeStart` or `onBeforeShutdown` hooks that modify platform state — for example, disabling the privacy pipeline, altering logging configuration to suppress audit entries, or replacing the credential store with a leaking implementation. | Tampering, Elevation of Privilege | Low | Critical |
| PL-9 | Config schema poisoning | A plugin extends the base Zod configuration schema with overly permissive definitions (e.g., making a required security field optional, or widening an enum to accept unsafe values). This weakens validation for the entire platform. | Tampering | Low | High |
| PL-10 | Anonymisation pattern abuse | A plugin registers anonymisation patterns with extremely low confidence weights or overly broad detection regexes that produce excessive false positives, effectively disabling anonymisation by making it unusable. Alternatively, a plugin could register patterns that intentionally miss its own domain's sensitive data. | Tampering, Information Disclosure | Medium | High |
| PL-11 | Extension point abuse — health check manipulation | A plugin registers a health check that always returns healthy, masking a genuine subsystem failure. Alternatively, a malicious health check could leak system information in its response. | Spoofing, Information Disclosure | Low | Medium |
| PL-12 | File system access outside designated directories | A plugin accesses files outside its designated directory (e.g., reading `/etc/passwd`, the user's SSH keys, or other applications' data). Without filesystem sandboxing, any registered plugin code has the same filesystem access as the loke process. | Information Disclosure, Elevation of Privilege | Medium | High |

### 6.3 OAuth Token Handling Threats (P5.2)

| ID | Threat | Description | STRIDE | Likelihood | Impact |
|----|--------|-------------|--------|-----------|--------|
| PL-13 | Token theft from OS credential store | An attacker with local access (malware, compromised application) reads OAuth access and refresh tokens from the OS credential store. On macOS, Keychain items are protected by the application's code signature and user authorisation, but a compromised loke binary or a user-approved malicious app could access them. | Information Disclosure | Low | High |
| PL-14 | Refresh token replay | An attacker obtains a refresh token (via credential store compromise, memory dump, or interception) and replays it against the OAuth provider to obtain new access tokens. If the provider does not enforce refresh token rotation (one-time use), a stolen refresh token provides persistent access. | Spoofing | Low | High |
| PL-15 | Authorisation code interception | During the OAuth authorisation code flow, the authorisation code is delivered to a redirect URI. If the redirect URI is a local HTTP endpoint without PKCE, another application on the device could intercept the code by racing to bind the port or by registering a matching custom URI scheme. | Spoofing | Medium | High |
| PL-16 | State parameter bypass | If the OAuth state parameter is not validated on the callback, an attacker could perform a CSRF attack by tricking the user into completing an authorisation flow that links the attacker's account to the user's loke instance. | Spoofing, Tampering | Medium | Medium |
| PL-17 | Token leakage in logs or errors | OAuth tokens inadvertently included in error messages, log output, or API response bodies. Even at debug log level, tokens must never appear in plaintext. | Information Disclosure | Medium | High |

### 6.4 i18n Injection Threats (P4)

| ID | Threat | Description | STRIDE | Likelihood | Impact |
|----|--------|-------------|--------|-----------|--------|
| PL-18 | Locale file poisoning | A malicious contributor submits a locale file containing crafted translation strings with embedded HTML, JavaScript, or control characters. If the i18n `t()` function does not sanitise output before DOM insertion, this enables stored XSS via translation strings. | Tampering, Elevation of Privilege | Medium | High |
| PL-19 | Template injection via translation strings | Translation strings use `{{name}}` interpolation. If interpolation parameters are rendered without escaping, an attacker who controls a parameter value could inject HTML or script content through the interpolation mechanism. | Information Disclosure, Elevation of Privilege | Medium | High |
| PL-20 | Key collision between platform and application | An application registers locale keys that collide with platform `loke.*` keys, overriding platform translations. This could change security-relevant UI text — for example, changing a "Block this request" button label to "Allow this request." | Tampering | Low | Medium |
| PL-21 | Locale file path traversal | If the locale loader accepts user-controlled locale identifiers without sanitising path components, an attacker could load arbitrary JSON files from outside the `locales/` directory by using path traversal (e.g., `../../package.json`). | Information Disclosure | Low | Medium |

### 6.5 Integration Adapter Threats (P5)

| ID | Threat | Description | STRIDE | Likelihood | Impact |
|----|--------|-------------|--------|-----------|--------|
| PL-22 | Adapter impersonation | A malicious plugin registers an integration adapter that presents itself as a legitimate service (e.g., a calendar adapter) but forwards data to an attacker-controlled endpoint. The platform's adapter interface does not verify the destination of adapter HTTP calls. | Spoofing, Information Disclosure | Medium | High |
| PL-23 | Circuit breaker manipulation | An attacker triggers repeated failures on an integration (e.g., by causing DNS resolution failures) to force the circuit breaker into the open state, denying the user access to the service. Alternatively, manipulating the half-open state to prevent recovery. | Denial of Service | Medium | Medium |
| PL-24 | Retry amplification | A misconfigured or malicious adapter sets aggressive retry parameters (high retry count, short backoff), amplifying a single failed request into a flood of outbound requests. This could trigger rate limits at the external API, cause cost overruns, or create a local resource exhaustion. | Denial of Service | Medium | Medium |
| PL-25 | Adapter credential leakage | An adapter logs, transmits, or caches credentials in locations outside the OS credential store — for example, including an OAuth bearer token in a debug log, storing it in the SQLite database, or passing it as a query parameter instead of an Authorization header. | Information Disclosure | Medium | High |
| PL-26 | Timeout exhaustion | An adapter with excessively long or missing timeout configuration holds connections open indefinitely, exhausting the platform's connection pool and blocking other adapters or platform operations. | Denial of Service | Low | Medium |

### 6.6 Platform Trust Boundary Summary

```
                    ┌────────────────────────────────────────────┐
                    │        External OAuth Provider              │
                    │        (Boundary G — Semi-trusted)          │
                    └──────────────┬─────────────────────────────┘
                                   │ Auth codes, tokens (HTTPS)
                    ┌──────────────▼─────────────────────────────┐
                    │        Platform Layer (Boundary B)          │
                    │                                            │
                    │  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
                    │  │ HTTP     │  │ Plugin   │  │ Integr.  │ │
                    │  │ Server   │  │ System   │  │ Adapters │ │
                    │  │ (P1)     │  │ (P2)     │  │ (P5)     │ │
                    │  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
                    │       │             │             │        │
                    │  ┌────▼─────────────▼─────────────▼─────┐  │
                    │  │ i18n (P4) · OAuth (P5.2) · UI (P3)  │  │
                    │  │ Error Handling (P6) · Sanitisation   │  │
                    │  └──────────────────────────────────────┘  │
                    └──────────────┬─────────────────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼──────────┐  ┌─────▼─────────┐  ┌──────▼──────────┐
    │ Plugin Code         │  │ External API  │  │ Locale Files    │
    │ (Boundary F)        │  │ (Boundary H)  │  │ (Community)     │
    │ Routes, hooks,      │  │ Untrusted     │  │ Partially       │
    │ config, patterns    │  │ responses     │  │ trusted         │
    └─────────────────────┘  └───────────────┘  └─────────────────┘
```

---

## 7. Threat Catalogue

The following table consolidates the highest-priority threats with their risk ratings.

### Foundation and Application Layer Threats

| ID | Threat | Likelihood | Impact | Risk | Priority |
|----|--------|-----------|--------|------|----------|
| I-1 | PII leakage through anonymisation bypass | Medium | Critical | **Critical** | P0 |
| I-2 | Mapping table exposure | Low | Critical | **High** | P0 |
| I-3 | MCP data exfiltration | Medium | Critical | **Critical** | P0 |
| I-5 | Prompt injection causing data leak | High | Critical | **Critical** | P0 |
| E-1 | Renderer to main process escape | Low | Critical | **High** | P0 |
| I-8 | Electron renderer data leak via IPC | Low | Critical | **High** | P0 |
| I-12 | Dependency data exfiltration | Low | Critical | **High** | P1 |
| T-4 | Model file tampering / poisoning | Low | High | **Medium** | P1 |
| S-1 | Companion device impersonation | Medium | High | **High** | P1 |
| I-4 | Companion device MITM | Medium | High | **High** | P1 |
| E-5 | Prompt injection to tool execution | High | High | **Critical** | P0 |
| I-6 | Log file PII leakage | Medium | High | **High** | P1 |
| I-10 | API key exposure | Medium | High | **High** | P1 |
| E-2 | MCP server privilege escalation | Low | High | **Medium** | P2 |
| T-1 | Mapping table tampering | Low | Medium | **Medium** | P2 |
| T-2 | Audit log tampering | Medium | Medium | **Medium** | P2 |
| S-5 | Local proxy port hijacking | Low | High | **Medium** | P2 |
| D-1 | Privacy pipeline resource exhaustion | Medium | Medium | **Medium** | P2 |
| T-6 | Semantic cache poisoning | Low | Medium | **Low** | P3 |
| I-9 | Side-channel leakage | Low | Low | **Low** | P3 |
| I-7 | Memory forensics | Low | Medium | **Low** | P3 |

### Platform Layer Threats

| ID | Threat | Likelihood | Impact | Risk | Priority |
|----|--------|-----------|--------|------|----------|
| PL-7 | Malicious plugin code (in-process memory access) | Medium | Critical | **Critical** | P0 |
| PL-1 | Localhost binding bypass | Medium | Critical | **Critical** | P0 |
| PL-8 | Hook injection (disable privacy pipeline) | Low | Critical | **High** | P0 |
| PL-3 | Route injection via plugins (shadow platform routes) | Medium | High | **High** | P1 |
| PL-15 | OAuth authorisation code interception | Medium | High | **High** | P1 |
| PL-18 | Locale file poisoning (stored XSS) | Medium | High | **High** | P1 |
| PL-19 | Template injection via translation strings | Medium | High | **High** | P1 |
| PL-22 | Adapter impersonation (data forwarding) | Medium | High | **High** | P1 |
| PL-25 | Adapter credential leakage | Medium | High | **High** | P1 |
| PL-12 | Plugin filesystem access outside designated dirs | Medium | High | **High** | P1 |
| PL-6 | Missing or misconfigured security headers | Medium | High | **High** | P1 |
| PL-9 | Config schema poisoning | Low | High | **Medium** | P2 |
| PL-10 | Anonymisation pattern abuse | Medium | High | **High** | P1 |
| PL-13 | Token theft from OS credential store | Low | High | **Medium** | P2 |
| PL-14 | Refresh token replay | Low | High | **Medium** | P2 |
| PL-17 | Token leakage in logs or errors | Medium | High | **High** | P1 |
| PL-2 | Middleware ordering attack | Low | High | **Medium** | P2 |
| PL-16 | OAuth state parameter bypass | Medium | Medium | **Medium** | P2 |
| PL-5 | Body size DoS | Medium | Medium | **Medium** | P2 |
| PL-23 | Circuit breaker manipulation | Medium | Medium | **Medium** | P2 |
| PL-24 | Retry amplification | Medium | Medium | **Medium** | P2 |
| PL-20 | i18n key collision (security text override) | Low | Medium | **Low** | P3 |
| PL-21 | Locale file path traversal | Low | Medium | **Low** | P3 |
| PL-4 | Request smuggling | Low | Medium | **Low** | P3 |
| PL-11 | Health check manipulation | Low | Medium | **Low** | P3 |
| PL-26 | Timeout exhaustion | Low | Medium | **Low** | P3 |

---

## 8. Risk Assessment Matrix

### Likelihood Definitions

| Level | Definition |
|-------|-----------|
| **High** | Likely to be attempted by common attackers. Known techniques exist. Requires no special access beyond what a typical user or malicious web content has. |
| **Medium** | Requires moderate attacker capability. May require local network access, a compromised dependency, or a targeted attack. |
| **Low** | Requires significant attacker capability. May require physical access, insider access, or exploitation of an unknown vulnerability. |

### Impact Definitions

| Level | Definition |
|-------|-----------|
| **Critical** | PII is exposed to an external party. User's trust in loke's core promise is broken. Regulatory consequences possible. |
| **High** | Sensitive data is at risk but not confirmed exposed. Credentials compromised. System integrity undermined. |
| **Medium** | Degraded functionality. Incorrect behaviour that could lead to user confusion or policy non-compliance. Data correctness affected. |
| **Low** | Minor information leakage (metadata, timing). Inconvenience. No PII exposure. |

### Risk Calculation

| | Low Impact | Medium Impact | High Impact | Critical Impact |
|---|-----------|--------------|-------------|----------------|
| **High Likelihood** | Medium | High | Critical | Critical |
| **Medium Likelihood** | Low | Medium | High | Critical |
| **Low Likelihood** | Low | Low-Medium | Medium-High | High |

---

## 9. Mitigations

### 9.1 PII Leakage (I-1) — Critical

**Threat:** Crafted input evades all four PII detection layers.

**Mitigations:**
1. **Defence in depth:** Four independent detection layers (regex, NLP, SLM NER, Presidio) with different detection methodologies. An input must evade all four to pass undetected.
2. **Fail closed:** If any layer encounters an error or timeout, the entire request is blocked. No fallback to "send anyway."
3. **Continuous test corpus:** Maintain a growing corpus of adversarial PII patterns, including obfuscated PII (e.g., SSNs with spaces, emails with Unicode confusables, names in non-Latin scripts). Run this corpus against every build.
4. **User review (beta):** During the beta period, outbound prompts are displayed for user review before transmission. The user is the final layer.
5. **Configurable strictness:** Enterprise deployments can require all four layers to agree before allowing transmission, rather than any single layer being sufficient to flag PII.
6. **Regular model updates:** Keep the SLM NER model and Presidio recognisers updated as new PII patterns emerge.

### 9.2 Mapping Table Exposure (I-2) — High

**Threat:** Encrypted mapping table is exfiltrated along with its encryption key.

**Mitigations:**
1. **AES-256-GCM encryption at rest** with a key derived from the user's OS keychain credential, not stored on disk.
2. **Key derivation:** Use PBKDF2 or Argon2 with a high iteration count. The raw key never exists on disk.
3. **Memory protection:** Zero mapping table plaintext from memory after each lookup. Use secure buffer allocation where the platform supports it.
4. **Access control:** Restrict file permissions on the mapping table database to the current user only. No group or world access.
5. **Mapping table rotation:** Support periodic rotation where old mappings are re-encrypted under a new key.
6. **Tamper detection:** Include HMAC on mapping table entries. Detect and alert on any modification outside the normal application flow.

### 9.3 MCP Data Exfiltration (I-3) — Critical

**Threat:** Cloud LLM uses MCP tool calls to access local data and exfiltrate it.

**Mitigations:**
1. **Explicit whitelist:** No MCP servers are connected by default. The user must explicitly approve each server.
2. **Bidirectional privacy filtering:** All data flowing through MCP connections — both requests and responses — passes through the privacy pipeline. PII in tool results is anonymised before being sent to a cloud LLM.
3. **Scoped access:** Filesystem MCP is restricted to explicitly granted directories. Database MCP has query restrictions. No MCP server gets blanket access to the user's system.
4. **Tool call approval (beta):** During the beta period, MCP tool calls initiated by cloud LLMs require explicit user approval.
5. **Rate limiting:** Limit the number and frequency of MCP tool calls per session to prevent exfiltration-by-volume.
6. **Audit trail:** Every MCP tool call is logged with full (anonymised) input and output. Anomalous patterns trigger alerts.
7. **Data volume caps:** Limit the total volume of data that can be returned from MCP tool calls in a single session.

### 9.4 Prompt Injection (I-5, E-5) — Critical

**Threat:** Adversarial content in user input, web content, or MCP tool results manipulates the LLM into exfiltrating data or executing unintended tool calls.

**Mitigations:**
1. **Input/output scanning:** Use LLM Guard scanners to detect known prompt injection patterns in both inputs and outputs.
2. **Instruction hierarchy:** When constructing prompts, use clear delimiters between system instructions, user content, and tool results. Mark untrusted content explicitly.
3. **Tool call validation:** MCP tool calls requested by the LLM are validated against the user's intent and the current session context. Out-of-scope tool calls are flagged.
4. **Response sanitisation:** LLM responses are sanitised before rendering. No response content is executed as code, used in database queries, or treated as trusted instructions.
5. **NeMo Guardrails:** Deploy programmable rails that define what the LLM is and is not allowed to do in the loke context.
6. **Garak testing:** Run Garak vulnerability probes (prompt injection, data leakage, jailbreak) against the full pipeline as part of the release process.
7. **Web content isolation:** In browser mode, web page content is sandboxed and never directly concatenated with LLM prompts. It passes through the privacy pipeline, which also serves as an injection filter.

### 9.5 Companion Device Security (S-1, I-4, T-5) — High

**Threat:** Rogue or compromised device on the local network impersonates a companion device or intercepts communication.

**Mitigations:**
1. **Explicit pairing:** Companion device pairing requires user approval with a visual verification code (similar to Bluetooth pairing).
2. **Host verification:** Before trust is established, loke verifies the companion device's identity through image verification, configuration checks, and software version validation.
3. **Certificate pinning (TOFU):** After initial pairing, the companion device's TLS certificate is pinned. Any certificate change triggers re-verification with user notification.
4. **End-to-end encryption:** All communication uses TLS 1.3 or WireGuard with forward secrecy. No plaintext traffic, even on the local network.
5. **Privacy pipeline on both sides:** Data sent to the companion device passes through the same privacy pipeline as data sent to cloud LLMs. The companion device is not implicitly trusted with raw PII.
6. **Session timeout:** Companion device sessions expire after configurable inactivity and require re-authentication.

### 9.6 Electron Security (E-1, I-8) — High

**Threat:** Malicious web content escapes the renderer sandbox or exploits IPC to access the main process.

**Mitigations:**
1. **Context isolation:** `contextIsolation: true` on all BrowserWindows. The renderer and preload scripts run in separate JavaScript contexts.
2. **Node integration disabled:** `nodeIntegration: false` in all renderers. No direct access to Node.js APIs from web content.
3. **Sandbox enabled:** `sandbox: true` on all renderers. Chromium's multi-process sandbox is active.
4. **Minimal IPC surface:** The `contextBridge` exposes only the minimum API needed for the renderer to communicate with the main process. Every IPC channel validates and sanitises arguments.
5. **Content Security Policy:** Strict CSP headers block inline scripts, eval, and connections to untrusted origins.
6. **Navigation restrictions:** `will-navigate` and `new-window` events are handled to prevent the renderer from navigating to unexpected URLs.
7. **Electron updates:** Track the Electron release schedule and apply security patches promptly.

### 9.7 Dependency Supply Chain (I-12) — High

**Threat:** A compromised or malicious npm package exfiltrates data during loke's processing pipeline.

**Mitigations:**
1. **Automated CVE scanning:** GitHub Dependabot and `npm audit` run on every pull request and on the main branch. Critical/high vulnerabilities block merge.
2. **Lockfile enforcement:** `npm ci` in CI ensures the exact dependency tree from the lockfile is used. No floating versions.
3. **Dependency review:** New dependencies undergo security review before adoption: maintenance status, known vulnerabilities, licence, maintainer reputation.
4. **Pinned CI actions:** GitHub Actions workflows use SHA-pinned action versions, not mutable tags.
5. **Package signature verification:** `npm audit signatures` verifies that packages were published through the npm registry's signing infrastructure.
6. **Minimal dependency surface:** Prefer dependencies with small transitive dependency trees. Audit transitive dependencies, not just direct ones.
7. **Runtime network monitoring (future):** Consider sandboxing dependencies at runtime to detect unexpected network calls.

### 9.8 API Key and Credential Security (I-10) — High

**Threat:** API keys stored insecurely are accessible to malware or other applications.

**Mitigations:**
1. **OS keychain storage:** All API keys and credentials stored in the OS keychain (macOS Keychain, Windows Credential Manager, Linux Secret Service). Never in plaintext config files.
2. **Memory hygiene:** Credentials loaded into memory only when needed and zeroed after use.
3. **Environment variable warnings:** If a user provides credentials via environment variables (common in terminal mode), warn them that environment variables are accessible to other processes.
4. **No logging of credentials:** Credentials are never included in log output at any log level.
5. **Proxy credential isolation:** In terminal mode, the proxy does not forward loke's own credentials to unintended endpoints. Credentials are matched to specific API endpoints.

### 9.9 Platform HTTP Server Security (PL-1, PL-2, PL-5, PL-6) — Critical/High

**Threat:** Localhost binding bypass, middleware ordering attacks, body size DoS, missing security headers.

**Mitigations:**
1. **Default localhost binding:** The server binds to `localhost` (127.0.0.1) by default. Binding to `0.0.0.0` or a non-loopback address requires explicit configuration and produces a startup warning that the server is network-accessible.
2. **Enforced middleware order:** The platform defines the middleware execution order. Plugin-injected middleware is only allowed at named insertion points that are documented to execute after CORS, body size limits, and before error handling. Plugins cannot inject middleware before the request ID, logging, or CORS stages.
3. **Body size limit enforcement:** The body size limit middleware is registered by the platform at a fixed position in the pipeline. Plugin-registered routes inherit this limit. Routes that require larger bodies must explicitly opt in with a documented maximum.
4. **Security headers by default:** CSP, X-Content-Type-Options, X-Frame-Options, Referrer-Policy, and Permissions-Policy headers are set by the platform's security middleware. Applications cannot remove them, only tighten them.
5. **Rate limiting:** Per-route rate limiting is active by default with sensible defaults for a single-user local application. Rate limit configuration is validated at startup.

### 9.10 Plugin System Security (PL-7, PL-8, PL-9, PL-10, PL-12) — Critical/High

**Threat:** Malicious plugins running in-process with access to platform internals.

**Mitigations:**
1. **Plugin registration validation:** All plugin registrations are validated against a strict schema. Route namespaces are enforced — plugins cannot register routes under the `loke` namespace. Configuration schema extensions are merged with precedence rules that prevent weakening existing constraints.
2. **Hook auditing:** Lifecycle hooks (onBeforeStart, onAfterStart, onBeforeShutdown) are logged with the registering plugin's identity. Hook execution is wrapped in a try-catch that prevents a failing hook from crashing the platform.
3. **Anonymisation pattern review:** Plugin-registered anonymisation patterns are validated for regex correctness and confidence weight bounds. Patterns with zero or negative confidence weights are rejected.
4. **Filesystem access policy:** Plugins should only access files within their designated directories. File operations outside the application data directory are logged as security events. (Note: full sandboxing within a shared Node.js process is a residual risk — see Section 10.)
5. **Plugin provenance (future):** A plugin signing and verification system is planned to allow users to verify that plugins come from trusted sources.

### 9.11 OAuth Token Security (PL-13, PL-14, PL-15, PL-16, PL-17) — High

**Threat:** Token theft, authorisation code interception, refresh token replay, state parameter bypass, token leakage.

**Mitigations:**
1. **PKCE enforcement:** All OAuth authorisation code flows use PKCE (Proof Key for Code Exchange) with S256 challenge method. This prevents authorisation code interception by other local applications.
2. **State parameter validation:** Every OAuth flow generates a cryptographically random state parameter that is validated on the callback. Requests with missing or mismatched state are rejected.
3. **OS credential store:** Access and refresh tokens are stored exclusively in the OS credential store (macOS Keychain, Windows Credential Manager). Never in plaintext files, environment variables, or the SQLite database.
4. **Refresh token rotation:** The platform requests refresh token rotation from the OAuth provider where supported. When rotation is active, each refresh token is single-use — replaying a used token is detected by the provider.
5. **Token redaction in logs:** OAuth tokens are added to the structured logger's automatic redaction list. Tokens are masked in all log output, error messages, and API responses regardless of log level.
6. **Short-lived access tokens:** Access tokens are not cached beyond their expiry time. The platform refreshes tokens only when needed and never persists access tokens to disk.

### 9.12 i18n Security (PL-18, PL-19, PL-20, PL-21) — High

**Threat:** Locale file poisoning, template injection, key collisions, path traversal.

**Mitigations:**
1. **Output escaping:** The `t()` function HTML-escapes all interpolated parameter values by default. Raw (unescaped) interpolation is not supported — all output is safe for DOM insertion.
2. **Locale file validation:** Locale files are validated against a schema at load time. Translation values must be plain strings (no HTML tags, no script content). Values containing `<script`, `javascript:`, `on[event]=` patterns are rejected.
3. **Namespace enforcement:** The `loke.*` key prefix is reserved for platform translations. Application-registered locale keys that collide with `loke.*` keys are rejected at startup with a clear error message.
4. **Path sanitisation:** The locale loader sanitises locale identifiers to alphanumeric characters, hyphens, and underscores only. Path separators and traversal sequences are stripped. Only files within the configured `locales/` directory are loaded.

### 9.13 Integration Adapter Security (PL-22, PL-23, PL-24, PL-25, PL-26) — High

**Threat:** Adapter impersonation, circuit breaker manipulation, retry amplification, credential leakage, timeout exhaustion.

**Mitigations:**
1. **Adapter endpoint validation:** Integration adapters must declare their target endpoints at registration time. The base HTTP client logs all outbound request destinations. Requests to undeclared endpoints are flagged as security events.
2. **Circuit breaker bounds:** Circuit breaker thresholds (failure count, cooldown period) have platform-enforced minimum and maximum values. Applications cannot set a cooldown shorter than 5 seconds or a failure threshold lower than 2.
3. **Retry limits:** The base HTTP client enforces a maximum retry count (default 3, hard cap 10) and minimum backoff interval (default 1 second, minimum 500ms). Retry configuration outside these bounds is rejected.
4. **Credential isolation:** The base HTTP client retrieves credentials from the OS credential store at request time and does not expose them to adapter code. Adapters specify which credential key to use, not the credential value itself.
5. **Mandatory timeouts:** All adapter HTTP requests have a mandatory timeout (default 30 seconds, hard cap 120 seconds). Requests without an explicit timeout use the default. Zero or negative timeouts are rejected.
6. **Response validation:** Adapter responses from external APIs are validated against expected schemas. Unexpected response shapes are logged and rejected rather than propagated.

---

## 10. Residual Risks and Accepted Limitations

The following risks are acknowledged and accepted, either because they are outside loke's control or because mitigation would impose unacceptable trade-offs.

### 10.1 Physical Access

If an attacker has physical access to the user's unlocked device, they can access anything loke can access. This is true of all local software and is not specific to loke. Mitigation is the user's responsibility (full-disk encryption, screen lock, etc.).

### 10.2 Compromised Operating System

If the user's OS is compromised (rootkit, kernel exploit), no application-level security can protect data. loke assumes a trustworthy OS. Defence against OS-level compromise is out of scope.

### 10.3 Memory Forensics

During processing, PII exists in unencrypted form in process memory. A memory dump, core dump, or swap file could expose this data. Mitigations (secure buffer allocation, memory zeroing) reduce but do not eliminate this risk. Accepted as a low-likelihood, medium-impact residual risk.

### 10.4 Side-Channel Leakage

The length and structure of anonymised prompts may reveal information about the original content. Full mitigation (e.g., padding all prompts to a fixed length) would significantly increase token costs and is not practical. Accepted as a low-priority residual risk.

### 10.5 Cloud LLM Provider Behaviour

Once an anonymised prompt reaches a cloud LLM provider, loke has no control over how the provider stores, processes, or uses that data. loke mitigates this by sending only anonymised, compressed data, but the provider could still retain and analyse it. Users must accept their provider's terms of service. loke's audit trail provides evidence of exactly what was sent.

### 10.6 Local Model Accuracy

Local SLM inference is not as capable as large cloud models. Incorrect PII classification by the local SLM (false negatives) is mitigated by having three additional detection layers, but no combination of layers guarantees 100% detection. The system is designed to improve over time through model updates and user feedback.

### 10.7 Zero-Day Vulnerabilities in Chromium/Electron

Electron applications inherit the attack surface of Chromium. Zero-day browser exploits could compromise the renderer sandbox. Mitigation is to track Electron security releases and update promptly. loke cannot mitigate unknown Chromium vulnerabilities proactively.

### 10.8 In-Process Plugin Isolation

Plugins run in the same Node.js process as the platform. There is no process-level or V8 isolate-level sandboxing for plugin code. A malicious plugin that passes registration validation can still access global objects, `process.env`, the filesystem, and the network. True sandboxing (e.g., worker threads with restricted APIs, or separate processes with IPC) would significantly increase complexity and latency. This is accepted as a residual risk, mitigated by plugin provenance verification (planned) and the expectation that users install only trusted plugins.

### 10.9 OAuth Provider Token Policy

loke requests refresh token rotation but cannot enforce it — the OAuth provider controls whether rotation is active. If the provider does not rotate refresh tokens, a stolen token provides persistent access until manually revoked. This is outside loke's control; the mitigation is to document which providers support rotation and recommend them.

---

## 11. Review Schedule

| Activity | Frequency | Owner | Next Due |
|----------|-----------|-------|----------|
| Threat model review and update | Quarterly | Security lead | 2026-07-04 |
| STRIDE analysis for new features | Per feature (before implementation) | Feature developer + security reviewer | Ongoing |
| Garak vulnerability probe suite | Every release | CI/CD pipeline | Each release |
| Dependency CVE scan | Continuous (automated) | GitHub Dependabot | Continuous |
| PII detection test corpus update | Monthly | Privacy pipeline owner | 2026-05-04 |
| Penetration test (external) | Before v1.0 release, then annually | External auditor | Before v1.0 |
| Companion device protocol review | Before companion device feature ships | Security lead + network engineer | Before companion device launch |
| MCP security model review | Before MCP broker feature ships | Security lead + MCP developer | Before MCP broker launch |
| Electron security configuration audit | Every Electron version upgrade | Security lead | Each Electron upgrade |
| Platform HTTP server security audit | Every release | Security lead | Each release |
| Plugin system security review | Before plugin system ships, then quarterly | Security lead + platform developer | Before P2 launch |
| OAuth flow security review | Before OAuth support ships, then annually | Security lead | Before P5.2 launch |
| i18n injection test suite | Every release | CI/CD pipeline | Each release |
| Integration adapter audit | When new adapters are added | Security reviewer + adapter developer | Ongoing |

### External Audit Plan

Before the v1.0 release, loke will engage an external security firm to conduct:

1. **Source code audit** focused on the privacy pipeline, mapping table encryption, and IPC bridge
2. **Penetration test** of the Electron application in browser mode
3. **Network security assessment** of the companion device protocol and MCP broker
4. **Prompt injection red team** exercise against the full pipeline
5. **Platform HTTP server review** covering localhost binding, middleware pipeline, security headers, and rate limiting
6. **Plugin system review** assessing registration validation, hook sandboxing, and filesystem access controls
7. **OAuth flow review** verifying PKCE implementation, state parameter validation, and token storage

Results will be published in a summary report (with sensitive details redacted) to maintain transparency with users.

---

## Appendix A: Data Classification

| Classification | Definition | Examples | Handling |
|---------------|-----------|----------|----------|
| **Restricted** | PII, credentials, mapping table contents | Names, SSNs, API keys, placeholder↔value mappings | Encrypted at rest, never transmitted externally, memory-zeroed after use |
| **Confidential** | User's prompts, documents, code before anonymisation | Raw user input, proprietary source code, business data | Processed locally, anonymised before any external transmission |
| **Internal** | Anonymised prompts, routing metadata, audit entries | Anonymised text with placeholders, model selection decisions, token counts | May be transmitted to cloud LLMs (anonymised form only), stored locally with encryption |
| **Public** | Application configuration (non-sensitive), documentation | Model names, provider names, version numbers | No special handling required |

## Appendix B: Threat Model Change Log

| Date | Change | Reason |
|------|--------|--------|
| 2026-04-05 | Platform layer threats added (Section 6, trust boundaries F/G/H, attack surfaces 4.3, mitigations 9.9-9.13, residual risks 10.8-10.9, 26 new threat IDs PL-1 to PL-26) | Story X1.5 — Update threat model for platform layer |
| 2026-04-04 | Initial threat model created | Story X1.3 — Security policy and vulnerability disclosure |
