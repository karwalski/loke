# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/check_figure_evidence.py and the evidence ledger (VM1.3a).

Run: python3 -m unittest benchmarks.lib.test_evidence   (the quality gate runs it)

Every test but the first drives the check with the real docs/metrics-baseline.md and the real
committed ledger, altered in one way, and asserts the named failure. The alterations are the
mistakes the check exists for: a figure typed in by hand, a figure that differs from its row, a
row edited after it was cited, and a new section published without evidence.
"""

from __future__ import annotations

import importlib.util
import json
import pathlib
import unittest

from benchmarks.lib import evidence, result

REPO = result.REPO
_spec = importlib.util.spec_from_file_location(
    "check_figure_evidence", REPO / "scripts" / "check_figure_evidence.py")
cfe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cfe)

DOC = (REPO / "docs" / "metrics-baseline.md").read_text(encoding="utf-8")
LEDGER = (REPO / "benchmarks" / "evidence" / "ledger.jsonl").read_text(encoding="utf-8")

BITRE = "**1.59x** <sub>[ev:4c287ad3c0f3 n=2]</sub>"
SAVING = "26% <sub>[ev:a5d0cdbc349c /saving n=2]</sub>"
SERIAL_TABLE_END = "| BITRE road fatalities, 500 rows — real data, CC BY |"

# A repeated, timed measurement, as summarise() records it: five runs, BCa interval.
TIMED = result.summarise(
    [9.0, 1.20, 1.25, 1.22, 1.31, 1.18], metric="toy_throughput", units="MB/s",
    workload="toy", n=5, arm="a", seed=1, tokenizer="bytes")
TIMED.recorded_at = "2026-10-02T09:00:00+00:00"
TIMED.toke_commit, TIMED.loke_commit, TIMED.ooke_commit = "abc1234", "def5678", "c07c503"
TIMED_ROW = json.loads(json.dumps(__import__("dataclasses").asdict(TIMED)))
TIMED_D = evidence.digest(TIMED_ROW)


def run(doc=DOC, ledger=LEDGER, head=None):
    return cfe.check(doc, ledger, head)[0]


def timed_section(value_cell, ci_cell=None, heading_date="2026-10-02", commits="toke `abc1234`, loke `def5678`"):
    ci = f" | {ci_cell}" if ci_cell is not None else ""
    head = "| Input | Throughput" + (" | Interval |" if ci_cell is not None else " |")
    sep = "|---|---" + ("|---|" if ci_cell is not None else "|")
    return (f"\n### Toy throughput — {heading_date}\n\n**Evidence: verified.**\n\n{head}\n{sep}\n"
            f"| toy | {value_cell}{ci} |\n\nMeasured at {commits}.\n\n")


def with_measured_section(section):
    """Insert a section at the top of '## Measured'."""
    return DOC.replace("## Measured\n", "## Measured\n" + section, 1)


def fmt(x, k=2):
    return f"{x:.{k}f}"


class RealPage(unittest.TestCase):
    def test_the_published_page_passes_and_is_not_vacuous(self):
        errors, summary = cfe.check(DOC, LEDGER, LEDGER)
        self.assertEqual(errors, [])
        self.assertGreaterEqual(summary["verified"], 1)
        self.assertGreaterEqual(summary["cited"], 19)

    def test_every_ledger_row_validates_and_is_unique(self):
        rows = evidence.parse_ledger(LEDGER)
        self.assertEqual(len({evidence.digest(r) for r in rows}), len(rows))
        for r in rows:
            evidence.validate_row(r)


class HandTypedFigure(unittest.TestCase):
    def test_a_table_row_typed_in_by_hand_fails(self):
        doc = DOC.replace(SERIAL_TABLE_END, "| Hand-typed, 50 rows | **1.91x** | 1.52x |\n" + SERIAL_TABLE_END, 1)
        errors = run(doc)
        self.assertTrue(any("'1.91x' in a verified section cites no recorded row" in e for e in errors), errors)
        self.assertTrue(any("'1.52x' in a verified section cites no recorded row" in e for e in errors), errors)

    def test_a_prose_figure_typed_in_by_hand_fails(self):
        doc = DOC.replace("YAML is worse than minified JSON on every payload measured.",
                          "YAML is worse than minified JSON on every payload measured, by up to 17%.", 1)
        errors = run(doc)
        self.assertTrue(any("'17%' in a verified section cites no recorded row" in e for e in errors), errors)

    def test_a_citation_stripped_from_a_figure_fails(self):
        doc = DOC.replace(BITRE, "**1.59x**", 1)
        self.assertTrue(any("'1.59x'" in e and "cites no recorded row" in e for e in run(doc)))


class MismatchedFigure(unittest.TestCase):
    def test_a_value_that_differs_from_its_row_fails(self):
        doc = DOC.replace(BITRE, BITRE.replace("1.59x", "1.62x"), 1)
        errors = run(doc)
        self.assertTrue(any("'1.62x' cites ev:4c287ad3c0f3: printed 1.62, but the row records 1.5929" in e
                            for e in errors), errors)

    def test_rounding_the_wrong_way_fails(self):
        # The row is 1.4946: 1.49x, not 1.50x. The check found this on the published page.
        doc = DOC.replace("1.49x <sub>[ev:d72e6141382a", "1.50x <sub>[ev:d72e6141382a", 1)
        self.assertTrue(any("printed 1.50" in e for e in run(doc)))

    def test_a_saving_that_differs_from_its_ratio_fails(self):
        doc = DOC.replace(SAVING, SAVING.replace("26%", "28%"), 1)
        self.assertTrue(any("'28%' cites ev:a5d0cdbc349c" in e for e in run(doc)))

    def test_a_wrong_n_fails(self):
        doc = DOC.replace(BITRE, BITRE.replace("n=2", "n=20"), 1)
        self.assertTrue(any("printed n=20, the row's N is 2" in e for e in run(doc)))

    def test_a_citation_to_a_row_that_does_not_exist_fails(self):
        doc = DOC.replace(BITRE, BITRE.replace("4c287ad3c0f3", "4c287ad3c0f4"), 1)
        self.assertTrue(any("ev:4c287ad3c0f4 is not in" in e for e in run(doc)))


class Ledger(unittest.TestCase):
    def test_editing_a_cited_row_breaks_its_citation(self):
        ledger = LEDGER.replace('"value":1.5929', '"value":1.6200', 1)
        self.assertNotEqual(ledger, LEDGER)
        self.assertTrue(any("ev:4c287ad3c0f3 is not in" in e for e in run(ledger=ledger)))

    def test_the_ledger_is_append_only(self):
        lines = LEDGER.splitlines(keepends=True)
        self.assertTrue(any("not a prefix" in e for e in run(ledger="".join(lines[1:]), head=LEDGER)))
        self.assertEqual(run(ledger=LEDGER + json.dumps(TIMED_ROW) + "\n", head=LEDGER), [])

    def test_a_row_that_no_longer_validates_is_reported(self):
        bad = dict(TIMED_ROW, ci_method="percentile-bootstrap-10000")
        errors = run(ledger=LEDGER + json.dumps(bad) + "\n")
        self.assertTrue(any("no longer validates" in e for e in errors), errors)

    def test_a_single_run_timing_cannot_enter_the_ledger(self):
        once = dict(TIMED_ROW, runs=None, ci_low=None, ci_high=None, ci_method=None)
        with self.assertRaises(result.ResultRejected):
            evidence.validate_row(once)


class RepeatedRuns(unittest.TestCase):
    LEDGER2 = LEDGER + json.dumps(TIMED_ROW) + "\n"

    def cell(self):
        return f"{fmt(TIMED.value)} MB/s <sub>[ev:{TIMED_D} n=5]</sub>"

    def ci(self, lo=None, hi=None):
        lo = TIMED.ci_low if lo is None else lo
        hi = TIMED.ci_high if hi is None else hi
        return f"{fmt(lo)}–{fmt(hi)} <sub>[ev:{TIMED_D} /ci n=5]</sub>"

    def test_a_repeated_measurement_with_its_bca_interval_passes(self):
        self.assertTrue(TIMED.ci_method.startswith("bca-"))
        self.assertEqual(run(with_measured_section(timed_section(self.cell(), self.ci())), self.LEDGER2), [])

    def test_a_repeated_measurement_without_its_interval_fails(self):
        errors = run(with_measured_section(timed_section(self.cell())), self.LEDGER2)
        self.assertTrue(any("is a repeated measurement (5 runs); print its BCa interval" in e for e in errors), errors)

    def test_an_interval_that_differs_from_the_row_fails(self):
        errors = run(with_measured_section(timed_section(self.cell(), self.ci(hi=TIMED.ci_high + 0.05))), self.LEDGER2)
        self.assertTrue(any("interval high" in e for e in errors), errors)

    def test_provenance_the_section_does_not_state_fails(self):
        errors = run(with_measured_section(timed_section(self.cell(), self.ci(), commits="toke `abc1234`")), self.LEDGER2)
        self.assertTrue(any("loke_commit def5678, which the section does not name" in e for e in errors), errors)

    def test_a_heading_dated_other_than_the_recording_fails(self):
        errors = run(with_measured_section(timed_section(self.cell(), self.ci(), heading_date="2026-10-05")), self.LEDGER2)
        self.assertTrue(any("not on the heading's date 2026-10-05" in e for e in errors), errors)


class Markers(unittest.TestCase):
    NEW = "\n### A new measurement — 2026-10-03\n\n| Metric | Value |\n|---|---|\n| thing | **0.87** |\n\n"

    def test_a_new_section_with_no_marker_fails(self):
        errors = run(with_measured_section(self.NEW))
        self.assertTrue(any("A new measurement" in e and "0 evidence marker" in e for e in errors), errors)

    def test_legacy_is_refused_after_the_cutoff(self):
        sec = self.NEW.replace("\n\n|", "\n\n**Evidence: legacy, unverified.** It was typed in from a terminal.\n\n|", 1)
        errors = run(with_measured_section(sec))
        self.assertTrue(any("'legacy, unverified' is only for figures published on or before" in e for e in errors), errors)

    def test_a_measured_section_cannot_call_itself_not_a_measurement(self):
        sec = self.NEW.replace("\n\n|", "\n\n**Evidence: not a measurement.** It is only a number we liked.\n\n|", 1)
        errors = run(with_measured_section(sec))
        self.assertTrue(any("'not a measurement' is not allowed there" in e for e in errors), errors)

    def test_legacy_without_a_reason_fails(self):
        doc = DOC.replace("**Evidence: legacy, unverified.** Read from test output;",
                          "**Evidence: legacy, unverified.**\n\nRead from test output;", 1)
        self.assertNotEqual(doc, DOC)
        self.assertTrue(any("must say why" in e for e in run(doc)))

    def test_a_page_with_nothing_verified_fails(self):
        # Every verified marker, not only the first: the page has more than one verified section.
        doc = DOC.replace("**Evidence: verified.**", "**Evidence: legacy, unverified.**")
        self.assertTrue(any("no section is verified" in e for e in run(doc)))


if __name__ == "__main__":
    unittest.main()
