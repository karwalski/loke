Built-in policy preset for APRA Prudential Standard CPS 234 (Information Security), transcribed from `docs/specifications/policy-examples/apra-cps-234.yaml`. Exports `preset()` (the `$policy` configuration), `rules()` (31 `$policyrule`s, each description prefixed with the YAML path that produced it), and `blockingstories()` (the story ids an entity should treat as blocking). Depends on `core.policy.schema` and `core.policy.types`.

This preset is not compliance. CPS 234 obligations fall on the APRA-regulated entity and cannot be discharged by configuration; loke cannot perform the third-party assessment, maintain the notification obligations, substitute for internal audit, or carry Board-level accountability. Every such item is present in `rules()` marked `NOT DISCHARGEABLE BY LOKE` rather than omitted, and every control the YAML asks for that loke does not implement is present marked `UNIMPLEMENTED` with its story id. A regulatory preset that silently drops a control is worse than one that names it as missing.

Clause-to-rule mapping (YAML key → rule id):

| YAML source | rule id | action / severity |
|---|---|---|
| `disclosure.default_path` | `cps234-no-custody-default` | warn / high |
| `disclosure.redact_and_forward.requires_justification` | `cps234-forward-requires-justification` | warn / high |
| `disclosure.redact_and_forward.prohibited_levels` | `cps234-restricted-never-forwarded` | block / critical |
| `disclosure.redact_and_forward.stated_limitation` | `cps234-redaction-is-not-deidentification` | log / medium |
| `disclosure.fail_closed` + `fail_closed_enforced: false` | `cps234-fail-closed` (UNIMPLEMENTED NC1.9) | block / critical |
| `provider_restrictions.default_action`, `requires_recorded_assessment`, `assessment_fields` | `cps234-provider-assessment-required` | block / critical |
| `provider_restrictions.providers[local].max_level` | `cps234-restricted-assets-local-only` | block / critical |
| `provider_restrictions.concentration_warning_threshold` | `cps234-provider-concentration` | warn / medium |
| `data_classification.levels` + `default_level` | `cps234-asset-classification` | log / medium |
| `data_classification.rules[*].detector_status: absent` | `cps234-detector-gap-au-identifiers` (UNIMPLEMENTED AD1.1) | warn / high |
| `data_classification.rules[aggregate_statistic]` | `cps234-aggregates-not-safe` | warn / medium |
| `disclosure.no_custody.residual_risks` | `cps234-query-channel-residual-risk` (NC1.10) | warn / high |
| `evidence.interaction_ledger` | `cps234-interaction-ledger` (UNIMPLEMENTED GA5.5, GA1.4) | log / high |
| `evidence.tamper_evidence` | `cps234-ledger-tamper-evidence` (UNIMPLEMENTED GA5.2, GA5.3) | log / high |
| `evidence.control_testing` | `cps234-control-testing` | log / medium |
| `evidence.independent_review.supported: false` | `cps234-independent-review-not-dischargeable` | log / medium |
| `incident.notify_apra: false` + `reference_windows` | `cps234-notification-not-dischargeable` | warn / critical |
| `incident.triggers_to_surface[unredacted_disclosure]` | `cps234-trigger-unredacted-disclosure` | block / critical |
| `incident.triggers_to_surface[restricted_asset_on_forward_path]` | `cps234-trigger-restricted-on-forward-path` | block / critical |
| `incident.triggers_to_surface[provider_used_without_assessment]` | `cps234-trigger-provider-unassessed` | warn / high |
| `incident.triggers_to_surface[detection_layer_unavailable]` | `cps234-trigger-detection-unavailable` | warn / high |
| `incident.triggers_to_surface[credential_detected_outbound]` | `cps234-trigger-credential-outbound` | block / critical |
| `incident.triggers_to_surface[bypass_observed]` | `cps234-trigger-bypass-observed` | warn / high |
| `incident.kill_switch` | `cps234-kill-switch` | log / high |
| `retention.notes`, `prompt_content: never_persisted` | `cps234-prompt-content-not-retained` | log / medium |
| `retention.at_rest_encryption` | `cps234-encryption-at-rest` (UNIMPLEMENTED X8) | block / critical |
| `anonymisation.special_categories` | `cps234-special-categories-blocked` | block / critical |
| `anonymisation.known_defect` | `cps234-placeholder-collision` (DEFECT PL1.1) | warn / high |
| `sensitivity_thresholds.approval_must_be_recorded` | `cps234-approval-must-be-recorded` | warn / high |
| `budget_limits.on_exceed` | `cps234-budget-tolerance-blocks` | block / high |
| `metadata.requires_entity_review`, `cannot_discharge` | `cps234-entity-review-required` | log / high |

Configuration mapping, and what loke cannot express:

- `data_classification.default_level: confidential` → `classificationdefault`.
- `data_classification.levels` includes a fifth level, `critical`. `$policy` has four (public, internal, confidential, restricted) and `core.policy.validate` accepts only those, so criticality is **not expressible**; the local provider's `max_level: critical` is capped at `restricted` and the cap is stated in that provider's `notes`.
- `data_classification.rules` + `anonymisation.special_categories` → `anonymisation` and `blockedentitytypes`.
- `provider_restrictions.providers` → `providers`. loke stores no assessment record, so `allowed` cannot be checked against evidence loke holds: flipping it asserts the assessment exists.
- `sensitivity_thresholds.require_approval_at: restricted` → `requireapprovalabove: "confidential"`.
- `retention.interaction_ledger_days: 2555` → `auditlogdays`; `placeholder_mappings_hours: 24` → `piimappingdays: 1`; `prompt_content: never_persisted` → `conversationdays: 0`. `cachedays` has no figure in the source and is set to 0 to match the never-persisted posture.
- `budget_limits.monthly_usd: 500.0` and `on_exceed: block` → `budget`. `daily_usd: 50.0` is **not expressible**: `$budgetlimit` carries one period. `maxtokens` stays 0 because the source document gives no token figure.
- `provider_restrictions.assessment_fields`, `evidence.control_testing` and `incident.reference_windows` have no field in `$policy` and are carried in `rules()` and `customrules` instead.
