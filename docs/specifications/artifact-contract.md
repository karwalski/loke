# Artifact Contract Specification

**Story:** NC1.1 — Define the artifact contract
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-09-19

---

## 1. Overview

On loke's no-custody path the model never receives data rows. It receives a schema profile and the
user's question, and it returns an **artifact**: a declarative description of the computation to
perform. loke validates that artifact and then executes it locally against data that never left the
device.

The artifact is therefore untrusted input that loke is about to act on. Everything that stops a
returned artifact from becoming a code-execution or data-exfiltration primitive lives in this
document.

This specification defines:

- The closed operation set an artifact may express, enumerated from the existing implementation
- The concrete grammar of an artifact document
- The validation rules, in evaluation order, and the explicit rejection criteria
- What happens on rejection, and why the failure mode is closed rather than open
- The single-definition requirement that removes the validator/executor parser differential
- The second execution backend — parameterised SQL through `std.db` — and the prohibition on
  string-interpolated SQL
- The side-effecting constructs that must be rejected outright should SQL or code ever become
  expressible

### 1.1 Design Alignment

- **Privacy is the foundation.** The artifact path exists because redaction is not a guarantee. An
  artifact contract that can be subverted returns the architecture to the position it was built to
  leave.
- **Do the right thing by default.** An artifact that cannot be fully validated is not executed. There
  is no permissive mode and no "best effort" execution of a partially-understood artifact.
- **Warnings must be earned.** A rejection is a specific, coded, actionable failure — not a generic
  caution banner. The user is told which rule failed and on which element.
- **The user is the authority.** The user may decline the no-custody path entirely (NC1.8) and choose
  the labelled fallback. What the user cannot do is authorise an artifact the validator rejected: the
  decision to run arbitrary model output is not one loke offers.

### 1.2 Dependencies

| Dependency | Story | Relationship |
|---|---|---|
| No-custody schema profile | NC1.2 | The declared schema is the *only* namespace an artifact may reference. Until the profile stops shipping real sample values, the contract's core premise is unmet |
| Local execution engine | NC1.7 | `packages/moke/src/compute.tk::execute()` is the reference executor; this contract is the language it accepts |
| Parameterised SQL backend | NC1.7 | `std.db`'s `db.many(sql, params)` is the second backend |
| Fail closed | NC1.9 | Rejection must not degrade into transmission or into execution |
| Bound the query-shaped channel | NC1.10 | Result-cardinality budgets in §8 are this contract's half of that bound |
| Disclosure accounting | DA1.1 | Every validation verdict, and every result volume, is a recorded field |
| Artifact-abuse corpus | AD1.5 | The adversarial corpus, including parser-differential variants, tests this document |

### 1.3 Evidence base and framing

Read `docs/research/disclosure-measurement-findings.md` before repositioning anything here.

Two constraints from it bear directly on this document.

- **§10 — the data flow is not novel.** Schema-out / execute-locally is the default implementation of
  the entire text-to-SQL field and ships in several commercial products. Nothing in this
  specification is claimed as an invention. What is being specified is the part those systems do not
  have: a validated language with a stated threat model and a proof obligation.
- **§11 — a returned query is itself a channel.** An adversary able to shape queries and observe
  results across turns can extract cell values a piece at a time. "The model never receives data" is
  true at the byte level and not necessarily at the information level. This contract bounds the
  channel (§8) but does not close it, and the limitation travels with the claim.

---

## 2. Why the language is closed — and why that is a security property

### 2.1 toke exposes no sandboxing primitive

The complete process-control surface available to loke is `std.process`:

| Export | Signature |
|---|---|
| `process.spawn` | `[str] → Handle!ProcessErr` |
| `process.wait` | `Handle → i32` |
| `process.stdout` | `Handle → str!ProcessErr` |
| `process.stderr` | `Handle → str!ProcessErr` |
| `process.kill` | `Handle → bool` |

That is spawn, wait, read, kill. There is **no** jail or chroot, no namespace or user switch, no
resource limit of any kind — CPU, memory, file descriptors, wall clock — no syscall filter, no
filesystem restriction and no network restriction. A spawned child inherits loke's full ambient
authority over the user's machine, including the local data store and the network.

Additionally: toke has no `eval`, no dynamic code loading, and no embedded WASM host. There is no
in-process interpreter to confine.

### 2.2 The consequence

If arbitrary code were an admissible artifact, the only enforcement mechanism available would be
static inspection of untrusted text immediately before running it with full authority. That is the
design that has repeatedly failed everywhere it has been tried, and there is no reason to expect it
to hold here.

So the operation set is closed, and **arbitrary code can never be a valid artifact**. This is not a
limitation pending a sandbox. It is the control:

> **NC-CLOSED.** Capability is removed rather than confined. An operation that is not in §4 cannot be
> expressed, so it does not need to be detected, contained or audited at run time.

A closed language is a stronger control than a sandbox for three reasons, and they should be stated
in that order whenever this design is questioned:

1. **It is decidable.** The validator can decide membership of the language totally. A sandbox
   decides, at best, whether a particular observed action is permitted.
2. **It has no escape surface.** There is no confinement boundary to break out of, because nothing
   untrusted is ever executed — only interpreted as parameters to loke's own code.
3. **It bounds cost.** Every operation in §4 is a single pass, or a bounded number of passes, over a
   dataset with a known row count. Termination is structural, not enforced by a timeout that does not
   exist.

The cost is expressiveness, and the cost is real: a question the contract cannot express is a question
the no-custody path cannot answer. That cost is measured rather than argued — see
`docs/specifications/correctness-benchmark.md`, where an artifact that cannot express a benchmark item
is scored as incorrect, not skipped.

### 2.3 Non-Turing-completeness, stated precisely

The artifact language has:

- no user-defined names, functions or macros
- no recursion and no user-visible iteration construct
- no conditionals other than the fixed equality predicate of `filter` (§4.2)
- no arithmetic on values supplied by the model; all arithmetic is internal to a named operation
- no composition of operations: each card carries exactly one operation, and no operation takes
  another operation's result as input
- a fixed, finite set of result shapes (§4.3)

An artifact is therefore a **bounded straight-line description of at most N independent aggregate
queries over one or two named datasets**, where N is capped in §8. It is not a program.

---

## 3. The artifact document

### 3.1 Concrete syntax

An artifact is a single JSON object, UTF-8 encoded, with no byte-order mark.

JSON is chosen because it is already the wire form on both ends of this path:
`packages/moke/src/ddl.tk::tojson` serialises the dashboard structure to JSON, and the dashboard
template consumes JSON. Introducing a second syntax would create a second parser, which §9 forbids.

### 3.2 Wire field names track the executor's struct

Field names on the wire are the field names of `packages/moke/src/compute.tk`'s `$query`, in
`snake_case`. This is deliberate. Every rename between the wire form and the executor's in-memory
struct is a place where the validator's understanding and the executor's can drift apart, which is
precisely the failure §9 exists to prevent. The contract therefore adds fields where the executor
needs them and renames nothing.

### 3.3 Grammar

```ebnf
artifact        = "{" , "contract"            , ":" , version
                    , "," , "dataset"         , ":" , dataset-ref
                    , "," , "schema_fingerprint" , ":" , hex64
                    , "," , "title"           , ":" , short-text
                    , [ "," , "summary"       , ":" , short-text ]
                    , "," , "cards"           , ":" , card-list
                , "}" ;

version         = '"1.0"' ;                        (* exact literal; see V2 *)
dataset-ref     = string ;                         (* must equal a declared dataset name *)
hex64           = string ;                         (* 64 lowercase hex digits *)
short-text      = string ;                         (* length <= 200, see V11 *)

card-list       = "[" , card , { "," , card } , "]" ;   (* 1 .. MAX_CARDS *)

card            = "{" , "id"       , ":" , card-id
                    , "," , "kind" , ":" , card-kind
                    , "," , "title", ":" , short-text
                    , "," , "col_span" , ":" , col-span
                    , "," , kind-block
                , "}" ;

card-id         = string ;                         (* ^[a-z0-9][a-z0-9-]{0,63}$ , unique *)
card-kind       = '"metric"' | '"chart"' | '"table"' | '"text"' | '"list"' ;
col-span        = 1 | 2 | 3 ;

kind-block      = metric-block | chart-block | table-block | text-block | list-block ;

metric-block    = '"metric"' , ":" , "{" , "label" , ":" , short-text
                    , [ "," , "unit" , ":" , unit ]
                    , "," , "query" , ":" , query
                , "}" ;

chart-block     = '"chart"' , ":" , "{" , "chart_type" , ":" , chart-type
                    , "," , "query" , ":" , query
                , "}" ;

table-block     = '"table"' , ":" , "{" , "columns" , ":" , colref-list
                    , "," , "query" , ":" , query
                , "}" ;

text-block      = '"text"' , ":" , "{" , "markdown" , ":" , prose , "}" ;
list-block      = '"list"' , ":" , "{" , "items" , ":" , prose-list , "}" ;

chart-type      = '"line"' | '"bar"' | '"pie"' | '"area"' | '"scatter"' ;
unit            = string ;                         (* ^[A-Za-z%$€£ /]{0,8}$ *)

query           = "{" , "op" , ":" , op
                    , [ "," , "column"        , ":" , colref ]
                    , [ "," , "group_by"      , ":" , colref ]
                    , [ "," , "filter_col"    , ":" , colref ]
                    , [ "," , "filter_val"    , ":" , literal ]
                    , [ "," , "top_n"         , ":" , bounded-int ]
                    , [ "," , "bucket_count"  , ":" , bounded-int ]
                    , [ "," , "join_dataset"  , ":" , dataset-ref ]
                    , [ "," , "join_col"      , ":" , colref ]
                , "}" ;

op              = '"count"'   | '"sum"'       | '"avg"'      | '"min"'
                | '"max"'     | '"group"'     | '"timeseries"'
                | '"topn"'    | '"distribution"' | '"correlate"'
                | '"percentile"' | '"count_by"' | '"latest"'
                | '"distinct"' | '"join"' ;

colref          = string ;        (* must equal, byte for byte, a column name in the profile *)
colref-list     = "[" , colref , { "," , colref } , "]" ;
literal         = string | number ;   (* never an object, array, or boolean; see V13 *)
bounded-int     = integer ;           (* range constrained per field; see §8 *)
prose           = string ;            (* length <= 2000; carries no data values; see V15 *)
prose-list      = "[" , prose , { "," , prose } , "]" ;   (* 1 .. 20 items *)
```

Notes on the grammar that are normative:

- Whitespace is JSON whitespace. Nothing else is permitted between tokens.
- Object member order is free, but no member may appear twice (V5).
- There is no `default`, no `extends`, no `$ref`, no expression of any kind, and no field whose value
  is interpreted as anything other than a literal or an enumerated token.
- `text` and `list` cards carry no query and produce no computed value. They are commentary. They are
  the only place prose from the model reaches the rendered output, and §8 caps their length. A `text`
  or `list` card **may not** be used to carry a number: see V15 and NC1.5.

---

## 4. The closed operation set

### 4.1 Enumeration, from the implementation

Fifteen operations exist in `packages/moke/src/compute.tk`. This is the whole set; there are no
others, and adding one is a change to this document, to the single definition in §9.2, and to the
conformance suite, in that order.

| `op` token | Implementation | Required | Optional | Result shape | Returns data values? |
|---|---|---|---|---|---|
| `count` | `opcount` | — | `filter_col`+`filter_val` | scalar | No — a cardinality |
| `sum` | `opsum` | `column` | `filter_col`+`filter_val` | scalar | No — an aggregate |
| `avg` | `opavg` | `column` | `filter_col`+`filter_val` | scalar, 2 dp | No — an aggregate |
| `min` | `opmin` | `column` | `filter_col`+`filter_val` | scalar | **Yes** — an extreme value is a real cell value |
| `max` | `opmax` | `column` | `filter_col`+`filter_val` | scalar | **Yes** — as `min` |
| `group` | `opgroup` | `group_by` | `filter_col`+`filter_val` | label/value series | **Yes** — labels are real values of `group_by` |
| `timeseries` | `optimeseries` | `column`, `group_by` (date column) | `filter_col`+`filter_val` | label/value series, labels truncated to 10 characters | **Yes** — labels are real dates |
| `topn` | `optopn` | `column` (numeric sort key) | `top_n` (default 10), `filter_col`+`filter_val` | row set | **Yes** — whole rows |
| `distribution` | `opdistribution` | `column` | `bucket_count` (default 10), `filter_col`+`filter_val` | label/value series, labels are numeric ranges | **Yes** — bucket bounds derive from the real min and max |
| `correlate` | `opcorrelate` | `column` (x), `group_by` (y) | `filter_col`+`filter_val` | scalar, 4 dp | No — an aggregate |
| `percentile` | `oppercentile` | `column` | `filter_col`+`filter_val` | fixed 5-row set: `p25`, `p50`, `p75`, `p90`, `p99` | **Yes** — each percentile is a real cell value |
| `count_by` | `opcountby` | `column` | `filter_col`+`filter_val` | label/value series, sorted descending by count | **Yes** — labels are real values |
| `latest` | `oplatest` | `column` (date column) | `top_n` (default 10), `filter_col`+`filter_val` | row set | **Yes** — whole rows |
| `distinct` | `opdistinct` | `column` | `filter_col`+`filter_val` | value list | **Yes** — the values themselves |
| `join` | `opjoin` | `join_dataset`, `join_col` | — | row set | **Yes** — whole merged rows |

The "returns data values" column is not decoration. It is the input to the result budget in §8 and to
the disclosure record in `docs/specifications/disclosure-accounting.md`: a locally-computed result is
not a disclosure, but a result that re-enters a later outbound payload is, and row-returning
operations are where a query-shaped extraction channel (§11 of the findings document) would live.

### 4.2 `applyfilter` is a modifier, not an operation

`applyfilter(ds, filtercol, filterval)` is the single predicate available. It is not an `op` and may
not be named as one. Its semantics, as implemented: exact string equality against the named column,
applied to the whole dataset before the operation runs; a no-op if either field is empty or the column
is not found.

Normative rules:

- `filter_col` and `filter_val` are either both present or both absent. One without the other is a
  rejection (V9), not a silent no-op. The current implementation treats a missing half as "no filter",
  which means a malformed artifact would quietly compute over the whole dataset instead of a subset —
  a correctness and disclosure divergence, not a convenience.
- There is exactly one predicate per query. No conjunction, no disjunction, no negation, no ordering
  or range comparison, no `LIKE`, no regular expression. A model that needs a compound predicate must
  express it as multiple cards, and each card is counted against the budget.
- `filter_val` is a literal. It is compared; it is never interpreted.

### 4.3 Result shapes

Four shapes only, matching `$result{op, column, value, rows, labels, values}`:

| Shape | Populated fields | Produced by |
|---|---|---|
| Scalar | `value` | `count`, `sum`, `avg`, `min`, `max`, `correlate` |
| Label/value series | `labels`, `values` | `group`, `timeseries`, `distribution`, `count_by` |
| Value list | `values` | `distinct` |
| Row set | `rows` | `topn`, `latest`, `percentile`, `join` |

A result of any other shape is a bug in the executor, not an artifact the contract admits.

### 4.4 Defects in the existing implementation that the contract requires fixing

These are conditions on NC1.7, not observations. Each is a place where the implementation as it stands
would not satisfy this contract.

| # | Defect | Required change |
|---|---|---|
| D1 | `execute()` dispatches fourteen operations. `join` is reachable only through the separate `executejoin(ds, other, q)` entry point, so the set an artifact can name and the set one function can execute differ | One dispatch surface for all fifteen operations, driven by the single definition in §9.2 |
| D2 | `opjoin` does not call `applyfilter`, so `filter_col`/`filter_val` are silently ignored on `join` | Either apply the filter on `join` or reject `filter_col` on `join` at validation. Silent ignoring is forbidden |
| D3 | `execute()` on an unknown op returns a `$result` whose `value` is the **string** `"error:unknown_op"`. That is a value a caller can render as a number-shaped answer, not an error | An unknown op must be unreachable after validation, and if reached must raise, never return a result |
| D4 | `packages/moke/src/ddl.tk::demodashboard` names the operations `mean`, `mean_by_group`, `count_by_day`, `top_n`, `mean_prev_period`, `count_prev_period`. Of these, **none** is in `execute()`'s dispatch table — the implemented tokens are `avg`, `group`, `timeseries`, `topn`, and there is no period-comparison operation at all | Delete the divergent vocabulary. See §9.1: this is the parser differential already in the tree |
| D5 | `$metriccard.deltaqueryop` has no implementation anywhere. `$query` carries no period or date-range field | Either specify a period operation and implement it, or remove the field. A field that is accepted and ignored is a differential |
| D6 | `ddl.tk::validate()` checks a non-empty title, a non-empty card list, and non-empty `id` and `kind` per card. It does not check `kind` against the enumeration, does not look at any query, and does not know the schema | Replaced entirely by §7. The existing function is not a validator in the sense this document uses the word |

---

## 5. The declared schema is the whole namespace

The only names an artifact may reference are those in the schema profile that was actually
transmitted on that request (NC1.2). Not the dataset's real columns — the *declared* ones.

| Rule | Statement |
|---|---|
| N1 | Every `colref` must equal, byte for byte after no normalisation at all, a column name present in the transmitted profile. No case folding, no trimming, no Unicode normalisation, no fuzzy or nearest match, no index-based fallback |
| N2 | Every `dataset_ref` and `join_dataset` must equal a dataset name present in the transmitted profile |
| N3 | The artifact carries `schema_fingerprint`: a SHA-256 digest, as 64 lowercase hex digits, over the canonical serialisation of the profile as transmitted. If it does not match the profile loke holds for that correlation ID, the artifact is rejected (`E-SCHEMA-DRIFT`) |
| N4 | A `colref` that does not resolve is a rejection, never a no-op. The existing `colindex()` returns `-1` for an unknown column and `getcol()` then returns `""`, so today an unknown column silently yields zeros. Silent zeros are indistinguishable from a real answer of zero |

N3 is what stops an artifact generated against one profile being replayed against another dataset, and
what stops a cached or injected artifact (AD1.5's persistence family) from executing against a schema
it was never shown.

N1's strictness is deliberate and is the single most important rule in §5. Every normalisation step is
a place where the validator's idea of "the same column" and the executor's can differ. Exact equality
has no such place.

---

## 6. Ordering: validate, then execute the validated object

| Rule | Statement |
|---|---|
| O1 | The artifact text is parsed **exactly once** |
| O2 | Validation operates on the parsed object |
| O3 | Execution consumes **the same in-memory object** validation approved. The original text is not retained for execution, not re-parsed, and not re-serialised and re-read |
| O4 | No canonicalisation, rewriting, defaulting, coercion or repair occurs after validation. Defaults (`top_n` = 10, `bucket_count` = 10) are applied *during* validation and recorded in the validated object, so the executor never applies a default of its own |
| O5 | The executor re-asserts the closed op token and the resolved column indices immediately before each operation. This is redundant with validation, and is kept: a redundant assertion is cheap, and an assertion that never fires is the evidence that O1–O4 hold |

O1–O3 remove the entire time-of-check/time-of-use class from this path. O5 is defence in depth
against a future refactor that breaks O3.

---

## 7. Validation rules

Rules are evaluated in the order given. Evaluation stops at the first failure: there is no
"collect all errors" mode, because continuing past a structural failure means reasoning about a
document the validator has already decided it does not understand.

### 7.1 Structural

| # | Rule | Code on failure |
|---|---|---|
| V1 | The payload is well-formed JSON, UTF-8, no BOM, and is a single object | `E-PARSE` |
| V2 | `contract` is present and is exactly `"1.0"`. An unknown version is rejected; it is never treated as a newer or older version to be read leniently | `E-VERSION` |
| V3 | Total payload size ≤ 64 KiB | `E-SIZE` |
| V4 | Nesting depth ≤ 6 | `E-DEPTH` |
| V5 | No object contains a duplicate member name | `E-DUPLICATE-KEY` |
| V6 | No member name appears that is not in the grammar in §3.3, at any level. **Unknown fields are rejected, never ignored** | `E-UNKNOWN-FIELD` |
| V7 | All members required by the grammar for the element's kind are present | `E-MISSING-FIELD` |
| V8 | Every value's JSON type matches the grammar. A number where a string is required, or a string where an integer is required, is a rejection, not a coercion | `E-TYPE` |

V6 is the rule most often relaxed for convenience, and relaxing it is how a field one side understands
and the other does not gets into the system. It is not relaxed.

### 7.2 Semantic

| # | Rule | Code on failure |
|---|---|---|
| V9 | `op` is one of the fifteen tokens in §4.1. Per-op required fields are present and per-op forbidden fields are absent, per §4.1 and §4.2. `filter_col` and `filter_val` are both present or both absent | `E-OP-UNKNOWN`, `E-OP-ARITY` |
| V10 | Every `colref`, `dataset` and `join_dataset` resolves under §5 N1–N2, and `schema_fingerprint` matches under N3 | `E-COLUMN-UNDECLARED`, `E-DATASET-UNDECLARED`, `E-SCHEMA-DRIFT` |
| V11 | Where an operation requires a numeric column (`sum`, `avg`, `min`, `max`, `correlate`, `topn`, `distribution`, `percentile`) the declared type of that column is numeric. Where it requires a date column (`timeseries` `group_by`, `latest` `column`) the declared type is temporal | `E-COLUMN-SHAPE` |
| V12 | `card.id` matches `^[a-z0-9][a-z0-9-]{0,63}$` and is unique within the artifact. `col_span` ∈ {1, 2, 3}. `chart_type` is one of the five enumerated values. `unit` matches its pattern. `title` and `summary` ≤ 200 characters | `E-FIELD-SHAPE` |
| V13 | `filter_val` is a JSON string or number and nothing else. A string `filter_val` is ≤ 128 characters. It is used only as the right operand of the equality comparison in §4.2 | `E-LITERAL-SHAPE` |
| V14 | Numeric bounds per §8 hold | `E-BOUND` |
| V15 | `markdown` and `items` prose contains no digit sequence of length ≥ 2 that is not also present in the question text. A `text` or `list` card is commentary; a model-invented number rendered as prose is exactly the failure NC1.5 exists to remove | `E-PROSE-NUMBER` |
| V16 | The artifact's aggregate result budget, computed from the declared cardinality of each referenced column, is within the per-artifact and per-session caps in §8 | `E-BUDGET` |
| V17 | Where the SQL backend is selected, the statement-shape rules in §10 hold | `E-SQL-SHAPE` |
| V18 | No element of the artifact matches the denylist in §11 | `E-DENYLIST` |

V18 is last, and is deliberately last. It is a secondary net, not the control — see §11.

---

## 8. Bounds and budgets

Every bound is a constant in the single definition (§9.2), not a literal in either the validator or
the executor.

| Bound | Value | Rationale |
|---|---|---|
| `MAX_PAYLOAD_BYTES` | 65 536 | V3 |
| `MAX_DEPTH` | 6 | V4 |
| `MAX_CARDS` | 24 | Caps operations per artifact; caps total result volume |
| `MAX_QUERIES_PER_CARD` | 1 | No composition (§2.3) |
| `TOP_N_RANGE` | 1 … 100 | `top_n`; default 10, as implemented |
| `BUCKET_COUNT_RANGE` | 2 … 50 | `bucket_count`; default 10, as implemented |
| `MAX_TABLE_COLUMNS` | 20 | `table.columns` |
| `MAX_ROWS_PER_CARD` | 100 | Row-returning operations |
| `MAX_SERIES_POINTS` | 500 | Label/value series and `distinct` value lists |
| `MAX_CELLS_PER_ARTIFACT` | 5 000 | Sum over all cards of rows × columns, series points, and distinct values |
| `MAX_JOIN_DATASETS` | 1 | `opjoin` takes exactly one other dataset |
| `SESSION_CELL_BUDGET` | Configurable; default 50 000 | Cumulative across a session, per NC1.10 |
| `SESSION_PREDICATE_REPEAT_LIMIT` | Configurable; default 20 | Distinct `filter_val` values against the same `filter_col` within a session |

### 8.1 The budgets are the contract's half of the NC1.10 bound

`MAX_CELLS_PER_ARTIFACT`, `SESSION_CELL_BUDGET` and `SESSION_PREDICATE_REPEAT_LIMIT` exist because of
finding §11: an adversary that can shape queries and observe results can extract values a piece at a
time, and a binary search over a numeric column needs only O(log n) narrow `filter_val` probes to
recover a single cell. Nothing in §4 prevents that; the budgets bound its rate.

Being honest about what this achieves:

- It **bounds** extraction. It does not prevent it.
- A per-session cap is evadable by an adversary willing to use more sessions, and the cross-session
  accounting that would close that is not specified here.
- The budgets are a rate limit chosen without measurement. They are a placeholder for a measured
  operating point, and NC1.10 owns producing one.

Every budget decision — the counter values, the consumption, and every refusal — is recorded as a
disclosure event (`docs/specifications/disclosure-accounting.md`), because a bound that is not
recorded cannot be evidenced.

---

## 9. One definition: the parser-differential requirement

### 9.1 The hazard, and the instance already in the tree

Any divergence between what the validator believes an artifact means and what the executor does with
it is a vulnerability. It is the classic proxy bug: the checking component and the acting component
disagree, and the attacker writes input that lands in the gap. In an enforcement proxy it is the
highest-severity class, because the validator is the only control.

This is not hypothetical here. Defect D4 in §4.4 is a live vocabulary differential: the DDL layer
constructs cards naming `mean`, `mean_by_group`, `count_by_day`, `top_n` and `mean_prev_period`,
while the executor dispatches on `avg`, `group`, `timeseries` and `topn` and has no period operation
at all. Two components in the same repository already disagree about what the operation set is. A
contract enforced by two independently-maintained descriptions of the same language will reach the
same state again.

### 9.2 Requirements

| # | Requirement |
|---|---|
| P1 | There is exactly **one** machine-readable definition of the artifact language: the op set, the per-op required and forbidden fields, the enumerations, the bounds, the result shapes, and the rejection codes. It is a data file in the repository, it is the normative artefact, and this document describes it |
| P2 | The validator and the executor both derive from that definition. Neither contains a literal op token, a literal field name, a literal bound or a hand-written dispatch table. Adding an operation is a change to the definition plus a change to one implementation function, and it is a compile-time or load-time error for one to exist without the other |
| P3 | There is exactly one parser, and it runs once (§6 O1–O3) |
| P4 | Neither side may have an "ignore what you do not recognise" path. V6 is the whole policy for unknown input, on both sides |
| P5 | Every rejection code in this document is produced by exactly one site |
| P6 | A **conformance suite** derived from the definition asserts, for every operation: accepted minimal form, accepted maximal form, and one rejection per applicable rule in §7. It fails if the definition contains an operation with no conformance case |
| P7 | A **differential test** drives the validator and the executor from the same generated corpus and asserts the invariant: *the executor executes an artifact if and only if the validator accepted it, and executes exactly the operations the validator enumerated.* The corpus includes the encoding and near-miss variants in AD1.5 — case variations, Unicode confusables and normalisation forms in `colref`s, duplicate keys, unknown members alongside known ones, numeric strings where integers are required, bounds at and one past each limit, and op tokens differing from a valid token by one character |
| P8 | The differential test runs in CI on every change, and a divergence is a build failure |

### 9.3 What a divergence would look like

Recorded so it is recognisable in review, not only in the abstract:

- The validator resolves `colref` exactly; the executor resolves it with a trimmed or case-folded
  comparison. An artifact naming ` salary` passes validation as undeclared-rejected — or worse, fails
  to be rejected and then reads a column the profile never declared.
- The validator caps `top_n` at 100; the executor's default-on-zero path (`if(!(nlimit>0)){nlimit=10}`)
  accepts a negative value and some other layer interprets it as unbounded.
- The validator rejects `filter_col` without `filter_val`; the executor's `applyfilter` treats it as
  no filter. The artifact computes over the whole dataset while the validator believes it computed
  over a subset, and the disclosure record is wrong.
- The validator enumerates fifteen operations; `execute()` dispatches fourteen and returns a
  result-shaped value for the fifteenth (D1 and D3 together).

---

## 10. The second backend: parameterised SQL

### 10.1 What `std.db` provides

```
db.one  : (str, [str]) → Row!DbErr
db.many : (str, [str]) → [Row]!DbErr
db.exec : (str, [str]) → u64!DbErr
```

Both query functions take a statement and an array of bound parameters. A generated query can
therefore execute against the local store **without any string interpolation of model output**. That
is the whole reason this backend is admissible.

### 10.2 Absolute prohibition

> **SQL-1.** SQL text is never assembled from model output. Not by concatenation, not by formatting,
> not by templating, not by quoting-and-escaping, not "only for identifiers", not "only for integers".
> There is no exception, and no reviewable exception process.

A string-interpolated SQL statement built from an artifact is a rejection of the change, not a
rejection of the artifact.

The idiom to be eliminated already exists in the tree:
`packages/core/src/storage/audit.tk::getrecent` builds its `LIMIT` clause with `str.concat` on a
converted integer. The value there is internal rather than model-supplied, so it is not currently
exploitable — but it is the pattern, and the pattern is what gets copied onto a path where the value
*is* model-supplied. The correct form is the one `collector.tk` and `logevent` already use: a fixed
statement string with bound parameters.

### 10.3 How a query reaches SQL

Identifiers cannot be bound as parameters in SQL. That is the only genuine difficulty, and it is
resolved by never taking an identifier from the model at all:

| # | Rule |
|---|---|
| Q1 | Each of the fifteen operations has **one** fixed statement template, written by hand, held in the single definition (§9.2), and containing no substitution point other than `?` parameter markers and numbered identifier slots |
| Q2 | An identifier slot is filled only from loke's own canonical, already-quoted rendering of a column or table name **looked up by resolved index** into the schema profile. The model's string is used to *find* the index (§5 N1, exact equality) and is then discarded. No model-supplied byte reaches the statement text |
| Q3 | Every value — `filter_val`, `top_n`, `bucket_count` — is a bound parameter. Values never reach the statement text |
| Q4 | The assembled statement is a single `SELECT`. Exactly one statement, no statement separator, no comment token (`--`, `/*`, `#`), no CTE that writes, no `RETURNING` |
| Q5 | The statement executes on a connection opened read-only, against the store, with the row cap of §8 applied as a bound `LIMIT` parameter — not as a post-filter on a larger result set |
| Q6 | The assembled statement is compared against the template it was generated from: the two must be identical outside the identifier slots. This is a cheap assertion that Q1–Q3 were not bypassed, and it is recorded |
| Q7 | The assembled statement and its parameter array are recorded in the disclosure record (DA1.1) with parameter *values* omitted and only their count and types kept |

Q2 is the load-bearing rule and the one most likely to be softened under delivery pressure. "The
column name came from the model but we validated it against the profile first" is not Q2. Q2 is that
loke emits its own name for column *i*, and *i* is an integer.

---

## 11. Side-effecting constructs: rejected outright

### 11.1 Status of this section

The primary control is §2: none of the following is expressible in the grammar of §3.3. A denylist as
a *primary* control is the design that fails, and this section is not offered as one.

It exists for three reasons, all of which are real:

1. The SQL backend (§10) assembles statement text. Q4 and Q6 already forbid everything below, and
   this list is the explicit assertion of that, checkable independently.
2. Should a future change make SQL or any code form expressible — including anything proposed as "a
   small, safe subset" — these constructs must be rejected before that change ships, and the list must
   already exist.
3. The adversarial corpus (AD1.5) needs an enumerated target set to generate cases against, including
   the encoding and parser-differential variants.

### 11.2 SQL-shaped constructs

| Construct | Effect | Disposition |
|---|---|---|
| `COPY … TO` / `COPY … TO PROGRAM` | Writes query results to a file or pipes them to a command | Reject |
| `INTO OUTFILE`, `INTO DUMPFILE` | Writes results to a file on the server host | Reject |
| `ATTACH`, `DETACH` | Binds another database file into the session, escaping the authorised dataset | Reject |
| `load_extension()`, `LOAD`, `CREATE EXTENSION`, `CREATE FUNCTION`, `CREATE LANGUAGE` | Loads native code or defines a UDF — arbitrary code execution | Reject |
| `PRAGMA`, `SET`, `ALTER SYSTEM` | Changes engine behaviour, including trust and path settings | Reject |
| `readfile()`, `writefile()`, `fileio_*`, `lo_import`, `lo_export` | Filesystem access from SQL | Reject |
| `.import`, `.output`, `.shell`, `.system`, `.load` and any dot-command | Client-side commands with host effects | Reject |
| `INSERT`, `UPDATE`, `DELETE`, `REPLACE`, `UPSERT`, `TRUNCATE`, `DROP`, `ALTER`, `CREATE`, `MERGE` | Mutation. The artifact path is read-only | Reject |
| `GRANT`, `REVOKE`, `CREATE ROLE` | Privilege change | Reject |
| `dblink`, `postgres_fdw`, any foreign-data wrapper, any `http`/`curl` SQL function | Outbound network egress from inside the query | Reject |
| Any statement separator producing a second statement | Statement chaining | Reject (Q4) |
| Any comment token | Truncation and differential attacks | Reject (Q4) |

### 11.3 Python-shaped constructs

Recorded because a Python artifact is the obvious next request, and because the benchmark harness for
arm C of the correctness experiment runs Python in a *harness* sandbox that has no counterpart in
production (see `docs/specifications/correctness-benchmark.md` §4.4). Nothing in this table is
admissible in a production artifact.

| Construct | Effect | Disposition |
|---|---|---|
| `import`, `from … import`, `__import__`, `importlib` | Capability acquisition. Module allowlists are routinely escaped via `__builtins__`, `__subclasses__` and attribute traversal | Reject — and reject an allowlisted-import design as a whole |
| `requests`, `urllib`, `http.client`, `socket`, `ftplib`, `smtplib`, `aiohttp` | Outbound egress | Reject |
| `os.system`, `os.popen`, `os.exec*`, `subprocess`, `pty`, `commands` | Command execution | Reject |
| `open`, `io.open`, `pathlib`, `shutil`, `tempfile`, `os.remove`, `os.rename` | Filesystem access | Reject |
| `eval`, `exec`, `compile`, `codeop`, `ast.literal_eval` on model input | Dynamic code | Reject |
| `pickle`, `marshal`, `shelve`, `dill`, `joblib.load`, `numpy.load` with `allow_pickle` | Deserialisation-to-execution | Reject |
| `pd.read_csv`, `pd.read_json`, `pd.read_parquet`, `pd.read_sql` or any `read_*` given a URL or a path outside the authorised dataset | Reads unauthorised data, or fetches remotely | Reject |
| `DataFrame.to_csv` / `to_json` / `to_sql` / `to_pickle` with any destination | Writes results out of process | Reject |
| **Any URL literal** — any `http://`, `https://`, `ftp://`, `file://`, `data:`, `//host`, or scheme-shaped prefix | Egress target | Reject |
| **Any hostname-shaped or IP-shaped literal**, including DNS-resolvable names used for out-of-band signalling | Egress target, including DNS-only exfiltration | Reject |
| `%`, `.format`, f-strings, `+` or `.join` applied to anything that becomes a query, a path, a command or a URL | String interpolation into a sink | Reject |
| `__builtins__`, `__globals__`, `__class__`, `__bases__`, `__subclasses__`, `getattr`, `setattr`, `globals`, `vars` | Sandbox-escape primitives | Reject |
| `ctypes`, `cffi`, `mmap`, `resource`, `signal`, `threading`, `multiprocessing`, `asyncio` | Native and concurrency primitives | Reject |
| `input`, `sys.stdin` | Interaction with the host process | Reject |

### 11.4 Matching rules

| # | Rule |
|---|---|
| M1 | Matching is on the **parsed** structure where one exists — the validated artifact object, or the assembled statement compared to its template (Q6). Matching on raw text is a supplementary check only |
| M2 | A match is a rejection of the artifact. It is never a redaction, a rewrite, a strip-and-continue, or a "warn and proceed" |
| M3 | Encoding variants are matched: case variation, Unicode escapes, percent-encoding, hex and octal escapes, base64-shaped literals, concatenated fragments, and comment-interrupted keywords. The corpus in AD1.5 generates them; this list is the specification of what it must cover |
| M4 | The denylist's own coverage is reported as a measured false-negative rate against that corpus, not asserted as complete. A denylist claiming completeness is the claim §2 exists to avoid having to make |

---

## 12. Rejection: failing closed

### 12.1 Behaviour

| # | Rule |
|---|---|
| R1 | A rejected artifact is **not executed, in whole or in part**. There is no partial execution of the cards that validated |
| R2 | No repair. loke does not strip an offending field, drop an offending card, coerce a type, or substitute a nearest-matching column |
| R3 | No fallback to transmission. Rejection must not cause the request to be retried on the anonymise-and-send path automatically. That path is selectable only by an explicit, recorded user decision (NC1.8) |
| R4 | No fabricated output. A card with no locally-resolved value displays no number (NC1.5), and a rejected artifact produces no dashboard |
| R5 | The user sees the rejection code, the element that failed, and the rule that failed, in plain language |
| R6 | The rejection is recorded: correlation ID, rejection code, failing element path, the artifact's SHA-256 digest, and the schema fingerprint. The artifact text itself is retained only if artifact retention is enabled, and never beyond the audit retention period |
| R7 | **Bounded re-ask.** loke may re-ask the model at most `MAX_REASKS` times (default 1). The re-ask carries only the rejection code, the failing element path, and the same schema profile. It carries **no data value, no result, and no dataset content**. A re-ask is a new external dispatch with its own disclosure record |
| R8 | On exhausting the re-ask budget, loke reports failure. It does not degrade to a lower-assurance path on its own initiative |
| R9 | If the validator itself cannot run — the single definition is unreadable, the profile for that correlation ID is missing, the fingerprint cannot be computed — the artifact is rejected. An unavailable control is a closed control, per NC1.9 |

R9 is the general form of the defect NC1.9 fixes elsewhere in the pipeline: when the detection sidecar
is unavailable, `packages/browser/pages/api/pipeline.tk` currently falls back to five substring checks
and still transmits. A filter that fails open is worse than one that fails closed, because it reports
success.

R7's constraint on the re-ask content matters more than it looks. The natural repair loop — "that
failed, here is the error and a few sample rows to help you get it right" — converts a validation
failure into a data disclosure, on the one path whose entire purpose is that no data is disclosed.

### 12.2 Rejection codes

| Code | Rule | Meaning |
|---|---|---|
| `E-PARSE` | V1 | Not well-formed JSON, or not a single object |
| `E-VERSION` | V2 | Unknown or absent contract version |
| `E-SIZE` | V3 | Payload over `MAX_PAYLOAD_BYTES` |
| `E-DEPTH` | V4 | Nesting over `MAX_DEPTH` |
| `E-DUPLICATE-KEY` | V5 | Duplicate member name |
| `E-UNKNOWN-FIELD` | V6 | Member not in the grammar |
| `E-MISSING-FIELD` | V7 | Required member absent |
| `E-TYPE` | V8 | JSON type mismatch |
| `E-OP-UNKNOWN` | V9 | `op` not in the closed set |
| `E-OP-ARITY` | V9 | Required field absent, or forbidden field present, for that op |
| `E-COLUMN-UNDECLARED` | V10 | `colref` not in the transmitted profile |
| `E-DATASET-UNDECLARED` | V10 | Dataset not in the transmitted profile |
| `E-SCHEMA-DRIFT` | V10 | `schema_fingerprint` does not match |
| `E-COLUMN-SHAPE` | V11 | Column's declared type is wrong for the op |
| `E-FIELD-SHAPE` | V12 | Identifier, enumeration or length constraint failed |
| `E-LITERAL-SHAPE` | V13 | `filter_val` is not an admissible literal |
| `E-BOUND` | V14 | Numeric bound exceeded |
| `E-PROSE-NUMBER` | V15 | Prose card carries a number not present in the question |
| `E-BUDGET` | V16 | Artifact or session result budget exceeded |
| `E-SQL-SHAPE` | V17 | Assembled statement failed a §10 rule |
| `E-DENYLIST` | V18 | Matched §11 |
| `E-VALIDATOR-UNAVAILABLE` | R9 | The control could not run |

---

## 13. Acceptance criteria

| # | Criterion |
|---|---|
| A1 | A single machine-readable definition file exists, and both the validator and the executor are driven by it. No op token, field name or bound appears as a literal in either |
| A2 | The conformance suite covers all fifteen operations in accepted-minimal and accepted-maximal form, and produces at least one case per rejection code in §12.2. It fails if the definition holds an operation with no case |
| A3 | The differential test (P7) passes: for every corpus item, the executor executes it if and only if the validator accepted it, and executes exactly the enumerated operations. It runs in CI and a divergence fails the build |
| A4 | An artifact naming an operation outside §4.1 is rejected with `E-OP-UNKNOWN` and nothing executes. `execute()` no longer returns `"error:unknown_op"` as a result value (D3) |
| A5 | An artifact naming a column absent from the transmitted profile is rejected with `E-COLUMN-UNDECLARED`. No silent zero is produced (D-N4) |
| A6 | An artifact whose `schema_fingerprint` does not match the profile held for its correlation ID is rejected with `E-SCHEMA-DRIFT`, including when the artifact is replayed from cache |
| A7 | An artifact carrying any member not in the grammar is rejected with `E-UNKNOWN-FIELD`. No configuration makes unknown members ignorable |
| A8 | An artifact with `filter_col` and no `filter_val` is rejected with `E-OP-ARITY`, and does not compute over the whole dataset |
| A9 | The vocabulary divergence D4 is gone: no module constructs a card naming an op the executor does not dispatch, and `deltaqueryop` is either implemented or removed (D5) |
| A10 | No SQL statement executed on the artifact path contains a byte that originated in model output. Demonstrated by a test that supplies a `colref` chosen to be a SQL fragment and asserts both that the artifact is rejected at V10 and that the assembled-statement comparison (Q6) would have caught it had validation been bypassed |
| A11 | Every statement on the SQL backend is a single read-only `SELECT` on a read-only connection, with its row cap bound as a parameter |
| A12 | Every construct in §11.2 and §11.3, and its encoding variants from the AD1.5 corpus, is rejected. The measured false-negative rate against that corpus is published in `docs/metrics-baseline.md`; it is not asserted to be zero |
| A13 | A rejected artifact produces no rendered card, no number, and no automatic retry on the anonymise-and-send path. Re-asks are bounded at `MAX_REASKS` and provably carry no data value |
| A14 | With the single definition file made unreadable, every artifact is rejected with `E-VALIDATOR-UNAVAILABLE` and nothing is executed or transmitted |
| A15 | Every validation verdict, every budget consumption and every rejection appears in the disclosure record with its correlation ID |

---

## 14. Open problems

Stated rather than resolved, because each is a real gap and a specification that hides one is worse
than a specification that names it.

| # | Problem |
|---|---|
| U1 | **The query-shaped channel is bounded, not closed** (findings §11, NC1.10). The §8 budgets limit the rate of an iterative extraction; they do not prevent it, they are evadable across sessions, and the values are unmeasured placeholders. Until NC1.10 produces a measured operating point, the no-custody claim carries this limitation wherever it appears |
| U2 | **Column names can themselves carry data.** A profile column named `col_ssn_078_05_1120` discloses a value through the schema, and this contract validates such a name as a perfectly good identifier. That is an NC1.2 and AD1.5 concern; noted here because the contract cannot detect it |
| U3 | **The schema is not nothing.** Table and column names have been reconstructed from a deployed text-to-SQL system at F1 up to 0.99 (findings §10). The correct framing for what the artifact path discloses is *bounded and auditable* — O(schema) rather than O(data), declared, with the exact bytes reviewable — never "low leakage" |
| U4 | **Expressiveness cost is unmeasured.** The closed set will fail to express some legitimate questions. That cost is counted against the architecture in `docs/specifications/correctness-benchmark.md`, where an inexpressible item is scored incorrect rather than skipped. The number is not yet known |
| U5 | **No period comparison exists.** `deltaqueryop` implies one and nothing implements it (D5). Adding one means adding a date-range concept to `$query`, which widens the language, the result budget and the extraction surface together. It is deferred deliberately |
| U6 | **Cross-dataset joins beyond one other dataset** are outside the contract, and the authorisation model for which datasets may be joined is specified only as "declared in the profile". A richer join model needs an authorisation rule of its own |
