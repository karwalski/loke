Built-in policy preset for APRA Prudential Standard CPS 230 Operational Risk Management. Exports `preset()`, `rules()` (36 `$policyrule`s) and `blockingstories()`. Depends on `core.policy.schema` and `core.policy.types`.

**Source.** Read 2026-10-01 on the Federal Register of Legislation:

- F2023L01242 — determination No. 2 of 2023, made 11 September 2023, in force from **1 July 2025**. Varied by F2024L01107 (30 August 2024): pre-existing service-provider contracts from the earlier of renewal or 1 July 2026, and some continuity paragraphs deferred for non-SFIs to 1 July 2026.
- F2026L00475 — determination No. 1 of 2026, made 23 April 2026, which revokes and remakes the standard, in force from **1 July 2026** (para 6). This is the instrument in force today, and **the paragraph numbers cited are its numbers**. The 2023 text numbered the same requirements one higher from 2026 para 7 to para 56 (it had a transitional para 7), and one lower for 2026 para 59 to para 61. 2026 para 57 and para 58, which exempt standardised terms with providers in the categories the Attachment lists, are new.

**Not compliance.** Identifying critical operations, setting tolerances, keeping the register, notifying APRA and owning the BCP are the entity's. **Not enforced.** Nothing on the request path calls `core.policy.loader.evaluate` (`cps230-preset-not-enforced`).

**Why this standard bites on loke.** A model provider a critical operation relies on is a *material service provider* (para 48), and core technology services are material by default unless the entity justifies otherwise (para 49(d)). The relief in para 57 for standardised terms covers only the Attachment's categories (government agencies, regulators, central banks, exchanges, clearing and settlement, payment systems, financial messaging), so a model provider's click-through terms do not escape the formal-agreement requirements of para 53 and para 54.

**Classes** are the CPS 234 preset's: `EVALUABLE` (a preset field loke's policy code reads, asserted by the test), `DOCUMENTATION ONLY` (always `log`), `UNIMPLEMENTED <story>`. Citations are `CPS 230 para N`.

| Paragraphs | Requirement | rule id | class | action / severity |
|---|---|---|---|---|
| 11, 12, 15, 16, 17 | Operational risk framework | `cps230-operational-risk-framework` | documentation | log / high |
| 19–22 | Board accountability | `cps230-board-accountability` | documentation | log / high |
| 23, 24 | Technology and data risk; meet CPS 234 | `cps230-technology-risk` | documentation | log / high |
| 25, 26 | New technology assessed; resources and scenarios | `cps230-new-technology-assessment` | documentation | log / high |
| 28, 29, 30 | Controls tested, gaps remediated | `cps230-controls-tested` | documentation | log / high |
| 28 | Controls implemented | `cps230-preset-not-enforced` | UNIMPLEMENTED RG1.2 | log / critical |
| 31 | Incidents recorded | `cps230-incidents-recorded` | documentation | log / medium |
| 32 | Notify APRA within 72 hours | `cps230-notify-apra-incident` | documentation | log / critical |
| 33, 34, 37 | Critical operations and tolerances, the entity's | `cps230-critical-operations-declared-by-entity` | documentation | log / high |
| 35 | Supporting systems critical by default | `cps230-assume-critical-until-declared` | documentation | log / high |
| 37, 40 | Tolerance monitoring | `cps230-tolerances-not-measured` | UNIMPLEMENTED RG1.2 | log / high |
| 39, 42–45 | BCP, testing, update, audit | `cps230-bcp-owned-by-entity` | documentation | log / high |
| 33, 40, 55 | Local inference as the alternative arrangement | `cps230-degrade-to-local` | UNIMPLEMENTED RG1.8, UNVALIDATED LC1 | log / high |
| 13, 31 | Fail visibly | `cps230-fail-visibly` | documentation | log / high |
| 41 | Notify APRA within 24 hours of disruption outside tolerance | `cps230-notify-apra-disruption` | documentation | log / critical |
| 14, 48, 52 | Provider denied until due diligence | `cps230-provider-denied-until-registered` | **evaluable** (`providers` `*`) | block / critical |
| 47, 55 | Substitute permitted | `cps230-local-substitute-permitted` | **evaluable** (`providers` `local`) | log / medium |
| 15 | Limits within risk appetite | `cps230-budget-tolerance-blocks` | **evaluable** (`budget`) | block / high |
| 60 | Offshoring notified first | `cps230-offshoring-denied` | **evaluable** (`crossborderallowed` false, derived `apra-cps-230-no-cross-border` deny) | block / high |
| 48, 49 | Materiality, the entity's | `cps230-materiality-determined-by-entity` | documentation | log / high |
| 48, 50 | Register, submitted annually | `cps230-service-provider-register` | UNIMPLEMENTED RG1.2 | log / high |
| 46, 47 | Service provider management policy | `cps230-service-provider-policy` | documentation | log / medium |
| 47, 52, 53 | Fourth parties | `cps230-fourth-party-disclosure` | documentation | log / high |
| 52, 53, 54 | Due diligence and formal agreement | `cps230-due-diligence-and-agreement` | documentation | log / high |
| 57, 58 | No standardised-terms relief for model providers | `cps230-standardised-terms-no-exemption` | documentation | log / high |
| 47, 55 | Exit plan | `cps230-exit-plan-recorded` | documentation | log / high |
| 55 | No-custody narrows the exit | `cps230-no-custody-simplifies-exit` | documentation | log / medium |
| 52 | Concentration | `cps230-provider-concentration` | UNIMPLEMENTED RG1.2 | log / medium |
| 52, 60 | Provider change | `cps230-provider-change-reassessment` | documentation | log / high |
| 23, 59 | Model version pinning | `cps230-model-version-pinning` | documentation | log / high |
| 59 | Monitoring of arrangements | `cps230-monitoring` | documentation | log / medium |
| 60 | Notify APRA within 20 business days | `cps230-notify-apra-material-arrangement` | documentation | log / critical |
| 45, 61 | Internal audit | `cps230-internal-audit` | documentation | log / medium |
| 24 | Encryption at rest | `cps230-encryption-at-rest` | UNIMPLEMENTED X8 | block / critical |
| 6 | Commencement | `cps230-commencement` | documentation | log / low |
| 19 | Entity review | `cps230-entity-review-required` | documentation | log / high |

**Not cited, deliberately:** APRA's own powers (para 18, para 36, para 38, para 51, para 56) and para 27, which concerns an entity providing a material service to others.

**Corrected from the earlier transcription.** It said local degradation "is the continuity control, and it is the real one". loke has no path that retries a failed provider call locally: the router's fallback runs from local to cloud at selection time (`core.router.selector`). That is now `UNIMPLEMENTED RG1.8`. It also said nothing calls the metrics collector and that loke fails open; DA1.3 and NC1.9 closed both. The rules that warned or blocked on obligations no field can express (`cps230-assume-critical-until-declared`, `cps230-exit-plan-recorded`, `cps230-fourth-party-disclosure` and others) are now `log`. The disruption-record retention rule is dropped because CPS 230 sets no retention period; the 2555-day figure is the YAML's and is carried as `auditlogdays`.
