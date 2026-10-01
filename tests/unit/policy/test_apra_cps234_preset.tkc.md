RG1.1. Tests the production APRA CPS 234 preset (`core.policy.presets.apracps234`) through `core.policy.presets.registry`, `core.policy.loader` and `core.governance.rulesengine`.

Asserts that it loads by name as one regulation carrying all 30 declared rules. Every rule must open with `EVALUABLE`, `DOCUMENTATION ONLY` or `UNIMPLEMENTED` (exactly 7 evaluable and 4 unimplemented), cite a `CPS 234 para`, and every documentation-only rule must be `log`. Each of paragraphs 13 to 36 must be cited by some rule. A citation counts only when `para N` is followed by a delimiter, so para 3 never matches para 35.

Named requirements: para 35 (72 hours, log-only) and para 36 (10 business days) notification; paras 16 and 22 as an evaluable provider rule; para 20's criticality axis and the absence of request-path enforcement named as unimplemented; testing and its independence; the 1 July 2019 commencement.

Each evaluable rule is checked against the field it names: the `*` provider denied with `requiresdpa` and a confidential ceiling, local allowed to restricted, `classificationdefault` confidential, health, biometric, TFN, API key and password blocked, `requireapprovalabove` confidential, and the rules engine's derived `apra-cps-234-approval-required`.

Evaluation: every rule evaluated by its own id through `loader.evaluatepreset` yields exactly one violation with that rule's id and action. The provider rule blocks at critical, and an unrelated context yields none. Stale or overstated wording ("fails OPEN", a no-custody provider "is not a third party managing one", compliance claims) must be absent.

Mutant (2026-10-01): removing `cps234-notify-apra-incident` and setting `cps234-response-plans` to `warn` failed 4 assertions (rule count, log-only, para 35 cited, the para 35 rule).
