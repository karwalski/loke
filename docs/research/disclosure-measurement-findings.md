# Disclosure Measurement — Literature Findings

**Version:** 1.1
**Date:** 2026-09-19
**Status:** Research input. Feeds epics PL1, EM1, DA1, CB1, AD1, GA5 and NC1.

Part I covers disclosure measurement and linkage. **Part II covers benchmarks, enforcement evaluation
and competitive prior art, and is the more consequential of the two for positioning.**

This document records what the external literature already establishes about measuring disclosure to
external language models, and what loke would have to establish itself. It exists so that loke's
stories are specified against the current state of the field rather than against assumptions, and so
that loke does not claim as novel anything already published.

Items marked **unverified** could not be confirmed in the research pass and must be checked against
the primary source before being relied on.

---

## 1. Redaction is a weak defence — established, but narrower than usually cited

- **Staab, Vero, Balunović, Vechev, "Beyond Memorization: Violating Privacy Via Inference with LLMs,"
  ICLR 2024** (arXiv:2310.07298). Pretrained models infer personal attributes from free text at up to
  **85% top-1 / 95% top-3**, at roughly 1/100 the cost and 1/240 the time of human annotators.
  Concludes text anonymisation and model alignment are currently ineffective.
- **Staab et al., "Large Language Models are Advanced Anonymizers," ICLR 2025** (arXiv:2402.13846).
  Adversarial anonymisation across 13 models, beating industry anonymisers on utility and privacy.

**Important scope limit.** Both are **single-text, single-shot attribute inference**. The unit of
analysis is one document. Neither models a *sequence* of prompts, neither models a *stable surrogate
token*, and neither measures whether an adversary can decide that two texts concern the same person.
They establish "one text leaks attributes" — they do **not** establish "many texts link".

**Consequence for loke:** these are the correct citations for *redaction is not a guarantee*, and they
are sufficient to justify the no-custody architecture (epic NC1). They must **not** be cited as
evidence for a cross-prompt linkage claim.

---

## 2. Cross-prompt linkage from consistent surrogates — genuine gap, and closing fast

No peer-reviewed work isolates and measures cross-prompt or cross-session linkage attributable to
consistent surrogate reuse. But the surrounding space filled substantially during 2026, and three
works now border the gap on three sides:

- **Ko, Jeong, Thakur, Kim, Jia, "From Weak Cues to Real Identities: Evaluating Inference-Driven
  De-Anonymization in LLM Agents," ICML 2026** (arXiv:2603.18382). Introduces **InferLink** and the
  **Linkage Success Rate (LSR)** metric. GPT-5 reaches **79.17% ± 4.97** at two auxiliary attributes
  and **99.00% ± 0.72** at eight, against a classical matching baseline of 56.0–60.2%. Claude 4.5
  shows LSR 0.70–0.80 under an *implicit* condition — silent linkage with no re-identification
  request. A privacy-aware prompt drives explicit-condition LSR to near zero but costs utility
  (Δ −0.05 to −0.54). **Explicitly does not evaluate consistent pseudonyms recurring across separate
  prompts or sessions**, and names harder linkage regimes as future work.
- **Jathanna, "SurrogateShield: Beyond Redaction for High-Utility, Privacy-Preserving LLM
  Interactions,"** arXiv:2606.29567 (June 2026, arXiv-only, no venue). **This is substantially loke's
  architecture, already published**: a client-side proxy, a three-stage detection cascade
  (regex → NER → context), 22 PII types plus k-anonymity-grounded quasi-identifier combinations,
  type-consistent locally-generated surrogates substituted before transmission and reversed on
  response, with mappings held in an AES-256-GCM-encrypted **per-conversation** store that never
  leaves the device. Reports 98.87% detection F1 on 1,124 queries, BERTScore 81.59% → 94.85%
  (+13.26 pp) for surrogates over placeholder redaction, and **zero** original values recovered by an
  LLM adversary in a 100-query adversarial trial versus 1.53% under placeholder redaction.
- **Panjwani, "CAMP: Cumulative Agentic Masking and Pruning for Privacy Protection in Multi-Turn LLM
  Conversations,"** arXiv:2604.16521 (April 2026, single-author arXiv preprint, no venue). Defines
  **Cumulative PII Exposure (CPE)** over a session-level entity registry plus an entity-type
  co-occurrence graph, arguing per-turn masking structurally cannot see combination risk. Evaluated
  on only four synthetic scenarios with hand-tuned thresholds. Weak work, but a **priority-date
  problem** for any "cumulative exposure metric" framing.

**Consequences for loke.**
1. loke may **not** claim that surrogates preserve utility better than redaction, nor that an LLM
   adversary cannot reverse surrogates. Both are SurrogateShield's published results.
2. loke may **not** present "consistent placeholders create a linkage channel" as a finding.
   Pfitzmann & Hansen (2010) define pseudonymity as trading anonymity for exactly this, and the
   practitioner tokenisation literature states it plainly. Only the **magnitude**, the
   **scoping-policy frontier**, and the **residual after a defence** are findings.
3. The per-session salting defence is not novel either — SurrogateShield already scopes per
   conversation.
4. What remains genuinely open is the **two-factor ablation**: surrogate *scoping policy* crossed
   with surrogate *style*, measured for linkage rather than for recovery. See §6.

---

## 3. Foundational citations for linkage

Use these rather than over-reaching on the LLM literature.

- **Fellegi & Sunter, "A Theory for Record Linkage," JASA 1969, 64(328):1183–1210.** The formal
  three-decision framework with m- and u-probabilities as log-likelihood match weights. Gives a
  principled scoring instrument and a classical baseline matcher.
- **Sweeney, "Simple Demographics Often Identify People Uniquely," CMU 2000.** 87% of the 1990 US
  population unique on {ZIP, gender, DOB}. Note the rebuttal — **Golle, WPES 2006** — the figure has
  been contested on 2000-census data, and a reviewer will expect that to be acknowledged.
- **de Montjoye et al., "Unique in the shopping mall," Science 2015, 347(6221).** Four spatiotemporal
  points re-identify 90% of 1.1M people over three months; transaction price raises risk ~22%.
  Contested in Science 2016 (Comment and Response).
- **Pfitzmann & Hansen, "A terminology for talking about privacy by data minimization" (v0.34, 2010).**
  The canonical vocabulary for pseudonymity and linkability, and the suggestion to quantify
  unlinkability via probabilities or entropies.
- **Article 29 Working Party Opinion 05/2014 (WP216), 10 April 2014.** The three-criteria test —
  singling out, linkability, inference — and the origin of linkability as a first-class regulatory
  risk category, explicitly about linking records across one or multiple databases.

### Legal position

**CJEU, EDPS v SRB, Case C-413/23 P, judgment 4 September 2025.** Personal-data status of
pseudonymised data is **relative and context-dependent**: the same dataset may be personal data for
the controller holding the re-identification key while not being personal data for a recipient without
reasonable means of identification. The Court declined a closed-list test, requiring case-by-case
assessment. *(Paragraph numbers 76, 77 and 86 are cited in secondary analysis — **unverified**
against the judgment text.)*

**This cuts against loke, and is the reason PL1 matters.** loke holds the mapping, so loke remains a
controller of personal data. The live question is whether the *provider* does — and persistent,
consistent surrogates push toward "yes", because an accumulating attribute space attached to a stable
token is precisely what supplies the recipient with reasonable means.

### Provider retention — the threat model, stated honestly

Default API retention is bounded (of the order of 30 days for abuse monitoring at major providers),
and zero-data-retention arrangements are available, reportedly with carve-outs. *(Specifics drawn from
secondary reporting — **unverified**; read the platform documentation directly, and expect it to
change.)*

So "the provider builds a permanent longitudinal profile" is **not supportable**. The defensible
framing is narrower and more interesting: *the account identifier already links prompts; consistent
surrogates additionally link the entities inside them, and that linkage survives even when the
account-level link does not — a shared account, a rotated key, an exported or leaked log.*

---

## 4. There is no accepted per-request exposure metric — but the composition slot is taken

- **Giomi, Boenisch, Wehmeyer, Tasnádi, "A Unified Framework for Quantifying Privacy Risk in Synthetic
  Data," PoPETs 2023(2)** (arXiv:2211.10459) — the **Anonymeter** framework. Operationalises the
  WP216 triad as three separately-measured risks — singling out, linkability, inference — each as a
  **control-corrected** attack success rate, so the reported quantity is an adversarial *advantage*
  over a baseline rather than a raw accuracy. *(The exact control-adjusted estimator and its
  confidence-interval treatment are **unverified** — the papers would not parse. Read directly; the
  estimator is load-bearing.)*
  **loke should adopt these three axes directly** rather than invent its own, inheriting both the
  legitimacy and the control-correction discipline.
- **Pilgram et al., "A consensus privacy metrics framework for synthetic data," Patterns 2025**
  (arXiv:2503.04980). A Delphi study across the field. Two binding findings: **similarity-based
  metrics fail to measure identity disclosure and their use is discouraged**, and every
  membership/attribute disclosure metric must state its threat model explicitly, because using a
  metric built for one threat model to report on another is misleading.
- **Alvim, Chatzikokolakis, Palamidessi, Smith, "Measuring Information Leakage using Generalized Gain
  Functions," CSF 2012**; book, **"The Science of Quantitative Information Flow," Springer 2020.**
  g-leakage is the right *theoretical* framing for why disclosure is adversary- and
  scenario-relative — and therefore why a single scalar implicitly fixes one gain function and hides
  that choice. Not computable exactly for an LLM prompt; use it to justify the metric's shape.
- **Dinur & Nissim, "Revealing Information while Preserving Privacy," PODS 2003**, and the US Census
  database-reconstruction line. The right precedent for cumulative releases reconstructing
  individuals. Wrong unit of analysis for a single request.
- **Differential privacy ε is a poor fit and should be said to be.** A prompt is a deterministic
  release with no noise mechanism; offering ε as the metric reads as a category error.

### Adjacent 2026 measurement work

- **Jazlan, Wang, Vekaria, Shafiq, "Tracking Conversations: Measuring Content and Identity Exposure on
  AI Chatbots,"** arXiv:2604.27438. Splits exposure into **content exposure** and **identity
  exposure** — a useful two-axis precedent, and evidence the threat surface extends beyond the model
  provider: 17 of 20 chatbots shared with at least one third party.
- **Zaman & Hoque, "Vulnerabilities in Personalization,"** arXiv:2609.14697 (13 Sep 2026). 179,057
  chats: 21.31% contained explicit health information, 3.62% high-to-extreme risk. Of 7,051 memory
  entries, **95.36% of memory updates occurred automatically without explicit user command**. A
  precedent for ordinal risk scoring, with rubric validation as its weak point.

---

## 5. The closest prior art, and where loke is actually differentiated

**Zhou et al., "Operationalizing Data Minimization for Privacy-Preserving LLM Prompting,"**
arXiv:2510.03662, reported accepted at **ICLR 2026** *(acceptance **unverified**)*.

- **Formalism.** A per-entity action space with an ordinal privacy order
  **RETAIN ≺ ABSTRACT ≺ REDACT**, maximising privacy subject to a utility floor, solved by a
  priority-queue tree search over the privacy-ordered transformation space. Deliberately **agnostic**
  to the concrete privacy and utility instantiations.
- **Metrics.** Privacy via a **pairwise comparator** (fine-tuned Qwen2.5-7B) at 71% agreement with
  human labels, 89% on high-consensus items. Utility via official task scorers, or a judge model for
  open-ended tasks.
- **Datasets.** ShareGPT, WildChat, CaseHOLD, MedQA, across nine response models.
- **Key results.** GPT-5 tolerates **85.7% REDACT** against **19.3%** for Qwen2.5-0.5B; GPT-4.1
  reaches 98.0% REDACT on closed-ended tasks. Models asked to predict the optimal minimisation
  directly do poorly, with an **abstraction-first bias causing oversharing**.
- **Adversarial validation worth copying verbatim.** Type-wise recovery: Name **90.3% → 0.0%** after
  masking; Geolocation **89.8% → 2.2%**. Span-wise recovery: **5.6–14.9% for ABSTRACT** versus
  **2.7–7.7% for REDACT**.

**Where it stops, and where loke differs.** Every point in that transformation lattice still **sends
data to a remote model**. There is no schema-only variant and no local execution of a returned
artifact. loke's no-custody path is *outside* the lattice — it is the redact-everything corner their
utility constraint would normally forbid, made feasible by **moving the computation rather than the
data**.

That is a genuine contribution **if and only if** loke demonstrates utility at a comparable operating
point on the same datasets. Anything less reads as "we redacted everything and lost the task".

---

## 6. If loke runs its own experiment: the design

For the linkage question (epic PL1), the design that is defensible:

**Attacker.** Honest-but-curious provider-side observer with the full stream of surrogate-bearing
prompts for an account over a window, no access to the local mapping, and optionally public auxiliary
data plus an LLM or web-search agent — which Ko et al. establish as the realistic attacker rather
than a classical matcher. Separate two goals: **same-entity linkage** (do two prompts concern the
same entity?) and **re-identification** (name it). The first is what loke's design affects; the second
is Staab and Ko territory where loke will not win a comparison.

**Arms** — a genuine ablation over scoping policy, holding detection, substitution style and task fixed:

| Arm | Policy |
|---|---|
| A | Persistent global mapping — same entity, same token, indefinitely *(treatment)* |
| B | Per-session mapping, fresh salt per session |
| C | Per-request mapping, fresh salt per request |
| D | No substitution — real values *(upper bound on attacker success)* |
| E | **Random re-pairing control** — the same attacker on pairs known not to share an entity |

Arm E is essential. Do not use 1/N analytically as the baseline: surrogate-type consistency leaks
structure and inflates the naive chance rate.

**Second factor.** Type-consistent realistic surrogates versus opaque tokens (`[PERSON_1]`).
Type-consistent surrogates are better for utility and plausibly worse for linkage, and that trade-off
is unmeasured. **This cell is the actually-novel one.**

**Metrics.** Control-corrected **linkage advantage** = LSR(arm) − LSR(arm E), with Wilson-score
confidence intervals; a Fellegi–Sunter-style operating curve reporting **TPR at fixed low FPR**, not
accuracy; and the **residual advantage under the defence** as the headline, because "we implemented
the fix and measured what remained" is the defensible shape.

**Sizing.** Roughly 1,000 attack trials per arm for a Wilson half-width near ±3 pp at rates around
0.5; about 390 pairs per arm to detect a 10 pp difference at 80% power, α=0.05. So ~1,000 pairs × 5
arms × 2 surrogate styles ≈ **10,000 attack trials**, over ≥200 distinct synthetic entities each
appearing in ≥5 prompts. Pre-register the attacker prompt and report per-attacker-model results,
since Ko et al. show the attacker model moves results by 20–40 pp.

**Cost of the defence, measured not assumed.** Loss of cross-session continuity (which is much of the
value of a persistent proxy), within-response coreference errors if scoping is too tight, and mapping
growth. Measure utility with instruments comparable to the published work. Note that Ko et al. already
buy near-zero LSR for −0.05 to −0.54 utility with a privacy-aware prompt, so a defence must beat that
frontier to be interesting.

---

## 7. Validating a metric rather than asserting one

For epic EM1. The order of persuasiveness:

1. **Dose-response on injected leakage.** Construct datasets with deliberately inserted disclosure of
   known magnitude and show the metric scales with the injected dose. This is the Anonymeter method,
   it is cheap, and it is the most convincing single piece of evidence.
2. **Correlation with attack success across configurations.** The unit of analysis must be
   *configurations* (arm × dataset × model × redaction level), not individual requests. **Spearman ρ**
   as the headline (or Kendall τ-b with many ties), with bootstrap confidence intervals. At least
   30–50 configurations before a correlation means anything.
3. **Two structurally different attacks.** Linkage/re-identification *and* attribute inference.
   Validating only against the attack the metric was designed around is circular.
4. **TPR at low FPR, not AUC.** **Carlini, Chien, Nasr, Song, Terzis, Tramèr, "Membership Inference
   Attacks From First Principles," IEEE S&P 2022** (arXiv:2112.03570) established that average-case
   metrics are the wrong instrument for a privacy breach, because one confident identification is a
   violation. Report log-scale ROC and TPR at 1% and 0.1% FPR. A metric can correlate well with AUC
   and not at all with the low-FPR regime that constitutes the actual breach.

**A vector, not a scalar.** Adopt Anonymeter's three axes. Reasons a reviewer will accept: g-leakage
is adversary-relative, so a scalar hides the gain function it fixes; Anonymeter's own precedent is
three separate risks; and Pilgram et al. require per-component threat models, which a scalar erases.
If a single number is needed for display, present it explicitly as a **lossy projection** of the
validated vector — and validate the vector.

**Components, with an honest read on each:**

| Component | Assessment |
|---|---|
| Bytes / tokens transmitted | Weakest. Near-zero construct validity — include only as the baseline to beat. A count-based proxy is a similarity-metric-class mistake unless validated. |
| Entity count and type disclosed | Solid; the field already uses it |
| **Quasi-identifier combination present** | **Strongest single component.** Directly grounded in Sweeney and WP216 singling-out |
| Field / column / schema names disclosed | Cheap and under-explored. Leaks structure, not individuals — deserves its own axis, not to be summed with entity counts |
| Cardinality / distributional information | Hardest to instrument honestly; where reconstruction risk lives |
| Any real values included | A **gate, not a summand** — such a request is categorically different |
| Linkability to prior requests | Ties §2 to §4; also the component most exposed to an under-validation objection |

**Skip membership inference against model weights** unless loke is fine-tuning. Prompts sent to a
frontier API are not training data under standard retention, so classical MIA is the wrong
instrument, and reaching for it looks like instrument-shopping. State that explicitly.

---

## 8. What loke must not claim

Collected, because each is a credibility risk:

1. That surrogates preserve utility better than redaction — SurrogateShield published it.
2. That an LLM adversary cannot reverse surrogates — same.
3. That consistent placeholders create a linkage channel, as a *finding* — it is a definition.
4. Staab et al. as evidence for linkage — it is single-text attribute inference.
5. A weighted-sum scalar exposure score with hand-chosen weights.
6. Bytes or tokens as a privacy measure other than as a strawman baseline.
7. That no exposure metric exists — three 2026 artifacts propose overlapping things and Anonymeter
   has held the composition slot since 2023. The narrower, defensible claim: *no exposure metric has
   been validated against measured attack success at the request level.*
8. That providers retain prompts indefinitely.
9. Any mixing of provider-side linkage, third-party analytics exposure and model memorisation into
   one number without separating their threat models.

## 9. Assessment

The linkage gap is real, narrow, and closing — April and June 2026 preprints moved into the
neighbourhood, and an ICML paper named the harder regime as future work, which others will have read
too. The measurement gap is the opposite shape: the *conceptual* slot is largely claimed, but the
*methodological* gap — validation rather than assertion — is open, less glamorous and more defensible.

For loke the priority order is therefore: implement the no-custody architecture (NC1), because §5
shows it is genuinely outside the closest prior art's design space; build the measurement substrate
(VM1) and disclosure accounting (DA1), because nothing can be claimed without them; fix the
placeholder collision defect (PL1.1), because it is a live bug rather than a research question; and
treat the scoping ablation and the metric validation as the research contributions, specified to the
standard in §6 and §7.

---

# Part II — Benchmarks, enforcement and competitive prior art

Added 2026-09-19 from a second research pass. This part is more consequential than Part I for
positioning, because it establishes that **loke's data flow is not novel** and locates where the
genuine contribution actually is.

## 10. The architecture is table stakes, not a contribution

**Schema-out / execute-locally is the default implementation of the entire text-to-SQL field.** BIRD,
Spider and Spider 2.0 all hand the model a schema and score by executing the returned SQL against a
database the model never saw. That is architecturally identical to loke's primary path.

It also ships commercially today:

| Product | Mechanism |
|---|---|
| **Vanna.AI** | RAG over the information schema; top-k schema chunks plus documentation and prior question/SQL pairs go into the prompt; the LLM returns SQL; Vanna executes it against the connected database. Credentials stay in your infrastructure |
| **WrenAI** | Same shape via a semantic layer and vector store retrieving the relevant schema slice |
| **Snowflake Cortex Analyst / Databricks Genie** | Warehouse-native: semantic model goes to the model, SQL executes inside the warehouse |

It is published as a named pattern ("the schema-driven LLM query pattern"), and **arXiv:2512.04852,
*Ask Safely: Privacy-Aware LLM Query Generation for Knowledge Graphs*** applies it to graphs with
almost exactly loke's privacy rationale — that the data may be sensitive while the schema is not.

**Worse for the strict version:** the field moved *away* from schema-only because it underperforms.
Sample rows and value retrieval are standard in competitive systems; adding first-few-rows to CREATE
TABLE statements is reported to raise Spider scores by around 6 points *(**unverified** — secondary
source; pin before relying on it)*. MaskSQL, which is far more permissive than loke in that it sends
*masked* values, still pays roughly **20 execution-accuracy points** on BIRD.

**Consequences.**
1. Do not position the data flow as novel. A reviewer retires that claim in one sentence.
2. Expect the no-custody arm to **lose** to a data-in-prompt baseline on some question classes. Plan
   the work around quantifying that cost credibly, not around proving it does not exist.
3. Do not claim "low leakage". **arXiv:2406.14545** (*Zero-Knowledge Schema Inference Attacks*,
   Findings of NAACL 2025) reconstructs table names from a deployed text-to-SQL system at **F1 up to
   0.99** against generative models and 0.78 against fine-tuned ones. Schemas encode business logic,
   regulatory scope and sometimes values in column names. Reformulate as **bounded and auditable**:
   O(schema) rather than O(data), declared, with the exact bytes reviewable.

## 11. The unaddressed hole: a returned query is a channel

A query is an information channel even when no row is transmitted. An adversary — or a compromised
model — that can shape queries and observe results across multiple turns can extract cell values a
piece at a time: a query-shaped oracle, including binary-search style extraction over N requests.

**No published benchmark tests this.** "The model never receives data" is therefore true at the byte
level and potentially false at the information level. If the enforcement layer does not bound it, this
is precisely the gap that sinks a security claim. It must be stated as an open problem and given a
story, not asserted away. Tracked in NC1 and AD1.

## 12. Where loke is genuinely differentiated

1. **Enforcement, not architecture.** Every commercial comparable is redact-and-forward, block-and-
   exclude, or detect-at-the-keyboard — see §14. The text-to-SQL products get the data flow right *by
   accident* and make **no security claim at all**: no threat model, no injection resistance, no
   artifact validation, no provenance. Being first to treat that data flow as a security control with
   a proof obligation and an audit trail is the real contribution.
2. **No proxy-level injection benchmark exists.** The closest work evaluates guardrail classifiers
   *inside* an agent harness; one paper uses a proxy as the *attacker*, not the enforcement point.
   This is a clean, publishable gap.
3. **The dominant patent does not read on loke.** See §15.
4. **The closest academic work leaves the runtime open.** arXiv:2510.03662 is an offline oracle with
   no enforcement, no adversary and no structured data — and its central finding argues *for* an
   architectural control: models are biased toward abstraction and **systematically overshare**, so a
   model-mediated minimisation decision cannot be trusted.

## 13. Benchmark selection, and the trap in it

**Primary: InfiAgent-DABench** (arXiv:2401.05507, ICML 2024, Apache-2.0). 257 closed-form questions
over 52 CSV files, 7 concept categories *and* 9 domains — the "7 categories" figure is the concept
axis, not the domain axis. Scoring is strict: a question counts only if **all** its sub-questions are
correct. Requires a Python execution sandbox (Docker or subprocess).

DABench is the right primary **because it is the only candidate where paste-the-data is the honest
status quo baseline.** On BIRD and Spider, schema-only is already the norm, so measuring it there
proves nothing.

> **The single largest internal-validity threat.** DABench's harness post-processes model output into
> its `@answer_name[value]` template using a separate reformat model. That reformat step is worth up
> to **32 accuracy points**: Mistral-7B-Instruct goes 6.23 → 38.67, Qwen-72B 44.75 → 59.92, GPT-4
> 72.76 → 78.99. That is larger than any plausible effect of the disclosure regime under test. If the
> treatment arm returns a structured spec (naturally parseable) and the baseline returns prose with an
> embedded answer, the experiment measures **format compliance** and calls it privacy-preserving
> correctness. The reformat step must be identical, frozen and applied symmetrically, and both
> reformat-on and reformat-off numbers must be reported.

**Statistical note.** 257 items gives roughly ±6 pp binomial confidence at 95%. Comparisons must be
**paired on identical items** with McNemar's test, not two independent proportions.

**Secondary: BIRD Mini-Dev** (500 items across SQLite/MySQL/PostgreSQL; CC BY-SA 4.0). Metrics are
**EX** (execution accuracy, set equality on returned rows) and **R-VES**, which has replaced raw VES
and is computed *only over queries that pass EX* — so R-VES is **not comparable across systems with
different EX** and must never be a standalone headline. BIRD is near saturation: leaderboard EX is
around 82 against reported human performance of 92.96, so a ±2 pp privacy cost sits inside leaderboard
churn.

**Avoid Spider 2.0-Snow.** The annotation-error audit below found a **62.8–66.1% error rate on Snow
specifically**, which makes scores above about 80 close to meaningless. Lite or DBT are defensible.
Spider 2.0 schemas "often contain over 1,000 columns", up to around 3,000 — *the frequently-quoted
"average 700–800 columns" is secondary-source only and should not be asserted.* Spider 2.0's relaxed
execution-accuracy semantics live in the evaluation code and are **not documented** on the official
site — read the evaluation suite before relying on them.

**Tertiary: DataSciBench** (arXiv:2502.13897; 222 effective prompts / 519 test cases; GPT-4o best API
at 64.51%).

### The corrected-benchmark critique — cite the right version

Two versions of this work exist and they disagree. **Cite the journal version as primary:** Jin, Choi,
Zhu, Kang (UIUC), *Pervasive Annotation Errors Break Text-to-SQL Benchmarks and Leaderboards*,
**arXiv:2601.08778 v3 = PVLDB Vol 19 No 5**, CC BY 4.0. It re-evaluates **16** open-source agents and
reports score changes of **−7% to 31%** and ranking changes of **−9 to +9** positions. The CIDR 2026
workshop precursor (*Text-to-SQL Benchmarks are Broken*) covers 5 systems and reports −3% to 31%.
Error rates: **BIRD Mini-Dev 52.8%**; Spider 2.0-Snow 62.8% (journal) or 66.1% (CIDR).

Rank-correlation evidence worth quoting: uncorrected versus full dev ranking gives Spearman
**rs = 0.85, p = 3.26e-5**; corrected versus full dev gives **rs = 0.32, p = 0.23** — not significant.

> **Correction to an earlier note in this project's planning:** the claim that CHESS rose from 62% to
> 81% after correction is **wrong**. The paper reports **67.3% → 76.3% (+9.0 pp)**. A secondary source
> claims it moved 7th → 1st; that rank change is **unverified**. Do not restate 62 → 81.

**The pre-emption loke should use is stronger and cheaper than the paper's own recommendation.**
Because loke's comparison is **within-benchmark and paired** — same question, same data, two disclosure
regimes — annotation errors are a *shared* confound that largely cancels in the difference. Say so
explicitly, then: report paired deltas rather than leaderboard-style absolutes; hand-audit a stratified
random sample of about 100 items and publish the audit; and report both raw and audited subsets. That
converts the objection into a methods contribution.

### Other candidates, one line each

| Benchmark | Size | Execution needed? |
|---|---|---|
| DS-1000 | 1,000 problems, 7 Python libraries | Yes |
| ARCADE | 1,082 problems / 136 notebooks / 106 datasets | Yes (fuzzy dataframe match) |
| TableBench | 3,681 tables, avg 16.7 rows × 6.7 cols | Optional (PoT/SCoT modes) |
| WikiTableQuestions | 4,344 questions | No |
| TabFact | 118,275 statements over 16,573 tables; 2,024-pair test slice | No |
| SpreadsheetBench | 912 instructions / 2,729 test cases | Yes (spreadsheet runtime) |
| SheetCopilot | 221 spreadsheet control tasks | Yes (live spreadsheet app) |

## 14. Injection and enforcement evaluation

**AgentDojo** (arXiv:2406.13352, NeurIPS 2024 D&B, latest v3 Nov 2024): **97 user tasks, 629 security
test cases**, four suites. Metrics **Benign Utility**, **Utility Under Attack**, **Attack Success
Rate**. It is now a **regression suite, not a discriminator** — use it for a floor, never as a headline.

**The methodological trap, with numbers.** A re-evaluation (AgentDyn, arXiv:2602.03117) on GPT-4o:

| Defence | Utility under attack | ASR |
|---|---|---|
| Prompt Sandwiching | 56.13% | 31.17% |
| Spotlighting | 52.24% | 27.61% |
| **Tool Filter** | **4.91%** | **4.22%** |

Tool Filter looks best on a security-only leaderboard while having destroyed the agent. Meta SecAlign,
state of the art on AgentDojo at ~1.9% ASR, rises to ~9% on AgentDyn — the AgentDojo figure is a
benchmark artefact.

**Mandatory for loke:** never report ASR without paired Utility-Under-Attack from the same run; define
a composite acceptance gate up front (for example, ASR ≤ X% *at* UuA ≥ 0.9 × Benign Utility); and
report **false-block rate on a clean benign corpus**, because over-refusal is the failure mode a
schema-enforcing proxy is most exposed to.

**Single-turn injection is saturated; multi-step and persistent attacks are where the signal is.**
**ClawTrojan** (arXiv:2605.31042, RUC-NLPIR, May 2026) reaches **95.5% ASR on a GPT-5.4-class local
agentic harness while existing single-turn injections produce near-zero ASR on the same model.** Its
shape is the one that matters for loke: the injection hides in a file or tool output, is **persisted
into workspace state**, and executes in a **later session** — no individual step is malicious.
**StepJack** (arXiv:2608.06477, 480 examples) shows multi-step raising ASR on 3 of 6 computer-use
agents by up to +31.2 pp, e.g. GPT-5.4-mini 41.7% → 72.9%.

Still-discriminative corpora to use, rather than AgentDojo alone: **ClawTrojan**, **StepJack**,
**AgentDyn** (60 tasks / 560 injection cases, tasks averaging 7.1 steps, 10 defences in 4 families
including real guardrail models), **Alizadeh et al.** (arXiv:2506.01055 — data-flow exfiltration
grafted onto AgentDojo; 15–50 pp utility drop, average ASR ~20%; models resist leaking passwords but
readily leak other personal data — **the closest published methodology to loke's exfiltration
evaluation, to extend rather than reinvent**), **ToolPrivacyBench** (arXiv:2606.28061 — purpose-bound
disclosure, with a ready-made over-disclosure metric), and **Adaptive Evaluation of Out-of-Band
Defenses** (arXiv:2606.26479 — the methodological standard a proxy will be judged against; read it
before designing the harness).

Also: **Agent Security Bench** (arXiv:2410.02644, ICLR 2025) — 16 attack types × 11 defences × 10
scenarios, highest average ASR **84.3%**. **InjecAgent** — 1,054 cases; GPT-4 vulnerable 24% baseline
rising to 47% with enhanced attack prompts. A 2026 taxonomy analysis (arXiv:2605.16282) finds these
suites disagree with one another, so **cross-benchmark ASR numbers are not commensurable** — pick two,
freeze versions, report both.

### Designing a proxy-specific corpus

Organise it around loke's **own invariants**, not around "did the agent misbehave":

- **I1** no data row value crosses the boundary outbound
- **I2** the returned artifact is well-formed in the permitted language, over the declared schema only
- **I3** executing the artifact touches only authorised data and opens no outbound channel
- **I4** state persisted by one request cannot alter the enforcement decision of a later one

Four attack families, each keyed to an invariant:

1. **Outbound disclosure (I1)** — injections in the *question* that induce the client to attach rows;
   schema field names that encode data (`col_ssn_078_05_1120`); requests for "sample values to
   disambiguate"; and **iterative oracles that extract a cell value over N requests through
   query-shaped channels alone**. This last class is the real hole in schema-only architectures and
   almost nobody tests it — see §11.
2. **Artifact abuse (I2/I3)** — returned code containing side-effecting constructs: `COPY TO`,
   `INTO OUTFILE`, UDF or extension loading, `ATTACH`, `requests.post`, `os.system`, DNS-resolving
   hostnames in string literals, `pd.read_csv('http://…')`. Include encoding and **parser-differential**
   variants: a differential between loke's validator and its executor is the classic proxy bug.
3. **Data-flow exfiltration** — the Alizadeh methodology; grade on what data reached the attacker, not
   on whether the model complied. Include exfiltration via error messages, timing and row counts.
4. **Persistence (I4)** — ClawTrojan-shaped: injections landing in cached schema descriptions, column
   comments, saved queries, semantic-layer metadata, few-shot examples or user memory, firing on a
   later request. **If loke caches schemas or learns from prior queries, this is the highest-severity
   untested class.**

Per case, record: invariant targeted, injection surface, turn count, adaptive versus static, and a
concrete ground-truth oracle. Every attack case needs a **paired benign twin** so over-refusal is
measured on the same distribution. Report a 4-tuple per configuration: Benign Utility, Utility Under
Attack, ASR, False-Block Rate. Add an **adaptive tier** — publish the enforcement rules, let a red team
optimise against them for a fixed budget, and report static and adaptive ASR separately. Static-only
ASR will not be believed.

### The enumerable bypass corpus — six classes, each with authority

Claiming unbypassability is not survivable. Claiming "enforced at N of 6, with these requiring endpoint
or managed-policy co-deployment" is.

1. **Default TLS-interception exemptions.** Vendors ship do-not-decrypt lists *enabled by default* and
   document that pinned and mutually-authenticated TLS cannot be inspected. **Test: does any LLM API
   endpoint fall in a default exemption category?**
2. **Certificate pinning in native apps and SDKs.** Vendor guidance for resigning failures is a
   do-not-decrypt rule — deliberate loss of visibility. Browser-facing pinning (HPKP, RFC 7469) was
   deprecated and removed from Chrome by v67, so the risk now concentrates in native clients.
3. **Split tunnelling.** A shipped product feature, including **URL-based split tunnelling as a browser
   extension**. **Test: can a user exclude an API host without admin rights?**
4. **Browser extensions** — both a bypass vector (requests originate outside an interposing agent's
   view) and, conversely, the only enforcement point that survives encrypted transport metadata.
   Related control: Chrome Enterprise `CACertificateManagementAllowed` governs whether a user can
   remove an interception root.
5. **Encrypted transport metadata — newest and most serious.** **RFC 9849, TLS Encrypted Client Hello,
   Standards Track, published March 2026**; OpenSSL shipped support 11 March 2026. SNI-based DLP rules
   fail **silently** against ECH-enabled destinations. Adjacent: QUIC/HTTP-3 and DoH (RFC 8484).
   *(Reported mitigation via managed browser policy is **unverified** — confirm the policy name.)*
6. **Direct-to-API egress with its own credentials.** The residual case, over pinned or ECH-protected
   TLS. **No vendor documents a reliable network-layer control**; every documented answer is
   non-network (endpoint agent, browser extension, managed policy, or provider-side key restriction).
   loke must include this case and state honestly that network enforcement alone does not cover it.

## 15. Patents

**US 12,554,888, "Privacy-preserving prompt engineering for generative artificial intelligence."**
Assignee **SAP SE**; filed 17 Nov 2023, granted 17 Feb 2026. Claim 1: receive prompt via UI → detect
sensitive data violating a security protocol → generate a modified prompt anonymising it → submit to
the LLM → receive a reply containing anonymised data → generate a modified reply that **de-anonymises**
→ present. That is textbook redact-and-forward with round-trip de-anonymisation, and it reads on
Presidio-style gateways, Nightfall, and MaskSQL's mapping step.

**It does not read on loke's primary path**, because there is no sensitive data in the prompt being
anonymised and no de-anonymisation of the reply — loke sends a schema and receives a query. That is a
genuine design-around **provided loke never adds value-masking to the question path.** The moment it
does, it lands inside the claim.
*(Inventor attribution is **unverified** — sources conflict between Laurent Gomez and
Hegde/C K/Venugopal. Resolve against the granted PDF before any freedom-to-operate work.)*

**US 12,556,533, "Protecting private information during large language module interactions."** Assignee
**Gen Digital**; filed 26 Mar 2024, granted 17 Feb 2026. Claim 1 covers sensitivity-scored
**provider routing** plus a **credential-decoupling relay** so the provider cannot link a prompt to the
user. Not redaction. Relevant only if loke does sensitivity-tiered routing or acts as a shared-credential
relay — note loke's router **does** route by sensitivity, so this one deserves a closer read.

**No patent found claiming schema-out/execute-locally** — but that is because it is well-known
published practice, not unclaimed white space. Novelty is likely barred by Ask Safely
(arXiv:2512.04852) and the schema-driven-query literature. Any IP strategy should target the
**enforcement** layer, not the data-flow shape.

## 16. Commercial comparables — none execute artifacts locally

| Product | Mechanism | Executes model output against unseen data? |
|---|---|---|
| LiteLLM | Routing, keys, budgets, fallbacks. **No built-in guardrails**; PII delegated to external services via hooks | No |
| Portkey | Guardrails run on Portkey's infrastructure before the model; deny/log/retry. Custom PII logic is Enterprise-gated | No |
| Cloudflare AI Gateway | Caching, rate limiting, retries, logging. **No native PII redaction or moderation** | No |
| Kong AI Gateway | Built-in PII sanitisation plus cloud guardrail integrations | No |
| Microsoft Purview DLP for M365 Copilot | Policy conditions on sensitive-information type or sensitivity label; actions **block prompt** or exclude labelled files from grounding | No — block-and-exclude, not even redact |
| Nightfall AI | POST the outgoing prompt to a scan endpoint, receive findings **plus a redacted payload**, forward the redacted prompt yourself | No — canonical redact-and-forward |
| Harmonic Security | Small models **at the point of typing**, in-browser, before submit | No |
| Prompt Security (SentinelOne, acquired Aug 2025) | Endpoint agent plus browser extension, DOM analysis, semantic DLP redacting before the prompt reaches the tool | No |

Group B — the ones that *do* share loke's data flow — are Vanna, WrenAI, Cortex Analyst and Genie
(§10). They make **no security claim**, which is exactly the space loke occupies.

## 17. Revised assessment

**The architecture is table stakes; the enforcement, the threat model and the measurement are the
product.** Lead with the proxy-specific invariant-keyed attack corpus (§14), the persistence and
data-flow classes in particular, and with the honest bypass enumeration (§14, six classes). Treat the
correctness benchmark as a **cost measurement loke is candid about**, not a novelty it is claiming —
and expect the no-custody arm to lose ground on some question classes.

Written the other way round, the engineering would be correct and the positioning would not survive
first contact with a reviewer or a competitor.

### Verification debt

These were not confirmed and must be checked before being relied on: the CHESS correction figures by
hand against the paper's tables; Spider 2.0's relaxed-EX definition from its evaluation suite; the
"+6 pp from sample rows" Spider result; per-category annotation-error counts; the inventor of
US 12,554,888; CyberSecEval per-category ASR ranges; AgentDojo's own per-defence table (the numbers in
§14 are AgentDyn's re-evaluation and must not be attributed to AgentDojo); the "adaptive attacks bypass
>90% of defences" and "78-study meta-analysis" claims; ToolPrivacyBench's case count; and the Chrome
ECH policy name.
