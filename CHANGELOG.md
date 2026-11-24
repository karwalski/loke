# Changelog

loke and moke are versioned together with semver: minor for a release that adds capability,
patch for fixes, major only by explicit decision. What loke may and may not claim is governed by
[docs/claims.md](docs/claims.md); every published figure comes from
[docs/metrics-baseline.md](docs/metrics-baseline.md). Nothing in this file is a figure or a claim
beyond those pages. Story IDs refer to [docs/epics-and-stories.md](docs/epics-and-stories.md), whose
rows carry the evidence for each item.

## loke 0.4.0, moke 0.3.0 — 2026-11-24

The first release since the foundation reset (0.3.0, 2026-09-20). It is a pre-1.0 release for
evaluation and development, macOS first.

### Toolchain and build
- Built on **toke v3.2.0** (`ea7ddf22`) and **ooke v3.0.0** (`7ac2472`), both public tagged
  releases, pinned in `TOOLCHAIN.lock` (F10.53).
- The build reports a per-module compile census and refuses to link an incomplete build; it no
  longer reports success over failed modules (F10.7).
- **CI is green for the first time**: GitHub Actions builds the pinned toolchain and loke on a
  macOS runner and runs the full suite, plus static, security and licence checks. Every job has a
  time limit and a hung test is reported as `TIMEOUT` instead of stalling the run (X8.12, X8.13 and
  the 2026-11-23 CI fixes).

### Privacy and enforcement
- Multi-layer privacy filter (F3b): configurable layers and trust (`[[privacy.layers]]`),
  consensus that keeps the most sensitive classification, entity routing, organisation-managed
  layer policies, custom token-classifier registration, per-layer metrics bound into the audit
  chain, and refusals audited (F3b.2, F3b.7, F3b.8 and F3b.10 are Partial; see their rows). The
  filter fails closed: no healthy detection layer, no request.
- AU and UK identifier detectors and preset entity vocabularies (RG1.7 and RG1.7a Partial;
  RG1.7c, the most sensitive classification surviving dedup and consensus, Done).
- The guardian is sent first on the no-custody dispatch and the body is checked against it
  (F3.9c). The guardian system prompt story itself (F3.8) is Partial.
- No-custody dispatch with artifact checks and configurable, tighten-only limits (NC1; NC1.10,
  bounding the query-shaped channel, is Partial).
- Kill switch on every call path, failing closed when its state cannot be read; graceful
  degradation to a local model on provider failure (RG1.8; G1.6 Partial: no enterprise remote
  trigger).
- Hosted POST requests over verified HTTPS (VM1.6g Partial: update checks need a header-carrying
  GET upstream); every HTTP caller reports a truncated body as a failure (F10.52).
- MCP: anonymise sends text only to the configured detection services (MK6.12).

### Audit and governance
- Hash-chained audit trail with a verifier, disclosure records reserved before send and completed
  after, per hop, on the browser and `loke ask` paths (GA5, DA1, F5.3).
- Compliance checks derived from stored state rather than literals; regulatory report generation
  (GA5.7, GA5.31; G4.4 Partial).

### moke
- Dataset catalogue on one data store, checked flows per dataset, origin guard on every API route,
  default-deny `/api/proxy` checked by resolved address (MK19, MK20, BG1).

### Quality
- Lint ratchet, codegen-hazard sweeps, a real-HOME and keychain guard around every test, and
  mutation checks recorded against Done rows (LS1, X8, RV1).

### Known limits
- Open rows in the backlog are listed with what each waits on; several need a product decision,
  hardware, or upstream toke work. SQLCipher at-rest encryption is not available at this toolchain
  (GA2.2 reopened, X8.1). Companion devices (F8) are reopened, not shipped.
- See `docs/claims.md` for every claim's verdict before relying on a capability.
