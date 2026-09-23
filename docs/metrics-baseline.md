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

### PII detection, regex layer, measured by loke's OWN compiled detector — 2026-09-23

**The first detection figure this project has taken from the code it ships.** Every earlier
figure, including the block below, came from `score_patterns.py` reading the pattern strings
and evaluating them with **Python's `re`**. This one calls `core.privacy.regex.detect`.

| Metric | Value | N |
|---|---|---|
| Recall, regex-addressable types, overlap rule | **95.45%** | 88 entities in 74 texts |
| Recall, exact span | 59.09% | 88 entities |
| Detections made | 94 | |

**Arm:** `regex-layer-toke-compiled`.
**Workload:** `tests/fixtures/pii-corpus`, seed 20260919, spans verified by construction.
**Assertion:** `tests/integration/test_detection_recall.tk`, with a **floor of 90.00%** held
in integer basis points. The floor is a policy, not a measurement — it is set below what the
detector achieves so that it fails when a change makes detection worse. Lowering it to make a
build pass is the thing that file exists to prevent.

**The headline is the cross-validation.** Overlap recall is **95.45%** here and **0.9545**
from the Python scorer on the same corpus — identical. The two engines agree, which is the
first evidence that the Python-based figures in the block below were not misleading about
recall, and it is worth more than the number itself: that instrument has carried a mandatory
"Python's engine is not toke's, and both limits push in unknown directions" caveat since
2026-09-19, and one of those directions is now known to be zero.

**Exact-span recall diverges, and the cause is loke's spans rather than its detection** —
59.09% against Python's 71.69%. toke's regex engine exposes **no match offset at all**, so
PL1.7 recovers each span with `str.indexof` on the matched value; where a value occurs twice
the span points at the first occurrence. That approximation is documented in `regex.tk` and is
exactly why the exact-span figure is **reported and not floored**: flooring a number whose
instrument has a stated approximation would assert more than is known.

**What this still is not.** The regex layer only. NER and Presidio need network sidecars that
are not running, so `PERSON` and the rest are outside the addressable set — the same reason
the block below publishes two recall figures. `core.privacy.evaluation` now constructs the
`$comparisonmatrix` that was declared when it was written and never built, so the other two
layers join this table when they can run without a sidecar.

Three things had to land first, and none alone was enough: **AD1.8** ran the privacy harness
for the first time in the project's history, which is how anyone discovered the detector was
reporting every Australian mobile as a Tax File Number; **PL1.7** gave entities real spans, so
the overlap rule became expressible; and **AD1.2** needed a threshold that survives reaching
its caller, since a bare `f64` return is corrupted across a module boundary (T-20) and a floor
of 0.90 could not otherwise have been asserted from a test at all.

Reproduce:

```sh
./scripts/run_tests.sh tests/integration/test_detection_recall.tk
```

### PII detection, regex layer with the PL1.10 filters — 2026-09-23

**The figures above describe a detector that no longer ships.** PL1.7 and PL1.10 added two
post-match filters, and this is the same corpus and the same ten pattern strings re-scored with
them. The 2026-09-19 block is kept because it is what earlier claims were made against, not
because it is current.

| Metric | Pre-filter | **Ships today** | N |
|---|---|---|---|
| Recall, regex-addressable types only | 0.955 | **0.955** | 88 entities |
| Recall, all claimed types | 0.792 | **0.792** | 106 entities |
| Recall, exact span match | 0.717 | **0.717** | 106 entities |
| Precision | 0.700 | **0.894** | 36 → **10** false positives |

**26 of 36 false positives removed, and not one true positive lost.** That is the whole result:
recall is byte-identical on all three definitions, and precision moves 0.700 → 0.894.

**Workload:** `tests/fixtures/pii-corpus`, 74 synthetic cases (40 positive, 20 negative, 14
adversarial), spans verified by construction, seed 20260919.
**Arm:** `regex-layer-python-re-with-pl110-filters`.

**Why the pre-filter column differs from the 2026-09-19 block** (0.955 against 0.932, 36 false
positives against 49): the corpus generator was corrected. It built the dash-separated adversarial
TFN by bumping a valid number's last digit "to keep the case unambiguous", which broke the
checksum as a side effect while still labelling the result `AU_TFN` with
`expected_detected: true`. So 4 of 16 `AU_TFN` positives asserted that a nine-digit run which is
**not** a tax file number must be detected as one — and that assertion is precisely what would
have made checksum gating look like a 25% recall loss. The generator now draws two independent
checksum-valid numbers. The 2026-09-19 figures were measured against the uncorrected fixture.

**Caveats, both mandatory and one of them new:**

1. As before: evaluated with Python's regex engine rather than toke's, and the regex layer is one
   of several. A real figure needs the compiled detector — which is now much closer, because
   AD1.8 made the detector testable for the first time.
2. **New, and a real weakening of the instrument.** The ten pattern strings are still *read* from
   `packages/core/src/privacy/patterns.tk`, so they are not reimplemented. The two filters **are**
   reimplemented in Python, from `regex.digitrunpattern`, `regex.boundaryclear` and
   `regex.tfnchecksumvalid`. That is the stub-test antipattern this project is trying to leave
   behind, done knowingly: without it this script would score a detector that does not exist, and
   a figure describing absent code is worse than a figure with a stated caveat. If those three
   toke predicates change, the Python must change with them. The only real fix is AD1.2's harness
   driving the compiled detector.

**What changed in the detector, and what it cost:**

- `au_tfn` and six other bare-digit-run patterns now reject a match with a digit immediately
  either side of it, which is what "unanchored" meant in practice: the pattern matched the
  trailing nine digits of any Australian mobile, so **every AU phone number was also reported as
  a Tax File Number** and the request's sensitivity escalated CONFIDENTIAL → RESTRICTED. That
  label drives routing, so over-detection was not fail-safe here.
- `au_tfn` is additionally gated on its real weighted-modulus checksum. Against this corpus that
  rejects **all 22** nine-digit `NOT_PII` decoys and loses none of the 16 labelled positives.
- `ssn_us` is deliberately **not** checksum-gated: its rules are not a single modulus and
  inventing one would reject valid numbers. It keeps the boundary check only, which is why 10
  false positives remain.

**Still true from the 2026-09-19 findings, and not addressed:**

- Every `EMAIL` miss is still a mixed-case address against a lower-case-only character class.
  Fixing it means changing a pattern string, which moves these figures again and is a separate
  decision.
- Medicare, BSB, ACN and bank account numbers still have **no detector at all**.
- `au_tfn` still fires inside `au_abn` — `"ABN 51 824 753 556"` reports both. The boundary check
  cannot see it, because the characters either side of the TFN match are spaces. Recorded as
  PL1.10's remaining tail.

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
