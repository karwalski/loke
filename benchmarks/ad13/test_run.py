# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for benchmarks/ad13/run.py --record (story VM1.3b).

Run: python3 -m unittest benchmarks.ad13.test_run   (the quality gate runs it)

`--record` once imported `bootstrap_ci`, which VM1.3 removed, so a recording run crashed after
spending its model runs and recorded nothing; and it widened each interval to contain the mean.
These tests run `main(["--record", ...])` end to end with the local services and the toke test
replaced by stubs that print AD13 lines, and read back what was written: every row carries the
BCa interval of the kept runs exactly as `result.bca_ci` computes it, the warm-up run is not in
it, and a row whose mean falls outside its interval is reported and not recorded.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import tempfile
import unittest
from unittest import mock

from benchmarks.lib import result

REPO = result.REPO
_spec = importlib.util.spec_from_file_location("ad13_run", REPO / "benchmarks" / "ad13" / "run.py")
ad13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ad13)

# Per run: (regex+ner direct recall %, ner false positives added). Run 1 is the warm-up and
# is an outlier on purpose, so a warm-up that leaks into a row moves its value.
RUNS = [(50.00, 90), (93.24, 43), (94.59, 47), (93.24, 45)]


def _stub_output(direct: float, fp_added: int) -> str:
    lines = [
        "AD13 texts=74 ner=http://127.0.0.1:1 ner_model=m pf=http://127.0.0.1:2 ner_failures=0 pf_failures=0",
        "AD13 layer=regex recall=79.25% matched=84 labelled=106 direct_recall=70.27% direct_matched=52 "
        "direct_labelled=74 precision=89.36% detections=94 false_positives=10",
        f"AD13 layer=regex+ner recall=95.28% matched=101 labelled=106 direct_recall={direct:.2f}% "
        f"direct_matched=69 direct_labelled=74 precision=66.47% detections=150 false_positives={fp_added + 10}",
        f"AD13 marginal=ner recall_gain=17 direct_gain=17 fp_added={fp_added} labelled=106",
        "AD13 layer=pf recall=88.68% matched=94 labelled=106 direct_recall=83.78% direct_matched=62 "
        "direct_labelled=74 precision=92.44% detections=119 false_positives=18",
        "AD13 marginal=pf recall_gain=18 direct_gain=18 fp_added=6 labelled=106",
        f"PASS         {ad13.TEST}",
    ]
    return "\n".join(lines) + "\n"


class _Proc:
    pid = 0

    def poll(self):
        return 0


class RecordEndToEnd(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        tmp = pathlib.Path(self.tmp.name)
        snaps = tmp / "snapshots"
        (snaps / "rev0123").mkdir(parents=True)
        self.results = tmp / "results"
        outputs = iter(_stub_output(d, f) for d, f in RUNS)
        self.patches = [
            mock.patch.object(ad13, "run_test", lambda env: next(outputs)),
            mock.patch.object(ad13, "start", lambda *a, **k: _Proc()),
            mock.patch.object(ad13, "stop", lambda p: None),
            mock.patch.object(ad13, "wait_for", lambda *a, **k: True),
            mock.patch.object(ad13, "model_digest", lambda *a: "357c53fb659c"),
            mock.patch.object(ad13, "post", lambda *a, **k: "{}"),
            mock.patch.object(ad13, "PF_SNAPSHOTS", snaps),
            mock.patch.object(result, "RESULTS_DIR", self.results),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def _main(self):
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
            rc = ad13.main(["--record", "--runs", str(len(RUNS)), "--ner-model", "m"])
        return rc, err.getvalue(), result.read_all(self.results)

    def _row(self, rows, metric, arm):
        found = [r for r in rows if r["metric"] == metric and r["arm"] == arm]
        self.assertEqual(len(found), 1, f"{metric} {arm}: {len(found)} rows")
        return found[0]

    def test_records_every_row_with_its_bca_interval(self):
        rc, err, rows = self._main()
        self.assertEqual(rc, 0, err)
        # 3 layers x 3 metrics, 2 marginals x 3 metrics.
        self.assertEqual(len(rows), 15)
        for r in rows:
            result.validate(result.Measurement(**r))
            self.assertEqual(r["runs"], 3, r["metric"])
            self.assertTrue(r["ci_method"].startswith("bca-bootstrap"), r["ci_method"])

        kept = [d / 100 for d, _ in RUNS[1:]]
        row = self._row(rows, "pii_recall_direct_identifiers", "layers:regex+ner")
        lo, hi, meth = result.bca_ci(kept)
        self.assertEqual(meth, "bca-bootstrap-exhaustive-27")
        self.assertEqual((row["ci_low"], row["ci_high"], row["ci_method"]), (lo, hi, meth))
        self.assertAlmostEqual(row["value"], sum(kept) / 3, places=12)
        self.assertEqual(row["n"], 74)
        self.assertEqual(row["model"], "ollama:m")
        self.assertEqual(row["model_version"], "357c53fb659c")

        fp = self._row(rows, "pii_marginal_false_positives_added", "regex+ner vs regex")
        self.assertEqual(fp["value"], 45.0)
        self.assertEqual((fp["ci_low"], fp["ci_high"]), result.bca_ci([43.0, 47.0, 45.0])[:2])

        regex = self._row(rows, "pii_recall_entity", "layers:regex")
        self.assertEqual((regex["value"], regex["ci_low"], regex["ci_high"]), (0.7925, 0.7925, 0.7925))
        self.assertIsNone(regex["model"])

    def test_an_interval_that_excludes_the_mean_is_reported_not_widened(self):
        real = result.bca_ci

        def shifted(values, *a, **k):
            lo, hi, meth = real(values, *a, **k)
            if lo != hi:  # move a varying row's interval wholly above its mean
                width = hi - lo
                return hi + width, hi + 2 * width + 1, meth
            return lo, hi, meth

        with mock.patch.object(result, "bca_ci", shifted):
            rc, err, rows = self._main()
        self.assertEqual(rc, 3)
        self.assertIn("lies outside its bca-bootstrap-exhaustive-27 interval", err)
        self.assertIn("pii_recall_direct_identifiers [layers:regex+ner]", err)
        # Nothing whose interval excludes its mean was written; the constant rows were.
        for r in rows:
            self.assertLessEqual(r["ci_low"], r["value"])
            self.assertLessEqual(r["value"], r["ci_high"])
        self.assertFalse([r for r in rows if r["arm"] == "layers:regex+ner"
                          and r["metric"] == "pii_recall_direct_identifiers"])
        self._row(rows, "pii_recall_entity", "layers:regex")

    def test_record_refuses_too_few_runs(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            ad13.main(["--record", "--runs", "2"])


if __name__ == "__main__":
    unittest.main()
