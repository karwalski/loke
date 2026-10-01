# Metrics Baseline

**Version:** 1.0
**Last updated:** 2026-10-01

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

**Evidence: legacy, unverified.** Scored by `score_patterns.py`, which prints its figures; no row
was recorded through `benchmarks/lib/result.py`, so there is none to cite. Superseded by the blocks
below.

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

**Evidence: legacy, unverified.** Read from the line `tests/integration/test_detection_recall.tk`
prints; no row was recorded through the result sink, so there is none to cite. The floor is asserted
by that test on every run, which is the evidence it has.

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

### PII detection, marginal value per layer — 2026-09-28

**Evidence: legacy, unverified.** `benchmarks/ad13/run.py --record` wrote its rows to the ignored
`benchmarks/results/` directory on the measuring machine, and they were never committed, so there is
nothing to cite. The figures are three-run ranges, not the BCa interval VM1.3 now requires of
anything a model produced, and `--record` no longer runs (VM1.3b). They were measured at toke
`0b0bc4e`, not the current toke 3.1.0 (`86c432da`). A re-measurement on 3.1.0 was attempted on
2026-10-01 and recorded nothing: the test runner's keychain guard fails a run this long (X8.10).

**The first measurement of any detection layer other than regex.** Every earlier per-layer figure
is void: until VM1.6e (2026-09-27) the NER and Presidio layers had never been reached at all.

Recall over all 106 labelled entities loke claims to detect (so PERSON is in, Medicare is out);
direct identifiers are the 74 of them that name a person (PERSON 18, EMAIL 28, PHONE_AU 12,
AU_TFN 16). Precision and false positives are the utility cost, counted as merged masked regions.
Where the NER layer is involved the figure varied between the three runs, and the range is given.

| Layers | Recall | **Recall, direct identifiers** | Precision (cost) | False-positive regions |
|---|---|---|---|---|
| regex alone | 79.25% (84) | **70.27%** (52) | 89.36% | 10 |
| NER alone | 77.36–80.19% (82–85) | 77.03–81.08% (57–60) | 65.43–66.67% | 50–56 |
| privacy-filter alone | 88.68% (94) | 83.78% (62) | 92.44% | 18 |
| regex + NER | 95.28–96.23% (101–102) | **93.24–94.59%** (69–70) | 66.47–67.48% | 53–57 |
| regex + privacy-filter | 96.23% (102) | **94.59%** (70) | 90.53% | 16 |
| all three | 97.17–98.11% (103–104) | **95.95–97.30%** (71–72) | 68.65–71.51% | 53–58 |

| Added to regex | Entities gained | of which direct identifiers | False-positive regions added |
|---|---|---|---|
| + NER | 17–18 | 17–18 | 43–47 |
| + privacy-filter | 18 | 18 | 6 |
| + both | 19–20 | 19–20 | 43–48 |

**What it says.** Every entity a model layer adds over regex is a direct identifier. NER and the
privacy-filter sidecar each lift direct-identifier recall from 70% to about 94%, but NER pays seven
to eight times the false-positive cost for it (43–47 regions against 6) and varies from run to
run, where the sidecar gives the same answer every time. **The better of the two is the layer
`pipeline.run` does not call** (AD1.4, B9). Adding both buys one or two more entities over either.
Even with every layer that ran, 2 to 3 labelled entities are still missed.

**Not measured, and why:**

- **Presidio**, which `pipeline.run` does call. No Presidio analyser is installed on the measuring
  machine and installing one needs the network. There is no figure for it.
- **NER with loke's default model.** `pipeline.newconfig` names `qwen2.5:7b`, which is not installed
  here; the model used is `qwen2.5:3b`. The NER rows describe that model, not the shipped default.
- No latency, no per-type breakdown of NER's false positives, and none of research-proposal §5.2's
  statistical tests (McNemar, Cochran's Q). Three runs is enough to show the spread, not to put an
  interval on it.

**Provenance.** toke `0b0bc4e`, ooke `v3.0.0-rc.1` (`c07c503`), loke branch `work/w20-ad1` on
`535a909` with the AD1.2/AD1.3 change. Corpus `tests/fixtures/pii-corpus`, seed 20260919, 74 cases,
`corpus.jsonl` sha256 `bece1023187d…`. NER: `core.privacy.ner.scan` against Ollama 0.22.0 on
loopback, `qwen2.5:3b` (digest `357c53fb659c`, Q4_K_M), no temperature pinned because loke pins
none. Privacy-filter: `core.privacy.sidecarclient.detect` against `packages/privacy-filter/server.py`
on loopback, `openai/privacy-filter` revision `7ffa9a043d54d1be65afb281eddf0ffbe629385b` from the
local Hugging Face cache with `HF_HUB_OFFLINE=1`, threshold 0.0 (the `models.json` default). Regex
in process. Three runs, 2026-09-28, macOS arm64; recorded through `benchmarks/lib/result.py`
(VM1.1). Scored by `core.privacy.evaluation` in `tests/integration/test_layer_marginal.tk`: entity
level, type-agnostic overlap, NER values placed wherever the pipeline would mask them. Because
false positives are merged regions, a union can count fewer than one of its parts (regex + sidecar
16, sidecar alone 18): a spurious fragment that merges into a region covering real PII stops being
spurious. Nothing was sent off the machine.

Reproduce (after `scripts/build_loke.sh` and the moke and loke-cli trees are built):

```sh
TOKE_DIR=<toke at 0b0bc4e> BUILDDIR=<dir> python3 benchmarks/ad13/run.py --ner-model qwen2.5:3b --runs 3 --record
```

### PII detection, regex layer, measured by loke's OWN compiled detector — 2026-09-23

**Evidence: legacy, unverified.** Read from test output; no row was recorded through the result
sink, so there is none to cite.

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

**Evidence: legacy, unverified.** Scored by `score_patterns.py`, which prints its figures; no row
was recorded through the result sink, so there is none to cite.

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
- ACN still has **no detector at all**. Medicare, BSB and bank account numbers gained regex
  detectors on 2026-10-01 (RG1.7: Medicare checksum-gated, BSB and account only after their
  label), and Centrelink CRN, passport, driver licence and superannuation member numbers the
  same day (RG1.7a: each only after its label, none with a check that can be applied). No
  figure here measures them yet; the counts in this section predate them.
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

**Evidence: verified.** Every figure in this section cites the recorded row it was read from; see
the end of the section.

The second measurement. It is a **baseline**, not a result for any compression technique: it says what
deleting whitespace is worth, so that a later claim has something honest to beat.

Ratios are `tokens(indented JSON) / tokens(format)`, geometric mean over `cl100k_base` and
`o200k_base`. Above 1.0 is a saving.

| Payload | Minified JSON | YAML |
|---|---|---|
| Uniform tabular, 100 rows | **1.80x** <sub>[ev:98f805d6d5a6 n=2]</sub> | 1.50x <sub>[ev:a0b160904a1a n=2]</sub> |
| Uniform tabular, 1000 rows | **1.80x** <sub>[ev:dc91fb0462ec n=2]</sub> | 1.49x <sub>[ev:d72e6141382a n=2]</sub> |
| Nested, 100 | **1.78x** <sub>[ev:494127ea3f20 n=2]</sub> | 1.42x <sub>[ev:ccbf49313072 n=2]</sub> |
| Mixed types, 100 | **1.66x** <sub>[ev:3324e382af99 n=2]</sub> | 1.38x <sub>[ev:ffa28a7defce n=2]</sub> |
| Wide, 40 columns | **1.35x** <sub>[ev:a5d0cdbc349c n=2]</sub> | 1.21x <sub>[ev:55b824c297aa n=2]</sub> |
| Sparse, 70% null | **1.54x** <sub>[ev:5ee276ae98e3 n=2]</sub> | 1.40x <sub>[ev:6972265f2c2c n=2]</sub> |
| BITRE road fatalities, 500 rows — real data, CC BY | **1.59x** <sub>[ev:4c287ad3c0f3 n=2]</sub> | 1.47x <sub>[ev:437f72427b98 n=2]</sub> |

**What this changes for every future token claim.** Deleting whitespace alone is worth
1.35x <sub>[ev:a5d0cdbc349c n=2]</sub> to 1.80x <sub>[ev:dc91fb0462ec n=2]</sub> — a 26% <sub>[ev:a5d0cdbc349c /saving n=2]</sub> to
44% <sub>[ev:dc91fb0462ec /saving n=2]</sub> token reduction. So a figure quoted against pretty-printed JSON is mostly measuring
indentation. **The baseline for any token-optimisation claim in this project is minified JSON**, and a
technique that only matches it has demonstrated `json.dumps(separators=(",",":"))`.

YAML is worse than minified JSON on every payload measured. A less verbose markup does not get there on
its own.

The real dataset lands at 1.59x <sub>[ev:4c287ad3c0f3 n=2]</sub>, inside the synthetic range, so the generated shapes are not flattering
the result.

**Caveat, which travels with the number:** input token count only. No model was called, so this says
nothing about accuracy — a format that halves the tokens and halves the accuracy is worse, not better.

**Not measured, and not approximated.** Anthropic's tokeniser is not public and counting requires an
API call; Google's likewise. Neither is substituted with `cl100k_base`, because a fabricated Claude
figure for the provider this project sends most of its traffic to would be worse than a gap.

**TOON itself is not measured.** No faithful encoder is available here: the methodology specifies the
`toon-format/toon` implementation, no package is installed, and loke's own encoder is toke and needs the
compiler. An encoder written from the format's description would measure something of this harness's
own invention under TOON's name. So the withdrawn TOON savings figure (see "Withdrawn figures" below)
stays withdrawn.

Reproduce:

```
python3 benchmarks/toon/run.py --self-test
python3 benchmarks/toon/run.py
```

Harness and full method: [`benchmarks/toon/README.md`](../benchmarks/toon/README.md). Payload checksums
are verified on every run.

**Where the figures come from (VM1.3a).** Each figure above cites, by digest, the row it was read from in
`benchmarks/evidence/ledger.jsonl`, the committed ledger `scripts/check_figure_evidence.py` resolves
in the quality gate. The fourteen rows are the ones `run.py --record` wrote on 2026-09-20 at toke
`8a9aafe`, ooke `b663797`, loke `f13bfa7`, copied verbatim. N is 2 because each ratio is the
geometric mean over two tokenisers. Token counts are deterministic, so one run is the measurement
(VM1.3); re-run on 2026-09-28 at toke `0b0bc4e`, the harness printed the same ratio for all fourteen.
**Corrected 2026-09-28:** the YAML ratio for 1000 uniform rows was published one hundredth too
high, rounded up from a recorded 1.4946. The check found the rounding error the first time it ran.

### Regex detector throughput, against F3.1's 10MB/s target — 2026-09-24

**Evidence: legacy, unverified.** No row for it is in the ledger, and the table prints the median
and range of five runs where the result sink recorded their mean with a percentile-bootstrap
interval (before VM1.3), so no recorded row matches the figures as printed.

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

**Evidence: legacy, unverified.** Its rows (loke `0d29b5e`, recorded 2026-09-26 UTC) survive only in
the measuring machine's ignored `benchmarks/results/` directory, and they record the mean with a
percentile-bootstrap interval, which `result.validate` now refuses for a repeated measurement
(VM1.3). The table prints median and range. It can be cited only once re-measured with a BCa
interval.

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

### Privacy harness over the request path, template × detector type — 2026-10-01

**Evidence: verified.** The three rows were recorded by `scripts/smoke_privacy_harness.sh` against
the loke binary built from `e273c9c4` (the F3.9a/F3.9b fix) with toke `86c432da` (ooke `3cc4998`).
Counts over fixed inputs with a recording stand-in and no model, so each is one deterministic
observation and is stated as a count, not as a rate. They replace the first, 60-cell run's rows
(`6a8ab4a7`, before RG1.7's three detector types and before the fix), which recorded the guardian
reaching the model in none of its cells; those rows stay in the ledger.

**What this is.** The coverage figure F3.9 once stated was never measured, and is withdrawn. What is
measured is this: every built-in template in `core.privacy.template` crossed with every detector
type `core.privacy.regex` emits, plus a PERSON for the NER layer and a control with no identifier.
Each cell is one `POST /api/pipeline` to the built binary, judged only on what
`scripts/lib/http_recorder.py`, standing in for Ollama, received: no raw identifier in any request
except the local NER layer's own, a placeholder of the right type where the value was, the
reply restored byte for byte, and the guardian at the start of the `system` the model was sent.
RESTRICTED cells are first held for approval (GA5.26), and the harness checks nothing was sent
while held. Outside the matrix, one cell per detector case puts the identifier in the caller's
`system_prompt` and none in the text (F3.9b): it must reach no request but the NER layer's, and the
model's `system` must carry the guardian and then a placeholder of its type.

| Measure | Count |
|---|---|
| Template × case cells passing every assertion (5 templates × 15 cases) | **75** <sub>[ev:d243a891829e n=75]</sub> |
| Dispatched template × case cells in which the guardian system prompt reached the model | **75** <sub>[ev:33611e731fce n=75]</sub> |
| System-prompt cells passing every assertion (one per case with an identifier) | **14** <sub>[ev:ae53a33795eb n=14]</sub> |

**Mutation-checked.** On the first run: with `page.api.pipeline.restoretext` returning its input
unchanged, every cell holding an identifier failed (the controls passed); with `toollama` sending
the original text in place of the anonymised one, the same cells failed on the leak and placeholder
assertions. On the fix (F3.9a, F3.9b): with `core.privacy.systemprompt` building the final system
prompt from the raw caller system prompt, every system-prompt cell failed; with the guardian
dropped from the Ollama payload and the Anthropic body, no cell of either kind passed. Each mutant
restored and checked with `cmp`.

**Caveats:**

- **The guardian row says it was sent, not that it works.** It is judged by the guardian's version
  marker at the start of the system prompt the stand-in received. Whether a model obeys it is
  unmeasured (AD1.5).
- **Recorded before RG1.7a merged.** The harness now also carries cases for `au_crn`, `passport`,
  `driver_licence` and `au_super_member` (RG1.7a), and for `uk_nhs_number`, `uk_nino`,
  `uk_sort_code`, `uk_driving_licence` and `sg_nric` (RG1.7a, completed 2026-10-01): 5 × 24 = 120
  matrix cells, run by the gate. The counts above are the 75-cell run and have not been re-recorded
  for the 120.
- **Not a recall figure.** Each type is exercised with one value the regex layer is known to
  detect (`tests/unit/privacy/test_regex.tk`). Recall is measured above, on the corpus.
- **One route.** The browser `/api/pipeline` to a local model. The Anthropic route cannot be driven
  through the binary (its endpoint is the real provider); `tests/integration/test_system_prompt_disclosure.tk`
  drives its own `toanthropicat` against a recorder instead. The CLI paths are not covered. The
  no-custody dispatch has carried the guardian since F3.9c, and the harness now runs six no-custody
  cells after the matrix (pass/fail assertions, not a published count); the figures above do not
  include them.
- The templates are rendered by the harness by the module's own rule; no route on the request path
  renders a template.

Reproduce (holds the fixed-port lock; it takes 11434):

```sh
scripts/build_loke.sh
HARNESS_RECORD=benchmarks/results/f39.jsonl scripts/smoke_privacy_harness.sh
```

---

## Status: no *performance* figure is published

**Evidence: not a measurement.** Summarises the sections above and publishes no figure of its own;
the rate named is the bound the F3.1b figures fall under.

The measurements are: detection recall for the regex layer and, since 2026-09-28, per detection layer (AD1.3), the serialisation baselines, and the
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

**Evidence: withdrawn.** Every figure in this section is listed so that nobody reinstates it; none
is a measurement.

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

**Evidence: not a measurement.** The table is provider list prices, read from the provider's pricing
page, which are inputs to loke's cost tables and not measured by this project.

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
3. A figure that can vary between runs (anything timed, or produced by a model) is reported from at
   least two kept runs, the first discarded as warm-up, with a BCa confidence interval — VM1.3, and
   `benchmarks/lib/result.py` refuses anything else. A deterministic figure (a count, or recall over a
   fixed corpus) may be a single observation, reported with its N and stated as one, never as a rate.
4. The caveat travels with the number, everywhere the number appears.
5. This file is updated first. Other pages cite it; they do not restate it independently.
6. **The figure cites its row (VM1.3a).** Promote the rows it was read from into the committed,
   append-only ledger with `python3 -m benchmarks.lib.evidence promote <results file> --metric …`,
   which prints each row's citation, and put that citation after the number:
   `1.80x <sub>[ev:<digest> n=<N>]</sub>`, `/ci` after an interval (required for a repeated
   measurement), `/saving` for a ratio printed as a percentage saved. Open the section with
   `**Evidence: verified.**` and name the rows' toke and loke commits in it; its heading's date is
   the rows' recording date. `scripts/check_figure_evidence.py`, in the quality gate, resolves every
   citation, re-validates the row, and fails on a figure with no citation or one that differs from
   its row at the precision printed. `legacy, unverified` is only for sections published on or
   before 2026-09-28.
