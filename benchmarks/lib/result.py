"""Numeric result sink for loke measurements (story VM1.1).

Why this exists
---------------
`std.test` exposes three assertion functions over string comparison and cannot
record a number. A toke test can therefore prove a threshold was met, but it
cannot publish the value it measured. Until something can record values, no
figure this project quotes can be traced to a measurement — which is why
`docs/metrics-baseline.md` currently has an empty measured column.

Every result written through this module carries the provenance needed to
reproduce it: workload, tokenizer (or explicitly "bytes"), sample size, model
and its pinned version, seed, the toolchain commits from TOOLCHAIN.lock, the
container digest if running in one, and the date. A result missing any of those
is rejected rather than written, because an unreproducible number is worse than
no number: it will be quoted.

Results are append-only JSON Lines under `benchmarks/results/`, one object per
measurement. CI uploads the directory as an artefact.

Usage
-----
    from benchmarks.lib.result import Measurement, write

    m = Measurement(
        metric="tokens_per_task",
        value=1843.0,
        units="tokens",
        workload="dabench-257",
        arm="A-data-in-prompt",
        n=257,
        tokenizer="cl100k_base",
        model="claude-sonnet-4-20250514",
        seed=0,
    )
    write(m)

For a repeated measurement, collect the per-run values and use
`summarise()` to attach a BCa bootstrap confidence interval before writing.

Repetition (VM1.3)
------------------
A measurement that can differ between runs cannot be recorded from one run: anything with a
model, and anything timed. It needs `runs` of at least two and a BCa interval, which
`summarise()` supplies after discarding the warm-up run. A measurement computed exactly from
fixed inputs (a token count, recall over the committed corpus) gives the same number every
time, so repeating it adds nothing and it is recorded once.
"""

from __future__ import annotations

import itertools
import json
import math
import os
import pathlib
import platform
import random
import re
import subprocess
import sys
from statistics import NormalDist
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO / "benchmarks" / "results"
LOCK = REPO / "TOOLCHAIN.lock"

# A tokenizer name is required for any token-denominated metric. "bytes" is an
# acceptable explicit answer; silence is not.
_TOKEN_METRICS = ("token", "prompt_size", "compression")

# VM1.3: what makes a measurement vary between runs. A model's output does, and so does
# anything read off a clock. Units are matched whole ("ms", "s") or as a rate ("MB/s").
_TIMED_UNITS = ("ns", "us", "ms", "s", "seconds")
_TIMED_METRICS = ("latency", "throughput", "duration", "elapsed")

# Up to this many kept runs the bootstrap distribution is enumerated exactly (all n^n
# resamples, 823 543 at seven) rather than drawn at random. Past it, BOOTSTRAP_RESAMPLES
# random resamples, as the methodology specifies. core.eval.interval uses the same bound.
EXHAUSTIVE_MAX_RUNS = 7
BOOTSTRAP_RESAMPLES = 10_000


class ResultRejected(ValueError):
    """A measurement lacking the provenance needed to reproduce it."""


def _lockval(key: str) -> str | None:
    if not LOCK.is_file():
        return None
    m = re.search(rf"^{re.escape(key)}\s*=\s*(.+)$", LOCK.read_text(), re.M)
    return m.group(1).strip() if m else None


def _container_digest() -> str | None:
    """Identify the container image if we are running inside one."""
    for probe in ("/opt/toolchain-pin.txt",):
        p = pathlib.Path(probe)
        if p.is_file():
            return p.read_text().strip()
    if pathlib.Path("/.dockerenv").exists():
        return "docker:unidentified"
    return None


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


@dataclass
class Measurement:
    """One recorded number, with everything needed to reproduce it."""

    metric: str                 # e.g. "tokens_per_task", "recall", "asr"
    value: float
    units: str                  # e.g. "tokens", "ratio", "ms", "count"
    workload: str               # named workload, e.g. "dabench-257"
    n: int                      # sample size this value was computed over

    arm: str | None = None      # experiment arm, where there is one
    tokenizer: str | None = None            # or the literal "bytes"
    model: str | None = None
    model_version: str | None = None
    seed: int | None = None

    # Interval, when the value is a summary over repeated runs.
    ci_low: float | None = None
    ci_high: float | None = None
    ci_method: str | None = None
    runs: int | None = None

    notes: str | None = None
    # A caveat that must travel with the number wherever it is quoted.
    caveat: str | None = None

    # Filled automatically.
    recorded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    toke_commit: str | None = field(default_factory=lambda: _lockval("toke_commit"))
    ooke_commit: str | None = field(default_factory=lambda: _lockval("ooke_commit"))
    loke_commit: str | None = field(default_factory=_git_commit)
    container: str | None = field(default_factory=_container_digest)
    host_platform: str = field(default_factory=lambda: f"{platform.system()}/{platform.machine()}")


def validate(m: Measurement) -> None:
    """Reject a measurement that could not be reproduced or interpreted."""
    problems: list[str] = []

    if not m.metric:
        problems.append("metric is required")
    if not m.units:
        problems.append("units are required — a bare number is uninterpretable")
    if not m.workload:
        problems.append("workload is required — a figure without its workload is not a measurement")
    if m.n is None or m.n < 1:
        problems.append("n is required and must be at least 1")

    if any(t in m.metric.lower() for t in _TOKEN_METRICS) and not m.tokenizer:
        problems.append(
            f"metric '{m.metric}' is token-denominated, so tokenizer is required "
            "(use the literal 'bytes' if the measurement really is byte-based)"
        )

    if m.model and not m.model_version:
        problems.append(
            "model_version is required whenever model is set — model behaviour changes "
            "between versions and an unpinned result cannot be reproduced"
        )

    if (m.ci_low is None) != (m.ci_high is None):
        problems.append("ci_low and ci_high must be given together")
    if m.ci_low is not None or m.ci_high is not None:
        if m.ci_method is None:
            problems.append("ci_method is required when an interval is given")
        # Only comparable once both bounds are present; the missing-bound case
        # is already reported above.
        if m.ci_low is not None and m.ci_high is not None:
            if not (m.ci_low <= m.value <= m.ci_high):
                problems.append(
                    f"value {m.value} lies outside its interval [{m.ci_low}, {m.ci_high}]"
                )
    if m.runs is not None and m.runs > 1 and m.ci_low is None:
        problems.append(
            f"{m.runs} runs were recorded but no interval — a repeated measurement "
            "must report its spread"
        )
    if m.runs is not None and m.runs > 1 and m.ci_method is not None \
            and not m.ci_method.startswith("bca-"):
        problems.append(
            f"the interval is '{m.ci_method}', and a repeated measurement is reported with a "
            "BCa bootstrap interval (docs/research/toon-benchmark-methodology.md, 5.2); "
            "use summarise() or bca_ci()"
        )
    why = needs_repetition(m)
    if why and (m.runs is None or m.runs < 2):
        problems.append(
            f"this measurement {why}, so it varies between runs and one run is not a "
            "result (VM1.3): repeat it, discard the warm-up, and record the runs and "
            "their BCa interval with summarise()"
        )

    if problems:
        raise ResultRejected(
            f"measurement '{m.metric}' rejected:\n  - " + "\n  - ".join(problems)
        )


def needs_repetition(m: Measurement) -> str:
    """Why this measurement can differ between runs, or "" when it cannot.

    A figure computed exactly from fixed inputs, such as a token count or recall over the
    committed corpus, is the same on every run. One that depends on a model's output, or is
    read off a clock, is not, and VM1.3 forbids publishing it from a single run.
    """
    if m.model:
        return f"depends on the output of model '{m.model}'"
    units = (m.units or "").strip().lower()
    if units.split(" ")[0] in _TIMED_UNITS or "/s" in units:
        return f"is timed (units '{m.units}')"
    metric = (m.metric or "").lower()
    if any(t in metric for t in _TIMED_METRICS):
        return f"is timed (metric '{m.metric}')"
    return ""


def _mean(xs) -> float:
    # fsum rounds once, at the end, so a resample's mean does not depend on the order its
    # values were drawn in, and two resamples with the same values compare equal.
    xs = list(xs)
    return math.fsum(xs) / len(xs)


def bootstrap_distribution(
    values: list[float], *, iterations: int = BOOTSTRAP_RESAMPLES, seed: int = 0,
) -> tuple[list[tuple[float, int]], int, str]:
    """The bootstrap distribution of the mean, as sorted (value, weight) pairs.

    Returns the pairs, their total weight B, and a label. Up to EXHAUSTIVE_MAX_RUNS values
    it is the complete distribution: every one of the n^n equally likely resamples, grouped
    by the multiset of indices drawn and weighted by its multinomial count. That is the
    distribution a random bootstrap only estimates, so no seed is involved. Past that,
    `iterations` resamples are drawn with a seeded generator, each of weight one.
    """
    n = len(values)
    if n < 2:
        raise ValueError("need at least two runs to bootstrap an interval")
    counts: dict[float, int] = {}
    if n <= EXHAUSTIVE_MAX_RUNS:
        nfact = math.factorial(n)
        for combo in itertools.combinations_with_replacement(range(n), n):
            weight = nfact
            for _, group in itertools.groupby(combo):
                weight //= math.factorial(len(list(group)))
            v = _mean(values[i] for i in combo)
            counts[v] = counts.get(v, 0) + weight
        total, label = n ** n, f"exhaustive-{n ** n}"
    else:
        rng = random.Random(seed)
        for _ in range(iterations):
            v = _mean(rng.choices(values, k=n))
            counts[v] = counts.get(v, 0) + 1
        total, label = iterations, f"{iterations}-seed{seed}"
    return sorted(counts.items()), total, label


def _quantile(dist: list[tuple[float, int]], total: int, q: float) -> float:
    """numpy's default ("linear") quantile of the expanded distribution, without expanding it."""
    rank = q * (total - 1)
    lo = max(0, min(total - 1, math.floor(rank)))
    hi = min(lo + 1, total - 1)
    frac = rank - lo

    def at(k: int) -> float:
        seen = 0
        for v, w in dist:
            seen += w
            if k < seen:
                return v
        return dist[-1][0]

    a = at(lo)
    return a + frac * (at(hi) - a)


def bca_from_distribution(
    values: list[float], dist: list[tuple[float, int]], total: int, confidence: float = 0.95,
) -> tuple[float, float]:
    """BCa bounds for the mean, given its bootstrap distribution.

    Efron and Tibshirani, An Introduction to the Bootstrap (1993), 14.3: z0 from the share
    of the bootstrap distribution below the estimate (a tie counted half, as scipy counts
    it), the acceleration from the jackknife, and the two percentiles those move the nominal
    ones to. benchmarks/lib/test_result.py checks this against scipy.stats.bootstrap with
    method='BCa' handed the same distribution.
    """
    n = len(values)
    theta = _mean(values)
    below = sum(w for v, w in dist if v < theta)
    atmost = sum(w for v, w in dist if v <= theta)
    norm = NormalDist()
    z0 = norm.inv_cdf((below + atmost) / (2 * total))

    jack = [_mean(values[:i] + values[i + 1:]) for i in range(n)]
    jbar = _mean(jack)
    u = [(n - 1) * (jbar - j) for j in jack]
    num = math.fsum(x ** 3 for x in u) / n ** 3
    den = math.fsum(x ** 2 for x in u) / n ** 2
    accel = num / (6 * den ** 1.5)

    alpha = (1.0 - confidence) / 2.0
    bounds = []
    for z in (norm.inv_cdf(alpha), norm.inv_cdf(1.0 - alpha)):
        shifted = z0 + z
        bounds.append(_quantile(dist, total, norm.cdf(z0 + shifted / (1 - accel * shifted))))
    return bounds[0], bounds[1]


def bca_ci(
    values: list[float],
    confidence: float = 0.95,
    iterations: int = BOOTSTRAP_RESAMPLES,
    seed: int = 0,
) -> tuple[float, float, str]:
    """Bias-corrected and accelerated bootstrap interval of the mean over repeated runs.

    The interval `docs/research/toon-benchmark-methodology.md` specifies. When every run gave
    the same value the bootstrap distribution is one point and the acceleration is 0/0, so
    BCa is undefined; the interval is then that point, and the label says so.
    """
    if len(values) < 2:
        raise ValueError("need at least two runs to bootstrap an interval")
    if all(v == values[0] for v in values):
        return values[0], values[0], "bca-bootstrap-degenerate-identical-runs"
    dist, total, label = bootstrap_distribution(values, iterations=iterations, seed=seed)
    lo, hi = bca_from_distribution(values, dist, total, confidence)
    return lo, hi, f"bca-bootstrap-{label}"


def summarise(values: list[float], *, discard_first: bool = True, **fields) -> Measurement:
    """Build a Measurement from repeated runs, with warm-up discarded.

    The methodology document specifies discarding the first run as warm-up.
    That is the default here; pass discard_first=False to override.
    """
    runs = list(values)
    if discard_first and len(runs) > 1:
        runs = runs[1:]
    if not runs:
        raise ValueError("no runs left after discarding warm-up")
    m = Measurement(value=_mean(runs), n=fields.pop("n", len(runs)), runs=len(runs), **fields)
    if len(runs) >= 2:
        m.ci_low, m.ci_high, m.ci_method = bca_ci(runs)
    return m


def write(m: Measurement, *, path: pathlib.Path | None = None) -> pathlib.Path:
    """Validate and append one measurement. Returns the file written to."""
    validate(m)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    target = path or RESULTS_DIR / f"{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
    with target.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(m), sort_keys=True) + "\n")
    return target


def read_all(directory: pathlib.Path | None = None) -> list[dict]:
    """Read every recorded measurement, newest file last."""
    directory = directory or RESULTS_DIR
    out: list[dict] = []
    if not directory.is_dir():
        return out
    for f in sorted(directory.glob("*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _self_test() -> int:
    """Exercise the guards. Run: python3 -m benchmarks.lib.result"""
    failures = 0

    def expect_rejected(label: str, **kw) -> None:
        nonlocal failures
        try:
            validate(Measurement(**kw))
        except ResultRejected:
            print(f"ok       rejected: {label}")
        else:
            print(f"FAIL     accepted but should not have: {label}")
            failures += 1

    def expect_accepted(label: str, **kw) -> None:
        nonlocal failures
        try:
            validate(Measurement(**kw))
            print(f"ok       accepted: {label}")
        except ResultRejected as e:
            print(f"FAIL     rejected but should not have: {label}\n{e}")
            failures += 1

    base = dict(metric="recall", value=0.5, units="ratio", workload="w", n=10)

    expect_accepted("minimal valid", **base)
    expect_rejected("no units", **{**base, "units": ""})
    expect_rejected("no workload", **{**base, "workload": ""})
    expect_rejected("n below one", **{**base, "n": 0})
    expect_rejected("token metric without tokenizer",
                    **{**base, "metric": "tokens_per_task"})
    expect_accepted("token metric with explicit bytes",
                   **{**base, "metric": "tokens_per_task", "tokenizer": "bytes"})
    expect_rejected("model without version", **{**base, "model": "some-model"})
    expect_rejected("half an interval", **{**base, "ci_low": 0.4})
    expect_rejected("value outside interval",
                    **{**base, "ci_low": 0.6, "ci_high": 0.8, "ci_method": "x"})
    expect_rejected("repeated runs without spread", **{**base, "runs": 5})

    expect_rejected("a model measured once",
                    **{**base, "model": "m", "model_version": "v1"})
    expect_rejected("a timing measured once", **{**base, "metric": "latency_mean", "units": "ms"})
    expect_rejected("a rate measured once", **{**base, "units": "MB/s (10^6 bytes)"})
    expect_rejected("a repeated measurement with a percentile interval",
                    **{**base, "runs": 5, "ci_low": 0.4, "ci_high": 0.6,
                       "ci_method": "percentile-bootstrap-10000"})
    expect_accepted("a repeated timing with a BCa interval",
                    **{**base, "units": "ms", "runs": 5, "ci_low": 0.4, "ci_high": 0.6,
                       "ci_method": "bca-bootstrap-exhaustive-3125"})

    lo, hi, method = bca_ci([1.0, 2.0, 3.0, 4.0, 5.0])
    if lo < 3.0 < hi and method.startswith("bca-bootstrap"):
        print(f"ok       BCa interval brackets the mean [{lo:.2f}, {hi:.2f}]")
    else:
        print(f"FAIL     BCa interval looks wrong [{lo}, {hi}]")
        failures += 1

    s = summarise([99.0, 2.0, 2.0, 2.0, 2.0], metric="latency", units="ms",
                  workload="w", n=4)
    if abs(s.value - 2.0) < 1e-9:
        print("ok       warm-up run discarded")
    else:
        print(f"FAIL     warm-up not discarded, mean is {s.value}")
        failures += 1

    print(f"\n{'PASS' if failures == 0 else 'FAIL'}: {failures} failure(s)")
    return failures


if __name__ == "__main__":
    sys.exit(_self_test())
