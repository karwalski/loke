# Benchmarks

Measurement harnesses and their recorded results.

**Nothing here has been run yet.** The apparatus is being built first, deliberately, because until a
measurement can be recorded reproducibly there is no point taking one — it will be quoted and it will
not be traceable. `docs/metrics-baseline.md` is the only place figures are published, and its measured
column is currently empty. That is the honest state.

## Why this directory exists rather than tests

toke's `std.test` exposes three assertion functions over string comparison. A test can therefore assert
that a value cleared a threshold, but it cannot record the value. Every figure this project has ever
quoted was written by hand into prose. This directory is the fix: harnesses write numbers, with
provenance, to `results/`.

## The contract

`lib/result.py` refuses to record a measurement that could not be reproduced or interpreted. It
rejects, rather than warns:

| Missing | Why it is fatal |
|---|---|
| `units` | A bare number is uninterpretable |
| `workload` | A figure without its workload is not a measurement |
| `n` | Sample size determines whether the number means anything |
| `tokenizer` on a token-denominated metric | Token counts differ by tokenizer; `"bytes"` is an acceptable explicit answer, silence is not |
| `model_version` when `model` is set | Model behaviour changes between versions |
| An interval, when more than one run was recorded | A repeated measurement must report its spread |

Filled automatically: the toke and ooke commits from `TOOLCHAIN.lock`, the loke commit, the container
identity if running in one, the host platform, and the timestamp.

A `caveat` field exists because the caveat has to travel with the number wherever it is quoted. Use it.

## Reproducibility

`Dockerfile` at the repository root builds a pinned environment from `TOOLCHAIN.lock`. Results recorded
inside it carry the container identity.

Results measured on linux/amd64 are **not** comparable with results measured on Apple Silicon. Anything
concerning local inference must state which it was — see epic LC1 for what a non-Apple-Silicon
environment cannot validate at all.

## Running

```sh
python3 -m benchmarks.lib.result     # self-test the guards
docker build -t loke-bench .         # pinned environment
```

## Layout

```
benchmarks/
  lib/result.py     numeric result sink and its guards (VM1.1)
  results/          recorded measurements, JSON Lines, git-ignored
  toon/             token-optimisation harness — not yet implemented (VM1.7)
```

`toon/` is specified in full in `docs/research/toon-benchmark-methodology.md`, which is already at
publishable standard: named baselines, twelve task types, four data shapes, a licensed dataset table,
N with warm-up discard, bootstrap intervals, Wilcoxon signed-rank, multiple-comparison correction and
checksummed snapshots. Implementing it is VM1.7. It does not need redesigning.

## Interval method

`bootstrap_ci` is a plain percentile bootstrap and is labelled as such. The methodology document
specifies BCa. The difference is real for skewed statistics, so the function reports what it actually
is rather than claiming BCa — replace it when the bias-correction and acceleration terms are
implemented.
