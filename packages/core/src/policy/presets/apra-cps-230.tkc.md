Built-in policy preset for APRA Prudential Standard CPS 230 (Operational Risk Management), transcribed from `docs/specifications/policy-examples/apra-cps-230.yaml`. Exports `preset()`, `rules()` (27 `$policyrule`s, each description prefixed with the YAML path that produced it), and `blockingstories()`. Depends on `core.policy.schema` and `core.policy.types`.

CPS 230 is less amenable to being discharged by configuration than CPS 234. Identifying critical operations, setting tolerance levels, maintaining the service-provider register, notifying APRA and owning the continuity plan are all the entity's obligations. The claim this preset supports is narrower than "loke removes the provider dependency", which is false — a no-custody request still needs the provider reachable to return an artifact. It is that the dependency becomes bounded, measurable and degradable.

Clause-to-rule mapping (YAML key → rule id):

| YAML source | rule id | action / severity |
|---|---|---|
| `critical_operations.declared_by_entity`, `entries: []` | `cps230-critical-operations-declared-by-entity` | log / high |
| `critical_operations.default_assumed_critical` | `cps230-assume-critical-until-declared` | warn / high |
| `critical_operations.entry_schema` tolerance fields | `cps230-tolerances-recorded-not-enforced` | log / high |
| `service_providers.default_action` | `cps230-provider-denied-until-registered` | block / critical |
| `service_providers.materiality_test` | `cps230-materiality-determined-by-entity` | log / high |
| `service_providers.register` (`implemented: false`) | `cps230-service-provider-register` (UNIMPLEMENTED) | log / high |
| `service_providers.providers[local].validation_status` | `cps230-local-degraded-mode` (UNVALIDATED, epic LC1) | warn / high |
| `service_providers.providers[*].conditions`, `exit_plan` | `cps230-exit-plan-recorded` | block / high |
| `service_providers.register.substitutability` | `cps230-substitutability-recorded` | log / high |
| `service_providers.concentration.warn_below: 0.20` | `cps230-local-ratio-concentration` (UNIMPLEMENTED DA1.2, DA1.3) | warn / medium |
| `service_providers.fourth_party` | `cps230-fourth-party-disclosure` | warn / high |
| `disruption.on_provider_unavailable` | `cps230-degrade-to-local` | log / medium |
| `disruption.on_local_unavailable` | `cps230-fail-visibly` | block / high |
| `disruption.degraded_mode.must_surface_to_user` | `cps230-degraded-mode-surfaced` | warn / medium |
| `disruption.in_flight_analysis` | `cps230-in-flight-analysis-survives` | log / low |
| `disruption.measurement` | `cps230-disruption-measurement` (UNIMPLEMENTED DA1.2, DA1.3) | log / high |
| `disruption.notification` | `cps230-disruption-notification` | warn / critical |
| `disclosure.rationale` | `cps230-no-custody-simplifies-exit` | log / medium |
| `disclosure.redact_and_forward.operational_consequence` | `cps230-forward-creates-exit-obligation` | warn / high |
| `disclosure.fail_closed` + `fail_closed_enforced: false` | `cps230-fail-closed` (UNIMPLEMENTED NC1.9) | block / critical |
| `change_management.provider_change_requires_reassessment` | `cps230-provider-change-reassessment` | warn / high |
| `change_management.model_version_pinning` | `cps230-model-version-pinning` | warn / high |
| `change_management.deprecation_watch` | `cps230-deprecation-watch` | log / medium |
| `retention.at_rest_encryption` | `cps230-encryption-at-rest` (UNIMPLEMENTED X8) | block / critical |
| `retention.disruption_record_days` | `cps230-disruption-record-retention` (NOT EXPRESSIBLE) | log / medium |
| `budget_limits.rationale` | `cps230-budget-tolerance-blocks` | block / high |
| `metadata.requires_entity_review`, `cannot_discharge` | `cps230-entity-review-required` | log / high |

Configuration mapping, and what loke cannot express:

- The CPS 230 YAML has no `data_classification`, `anonymisation` or `sensitivity_thresholds` section. Its `disclosure` section is stated as "inherited from the CPS 234 preset", and `metadata.related_presets` names `apra-cps-234`, so `classificationdefault`, `anonymisation`, `blockedentitytypes` and `requireapprovalabove` are taken from that preset rather than invented here.
- `critical_operations.entries` is deliberately empty in the source and there is no `$policy` field for it. `allowedusecases` is left empty rather than populated with a guess.
- `service_providers.register` has eighteen fields and `$providerpermission` has five, so the register is **not expressible**; nothing in loke maintains one.
- `retention.disruption_record_days` is **not expressible**: `$retentionpolicy` has one audit-log period.
- `budget_limits.monthly_usd: 500.0` and `on_exceed: block` → `budget`; `daily_usd` is not expressible, and `maxtokens` has no figure in the source.
- `concentration.measure: local_request_ratio` has no field and no measurement behind it (DA1.2, DA1.3).
