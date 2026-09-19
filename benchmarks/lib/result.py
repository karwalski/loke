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
`summarise()` to attach a bootstrap confidence interval before writing.
"""

from __future__ import annotations

import json
import os
import pathlib
import platform
import random
import re
import statistics
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = REPO / "benchmarks" / "results"
LOCK = REPO / "TOOLCHAIN.lock"

# A tokenizer name is required for any token-denominated metric. "bytes" is an
# acceptable explicit answer; silence is not.
_TOKEN_METRICS = ("token", "prompt_size", "compression")


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

    if problems:
        raise ResultRejected(
            f"measurement '{m.metric}' rejected:\n  - " + "\n  - ".join(problems)
        )


def bootstrap_ci(
    values: list[float],
    confidence: float = 0.95,
    iterations: int = 10_000,
    seed: int = 0,
) -> tuple[float, float, str]:
    """Percentile bootstrap interval over repeated runs.

    `docs/research/toon-benchmark-methodology.md` specifies BCa intervals. This
    is the plain percentile bootstrap: adequate for symmetric statistics, and
    honestly labelled as what it is so nobody reports it as BCa. Replace with
    BCa when the bias-correction and acceleration terms are implemented.
    """
    if len(values) < 2:
        raise ValueError("need at least two runs to bootstrap an interval")
    rng = random.Random(seed)
    n = len(values)
    means = []
    for _ in range(iterations):
        means.append(statistics.fmean(rng.choices(values, k=n)))
    means.sort()
    lo_i = int((1.0 - confidence) / 2.0 * iterations)
    hi_i = int((1.0 + confidence) / 2.0 * iterations) - 1
    return means[lo_i], means[hi_i], f"percentile-bootstrap-{iterations}"


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
    mean = statistics.fmean(runs)
    m = Measurement(value=mean, n=fields.pop("n", len(runs)), runs=len(runs), **fields)
    if len(runs) >= 2:
        m.ci_low, m.ci_high, m.ci_method = bootstrap_ci(runs)
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

    lo, hi, method = bootstrap_ci([1.0, 2.0, 3.0, 4.0, 5.0])
    if lo < 3.0 < hi and method.startswith("percentile-bootstrap"):
        print(f"ok       bootstrap interval brackets the mean [{lo:.2f}, {hi:.2f}]")
    else:
        print(f"FAIL     bootstrap interval looks wrong [{lo}, {hi}]")
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
