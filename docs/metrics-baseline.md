# Metrics Baseline

**Version:** 1.0
**Last updated:** 2026-09-19

This file is the **only** source from which this project publishes figures. Every number here carries
its workload, its tokenizer (or says "bytes"), its sample size and its date. Where a figure is widely
quoted but has no entry here, it is **named below and not restated**.

**If another page in this repository or on the website disagrees with this one, this one is right and
the other is a bug.** Report it.

Negative results belong here too. A project that only publishes favourable numbers is not measuring,
it is marketing.

---

## Measured

### PII detection, regex layer only — 2026-09-19

The first measurement this project has recorded. **It is not loke's detection accuracy**, and the
caveat travels with the number wherever it is quoted.

| Metric | Value | N |
|---|---|---|
| Recall, regex-addressable types only | **0.932** | 88 entities |
| Recall, all claimed types | **0.774** | 106 entities |
| Recall, exact span match | 0.698 | 106 entities |
| Precision | 0.626 | 49 false positives |

**Workload:** `tests/fixtures/pii-corpus`, 74 synthetic cases (40 positive, 20 negative, 14
adversarial), spans verified by construction, seed 20260919.
**Arm:** `regex-layer-python-re`.
**Caveat, mandatory:** the ten pattern strings are read directly from
`packages/core/src/privacy/patterns.tk`, so this is not a reimplementation — but it is evaluated with
Python's regex engine rather than toke's, and the regex layer is one of several. Both limits push in
unknown directions. A real figure needs the compiled detector and is blocked on the toolchain
migration.

Both recall figures are given because neither alone is honest: scoring the regex layer against
`PERSON` understates the layer, and omitting `PERSON` overstates loke, since the layers that would
cover the remainder are not running.

**What it found, which is the point of measuring:**

- Every `EMAIL` miss (6 of 28) is a mixed-case address. The pattern is `[a-z0-9._%+-]+@…` with no
  case-insensitive flag, so `John.Smith@Corp.COM` is not matched. That is a leak, not a rounding error.
- 36 of the 49 false positives come from `au_tfn` (20) and `ssn_us` (16). Both are bare nine-digit
  patterns with no checksum validation, so they match invoice numbers, sequence identifiers and
  measurement codes, and they collide with each other.
- 10 of the 18 entities of types with no detector were matched incidentally by another pattern, which
  means **Medicare numbers are currently reported as tax file numbers**.
- Medicare, BSB, ACN and bank account numbers have **no detector at all**, despite Medicare being the
  primary identifier in the flagship demo datasets and central to two of the shipped regulatory presets.

Reproduce:

```sh
python3 tests/fixtures/pii-corpus/generate.py
python3 tests/fixtures/pii-corpus/score_patterns.py
```

---

### Serialisation baselines, input tokens only — 2026-09-20

The second measurement. It is a **baseline**, not a result for any compression technique: it says what
deleting whitespace is worth, so that a later claim has something honest to beat.

Ratios are `tokens(indented JSON) / tokens(format)`, geometric mean over `cl100k_base` and
`o200k_base`. Above 1.0 is a saving.

| Payload | Minified JSON | YAML |
|---|---|---|
| Uniform tabular, 100 rows | **1.80x** | 1.50x |
| Uniform tabular, 1000 rows | **1.80x** | 1.50x |
| Nested, 100 | **1.78x** | 1.42x |
| Mixed types, 100 | **1.66x** | 1.38x |
| Wide, 40 columns | **1.35x** | 1.21x |
| Sparse, 70% null | **1.54x** | 1.40x |
| BITRE road fatalities, 500 rows — real data, CC BY | **1.59x** | 1.47x |

**What this changes for every future token claim.** Deleting whitespace alone is worth 1.35x to 1.80x
— a 26% to 44% token reduction. So a figure quoted against pretty-printed JSON is mostly measuring
indentation. **The baseline for any token-optimisation claim in this project is minified JSON**, and a
technique that only matches it has demonstrated `json.dumps(separators=(",",":"))`.

YAML is worse than minified JSON on every payload measured. A less verbose markup does not get there on
its own.

The real dataset lands at 1.59x, inside the synthetic range, so the generated shapes are not flattering
the result.

**Caveat, which travels with the number:** input token count only. No model was called, so this says
nothing about accuracy — a format that halves the tokens and halves the accuracy is worse, not better.

**Not measured, and not approximated.** Anthropic's tokeniser is not public and counting requires an
API call; Google's likewise. Neither is substituted with `cl100k_base`, because a fabricated Claude
figure for the provider this project sends most of its traffic to would be worse than a gap.

**TOON itself is not measured.** No faithful encoder is available here: the methodology specifies the
`toon-format/toon` implementation, no package is installed, and loke's own encoder is toke and needs the
compiler. An encoder written from the format's description would measure something of this harness's
own invention under TOON's name. So the withdrawn "30-60% TOON" figure stays withdrawn.

Reproduce:

```
python3 benchmarks/toon/run.py --self-test
python3 benchmarks/toon/run.py
```

Harness and full method: [`benchmarks/toon/README.md`](../benchmarks/toon/README.md). Payload checksums
are verified on every run.

---

## Status: no *performance* figure is published

Two measurements exist: detection recall for the regex layer, and the serialisation baselines above.
**No figure for latency, throughput, cache hit rate or any compression technique has been measured**,
so none is published. The serialisation entry is a baseline for future token claims, not a result for
any technique loke implements.

The apparatus needed to change this is specified and tracked:

| Blocker | Story |
|---|---|
| No numeric result sink — `std.test` exposes three string-comparison assertions and cannot record a value, so a test can prove a threshold was met but cannot publish the number it measured | VM1.1 |
| No pinned model versions, seeds, repetition or confidence intervals | VM1.2, VM1.3 |
| No container, so no reproducible environment | VM1.4 |
| CI uploads pass/fail counts only, never numbers | VM1.5 |
| ~~The token-optimisation methodology is written but not implemented~~ — **baselines done**, see above; the accuracy half needs model spend | VM1.7 |
| No disclosure accounting on any request | DA1 |
| ~~No labelled PII corpus and no ground truth~~ — **done**, see the measurement above | AD1.1 |

The methodology for the token-optimisation work already exists at publishable standard in
[research/toon-benchmark-methodology.md](research/toon-benchmark-methodology.md) — named baselines
(raw JSON primary, minified, YAML), twelve task types, four data shapes, a licensed dataset table, N
with warm-up discard, bootstrap confidence intervals, Wilcoxon signed-rank tests, multiple-comparison
correction and frozen snapshots with checksums. It has not been executed. Implementing it is VM1.7;
it does not need redesigning.

---

## Withdrawn figures

These were published previously without a measurement behind them. They are withdrawn, and are listed
so that nobody reinstates them from an older document or a slide. Each returns only as a measurement
with its workload, its tokenizer and its N.

| Figure | Where it appeared | Why withdrawn |
|---|---|---|
| **60–80% token reduction** (combined) | README, features-loke, architecture diagram, website | No end-to-end benchmark ever combined the mechanisms and measured the composite. Described as a "target" in some places and as achieved in others |
| **30–60% savings** (TOON) | README, features-loke | No token measurement. The only saving computed in code is a **character-length** ratio, which is not a token count |
| **up to 20x compression** (LLMLingua) | README, features-loke | "Up to" is unfalsifiable, and the sidecar that would perform the compression is not bundled, so the path is inert out of the box |
| **up to 73% on cache hits** | README, features-loke, website | Hit rate depends entirely on the workload. Never measured here. The figure also conflates a hit rate with a saving |
| **5–30x** (AAAK shorthand) | README, features-loke, website | Design target, never measured |
| **< 500ms for 100K entries** (memory search) | README, features-loke, website | No benchmark, and no hardware specified. Separately, the search is keyword matching over an index table, so the figure would not describe the implementation even if measured |
| **< 10ms** (intent classification) | README, design-principles, website | No timing test exists anywhere. The classifier is a keyword and pattern cascade |
| **< 1 second** (pipeline overhead) | README, design-principles, website | No timing test exists anywhere |
| **85% cost reduction, 95% quality retention** (RouteLLM) | features-loke | A third-party figure repeated without citation, workload, or a definition of the quality metric |
| **98%+ F1** (PII detection) | research-proposal abstract | No corpus, no ground truth, no measurement. The abstract stated it as a presented result |
| **40–65% reduction in cloud API calls** | research-proposal abstract | Same |

Figures appearing in specification documents as **illustrative mock-ups** (for example worked examples
in the savings-dashboard and pipeline-visibility specs) are not withdrawn, because they were never
claims. They should be visibly marked as examples where they are not already.

---

## Definitions

The top-level description makes three claims. Each is meant to be measurable, and this is what each
one means.

### "Reducing what is disclosed"

**Disclosure** is what crosses the boundary to a third party on a given request, measured as a vector
rather than a single score (epic EM1, on the three established axes of singling out, linkability and
inference). Components include bytes and tokens transmitted, the count and type of entities disclosed,
whether any real data value was included, the field names disclosed, and linkability to prior requests.

**Reduction** is always *relative to a named baseline arm* on a named workload — never absolute, and
never "elimination". The baseline is the status quo the claim is compared against, which for analysis
work means placing the data in the prompt.

What it does not measure: inference from context, provider-side retention or training, and correlation
across accounts. The metric bounds disclosure, not consequence.

### "Reducing what is spent"

**Tokens per completed task**, against a named baseline arm on a named benchmark, with the tokenizer
stated. Completion is judged by the benchmark's own scoring, so a reduction that breaks the task does
not count as a reduction. Cost figures additionally state the model and the price date.

### "Keeping the data on the device"

Scoped precisely, because the unqualified version is not true:

- On the **primary path**, no data row is transmitted. What is transmitted is a schema profile — names,
  types, cardinality, null-rate — and the user's question. This is verifiable by asserting that a
  sentinel value present in the data appears zero times in the captured outbound payload.
- **It is not a guarantee of no information flow.** A returned query is itself a channel, and an
  adversary able to shape queries and observe results across turns can extract values a piece at a
  time. Bounding that is an open problem (NC1.10), not a solved one.
- On the **fallback path**, redacted text *is* transmitted. Redaction reduces disclosure without
  preventing identification.
- **loke is not a chokepoint.** Applications must be configured to route through it; anything addressed
  elsewhere never reaches it; and a flag exists to disable the pipeline. Six classes of bypass are
  enumerated and testable (AD1.6). The supportable claim is that *when traffic is in path*, enforcement
  is ordered, recorded and inspectable.
- **Local storage is not currently encrypted.** The key is generated and held in the OS keychain
  correctly, but the toolchain links plain SQLite, which ignores the encryption pragma and reports
  success. The database is plaintext on disk. Tracked as X8.

---

## How to add a figure

1. The measurement comes from a committed harness, not from a manual run.
2. The result records workload, tokenizer or "bytes", N, model and pinned version, seed, date, and the
   toolchain commit from `TOOLCHAIN.lock`.
3. It is reported with a confidence interval, or with its N and the statement that it is a single
   observation. One observation is reported as one observation, never as a rate.
4. The caveat travels with the number, everywhere the number appears.
5. This file is updated first. Other pages cite it; they do not restate it independently.
