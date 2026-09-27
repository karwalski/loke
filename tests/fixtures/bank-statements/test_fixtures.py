#!/usr/bin/env python3
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
"""Tests for the synthetic bank statement fixtures (story MK21.12).

Run: python3 tests/fixtures/bank-statements/test_fixtures.py   (the quality gate runs it)

Four things are checked, each against the committed files:

  1. They are exactly what generate.py produces from its seed: regenerated into a temporary
     directory, every file is byte-identical (the PNG's pixels are; its deflate stream is the
     zlib build's), and manifest.json's digests match both.
  2. Each format reads back, with a reader written here independently of the writer, to the
     transactions in ground-truth.json: the workbook through its shared strings, styles and
     cell references, the PDF from each string's position rather than stream order.
  3. The difficulties the manifest names are really in the files (a text date, a split text
     object, a rotated scan, identical twin transactions, a shared June), so a fixture cannot
     quietly lose the thing it exists to test.
  4. Nothing in any of them could be a real person's identifier: loke's own PII patterns
     (read from packages/core/src/privacy/patterns.tk by the corpus scorer) find nothing
     personal in any string, and neither do stricter checks for what that layer has no
     pattern for (BSBs, account numbers, card numbers by Luhn, holder names). A planted
     identifier is found, so the scan is not vacuous.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from xml.etree import ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent
sys.path.insert(0, str(HERE))

import generate  # noqa: E402
import render  # noqa: E402

# loke's PII patterns, as the corpus scorer reads them from patterns.tk. Loaded by path: that
# directory has its own generate.py, which must not shadow this one.
_spec = importlib.util.spec_from_file_location(
    "score_patterns", REPO / "tests" / "fixtures" / "pii-corpus" / "score_patterns.py")
score_patterns = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(score_patterns)

MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
TRUTH = json.loads((HERE / "ground-truth.json").read_text(encoding="utf-8"))
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


def regenerate() -> pathlib.Path:
    out = pathlib.Path(tempfile.mkdtemp(prefix="mk21-fixtures-"))
    r = subprocess.run([sys.executable, str(HERE / "generate.py"), "--out", str(out)],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"generate.py failed:\n{r.stdout}\n{r.stderr}")
    return out


# ── Independent readers ────────────────────────────────────────────────────────

def read_xlsx(path: pathlib.Path) -> dict:
    """Cells by reference, with shared strings resolved and date cells converted."""
    z = zipfile.ZipFile(path)
    sst = []
    for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS):
        # The string is its own <t> or its runs' <t>s, never the phonetic <rPh>.
        parts = [t.text or "" for t in si.findall("m:t", NS)]
        parts += [t.text or "" for r in si.findall("m:r", NS) for t in r.findall("m:t", NS)]
        sst.append("".join(parts))
    styles = ET.fromstring(z.read("xl/styles.xml"))
    xfs = [int(x.get("numFmtId")) for x in styles.find("m:cellXfs", NS).findall("m:xf", NS)]
    cells = {}
    for c in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(f"{{{NS['m']}}}c"):
        ref, t = c.get("r"), c.get("t")
        v = c.find("m:v", NS)
        v = v.text if v is not None else None
        style = xfs[int(c.get("s", "0"))]
        if t == "s":
            cells[ref] = ("str", sst[int(v)])
        elif style == 14:
            cells[ref] = ("date", date(1899, 12, 30) + timedelta(days=int(v)))
        else:
            cells[ref] = ("num", float(v), c.find("m:f", NS) is not None)
    return {"cells": cells, "sst": sst, "raw_sst": z.read("xl/sharedStrings.xml").decode()}


_TJ = re.compile(r"BT /F1 ([\d.]+) Tf ([\d.]+) ([\d.]+) Td \(((?:[^\\)]|\\.)*)\) Tj ET")


def read_pdf(path: pathlib.Path) -> list[list[tuple[float, float, str]]]:
    """Every string on every page as (x, y, text), in STREAM order."""
    data = path.read_bytes().decode("latin-1")
    pages = []
    for m in re.finditer(r"stream\n(.*?)endstream", data, re.S):
        page = []
        for t in _TJ.finditer(m.group(1)):
            text = re.sub(r"\\(.)", r"\1", t.group(4))
            page.append((float(t.group(2)), float(t.group(3)), text))
        pages.append(page)
    return pages


def pdf_lines(page, size=9.0) -> list[list[tuple[float, float, str]]]:
    """Reading order: by y, then x, with abutting fragments joined."""
    rows: dict[float, list] = {}
    for x, y, text in page:
        rows.setdefault(y, []).append((x, text))
    out = []
    for y in sorted(rows, reverse=True):
        frags = sorted(rows[y])
        joined = []
        for x, text in frags:
            if joined:
                px, pt = joined[-1]
                if abs(px + render.helv_width(pt, size) - x) < 0.5:
                    joined[-1] = (px, pt + text)
                    continue
            joined.append((x, text))
        out.append([(x, y, t) for x, t in joined])
    return out


def money(s: str) -> float:
    return float(s.replace(",", "").replace("$", ""))


def pdf_transactions(path: pathlib.Path) -> list[dict]:
    txns = []
    for page in read_pdf(path):
        for line in pdf_lines(page):
            fields = {}
            for x, y, text in line:
                if abs(x - generate.PDF_COLS["date"]) < 1:
                    fields["date"] = text
                elif generate.PDF_COLS["desc"] - 1 < x < 300:
                    fields["desc"] = text
                else:
                    right = x + render.helv_width(text, 9)
                    for col in ("debit", "credit", "balance"):
                        if abs(right - generate.PDF_COLS[col]) < 0.5:
                            fields[col] = text
            if re.fullmatch(r"\d\d/\d\d/\d\d", fields.get("date", "")):
                d, m, yy = fields["date"].split("/")
                amt = -money(fields["debit"]) if "debit" in fields else money(fields["credit"])
                txns.append({"date": f"20{yy}-{m}-{d}", "merchant": fields["desc"], "amount": amt})
    return txns


# ── 1. Deterministic ───────────────────────────────────────────────────────────

class Regenerates(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = regenerate()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.out, ignore_errors=True)

    def test_every_file_regenerates_identically(self):
        names = sorted(MANIFEST["files"]) + ["manifest.json"]
        for name in names:
            with self.subTest(name=name):
                new, old = (self.out / name).read_bytes(), (HERE / name).read_bytes()
                if name.endswith(".png"):
                    self.assertEqual(render.png_pixels(new), render.png_pixels(old),
                                     f"{name}: pixels differ from the committed scan")
                else:
                    self.assertEqual(new, old, f"{name} does not regenerate byte for byte")

    def test_manifest_digests_match_the_committed_files(self):
        for name, info in MANIFEST["files"].items():
            with self.subTest(name=name):
                self.assertEqual(generate.content_digest(name, (HERE / name).read_bytes()), info["digest"])

    def test_the_manifest_covers_every_fixture_and_names_its_difficulties(self):
        present = {p.name for p in HERE.iterdir()
                   if p.suffix in (".csv", ".xlsx", ".pdf", ".png", ".json") and p.name != "manifest.json"}
        self.assertEqual(present, set(MANIFEST["files"]))
        for fmt in ("csv", "xlsx", "pdf", "png"):
            self.assertTrue(any(n.endswith(fmt) for n in MANIFEST["files"]), f"no {fmt} fixture")
        for name, info in MANIFEST["files"].items():
            if name != "ground-truth.json":
                self.assertTrue(info["difficulties"], f"{name} names no difficulty")


# ── 2 and 3. Each format reads back to the ground truth, difficulties included ──

def truth(name):
    return [{k: t[k] for k in ("date", "merchant", "amount")} for t in TRUTH["ground_truth"][name]]


class Xlsx(unittest.TestCase):
    NAME = "spreadsheet-export.xlsx"

    @classmethod
    def setUpClass(cls):
        cls.x = read_xlsx(HERE / cls.NAME)

    def test_the_transactions_read_back(self):
        c = self.x["cells"]
        self.assertEqual([c[f"{col}5"][1] for col in "ABCDE"],
                         ["Date", "Description", "Reference", "Amount", "Balance"])
        got, r = [], 6
        while f"B{r}" in c:
            kind, v = c[f"A{r}"][:2]
            d = v if kind == "date" else date(int(v[6:]), int(v[3:5]), int(v[:2]))
            got.append({"date": d.isoformat(), "merchant": c[f"B{r}"][1], "amount": c[f"D{r}"][1]})
            r += 1
        self.assertEqual(got, truth(self.NAME))

    def test_the_difficulties_are_in_the_file(self):
        c = self.x["cells"]
        self.assertEqual(c["A1"][1], "SAMPLE MUTUAL (FICTITIOUS) - TRANSACTIONS")
        self.assertIn("<rPh", self.x["raw_sst"])                       # phonetic run present
        self.assertNotIn("A4", c)                                       # a sparse row
        self.assertNotIn('t="inlineStr"', self.x["raw_sst"])
        tr = TRUTH["files"][self.NAME]["text_date_row"]
        self.assertIsNotNone(tr, "no date was written as text")
        self.assertEqual(c[f"A{tr}"][0], "str")                         # a date typed as text
        self.assertRegex(c[f"A{tr}"][1], r"^(0[2-9]|1[0-2])/0\d/2026$")
        self.assertTrue(all(c[f"E{r}"][2] for r in range(6, 6 + len(truth(self.NAME)))))  # formulas
        refs = [r for r in range(6, 6 + len(truth(self.NAME))) if f"C{r}" in c]
        self.assertTrue(0 < len(refs) < len(truth(self.NAME)) // 2)     # a sparse column
        rows = [json.dumps(t, sort_keys=True) for t in truth(self.NAME)]
        self.assertTrue(any(rows.count(r) == 2 for r in rows), "no genuinely identical pair")

    def test_the_workbook_reconciles(self):
        c, t = self.x["cells"], truth(self.NAME)
        self.assertAlmostEqual(c["B3"][1] + sum(r["amount"] for r in t), c["E3"][1], places=2)
        self.assertAlmostEqual(c[f"E{5 + len(t)}"][1], c["E3"][1], places=2)


# The reader loke's XLSX import will use (MK21.3a): toke's std.xlsx at the pinned toolchain.
XLSX_DUMP_TK = r'''m=xlsxdump;
i=io:std.io;
i=s:std.str;
i=env:std.env;
i=x:std.xlsx;

f=main():i64{
  let w=x.openfile(env.getor("XLFILE";"/nonexistent.xlsx"));
  mt w {
    $ok:b dumpbook(b);
    $err:e io.println(s.concat("open=ERR|";x.lasterr()))
  };
  <0
};

f=dumpbook(b:$xlsxbook):i64{
  io.println(s.concat("datesystem=";x.datesystem(b)));
  let r=x.rows(b;"Transactions");
  mt r {
    $ok:rows dumprows(rows);
    $err:e io.println(s.concat("rows=ERR|";x.lasterr()))
  };
  x.close(b);
  <0
};

f=dumprows(rows:@(@($xlsxcell))):i64{
  lp(let r=0;r<rows.len;r=r+1){
    let row=rows.get(r);
    lp(let c=0;c<row.len;c=c+1){
      let cell=row.get(c);
      io.println("\(cell.ref)|\(cell.celltype)|\(cell.value)")
    }
  };
  <0
};
'''


class TokeReadsTheWorkbook(unittest.TestCase):
    NAME = "spreadsheet-export.xlsx"

    def test_std_xlsx_reads_the_transactions(self):
        toke = pathlib.Path(os.environ.get("TOKE_DIR", "/nonexistent")) / "toke"
        if not toke.is_file():
            self.skipTest("TOKE_DIR is not set to a built toke; the Python reader above still ran")
        work = pathlib.Path(tempfile.mkdtemp(prefix="mk21-xlsx-"))
        try:
            (work / "xl.tk").write_text(XLSX_DUMP_TK, encoding="utf-8")
            built = subprocess.run([str(toke), "--out", str(work / "xl"), str(work / "xl.tk")],
                                   capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            ran = subprocess.run([str(work / "xl"), "--allow-read"], capture_output=True, text=True,
                                 env={**os.environ, "XLFILE": str(HERE / self.NAME)})
        finally:
            shutil.rmtree(work, ignore_errors=True)
        cells = {}
        for line in ran.stdout.splitlines():
            parts = line.split("|", 2)
            if len(parts) == 3:
                cells[parts[0]] = (parts[1], parts[2])
        self.assertEqual(cells.get("A1"), ("str", "SAMPLE MUTUAL (FICTITIOUS) - TRANSACTIONS"))
        got, r = [], 6
        while cells.get(f"B{r}", ("empty",))[0] == "str":
            kind, v = cells[f"A{r}"]
            iso = v if kind == "date" else f"{v[6:]}-{v[3:5]}-{v[:2]}"
            got.append({"date": iso, "merchant": cells[f"B{r}"][1], "amount": float(cells[f"D{r}"][1])})
            r += 1
        self.assertEqual(got, truth(self.NAME))


class Pdf(unittest.TestCase):
    NAME = "statement-text.pdf"

    def test_the_transactions_read_back_by_position(self):
        self.assertEqual(pdf_transactions(HERE / self.NAME), truth(self.NAME))

    def test_stream_order_is_not_reading_order(self):
        # Every date on page 1 is drawn before any description, so reading the stream in
        # order gives a column of dates, not a row.
        page = read_pdf(HERE / self.NAME)[0]
        dates = [i for i, (_, _, t) in enumerate(page) if re.fullmatch(r"\d\d/\d\d/\d\d", t)]
        descs = [i for i, (_, _, t) in enumerate(page) if t == truth(self.NAME)[0]["merchant"]]
        self.assertGreater(len(dates), 20)
        self.assertLess(max(dates), min(descs))

    def test_a_description_is_split_across_two_text_objects(self):
        whole = truth(self.NAME)[generate.SPLIT_ROW]["merchant"]
        strings = [t for page in read_pdf(HERE / self.NAME) for _, _, t in page]
        expected = sum(1 for t in truth(self.NAME) if t["merchant"] == whole)
        self.assertEqual(strings.count(whole), expected - 1)
        self.assertIn(whole[:6], strings)
        self.assertIn(whole[6:], strings)

    def test_the_page_break_carries_a_balance_that_is_not_a_transaction(self):
        pages = read_pdf(HERE / self.NAME)
        self.assertEqual(len(pages), 2)
        last1 = [t for _, _, t in pages[0]]
        first2 = [t for _, _, t in pages[1]]
        self.assertIn("BALANCE CARRIED FORWARD", last1)
        self.assertIn("BALANCE BROUGHT FORWARD", first2)

    def test_pdftotext_extracts_every_merchant(self):
        if not shutil.which("pdftotext"):
            self.skipTest("pdftotext not installed; the position reader above still ran")
        text = subprocess.run(["pdftotext", "-layout", str(HERE / self.NAME), "-"],
                              capture_output=True, text=True, check=True).stdout
        for t in truth(self.NAME):
            self.assertIn(t["merchant"], text)


class Scan(unittest.TestCase):
    NAME = "statement-scan.png"

    @classmethod
    def setUpClass(cls):
        cls.w, cls.h, cls.px = render.png_pixels((HERE / cls.NAME).read_bytes())

    def test_it_is_page_one_of_the_pdf_statement(self):
        self.assertEqual(truth(self.NAME), truth("statement-text.pdf")[:len(truth(self.NAME))])
        self.assertLess(len(truth(self.NAME)), len(truth("statement-text.pdf")))

    def test_the_scan_is_crooked(self):
        # The sheet was fed shifted right and up, so the lid (value 150) shows down the left
        # edge and along the bottom, while the top-right corner and right edge are paper.
        px, w, h = self.px, self.w, self.h
        self.assertEqual(px[(h - 2) * w + w // 2], 150)
        self.assertEqual(px[5 * w + 2], 150)
        self.assertEqual(px[(h - 5) * w + 5], 150)
        self.assertGreater(px[5 * w + w - 30], 200)
        self.assertGreater(px[(h // 2) * w + w - 5], 200)
        # A shift alone would leave the lid a constant width down the left edge; a rotation
        # makes it wider towards one end.
        def lid_width(y):
            n = 0
            while n < w and px[y * w + n] == 150:
                n += 1
            return n
        self.assertGreater(abs(lid_width(h - 150) - lid_width(100)), 20)

    def test_it_has_no_text_layer_and_real_ink(self):
        data = (HERE / self.NAME).read_bytes()
        self.assertNotIn(b"tEXt", data)
        dark = sum(1 for v in self.px if v < 100) / len(self.px)
        self.assertTrue(0.005 < dark < 0.2, dark)


class Csv(unittest.TestCase):
    def test_the_two_csv_statements_share_june(self):
        a = [json.dumps(t, sort_keys=True) for t in truth("westpac-shaped.csv")]
        b = [json.dumps(t, sort_keys=True) for t in truth("anz-shaped.csv")]
        shared = [t for t in b if t in a]
        self.assertEqual(len(shared), TRUTH["overlap"]["shared_transactions"])
        self.assertGreater(len(shared), 10)
        self.assertTrue(all(json.loads(t)["date"].startswith("2026-06") for t in shared))


# ── 4. Nothing a real person could be ─────────────────────────────────────────

PERSONAL = {"EMAIL", "PHONE_AU", "PHONE_US", "CREDIT_CARD", "IP_V4", "AU_TFN", "SSN_US", "API_KEY"}
# Written out here, not read from the generator, so a changed holder is a failure to review
# rather than a new baseline.
SYNTHETIC_HOLDERS = {"A N EXAMPLE"}
MERCHANT_DOMAINS = {m.split()[0] for m, _ in generate.MERCHANTS if "." in m.split()[0]}


def all_text() -> dict[str, str]:
    """Every string a reader of each fixture would see."""
    out = {}
    for name in MANIFEST["files"]:
        p = HERE / name
        if name.endswith(".csv"):
            enc = TRUTH["files"][name].get("encoding", "utf-8")
            out[name] = p.read_bytes().decode(enc)
        elif name.endswith(".json"):
            out[name] = p.read_text(encoding="utf-8")
        elif name.endswith(".xlsx"):
            x = read_xlsx(p)
            out[name] = "\n".join(x["sst"]) + "\n" + "\n".join(str(v[1]) for v in x["cells"].values())
        elif name.endswith(".pdf"):
            out[name] = "\n".join(" ".join(t for _, _, t in line)
                                  for page in read_pdf(p) for line in pdf_lines(page))
        elif name.endswith(".png"):
            header, pages = scan_source()
            out[name] = "\n".join(t for _, _, t in generate.scan_lines(header, pages[0]))
    # The manifest's digests are hex, and their digit runs are not account numbers.
    manifest = (HERE / "manifest.json").read_text(encoding="utf-8")
    out["manifest.json"] = re.sub(r"(sha256|pixels):[0-9a-f]{64}", r"\1:<digest>", manifest)
    return out


def scan_source():
    """The statement the scan renders, rebuilt from the ground truth rather than the pixels."""
    rows = TRUTH["ground_truth"]["statement-text.pdf"]
    info = TRUTH["files"]["statement-text.pdf"]
    bal, txns = info["opening_balance"], []
    for r in rows:
        bal = round(bal + r["amount"], 2)
        t = {"date": date.fromisoformat(r["date"]), "merchant": r["merchant"], "amount": r["amount"],
             "balance": bal}
        if r["merchant"] == "TRANSFER TO SAVINGS":
            t["reference"] = "REF 00123 SAVINGS GOAL"
        txns.append(t)
    return generate.statement_pages(txns, info["opening_balance"], info["closing_balance"],
                                    date(2026, 2, 1), date(2026, 2, 28))


def luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        d = int(ch)
        if i % 2:
            d = d * 2 - 9 if d > 4 else d * 2
        total += d
    return total % 10 == 0


def personal_findings(text: str, patterns) -> list[str]:
    found = []
    for d in score_patterns.detect(text, patterns):
        if d["type"] in PERSONAL:
            found.append(f"{d['type']} {d['value']!r}")
        elif d["type"] == "URL" and d["value"].upper() not in MERCHANT_DOMAINS:
            found.append(f"URL {d['value']!r}")
    for m in re.finditer(r"(?<![\d.])\d(?:[ -]?\d){12,18}(?![\d.])", text):
        if luhn(re.sub(r"\D", "", m.group(0))):
            found.append(f"Luhn-valid card number {m.group(0)!r}")
    for m in re.finditer(r"\b\d{3}-\d{3}\b", text):
        if m.group(0) != "000-000":
            found.append(f"BSB {m.group(0)!r}")
    for m in re.finditer(r"(?<![\d.,/])\d{8,}(?![\d.,/])", text):
        if set(m.group(0)) != {"0"}:
            found.append(f"account-length digit run {m.group(0)!r}")
    for m in re.finditer(r"ACCOUNT HOLDER:\s*([A-Z ]+)", text):
        if m.group(1).strip() not in SYNTHETIC_HOLDERS:
            found.append(f"holder {m.group(1).strip()!r}")
    return found


class NoRealIdentifiers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patterns = score_patterns.load_patterns()

    def test_the_patterns_were_loaded(self):
        self.assertEqual(set(self.patterns), set(score_patterns.PATTERN_TO_TYPE))

    def test_no_fixture_contains_a_personal_identifier(self):
        texts = all_text()
        self.assertEqual(set(texts), set(MANIFEST["files"]) | {"manifest.json"})
        for name, text in texts.items():
            with self.subTest(name=name):
                self.assertGreater(len(text), 100)
                self.assertEqual(personal_findings(text, self.patterns), [])

    def test_a_planted_identifier_is_found(self):
        # Not vacuous: each kind of finding fires on a planted value.
        planted = ("ACCOUNT HOLDER: JANE CITIZEN\ncontact jane.citizen@example.com or 0412 345 678\n"
                   "TFN 123 456 782  card 4111 1111 1111 1111  BSB 062-000  ACCOUNT 12345678\n")
        found = " ".join(personal_findings(planted, self.patterns))
        for kind in ("EMAIL", "PHONE_AU", "AU_TFN", "Luhn-valid", "BSB", "account-length", "holder"):
            self.assertIn(kind, found)


if __name__ == "__main__":
    unittest.main()
