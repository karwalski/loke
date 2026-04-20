# TOON Benchmark Methodology

**Token-Optimised Object Notation: A Comprehensive Evaluation Framework**

Version 0.1 | loke Research Track (Story X2.2)

---

## Abstract

This document defines the benchmark methodology for evaluating Token-Optimised Object Notation (TOON) as a data serialisation format for large language model (LLM) communication. The evaluation framework covers 12 task types across 4 data shapes, tested against 6 models spanning multiple providers and parameter scales. We measure token count, task accuracy, end-to-end latency, and cost, with accuracy-per-1K-tokens as the primary composite metric. The methodology enables fair comparison against existing prompt compression techniques — LLMLingua, 500xCompressor, and EHPC — and is designed for full reproducibility through published scripts, datasets, and result artifacts.

---

## 1. Benchmark Design

### 1.1 Task Types

The benchmark suite comprises 12 task types, selected to represent the breadth of structured-data interactions that occur in real-world LLM usage. Each task is defined by a natural language instruction template, an expected output format, and a scoring rubric.

| ID | Task Type | Description | Input Shape | Expected Output |
|----|-----------|-------------|-------------|-----------------|
| T01 | Tabular QA | Answer factual questions about tabular data (e.g., "What is the average revenue for Q3?") | Tabular | Short-form text answer |
| T02 | Data Summarisation | Produce a natural language summary of a dataset's key characteristics | Tabular, Nested | Paragraph-length summary |
| T03 | Schema Inference | Infer column names, data types, constraints, and relationships from raw data | Tabular, Nested | Structured schema description |
| T04 | Time Series Analysis | Identify trends, seasonality, anomalies, and inflection points in temporal data | Time Series | Structured analysis with cited data points |
| T05 | Code Documentation | Generate docstrings, type annotations, or README sections from structured API specs | Nested | Code or Markdown |
| T06 | API Response Parsing | Extract specific fields, flatten nested structures, or transform API responses | Nested | Structured extraction |
| T07 | Log Analysis | Identify error patterns, frequency distributions, and root causes from log data | Mixed | Structured report |
| T08 | Report Generation | Produce a formatted report (Markdown or HTML) from input data | Tabular, Nested | Long-form document |
| T09 | Data Transformation | Convert data between formats, apply filters, compute derived columns | Tabular | Transformed dataset |
| T10 | Multi-Table Join Reasoning | Answer questions requiring reasoning across multiple related tables | Tabular (multi) | Short-form text answer |
| T11 | Anomaly Detection | Identify outliers and explain why they are anomalous given the dataset context | Tabular, Time Series | Annotated anomaly list |
| T12 | Data Validation | Check data against stated constraints and report violations | Tabular, Nested | Violation report |

### 1.2 Data Shapes

Each task is executed against at least one of four data shapes. Where a task supports multiple shapes, it is benchmarked against each applicable shape independently.

**Tabular (CSV-like).** Rectangular data with typed columns. Varying dimensions: narrow (4-8 columns, 50-500 rows), wide (20-50 columns, 50-500 rows), and long (4-8 columns, 1,000-10,000 rows). Includes numeric, categorical, date, and free-text column types.

**Nested (JSON).** Hierarchical data with variable depth (2-6 levels). Includes arrays, objects, mixed types, and nullable fields. Represents API responses, configuration files, and document structures.

**Time Series.** Uniformly or irregularly sampled temporal data. Varying resolutions: minute-level (sensor data), hourly (infrastructure metrics), daily (financial data), and monthly (economic indicators). Includes univariate and multivariate series.

**Mixed.** Combinations of the above: tabular data with JSON-encoded columns, time series embedded within nested structures, or multi-format payloads representing real-world data pipelines.

### 1.3 Dataset Sources

All benchmark datasets are drawn from publicly available sources to ensure reproducibility. No proprietary or restricted-access data is used.

| Dataset | Source | Shape | Tasks | License |
|---------|--------|-------|-------|---------|
| UCI Machine Learning Repository (Adult, Iris, Wine Quality) | archive.ics.uci.edu | Tabular | T01, T02, T03, T09, T10, T12 | CC BY 4.0 |
| NYC Taxi Trip Records (sample) | nyc.gov/tlc | Tabular | T01, T02, T11 | Public domain |
| GitHub REST API responses (public repos) | api.github.com | Nested | T03, T05, T06 | Public API |
| OpenWeatherMap historical data | openweathermap.org | Time Series | T04, T11 | CC BY-SA 4.0 |
| Common Crawl web server logs (sample) | commoncrawl.org | Mixed | T07 | Public domain |
| World Bank Open Data (economic indicators) | data.worldbank.org | Time Series, Tabular | T04, T08, T10 | CC BY 4.0 |
| JSONPlaceholder API (synthetic) | jsonplaceholder.typicode.com | Nested | T06, T12 | MIT |
| Synthetic multi-table dataset (generated) | Benchmark repository | Tabular (multi) | T10, T12 | Apache 2.0 |
| Apache access log corpus (synthetic) | Benchmark repository | Mixed | T07 | Apache 2.0 |
| OpenAPI specification files (public APIs) | apis.guru | Nested | T05 | CC0 |

For each dataset, the benchmark repository includes:
- A frozen snapshot at a specific version or date
- SHA-256 checksums for integrity verification
- A preprocessing script that produces the exact input fed to each task
- Metadata documenting row/column counts, data types, and any sampling applied

### 1.4 Dataset Sizing

To isolate the effect of serialisation format from context window limitations, each dataset is prepared at three size tiers:

| Tier | Token Budget (approximate) | Purpose |
|------|---------------------------|---------|
| Small | 500-2,000 tokens (in JSON) | Fits comfortably in all model context windows; isolates format efficiency |
| Medium | 5,000-15,000 tokens (in JSON) | Representative of typical analytical workloads |
| Large | 30,000-80,000 tokens (in JSON) | Stresses context windows; tests whether compression preserves accuracy at scale |

---

## 2. Models Under Test

### 2.1 Model Selection Criteria

Models are selected to span three dimensions:
1. **Provider diversity** — at least three distinct API providers plus local inference
2. **Parameter scale** — from small (< 10B) through large (> 100B)
3. **Architecture diversity** — dense transformers, mixture-of-experts, and distilled variants

### 2.2 Model Matrix

| ID | Model | Provider | Parameters | Context Window | Access Method |
|----|-------|----------|------------|----------------|---------------|
| M1 | GPT-4o | OpenAI | Undisclosed (large) | 128K | Cloud API |
| M2 | Claude 3.5 Sonnet | Anthropic | Undisclosed (large) | 200K | Cloud API |
| M3 | Gemini 2.0 Flash | Google | Undisclosed (large) | 1M | Cloud API |
| M4 | Llama 3.3 70B | Meta (via Ollama) | 70B | 128K | Local inference |
| M5 | Qwen 3.5 9B | Alibaba (via Ollama) | 9B | 32K | Local inference |
| M6 | Mistral Small 24B | Mistral (via Ollama) | 24B | 32K | Local inference |

Local models are served via Ollama to standardise the inference pipeline. Cloud models are accessed through their respective REST APIs. All models use default sampling parameters (temperature = 0.0, top_p = 1.0) unless otherwise stated, to maximise response determinism.

### 2.3 Tokeniser Configuration

Token counts are measured using each provider's canonical tokeniser:

| Provider | Tokeniser | Library |
|----------|-----------|---------|
| OpenAI | cl100k_base / o200k_base | tiktoken |
| Anthropic | Claude tokeniser | anthropic SDK `.count_tokens()` |
| Google | Gemini tokeniser | google-generativeai SDK |
| Meta / Llama | LlamaTokenizer | tokenizers (HuggingFace) |
| Alibaba / Qwen | Qwen tokeniser | tokenizers (HuggingFace) |
| Mistral | Mistral tokeniser | tokenizers (HuggingFace) |

All token counts are reported per-tokeniser. Cross-model comparisons use the geometric mean of per-tokeniser token counts to avoid bias toward any single tokenisation scheme.

---

## 3. Serialisation Formats Compared

### 3.1 Format Definitions

Each benchmark configuration serialises the same underlying data using one of the following formats. The system prompt and task instruction are held constant across formats; only the data payload varies.

**F1: Raw JSON.** Standard `JSON.stringify` output with 2-space indentation. This is the baseline format, representing how most applications currently pass structured data to LLMs.

**F2: Minified JSON.** `JSON.stringify` with no whitespace. Tests whether trivial whitespace removal accounts for a significant portion of savings.

**F3: YAML.** PyYAML-style serialisation with default flow style for short sequences. Tests whether a less verbose markup language provides meaningful improvement.

**F4: TOON.** Token-Optimised Object Notation as specified in the toon-format/toon repository. Includes schema descriptors, statistical summaries, typed columns, and compact row encoding. The TOON serialiser is configured with default settings (no manual tuning per dataset).

**F5: LLMLingua-compressed.** The JSON payload is first serialised as natural language description, then compressed using LLMLingua-2 with the data-distilled XLM-RoBERTa model. Compression ratio target: 5x (adjustable per experiment).

**F6: TOON + LLMLingua.** The TOON-serialised payload is further compressed by LLMLingua-2 applied to any natural language segments within the TOON packet (contextual framing, statistical descriptions). Tests whether the two techniques compose.

**F7: toke (when available).** The toke compressed language format. If toke is not publicly available at benchmark time, this format is omitted and noted as planned future work.

### 3.2 Format Preparation

All format conversions are performed deterministically by benchmark scripts. No manual editing or per-dataset tuning is applied. Format preparation time (serialisation latency) is recorded as part of the latency metrics.

For LLMLingua-based formats, the compression model is loaded once and reused across all configurations. Model loading time is excluded from per-task latency but reported separately as setup overhead.

---

## 4. Metrics

### 4.1 Primary Metrics

#### 4.1.1 Token Count

- **Input tokens:** number of tokens in the complete prompt (system prompt + task instruction + serialised data), as measured by the target model's tokeniser
- **Output tokens:** number of tokens in the model's response
- **Total tokens:** input + output
- **Compression ratio:** `tokens(JSON) / tokens(format)` for input tokens only

All token counts exclude any API overhead (request framing, safety preambles injected by the provider). Where a provider does not expose raw token counts, we use the closest available tokeniser and note the approximation.

#### 4.1.2 Task Accuracy

Each task type has a dedicated scoring rubric. Scores are normalised to the range [0, 100].

| Task | Scoring Method | Details |
|------|---------------|---------|
| T01 Tabular QA | Exact match + fuzzy numeric | Exact string match for categorical answers; within 1% for numeric answers; partial credit for correct reasoning with wrong final answer |
| T02 Data Summarisation | LLM-as-judge (GPT-4o) | 5-point rubric: completeness, accuracy, conciseness, insight quality, coherence. Score = mean of 3 independent judge calls |
| T03 Schema Inference | Structural F1 | F1 score over (column_name, data_type) pairs. Partial credit for correct column name with wrong type |
| T04 Time Series Analysis | Checklist scoring | Pre-defined checklist of expected findings (trend direction, seasonality period, named anomalies). Score = fraction of checklist items identified |
| T05 Code Documentation | LLM-as-judge + syntax check | Syntax validity (parseable docstring/Markdown) + LLM judge on completeness and accuracy |
| T06 API Response Parsing | Exact structural match | JSON equality of extracted fields against gold standard. Partial credit for correct subset |
| T07 Log Analysis | Checklist scoring | Pre-defined checklist of error patterns, frequencies, and root causes |
| T08 Report Generation | LLM-as-judge | 5-point rubric: data accuracy, structure, readability, completeness, actionability |
| T09 Data Transformation | Row-level exact match | Fraction of output rows matching expected transformation. Tolerance for floating-point rounding |
| T10 Multi-Table Join | Exact match + reasoning trace | Correct final answer + evidence of cross-table reasoning in chain-of-thought |
| T11 Anomaly Detection | Precision and recall | Precision and recall over the set of true anomalies, with partial credit for correct anomaly with wrong explanation |
| T12 Data Validation | Precision and recall | Precision and recall over the set of true violations |

**LLM-as-judge calibration.** For tasks scored by LLM judge (T02, T05, T08), we calibrate the judge by scoring 50 human-annotated examples and reporting inter-annotator agreement (Cohen's kappa) between the judge and human annotators. The judge model (GPT-4o) is held constant and is never the same model being evaluated.

#### 4.1.3 Latency

- **Serialisation latency:** wall-clock time to convert raw data into the target format (TOON serialisation, LLMLingua compression, etc.)
- **API latency:** wall-clock time from request submission to final response token (time-to-last-token, TTLT)
- **Time-to-first-token (TTFT):** time from request submission to first response token
- **End-to-end latency:** serialisation + API latency + any post-processing (destoking, decompression)

All latency measurements use monotonic clocks (`performance.now()` or equivalent). Network variability for cloud models is addressed through repeated measurements (see Section 5).

#### 4.1.4 Cost

Cost is computed from published per-token pricing at the time of benchmark execution. Both input and output token costs are included.

```
cost = (input_tokens * input_price_per_token) + (output_tokens * output_price_per_token)
```

Pricing is recorded in a versioned configuration file with the date retrieved and source URL. For local models, cost is reported as zero (API cost) with a separate annotation for estimated electricity and hardware amortisation based on TDP and wall-clock time.

### 4.2 Composite Metrics

#### 4.2.1 Accuracy-per-1K-Tokens

The primary composite metric from TOON research, measuring how much task performance is obtained per unit of token expenditure:

```
accuracy_per_1k = (accuracy_score / total_input_tokens) * 1000
```

This metric directly captures the value proposition of TOON: achieving equal or better accuracy with fewer tokens. A higher value indicates a more efficient serialisation format.

#### 4.2.2 Cost-Adjusted Accuracy

```
cost_adjusted_accuracy = accuracy_score / cost_usd
```

Normalises accuracy by monetary cost, capturing the combined effect of token reduction and per-token pricing differences across providers.

#### 4.2.3 Pareto Efficiency

For each (model, task, data_shape) triple, we plot accuracy vs. token count across formats and identify the Pareto frontier. Formats on the frontier are Pareto-efficient; formats below the frontier are dominated. We report the fraction of configurations where each format appears on the Pareto frontier.

---

## 5. Statistical Methodology

### 5.1 Experimental Design

The full benchmark is a factorial design across four factors:

| Factor | Levels |
|--------|--------|
| Task type | 12 |
| Data shape | 4 (where applicable per task) |
| Model | 6 |
| Serialisation format | 6-7 |

Not all factor combinations are valid (e.g., not all tasks apply to all data shapes). The benchmark runs all valid combinations, yielding approximately 800-1,200 unique configurations.

### 5.2 Repetitions

Each configuration is executed **N = 10** times for cloud models and **N = 5** times for local models (which exhibit lower variance). The first run of each configuration is treated as a warm-up and excluded from analysis, yielding 9 and 4 usable measurements respectively.

For LLM-as-judge evaluations, each response is scored 3 times by the judge model, and the median score is used.

### 5.3 Confidence Intervals

All reported metrics include 95% confidence intervals computed via bootstrap resampling (B = 10,000 resamples). For metrics with non-normal distributions (latency, cost), we report the bias-corrected and accelerated (BCa) bootstrap interval.

Point estimates are reported as the median (for latency and cost) or mean (for accuracy and token count), chosen based on the expected distribution shape.

### 5.4 Statistical Significance Testing

Pairwise comparisons between serialisation formats use the following tests:

| Metric | Test | Justification |
|--------|------|---------------|
| Token count | Exact computation (deterministic) | Token counts are deterministic for a given input; no statistical test needed |
| Accuracy | Wilcoxon signed-rank test | Non-parametric; does not assume normality; paired by (task, model, data, run) |
| Latency | Wilcoxon signed-rank test | Non-parametric; latency distributions are typically right-skewed |
| Cost | Derived from token count | Deterministic given token counts and pricing; no statistical test needed |
| Accuracy-per-1K-tokens | Wilcoxon signed-rank test | Composite metric; paired comparison |

All p-values are corrected for multiple comparisons using the Benjamini-Hochberg procedure (controlling false discovery rate at q = 0.05). We report both raw and adjusted p-values.

### 5.5 Effect Size

For each statistically significant pairwise comparison, we report:

- **Cliff's delta (d):** a non-parametric effect size measure bounded in [-1, 1], interpreted as: negligible (|d| < 0.147), small (0.147 <= |d| < 0.33), medium (0.33 <= |d| < 0.474), large (|d| >= 0.474)
- **Percentage change:** `((metric_new - metric_baseline) / metric_baseline) * 100`, relative to the JSON baseline

### 5.6 Handling Non-Determinism

LLM responses are inherently non-deterministic even at temperature 0 (due to batching, floating-point non-associativity, and provider-side changes). We address this through:

1. **Fixed random seeds** where the API supports them (OpenAI `seed` parameter)
2. **Multiple runs** with variance reporting (see Section 5.2)
3. **Version pinning** of model checkpoints where possible (e.g., `gpt-4o-2025-01-01`)
4. **Temporal clustering** — all runs for a single configuration are executed within a 30-minute window to minimise the effect of provider-side updates

---

## 6. Reproducibility

### 6.1 Dataset Licensing and Availability

All datasets used in the benchmark are available under open licenses (CC BY 4.0, CC0, public domain, MIT, or Apache 2.0). The benchmark repository includes:

- Frozen dataset snapshots with SHA-256 checksums
- Preprocessing scripts that produce benchmark inputs from raw data
- A `DATASETS.md` file documenting each dataset's source, license, access date, and any transformations applied
- A programmatic license checker that validates all datasets against an allowlist

No dataset requires authentication, payment, or agreement to terms of service beyond the stated open license.

### 6.2 Hardware Specifications

All benchmark reports must include the following hardware metadata:

**For local model inference:**
- CPU model, core count, and clock speed
- GPU model, VRAM, and driver version (if applicable)
- Apple Silicon model and unified memory (if applicable)
- Total system RAM
- Storage type (SSD/NVMe)
- Operating system and kernel version
- Ollama version
- Model quantisation level (e.g., Q4_K_M, Q8_0, FP16)

**For cloud model inference:**
- API endpoint region (if known)
- Network round-trip time to API endpoint (measured by ping to API host)
- Client machine location (country/region, not exact address)
- API client library version
- Date and time of benchmark execution (UTC)

### 6.3 Script Structure

The benchmark is implemented as a set of deterministic scripts organised as follows:

```
benchmarks/
  toon/
    README.md                    # Setup and execution instructions
    DATASETS.md                  # Dataset documentation and licensing
    config/
      models.yaml                # Model definitions and API configuration
      formats.yaml               # Serialisation format definitions
      tasks.yaml                 # Task definitions and scoring rubrics
      pricing.yaml               # Per-token pricing (versioned, dated)
    datasets/
      raw/                       # Frozen dataset snapshots
      processed/                 # Benchmark-ready inputs (generated by prepare.ts)
      checksums.sha256           # Integrity verification
    scripts/
      prepare.ts                 # Dataset preprocessing and input generation
      run.ts                     # Main benchmark execution loop
      score.ts                   # Response evaluation and scoring
      analyse.ts                 # Statistical analysis and visualisation
      report.ts                  # Generate summary tables and figures
      validate.ts                # Validate environment and dependencies
    results/
      raw/                       # Raw API responses and measurements (JSON lines)
      processed/                 # Aggregated metrics with confidence intervals
      figures/                   # Generated plots and visualisations
      report.md                  # Auto-generated summary report
    lib/
      serialisers/               # Format implementations (JSON, YAML, TOON, etc.)
      tokenisers/                # Provider-specific token counting
      scorers/                   # Task-specific scoring rubric implementations
      stats/                     # Statistical analysis utilities
```

### 6.4 Execution Protocol

A complete benchmark run follows this sequence:

1. **Environment validation** (`validate.ts`): verify all dependencies, model availability, API keys, dataset integrity
2. **Dataset preparation** (`prepare.ts`): generate benchmark inputs from frozen snapshots, verify checksums
3. **Benchmark execution** (`run.ts`): iterate over all valid (task, shape, model, format) configurations with configured repetitions
4. **Scoring** (`score.ts`): evaluate all responses against task-specific rubrics
5. **Analysis** (`analyse.ts`): compute summary statistics, confidence intervals, significance tests
6. **Reporting** (`report.ts`): generate tables, figures, and narrative summary

Each step is idempotent and can be re-run independently. Intermediate results are persisted to enable partial re-execution after failures.

### 6.5 Result Format and Publication

Raw results are stored as JSON Lines (one record per (task, shape, model, format, run) configuration):

```json
{
  "task_id": "T01",
  "data_shape": "tabular",
  "dataset": "uci_adult",
  "size_tier": "medium",
  "model_id": "M1",
  "format_id": "F4",
  "run_number": 3,
  "timestamp_utc": "2026-04-15T10:23:45.123Z",
  "input_tokens": 1247,
  "output_tokens": 89,
  "tokeniser": "o200k_base",
  "accuracy_score": 85.0,
  "scoring_method": "exact_match_fuzzy_numeric",
  "serialisation_latency_ms": 12.4,
  "ttft_ms": 340.2,
  "ttlt_ms": 1203.7,
  "e2e_latency_ms": 1216.1,
  "cost_usd": 0.000187,
  "model_version": "gpt-4o-2025-01-01",
  "format_version": "toon-0.3.1",
  "raw_response_hash": "sha256:abc123..."
}
```

Aggregated results are published as CSV files with one row per (task, shape, model, format) configuration, including mean, median, standard deviation, and 95% confidence interval bounds for each metric.

All results, scripts, and datasets are published in the benchmark repository under Apache 2.0 license, alongside the technical report.

---

## 7. Comparison Framework

### 7.1 Baseline Definitions

The benchmark defines three baselines against which all formats are compared:

**B1: Raw JSON (indented).** The most common format in which structured data is passed to LLMs today. This is the primary baseline for all comparisons.

**B2: Minified JSON.** Establishes the floor for trivial whitespace-based savings, isolating the contribution of structural optimisation.

**B3: YAML.** A widely used alternative serialisation format that is less verbose than JSON. Establishes whether simple format switching (without structural changes) provides meaningful benefit.

### 7.2 Existing Work Comparison

The benchmark is designed to enable fair, like-for-like comparison with three published compression techniques.

#### 7.2.1 LLMLingua / LLMLingua-2 (Microsoft Research)

**Reference:** Jiang et al., "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression" (ACL 2024).

**Integration approach:**
- LLMLingua-2 is included directly as format F5 in the benchmark
- We use the published `llmlingua` Python package with the recommended `microsoft/llmlingua-2-xlm-roberta-large-meetingbank` model
- Compression ratios are swept across {2x, 5x, 10x, 20x} to characterise the accuracy-compression trade-off
- Results are compared against the paper's reported figures on overlapping tasks (where available) to validate our implementation

**Fairness considerations:**
- LLMLingua is designed for natural language compression, not structured data. The comparison acknowledges this scope difference
- We test LLMLingua both on JSON-serialised data (its weakest case) and on natural language descriptions of the data (its intended use case)
- The combined TOON + LLMLingua format (F6) tests whether the techniques are complementary

#### 7.2.2 500xCompressor (ACL 2025)

**Reference:** Li et al., "500xCompressor: Generalized Prompt Compression for Large Language Models" (ACL 2025).

**Integration approach:**
- 500xCompressor compresses prompts into a small number of special "compression tokens" that are prepended to the LLM input
- If model weights and inference code are publicly available, we integrate 500xCompressor as an additional format (F8) and measure token count as the number of compression tokens plus task instruction tokens
- If only API access is available, we use the API and report results with a note about the black-box nature of the compression
- If neither is available, we compare against the paper's published results on overlapping benchmarks, noting the limitations of cross-study comparison

**Fairness considerations:**
- 500xCompressor requires fine-tuning or adaptation to specific LLMs. We report results only for models where the compressor has been adapted
- Compression token counts may not be directly comparable to natural language token counts (different information density). We report both raw token counts and accuracy-per-1K-tokens, and discuss this limitation
- We reproduce the paper's evaluation on at least one shared benchmark to calibrate cross-study comparison

#### 7.2.3 EHPC (NeurIPS 2025)

**Reference:** Expected publication at NeurIPS 2025. "Efficient Hierarchical Prompt Compression" (title provisional; to be updated with final reference).

**Integration approach:**
- EHPC introduces hierarchical compression that preserves document structure — a property particularly relevant to comparison with TOON
- Integration follows the same protocol as 500xCompressor: direct integration if code is available, API-based if not, cross-study comparison as fallback
- We specifically evaluate EHPC's performance on nested/hierarchical data (JSON structures) where its hierarchical approach should have the greatest advantage

**Fairness considerations:**
- As a NeurIPS 2025 publication, EHPC may not have publicly available code at benchmark time. We note the availability status and update the benchmark when code is released
- If cross-study comparison is necessary, we identify at least two shared evaluation dimensions (dataset, task type, or model) to anchor the comparison

### 7.3 Cross-Study Comparison Protocol

When direct integration of a competing technique is not possible, we follow this protocol for cross-study comparison:

1. **Identify shared evaluation points.** Find overlapping (dataset, task, model) configurations between our benchmark and the published results
2. **Reproduce baseline.** Run our own JSON baseline on the shared configurations and compare with the other paper's JSON baseline to calibrate any systematic differences
3. **Normalise metrics.** Report all comparisons as relative improvements over the respective JSON baselines, rather than absolute values, to control for differences in evaluation setup
4. **Document limitations.** Explicitly enumerate differences in evaluation methodology (model version, temperature, scoring rubric, dataset version) that may affect comparability
5. **Sensitivity analysis.** Where possible, vary our evaluation parameters to bracket the range of plausible comparisons

### 7.4 Comparison Dimensions

The comparison framework evaluates each technique across the following dimensions:

| Dimension | What It Captures | How It Is Measured |
|-----------|-----------------|-------------------|
| Token efficiency | Raw reduction in token count | Compression ratio relative to JSON baseline |
| Accuracy preservation | Whether compression degrades task performance | Accuracy delta from JSON baseline |
| Efficiency frontier | Token-accuracy trade-off | Accuracy-per-1K-tokens |
| Latency overhead | Compression preprocessing cost | Serialisation/compression latency |
| Generality | Performance across diverse tasks and data shapes | Variance in compression ratio and accuracy across task types |
| Composability | Whether the technique combines with others | Performance of combined pipelines (e.g., TOON + LLMLingua) vs. individual techniques |
| Implementation complexity | Practical deployment burden | Lines of code, dependency count, setup steps, hardware requirements |
| Model dependence | Whether the technique requires model-specific adaptation | Performance variance across models without per-model tuning |

---

## 8. Threats to Validity

### 8.1 Internal Validity

- **LLM non-determinism.** Mitigated by multiple runs, fixed seeds where available, and temporal clustering (Section 5.6)
- **LLM-as-judge reliability.** Mitigated by calibration against human annotations and reporting inter-annotator agreement (Section 4.1.2)
- **API-side changes.** Model versions are pinned where possible. Benchmark execution dates are recorded to enable retrospective analysis

### 8.2 External Validity

- **Task selection bias.** The 12 tasks are designed to cover common structured-data interactions but may not represent all LLM use cases. We explicitly scope claims to structured data tasks
- **Dataset representativeness.** Public datasets may not reflect the complexity of proprietary enterprise data. We include synthetic datasets that emulate enterprise characteristics (wide tables, deep nesting, mixed types)
- **Model selection.** Results may not generalise to models not tested. We mitigate by spanning three provider families and three parameter scales

### 8.3 Construct Validity

- **Accuracy-per-1K-tokens** assumes a linear trade-off between accuracy and tokens. In practice, the relationship may be non-linear (e.g., some tasks require a minimum token threshold). We report the raw accuracy-vs-tokens curve in addition to the composite metric
- **Cost metrics** are based on published pricing, which changes frequently. All pricing is dated and versioned

---

## 9. Ethical Considerations

- All datasets are publicly available under open licenses. No human subjects data is collected for this benchmark
- LLM-as-judge evaluations use the judge model solely for scoring, not for generating benchmark data. Judge model outputs are not published as research findings
- Cost estimates are reported transparently to help practitioners make informed decisions about token optimisation trade-offs
- We do not make claims about the safety implications of prompt compression (e.g., whether compressed prompts are more or less susceptible to adversarial attacks). This is noted as important future work

---

## 10. Timeline and Milestones

| Phase | Activities | Duration |
|-------|-----------|----------|
| 1. Infrastructure | Script scaffolding, dataset collection and freezing, format implementation, tokeniser integration | 2 weeks |
| 2. Pilot | Run benchmark on 3 tasks, 2 models, 3 formats to validate methodology and scoring rubrics | 1 week |
| 3. Full execution | Complete benchmark across all valid configurations | 2 weeks |
| 4. Analysis | Statistical analysis, figure generation, cross-study comparison | 1 week |
| 5. Writing | Technical report or workshop paper drafting | 2 weeks |
| 6. Review | Internal review, revision, and publication | 1 week |

---

## 11. Expected Outputs

1. **Technical report** (8-12 pages, ACL/NeurIPS format) presenting results and analysis
2. **Benchmark repository** with all scripts, datasets, and raw results under Apache 2.0
3. **Summary tables and figures** suitable for inclusion in the loke project documentation
4. **Recommendations** for the loke token optimisation pipeline configuration based on empirical results

---

## References

- TOON Format. "Token-Optimised Object Notation." github.com/toon-format/toon
- Jiang, H., Wu, Q., Lin, C.-Y., Yang, Y., Qiu, L. (2023). "LLMLingua: Compressing Prompts for Accelerated Inference of Large Language Models." EMNLP 2023.
- Jiang, H., Wu, Q., Luo, X., Li, D., Lin, C.-Y., Yang, Y., Qiu, L. (2024). "LLMLingua-2: Data Distillation for Efficient and Faithful Task-Agnostic Prompt Compression." ACL 2024.
- Li, Z. et al. (2025). "500xCompressor: Generalized Prompt Compression for Large Language Models." ACL 2025.
- EHPC. (2025). "Efficient Hierarchical Prompt Compression." NeurIPS 2025. (Reference to be updated with final publication details.)
- Rickard, M. "Tok-son: A Token-Optimised JSON Alternative." matt-rickard.com.
