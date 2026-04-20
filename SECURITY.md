# Security Policy

## Reporting a Vulnerability

**Do not report security vulnerabilities through public GitHub issues, discussions, or pull requests.**

loke is a privacy-focused product. Security vulnerabilities — especially those involving PII leakage, mapping table exposure, or anonymisation bypass — are treated as severity-1 incidents. We take every report seriously.

### How to Report

Report vulnerabilities privately using one of the following channels:

1. **GitHub Security Advisories (preferred):** Use [GitHub's private vulnerability reporting](https://github.com/karwalski/loke/security/advisories/new) to create a draft advisory. This keeps the report confidential and allows us to collaborate on a fix before public disclosure.

2. **Email:** Send a detailed report to **security@loke.dev**. If you want to encrypt your message, use our PGP key (available at `https://loke.dev/.well-known/security.txt`).

### What to Include

A good vulnerability report helps us triage and fix the issue faster. Please include:

- **Description** of the vulnerability and its potential impact
- **Affected component** (e.g., privacy pipeline, mapping storage, companion device protocol, MCP broker, Electron shell, CLI proxy)
- **Steps to reproduce** the issue, including any proof-of-concept code or configuration
- **Environment details** — OS, loke version, mode (browser/terminal), relevant configuration
- **Severity assessment** — your view of the impact (we may adjust this during triage)

If you are unsure whether something qualifies as a security vulnerability, report it anyway. We would rather receive a false alarm than miss a real issue.

### What to Expect

| Milestone | Target |
|-----------|--------|
| Acknowledgement of your report | Within **48 hours** |
| Initial triage and severity assessment | Within **5 business days** |
| Patch for critical vulnerabilities (CVSS 9.0+) | Within **7 days** of confirmation |
| Patch for high-severity vulnerabilities (CVSS 7.0–8.9) | Within **14 days** of confirmation |
| Patch for medium/low vulnerabilities | Within **30 days** of confirmation |

We will keep you informed throughout the process. If we need more information, we will ask within the acknowledgement window.

### Coordinated Disclosure

We follow a coordinated disclosure process:

1. You report the vulnerability privately.
2. We acknowledge, triage, and develop a fix.
3. We prepare a security advisory and release a patched version.
4. We publish the advisory and credit you (unless you prefer to remain anonymous).
5. We request a **90-day disclosure window** from the date of your initial report. If we have not resolved the issue within 90 days, you are free to disclose publicly.

### Recognition

We credit security researchers who report valid vulnerabilities in our release notes and security advisories. If you would like to be credited, please include your preferred name and optional affiliation in your report.

## Supported Versions

| Version | Supported |
|---------|-----------|
| Latest release | Yes |
| Previous minor release | Security patches only |
| Older versions | No |

We recommend always running the latest version of loke.

## Security Design Principles

loke's security posture is rooted in the project's core philosophy: **privacy is the foundation, not a feature**. The following principles guide our security decisions:

1. **Defence in depth.** No single layer is trusted to catch everything. PII detection uses four independent layers (regex, NLP, SLM NER, Presidio). Each layer assumes the others may fail.

2. **Local by default.** Sensitive data — PII, mapping tables, audit logs, API keys — never leaves the user's device unless the user explicitly authorises it. There is no telemetry that includes user data.

3. **Least privilege.** Each component has access only to what it needs. MCP servers are explicitly whitelisted. Companion devices undergo host verification. Electron renderer processes are sandboxed.

4. **Fail closed.** When the privacy pipeline encounters an error, the request is blocked, not sent through unfiltered. When in doubt, loke protects.

5. **Auditability.** Every outbound request, every routing decision, every MCP tool call is logged locally. Users and enterprise administrators can review the complete audit trail.

6. **Zero trust for external inputs.** LLM responses, MCP tool results, and companion device messages are all treated as untrusted input and sanitised before processing.

## Scope

The following areas are in scope for vulnerability reports:

- PII leakage through the anonymisation pipeline (bypass, incomplete detection, mapping table exposure)
- Prompt injection attacks that cause data exfiltration
- MCP data exfiltration or unauthorised tool execution
- Companion device authentication bypass or man-in-the-middle attacks
- Electron/Chromium sandbox escapes or privilege escalation
- Local storage encryption weaknesses (mapping tables, audit logs, credentials)
- Dependency vulnerabilities in shipped packages
- API key or credential exposure
- Cross-site scripting (XSS) in browser mode
- Remote code execution in any component
- Denial of service against the local processing pipeline

The following are out of scope:

- Vulnerabilities in upstream LLM providers (report those to the provider directly)
- Social engineering attacks against users
- Physical access attacks (if an attacker has physical access to the device, the device is compromised regardless)
- Vulnerabilities in dependencies that do not affect loke's usage of them
- Theoretical attacks without a demonstrated proof of concept

## Security-Related Configuration

Users and enterprise administrators should review the following security-relevant settings:

- **Anonymisation strictness** — defaults to maximum; can be relaxed per policy
- **MCP server whitelist** — no MCP servers are permitted by default
- **Companion device pairing** — requires explicit approval and host verification
- **Cloud provider allowlist** — controls which external LLMs may receive data
- **Audit log retention** — defaults to indefinite local retention
- **Encryption at rest** — enabled by default for mapping tables and credentials

## Contact

- Security reports: **security@loke.dev** or [GitHub Security Advisories](https://github.com/karwalski/loke/security/advisories/new)
- General questions about security: Open a [GitHub Discussion](https://github.com/karwalski/loke/discussions) (do not include vulnerability details)
- License: Apache 2.0
