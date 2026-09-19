# Control Framework Mapping

**Version:** 1.0
**Date:** 2026-09-19
**Story:** RG1.6

A reference table mapping loke's controls to named AI governance and security frameworks, with honest
coverage gaps.

## What this document is

A **reference**, so that someone assessing loke against a framework they already use can find the
relevant control quickly and see what is actually implemented.

## What it is not

It is not a claim of conformance, certification or compliance, and it must not be used as one.

Three reasons, each of which is enough on its own:

1. **Framework obligations fall on an organisation, not on a tool.** Nothing in this table is
   discharged by installing software. An organisation using loke still has to do the work.
2. **Several of loke's own controls do not currently operate.** The gaps are listed per row rather
   than summarised away, and five of them are severe enough that an assessment relying on them would
   be wrong. They are collected in [Blocking gaps](#blocking-gaps) below.
3. **A mapping is an opinion.** These are loke's own readings of which control a feature relates to.
   An assessor may disagree, and where a reading is arguable the row says so.

Every framework here is cited by name and version. Paragraph and control-identifier citations are
deliberately sparse: cite the framework text, not this file.

Related: [`specifications/policy-examples/apra-cps-234.yaml`](specifications/policy-examples/apra-cps-234.yaml)
and [`apra-cps-230.yaml`](specifications/policy-examples/apra-cps-230.yaml) carry the equivalent
mapping for the two APRA prudential standards, in more depth and with the ANZ financial-services
framing. [`claims.md`](claims.md) is the authoritative record of what is implemented;
[`metrics-baseline.md`](metrics-baseline.md) is the only source of figures.

---

## Status legend

| Mark | Meaning |
|---|---|
| **operates** | Implemented and exercised on a live path |
| **partial** | Implemented but narrower than the control implies, or not on every path |
| **specified** | Designed and documented; code absent or unwired |
| **absent** | Not addressed |
| **inert** | Code exists and does not do what it appears to. The worst category, because it looks like coverage |

---

## NIST AI Risk Management Framework 1.0 (2023)

The AI RMF organises around four functions: Govern, Map, Measure, Manage. loke touches all four
unevenly, and is weakest exactly where the framework is most insistent — Measure.

| Function | Theme | loke control | Status | Gap |
|---|---|---|---|---|
| **Govern** | Policies and accountability | Three-tier policy loader (enterprise, team, user) with regulatory presets | **operates** | Presets are policy definitions. Accountability, ownership and review remain organisational |
| Govern | Risk tolerance made explicit | Sensitivity thresholds, graduated warnings, kill switch | **partial** | The kill switch operates; its state is not recorded, so its use cannot be evidenced (GA5.5) |
| Govern | Third-party risk | Provider registry, per-provider policy, default-deny in the APRA presets | **partial** | No assessment record and no register in code |
| **Map** | Context and intended use | Use-case registry, risk classification by sensitivity and use case | **operates** | Classification quality is unmeasured against ground truth for the full pipeline |
| Map | Data provenance | Dataset manifest with publisher, licence, retrieval date, checksum and a transformation list | **operates** | Covers demo datasets. User-supplied data has no equivalent |
| Map | Capability and limitation disclosure | `claims.md`, `metrics-baseline.md`, and inline caveats on unverified claims | **operates** | This is loke's strongest area against the framework, and the least conventional |
| **Measure** | Metrics for trustworthiness | Numeric result sink with mandatory provenance | **partial** | The sink operates and refuses unreproducible results. Almost nothing has been measured through it yet |
| Measure | Privacy evaluation | Span-labelled PII corpus, entity-level scoring with a recall floor | **partial** | Regex layer measured; the full pipeline needs the compiled detector (AD1.2) |
| Measure | Robustness and adversarial testing | Injection, exfiltration and bypass corpora | **specified** | Specified in `enforcement-bypass-corpus.md` and AD1.5; not run |
| Measure | Performance monitoring in deployment | Per-request metrics collector | **inert** | The table has no migration and nothing calls the collector (DA1.2, DA1.3) |
| **Manage** | Risk response | Fail-closed on detection unavailability | **inert** | It **fails open**: the original text is transmitted when the sidecar is down. The most serious gap in this table (NC1.9) |
| Manage | Incident response | Kill switch, incident triggers defined in the APRA presets | **partial** | Detection and recording only; notification is organisational |
| Manage | Documented residual risk | Threat model with accepted residual risks stated | **operates** | |

## ISO/IEC 42001:2023 — AI Management Systems

42001 is a management-system standard, so most of it is organisational by construction. A tool can
supply evidence; it cannot hold a management system. Only the clauses where loke can contribute are
listed, and the omission of the rest is deliberate rather than an oversight.

| Theme | loke control | Status | Gap |
|---|---|---|---|
| AI policy | Policy presets, three-tier precedence, policy-as-configuration | **operates** | |
| Roles and responsibilities | — | **absent** | Single-user local-first by design. No multi-user access control exists |
| AI system impact assessment | Risk classification, sensitivity levels, decision traces | **partial** | The trace structure is well designed and never persisted (GA5.5) |
| Data for AI systems | Manifest provenance, licence attribution, transformation records | **operates** | Demo data only |
| Operational controls | Privacy pipeline, router, governance gateway | **partial** | Multi-layer composition modules are written and unwired (AD1.7) |
| Monitoring and measurement | Metrics, audit ledger | **inert** | Neither is written to (DA1.3, GA5.5) |
| Documented information | Claims register, metrics baseline, threat model, specifications | **operates** | |
| Internal audit | Verifiable audit chain | **inert** | The digest does not chain and there is no verifier (GA5.2, GA5.3) |
| Improvement | Feedback capture, thumbs up/down on every interaction | **operates** | |

## OWASP Top 10 for LLM Applications (2025)

The most directly applicable of the four, and the one where loke's position is most mixed.

| Risk | loke control | Status | Gap |
|---|---|---|---|
| **Prompt injection** | Guardian system prompt; policy gate | **partial** | A system prompt is a request to the model, not enforcement. Single-turn injection is no longer discriminative against current models; multi-step and persistence attacks are what matter and are untested (AD1.5) |
| **Sensitive information disclosure** | Multi-layer PII detection, placeholder substitution, log redaction, no-custody path | **partial** | Redaction reduces disclosure and does not prevent identification. The no-custody path is specified, not built (NC1). The filter fails open (NC1.9) |
| **Supply chain** | Toolchain pinned by commit with a drift watch; no GPL in core; licence check in CI | **operates** | Model provenance is weaker: one sidecar model was unpinned until recently (VM1.2) |
| **Data and model poisoning** | — | **absent** | loke consumes models rather than training them, so mostly out of scope. Its *own* trust in a provider's model output is in scope and unaddressed |
| **Improper output handling** | DDL validation; a closed artifact op-set with no eval and no Turing-completeness | **specified** | The artifact contract is specified (NC1.1); the validator is not built. A parser differential between validator and executor is the classic vulnerability and the repo already contains a live example of the vocabulary diverging |
| **Excessive agency** | Agent capability scoping over paths, tools and cost | **partial** | Capability scoping, not process isolation — there is no sandboxing primitive in the toolchain at all |
| **System prompt leakage** | Guardian prompt is not secret and carries no credential | **operates** | By design rather than by control: nothing sensitive is in it |
| **Vector and embedding weaknesses** | Semantic cache with a similarity threshold | **partial** | Cache poisoning across sessions is not considered |
| **Misinformation** | Provenance states on computed values; no fabricated number may render | **operates** | Recently fixed. The dashboard previously rendered model-invented numbers labelled "computed locally" (NC1.5, NC1.6) |
| **Unbounded consumption** | Token budgets, cost limits, rate limiting | **partial** | Budgets exist; the savings metrics that would report against them return zeros |

## OWASP Top 10 for Agentic Applications (2026)

Newer and less settled. loke's agent framework is modest, so coverage is thin and the honest reading is
that this is the least-addressed framework of the four.

| Risk | loke control | Status | Gap |
|---|---|---|---|
| Excessive agency and least privilege | Per-agent permission allowlists, cost limits | **partial** | Enforced in-process only |
| Memory and state poisoning | — | **absent** | The memory palace has no integrity control, and persistence attacks landing in cached state are exactly the untested class (AD1.5) |
| Tool misuse | MCP broker per-server tool allowlist and denylist | **operates** | Genuinely one of the better-implemented controls in the project |
| Identity and impersonation | — | **absent** | Single-user model |
| Cascading failures | Kill switch; sequential background queue | **partial** | |
| Untraceable actions | Decision trace with seventeen fields | **specified** | No caller, no table, no insert (GA5.5) |
| Human oversight | Prompt approval, dry-run mode, graduated warnings | **partial** | Approval is a mode the user asks for, not a gate that defaults on |

---

## Blocking gaps

Five gaps appear repeatedly above and are severe enough that an assessment relying on the affected
controls would reach a wrong conclusion. Anyone using this document for an assessment should read these
first:

| Gap | Effect on this mapping | Story |
|---|---|---|
| **The filter fails open** | Every "sensitive information disclosure" and "risk response" row is weaker than it appears. When the detection sidecar is unavailable the original text is transmitted | NC1.9 |
| **Nothing writes the audit ledger** | Every monitoring, traceability and internal-audit row is unevidenced. The table is empty because the logger has no caller | GA5.5, GA1.4 |
| **The ledger is not tamper-evident** | The stored digest does not incorporate the previous record, so an integrity claim cannot be made | GA5.2, GA5.3 |
| **Encryption at rest is inert** | The pragma is ignored by the underlying database and data is plaintext on disk | X8 |
| **Detection recall is unmeasured for the full pipeline** | Every detection-quality row rests on a regex-layer figure measured with a different regex engine | AD1.2 |

## How to use this honestly

- Cite the framework, not this file.
- Read a row's gap column before relying on its status.
- Treat **inert** as worse than **absent**: absent is a known gap, inert looks like coverage.
- Check `claims.md` for what is implemented and `metrics-baseline.md` for any figure. If this document
  disagrees with either, they are right and this is a bug.
- Re-verify before an assessment. This mapping was accurate on the date above and the codebase moves.
