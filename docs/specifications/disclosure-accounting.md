# Disclosure Accounting Specification

**Story:** DA1.1 — Define the disclosure record
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-09-19

---

## 1. Overview

loke's entire proposition is that less crosses the boundary to a third party. Today nothing in the
codebase records what crossed it. There is a usage and cost ledger (`audit_log`) that records tokens,
model, provider and duration, and there is a per-stage pipeline log whose payload is a free-text
string. Neither answers the question "what was disclosed on this request".

This specification defines that record. It is the substrate every later claim depends on: the exposure
metric (EM1) is computed from it, the three-arm correctness experiment (CB1) reports it per arm, the
assurance evidence (GA5) chains it, and nothing in `docs/metrics-baseline.md` can carry a disclosure
figure until it exists.

This specification defines:

- The unit of account, and its lifecycle across a request
- The complete field set, with types and provenance
- The custody classification, and the rule that it is observed rather than declared
- The counting rules that make two numbers comparable
- Where the record lives: typed per-stage fields on the pipeline log, persisted through `audit_log`
- What must never enter the record
- The honest headline the record yields for a no-custody request, and its limit

### 1.1 Design Alignment

- **Privacy is the foundation.** A record of disclosure must not itself be a disclosure. The record
  carries names, types and counts. It never carries a value.
- **Warnings must be earned.** The record is an instrument, not an alarm. It produces a number; whether
  that number warrants a warning is the policy engine's decision, not the accountant's.
- **The user is the authority.** The record is the user's own. It exists so the user can see what left,
  and is the evidence behind the pipeline panel and the scorecard.
- **Do the right thing by default.** Accounting is not optional and has no off switch. A dispatch with
  no disclosure record is a defect, and §6.4 makes it detectable.

### 1.2 Dependencies

| Dependency | Story | Relationship |
|---|---|---|
| No-custody schema profile | NC1.2 | The profile's serialised length is the disclosed-bytes figure on the no-custody path |
| Artifact contract | NC1.1 | Supplies the validation verdict, the operation list and the result volume |
| Bound the query-shaped channel | NC1.10 | Consumes the cumulative result-volume fields defined in §5.5 |
| Labelled fallback | NC1.8 | Supplies the custody classification and the fallback reason |
| Missing metrics table | DA1.2 | Blocker: see §6.3 |
| Wire the collector | DA1.3 | Blocker: see §6.3 |
| Typed stage records | DA1.4 | Implements §6.2 |
| Audit timestamps, hash chain | GA5.1, GA5.2 | Blockers on evidentiary value: see §6.5 |
| Exposure metric | EM1.1 | Sole consumer for the metric; the metric must be computable from this record alone |

### 1.3 Evidence base

`docs/research/disclosure-measurement-findings.md` is the evidence base, and two of its findings shape
this document rather than merely being cited by it.

- **§11 — a returned query is a channel.** A record that counts only outbound bytes would report a
  no-custody request as near-zero disclosure while an adversary shaped queries across turns and
  extracted cell values a piece at a time. The record therefore counts **results returned to the
  model**, and does so cumulatively across a session (§5.5). Without that field the record would
  actively mislead.
- **§8 — nine things loke must not claim.** Item 6 bears directly here: bytes and tokens are not a
  privacy measure. They are in this record because they are the strawman baseline the exposure metric
  has to beat, and because they are exactly measurable. They are not the headline, and §8.2 states what
  they do and do not support.

---

## 2. Unit of account

### 2.1 One record per external dispatch

The unit is **one external dispatch**: one request actually handed to transport, addressed to a
third-party endpoint. Not one user turn, not one conversation, not one pipeline run.

Consequences that need stating because each has been got wrong elsewhere:

- A retry is a dispatch. A bounded re-ask after an artifact rejection (NC1.1 §12.1 R7) is a dispatch,
  with its own record.
- A request served from cache with no transport is **not** a dispatch and produces no disclosure
  record. It produces a cache-hit event. Counting a cache hit as zero-disclosure disclosure would
  inflate the denominator of every rate computed over these records.
- A request routed to a local model is not a dispatch to a third party. It is recorded, with
  `provider_class = local`, precisely so that the local ratio is computable from one table; but it
  contributes zero to every disclosure figure.
- A multi-turn exchange produces one record per turn, linked by `session_id`. The session-level
  cumulative fields (§5.5) are what make the sequence legible, because the per-turn figures do not add
  up to the risk.

### 2.2 Keys

| Key | Meaning |
|---|---|
| `record_id` | Primary key, 128-bit random, hex |
| `correlation_id` | Joins to the `audit_log` row for the same dispatch. One-to-one |
| `request_id` | Joins to the moke pipeline session log (`$sessionlog.requestid`) |
| `session_id` | Joins turns into a session. The scope over which the cumulative fields in §5.5 accumulate |
| `parent_record_id` | Set when this dispatch is a retry or a re-ask of another. Null otherwise |

### 2.3 Lifecycle: two-phase write

A record that is only written after a successful response does not exist for the dispatches that most
need it — the ones that crashed, timed out, or were terminated mid-flight. The bytes still left.

| Phase | When | Fields |
|---|---|---|
| **Reserve** | Immediately before the payload is handed to transport, and after every transform | Everything in §5.1 to §5.4 — that is, everything about what is being sent. `state = dispatched` |
| **Complete** | On response, or on error, or on timeout | §5.5 and §5.6 — what came back. `state = completed`, `failed` or `abandoned` |

| # | Rule |
|---|---|
| L1 | The reserve write happens before transport, not after. If it fails, the dispatch does not happen (fail closed, per NC1.9) |
| L2 | A record left in `state = dispatched` past the request timeout is swept to `abandoned`. It is **not** deleted. An incomplete record is evidence of a dispatch whose outcome is unknown, which is a different and more useful thing than no record |
| L3 | Completion never edits a reserve field. Reserve fields describe what left and are immutable once written — a property the hash chain (GA5.2) depends on |
| L4 | The count of `abandoned` records is reported. A rising count means the accounting is lossy, and a lossy accounting silently understates disclosure |

---

## 3. Custody classification

### 3.1 The three classes

| Class | Definition | Path |
|---|---|---|
| `no-custody` | The payload contains **no value drawn from the data**. Names, types, cardinalities, null rates and row counts only, plus the user's question | NC1's primary path |
| `redacted-data` | The payload contains values drawn from the data, transformed by redaction or surrogate substitution | The anonymise-and-send fallback (NC1.8) |
| `raw` | The payload contains values drawn from the data, untransformed | Explicit user choice, or a pipeline bypass such as `--no-privacy` |

### 3.2 Observed, not declared

| # | Rule |
|---|---|
| C1 | The classification is computed from the payload as dispatched. It is never taken from a caller's assertion, a configuration flag, or which code path was taken |
| C2 | `no-custody` requires a positive check, not the absence of a negative one. The check is the NC1.2 sentinel assertion: a value known to be unique in the dataset appears zero times in the captured outbound payload. The check runs per dispatch, not once at build time |
| C3 | If the classification cannot be determined — the payload is not inspectable at the dispatch boundary, or the profile for that correlation ID is missing — the record is written as `unknown` and the dispatch does not proceed. An unclassifiable disclosure is a closed control |
| C4 | Where a classification could be argued either way, the more disclosing class is recorded |

C2 is the rule that makes the whole record trustworthy, and it is also the rule the codebase currently
fails. `packages/moke/src/hooks.tk::profiletotoon` and
`packages/core/src/optimiser/profiler.tk::totoonschema` both embed three real sample values per column
plus real minimum, maximum and mean. A request built by either emitter today is `redacted-data` at
best and `raw` in substance, however the path is labelled. A sentinel check applied to the current
emitters fails, which is the correct outcome and is the acceptance criterion for NC1.2.

### 3.3 Sub-classification of the fallback

`redacted-data` additionally records:

| Field | Meaning |
|---|---|
| `fallback_reason` | Enumerated: `task_requires_prose`, `artifact_inexpressible`, `user_choice`, `policy_directed` |
| `fallback_selected_by` | `user` or `policy`. Never `default` — selecting the fallback is a deliberate, recorded decision (NC1.8) |
| `surrogate_style` | `opaque_token` or `type_consistent` (PL1.3's second axis) |
| `surrogate_scope` | `per_request`, `per_session` or `global` (PL1.3's first axis) |
| `residual_risk_shown` | Whether the residual-risk statement was displayed at the point of use |

`surrogate_style` and `surrogate_scope` are recorded because they are the two factors of the scoping
ablation (PL1.4). Without them in the record, the ablation cannot be run over real traffic at all.

---

## 4. What never enters the record

| # | Rule |
|---|---|
| X1 | No prompt content, in any form |
| X2 | No data value: no cell value, no sample value, no aggregate computed from data, no minimum, maximum, mean or percentile |
| X3 | No entity value. Entity **types** and **counts** only. This matches the existing discipline in the audit reporting specification, which records detections without values |
| X4 | No placeholder-to-original mapping, and no placeholder token. The mapping has its own store with its own lifecycle |
| X5 | No SQL parameter values. The assembled statement's parameter *count* and *types* are recorded; the values are not (NC1.1 §10.3 Q7) |
| X6 | Column **names** are recorded; column names are not values. Noted as an exception to the spirit of X2 and a real residual risk — a column named `col_ssn_078_05_1120` carries a value in its name. That hazard is NC1.2's and AD1.5's; here it means the field-name list is itself sensitive and inherits the audit trail's access controls |
| X7 | The artifact text is recorded as a SHA-256 digest by default. Full retention is opt-in, off by default, time-boxed, and itself a recorded event |

---

## 5. The record

### 5.1 Identity and context

| Field | Type | Provenance | Notes |
|---|---|---|---|
| `record_id` | string | generated | 32 hex characters |
| `correlation_id` | string | pipeline | One-to-one with `audit_log.correlation_id` |
| `request_id` | string | pipeline | Joins the per-stage log |
| `session_id` | string | pipeline | Cumulative scope |
| `parent_record_id` | string, nullable | pipeline | Set on a retry or re-ask |
| `occurred_at` | string, ISO 8601 UTC | clock | A real timestamp. See §6.5 — `audit.tk` currently writes the seven-character literal `'now()'` |
| `state` | enum | lifecycle | `dispatched`, `completed`, `failed`, `abandoned` |
| `dispatch_kind` | enum | pipeline | `initial`, `retry`, `reask` |
| `pipeline_disabled` | bool | config | True when the privacy pipeline was bypassed, e.g. `--no-privacy`. Recorded because an unrecorded bypass is the worst case in the table |

### 5.2 Destination

| Field | Type | Provenance | Notes |
|---|---|---|---|
| `provider` | string | router | Provider identifier |
| `provider_class` | enum | router | `local`, `cloud`, `self_hosted`. `local` contributes zero to every disclosure figure |
| `model_id` | string | router | |
| `model_version` | string | router | The exact version string, per VM1.2. An unpinned model makes every figure computed over this record unreproducible |
| `endpoint_host` | string | transport | The host actually connected to |
| `jurisdiction` | string, nullable | provider registry | Where known. Null rather than guessed |
| `retention_class` | enum, nullable | provider registry | `zdr`, `bounded`, `unknown`. Default `unknown`. Findings §8 item 8 forbids claiming indefinite retention; this field must not be filled from assumption |

### 5.3 Volume

| Field | Type | Provenance | Notes |
|---|---|---|---|
| `bytes_body` | integer | transport | Octets of the request body exactly as handed to transport. Measured, never estimated. §5.7 C1 |
| `bytes_headers` | integer | transport | Octets of request headers. Recorded separately; never folded into the headline |
| `bytes_schema_profile` | integer | profile emitter | Octets of the serialised schema profile within the body. On the no-custody path this is the disclosure figure of §8.1 |
| `bytes_question` | integer | pipeline | Octets of the user's question within the body |
| `bytes_other` | integer | derived | `bytes_body` less the above. Non-zero on a no-custody request means framing and instructions; a large value warrants inspection |
| `tokens_estimated` | integer | tokeniser | An **estimate**. §5.7 C2 |
| `tokeniser_id` | string | tokeniser | Required whenever `tokens_estimated` is non-null. A token count without a named tokeniser is not a figure `docs/metrics-baseline.md` accepts |
| `tokens_source` | enum | tokeniser | `provider_reported`, `local_tokeniser`, `heuristic`. Never presented as measured unless `provider_reported` |

### 5.4 Content disclosed

| Field | Type | Provenance | Notes |
|---|---|---|---|
| `custody` | enum | observed | §3 |
| `custody_check` | enum | observed | `sentinel_pass`, `sentinel_fail`, `not_run`. `no-custody` requires `sentinel_pass` |
| `fallback_reason` | enum, nullable | pipeline | §3.3 |
| `fallback_selected_by` | enum, nullable | pipeline | §3.3 |
| `surrogate_style` | enum, nullable | privacy | §3.3 |
| `surrogate_scope` | enum, nullable | privacy | §3.3 |
| `datasets_disclosed` | array of string | profile emitter | Dataset names present in the payload |
| `fields_disclosed` | array of string | profile emitter | Column and field names present in the payload, deduplicated, in the payload's own spelling |
| `fields_disclosed_count` | integer | derived | Set cardinality of the above |
| `field_types_disclosed` | array of string | profile emitter | Declared types, positionally aligned with `fields_disclosed` |
| `cardinality_disclosed` | bool | profile emitter | Whether per-column cardinality or null-rate was included. Distributional information is where reconstruction risk lives (findings §7) and it is disclosed by the profile by design |
| `row_count_disclosed` | bool | profile emitter | Whether the dataset row count was included |
| `entity_types` | array of `{type, count}` | privacy pipeline | Types and counts. Never values (X3) |
| `entities_total` | integer | derived | |
| `detection_layers` | array of string | privacy pipeline | Which layers contributed. Needed for AD1.3's marginal-value reporting |
| `real_values_included` | bool | observed | **The gate.** True when any value drawn from the data is present, whatever its transformation |
| `real_value_count` | integer | observed | Occurrences, deduplicated per §5.7 C4 |
| `sample_values_included` | bool | observed | Specifically the three-per-column sample values the current emitters embed. Separated from `real_values_included` because it is a known, named, fixable defect and its elimination is measurable |
| `aggregates_included` | bool | observed | Whether min, max, mean or any other value-derived statistic was included. An aggregate is not a cell but it is not nothing |
| `qi_combination_present` | bool | privacy pipeline | Whether a quasi-identifier combination was present. The strongest single component of the exposure metric (findings §7), so it is recorded here rather than recomputed later |
| `qi_combination_fields` | array of string | privacy pipeline | Which field names formed it |

### 5.5 Results returned to the model — the §11 channel

This is the group that exists because of finding §11, and the one most likely to be omitted by an
implementer who thinks of disclosure as an outbound property.

| Field | Type | Provenance | Notes |
|---|---|---|---|
| `artifact_returned` | bool | artifact path | Whether the response contained an artifact |
| `artifact_digest` | string, nullable | artifact path | SHA-256 of the artifact text |
| `artifact_ops` | array of string | validator | The operation tokens the validated artifact enumerated |
| `artifact_verdict` | enum | validator | `accepted` or `rejected` |
| `artifact_rejection_code` | string, nullable | validator | The NC1.1 §12.2 code |
| `artifact_rejection_path` | string, nullable | validator | The failing element |
| `local_rows_computed` | integer | executor | Rows the local execution produced. **Not a disclosure** — recorded as the denominator |
| `local_cells_computed` | integer | executor | As above |
| `results_returned_rows` | integer | next dispatch | Rows from a local result that were serialised into an outbound payload |
| `results_returned_cells` | integer | next dispatch | Cells, as above. **This is the disclosure figure** |
| `results_returned_bytes` | integer | next dispatch | Octets of that serialised result |
| `results_returned_columns` | array of string | next dispatch | Which columns' values crossed |
| `results_returned_ops` | array of string | next dispatch | Which operations produced them. Row-returning operations (NC1.1 §4.1) are flagged |
| `session_cells_returned_cumulative` | integer | session counter | Running total across the session |
| `session_rows_returned_cumulative` | integer | session counter | |
| `session_dispatch_ordinal` | integer | session counter | Which turn this is |
| `predicate_fingerprint` | string, nullable | validator | Stable digest over `(filter_col, op, column)` with `filter_val` excluded. Lets repeated near-identical predicates be counted without recording the probe value |
| `predicate_repeat_count` | integer | session counter | Occurrences of this fingerprint in the session. The signal an iterative value-probing sequence produces |
| `budget_consumed_cells` | integer | validator | Against `SESSION_CELL_BUDGET` |
| `budget_refusals` | integer | validator | Refusals on this dispatch. A bound that is not recorded cannot be evidenced |

### 5.6 Outcome

| Field | Type | Provenance | Notes |
|---|---|---|---|
| `response_bytes` | integer | transport | Octets of the response body |
| `tokens_in_reported`, `tokens_out_reported` | integer, nullable | provider | Provider-reported counts where available. Distinct from `tokens_estimated` |
| `cost_usd` | number, nullable | pricing | With `price_date`, per `docs/metrics-baseline.md` |
| `duration_ms` | integer | clock | |
| `outcome` | enum | transport | `ok`, `provider_error`, `timeout`, `blocked`, `rejected_locally` |
| `policy_id`, `policy_version` | string, nullable | policy engine | Which policy was active |
| `approval_outcome` | enum, nullable | approval workflow | `not_required`, `approved`, `edited`, `cancelled` |

### 5.7 Counting rules

Two numbers are comparable only if they were counted the same way. These rules are normative and any
figure published from this record states which of them applied.

| # | Rule |
|---|---|
| C1 | **Bytes are octets of the request body exactly as handed to transport**, after every transform — anonymisation, optimisation, format conversion, compression — at the last point before transport. Not the user's input, not an intermediate form, not a character count. Header octets are counted separately and never folded into the headline. Transport-layer compression is recorded as a separate `bytes_on_wire` where observable, but the headline is the uncompressed body, because that is what the recipient reads |
| C2 | **Tokens are an estimate** unless `tokens_source = provider_reported`. The tokeniser is named. An estimate is labelled an estimate wherever it appears |
| C3 | **Field names are a set.** Deduplicated, in the payload's own spelling, no normalisation. Count is set cardinality. A name appearing in both a profile block and an instruction block counts once |
| C4 | **Entity and value counts are occurrences after the pipeline's deduplication**, and the dedup rule in force is recorded. The rule matters: with the PL1.1 collision defect present, three distinct people collapse to one token, so an occurrence count taken after substitution would report one entity where three were disclosed. Until PL1.1 is fixed, entity counts are taken **before** substitution and this is recorded in the figure's caveat |
| C5 | **Only results that cross the boundary count as disclosure.** A locally-computed result displayed to the user is zero disclosure and is recorded in the `local_*` fields. The same result serialised into a later outbound payload is disclosure and is recorded in the `results_returned_*` fields of *that* dispatch. This distinction is the whole instrument for finding §11, and collapsing the two would make every no-custody session look either free or ruinous depending on which way it collapsed |
| C6 | **Cumulative session fields are monotonic within a session** and reset only on a new `session_id`. They are recorded on every dispatch, so the sequence is reconstructable from any single row |
| C7 | **A cache hit produces no record** (§2.1) |
| C8 | **A local dispatch produces a record with `provider_class = local`** and contributes zero to every disclosure figure. It is not excluded, so that the local ratio and the disclosure rate share one denominator |

---

## 6. Where it lives

### 6.1 Two surfaces, one record

| Surface | Scope | Lifetime |
|---|---|---|
| Per-stage pipeline record | In-flight, per pipeline stage, returned to the client for the pipeline panel | Request |
| `disclosure_log` table | Persisted, one row per dispatch, joined to `audit_log` on `correlation_id`, digested into its hash chain | Audit retention period |

The per-stage record is what the user watches. The persisted row is the evidence. They carry the same
values, and the persisted row is authoritative.

### 6.2 Typed fields on the per-stage record

`packages/moke/src/console_log.tk` defines:

```
$logentry{ stage:str; status:str; detail:str; durationms:i32; ts:i64 }
```

It already rides along in the pipeline response and already reports column counts — inside `detail`,
as English prose, assembled for display. `formatentry` interpolates it into a line and `tojson` emits
it as a JSON string. Nothing can compute on it.

Required change (DA1.4):

| # | Rule |
|---|---|
| S1 | `$logentry` gains typed disclosure fields: at minimum `custody`, `bytes_body`, `bytes_schema_profile`, `tokens_estimated`, `tokeniser_id`, `fields_disclosed_count`, `entities_total`, `real_values_included`, `results_returned_cells`, `artifact_verdict`. Types are the §5 types |
| S2 | `detail` is retained and **demoted to display only**. It is documented as non-authoritative, and no consumer parses it. It is generated *from* the typed fields, not alongside them, so the two cannot disagree |
| S3 | `tojson` emits the typed fields as JSON numbers, booleans and arrays — not as strings. A number emitted as a string is a consumer-side parse waiting to diverge |
| S4 | The existing `$logstage` enumeration gains no new stages. The stages that matter already exist: `profile`, `query_dispatch`, `local_compute`, `llm_call`. Disclosure fields attach to `llm_call` for what left and to `query_dispatch` and `local_compute` for what was computed and what came back |
| S5 | Fields the stage does not know are null, not zero. A null means "not applicable at this stage"; a zero means "measured as none". Conflating them is how a missing measurement becomes a favourable one |

S5 is the rule that keeps the accounting honest under partial implementation. During the transition,
many fields will be null. Null aggregates to "not measured", which is reportable; zero aggregates to
"no disclosure", which would be a false claim.

### 6.3 Persistence — and the two defects in the way

The record persists through the audit store, joined to `audit_log`. Two live defects must be
acknowledged, because a naive implementation will land on both.

| # | Defect | Consequence |
|---|---|---|
| F1 | **`metrics_raw` has no migration.** `packages/core/src/metrics/collector.tk::record` inserts into `metrics_raw`, and `packages/core/src/storage/migrations.tk` creates only `schema_migrations`, `settings`, `audit_log`, `placeholder_maps` and `sessions`. The table does not exist, so `record()` fails at run time and `summarise()` cannot read anything. This is DA1.2 | The obvious host for these fields is a table that is not there |
| F2 | **Nothing calls `collector.record`.** The insert path has no caller anywhere in the codebase, so even with the table created, no row would appear. This is DA1.3 | Creating the table is necessary and not sufficient |

Also inherited: `summarise()` returns a hardcoded `avgsavingpct:0.0` (`collector.tk:91`), so a
disclosure summary built on top of `$metricssummary` as it stands would publish a literal zero as a
measurement.

The implementation target is therefore:

| # | Rule |
|---|---|
| P1 | A migration creates `disclosure_log`, with one column per §5 field and a `UNIQUE` constraint on `correlation_id` |
| P2 | `disclosure_log` is written on every external dispatch, at the same call site that writes `audit_log`, in one transaction. Two records describing the same dispatch that can be written independently will eventually disagree |
| P3 | `metrics_raw` is created by its own migration (DA1.2) and keeps its existing purpose — token and cost savings. It is **not** the home of the disclosure fields. Rationale: `metrics_raw` is a savings ledger with a `savings_by_stage` free-text column; disclosure needs to be chained and is not a savings figure |
| P4 | `avgsavingpct` is computed or removed. A hardcoded zero in a summary is a published figure with no measurement behind it |

Choice of a companion table rather than widening `audit_log` — and the reasoning, since the story text
says "persist through the `audit_log` table":

- `audit_log` is deliberately content-free: a per-interaction usage and cost ledger that excludes
  prompt content and placeholder values by design (GA5.8). Widening it by forty columns changes what it
  is and what its hash covers.
- A companion table that is *not* in the hash chain would be unevidenced, which defeats the purpose.

So: `disclosure_log` is a separate table, and its canonical serialisation is an input to the
`audit_log` row's digest (GA5.2). The chain therefore covers the disclosure record, and tampering with
a disclosure row breaks verification at the corresponding `audit_log` row. "Through `audit_log`" is
satisfied by the chain and the join, not by the column list.

### 6.4 A dispatch with no record is detectable

| # | Rule |
|---|---|
| G1 | Every `audit_log` row of an external-dispatch event type has exactly one `disclosure_log` row on the same `correlation_id`. An orphan on either side is a defect, not a gap to be tolerated |
| G2 | A reconciliation check runs on demand and reports orphan counts both ways. It is the only way to know the accounting is complete, and completeness is the property every rate computed from this table assumes |
| G3 | Acceptance, per DA1.3: after exactly one external request, exactly one `disclosure_log` row exists, with non-null values in every reserve field of §5.1 to §5.4 |

### 6.5 Inherited evidentiary defects

The record's value as evidence is capped by three defects it does not own. Stated so that nobody reads
a disclosure figure as more load-bearing than it is:

| Defect | Effect on this record |
|---|---|
| `audit.tk:47` writes the string literal `'now()'` into `created_at` (GA5.1) | Every existing audit row carries the same seven characters instead of a time. `disclosure_log.occurred_at` must be a real timestamp, and until GA5.1 lands, joins to `audit_log` cannot be ordered by time |
| `audit.tk:38` computes `hash = str.concat(correlationid, eventtype)` and `prev_hash` is stored but is not an input (GA5.2) | Nothing chains. Digesting the disclosure record into that value evidences nothing until GA5.2 lands. The dependency is stated rather than assumed |
| Local storage is not encrypted — the toolchain links plain SQLite, which ignores the encryption pragma and reports success (X8) | `disclosure_log` holds the field-name list, which is sensitive (X6), in plaintext on disk. This must not be described as an encrypted record |

---

## 7. Access, retention and surfacing

| # | Rule |
|---|---|
| T1 | `disclosure_log` inherits the audit trail's retention period and its access controls |
| T2 | The field-name list is treated as sensitive (X6). Export of disclosure records follows the audit-export redaction rules, and field names are redacted by default in any export that leaves the device |
| T3 | Records are append-only. The append-only property is not currently enforced by anything (GA5.9), and that is stated rather than implied |
| T4 | The per-request view is the pipeline panel; the aggregate view is the savings and scorecard surfaces (DA1.5). Both read this record. Neither carries a hardcoded percentage — the current hardcoded values in `packages/browser/templates/savings.tkt` and `packages/moke/templates/chat.tkt` are replaced, not supplemented |
| T5 | Any figure derived from this record and published anywhere goes through `docs/metrics-baseline.md` first, with its N and its date. That file has precedence |

---

## 8. The headline, and its limit

### 8.1 What the record yields for a no-custody request

For a request on the primary path, with the NC1.2 emitter in place and the sentinel check passing:

| Quantity | Value |
|---|---|
| `custody` | `no-custody` |
| `custody_check` | `sentinel_pass` |
| **Bytes disclosed** | **Exactly `bytes_schema_profile` — the serialised length of the schema profile — plus `bytes_question`** |
| **Rows disclosed** | **Zero** |
| `real_values_included` | False |
| `sample_values_included` | False |
| `aggregates_included` | False |
| `results_returned_cells` | Zero on the first turn of a session |
| Comparison to arm A | The same request with the data in the prompt discloses `bytes_body` of O(data). The ratio is computable per request and is reported as a ratio against a named baseline arm, never as an absolute reduction |

That is a precise, falsifiable, per-request statement, and it is the first one loke has been in a
position to make. It is exactly measurable — bytes are counted, not estimated — and it is checkable by
a third party from the captured payload.

### 8.2 The limit, stated in the same breath

The limit is not a caveat appended for form. It is the reason the fields in §5.5 exist.

1. **The statement is byte-level, not information-level.** Per finding §11, a returned query is itself
   a channel. An adversary — or a compromised model — able to shape queries and observe results across
   turns can extract cell values a piece at a time, including by binary search, without ever being sent
   a row. "Bytes disclosed equals the schema profile, rows disclosed is zero" can be true on every turn
   of a session at the end of which a specific cell value has been recovered.
2. **No published benchmark tests this**, so there is no external result to cite and no measured bound
   to quote. It is an open problem (NC1.10), not a solved one.
3. **The quantity that bounds it is cumulative and session-level**, not per-request:
   `session_cells_returned_cumulative`, `predicate_repeat_count` and `budget_consumed_cells`. A
   per-request headline of "zero rows" alongside a session cumulative of thousands of returned cells is
   the shape of the risk, and both figures must appear together.
4. **Therefore:** wherever the §8.1 headline is published, the cumulative result-volume figure for the
   same session is published beside it, and the claim carries the limitation. Until NC1.10 bounds the
   channel with a measured operating point, the no-custody claim is stated with the limitation
   attached — which is already the position `docs/metrics-baseline.md` takes.
5. **Separately, the schema is not nothing.** Table and column names have been reconstructed from a
   deployed text-to-SQL system at F1 up to 0.99 (findings §10), and schemas encode business logic,
   regulatory scope and sometimes values in column names. The defensible framing for `bytes_disclosed`
   is **bounded and auditable** — O(schema) rather than O(data), declared, with the exact bytes
   reviewable — never "low leakage" and never "no disclosure".

### 8.3 What bytes and tokens do not support

Recorded because these fields are the most quotable in the record and the least meaningful.

Bytes and tokens are in this record because they are exactly measurable and because they are the
strawman baseline the exposure metric must beat (findings §7 and §8 item 6). They have near-zero
construct validity as a privacy measure: a single quasi-identifier combination in forty bytes can be
more disclosing than forty kilobytes of schema. They are never presented as a privacy measure, never
used as the headline of a privacy claim, and never summed with anything from §5.4 to make a score. The
measure is specified in `docs/specifications/exposure-metric.md`.

---

## 9. Acceptance criteria

| # | Criterion |
|---|---|
| A1 | A migration creates `disclosure_log` with one column per §5 field and `UNIQUE(correlation_id)` |
| A2 | After exactly one external request, exactly one `disclosure_log` row exists with non-null values in every reserve field of §5.1 to §5.4 (DA1.3) |
| A3 | The reserve write precedes transport. With the write forced to fail, no dispatch occurs |
| A4 | A dispatch that times out leaves a row in `state = abandoned`, not no row. The abandoned count is reportable |
| A5 | `custody` is computed from the dispatched payload. A test that mislabels the path and dispatches a payload containing a real value records `raw`, not the label |
| A6 | `custody = no-custody` requires `custody_check = sentinel_pass`. Run against the current `profiletotoon` and `totoonschema` emitters, the check **fails**, and the record classifies accordingly |
| A7 | `bytes_body` equals the exact octet count of the dispatched body, asserted against a captured payload. `bytes_headers` is separate |
| A8 | `tokens_estimated` is never non-null without `tokeniser_id`, enforced by a constraint |
| A9 | `fields_disclosed` is a deduplicated set and `fields_disclosed_count` is its cardinality, verified against a payload naming the same column in two places |
| A10 | No field of any `disclosure_log` row contains a data value, a prompt fragment, an entity value or a placeholder original. Verified by a sentinel scan over the whole table |
| A11 | `results_returned_cells` is zero when a local result is displayed only, and non-zero when the same result is serialised into a later outbound payload (C5) |
| A12 | `session_cells_returned_cumulative` and `predicate_repeat_count` increase correctly across a synthetic value-probing sequence of ten turns, and the sequence is reconstructable from any single row |
| A13 | `$logentry` carries the S1 typed fields, `tojson` emits them as JSON numbers, booleans and arrays, and no consumer parses `detail` |
| A14 | The reconciliation check reports zero orphans in both directions over a run of at least 100 dispatches |
| A15 | The `disclosure_log` row's canonical serialisation is an input to the corresponding `audit_log` digest, and mutating a disclosure field breaks chain verification at that row (dependent on GA5.2) |
| A16 | No surface displays a hardcoded disclosure percentage. The values in `savings.tkt:138,225` and `chat.tkt:2764` are gone |
| A17 | For a no-custody request, the reported headline is the §8.1 pair, and the §8.2 limitation and the session cumulative figure appear with it in every surface that shows it |

---

## 10. Open problems

| # | Problem |
|---|---|
| U1 | **Cross-session accounting.** The cumulative fields reset on `session_id`. An adversary willing to use more sessions evades the bound, and a cross-session identity to accumulate against does not exist. NC1.10 |
| U2 | **Entity counts are unreliable until PL1.1 is fixed.** The NER layers return a hardcoded `[<LABEL>_NER_1]`, so distinct entities collapse to one token. C4 works around it by counting before substitution and recording that it did; the workaround is not a fix |
| U3 | **`cardinality_disclosed` is a boolean where a quantity belongs.** Distributional information is where reconstruction risk lives (findings §7) and it is the hardest component to instrument honestly. A boolean is a placeholder, and the exposure metric treats this component as reported-but-unvalidated |
| U4 | **Column names as values** (X6) are undetected by this record and can only be addressed at the emitter |
| U5 | **`retention_class` is unfillable for most providers.** Default retention is bounded and zero-retention arrangements exist, reportedly with carve-outs, but the specifics are secondary-source and change. The field defaults to `unknown` and must not be populated from assumption — findings §8 item 8 |
| U6 | **The record is plaintext on disk** (X8). It contains the field-name list, which is sensitive |
