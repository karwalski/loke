Built-in policy preset for APRA Prudential Standard CPS 234 Information Security. Exports `preset()` (the `$policy` configuration), `rules()` (30 `$policyrule`s) and `blockingstories()` (the story ids an entity should treat as blocking). Depends on `core.policy.schema` and `core.policy.types`.

**Source.** The standard as APRA publishes it: determination No. 1 of 2018 (F2018L01745), made 30 November 2018, in force from 1 July 2019 (para 5), and for information assets a third party manages from the earlier of the next contract renewal or 1 July 2020 (para 6). Read 2026-10-01 from APRA's July 2019 PDF; APRA's standards page still lists this instrument as the current CPS 234. The configuration started as a transcription of `docs/specifications/policy-examples/apra-cps-234.yaml`; the rules now cite the standard, not the YAML.

**Not compliance.** CPS 234 obligations fall on the APRA-regulated entity and cannot be discharged by configuration. **Not enforced.** Nothing on loke's request path calls `core.policy.loader.evaluate`, so no rule here acts on traffic; the preset says so itself (`cps234-preset-not-enforced`).

**Classes.** Every rule description opens with one of:

- `EVALUABLE` — the condition is a field of this preset that loke's own policy code reads (`providers`, `classificationdefault`, `blockedentitytypes`, `requireapprovalabove`, which `core.governance.rulesengine.presetrules` turns into `apra-cps-234-approval-required`). The test asserts each field.
- `DOCUMENTATION ONLY` — an entity obligation or a fact about loke that no `$policy` field expresses. Always `log`, so nothing unevaluable can warn or block. Entity obligations also say `NOT DISCHARGEABLE BY LOKE`.
- `UNIMPLEMENTED <story>` — something the standard asks of a control like loke that loke does not do.

Then comes the citation, written `CPS 234 para N`. Cross-references to other standards are written `paragraph N`, so the test's citation check counts CPS 234 only.

| Paragraphs | Requirement | rule id | class | action / severity |
|---|---|---|---|---|
| 13, 14 | Board responsibility, defined roles | `cps234-board-accountability` | documentation | log / high |
| 15, 17 | Capability commensurate with threats, kept current | `cps234-capability-maintained` | documentation | log / medium |
| 18, 19 | Policy framework | `cps234-policy-framework` | documentation | log / medium |
| 16, 22 | Third-party capability assessed, control design evaluated | `cps234-provider-assessment-required` | **evaluable** (`providers` `*`: `allowed` false, `requiresdpa` true) | block / critical |
| 16, 22, 28 | The assessment itself | `cps234-third-party-assessment` | documentation | log / high |
| 16, 21 | No-custody path narrows, does not remove, para 16 | `cps234-no-custody-default` | documentation | log / high |
| 20 | Classification by sensitivity | `cps234-asset-classification` | **evaluable** (`classificationdefault`) | log / medium |
| 20 | Classification by criticality | `cps234-criticality-axis` | UNIMPLEMENTED RG1.1 | log / high |
| 21 | Restricted assets local only | `cps234-restricted-assets-local-only` | **evaluable** (`providers` ceilings) | block / critical |
| 21 | Restricted never forwarded | `cps234-restricted-never-forwarded` | **evaluable** (`*` ceiling confidential) | block / critical |
| 21 | Approval above confidential | `cps234-approval-above-confidential` | **evaluable** (`requireapprovalabove`) | warn / high |
| 21 | Special categories blocked | `cps234-special-categories-blocked` | **evaluable** (`blockedentitytypes`) | block / critical |
| 21, 23 | Credentials blocked outbound | `cps234-credential-outbound-blocked` | **evaluable** (`blockedentitytypes`) | block / critical |
| 21 | Medicare, BSB, account number detectors | `cps234-au-identifier-detectors` | UNIMPLEMENTED RG1.7 | log / high |
| 21 | Redaction is not de-identification | `cps234-redaction-is-not-deidentification` | documentation | log / medium |
| 21 | Query channel and aggregates | `cps234-query-channel-residual-risk` | documentation (NC1.10) | log / high |
| 21 | Encryption at rest | `cps234-encryption-at-rest` | UNIMPLEMENTED X8 | block / critical |
| 21 | Controls implemented | `cps234-preset-not-enforced` | UNIMPLEMENTED RG1.1 | log / critical |
| 23 | Detection fails closed, kill switch | `cps234-detection-fails-closed` | documentation (NC1.9, built in) | log / high |
| 23, 25 | Candidate incident triggers | `cps234-incident-triggers` | documentation | log / high |
| 24, 25, 26 | Response plans, annual test | `cps234-response-plans` | documentation | log / medium |
| 27, 29, 31 | Systematic testing program | `cps234-control-testing` | documentation | log / medium |
| 27 | Untrusted environments, para 27(d) | `cps234-untrusted-environment` | documentation | log / medium |
| 30 | Functionally independent testers | `cps234-independent-testing` | documentation | log / medium |
| 32, 33, 34 | Internal audit | `cps234-internal-audit` | documentation | log / medium |
| 32 | Records loke can supply (GA1.4, GA5.2, GA5.3, DA1.3) | `cps234-audit-evidence` | documentation | log / high |
| 35 | Notify APRA within 72 hours | `cps234-notify-apra-incident` | documentation | log / critical |
| 36 | Notify APRA within 10 business days | `cps234-notify-apra-control-weakness` | documentation | log / critical |
| 5, 6 | Commencement | `cps234-commencement` | documentation | log / low |
| 13 | Entity review | `cps234-entity-review-required` | documentation | log / high |

**Dropped from the YAML transcription**, because no CPS 234 paragraph supports them as rules: provider concentration (a CPS 230 matter, carried in that preset as `cps230-provider-concentration`) and the budget rule (CPS 234 sets no spend limit; the `budget` figure is kept for parity with CPS 230 and its comment says so). Rules that described closed gaps as open were corrected: loke fails closed (NC1.9), audit rows are written on the browser request path (GA1.4) and hash-chained with verification (GA5.2, GA5.3), and the placeholder-collision rule is gone because PL1.1 is recorded Done in the backlog (not re-verified here).

**Configuration not expressible:** criticality (`$policy` has four sensitivity levels and no criticality axis, so the local provider's `critical` ceiling is capped at `restricted`); the YAML's `daily_usd` (one budget period only); the assessment record itself.
