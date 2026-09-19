# Correctness Benchmark Specification — Three Arms

**Stories:** CB1.1 — Define the three arms, and the honest framing; CB1.3 — Output-contract control
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-09-19

---

## 1. Overview

loke's no-custody path withholds data from the model. The question this experiment answers is what that
costs in correctness, on a benchmark loke did not design, measured against the status quo of putting the
data in the prompt.

This specification defines:

- The three arms, what each sends and receives, and what the differences between them mean
- The controlled variables, of which the output contract is the most dangerous
- Benchmark selection, and why each choice was made and each exclusion made
- **The output-contract control (§6), which is the most important section in this document**
- The statistics, which are paired and tested with McNemar rather than as independent proportions
- What counts as an item arm C failed, and why an inexpressible question is a loss rather than a skip
- The reporting template, and the pre-registration freeze

### 1.1 The framing constraint, stated first

Per `docs/research/disclosure-measurement-findings.md` §10:

> **Arm C's data flow is not novel.** Schema-out / artifact-back / execute-locally is the default
> implementation of the entire text-to-SQL field — BIRD, Spider and Spider 2.0 all hand the model a
> schema and score by executing the returned query against a database the model never saw. It ships
> commercially in Vanna.AI, WrenAI, Snowflake Cortex Analyst and Databricks Genie. It is published as a
> named pattern, and arXiv:2512.04852 (*Ask Safely*) applies it to knowledge graphs with almost exactly
> loke's privacy rationale.

Three consequences, which govern how this document is written:

1. **Nothing here is claimed as an invention.** A reviewer retires a novelty claim about this data flow
   in one sentence. What is being measured is the *cost* of enforcing it strictly.
2. **Arm C should be expected to lose ground on some question classes.** The field moved *away* from
   schema-only because it underperforms: sample rows and value retrieval are standard in competitive
   systems, and MaskSQL — far more permissive than loke, in that it sends masked values — still pays
   roughly 20 execution-accuracy points on BIRD. The work is planned around quantifying that cost
   credibly, not around proving it does not exist.
3. **A favourable result is not the goal.** This document must not be written as though it were. Where a
   design choice could bias the comparison toward arm C, the choice is made the other way and the reason
   is recorded. §6 and §7.5 are both instances of that.

The genuine contribution sits elsewhere — enforcement, the threat model, and the measurement — and it is
specified in `docs/specifications/artifact-contract.md`, `docs/specifications/disclosure-accounting.md`
and `docs/specifications/exposure-metric.md`. This experiment's job is to make the cost side of the
trade honest and numerate.

### 1.2 Design Alignment

- **Negative results are results.** A result unfavourable to arm C is published in
  `docs/metrics-baseline.md` with the same prominence as a favourable one. That file requires it.
- **Privacy is the foundation.** The experiment does not weaken the artifact contract to raise arm C's
  score. If the contract cannot express an item, that is the measurement.
- **Warnings must be earned.** Applies to claims as much as to dialogs. An effect inside the confidence
  interval is reported as not resolvable at this N.

### 1.3 Dependencies

| Dependency | Story | Relationship |
|---|---|---|
| Measurement substrate | VM1.1–VM1.5 | No numeric result can be recorded, repeated or reproduced without it. `std.test` cannot carry a number |
| Artifact contract | NC1.1 | Defines what arm C can express, and therefore its coverage ceiling |
| No-custody schema profile | NC1.2 | Arms B and C send this and nothing else. Until it stops embedding sample values, arms B and C are not schema-only |
| Local execution engine | NC1.7 | Executes arm C's artifacts |
| Scoring harness | CB1.2 | Implements §5 and §7 |
| Reformat freeze | CB1.2a | Implements §6 |
| Annotation-error pre-emption | CB1.4 | Implements §7.5 |
| Token accounting | CB1.5 | Implements §8 |
| Prior-art positioning | CB1.6 | Consumes these results |
| Disclosure accounting | DA1.1 | Supplies the per-arm disclosure figures |
| Exposure metric | EM1.3 | Reports the exposure vector per arm on this workload |

---

## 2. The three arms

| Arm | Name | Sent to the model | Received | Executed where | Scored on |
|---|---|---|---|---|---|
| **A** | Data in the prompt | The question **and the data** — the status quo for analysis work | A prose answer containing the answer | Nowhere; the model computed it | The extracted answer |
| **B** | Schema only, model answers directly | The question and the NC1.2 schema profile. No rows | A prose answer containing the answer | Nowhere; the model produced a number without the data | The extracted answer |
| **C** | Schema only, artifact executed locally | The question and the NC1.2 schema profile. No rows | A validated artifact (NC1.1) | Locally, by loke, against data that never left the device | The answer computed from the local result |

### 2.1 What the three arms decompose

Two arms would confound two different things. Three separate them:

| Contrast | Measures |
|---|---|
| **A − B** | The cost of withholding the data, with nothing put back. Arm B is the model guessing from structure alone, and it is expected to be poor |
| **C − B** | The value of local execution — what is recovered by executing a specification against the real data |
| **A − C** | **The primary comparison.** The net cost of strict no-custody against the status quo |

Arm B is not a strawman to be beaten; it is the term that makes A − C interpretable. Without it, a small
A − C gap could be read as "withholding data barely matters", when the correct reading is "withholding
data matters a great deal and local execution recovers most of it".

### 2.2 Which model does what, per arm

This is CB1.1's explicit requirement, and it answers a specific objection in advance.

| Arm | Generation model | Local model | Local execution |
|---|---|---|---|
| A | The frontier model under test | None | None |
| B | The same frontier model, same version pin | None | None |
| C | **The same frontier model, same version pin** | None for generation | loke's deterministic artifact executor |

> **Arm C does not use a local model for generation at all.** The frontier model does the reasoning in
> every arm. Locality applies to *custody of the data* and to *execution of the artifact*, not to
> inference. The objection "your architecture is handicapped by weak local models" does not apply to
> this experiment, and that is why the arms are defined this way rather than pairing no-custody with
> local inference.

A separate, later experiment may substitute a local generation model in arm C. It is out of scope here,
because it would confound the disclosure regime with model capability — which is the confound §6 exists
to prevent in another form.

### 2.3 Arm definitions are exact

| # | Rule |
|---|---|
| E1 | Arm A's prompt contains the data in the benchmark's own form (CSV content), unmodified and untruncated. If an item's data exceeds the context window, that is recorded as an arm A context failure and the item is scored incorrect for arm A. Truncating arm A's data to fit would quietly convert the status-quo baseline into a weaker arm |
| E2 | Arms B and C receive the NC1.2 profile: column names, inferred types, cardinality, null rate, row count, and nothing else. A sentinel assertion runs per request: a value unique in the dataset appears zero times in the captured outbound payload. **An arm that fails the sentinel check is not schema-only and its run is void** |
| E3 | Arm C's artifact is validated against the contract (NC1.1) before execution, with no relaxation for the benchmark. A rejected artifact consumes the same bounded re-ask budget the product uses, and then the item is scored incorrect |
| E4 | Arm C's execution uses the production executor, not a benchmark-only path. A benchmark-only executor would measure something loke does not ship |
| E5 | The question text is byte-identical across arms |

---

## 3. Controlled variables

Every variable below is fixed across arms. The only intended differences are the data/schema block and
the required output kind.

| Variable | Control |
|---|---|
| Generation model and version | One model, one pinned version string, recorded per result (VM1.2) |
| Decoding parameters | Identical: temperature, top-p, max tokens, stop sequences. Temperature 0 where the provider supports it |
| Seed | Fixed and recorded where the provider supports it |
| Prompt template | One template per arm, differing only in the data/schema block and the output-kind instruction. **The full diff between arm templates is published** |
| System prompt | Identical across arms |
| Few-shot examples | Identical count and content, or none in every arm. None is preferred: examples are a hidden format lesson, and a different number per arm is §6's confound in another costume |
| Attempt and retry budget | Identical. Arm C's artifact re-ask counts against the same budget as an arm A retry |
| Tool availability | Identical. No arm has a tool another lacks |
| Item set | Identical and complete. Same items, same order, same pairing (§7) |
| Output contract | §6 — the reformat step, identical, frozen, symmetric |
| Runs per configuration | Identical N, first run discarded as warm-up (VM1.3) |
| Container image | One pinned image, digest recorded (VM1.4) |

### 3.1 Prompt instructions that must not differ

| # | Rule |
|---|---|
| C1 | No arm's prompt contains guidance about answer formatting that another's lacks. Format guidance is part of the output contract and is governed by §6 |
| C2 | No arm's prompt tells the model to be concise, careful, or step-by-step unless every arm's does |
| C3 | Arms B and C must not be told that data is unavailable in terms that invite abstention, while arm A is not. An abstention rate difference caused by prompt wording would be read as an accuracy difference |
| C4 | The instruction `Use realistic sample values that match the dataset schema`, present in moke's production prompts (`dashboard.tkt:1019` and `:1095`, `chat.tkt:2527`), appears in no arm. It instructs fabrication, which NC1.4 removes from the product and which would make arm B and arm C outputs unscoreable |

---

## 4. Benchmark selection

### 4.1 Primary: InfiAgent-DABench

arXiv:2401.05507, ICML 2024, Apache-2.0.

| Property | Value |
|---|---|
| Items | 257 closed-form questions |
| Data | 52 CSV files |
| Axes | 7 concept categories **and** 9 domains. The frequently-quoted "7 categories" is the *concept* axis, not the domain axis |
| Scoring | Strict: an item counts only if **all** its sub-questions are correct |
| Harness requirement | A Python execution sandbox (Docker or subprocess) |
| Licence | Apache-2.0 |

**Why primary, and it is the only reason that matters:** DABench is the only candidate where **pasting
the data is the honest status-quo baseline**. A data analyst with a CSV and a chat window pastes the
CSV. That is the behaviour arm A represents, and arm A is only a meaningful baseline where it represents
what people actually do.

On the text-to-SQL suites, schema-only is *already* standard practice — it is how the benchmarks are
constructed. Running the three arms there would compare loke against the field's own default and call
the absence of a difference a result. Measuring there proves nothing about the cost of no-custody,
because there is no custody in the baseline either.

### 4.2 Secondary: BIRD Mini-Dev

500 items across SQLite, MySQL and PostgreSQL; CC BY-SA 4.0.

Included for external comparability — BIRD is the suite readers know — and reported with three
qualifications, all of which must travel with any BIRD figure:

| # | Qualification |
|---|---|
| Q1 | **R-VES is not a standalone headline.** BIRD's metrics are EX (execution accuracy, set equality on returned rows) and R-VES, which has replaced raw VES and is computed **only over queries that pass EX**. It is therefore **not comparable across systems with different EX**, and an arm with lower EX can show a flattering R-VES over the easier subset it happened to get right |
| Q2 | **BIRD is near saturation.** Leaderboard EX is around 82 against reported human performance of 92.96, so a ±2 pp difference sits inside leaderboard churn and is not a result |
| Q3 | **Arm A is not the status quo here.** Pasting a multi-table database into a prompt is not what anyone does, so arm A on BIRD is a synthetic upper bound rather than a baseline, and is labelled as such |

### 4.3 Excluded: Spider 2.0-Snow

**Excluded on evidence, not on preference.** The annotation-error audit (Jin, Choi, Zhu, Kang, *Pervasive
Annotation Errors Break Text-to-SQL Benchmarks and Leaderboards*, arXiv:2601.08778 v3 = PVLDB Vol 19
No 5, CC BY 4.0) found a **62.8% error rate on Snow specifically** (66.1% in the CIDR 2026 workshop
precursor). At that rate, scores above roughly 80 are close to meaningless, and a paired comparison
whose effect size is a few points cannot be read through that much label noise.

Spider 2.0-Lite or -DBT would be defensible if a text-to-SQL suite beyond BIRD were needed. Two cautions
if either is used: Spider 2.0 schemas often contain over 1,000 columns and up to around 3,000 — the
frequently-quoted "average 700–800 columns" is secondary-source only and is not asserted — and Spider
2.0's relaxed execution-accuracy semantics live in the evaluation code and are **not documented** on the
official site, so the evaluation suite must be read before relying on them.

### 4.4 The sandbox distinction, which must not be blurred

DABench requires a Python execution sandbox. That sandbox is a property of the **benchmark harness**, and
it has no counterpart in loke.

| # | Rule |
|---|---|
| S1 | The harness's Python sandbox executes the *benchmark's* gold solutions and, in arm A and B, evaluates nothing but the extracted answer. It is never the execution path for a model-returned artifact |
| S2 | Arm C executes through the production artifact executor over the closed operation set (NC1.1). It does not execute Python. toke exposes no sandboxing primitive, which is exactly why the operation set is closed |
| S3 | No result from this experiment may be presented as evidence that loke can safely execute model-generated code. It is evidence about a closed operation set only |
| S4 | The harness sandbox's isolation properties are the harness's problem. They are stated in the harness documentation and are not a loke security claim |

### 4.5 Optional tertiary

DataSciBench (arXiv:2502.13897; 222 effective prompts / 519 test cases; best reported API model 64.51%)
may be added for breadth. It is not required, and adding it does not change the primary comparison.

### 4.6 Gold-executability invariant, asserted first

| # | Rule |
|---|---|
| X1 | Before any arm runs, the harness asserts for every item that the **gold** answer is reproducible in the harness environment |
| X2 | Items where it is not are reported as a **harness-excluded set** with its size and the reason per item. They are not silently dropped |
| X3 | The primary result is reported twice: over all 257 items, and over the gold-executable subset. Both figures appear together |
| X4 | If the harness-excluded set exceeds 10% of items, the harness is the problem and is fixed before the experiment is run |

---

## 5. Coverage: an inexpressible item is a loss, not a skip

The strongest temptation in this experiment is to exclude items arm C cannot express. It must be
resisted, and the rule is stated before the statistics because it determines the denominator.

| # | Rule |
|---|---|
| K1 | **The denominator is always all items** in the benchmark subset under test — 257 for DABench. It is identical for all three arms, always |
| K2 | An item arm C cannot express within the artifact contract is **scored incorrect for arm C**. It is not skipped, not excluded, and not moved to a separate "unsupported" category that is then removed from the rate |
| K3 | An artifact rejected by the validator after the bounded re-ask budget is scored incorrect. Validation failures are part of the cost being measured |
| K4 | **Coverage is reported as a first-class result**: the count and proportion of items arm C could express, with a breakdown by DABench concept category and domain. This is the most useful single output of the experiment for the roadmap, because it names which operations are missing |
| K5 | Items arm C could not express are listed with the reason — missing operation, unsupported predicate, composition required, no period operation (NC1.1 D5) — so the list is actionable rather than a number |
| K6 | An arm A context-window failure (E1) is likewise scored incorrect for arm A, not excluded |

---

## 6. The output contract — the largest internal-validity threat

**This section is the most important part of this document.** An experiment that gets everything else
right and this wrong produces a number that measures format compliance and reports it as
privacy-preserving correctness.

### 6.1 The mechanism

DABench's harness post-processes model output into its `@answer_name[value]` template using a **separate
reformat model**. The scorer does not read the model's prose; it reads the reformatted template.

### 6.2 The magnitude

From findings §13:

| Model | Without reformat | With reformat | Delta |
|---|---|---|---|
| Mistral-7B-Instruct | 6.23 | 38.67 | **+32.44** |
| Qwen-72B | 44.75 | 59.92 | +15.17 |
| GPT-4 | 72.76 | 78.99 | +6.23 |

Up to **32 accuracy points**. That is larger than any plausible effect of the disclosure regime under
test, and it is a step outside the model's own reasoning.

### 6.3 The specific failure mode

Arm C's output is a **structured specification** — a validated artifact, machine-parseable by
construction, from which a locally-computed value is extracted deterministically. Arm A's output is
**prose with an answer embedded in it**.

If the reformat step is applied asymmetrically, or is skipped where the output is "already parseable",
then:

- arm C is scored on a clean extraction
- arm A is scored on whatever the reformat step made of its prose
- the measured difference is largely **format compliance**
- and it is reported as the correctness cost of the disclosure regime

The difference in the wrong direction would be equally invalid. The failure is asymmetry, whichever arm
it favours.

### 6.4 The two-stage pipeline, published and symmetric

A single frozen reformat step is necessary but not sufficient, because arm C's output is not the same
*kind* of object as arm A's. The output is therefore normalised in two published stages, and the arms
converge at a defined point:

```
raw arm output
   │
   ├── Stage 1: arm-specific rendering to a COMMON INTERMEDIATE FORM
   │            a plain-text answer statement. Deterministic, published,
   │            no model involved. Arm C's structural advantage ends here.
   │
   └── Stage 2: the SINGLE FROZEN REFORMAT MODEL, applied to the
                common intermediate form. Identical for every arm.
   │
   └── Scored by the benchmark's own scorer.
```

| # | Rule |
|---|---|
| O1 | **Stage 1 is deterministic and model-free.** Arm A's rendering is the identity function on the model's text. Arm C's rendering is a fixed template applied to the locally-computed result. Arm B's is the identity function. No stage-1 rendering involves a language model, a heuristic parser or a regular expression tuned per item |
| O2 | **Stage 1 renderings are published in full**, as code, alongside the results. This is where arm C's parseability advantage is removed, and a reader must be able to check that it was removed rather than reduced |
| O3 | **Stage 2 is one reformat model**: one version pin, one prompt, one decoding configuration, frozen before the first scoring run, with a recorded digest of prompt and configuration |
| O4 | **Stage 2 is applied to every arm's output, always** — including outputs that are already in template form. There is **no bypass for "already correctly formatted"**. The bypass *is* the asymmetry |
| O5 | **Stage 2 sees only the common intermediate form.** It never sees the artifact, the schema, the question's data, the arm label, or which arm produced the text. Arm identity is withheld from the reformat step |
| O6 | Stage 2's own outputs are recorded verbatim, so the reformat step's behaviour is auditable after the fact |

O5 is worth being explicit about: if the reformat model can tell which arm it is serving, it can be
differentially helpful, and a reformat model that is differentially helpful is an uncontrolled treatment
applied to the treatment arm.

### 6.5 Both reformat-on and reformat-off are reported

| # | Rule |
|---|---|
| O7 | Every arm is scored **both** with stage 2 and without it. The primary results table is 3 arms × 2 reformat conditions, always. There is no single-number result |
| O8 | The **reformat delta per arm** is reported as a first-class result, not as a diagnostic |
| O9 | **Pre-registered symmetry gate.** If the reformat deltas differ across arms by more than **5 percentage points**, the primary comparison is reported **reformat-off**, and the discrepancy is reported as a finding in its own right. The 5 pp margin is pre-registered before the first run, and is chosen to sit below the smallest published per-model delta in §6.2 |
| O10 | **Format-compliance rate per arm** — the proportion of raw outputs the benchmark's scorer could read without stage 2 — is reported per arm. If it differs materially, the confound is visible rather than inferred |
| O11 | A stratified random sample of at least 50 stage-2 outputs is hand-audited for whether the reformat changed the substance of the answer rather than its shape. The audit is published, and any substance change is a defect in the pipeline, not a scoring outcome |
| O12 | No per-item, per-arm or per-category tuning of any stage. A prompt change to either stage after the first scoring run voids the run |

### 6.6 Why the output contract is a controlled variable and not an implementation detail

Adherence to a required output format materially changes scores on published analysis benchmarks — by up
to 32 points, larger than the effect under study. A variable of that magnitude that is not controlled is
not an implementation detail; it is the dominant term. It is listed in §3 with the model and the
decoding parameters, it has its own pre-registered gate, and it is reported in every results table
(CB1.3).

---

## 7. Statistics

### 7.1 What 257 items can support

257 items gives roughly **±6 percentage points** of binomial confidence at 95% for a single arm's
accuracy. That is wider than the effect this experiment is likely to be looking for.

Consequence: **two independent proportions cannot resolve the difference.** Comparing arm A's accuracy
to arm C's as if they were independent samples would be the wrong test on the wrong data, and would
produce a confidence interval wide enough to be consistent with almost any conclusion.

### 7.2 Paired design and McNemar's test

| # | Rule |
|---|---|
| M1 | **Arms are paired on identical items.** Same 257 items, same data files, same question text, same run index. The pairing is at the item level and is preserved through every stage of §6 |
| M2 | **Comparisons use McNemar's test** on the 2×2 table of concordant and discordant outcomes, exact binomial where discordant counts are small. Never two independent proportions |
| M3 | **Discordant-pair counts are published** — `b` (A right, C wrong) and `c` (A wrong, C right). They are the informative quantity, and a reader who has them can redo the test |
| M4 | The paired difference is reported with a confidence interval appropriate to paired proportions (Newcombe's method for the difference of paired proportions), alongside each arm's own Wilson interval |
| M5 | **Power is reported honestly.** McNemar's detectable effect depends on the discordance rate, which is not known before the run. After the run, the minimum detectable difference at 80% power given the observed discordance is computed and published. If the observed difference falls below it, the result is reported as **not resolvable at this N** — not as "no difference" and not as "a trend" |

### 7.3 Multiplicity

| # | Rule |
|---|---|
| M6 | The **primary comparison is pre-registered**: arm A versus arm C, on DABench, reformat-on, over all items |
| M7 | All other comparisons — A versus B, B versus C, per-category, per-domain, reformat-off, BIRD — are secondary and are corrected with Benjamini–Hochberg, consistent with the methodology already established in `docs/research/toon-benchmark-methodology.md` |
| M8 | Per-category and per-domain breakdowns over 257 items across 7 concept categories and 9 domains put very few items in some cells. Cell N is published with every breakdown, and cells below 15 items are reported as descriptive only, with no test |

### 7.4 Repetition

| # | Rule |
|---|---|
| M9 | N runs per configuration with the first discarded as warm-up (VM1.3), BCa bootstrap intervals. No single-run number is published |
| M10 | Pairing holds **within** a run index: run *i* of arm A pairs with run *i* of arm C on the same item. Aggregating across runs before pairing would discard the pairing that §7.2 depends on |
| M11 | Where decoding is not deterministic, the per-item outcome distribution across runs is published, not only the mean |

### 7.5 Annotation errors — the pre-emption

Published benchmarks carry large annotation-error rates: **BIRD Mini-Dev 52.8%**, Spider 2.0-Snow
62.8–66.1%. Re-evaluating 16 open-source agents on corrected labels moved scores by **−7% to 31%** and
rankings by **−9 to +9** positions. Cite the journal version — arXiv:2601.08778 v3 = PVLDB Vol 19 No 5 —
as primary, not only the CIDR 2026 workshop precursor, which covers 5 systems and reports −3% to 31%.

The rank-correlation evidence is worth quoting directly: uncorrected versus full dev ranking gives
Spearman rs = 0.85, p = 3.26e-5; corrected versus full dev gives rs = 0.32, p = 0.23 — not significant.

**loke's pre-emption is stronger and cheaper than the paper's own recommendation**, and it should be
stated rather than implied:

> Because this comparison is **within-benchmark and paired** — the same question, the same data, two
> disclosure regimes — annotation errors are a **shared confound that largely cancels in the difference**.
> An item with a wrong gold label is wrong for arm A and wrong for arm C alike, and contributes to
> neither discordant cell unless the arms differ on it for some other reason.

| # | Rule |
|---|---|
| N1 | Report **paired deltas**, not leaderboard-style absolutes, as the headline |
| N2 | **Hand-audit a stratified random sample of about 100 items** and publish the audit — per-item verdicts, not a summary rate |
| N3 | Report the primary comparison on the **raw** set and on the **audited** subset, separately, both with their N |
| N4 | State the cancellation argument explicitly wherever an absolute figure is unavoidable. The argument does not license quoting absolutes as leaderboard-comparable |
| N5 | Do **not** restate the claim that CHESS rose from 62% to 81% after correction. The paper reports **67.3% → 76.3% (+9.0 pp)**, and the secondary claim that it moved 7th → 1st is unverified |

### 7.6 Void conditions

A run is void, not adjusted, if any of these holds. Recorded so the decision is not made under pressure
after the fact.

| # | Condition |
|---|---|
| Z1 | The sentinel check fails on any arm B or arm C dispatch (E2) — the arm was not schema-only |
| Z2 | Either stage of §6.4 was changed after the first scoring run (O12) |
| Z3 | Model version, decoding parameters or prompt template differed across arms outside the permitted diff (§3) |
| Z4 | The item set was not identical across arms (K1) |
| Z5 | The gold-executability excluded set exceeds 10% (X4) |
| Z6 | The pre-registration digest does not match the configuration actually run |

---

## 8. Token and cost accounting per arm

Brief, because CB1.5 owns it, and because it is the second falsifiable claim this experiment supports.

| # | Rule |
|---|---|
| A1 | **Tokens per completed task**, with arm A as the named baseline. The denominator is *completed* tasks by the benchmark's own scoring, so a reduction that breaks the task does not count as a reduction |
| A2 | The tokeniser is named, and `tokens_source` distinguishes provider-reported from estimated (DA1.1 §5.3) |
| A3 | Arm C's total includes the artifact, every re-ask, and the outbound bytes of any result returned to the model. Counting only the first dispatch would understate it |
| A4 | Cost figures state the model and the price date |
| A5 | The per-arm disclosure figures from DA1.1 and the per-arm exposure vector from EM1.3 are reported in the same table as accuracy. Accuracy without the disclosure figure beside it is the comparison this experiment exists to avoid making |

---

## 9. Reporting

### 9.1 Primary results table

Every published version of this table carries all six cells. There is no headline number extracted from
it.

| | Arm A — data in prompt | Arm B — schema only, direct | Arm C — schema only, artifact |
|---|---|---|---|
| Accuracy, reformat-off | … (Wilson CI) | … | … |
| Accuracy, reformat-on | … (Wilson CI) | … | … |
| Reformat delta | … | … | … |
| Format-compliance rate | … | … | … |
| Coverage (expressible) | n/a | n/a | … % (§5 K4) |
| Tokens per completed task | baseline | … | … |
| Bytes disclosed per request | … | … | … |
| Exposure vector | (S, L, I) | (S, L, I) | (S, L, I) |

### 9.2 Paired comparisons table

| Comparison | b (first right, second wrong) | c (first wrong, second right) | McNemar p | Paired difference (CI) | Min detectable at 80% power | Verdict |
|---|---|---|---|---|---|---|
| A vs C, reformat-on (**primary**) | | | | | | |
| A vs C, reformat-off | | | | | | |
| A vs B | | | | | | |
| B vs C | | | | | | |

### 9.3 Rules

| # | Rule |
|---|---|
| P1 | Every figure goes through `docs/metrics-baseline.md` first, with its workload, tokeniser or "bytes", N, model and pinned version, seed, date, container digest and toolchain commit. Other pages cite it; they do not restate it |
| P2 | The caveat travels with the number, everywhere the number appears |
| P3 | An unfavourable result is published with the same prominence as a favourable one |
| P4 | No figure from this experiment is published as a general claim about loke's correctness. It is a figure about DABench, on a named model, at a named date |
| P5 | The §1.1 framing — that arm C's data flow is not novel and that this measures cost — accompanies every publication of these results |

### 9.4 Pre-registration and freeze

| # | Rule |
|---|---|
| F1 | Pre-registered and frozen before the first scoring run: the arm definitions, the prompt templates and their diff, the model and version pins, decoding parameters and seeds, both stages of §6.4 with their digests, the primary comparison, the symmetry-gate margin, the item set, and the container digest |
| F2 | The pre-registration digest is recorded in the results file, and a mismatch voids the run (Z6) |
| F3 | The audit sample (N2) is drawn with a recorded seed before results are inspected |

---

## 10. Threats to validity

| # | Threat | Disposition |
|---|---|---|
| T1 | **The reformat step, worth up to 32 points** | Controlled: §6, two-stage published pipeline, frozen symmetric reformat, both conditions reported, pre-registered symmetry gate |
| T2 | **Arm C's structural parseability advantage** | Controlled: §6.4 stage 1 removes it at a published, checkable point; format-compliance rate reported per arm |
| T3 | **Annotation errors** | Mitigated: paired design cancels the shared confound; ~100-item audit published; raw and audited subsets reported (§7.5) |
| T4 | **N = 257 is small** | Stated: ±6 pp per arm; paired McNemar; minimum detectable effect published; sub-cells below 15 items descriptive only |
| T5 | **Arm C expressiveness** | Counted, not excluded: inexpressible items score incorrect, coverage reported by category with reasons (§5) |
| T6 | **Sandbox non-equivalence** | Stated: the harness's Python sandbox is not loke's execution path and no result speaks to executing code safely (§4.4) |
| T7 | **BIRD near saturation, R-VES not comparable** | Stated: §4.2 Q1–Q3; R-VES never a standalone headline |
| T8 | **Provider model drift** | Version pinned and recorded (VM1.2). A re-run on a different version is a different measurement and is labelled as one |
| T9 | **Generality** | A favourable DABench result does not establish generality. DABench is single-table CSV analysis; it says nothing about multi-table joins, long schemas, or production query workloads |
| T10 | **Arm A is a strong baseline where data fits, and impossible where it does not** | Context failures scored as arm A losses (E1), and the count published. Arm A's advantage is real on small data and shrinks as data grows, so the result is workload-dependent and is reported that way |
| T11 | **The experiment measures a cost, and costs are unwelcome** | Stated in §1.1 and repeated in §9.3 P3 and P5. Arm C is expected to lose ground on some question classes, and the design choices in §5 and §6 are deliberately the ones that make that visible rather than the ones that hide it |
| T12 | **Schema-only is standard elsewhere** | Acknowledged and cited as support, never denied (findings §10). It is why DABench is primary and the text-to-SQL suites are secondary |

---

## 11. Acceptance criteria

| # | Criterion |
|---|---|
| A1 | Three arms are implemented to §2 and §2.3, with arm A carrying the data untruncated and arms B and C carrying only the NC1.2 profile |
| A2 | The sentinel check runs on every arm B and arm C dispatch and a failure voids the run (E2, Z1) |
| A3 | Arm C validates and executes through the production contract and executor, with no benchmark-only relaxation (E3, E4) |
| A4 | All three arms use the same generation model and version pin, and arm C uses no local model for generation (§2.2) |
| A5 | The gold-executability invariant is asserted before any arm runs, the excluded set is published, and results are reported over all items and over the executable subset (§4.6) |
| A6 | The denominator is all 257 items for every arm. Inexpressible items score incorrect and coverage is reported by concept category and domain with per-item reasons (§5) |
| A7 | The two-stage output pipeline is implemented, stage 1 is deterministic and model-free, and both stages' code and digests are published (§6.4) |
| A8 | Stage 2 is applied to every arm's output including already-formatted ones, and cannot see the arm label (O4, O5) |
| A9 | Every results table carries reformat-on and reformat-off for all three arms, plus the per-arm reformat delta and format-compliance rate (O7, O8, O10) |
| A10 | The symmetry gate is pre-registered at 5 pp and enforced: if exceeded, the primary comparison is reported reformat-off and the discrepancy reported as a finding (O9) |
| A11 | At least 50 stage-2 outputs are hand-audited for substance change, and the audit is published (O11) |
| A12 | Comparisons are paired at the item and run index, tested with McNemar, with discordant counts `b` and `c` published (§7.2) |
| A13 | No comparison in any published output treats the arms as independent proportions |
| A14 | The minimum detectable difference at 80% power given observed discordance is published, and an unresolvable result is reported as unresolvable (M5) |
| A15 | The primary comparison is pre-registered and all secondary comparisons are Benjamini–Hochberg corrected, with cell N published on every breakdown (M6–M8) |
| A16 | A ~100-item stratified audit is published, and the primary comparison is reported on raw and audited subsets separately (N2, N3) |
| A17 | Spider 2.0-Snow is not used. BIRD figures carry the Q1–Q3 qualifications and R-VES never appears as a standalone headline |
| A18 | Tokens per completed task are reported per arm against arm A as the named baseline, with the tokeniser named, and arm C's total includes re-asks and returned results (§8) |
| A19 | Every figure is recorded through VM1.1's result sink with its full provenance and lands in `docs/metrics-baseline.md` before appearing anywhere else |
| A20 | The pre-registration digest exists, predates the first scoring run, and a mismatch voids the run |
| A21 | The §1.1 framing accompanies every publication of these results, and an unfavourable result is published with equal prominence |
