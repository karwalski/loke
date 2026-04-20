# loke: A Local-First Privacy-Preserving Intermediary for Large Language Model Interaction

## Research Proposal — Detailed Outline

**Working title:** "loke: Privacy-Preserving Token Optimisation and Intelligent Routing Through a Local-First AI Intermediary"

**Alternative titles:**
- "Local-First, Send-Less: An Intermediary Architecture for Private, Efficient, and Controllable LLM Interaction"
- "Defence in Depth for Everyday AI: Combining PII Detection, Token Compression, and Intelligent Routing in a Desktop Intermediary"

---

## 1. Abstract (250 words)

**Content summary:** The abstract will present loke as a novel desktop intermediary architecture that interposes between users and cloud-hosted large language models. It addresses three converging problems: (1) uncontrolled transmission of personally identifiable information and proprietary data to cloud LLMs, (2) excessive token consumption from unoptimised prompts and data serialisation, and (3) lack of user visibility into what data leaves their device. loke combines a multi-layer PII detection pipeline with reversible anonymisation, a layered token optimisation stack (TOON format conversion, LLMLingua-2 prompt compression, and semantic caching), and sensitivity-aware routing between local and cloud models. We present empirical benchmarks demonstrating token savings of 60-80% across representative workloads, PII detection accuracy exceeding 98% F1-score through multi-layer defence-in-depth, and routing decisions that preserve task quality while reducing cloud API calls by 40-65%. We propose a user study protocol examining the transparency/control trade-offs inherent in intermediary-based privacy tools. The system is contextualised against the regulatory landscape (EU AI Act high-risk provisions, August 2026) and the growing cultural demand for local-first AI sovereignty, as articulated by figures including Vitalik Buterin. We argue that the intermediary pattern — sitting between user and LLM rather than replacing either — represents an underexplored and practically important point in the design space.

---

## 2. Introduction (2,500 words)

### 2.1 The Privacy Problem in Everyday LLM Use

**Content summary:** Open with the concrete threat. The UC Davis study (August 2025) demonstrated that AI browser extensions — Merlin, MaxAI, Monica AI, and others — routinely exfiltrate sensitive data from web pages, including Social Security Numbers from IRS forms. This is not an edge case; it reflects the fundamental architecture of cloud-dependent AI tools. Users paste proprietary code into ChatGPT, upload client documents to Claude, and share financial data with Gemini — often unaware that this data is transmitted, stored, and potentially used for training. The scale of the problem is measurable: enterprise surveys consistently report that 30-60% of employees use unsanctioned AI tools with corporate data.

### 2.2 The Token Cost Problem

**Content summary:** LLM interaction is expensive and wasteful. Users transmit entire documents when summaries would suffice, send JSON where compact formats would save 30-60% of tokens, and re-send semantically identical prompts that could be served from cache. The economic burden falls disproportionately on individual users and small organisations who lack the infrastructure for enterprise-grade optimisation gateways. Present token economics data: typical API costs, growth in LLM usage volume, and the gap between enterprise and individual optimisation capabilities.

### 2.3 The Control and Transparency Problem

**Content summary:** Users lack visibility into what data their AI tools transmit. Even privacy-conscious users cannot inspect outbound prompts in most interfaces. The problem is compounded by the Model Context Protocol (MCP), which enables LLMs to invoke tools that access filesystems, databases, and cloud services — creating multi-hop data flows that are even harder to audit. The transparency deficit undermines informed consent and makes regulatory compliance (GDPR Article 13, EU AI Act transparency requirements) structurally difficult.

### 2.4 The Local-First Response

**Content summary:** Contextualise the emerging local-first AI movement. Vitalik Buterin's "My self-sovereign / local / private / secure LLM setup" (April 2026) articulates the philosophy: keep all files local, run inference locally where possible, and treat cloud LLMs as untrusted services to be used cautiously. This aligns with the local-first software movement (Kleppmann et al., 2019) and the growing availability of capable small language models (Gemma 3n, Phi-4-mini, Qwen 3.5) that run on consumer hardware. Present the thesis: a local intermediary that sits between user and LLM — rather than replacing the LLM — occupies an underexplored and practically important point in the design space.

### 2.5 Contributions

**Content summary:** Enumerate the five contributions of this work:

1. **Architecture.** The design and implementation of loke, a local-first intermediary that combines privacy filtering, token optimisation, intelligent routing, and transparency controls in a single desktop application.
2. **Multi-layer PII detection.** A four-layer pipeline (regex, NLP NER, SLM-based NER, Presidio) with reversible anonymisation, benchmarked against single-layer approaches.
3. **Layered token optimisation.** Empirical evaluation of combining TOON format conversion, LLMLingua-2 compression, and semantic caching, including interaction effects between layers.
4. **Routing intelligence.** A sensitivity-aware routing framework that balances privacy, cost, latency, and task quality when deciding between local and cloud inference.
5. **Transparency UX.** A user study examining how intermediary-based transparency and control mechanisms affect user trust, task performance, and privacy behaviour.

### 2.6 Hypotheses

**H1 (Token optimisation):** The layered optimisation pipeline (TOON + LLMLingua-2 + semantic caching) achieves greater token savings than any individual technique alone, with less than 2% degradation in downstream task accuracy.

**H2 (PII detection):** The multi-layer PII detection pipeline achieves higher F1-score than any individual layer, with the marginal contribution of each layer statistically significant (p < 0.05).

**H3 (Routing quality):** Sensitivity-aware routing achieves task quality within 5% of always-cloud routing while reducing cloud API calls by at least 40%.

**H4 (User transparency):** Users who can inspect and modify outbound prompts (transparency condition) report higher trust and perceived control than users with opaque intermediary processing, without significant degradation in task completion time.

**H5 (Privacy behaviour):** Exposure to the intermediary's PII detection alerts changes users' subsequent data-sharing behaviour, even when the intermediary is removed (lasting effect).

---

## 3. Related Work (3,000 words)

### 3.1 Survey Structure

The related work section is organised around five research areas, each with identified key papers and categories.

### 3.2 Privacy-Preserving LLM Interaction

**Key categories:**
- Differential privacy for language models (Abadi et al., 2016; McMahan et al., 2018; Yu et al., 2022)
- Federated learning for language models (McMahan et al., 2017; Hard et al., 2018)
- PII detection and anonymisation (Microsoft Presidio documentation; Lison et al., 2021 — NER for anonymisation; Pilán et al., 2022 — text anonymisation benchmark)
- Prompt sanitisation (Chen et al., 2023 — prompt injection defences; Greshake et al., 2023 — indirect prompt injection)
- Data governance for AI (EU AI Act text; NIST AI RMF 1.0)

**Key distinction to draw:** Most privacy work focuses on the model training phase (differential privacy, federated learning) or on the model provider's obligations (data retention policies). loke addresses the inference-time privacy gap — what happens between the user composing a prompt and the cloud LLM receiving it. This gap is largely unaddressed in the academic literature.

### 3.3 Token and Prompt Optimisation

**Key categories:**
- Prompt compression: LLMLingua (Jiang et al., 2023), LLMLingua-2 (Pan et al., 2024), 500xCompressor (ACL 2025), EHPC (NeurIPS 2025)
- Data serialisation for LLMs: TOON (toon-format benchmark paper), Tok-son (Rickard, 2023 — 62% token reduction over JSON)
- Semantic caching: GPTCache (Zilliz), LangCache, and Redis-based approaches (Bang et al., 2023)
- Context window management: Lost in the Middle (Liu et al., 2023), retrieval-augmented generation (Lewis et al., 2020)

**Key distinction to draw:** Prior work evaluates these techniques in isolation. loke layers them in sequence and the interaction effects — whether gains compound, conflict, or plateau — have not been studied.

### 3.4 LLM Routing and Model Selection

**Key categories:**
- Cost-quality routing: RouteLLM (LMSYS, 2024), FrugalGPT (Chen et al., 2023)
- Multi-algorithm routing: LLMRouter (UIUC), Semantic Router (Aurelio AI)
- Mixture of experts and cascading: speculative decoding (Leviathan et al., 2023), model cascades (Varshney & Baral, 2023)
- Local vs. cloud decision-making: this is an underexplored area with limited academic literature; most routing research assumes all models are cloud-hosted

**Key distinction to draw:** Existing routing research optimises for cost and quality. loke adds sensitivity as a routing dimension — some data should never leave the device regardless of which model would produce the best answer. This privacy-first routing constraint creates a different optimisation problem.

### 3.5 Local-First Software and Edge AI

**Key categories:**
- Local-first software principles (Kleppmann et al., 2019 — "Local-First Software: You Own Your Data, in Spite of the Cloud")
- Edge AI and on-device inference: MLX (Apple), llama.cpp, Ollama ecosystem
- Small language models: Phi series (Microsoft), Gemma series (Google), Qwen series (Alibaba)
- Distributed inference: Exo (peer-to-peer), Petals (BitTorrent-style)

**Key distinction to draw:** Local-first software literature focuses on data ownership and availability. Local AI tools (Ollama, LM Studio) focus on model serving. loke bridges these — it applies local-first principles specifically to the LLM interaction pipeline, treating cloud LLMs as optional, untrusted accelerators rather than primary infrastructure.

### 3.6 Usable Privacy and Transparency

**Key categories:**
- Usable privacy: Cranor (2012 — "A Framework for Reasoning About the Human in the Loop"), Schaub et al. (2015 — privacy notice design space)
- Transparency in AI systems: Ehsan et al. (2021 — explainability), Liao et al. (2020 — question-driven XAI design)
- Privacy decision-making: Acquisti et al. (2015 — privacy and human behaviour in the age of information), nudging approaches
- Control and autonomy in human-AI interaction: Amershi et al. (2019 — guidelines for human-AI interaction), Shneiderman (2022 — human-centred AI)

**Key distinction to draw:** The privacy literature extensively studies notice-and-consent for data collection. loke presents a different paradigm: real-time inspection and modification of outbound data. The transparency is active (users see and can change what leaves) rather than passive (users read a policy). This active transparency model has not been empirically studied in the LLM interaction context.

---

## 4. System Architecture (2,500 words)

### 4.1 Overview

**Content summary:** Present the high-level architecture of loke as a local intermediary. The system intercepts all LLM-bound traffic — whether from a browser workspace, a CLI coding tool, or an MCP-connected application — and processes it through a pipeline of privacy filtering, token optimisation, and intelligent routing before any data leaves the device. Include an architecture diagram showing the data flow from user input through the processing pipeline to either local or cloud inference, and back.

### 4.2 Multi-Layer PII Detection Pipeline

**Content summary:** Detail the four-layer detection architecture:

- **Layer 1 (Regex):** Zero-dependency pattern matching for structured PII. Emails, phone numbers (international formats), SSNs, credit card numbers (Luhn-validated), IP addresses, dates of birth. Near-perfect precision on structured formats; zero recall on unstructured PII. Execution time: sub-millisecond per request.
- **Layer 2 (NLP NER — compromise.js):** Lightweight named entity recognition for person names, locations, and organisations in unstructured text. 180KB footprint, approximately 1MB/s throughput. Good recall on common Western names; weaker on non-Western naming conventions and ambiguous entities.
- **Layer 3 (SLM-based NER):** A local small language model (Anonymizer SLM or GLiNER) performing semantic-aware entity recognition. Catches context-dependent PII that earlier layers miss — e.g., "the patient in room 302" or indirect identifiers. Under 500ms overhead, over 99% response parity with unfiltered prompts.
- **Layer 4 (Presidio):** Microsoft Presidio running as a local HTTP microservice for comprehensive detection across 180+ entity types. Serves as the high-confidence final pass with reversible anonymisation using a locally-stored placeholder mapping.

**Present the reversible anonymisation protocol:** PII tokens are replaced with short placeholders ($c1, $l2, $p3). The mapping table is stored only on the local device. After the LLM responds using placeholders, the mapping is applied in reverse to produce a natural-language response. Discuss the security properties of this approach: the mapping never leaves the device, placeholders are semantically neutral, and the LLM receives sufficient context to reason about the data without accessing the actual values.

### 4.3 Token Optimisation Stack

**Content summary:** Detail the four-stage optimisation pipeline:

- **Stage 1 (TOON format conversion):** Structured data (JSON, CSV, database results) converted to Token-Optimised Object Notation. Schema descriptors, statistical summaries, and representative examples replace raw data. Measured savings: 30-60% token reduction with higher downstream accuracy than raw JSON (76.4% vs. 75.0% on benchmarked tasks).
- **Stage 2 (LLMLingua-2 prompt compression):** Natural language portions of the prompt compressed using data-distilled XLM-RoBERTa. Up to 20x compression with approximately 1.5% quality loss. The model runs locally, adding 50-200ms of latency depending on prompt length.
- **Stage 3 (Semantic caching):** Prompts are embedded and compared against a local vector store (LanceDB) of previous prompt-response pairs. Semantically similar prompts (cosine similarity above a configurable threshold) are served from cache. Measured savings on cache hits: up to 73% API cost reduction in repeated-pattern workloads.
- **Stage 4 (toke encoding):** When the target LLM supports it, the final prompt is encoded in toke compressed language format. Approximately 62% token reduction over JSON for structured content. (Note: toke is in early development; TOON and LLMLingua serve as interim compression in current implementation.)

**Discuss interaction effects:** The stages are applied in sequence, and their savings are not simply additive. TOON reduces the data portion; LLMLingua compresses the natural language portion; semantic caching eliminates redundant requests entirely. The empirical evaluation (Section 6) measures the actual combined effect.

### 4.4 Intelligent Routing Engine

**Content summary:** Present the routing framework and its five dimensions:

1. **Content sensitivity.** Classified by the PII detection pipeline. High-sensitivity content is routed to local models only, regardless of other factors.
2. **Task complexity.** Assessed by intent classification (Semantic Router, approximately 10ms). Simple completions, formatting tasks, and factual lookups can be handled locally. Complex reasoning, creative generation, and multi-step analysis are routed to cloud models.
3. **Cost.** Given the user's available subscriptions and current token consumption, route to the cheapest model that meets quality requirements. RouteLLM provides 85% cost reduction with 95% quality retention.
4. **Latency.** For interactive tasks (code completion, chat), prefer the model with lowest time-to-first-token. For batch tasks (document summarisation), optimise for throughput.
5. **User preference.** Manual overrides at the per-task, per-session, or system-wide level. The user always has final authority over routing decisions.

**Formalise the routing decision** as a constrained optimisation problem: minimise cost subject to sensitivity constraints (hard), quality constraints (soft, configurable threshold), and latency constraints (soft, task-dependent).

### 4.5 Transparency and Control Interface

**Content summary:** Describe the UX patterns that make the intermediary's processing visible and controllable:

- **Pre-transmission display:** Every outbound prompt is displayed to the user before sending. In browser mode, this appears as a side panel; in terminal mode, as a coloured diff showing original vs. processed prompt.
- **Modification capability:** Users can edit the processed prompt before approving transmission.
- **PII highlights:** Detected PII entities are highlighted with their classification (name, email, location, etc.) and the proposed anonymisation.
- **Audit trail:** A persistent, searchable log of all interactions — local processing steps, external transmissions, LLM responses, and MCP tool calls.
- **Progressive trust:** As users gain confidence, they can relax the approval requirement — from per-prompt approval to per-session approval to automatic processing with logging.

---

## 5. Methodology (3,500 words)

### 5.1 Benchmark 1: Token Savings

**Objective:** Measure the token reduction achieved by each optimisation stage individually and in combination, and quantify the effect on downstream task accuracy.

**Dataset construction:**
- **Structured data tasks (n=200):** Drawn from real-world data analysis scenarios — financial reports, customer databases, sensor readings, log files. Each task consists of a dataset (JSON/CSV) and a natural language question. Datasets range from 500 to 50,000 tokens in raw JSON representation.
- **Unstructured text tasks (n=200):** Document summarisation, question answering, and information extraction tasks drawn from standard NLP benchmarks (SQuAD 2.0, CNN/DailyMail, Natural Questions) augmented with synthetic PII to enable privacy pipeline testing.
- **Code tasks (n=200):** Repository-level coding tasks drawn from SWE-bench Lite and HumanEval, with injected proprietary identifiers (company names, internal API endpoints, customer-specific variable names) to test anonymisation effects on code comprehension.

**Experimental conditions:**
1. **Baseline:** Raw prompt, no optimisation.
2. **TOON only:** Structured data converted to TOON format; natural language unchanged.
3. **LLMLingua only:** Natural language compressed; structured data unchanged.
4. **Caching only:** Semantic cache populated from half the dataset; measured on remaining half.
5. **TOON + LLMLingua:** Format conversion followed by prompt compression.
6. **Full pipeline:** TOON + LLMLingua + semantic caching.
7. **Full pipeline + anonymisation:** Full pipeline with PII detection and placeholder substitution.

**Metrics:**
- **Token count:** Measured using tiktoken (cl100k_base encoding) for both input and output tokens.
- **Token savings (%):** (baseline_tokens - optimised_tokens) / baseline_tokens * 100.
- **Task accuracy:** Task-specific metrics — exact match and F1 for QA tasks, ROUGE-L for summarisation, pass@1 for code tasks, accuracy for data analysis tasks.
- **Accuracy preservation (%):** optimised_accuracy / baseline_accuracy * 100.
- **Latency overhead (ms):** Additional processing time introduced by each optimisation stage.
- **Cost savings ($):** Estimated API cost using published pricing for GPT-4o, Claude 3.5 Sonnet, and Gemini 1.5 Pro.

**Statistical methods:**
- Paired t-tests (or Wilcoxon signed-rank tests if normality assumptions are violated, assessed via Shapiro-Wilk test) comparing each condition against baseline for both token savings and accuracy.
- Two-way repeated-measures ANOVA to test for interaction effects between TOON and LLMLingua (do their savings compound, or does one subsume the other?).
- Effect size reporting using Cohen's d for all pairwise comparisons.
- Bonferroni correction for multiple comparisons across the seven experimental conditions.
- 95% confidence intervals for all reported metrics.

**Power analysis:** With 200 tasks per category and an expected effect size of d=0.3 (small-medium) for accuracy differences, we achieve power > 0.90 at alpha = 0.05 (two-tailed).

### 5.2 Benchmark 2: PII Detection Accuracy

**Objective:** Measure the precision, recall, and F1-score of each PII detection layer individually and in combination, with particular attention to the marginal contribution of each successive layer.

**Dataset construction:**
- **Synthetic PII corpus (n=5,000 text segments):** Generated using Faker (Python) across 12 locales, embedded in realistic contexts — emails, chat messages, code comments, data analysis prompts, business documents. Each segment contains 0-10 PII entities with ground-truth labels.
- **Entity types covered:** Person names (including non-Western naming conventions), email addresses, phone numbers (international formats), physical addresses, SSNs, credit card numbers, dates of birth, IP addresses, medical record numbers, bank account numbers, passport numbers, and indirect identifiers (job titles combined with company names, "the CEO of [company]").
- **Adversarial examples (n=500):** Designed to test edge cases — PII embedded in code strings, base64-encoded PII, PII split across sentence boundaries, false positives (entity names that resemble person names, version numbers that resemble phone numbers).

**Experimental conditions:**
1. **Layer 1 only (Regex).**
2. **Layer 2 only (compromise.js NLP NER).**
3. **Layer 3 only (SLM-based NER).**
4. **Layer 4 only (Presidio).**
5. **Layers 1+2 (Regex + NLP).**
6. **Layers 1+2+3 (Regex + NLP + SLM).**
7. **Full pipeline (Layers 1+2+3+4).**

**Metrics:**
- Per-entity-type precision, recall, and F1-score.
- Aggregate precision, recall, and F1-score (micro and macro averaged).
- Marginal recall: additional true positives detected by each successive layer.
- Marginal false positive rate: additional false positives introduced by each successive layer.
- Latency per layer and cumulative pipeline latency.
- Reversibility accuracy: percentage of placeholder-substituted prompts that produce semantically equivalent LLM responses compared to original prompts (measured by human evaluation on a stratified sample of n=100).

**Statistical methods:**
- McNemar's test for pairwise comparison of detection accuracy between layer configurations (appropriate for paired binary classification on the same dataset).
- Bootstrap confidence intervals (10,000 resamples) for F1-scores.
- Cochran's Q test to assess whether there is a statistically significant difference across all layer configurations simultaneously.
- Stratified analysis by entity type, locale, and context type (email, code, document).

### 5.3 Benchmark 3: Routing Quality

**Objective:** Measure the quality of routing decisions — specifically, how well sensitivity-aware routing preserves task quality compared to always-cloud and always-local baselines.

**Dataset construction:**
- **Mixed-sensitivity task set (n=500):** Tasks annotated with ground-truth sensitivity labels (high/medium/low) based on the presence and type of PII, proprietary code markers, and domain classification. Sensitivity labels assigned by three independent annotators; inter-rater reliability reported using Fleiss' kappa.
- **Tasks span:** general knowledge QA (low sensitivity), code completion with proprietary identifiers (medium), personal health/financial queries (high).

**Experimental conditions:**
1. **Always-cloud:** All tasks sent to cloud LLM (GPT-4o) without filtering.
2. **Always-local:** All tasks processed by local SLM (Qwen 3.5-9B via Ollama).
3. **Random routing:** Tasks randomly assigned to local or cloud (50/50 split).
4. **Complexity-only routing:** Route by task complexity (Semantic Router classification), ignoring sensitivity.
5. **Sensitivity-only routing:** Route by PII detection results, ignoring complexity.
6. **Full loke routing:** Sensitivity-aware routing using all five dimensions.

**Metrics:**
- **Task quality:** Task-specific accuracy metrics (same as Benchmark 1).
- **Cloud call rate (%):** Percentage of tasks routed to cloud.
- **Privacy violations (count):** Number of tasks containing high-sensitivity PII that were routed to cloud.
- **Routing accuracy:** Agreement between loke's routing decision and an "oracle" routing (defined as: local if local quality >= 90% of cloud quality AND contains any PII; cloud otherwise). Oracle labels established by running all tasks through both local and cloud models.
- **Cost efficiency:** Total API cost as a percentage of always-cloud cost.
- **Latency profile:** Distribution of response times across routing conditions.

**Statistical methods:**
- Chi-squared tests for routing accuracy comparisons.
- Mixed-effects models with task quality as the dependent variable, routing condition as a fixed effect, and task difficulty as a random effect.
- ROC analysis for the routing decision boundary (sensitivity threshold for local vs. cloud).
- Cost-quality Pareto frontier analysis across routing configurations.

### 5.4 Privacy Analysis: Formal Threat Model

**Objective:** Enumerate the threats to user privacy in the loke architecture and analyse the system's defences against each.

**Threat model framework:** We adopt the STRIDE model (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) applied to each component and data flow in the architecture.

**Adversary models:**

1. **Honest-but-curious cloud LLM provider.** The LLM provider faithfully executes inference but records and analyses all prompts and responses. This is the primary adversary model. Defence: PII anonymisation pipeline ensures the provider receives only placeholder-substituted content.

2. **Malicious MCP server.** An MCP server (cloud-hosted or compromised local) attempts to exfiltrate data through tool call responses or by requesting access to local resources. Defence: MCP broker applies the same privacy filter to all MCP data flows; whitelist-based access control.

3. **Network adversary.** An attacker observing network traffic between loke and cloud services. Defence: TLS for all external connections; traffic analysis resistance is out of scope (prompt length and timing may leak information).

4. **Compromised local environment.** Malware on the user's device attempts to access loke's stored mappings, audit logs, or intercepted prompts. Defence: encrypted storage for mapping tables; OS-level process isolation; this threat model acknowledges that a fully compromised device is beyond the system's defensive boundary.

5. **Social engineering / user bypass.** The user is tricked into disabling privacy protections or manually pasting sensitive data into a direct LLM interface. Defence: progressive trust model; conservative defaults; transparency displays that make privacy state visible.

**Data flow analysis:** For each data flow in the architecture (user input to processing pipeline, pipeline to local SLM, pipeline to cloud LLM, MCP tool calls, companion device communication, audit log writes), enumerate: (a) what data traverses the flow, (b) what protections are applied, (c) what residual risk remains.

**Attack surface enumeration:**
- Electron application attack surface (renderer process compromise, IPC exploitation)
- Local model serving attack surface (Ollama API, model poisoning)
- Network API surface (proxy endpoints, MCP broker)
- Storage attack surface (SQLite databases, LanceDB vector store, mapping tables)
- Supply chain attack surface (npm dependencies, model weights)

### 5.5 User Study Protocol (IRB-Ready)

**Title:** "Transparency and Control in Privacy-Preserving AI Intermediaries: Effects on Trust, Task Performance, and Privacy Behaviour"

**Research questions:**
- RQ1: Does real-time visibility into intermediary processing increase user trust in AI tools?
- RQ2: Does the ability to modify intermediary decisions (edit anonymised prompts, override routing) affect task completion time and quality?
- RQ3: Does exposure to PII detection feedback change subsequent data-sharing behaviour?
- RQ4: How do users balance privacy protection against convenience and response quality?

**Study design:** 2 x 2 between-subjects factorial design.

- **Factor 1: Transparency.** (a) Opaque — the intermediary processes prompts but the user sees only the final response. (b) Transparent — the user sees the processing pipeline, detected PII, proposed anonymisations, and routing decisions before transmission.
- **Factor 2: Control.** (a) Automatic — the intermediary acts on its processing without user intervention. (b) Interactive — the user can modify anonymisations, override routing decisions, and approve/reject each outbound prompt.

This yields four conditions: Opaque-Automatic, Opaque-Interactive, Transparent-Automatic, Transparent-Interactive.

**Participants:**
- Target: n=120 (30 per condition), recruited from a university participant pool and professional networks.
- Inclusion criteria: age 18+, regular use of AI chatbots (at least weekly), sufficient English proficiency for the task scenarios.
- Exclusion criteria: professional expertise in AI privacy or security (to avoid ceiling effects on privacy awareness).
- Compensation: $25 for approximately 60 minutes.

**Power analysis:** With n=30 per cell, alpha=0.05, and the ability to detect a medium effect size (f=0.25) in a 2x2 ANOVA, achieved power is approximately 0.80. For the primary trust measure, based on pilot data from comparable transparency studies, we expect effect sizes in the medium-to-large range.

**Procedure:**

1. **Pre-study questionnaire (10 min).** Demographics, AI usage frequency, privacy concern scales (Westin privacy index, Concern for Information Privacy — CFIP), technology self-efficacy, prior experience with privacy tools.

2. **Training phase (10 min).** Participants receive a standardised tutorial on the intermediary tool appropriate to their condition. All participants learn that the tool processes prompts for privacy; transparency conditions additionally see the processing interface; interactive conditions additionally learn the modification controls.

3. **Task phase (25 min).** Participants complete eight tasks of escalating sensitivity using the intermediary:
   - Tasks 1-2 (Low sensitivity): General knowledge questions. No PII present.
   - Tasks 3-4 (Medium sensitivity): Data analysis tasks with synthetic customer names and email addresses embedded in the data.
   - Tasks 5-6 (High sensitivity): Personal health queries and financial planning tasks requiring disclosure of (synthetic) personal health conditions, income, and SSN.
   - Tasks 7-8 (Adversarial): Tasks designed to tempt bypassing the intermediary — e.g., "I need this answered quickly and the privacy filter is slowing me down" with an option to disable the intermediary.

   Each task includes a correct answer and a time limit. Task order is fixed (escalating sensitivity) to simulate realistic trust-building.

4. **Post-study questionnaire (10 min).** Trust scale (adapted from Jian et al., 2000 — Trust in Automation scale), perceived control (Ajzen's perceived behavioural control items), System Usability Scale (SUS), NASA-TLX (cognitive load), willingness to use the tool in the future, open-ended feedback.

5. **Behavioural follow-up (1 week later).** Participants complete a brief online task involving sharing personal information with an AI tool — without the intermediary. Measures whether exposure to PII detection feedback in the study changed their subsequent data-sharing behaviour.

**Measures:**

| Measure | Instrument | When |
|---------|-----------|------|
| Privacy concern | CFIP (Smith et al., 1996) | Pre-study |
| Trust | Trust in Automation (Jian et al., 2000) | Post-study |
| Perceived control | Perceived Behavioural Control (Ajzen, 1991) | Post-study |
| Usability | System Usability Scale (Brooke, 1996) | Post-study |
| Cognitive load | NASA-TLX (Hart & Staveland, 1988) | Post-study |
| Task accuracy | Correctness of responses (0-1 per task) | During task |
| Task completion time | Seconds per task | During task |
| Bypass attempts | Count of attempts to disable intermediary | During task |
| Modification frequency | Count of edits to intermediary decisions (interactive conditions) | During task |
| Post-exposure behaviour | PII disclosure in follow-up task (binary + count) | 1-week follow-up |

**Statistical analysis plan:**
- 2x2 ANOVA for each dependent variable (trust, perceived control, SUS, NASA-TLX, mean task accuracy, mean task completion time).
- Planned contrasts: Transparent vs. Opaque (collapsing across control); Interactive vs. Automatic (collapsing across transparency).
- Mixed-effects regression for per-task analysis (task nested within participant) to model how trust and behaviour change across escalating sensitivity levels.
- Logistic regression for bypass attempts (binary: attempted vs. did not attempt) with condition, privacy concern (CFIP), and technology self-efficacy as predictors.
- Mann-Whitney U tests for the follow-up behavioural measure (expected non-normal distribution).
- Qualitative coding of open-ended responses using thematic analysis (Braun & Clarke, 2006).

**Ethical considerations:**
- Study involves synthetic PII only; no real personal data is collected or transmitted.
- Participants are informed that the AI intermediary is experimental and that all data processing is simulated.
- Deception is minimal: participants in the opaque condition are not told that the tool processes their prompts differently from those in the transparent condition, but all participants are debriefed at the end.
- The follow-up behavioural task involves informed consent for data sharing; participants can opt out at any stage.
- Data storage: all study data de-identified and stored on university-managed encrypted servers.
- Approval to be sought from [institution] IRB before participant recruitment.

---

## 6. Evaluation and Results (3,000 words)

### 6.1 Token Savings Results

**Content summary:** Present results in tables and figures:
- Table: Token counts (mean, SD) by condition and task category (structured, unstructured, code).
- Figure: Bar chart showing percentage token savings by condition, with error bars (95% CI).
- Figure: Accuracy preservation scatter plot — each point is a task, x-axis is token savings, y-axis is accuracy ratio (optimised/baseline). Identify the Pareto frontier.
- Table: Statistical test results — pairwise comparisons between conditions.
- Table: Interaction effects — ANOVA results for TOON x LLMLingua interaction.
- Figure: Latency breakdown by pipeline stage.

**Expected findings:** Based on the component literature, we anticipate combined savings of 60-80% on structured data tasks (TOON provides the largest contribution) and 40-60% on unstructured text tasks (LLMLingua dominates). Semantic caching is highly variable — near-100% savings on cache hits, zero on cache misses — with overall savings dependent on workload repetitiveness. The interaction between TOON and LLMLingua may be sub-additive on structured data (TOON already removes redundancy that LLMLingua would have targeted) but complementary on mixed-content prompts.

### 6.2 PII Detection Results

**Content summary:** Present results:
- Table: Per-entity-type precision, recall, F1 by layer configuration.
- Figure: Cumulative recall curve showing how each successive layer adds to detection coverage.
- Table: Marginal contribution analysis — additional true positives and false positives per layer.
- Figure: Confusion matrix for the full pipeline on adversarial examples.
- Table: Latency by layer (individual and cumulative).
- Table: Reversibility accuracy — LLM response quality with and without anonymisation.

**Expected findings:** Regex achieves near-perfect precision on structured PII (emails, SSNs, credit cards) but zero recall on names and indirect identifiers. NLP NER adds substantial recall for common Western names but introduces false positives (entity names, place names used as adjectives). SLM-based NER catches context-dependent PII that all other layers miss. Presidio serves as a high-confidence validator, marginally improving recall while reducing false positives through its multi-signal approach. The full pipeline is expected to exceed 98% F1 on the standard corpus and 90%+ on adversarial examples.

### 6.3 Routing Quality Results

**Content summary:** Present results:
- Table: Task quality by routing condition.
- Figure: Cloud call rate vs. task quality scatter plot for all routing configurations.
- Table: Privacy violations by condition (critical safety metric).
- Figure: Cost-quality Pareto frontier.
- Table: Routing decision confusion matrix (loke routing vs. oracle).
- Figure: Latency distribution by routing condition.

**Expected findings:** Full loke routing should achieve zero privacy violations (high-sensitivity tasks never routed to cloud), task quality within 5% of always-cloud (because most quality-demanding tasks are low-sensitivity and still routed to cloud), and cloud call reduction of 40-65% depending on the workload's sensitivity distribution.

### 6.4 User Study Results

**Content summary:** Present results:
- Table: Descriptive statistics for all measures by condition.
- Table: 2x2 ANOVA results for primary measures (trust, perceived control, usability, cognitive load).
- Figure: Trust scores by condition with interaction plot.
- Figure: Task completion time across the eight tasks (by condition), showing the learning/trust trajectory.
- Table: Regression results for bypass behaviour.
- Figure: Follow-up behavioural data — PII disclosure by condition.
- Qualitative themes from open-ended responses.

**Expected findings:** Transparency will increase trust and perceived control (main effect). Interactivity will increase perceived control but also cognitive load (main effect). The interaction may reveal that Transparent-Interactive produces the highest trust but also the highest cognitive load, suggesting a design trade-off. The follow-up behavioural measure may show that transparent conditions produce more cautious subsequent behaviour, supporting H5.

---

## 7. Discussion (2,000 words)

### 7.1 The Intermediary Pattern as a Design Paradigm

**Content summary:** Argue that the intermediary pattern — sitting between user and LLM rather than modifying either — is a generalizable approach to AI safety and privacy. Unlike approaches that require model modification (differential privacy, fine-tuning) or provider cooperation (data retention policies), the intermediary is user-deployed and provider-agnostic. Discuss the limitations: the intermediary cannot prevent the LLM provider from misusing data that does get transmitted; it can only minimise what gets transmitted and ensure the user is informed.

### 7.2 Practical Implications

**Content summary:** Discuss deployment implications. loke as implemented requires a desktop application and local compute resources. This limits accessibility to users with modern hardware (Apple Silicon Mac, or PC with discrete GPU for larger models). Discuss the tension between privacy and accessibility — the users most vulnerable to privacy violations (less technical, lower-income) may lack the hardware to run local inference. Consider companion device economics and cloud-free configurations for resource-constrained environments.

### 7.3 Regulatory Alignment

**Content summary:** Map loke's capabilities to specific EU AI Act requirements (transparency, human oversight, data governance) and discuss how the intermediary pattern could serve as a compliance mechanism for organisations using cloud-hosted AI systems classified as high-risk. The EU AI Act high-risk provisions take effect in August 2026, creating immediate demand for tools that provide audit trails, data governance, and human oversight of AI interactions.

### 7.4 Limitations

**Content summary:** Acknowledge limitations explicitly:
- The PII detection pipeline is not perfect; rare entity types and novel encoding strategies can evade detection.
- Token optimisation benchmarks depend on the specific tasks chosen; real-world workloads may differ.
- The user study uses synthetic PII and simulated scenarios; ecological validity is limited.
- Routing quality depends on the capability gap between local and cloud models, which changes as local models improve.
- The threat model assumes the local device is not fully compromised; a device-level adversary defeats all local protections.
- Performance benchmarks are hardware-dependent; results on Apple Silicon M-series may not generalise to other platforms.

### 7.5 Future Work

**Content summary:**
- Extend PII detection to multimodal inputs (images, audio, video) as LLMs become multimodal.
- Investigate differential privacy techniques applied at the intermediary layer (adding calibrated noise to anonymised prompts).
- Longitudinal study of user behaviour changes with prolonged intermediary use.
- Enterprise deployment study examining organisational policy enforcement through the intermediary.
- Formal verification of the privacy properties of the reversible anonymisation protocol.
- Web privacy metadata standardisation — propose and evaluate the `data-ai-sensitivity` HTML attribute for per-element privacy declarations.

---

## 8. Conclusion (500 words)

**Content summary:** Restate the contributions, summarise the key findings, and argue for the practical importance of the intermediary pattern. The convergence of regulatory pressure (EU AI Act), cultural demand (local-first AI movement), and technical capability (small language models on consumer hardware) creates a timely window for this work. loke demonstrates that privacy, efficiency, and usability need not be in tension — the intermediary architecture achieves strong privacy guarantees and substantial cost savings while preserving (and in some cases improving) task quality. The user study results inform the design of transparency and control mechanisms that respect user autonomy without imposing excessive cognitive burden.

---

## 9. Target Venue Analysis

### 9.1 USENIX Security Symposium

**Why appropriate:** USENIX Security is the premier venue for systems security research. loke's threat model, attack surface analysis, and multi-layer defence-in-depth approach to PII detection align with the conference's emphasis on practical security systems. The privacy analysis (formal threat model, data flow analysis) forms the core contribution for this venue.

**Specific fit:** The 2025-2026 programmes have included work on LLM security, prompt injection, and data leakage. The intermediary pattern addresses a systems security problem (preventing data exfiltration to cloud services) with a systems security solution (interposition and filtering).

**Submission format:** 18 pages (excluding references), double-blind review. Emphasise the security analysis and threat model; de-emphasise the user study.

**Typical acceptance rate:** 15-18%.

### 9.2 Proceedings on Privacy Enhancing Technologies (PoPETs)

**Why appropriate:** PoPETs is the top venue for privacy-enhancing technologies. loke's reversible anonymisation protocol, multi-layer PII detection pipeline, and privacy-preserving routing are direct contributions to the PETs literature. The formal privacy analysis and the data flow analysis are central.

**Specific fit:** PoPETs has published work on differential privacy for language models, anonymisation techniques, and privacy-preserving data analysis. loke extends this to the inference-time interaction between users and cloud LLMs — a gap in the current PoPETs literature.

**Submission format:** Rolling submission (4 issues per year), 15-20 pages. Emphasis on provable privacy properties and empirical privacy evaluation.

**Typical acceptance rate:** 20-25%.

### 9.3 ACM CHI Conference on Human Factors in Computing

**Why appropriate:** CHI is the premier venue for human-computer interaction research. The user study examining transparency and control trade-offs in privacy-preserving AI tools is a direct CHI contribution. The progressive trust model, the active transparency pattern (inspect-and-modify vs. notice-and-consent), and the behavioural follow-up measure are novel HCI contributions.

**Specific fit:** CHI 2025-2026 has featured substantial work on human-AI interaction, explainable AI, and usable privacy. loke contributes to the intersection of these areas.

**Submission format:** 10-page paper + references, double-blind. Emphasise the user study, UX design rationale, and qualitative findings; include system description as context.

**Typical acceptance rate:** 25-28%.

### 9.4 ACM CCS (Conference on Computer and Communications Security)

**Why appropriate:** CCS covers a broad range of security topics, including applied cryptography, systems security, and privacy. loke's contribution to CCS would emphasise the security architecture: the intermediary as a reference monitor for LLM traffic, the attack surface analysis, and the formal properties of the reversible anonymisation protocol.

**Specific fit:** CCS has featured work on ML security, adversarial ML, and data privacy. The intermediary pattern as a security mechanism for AI interaction is novel in the CCS literature.

**Submission format:** 12 pages + references, double-blind. Emphasis on security properties and formal analysis.

**Typical acceptance rate:** 18-20%.

### 9.5 Venue Strategy Recommendation

**Primary submission:** PoPETs — the strongest alignment with loke's core contribution (privacy-enhancing technology for LLM interaction), rolling deadline reduces time pressure, and the acceptance rate is the most favourable.

**Secondary submission (different emphasis):** CHI — the user study can be developed into a standalone paper emphasising the HCI contribution, with the system architecture as supporting context. This does not conflict with a PoPETs submission if the CHI paper focuses on user behaviour and the PoPETs paper focuses on the privacy technology.

**Tertiary target:** USENIX Security — if the formal threat model and security analysis are substantially developed, the security-focused version of the paper could target USENIX Security.

---

## 10. Potential Academic Collaborators

### 10.1 By Research Area

**Privacy-preserving machine learning:**
- Researchers at institutions with established groups in differential privacy, federated learning, and privacy-preserving computation (e.g., groups working on DP-SGD, secure multi-party computation for ML, or privacy-preserving inference).
- Look for authors of recent papers on inference-time privacy for LLMs, as opposed to training-time privacy — this is a smaller but directly relevant community.

**Local-first software and edge computing:**
- Researchers working on CRDTs, local-first architectures, and offline-capable systems, particularly those who have engaged with the "local-first software" manifesto (Kleppmann et al., 2019) and its community.
- Edge AI researchers working on efficient inference on consumer hardware, particularly those benchmarking small language models on Apple Silicon or mobile devices.

**Usable privacy and security:**
- HCI researchers with publication records in usable privacy (SOUPS, CHI privacy tracks), particularly those studying privacy decision-making, privacy notices and consent, or transparency mechanisms.
- Researchers who have conducted IRB-approved user studies involving AI tools and privacy, who can advise on study design and institutional review.

**NLP and information extraction:**
- Researchers working on named entity recognition, particularly PII-specific NER and de-identification in clinical or legal text (the clinical NLP community has extensive experience with de-identification evaluation).
- Researchers working on prompt compression or efficient LLM interaction (authors of LLMLingua, 500xCompressor, or semantic caching papers).

**AI governance and regulation:**
- Legal scholars and policy researchers working on the EU AI Act, particularly those studying the technical requirements for high-risk AI system compliance.
- Researchers at the intersection of computer science and law who work on translating regulatory requirements into technical mechanisms.

### 10.2 Collaboration Strategy

- **Conference networking:** Present preliminary results at workshops co-located with target venues (e.g., USENIX Security workshops, CHI workshops on AI and privacy).
- **Open-source engagement:** Release benchmarking code and datasets early to attract contributors with relevant expertise.
- **Pre-print circulation:** Post a pre-print to arXiv (cs.CR / cs.HC / cs.CL) to signal the research direction and invite feedback.
- **Direct outreach:** Contact authors of the most relevant cited papers (LLMLingua, RouteLLM, local-first software) with specific collaboration proposals tied to their expertise.

---

## 11. Research Timeline

### Phase 1: Foundation (Months 1-3)

| Activity | Duration | Deliverable |
|----------|----------|-------------|
| Literature review and related work section | 6 weeks | Complete related work survey |
| System implementation: PII detection pipeline | 8 weeks | Four-layer pipeline with unit tests |
| System implementation: token optimisation stack | 8 weeks | TOON + LLMLingua + caching pipeline |
| System implementation: routing engine | 6 weeks | Five-dimension routing with Semantic Router |
| Benchmark dataset construction | 4 weeks | 600 tasks (200 structured + 200 unstructured + 200 code) |
| PII evaluation corpus construction | 3 weeks | 5,500 annotated text segments |

### Phase 2: Empirical Evaluation (Months 3-5)

| Activity | Duration | Deliverable |
|----------|----------|-------------|
| Token savings benchmarks (Benchmark 1) | 3 weeks | Results tables, statistical analysis |
| PII detection benchmarks (Benchmark 2) | 3 weeks | Per-layer and combined results |
| Routing quality benchmarks (Benchmark 3) | 3 weeks | Routing accuracy and cost analysis |
| Formal threat model and security analysis | 4 weeks | STRIDE analysis, data flow diagrams, attack surface documentation |
| Paper drafting: architecture and methodology sections | 4 weeks | Draft sections 4-5 |
| Paper drafting: results and discussion sections | 3 weeks | Draft sections 6-7 |

### Phase 3: User Study (Months 5-8)

| Activity | Duration | Deliverable |
|----------|----------|-------------|
| IRB application preparation and submission | 3 weeks | Complete IRB protocol |
| IRB review period | 4-8 weeks | Approval |
| Participant recruitment | 2 weeks | n=120 enrolled |
| Study sessions (staggered) | 4 weeks | Raw data collected |
| 1-week follow-up data collection | 2 weeks | Behavioural follow-up data |
| Data analysis | 3 weeks | Statistical results |
| User study section drafting | 2 weeks | Complete user study results |

### Phase 4: Paper Completion and Submission (Months 8-10)

| Activity | Duration | Deliverable |
|----------|----------|-------------|
| Complete draft integration | 3 weeks | Full paper draft |
| Internal review and revision | 2 weeks | Revised draft |
| External review (collaborators) | 3 weeks | Reviewed draft |
| Final revision and formatting | 2 weeks | Submission-ready paper |
| Submission to primary venue (PoPETs) | — | Paper submitted |
| Prepare CHI-focused user study paper (if applicable) | 4 weeks | Second paper draft |

### Phase 5: Dissemination (Months 10-12)

| Activity | Duration | Deliverable |
|----------|----------|-------------|
| ArXiv pre-print | — | Public pre-print |
| Open-source release of benchmarking code and datasets | 2 weeks | GitHub repository |
| Conference presentation preparation | 2 weeks | Slides and demo |
| Workshop paper or poster for secondary venue | 3 weeks | Workshop submission |
| Blog post and community engagement | 1 week | Public summary |

---

## Appendices (Planned)

### Appendix A: TOON Format Specification
Complete specification of the Token-Optimised Object Notation format as used in loke, including schema descriptors, statistical summary fields, and example encodings.

### Appendix B: PII Detection Patterns
Full list of regex patterns used in Layer 1, including international format support and validation rules (Luhn check for credit cards, check digit validation for SSNs).

### Appendix C: User Study Materials
Pre-study questionnaire, task descriptions, post-study questionnaire, follow-up task description, informed consent form, debriefing script.

### Appendix D: Benchmark Dataset Samples
Representative examples from each task category (structured, unstructured, code) and each sensitivity level (low, medium, high), with expected outputs.

### Appendix E: Full Statistical Results
Complete statistical tables including all pairwise comparisons, effect sizes, confidence intervals, and assumption checks (normality, homogeneity of variance).

---

## References (Planned — Key Papers)

The following papers and resources form the core of the related work survey. This is not exhaustive; the full reference list will expand during the literature review phase.

**Privacy and anonymisation:**
- Abadi, M., et al. (2016). Deep learning with differential privacy. CCS.
- Lison, P., et al. (2021). Named entity recognition without labelled data for anonymous text. ACL Workshop on NLP and Computational Social Science.
- Pilán, I., et al. (2022). The text anonymization benchmark (TAB). LREC.
- Microsoft Presidio documentation and technical reports.

**Prompt compression and token optimisation:**
- Jiang, H., et al. (2023). LLMLingua: Compressing prompts for accelerated inference of large language models. EMNLP.
- Pan, Z., et al. (2024). LLMLingua-2: Data distillation for efficient and faithful task-agnostic prompt compression. ACL Findings.
- TOON format benchmarks (toon-format/toon repository).

**LLM routing and model selection:**
- Chen, L., et al. (2023). FrugalGPT: How to use large language models while reducing cost and improving performance. ICML.
- RouteLLM (LMSYS) technical report.
- LLMRouter (UIUC) technical report.

**Local-first and edge AI:**
- Kleppmann, M., et al. (2019). Local-first software: You own your data, in spite of the cloud. Onward!
- Buterin, V. (2026). My self-sovereign / local / private / secure LLM setup. Blog post.

**Usable privacy:**
- Acquisti, A., et al. (2015). Privacy and human behavior in the age of information. Science.
- Cranor, L.F. (2012). A framework for reasoning about the human in the loop. USENIX Security.
- Schaub, F., et al. (2015). A design space for effective privacy notices. SOUPS.

**Human-AI interaction:**
- Amershi, S., et al. (2019). Guidelines for human-AI interaction. CHI.
- Jian, J., et al. (2000). Foundations for an empirically determined scale of trust in automated systems. IJCAS.
- Shneiderman, B. (2022). Human-centered AI. Oxford University Press.

**AI governance and regulation:**
- EU AI Act (Regulation 2024/1689). Official Journal of the European Union.
- NIST AI Risk Management Framework 1.0 (2023).
- UC Davis study on AI browser extension privacy violations (2025).

**Security analysis:**
- Greshake, K., et al. (2023). Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection. AISec Workshop.
- Chen, S., et al. (2023). Prompt injection attacks and defenses in LLM-integrated applications. arXiv.
