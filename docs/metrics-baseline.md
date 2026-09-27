# Metrics Baseline

**Version:** 1.0
**Last updated:** 2026-09-28

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

### PII detection, regex layer, entity-level with a direct-identifier recall floor — 2026-09-28

**The headline is recall on direct identifiers**, because a missed one names a person to a third
party. Precision is the utility cost of that recall, reported under it and not floored.

| Metric | Value | N |
|---|---|---|
| **Recall, direct identifiers** the regex layer has a pattern for | **92.86%** | 52 of 56 (EMAIL 28, PHONE_AU 12, AU_TFN 16) |
| Recall, every regex-addressable type, overlap | 95.45% | 84 of 88 |
| Recall, exact span | 86.36% | 76 of 88 |
| Precision (utility cost), detection regions overlapping real PII | 89.36% | 94 regions, 10 false positives |

**Arm:** `regex-layer-toke-compiled`, scored by `core.privacy.evaluation` (production module).
**Toolchain:** toke `0b0bc4e`, ooke `v3.0.0-rc.1` (`c07c503`), loke branch `work/w20-ad1` on
`535a909`. **Workload:** `tests/fixtures/pii-corpus`, seed 20260919, 74 cases, `corpus.jsonl`
sha256 `bece1023187d…`. Deterministic: no model is involved. **Measured:** 2026-09-28 by
`tests/integration/test_detection_recall.tk`, which prints the line these figures are read from.

**The floor:** `evaluation.directrecallfloorbp()` = **92.50%**, asserted by that test. It is as high
as the shipped regex layer can hold on this corpus and no higher: losing **one** more direct
identifier (51 of 56, 91.07%) fails it. The four misses today are the separator-formatted `AU_TFN`
positives (`288 916 313`, `638-652-169`, …). PERSON is a direct identifier but has no pattern, so it
is outside this floor and is measured with the model layers below. **Mutation-checked:** with the
email pattern reverted to lower-case only (the 2026-09-19 defect), direct-identifier recall falls to
82.14% (46 of 56) and the floor assertion fails, as does the 90% addressable floor; restored and
checked with `cmp`.

**What changed in the instrument, and why these differ from the 2026-09-23 block:** scoring moved
out of the test into `core.privacy.evaluation`, where it is entity-level and **type-agnostic** (any
overlapping detection masks the span, whatever the layer called it — the rule `score_patterns.py`
always used). And labelled spans are placed by locating each labelled value in the text as loke
decoded it, because std.json turns the corpus's escaped em dash into `u2014` (T-47). That fix is
the whole of the exact-span change, 59.09% → 86.36%, and it now agrees with the Python scorer
exactly (76 of 88, 0.717 over all 106 claimed). Overlap recall is unchanged at 95.45%.

Reproduce:

```sh
python3 tests/fixtures/pii-corpus/generate.py
./scripts/run_tests.sh tests/integration/test_detection_recall.tk
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

**Corrected 2026-09-28 (AD1.2):** the explanation in the next paragraph is wrong. The divergence
was the *scorer's*, not loke's spans: std.json decodes the corpus's escaped em dash as the five
letters `u2014` (T-47), so in the twelve texts containing one every later labelled offset was four
bytes out of the text the detector saw. Scored by `core.privacy.evaluation`, which places each
labelled value in the text as loke decoded it, exact-span recall is **86.36%** — see the 2026-09-28
block above. The paragraph is kept because it is what was published.

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

### Regex detector throughput, against F3.1's 10MB/s target — 2026-09-24

**Superseded for memory by the 2026-09-27 section below (F3.1b); kept as the record of the
defect.** **Result: the target is missed by more than an order of magnitude, and the detector never reaches
10MB at all.** Throughput falls as the input grows, because time and memory both grow roughly with
the square of the input size.

| Input | Median throughput | Range, 5 runs | Median time | Median peak RSS |
|---|---|---|---|---|
| 0.25 MB (249 928 bytes) | **1.07 MB/s** | 0.97–1.13 | 234 ms | 141 MB |
| 0.5 MB (499 932 bytes) | **0.83 MB/s** | 0.81–0.84 | 603 ms | 519 MB |
| 1 MB (999 680 bytes) | **0.57 MB/s** | 0.56–0.58 | 1 750 ms | 1 972 MB |
| 2 MB (1 999 332 bytes) | **0.32 MB/s** | 0.31–0.32 | 6 323 ms | 7 185 MB |
| 10 MB | **not measurable** | — | — | killed by the OS (SIGKILL) |

MB here means 10^6 bytes. **Arm:** `regex-layer-toke-compiled`, timing `core.privacy.regex.detect`,
which is what the pipeline calls. That covers the ten patterns, span recovery, the PL1.10 filters,
placeholder assignment and applying the placeholders to the text, so it is the layer's cost and not
the regex engine's alone. **Toolchain:** toke `fedd48d` (built from that commit, not the
`TOOLCHAIN.lock` value) and loke `c023b3b`. **Host:** one Apple M2 Pro (Mac14,10) with 16 GB, macOS.
**Method (VM1.3):** 6 runs per size, each in a fresh process, with the first discarded as warm-up.
Figures are the median and range of the 5 kept runs. The timer is std.time's millisecond wall clock,
read inside the compiled program, so process start-up and reading the file are excluded. The
percentile-bootstrap interval of the mean, which is in `benchmarks/results/`, sits inside the range
in every row. **Workload:** the 74 cases of `tests/fixtures/pii-corpus` (seed 20260919), each
followed by eight lines of PII-free prose and repeated to size. That is 1.31–1.38 labelled PII
entities and 0.6 decoys per 1 000 bytes.

**Caveats, which travel with the numbers:**

- **One host, one density, one observation series.** The figures are not a rate for other hardware
  or for sparser text, and the quadratic term means density matters a great deal.
- **10 MB never completed.** It was tried three times: once in-process after eleven 1 MB runs, and
  twice as a fresh single-run process on 9 999 870 bytes (13 100 labelled PII, 6 300 decoys). The OS
  killed every attempt with SIGKILL. The two fresh processes died after 54 s and 92 s, before the
  detector returned, and one had passed 5 GB resident when last sampled. Peak RSS grows about ×3.7
  per doubling in the table above, which is the reason. No 10 MB figure is extrapolated from it.
- **Fresh processes are needed.** In one process the times climbed from 1.9 s to 7.3 s over eleven
  1 MB runs, because memory is not released between calls. That is why each run is a separate
  process. The failure is also relevant to the long-running server, and it is filed with the
  quadratic cost as F3.1b.
- The "detections" count the harness prints is placeholder-deduplicated output. It is not a recall
  figure. Recall is published only in the detection blocks above.

Reproduce:

```sh
python3 tests/fixtures/pii-corpus/generate.py
scripts/build_loke.sh && scripts/run_tests.sh tests/unit/browser/test_pipeline_handler.tk   # builds the archives
TOKE_DIR=<toke at fedd48d> python3 benchmarks/regex/run.py --sizes 0.25,0.5,1,2 --runs 6 --record --toke-commit fedd48d
```

### Regex detector throughput after F3.1b — 2026-09-27

**Result: memory now grows linearly and a 10 MB input completes. Throughput is still far below the
10MB/s target, and time still grows faster than the input.** F3.1b removed two allocations that grew
with matches × text length: the span search copied the rest of the text for every match, and
placeholder application copied the whole text once per entity, including every repeat of a value
already replaced.

| Input | Median throughput | Range, 5 runs | Median time | Median peak RSS |
|---|---|---|---|---|
| 0.25 MB (249 928 bytes) | **1.84 MB/s** | 1.77–1.88 | 136 ms | 40 MB |
| 0.5 MB (499 932 bytes) | **1.76 MB/s** | 1.74–1.78 | 284 ms | 72 MB |
| 1 MB (999 680 bytes) | **1.61 MB/s** | 1.60–1.61 | 622 ms | 138 MB |
| 2 MB (1 999 332 bytes) | **1.38 MB/s** | 1.38–1.38 | 1 451 ms | 276 MB |
| 10 MB (9 999 870 bytes) | **0.63 MB/s** | 0.62–0.63 | 15 900 ms | 1 670 MB |

**Arm:** `regex-layer-toke-compiled`, timing `core.privacy.regex.detect`, as above. **Toolchain:** toke
`0b0bc4e` (the `TOOLCHAIN.lock` commit, a clean checkout) and loke `0d29b5e`. **Host:** the same Apple
M2 Pro (Mac14,10) with 16 GB. **Method (VM1.3):** 6 runs per size, each in a fresh process, the first
discarded; median and range of the 5 kept. **Workload:** the same corpus construction; 1.31–1.38
labelled PII entities and 0.6 decoys per 1 000 bytes. The detection count is identical to the
pre-fix build at every size measured on both (248, 512, 1 000, 1 988), so the fix changed the cost
and not the output.

**Caveats:**

- **The comparison with the 2026-09-24 table crosses a toolchain change** (`fedd48d` there, `0b0bc4e`
  here). Before changing the code, the old build was re-measured on `0b0bc4e` (3 runs, first
  discarded): 141, 519 and 1 971 MB peak at 0.25, 0.5 and 1 MB, the same growth as the table above.
- **Peak RSS grows about ×1.8–2.0 per doubling from 0.25 to 2 MB.** From 2 to 10 MB it is ×6.1 for
  ×5 the input, so it is not perfectly linear at the top.
- **Time is still superlinear.** 10 MB takes about 11 times as long as 2 MB. Each per-match call
  (`str.indexof`, `str.substr`) still measures the whole string (T-55), so a term in matches × length
  remains in time, although no longer in memory.
- One host, one density, one observation series, as before.

Reproduce:

```sh
python3 tests/fixtures/pii-corpus/generate.py
scripts/build_loke.sh && scripts/run_tests.sh tests/unit/privacy   # builds the archives
TOKE_DIR=<toke at 0b0bc4e> python3 benchmarks/regex/run.py --sizes 0.25,0.5,1,2,10 --runs 6 --record --toke-commit 0b0bc4e
```

---

## Status: no *performance* figure is published

Three measurements exist: detection recall for the regex layer, the serialisation baselines, and the
regex detector's standalone throughput above. That throughput figure is still a **negative** result
against its target (F3.1b made memory linear and 10 MB completes, but throughput is under 2 MB/s),
and it covers one function on one host. **No figure for end-to-end latency, pipeline throughput, cache hit
rate or any compression technique has been measured**, so none is published. The serialisation entry is a baseline for future token claims, not a result for
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

**Provider list prices used as inputs (F5.11b).** These are published prices, not measurements, and
no figure on this page is derived from them yet. They are the rates loke's cost tables use
(`core.providers.anthropic`, `core.router.router`, `selector`, `strategy`, moke's `cost_comparison`).
Source: Anthropic's pricing page, `platform.claude.com/docs/en/about-claude/pricing`, read 2026-09-27.
Base rates only; prompt-cache, batch and data-residency multipliers are not applied anywhere in loke.

| Model | Model id | Input, USD per million tokens | Output, USD per million tokens |
|---|---|---|---|
| Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 1 | 5 |
| Claude Sonnet 5 | `claude-sonnet-5` | 2 | 10 |
| Claude Opus 5.5 | `claude-opus-5-5` | 4 | 20 |

The OpenAI rates in the same tables were not re-checked, and they disagree with each other:
`core.providers.openai` prices `gpt-4o` at 2.50 / 10, the router tables at 5 / 15.

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
