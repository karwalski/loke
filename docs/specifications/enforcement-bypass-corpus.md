# Enforcement Bypass Corpus

**Version:** 1.0
**Date:** 2026-09-19
**Story:** AD1.6
**Status:** Specification. No test has been run against this yet.

## Why this document exists

loke has claimed, in public material, that "no AI usage bypasses governance — it is architecturally
impossible." That claim is not survivable, and this document replaces it with something testable.

Every network-level enforcement point has documented bypass paths. That is not a criticism of loke
specifically; it is a property of the layer. The supportable claim is narrower and more useful:

> When traffic is in path, enforcement is ordered, recorded and inspectable. Six classes of bypass are
> enumerated below, each independently testable. Coverage is reported as "enforced at N of 6, with
> these requiring endpoint or managed-policy co-deployment" — never as unbypassability.

Two loke-specific facts make this unavoidable rather than theoretical:

- **The proxy is opt-in reconfiguration, not interception.** Applications must be pointed at
  `127.0.0.1:11431`. There is no CA certificate installation, no PAC file, no packet filtering and no
  network extension anywhere in the codebase. Anything addressed elsewhere never reaches loke. The
  word "transparent" in existing documentation is therefore wrong and is being corrected.
- **loke ships a disable flag.** `locales/en.json` carries `loke.cli.flag.no_privacy` —
  "Disable privacy pipeline (use with caution)" — and a documented "Privacy off" state. A shipped
  opt-out is incompatible with "no exceptions".

See also `docs/threat-model.md`, which already states honestly that no combination of detection layers
guarantees complete detection. This document is the enforcement-layer equivalent of that admission.

## Scope

This corpus tests whether traffic *reaches* loke. It does not test what loke does once traffic arrives —
that is the injection and exfiltration corpus (AD1.5) and the invariant set in
`artifact-contract.md`. A bypass is a success for the attacker regardless of how good the pipeline is.

## The six classes

Each class states the mechanism, why it is authoritative rather than speculative, the concrete test, and
what mitigation is available. Several mitigations are not network controls at all, which is itself the
finding.

### B1 — Default TLS-interception exemptions

**Mechanism.** Inspection products ship do-not-decrypt exception lists, enabled by default, covering
destinations that cannot be intercepted. Vendors document that certificate-pinned and
mutually-authenticated TLS cannot be decrypted and must therefore be exempted. An exemption is a
deliberate, documented loss of visibility.

**Test.** For each cloud model provider endpoint loke knows about, determine whether it falls within any
default exemption category of the inspection products in use. Record the category name and whether the
exemption is on by default.

**Mitigation.** Explicit per-destination decryption policy. Note that this cannot be done for
client-certificate-authenticated sessions at all.

**Expected result.** Partial at best. This class is not fully closable by a network control.

### B2 — Certificate pinning in native clients

**Mechanism.** An application that pins its origin certificate fingerprint rejects a resigned
certificate, so interception breaks the connection. Vendor guidance for this situation is to add a
do-not-decrypt rule — again, deliberate loss of visibility.

Browser-facing pinning was deprecated and removed from mainstream browsers some years ago, so the
residual risk concentrates in **native applications and SDKs** — which is precisely what a coding agent
or a desktop LLM client is.

**Test.** Attempt interception against a pinned native client talking to a provider API. Confirm whether
the result is a blocked connection, a bypass, or a silent exemption.

**Mitigation.** None at the network layer. Endpoint control only.

### B3 — Split tunnelling

**Mechanism.** Split tunnelling is a shipped product feature: traffic for selected destinations goes
direct, outside the tunnel and outside inspection. URL-based split tunnelling is distributed as a
browser extension by at least one major vendor. A documented consequence is that it also bypasses
administrator-configured private DNS blocklists.

**Test.** Determine whether an unprivileged user can add a provider hostname to a split-tunnel exclusion
list without administrator rights. This is the decisive question — if they can, the control is advisory.

**Mitigation.** Managed policy locking the exclusion list. Requires device management.

### B4 — Browser extensions

**Mechanism.** Two distinct issues, in opposite directions.

- As a **bypass**: an extension can originate requests from the browser's own network stack, outside the
  view of an interposing local agent.
- As the **only surviving control**: an extension is part of the browser platform, so it continues to see
  content even when transport metadata is encrypted (see B5). This makes extensions simultaneously the
  weakness and the mitigation.

A related control governs whether a user may edit certificate-authority trust or import certificates —
that is, whether they can remove an interception root.

**Test.** (a) Confirm whether an extension-originated request to a provider API is visible to loke.
(b) Confirm whether an unprivileged user can remove an interception root.

**Mitigation.** Managed browser policy, plus an extension allowlist.

### B5 — Encrypted transport metadata

**Mechanism.** The newest and most serious class. **RFC 9849, TLS Encrypted Client Hello**, is a
Standards Track RFC published in March 2026, and OpenSSL shipped support in the same month. Where a
destination supports it, the server name is no longer visible in the handshake.

The consequence is that **rules matching on server name fail silently** — not with an error, not with a
log entry, but by simply not matching. Endpoint proxying of an ECH-enabled client fails, and
server-name-based logs degrade to CDN addresses. Adjacent mechanisms with the same effect on
metadata-based enforcement are QUIC/HTTP-3 and DNS-over-HTTPS (RFC 8484).

**Test.** Against an ECH-enabled destination, confirm whether a server-name-based rule matches. The
failure mode to look for specifically is *silence* — a rule that neither fires nor errors.

**Mitigation.** Managed browser policy disabling the feature, where the client honours such a policy.
This is a holding action, not a solution, and it will stop working as adoption spreads.

**This class is the reason the six-of-six framing matters.** Any enforcement design resting on server
name inspection has a scheduled expiry date.

### B6 — Direct-to-API egress with the caller's own credentials

**Mechanism.** A process on the device holding its own API key, talking straight to a provider over
pinned or ECH-protected TLS. This is the residual case after B1–B5.

**No vendor documents a reliable network-layer control for it.** Every documented answer is
non-network: an endpoint agent, a browser extension, managed policy, or provider-side controls such as
organisation-level key issuance and egress-address restriction on the API account.

**Test.** From an unprivileged process, make a direct call to a provider API with an independently
obtained key. Confirm whether loke observes it. The expected answer is no.

**Mitigation.** Provider-side key governance, which is outside loke's boundary entirely. loke should say
so rather than implying otherwise.

## Reporting format

A single table, published with each evaluation, and never collapsed into a single claim:

| Class | Enforced | Requires | Evidence |
|---|---|---|---|
| B1 default exemptions | partial / no / yes | inspection policy change | test result reference |
| B2 certificate pinning | | endpoint control | |
| B3 split tunnelling | | device management | |
| B4 browser extensions | | managed browser policy | |
| B5 encrypted metadata | | managed policy, time-limited | |
| B6 direct-to-API | | provider-side key governance | |

Plus, separately and explicitly: **loke's own `--no-privacy` flag**, which is a deliberate user-facing
opt-out and belongs in any honest accounting of how enforcement is avoided.

## Acceptance criteria

1. Every class has a scripted, repeatable test with a recorded pass/fail and a named artefact.
2. Results are recorded through `benchmarks/lib/result.py` so they carry the environment they were
   measured in, and are reported as a fraction of classes covered — never as a single yes or no.
3. No public or internal document claims unbypassability. Each claim about enforcement names the classes
   it covers and the co-deployment it assumes.
4. Where a class cannot be closed by a network control, the document says which non-network control is
   required and states plainly that it is outside loke's boundary.
5. The corpus is re-run when the toolchain or the enforcement path changes, and B5 is re-checked on a
   schedule because adoption is still moving.

## What this corpus deliberately does not claim

That six classes are exhaustive. They are the six with vendor or standards documentation behind them
today. A seventh will appear. The reporting format is designed so that adding one changes a denominator
rather than invalidating a claim — which is the practical reason to count coverage rather than assert
completeness.
