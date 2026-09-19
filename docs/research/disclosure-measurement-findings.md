# Disclosure Measurement — Literature Findings

**Version:** 1.0
**Date:** 2026-09-19
**Status:** Research input. Feeds epics PL1, EM1, DA1, CB1, AD1 and NC1.

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
