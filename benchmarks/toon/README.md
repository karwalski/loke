# Token-Optimisation Baselines

**Story:** VM1.7
**Methodology:** [`docs/research/toon-benchmark-methodology.md`](../../docs/research/toon-benchmark-methodology.md)
**Workload:** `toon-baselines-v1`
**First run:** 2026-09-20

```
python3 benchmarks/toon/run.py --self-test   # 7 guard groups on the instrument
python3 benchmarks/toon/run.py               # measure and print
python3 benchmarks/toon/run.py --record      # write through benchmarks/lib/result.py
```

## What this measures

Input token counts for the same data in three serialisation formats, counted with
real provider tokenisers. No model is called.

That is a deliberately narrow slice of the methodology, and the slice that costs
nothing. It is also the slice that fixes a specific defect:
`packages/core/src/optimiser/toon.tk:285` computes savings as
`str.len(json) / str.len(toon)` — a ratio of **character counts**. A character
saving is not a token saving, they can disagree in either direction, and only the
token count changes what a provider charges or what fits in a context window.

## The finding

The headline is not about any compression technique. It is about the baseline.

| Payload | Minified JSON | YAML |
|---|---|---|
| uniform tabular, 100 rows | **1.80x** | 1.50x |
| uniform tabular, 1000 rows | **1.80x** | 1.50x |
| nested, 100 | **1.78x** | 1.42x |
| mixed types, 100 | **1.66x** | 1.38x |
| wide, 40 columns | **1.35x** | 1.21x |
| sparse, 70% null | **1.54x** | 1.40x |
| **BITRE road fatalities, 500 (real, CC BY)** | **1.59x** | 1.47x |

Ratios are `tokens(indented JSON) / tokens(format)`, geometric mean over
`cl100k_base` and `o200k_base`. Above 1.0 is a saving.

Two things follow.

**Deleting whitespace gets 1.35x to 1.80x — a 26% to 44% token reduction — on its
own.** So a compression figure quoted against *pretty-printed* JSON is mostly
measuring indentation. Any claim this project makes about a token-optimisation
technique has to beat `b2_json_min`, not `b1_json`, or it has demonstrated
`json.dumps(separators=(",",":"))`.

**YAML is worse than minified JSON in every single payload.** A less verbose markup
language does not get there by itself.

The real dataset lands at 1.59x, inside the synthetic range, so the generated
shapes are not flattering the result. That cross-check is why it is in the set.

## What this does not measure

**Accuracy.** A format that halves the tokens and halves the accuracy is worse, not
better, and nothing here can tell you which happened. That caveat is attached to
every recorded figure and travels with it.

The accuracy half needs LLM-as-judge calls and repeated frontier-model runs across
every configuration — real recurring spend, and a decision nobody has taken. So it
is unstarted rather than half-started.

## Formats not implemented, and why

| Format | Why |
|---|---|
| **F4 TOON** | No faithful encoder is available. The methodology specifies the `toon-format/toon` implementation; no Python or JS package is installed here, and loke's own encoder is `packages/core/src/optimiser/toon.tk` and needs the compiler. **An encoder written from the format's description would measure a format of this harness's invention under TOON's name**, which is worse than reporting no number |
| F5 LLMLingua | Needs the sidecar and its XLM-RoBERTa weights, which this repository does not bundle (`claims.md` C2) |
| F6 TOON + LLMLingua | Composition of two unavailable formats |
| F7 toke | Needs the compiler |

So this harness currently establishes the **baseline** that TOON will have to beat,
and cannot yet say whether it does.

## Tokenisers

| Provider | Status |
|---|---|
| OpenAI `cl100k_base`, `o200k_base` | Measured, offline, exact |
| Llama / Qwen / Mistral | Measured **if** the tokeniser is already cached locally; skipped otherwise, never downloaded mid-run |
| **Anthropic** | **Not measured.** The Claude tokeniser is not public; counting needs an API call. Not approximated with `cl100k_base` — that would be a fabricated Claude figure for the provider this project sends most of its traffic to |
| **Google** | Not measured, same reason |

Cross-tokeniser figures use the geometric mean, per methodology §2.3.

## Payloads

Seven, checksummed in `datasets/checksums.sha256` and verified on every run: a
token count describes a specific sequence of bytes, and if the bytes change the
figure no longer describes anything.

Six are generated deterministically from seed `20260920`. The data *shapes* in §1.2
are structural properties, and structure is what a serialisation format responds
to; real content would add licence obligations and nothing to the measurement.

The seventh is real — BITRE Australian Road Deaths Database, CC BY, attributed,
already fetched with a verified licence by `scripts/fetch_opendata.py`. It is the
cross-check that the synthetic shapes are not misleading.

Every payload declares a licence and `build()` refuses one outside
`{generated, cc-by, cc-by-4.0, cc0, public-domain}`. A benchmark input committed to
this repository is redistribution, so the same rule as the demo datasets applies.

Every format is round-trip checked per payload. A lossy format shows the model
different data, so its token count is not comparable to the baseline and the
pairing is excluded rather than warned about. YAML type coercion — an unquoted `no`
becoming `False`, a version-like string becoming a float — is a real hazard here,
which is why it is checked per payload rather than once.

## Reproducing

Deterministic and offline. The self-test asserts it, along with the property that
matters most: minified JSON must use fewer tokens than indented JSON. If that ever
fails, the tokeniser or the serialiser is wrong and every ratio above is suspect.
