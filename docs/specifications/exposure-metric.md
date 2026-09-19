# Exposure Metric Specification

**Story:** EM1.1 — Specify the metric on established axes
**Status:** Draft
**Version:** 0.1.0
**Last updated:** 2026-09-19

---

## 1. Overview

loke's top-level claim is that it reduces what is disclosed. A claim of reduction requires a measure,
and the measure has to be one that would survive somebody trying to break it.

This specification defines that measure. It also defines, at equal length, how the measure will be
validated — because the defensible position is not that loke invented an exposure metric, but that
loke validated one against measured attack success, which nobody has done at the request level.

This specification defines:

- The three axes, adopted rather than invented, each as a control-corrected rate with its own threat
  model
- Why the measure is a vector and not a weighted-sum scalar
- The components, and which of them are summands, which is a gate, and which are baseline-only
- The inputs, which come entirely from the disclosure record
- The validation programme, in the order that makes it persuasive
- Why membership inference against model weights is the wrong instrument here
- What the metric cannot measure

EM1.1 specifies. **EM1.2 executes the validation.** Nothing here may be published as a validated
measure before EM1.2 has run, and §7.6 states what is publishable in the interim.

### 1.1 Design Alignment

- **Privacy is the foundation.** A metric that overstates protection is worse than no metric, because it
  licenses disclosure. Every default in this document resolves toward reporting more exposure, not less.
- **Warnings must be earned.** The metric is an instrument. It produces a vector; policy decides whether
  that vector warrants an intervention. A metric that fires constantly trains users to ignore it.
- **The user is the authority.** The metric informs a decision the user makes. It does not block.
- **Negative results are results.** If a component does not correlate with attack success, that is
  published — in `docs/metrics-baseline.md`, which requires it — and the component is demoted, not
  reweighted until it fits.

### 1.2 Dependencies

| Dependency | Story | Relationship |
|---|---|---|
| Disclosure accounting | DA1.1 | The metric's sole input. It must be computable from the disclosure record alone |
| Metric validation | EM1.2 | Executes §7 |
| Comparative measurement across arms | EM1.3 | Reports the vector for the three arms of CB1 |
| Scorecard surface | EM1.4 | The display projection of §8 |
| Limits statement | EM1.5 | Publishes §9 |
| Measurement substrate | VM1.1–VM1.5 | No numeric result can be recorded without it |
| Scoping ablation | PL1.4 | Supplies the linkability axis's attack results and its control arm |
| Adversarial corpora | AD1.5 | Supplies the second, structurally different attack |

### 1.3 Evidence base, and the claim this metric supports

`docs/research/disclosure-measurement-findings.md` §4 and §7 are binding on this document. Three
findings in particular are not negotiable here.

- **The composition slot is taken.** Anonymeter (Giomi, Boenisch, Wehmeyer, Tasnádi, PoPETs 2023(2),
  arXiv:2211.10459) has operationalised the WP216 triad as three separately-measured, control-corrected
  risks since 2023, and three 2026 artifacts propose overlapping schemes. loke must not claim that no
  exposure metric exists (findings §8 item 7).
- **The defensible claim is narrower.** *No exposure metric has been validated against measured attack
  success at the request level.* That is the claim this document is built to support, and the reason §7
  is as long as §4.
- **A scalar is forbidden** (findings §8 item 5). See §3.

---

## 2. The three axes

loke adopts the three axes already established for disclosure risk, rather than inventing a scheme.
They originate in Article 29 Working Party Opinion 05/2014 (WP216) as the three-criteria test and are
operationalised as separately-measured, control-corrected attack success rates by Anonymeter.

Adopting them inherits two things worth having: the legitimacy of a framework a regulator and a
reviewer already recognise, and the control-correction discipline that stops a raw accuracy being
reported as a risk.

| Axis | Question | Symbol |
|---|---|---|
| **Singling out** | Can the recipient isolate one individual or record from this disclosure? | `S` |
| **Linkability** | Can the recipient decide that two disclosures concern the same entity? | `L` |
| **Inference** | Can the recipient infer an attribute that was not disclosed? | `I` |

### 2.1 Each axis carries its own threat model

Pilgram et al. (*A consensus privacy metrics framework for synthetic data*, Patterns 2025,
arXiv:2503.04980) is a Delphi study across the field and it is binding on this point: every
membership or attribute disclosure metric must state its threat model explicitly, because using a
metric built for one threat model to report on another is misleading.

Mixing provider-side linkage, third-party analytics exposure and model memorisation into one number
without separating their threat models is the specific error findings §8 item 9 forbids. Each axis
therefore names its adversary, its knowledge, its goal and its control.

| | `S` — singling out | `L` — linkability | `I` — inference |
|---|---|---|---|
| **Adversary** | Honest-but-curious recipient of one request | Provider-side observer over one account's stream for a window | Recipient of one request, using a large model |
| **Knowledge** | The dispatched payload; public auxiliary data | The stream of payloads; public auxiliary data; a web-search or LLM agent. **No access to the local mapping** | The dispatched payload; the model's own pretrained knowledge |
| **Goal** | Isolate a single record | Decide whether two payloads concern the same entity | Infer an undisclosed attribute |
| **Not the goal** | Naming the individual | Naming the entity — that is re-identification, and it is Staab and Ko territory where loke will not win a comparison | Isolating a record |
| **Control arm** | Payloads with the quasi-identifier combination removed, task held fixed | **Random re-pairing**: the same attacker on pairs known not to share an entity | Attribute prediction with the relevant field withheld from the payload |
| **Reported as** | Advantage over control, Wilson interval | Advantage over control, Wilson interval | Advantage over control, Wilson interval |

Two notes on `L` that keep it honest:

- The account identifier already links prompts. The quantity `L` measures is therefore the
  **additional** linkage of the *entities inside* the prompts — linkage that survives when the
  account-level link does not: a shared account, a rotated key, an exported or leaked log.
- The **random re-pairing control is mandatory** and 1/N must not be used as an analytic baseline.
  Type-consistent surrogates leak structure, which inflates the naive chance rate. This is finding §6's
  arm E and it is not optional.

### 2.2 Control-corrected rates

Each axis is reported as an advantage, not a raw accuracy:

```
A_axis = success(treatment) − success(control)
```

with a Wilson-score confidence interval on each term and a bootstrap interval on the difference.

> **Verification debt.** Findings §4 records that Anonymeter's exact control-adjusted estimator and its
> confidence-interval treatment could not be confirmed in the research pass, and states that the
> estimator is load-bearing. The formula above is the general shape, not Anonymeter's estimator. Before
> any implementation, the primary source is read and the estimator implemented as published, or a
> deliberate documented departure is recorded. Coding the general shape and citing Anonymeter for it
> would be a misattribution, and the estimator affects every number the metric produces.

### 2.3 Why these three and not a theory of leakage

g-leakage (Alvim, Chatzikokolakis, Palamidessi, Smith, CSF 2012; *The Science of Quantitative
Information Flow*, Springer 2020) is the correct theoretical framing for *why* disclosure is adversary-
and scenario-relative. It is not exactly computable for an LLM prompt. Its role here is to justify the
metric's shape — specifically §3 — and not to be the metric.

Differential privacy ε is a poor fit and this document says so plainly, per findings §4: a prompt is a
deterministic release with no noise mechanism, so offering ε as the metric would be a category error.

The Dinur–Nissim database-reconstruction line (PODS 2003) and the US Census work are the right
precedent for cumulative releases reconstructing individuals, and the wrong unit of analysis for a
single request. They belong to the cumulative, session-level problem of finding §11, which §9.2 places
outside this metric.

---

## 3. A vector, never a scalar

> **EM-VECTOR.** The metric is the ordered triple `(A_S, A_L, A_I)`, each with its interval, its threat
> model and its validation status. There is no weighted-sum scalar exposure score with hand-chosen
> weights. Findings §8 item 5.

Three independent reasons, which is why this holds even if one of them is disputed:

1. **A scalar fixes an adversary model and hides that it did so.** g-leakage establishes that leakage is
   relative to a gain function. Weights are a gain function. Choosing weights by hand and not reporting
   them as a choice presents one adversary's view as the measurement.
2. **The precedent is three separate risks.** Anonymeter measures three and reports three. Collapsing
   them discards the structure that makes the framework recognisable.
3. **Per-component threat models are required.** Pilgram et al. require them, and a scalar erases them —
   it is not possible to state the threat model of a sum whose terms have different ones.

### 3.1 Pairs of vectors are compared componentwise

A reduction claim is three claims. `(0.12, 0.31, 0.44) → (0.02, 0.05, 0.41)` is a reduction on `S` and
`L` and approximately no change on `I`, and it is reported that way. It is not reported as "68%
reduction in exposure".

If one component worsens while others improve, that is reported. A scalar would hide it, which is the
practical reason the rule exists rather than the theoretical one.

---

## 4. Components

Components are the observable features of a disclosure that feed the axes. This table follows findings
§7 and adds the disposition that makes it implementable.

| Component | Disposition | Feeds | Assessment |
|---|---|---|---|
| **Quasi-identifier combination present** | **Summand — the strongest single component** | `S` primarily, `L` secondarily | Directly grounded in Sweeney (*Simple Demographics Often Identify People Uniquely*, CMU 2000 — 87% of the 1990 US population unique on {ZIP, gender, DOB}) and in WP216's singling-out criterion. The Sweeney figure has been contested on 2000-census data by Golle (WPES 2006) and that must be acknowledged wherever it is cited |
| Entity count and type disclosed | Summand | `S`, `I` | Solid; the field already uses it |
| Field / column / schema names disclosed | **Its own component, on its own axis position** | `S` structural sub-score | Cheap and under-explored. It leaks *structure*, not individuals, and **must not be summed with entity counts**. Not harmless: table names have been reconstructed from a deployed text-to-SQL system at F1 up to 0.99 (findings §10) |
| Cardinality / distributional information | Summand, **status: unvalidated** | `S`, `I` | Hardest to instrument honestly, and where reconstruction risk lives. Reported with its status until EM1.2 covers it. The disclosure record currently carries only a boolean (DA1.1 §10 U3) |
| Linkability to prior requests | Summand | `L` | Ties findings §2 to §4, and is the component most exposed to an under-validation objection, so it is the one most needing §7 |
| **Any real value included** | **GATE — not a summand** | All axes | §4.1 |
| Bytes / tokens transmitted | **Baseline only — not a component** | None | §4.2 |

### 4.1 The gate

`real_values_included` from the disclosure record is a gate, not a number added to an axis.

| # | Rule |
|---|---|
| G1 | When the gate is true, the request is **categorically different** and is labelled with its custody class (`redacted-data` or `raw`) wherever its vector appears |
| G2 | A gated request's vector is **not comparable** on these axes to a no-custody request's vector. Comparisons are made within a custody class, or the class difference is reported as the finding |
| G3 | The gate contributes no number to any axis. It does not become a large summand, a multiplier, or a penalty term. Turning a categorical difference into a quantity is what allows "a bit of raw data" to be traded against "a lot of schema", which is not a trade the axes support |
| G4 | The gate cannot be cleared by transformation. `redacted-data` is gated. Redaction reduces disclosure; it does not prevent identification, and the peer-reviewed position is that inference from surrounding context defeats it (Staab et al., ICLR 2024, arXiv:2310.07298 — attribute inference at up to 85% top-1 / 95% top-3; ICLR 2025, arXiv:2402.13846) |

### 4.2 Bytes and tokens are the strawman baseline

Bytes and tokens are the baseline the metric has to beat, not a privacy measure (findings §8 item 6).

| # | Rule |
|---|---|
| B1 | Bytes and tokens are reported as a **named baseline arm** in the validation of §7, against which the three axes must show better correlation with attack success |
| B2 | They are never a component of any axis and never summed with anything in §4 |
| B3 | They are never the headline of a privacy claim. They are exact, cheap and quotable, which is what makes the rule necessary |
| B4 | A count-based proxy for privacy is a similarity-metric-class mistake unless validated. The consensus framework discourages similarity-based metrics for identity disclosure outright, and a byte count is in that family |

The one thing bytes are good for: an exact, checkable, per-request statement of volume, which is what
`docs/specifications/disclosure-accounting.md` §8.1 reports. That is a volume claim, not a privacy
claim, and the two are kept apart.

---

## 5. Inputs

| # | Rule |
|---|---|
| I1 | The metric is computed **from the disclosure record alone** (DA1.1). It never reads prompt content, and never reads a data value |
| I2 | A component whose input field is null is reported as **not measured**, not as zero. Null is not favourable evidence |
| I3 | The record's own caveats propagate. Entity counts are unreliable until PL1.1 is fixed, so any axis consuming them carries that caveat (DA1.1 §5.7 C4) |

| Component | Record fields |
|---|---|
| QI combination present | `qi_combination_present`, `qi_combination_fields` |
| Entity count and type | `entity_types`, `entities_total`, `detection_layers` |
| Field / schema names | `fields_disclosed`, `fields_disclosed_count`, `field_types_disclosed`, `datasets_disclosed` |
| Cardinality / distributional | `cardinality_disclosed`, `row_count_disclosed`, `aggregates_included` |
| Linkability to prior requests | `session_id`, `session_dispatch_ordinal`, `surrogate_style`, `surrogate_scope`, `fields_disclosed` overlap across the session |
| Gate | `real_values_included`, `sample_values_included`, `custody`, `custody_check` |
| Baseline | `bytes_body`, `bytes_schema_profile`, `tokens_estimated`, `tokeniser_id` |

That the metric is computable from the record alone is a design constraint, not an observation: it means
the metric can be recomputed retrospectively over stored records when its definition changes, and it
means computing the metric is never itself a reason to retain prompt content.

---

## 6. Session-level quantities are out of scope for the per-request vector

The vector is per request. Three quantities are cumulative and are reported **alongside** it, never
folded into it:

| Quantity | Source | Why separate |
|---|---|---|
| `session_cells_returned_cumulative` | DA1.1 §5.5 | The query-shaped channel of findings §11 is a session-level phenomenon. A per-request vector cannot see it |
| `predicate_repeat_count` | DA1.1 §5.5 | The signal of an iterative value-probing sequence |
| Session linkage advantage | PL1.4 | `A_L` per request is a per-request proxy; the measured linkage advantage over a session is the real quantity, and it comes from the five-arm ablation |

Folding a cumulative quantity into a per-request score is the Dinur–Nissim unit-of-analysis error, and
it would make the per-request vector uninterpretable.

---

## 7. Validation

A metric that is asserted is worth nothing. This is the order of persuasiveness from findings §7, and
the order is itself part of the specification: step 1 is cheap and convincing, and doing step 2 first
produces a correlation with nothing to anchor it.

### 7.1 Step 1 — dose-response on injected disclosure

Construct datasets with deliberately inserted disclosure of known magnitude and show that the metric
scales with the injected dose.

| # | Rule |
|---|---|
| D1 | The dose is the independent variable and is known by construction: number of quasi-identifier fields present; number of entities; number of real values; presence and size of distributional information |
| D2 | At least five dose levels per component, including a zero dose |
| D3 | Each axis is plotted against dose with its interval. Monotonicity is reported, not assumed. A component that does not move with its own injected dose has failed at the first and cheapest hurdle and is demoted immediately |
| D4 | The task is held fixed across dose levels, so dose is the only thing that varies |
| D5 | This is the Anonymeter method, it is cheap, and it is the most convincing single piece of evidence. It runs first and it runs before any attack correlation |

### 7.2 Step 2 — correlation with attack success across configurations

| # | Rule |
|---|---|
| R1 | **The unit of analysis is a configuration**, not a request. A configuration is (arm × dataset × model × redaction level) |
| R2 | **At least 30–50 configurations** before a correlation means anything. A correlation over fewer is not reported as a correlation |
| R3 | **Spearman ρ** is the headline. Kendall τ-b where ties are heavy, which they will be on boolean components |
| R4 | Bootstrap confidence intervals on every coefficient |
| R5 | Correlating over individual requests inflates N by orders of magnitude and measures within-configuration noise. It is not permitted, and if it is reported anywhere it is labelled as a diagnostic, not a result |
| R6 | The bytes-and-tokens baseline (§4.2 B1) is correlated over the same configurations. The three axes must beat it. If they do not, that is the result |

### 7.3 Step 3 — two structurally different attacks

Validating only against the attack the metric was designed around is circular.

| Attack | Source | Targets |
|---|---|---|
| Linkage / re-identification | PL1.4's five-arm ablation, with the random re-pairing control. Attacker per findings §6: honest-but-curious provider-side observer with the account's stream, no local mapping, optionally public auxiliary data plus an LLM or web-search agent | `L`, and `S` secondarily |
| Attribute inference | A Staab-style single-text attribute-inference attack, and the type-wise and span-wise recovery audits from arXiv:2510.03662, reused rather than reinvented so the numbers are comparable to a published baseline | `I`, and `S` secondarily |

| # | Rule |
|---|---|
| T1 | Both attacks run on the same configurations, and each axis's correlation is reported against both |
| T2 | The attacker model is pre-registered along with its prompt, and results are reported per attacker model. Ko et al. (ICML 2026, arXiv:2603.18382) show the attacker model moves linkage results by 20–40 pp, so a single-attacker result is not a result |
| T3 | An axis that correlates with the attack it was designed around and not with the other is reported as such. That is the circularity check doing its job |

### 7.4 Step 4 — TPR at low FPR, not AUC

| # | Rule |
|---|---|
| P1 | Reported as **true-positive rate at fixed low false-positive rate on a log-scale ROC** — at 1% and 0.1% FPR |
| P2 | **AUC is not the headline.** Carlini, Chien, Nasr, Song, Terzis, Tramèr, *Membership Inference Attacks From First Principles*, IEEE S&P 2022 (arXiv:2112.03570) established that average-case metrics are the wrong instrument for a privacy breach: one confident identification is a violation |
| P3 | A metric can correlate well with AUC and not at all with the low-FPR regime that constitutes the actual breach. Both are computed; the low-FPR figure is the one published as the result |
| P4 | Where the low-FPR regime has too few positives to estimate, that is stated with the count, rather than substituted with the next-best-estimable figure |

### 7.5 Discipline

| # | Rule |
|---|---|
| V1 | **Pre-registration.** The component set, the axis assignments, the attacks, the attacker models and prompts, the configuration list, and the primary statistic are frozen before the first validation run, with a recorded digest |
| V2 | **No post-hoc reweighting.** A component that does not correlate is demoted to unvalidated and reported as such. It is not reweighted, rescaled or recombined until the correlation appears. There are no weights to tune, by §3 |
| V3 | **Negative results are published.** If the metric does not correlate, that is the finding, and it goes in `docs/metrics-baseline.md`, which requires negative results |
| V4 | **Repetition and intervals** per VM1.3: N runs per configuration with the first discarded as warm-up, and BCa bootstrap intervals. No single-run number is published |
| V5 | **Every published figure** carries its workload, its N, its model and pinned version, its seed, its date and the toolchain commit, and goes through `docs/metrics-baseline.md` first |

### 7.6 What is publishable before validation completes

| Status | May be said |
|---|---|
| Specified | "loke defines exposure on the three established axes of singling out, linkability and inference, each as a control-corrected rate." A definition, presented as a definition |
| Dose-response passed | "Component X scales with injected disclosure of known magnitude over five dose levels." With the figures |
| Fully validated | "Component X correlates with attack success across N configurations at Spearman ρ = …, with TPR at 1% FPR of …, against two structurally different attacks" |

| # | Rule |
|---|---|
| W1 | An unvalidated component is labelled unvalidated at every point of display, including in the product surface, not only in the documents |
| W2 | The vector is not published as a measurement of privacy until at least the dose-response step has passed for every component it contains |
| W3 | "loke measures exposure" is not said while the measure is unvalidated. "loke defines and records exposure" is accurate and is said instead |

---

## 8. The display projection

A product surface sometimes needs one number. That is a display requirement, not a measurement one.

| # | Rule |
|---|---|
| Y1 | A single display number is an **explicitly lossy projection of the validated vector**, labelled as such at the point of display and not only in a tooltip |
| Y2 | The projection function is published, versioned, and stated to be a presentation choice, not a measurement |
| Y3 | The projection may be computed only over components that are validated. An unvalidated component does not enter the number that a user reads as a measurement |
| Y4 | The vector is reachable from the projection in one interaction. A user who wants the three axes and their intervals can see them |
| Y5 | The projection is never the figure cited in a claim. Claims cite the vector |
| Y6 | Exposure belongs in the ambient scorecard alongside privacy, cost, compliance and local ratio (`docs/design-principles.md`), not in a warning. A measure that presents as an alarm is a measure users learn to dismiss |

The default projection: the maximum component advantage, plus the custody class, plus the count of
unvalidated components. Maximum rather than mean, because the axes measure different breaches and the
worst is the one that matters; and it is chosen to be visibly crude, so that nobody mistakes it for the
measurement.

---

## 9. What this metric cannot measure

Published alongside the metric (EM1.5), not buried. The metric bounds disclosure, not consequence.

### 9.1 Out of scope by construction

| # | Limit |
|---|---|
| N1 | **Inference from context.** A recipient can infer attributes from the surrounding text and from its own pretrained knowledge. The `I` axis measures inference from *this disclosure*; it does not measure what a model already knows or can deduce from a conversation the metric never saw |
| N2 | **Provider-side retention and training.** What the provider stores, for how long, and whether it trains on it, is not observable from the client. `retention_class` in the disclosure record defaults to `unknown` and must not be filled from assumption. loke must not claim providers retain prompts indefinitely (findings §8 item 8) |
| N3 | **Cross-account correlation.** The `L` threat model is one account's stream. Linkage performed by correlating across accounts, or against data the provider holds from other sources, is outside it |
| N4 | **Consequence.** Harm depends on who the recipient is, what they do, and what else they hold. The metric measures disclosure |

### 9.2 Known open, and tracked

| # | Limit |
|---|---|
| N5 | **The query-shaped channel** (findings §11, NC1.10). Cumulative, session-level, and not captured by a per-request vector. Reported beside the vector per §6. No published benchmark tests it |
| N6 | **Cardinality and distributional disclosure** is a component with the weakest instrumentation, currently a boolean in the record |
| N7 | **Third-party exposure beyond the provider.** The threat surface extends past the model provider — 17 of 20 chatbots were found to share with at least one third party (Jazlan, Wang, Vekaria, Shafiq, arXiv:2604.27438). loke's axes are defined against the provider as recipient. Third-party onward sharing is a different threat model and is not mixed into these numbers (findings §8 item 9) |
| N8 | **Bypass.** loke is not a chokepoint. Traffic not routed through it is not measured at all, and six classes of bypass are enumerated and testable (AD1.6). An exposure figure describes measured traffic only, and says so |

### 9.3 Membership inference against model weights is the wrong instrument

Stated explicitly, because reaching for it is a recognisable error and it is worth being on record
about (findings §7).

| # | Reason |
|---|---|
| M1 | **Wrong threat model.** Classical MIA asks whether a particular record was in a model's *training set*. Prompts sent to a frontier API are not training data under standard retention. The question MIA answers is not the question loke is asking |
| M2 | **It would be misleading to report.** Pilgram et al. are explicit that using a metric built for one threat model to report on another is misleading. MIA against provider weights would report on memorisation while loke's exposure is about what crossed a boundary |
| M3 | **It looks like instrument-shopping.** Borrowing a well-known privacy metric because it is well-known, rather than because it measures the quantity at issue, is transparent to a reader and undermines the rest |
| M4 | **The useful part is already adopted.** The genuinely portable contribution of that literature is Carlini et al.'s methodological result — low-FPR reporting rather than average-case — and §7.4 adopts it |
| M5 | **The one exception.** If loke ever fine-tunes a model on user data, MIA becomes the right instrument **for that model**, and is scoped to it. It never becomes an instrument for measuring disclosure to a third-party API |

---

## 10. Claims discipline

The claims this metric supports, and the ones it does not. Each forbidden item is from findings §8.

| Claim | Permitted? |
|---|---|
| "Exposure is defined on three established axes, each a control-corrected rate, each with its threat model" | Yes — a definition |
| "No exposure metric has been validated against measured attack success at the request level" | Yes — this is the defensible framing |
| "Arm C's exposure vector is lower than arm A's on components S1 and L1, on workload W, N = n" | Yes, once validated and reported componentwise against a named baseline |
| "loke reduces exposure by X%" | **No.** A scalar reduction over a vector measure, and an absolute rather than a comparison to a named baseline arm |
| "No exposure metric exists" | **No** — item 7. Anonymeter has held the composition slot since 2023 |
| A weighted-sum scalar score with hand-chosen weights | **No** — item 5 |
| Bytes or tokens as a privacy measure | **No** — item 6. Baseline only |
| "Surrogates preserve utility better than redaction" | **No** — item 1. Published by SurrogateShield (arXiv:2606.29567) |
| "An LLM adversary cannot reverse surrogates" | **No** — item 2. Same |
| "Consistent placeholders create a linkage channel", as a finding | **No** — item 3. It is a definition (Pfitzmann & Hansen, 2010). Only the magnitude, the scoping frontier and the residual are findings |
| Staab et al. cited as evidence for linkage | **No** — item 4. It is single-text attribute inference |
| "Providers retain prompts indefinitely" | **No** — item 8 |
| One number mixing provider-side linkage, third-party exposure and memorisation | **No** — item 9 |

---

## 11. Acceptance criteria

| # | Criterion |
|---|---|
| A1 | The metric is implemented as an ordered triple with an interval and a validation status per axis. No code path produces a scalar exposure score except the §8 projection, and that path is labelled lossy at its output |
| A2 | Each axis carries a machine-readable threat model — adversary, knowledge, goal, control arm — that travels with every reported value |
| A3 | Anonymeter's control-corrected estimator is read from the primary source and either implemented as published or departed from with the departure documented. The verification debt in §2.2 is closed before any figure is published |
| A4 | Every axis is computed as an advantage over a named control arm. No raw success rate is reported as a risk |
| A5 | The linkability axis's control is random re-pairing. No code path uses 1/N as an analytic baseline |
| A6 | `real_values_included` acts as a gate: it contributes to no axis, forces the custody label onto the vector, and marks cross-class comparisons as non-comparable |
| A7 | Bytes and tokens appear only as the named baseline arm in validation, and no axis consumes them |
| A8 | The metric is computable from the disclosure record alone, demonstrated by recomputing historical vectors from stored records with no access to prompt content |
| A9 | A null input field yields "not measured", never zero, and the distinction survives aggregation |
| A10 | Dose-response passes for every summand component over at least five dose levels including zero, with monotonicity reported. A component that fails is demoted and labelled |
| A11 | Correlation is computed over at least 30 configurations, unit = configuration, with Spearman ρ and bootstrap intervals. A per-request correlation is not published as a result |
| A12 | Both attacks — linkage and attribute inference — are run over the same configurations, results reported per attacker model |
| A13 | Results are reported as TPR at 1% and 0.1% FPR on a log ROC. AUC, if reported, is secondary and labelled |
| A14 | The pre-registration digest exists and predates the first validation run |
| A15 | No component's weight, scale or axis assignment changed after a validation run. Verified against the pre-registration |
| A16 | A non-correlating component is published as non-correlating in `docs/metrics-baseline.md` |
| A17 | Unvalidated components are labelled unvalidated in the product surface, not only in the documents |
| A18 | The limits of §9, including §9.3 on membership inference, are published with the metric (EM1.5) |
| A19 | No surface presents the display projection as a measurement, and the vector is one interaction away |
