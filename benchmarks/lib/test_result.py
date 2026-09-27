# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the BCa interval and the repetition rule in benchmarks/lib/result.py (VM1.3).

Run: python3 -m unittest benchmarks.lib.test_result   (the quality gate runs it)

The reference is scipy.stats.bootstrap(method='BCa'). scipy accepts a bootstrap distribution
through `bootstrap_result` with n_resamples=0, so it can be handed exactly the distribution
this module built, and the two must then agree to rounding. Where scipy is installed that
comparison runs live. The same comparisons are also frozen below, as the values scipy 1.17.1
(numpy 2.4.4) returned on 2026-09-28, so the check still bites on a machine without scipy.

The data are integers or dyadic fractions on purpose. Their sums are exact in binary, so the
estimate and every resample mean are the same float whether numpy or math.fsum adds them,
and the tie-counting in z0 cannot differ between the two implementations for that reason.
"""

from __future__ import annotations

import itertools
import math
import unittest

from benchmarks.lib import result as r

# name -> (values, scipy's BCa low, scipy's BCa high, label of the distribution)
REFERENCE = {
    "latency_ms_5": ([212.0, 198.0, 205.0, 341.0, 201.0],
                     202.06722722477704, 313.8, "exhaustive-3125"),
    "latency_ms_4": ([1750.0, 1622.0, 1618.0, 1904.0], 1621.0, 1865.5, "exhaustive-256"),
    "score_7": ([1.0, 0.75, 1.0, 0.5, 1.0, 1.0, 0.25],
                0.5357142857142857, 0.9642857142857143, "exhaustive-823543"),
    "mc_12": ([3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.0, 5.0, 35.0],
              3.5, 16.666666666666668, "10000-seed0"),
}

try:
    import numpy as np
    import scipy.stats as st
    from types import SimpleNamespace
    HAVE_SCIPY = True
except ImportError:  # pragma: no cover - depends on the machine
    HAVE_SCIPY = False


def close(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-12)


class BCaAgainstReference(unittest.TestCase):

    def test_frozen_scipy_values(self):
        for name, (values, lo, hi, label) in REFERENCE.items():
            with self.subTest(name=name):
                got_lo, got_hi, method = r.bca_ci(values)
                self.assertEqual(method, f"bca-bootstrap-{label}")
                self.assertTrue(close(got_lo, lo), f"{name} low {got_lo!r} != scipy {lo!r}")
                self.assertTrue(close(got_hi, hi), f"{name} high {got_hi!r} != scipy {hi!r}")

    @unittest.skipUnless(HAVE_SCIPY, "scipy is not installed; the frozen values still ran")
    def test_live_scipy_given_the_same_distribution(self):
        for name, (values, _, _, _) in REFERENCE.items():
            with self.subTest(name=name):
                dist, total, _ = r.bootstrap_distribution(values)
                expanded = np.repeat([v for v, _ in dist], [w for _, w in dist])
                self.assertEqual(len(expanded), total)
                ref = st.bootstrap(
                    (np.array(values),), np.mean, method="BCa", n_resamples=0,
                    bootstrap_result=SimpleNamespace(bootstrap_distribution=expanded),
                    confidence_level=0.95,
                ).confidence_interval
                lo, hi = r.bca_from_distribution(values, dist, total)
                self.assertTrue(close(lo, float(ref.low)), f"{name}: {lo!r} vs {float(ref.low)!r}")
                self.assertTrue(close(hi, float(ref.high)), f"{name}: {hi!r} vs {float(ref.high)!r}")

    def test_bca_is_not_the_percentile_interval(self):
        # On skewed runs the bias correction and acceleration move the interval. If they were
        # dropped this would be the percentile bootstrap, which is what VM1.3 replaced.
        values = REFERENCE["latency_ms_5"][0]
        dist, total, _ = r.bootstrap_distribution(values)
        pct_lo = r._quantile(dist, total, 0.025)
        pct_hi = r._quantile(dist, total, 0.975)
        lo, hi, _ = r.bca_ci(values)
        self.assertGreater(hi - pct_hi, 20.0, "BCa stretches the upper tail of right-skewed runs")
        self.assertGreater(lo, pct_lo)


class ExhaustiveDistribution(unittest.TestCase):

    def test_multisets_weighted_equal_the_full_enumeration(self):
        for values in ([5.0, 1.0, 2.0], [7.0, 7.0, 1.0, 3.0], [1.0, 2.0, 4.0, 8.0, 16.0]):
            n = len(values)
            with self.subTest(n=n):
                naive: dict[float, int] = {}
                for idx in itertools.product(range(n), repeat=n):
                    m = math.fsum(values[i] for i in idx) / n
                    naive[m] = naive.get(m, 0) + 1
                dist, total, label = r.bootstrap_distribution(values)
                self.assertEqual(total, n ** n)
                self.assertEqual(label, f"exhaustive-{n ** n}")
                self.assertEqual(dist, sorted(naive.items()))

    def test_quantile_matches_numpy_linear_on_the_expansion(self):
        dist = [(1.0, 2), (2.0, 1), (5.0, 3)]
        expanded = [1.0, 1.0, 2.0, 5.0, 5.0, 5.0]
        for q in (0.0, 0.1, 0.25, 0.5, 0.61, 0.9, 1.0):
            rank = q * (len(expanded) - 1)
            lo = math.floor(rank)
            hi = min(lo + 1, len(expanded) - 1)
            want = expanded[lo] + (rank - lo) * (expanded[hi] - expanded[lo])
            self.assertAlmostEqual(r._quantile(dist, 6, q), want, places=12)

    def test_identical_runs_give_a_point_and_say_so(self):
        lo, hi, method = r.bca_ci([4.0, 4.0, 4.0, 4.0])
        self.assertEqual((lo, hi), (4.0, 4.0))
        self.assertIn("degenerate", method)

    def test_one_run_has_no_interval(self):
        with self.assertRaises(ValueError):
            r.bca_ci([1.0])


class RepetitionRule(unittest.TestCase):

    base = dict(metric="recall", value=0.5, units="ratio", workload="w", n=10)

    def rejected(self, **kw) -> str:
        with self.assertRaises(r.ResultRejected) as cm:
            r.validate(r.Measurement(**{**self.base, **kw}))
        return str(cm.exception)

    def test_deterministic_single_measurement_is_accepted(self):
        r.validate(r.Measurement(**self.base))

    def test_model_or_clock_needs_repetition(self):
        self.assertIn("VM1.3", self.rejected(model="m", model_version="v"))
        self.assertIn("VM1.3", self.rejected(units="ms"))
        self.assertIn("VM1.3", self.rejected(units="MB/s (10^6 bytes)"))
        self.assertIn("VM1.3", self.rejected(metric="latency_mean", units="count"))
        self.assertIn("VM1.3", self.rejected(units="ms", runs=1))

    def test_repeated_measurement_needs_bca(self):
        msg = self.rejected(units="ms", runs=4, ci_low=0.4, ci_high=0.6,
                            ci_method="percentile-bootstrap-10000")
        self.assertIn("BCa", msg)

    def test_summarise_of_timed_runs_is_accepted_and_discards_warm_up(self):
        m = r.summarise([900.0, 212.0, 198.0, 205.0, 341.0, 201.0],
                        metric="latency_mean", units="ms", workload="w")
        r.validate(m)
        self.assertEqual(m.runs, 5)
        self.assertEqual(m.value, 231.4)
        self.assertEqual(m.ci_method, "bca-bootstrap-exhaustive-3125")
        self.assertTrue(close(m.ci_low, REFERENCE["latency_ms_5"][1]))
        self.assertTrue(close(m.ci_high, REFERENCE["latency_ms_5"][2]))


if __name__ == "__main__":
    unittest.main()
