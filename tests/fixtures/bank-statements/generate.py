#!/usr/bin/env python3
"""Generate synthetic bank statement fixtures (story MK21.12).

Why synthetic, and why generated
--------------------------------
The personal-finance workspace (MK21) must be demonstrable and testable without
anyone's real bank statement. Nobody should have to hand over their financial
history to try a demo, and a repository should not contain one.

Generated rather than hand-written for the same reason as the PII corpus: the
expected parse is known by construction. Each statement ships with a ground-truth
JSON file giving the transactions that should be extracted, so an import can be
scored rather than eyeballed.

The deliberate difficulties are the point
-----------------------------------------
A fixture that parses cleanly first time tests nothing. Each institution shape
below embeds a specific real-world problem, and MK21.5's confidence and
reconciliation work exists to catch exactly these:

  westpac-shaped   separate debit and credit columns, DD/MM/YYYY dates,
                   a quoted description containing a comma
  anz-shaped       single signed amount column, D/M/YY dates, processor noise
                   and card suffixes in merchant strings, a CP1252 character
  overlap          the same period boundary as the first file, so importing
                   both must deduplicate rather than double-count
  ragged           a trailing-comma row and a short row, which is common in
                   real exports
  reconciliation   opening and closing balances that the transactions must sum
                   to. One fixture deliberately does NOT reconcile, so the
                   check can be shown to fire
  xlsx             a workbook as Excel writes one: shared strings, date serials
                   typed only by styles.xml, sparse rows and cells, a text date,
                   formulas, and two genuinely identical transactions
  text PDF         column-major content stream, a split text object, DD/MM/YY,
                   a page break with carried/brought-forward balance lines
  scanned image    page 1 of the PDF's statement, rotated 1.75 degrees, shifted,
                   speckled, streaked and hole-punched, with no text layer

The binary formats are written by render.py with the standard library alone, so
every file regenerates byte for byte on any machine (the PNG's pixels do; its
deflate stream depends on the zlib build). manifest.json records each file's
digest, what it contains and its difficulties; test_fixtures.py regenerates
everything and compares, reads each format back with an independent reader, and
runs loke's PII patterns over every string to show nothing in them could be a
real person's identifier.

Every amount, reference and holder detail is invented. The holder is
"A N EXAMPLE" of a "FICTITIOUS" institution, the BSB is 000-000 and the account
is identified only as "ENDING 0000", none of which is issued. Merchants are
generic or large businesses, never people.

Usage:
    python3 generate.py              write the fixtures here
    python3 generate.py --out DIR    write them to DIR (the test regenerates this way)
    python3 generate.py --verify     check reconciliation (the quality gate)
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import random
import sys
import tempfile
from datetime import date, timedelta

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import render  # noqa: E402

# Merchants chosen to exercise categorisation, including the cases that make
# merchant text personal information: a pharmacy, a clinic and a gambling site
# each disclose something material about a person. MK21.7 depends on these
# never leaving the device.
MERCHANTS = [
    ("WOOLWORTHS 1234 SYDNEY", "groceries"),
    ("COLES 5678 NEWTOWN", "groceries"),
    ("SQ *THE LOCAL CAFE", "eating out"),
    ("UBER *EATS SYDNEY", "eating out"),
    ("OPAL TOP UP", "transport"),
    ("AMPOL 4455 ALEXANDRIA", "transport"),
    ("ORIGIN ENERGY BPAY", "utilities"),
    ("TELSTRA CORP LTD", "utilities"),
    ("PRICELINE PHARMACY 882", "health"),
    ("NEWTOWN MEDICAL CENTRE", "health"),
    ("CITY DENTAL GROUP", "health"),
    ("NETFLIX.COM", "subscriptions"),
    ("SPOTIFY P2B4C5D6", "subscriptions"),
    ("BUNNINGS 3099", "home"),
    ("KMART 1188", "home"),
    ("SPORTSBET PTY LTD", "gambling"),
    ("QANTAS AIRWAYS", "travel"),
    ("AIRBNB * HMXY2R", "travel"),
    ("TRANSFER TO SAVINGS", "transfer"),
    ("SALARY EXAMPLE PTY LTD", "income"),
    ("ATO PAYMENT", "tax"),
    ("BODY CORPORATE LEVY", "home"),
]


def statement(rng: random.Random, start: date, days: int, opening: float):
    """Build a transaction list with a running balance that reconciles."""
    txns = []
    balance = opening
    d = start
    end = start + timedelta(days=days)

    # Salary lands fortnightly from the first Thursday on or after the start.
    # Computed explicitly rather than as a coincidence of weekday and a modulo,
    # which is how an earlier version of this generator paid salary almost
    # never and produced an account tens of thousands overdrawn.
    first_thursday = start + timedelta(days=(3 - start.weekday()) % 7)
    pay_days = set()
    pd = first_thursday
    while pd < end:
        pay_days.add(pd)
        pd += timedelta(days=14)

    while d < end:
        if d in pay_days:
            amt = round(rng.uniform(2800, 3200), 2)
            balance += amt
            txns.append({"date": d, "merchant": "SALARY EXAMPLE PTY LTD",
                         "category": "income", "amount": amt, "balance": round(balance, 2)})
        # Rent monthly.
        if d.day == 1:
            amt = -round(rng.uniform(2100, 2200), 2)
            balance += amt
            txns.append({"date": d, "merchant": "RENT PAYMENT AGENT", "category": "housing",
                         "amount": amt, "balance": round(balance, 2)})
        for _ in range(rng.randint(0, 3)):
            m, cat = rng.choice(MERCHANTS)
            if cat in ("income", "tax"):
                continue
            amt = -round(rng.uniform(4.5, 240.0), 2)
            balance += amt
            txns.append({"date": d, "merchant": m, "category": cat,
                         "amount": amt, "balance": round(balance, 2)})
        d += timedelta(days=1)
    return txns, round(balance, 2)


def write_westpac_shaped(txns, opening, closing, out: pathlib.Path) -> dict:
    """Separate debit/credit columns, DD/MM/YYYY, a comma inside a quoted field."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\r\n")   # CRLF, as real exports use
    w.writerow(["Date", "Narrative", "Debit Amount", "Credit Amount", "Balance"])
    for i, t in enumerate(txns):
        narrative = t["merchant"]
        if i == 3:
            # A comma inside a quoted field: splits the record if quoting is ignored.
            narrative = f'{narrative}, REF 8891'
        debit = f'{-t["amount"]:.2f}' if t["amount"] < 0 else ""
        credit = f'{t["amount"]:.2f}' if t["amount"] > 0 else ""
        w.writerow([t["date"].strftime("%d/%m/%Y"), narrative, debit, credit, f'{t["balance"]:.2f}'])
    out.write_bytes(buf.getvalue().encode("utf-8"))
    return {
        "shape": "westpac-shaped",
        "encoding": "utf-8",
        "line_ending": "crlf",
        "date_format": "DD/MM/YYYY",
        "amount_style": "separate_debit_credit",
        "difficulties": [
            "Debit and credit are separate columns, so the sign must be derived",
            "DD/MM/YYYY is ambiguous with MM/DD/YYYY for days 1-12",
            "Row 4's narrative contains a comma inside a quoted field",
            "CRLF line endings",
        ],
        "opening_balance": opening,
        "closing_balance": closing,
        "reconciles": True,
    }


def write_anz_shaped(txns, opening, closing, out: pathlib.Path) -> dict:
    """Single signed amount, D/M/YY, processor noise, CP1252 encoding."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Transaction Date", "Description", "Amount"])
    for i, t in enumerate(txns):
        desc = t["merchant"]
        if i % 7 == 0:
            desc = f"VISA PURCHASE {desc} CARD 4111"      # card suffix noise
        if i % 11 == 0:
            desc = f"{desc} – CAFE"                   # en dash, not in ASCII
        # D/M/YY with no zero padding, which breaks naive fixed-width parsing.
        w.writerow([f'{t["date"].day}/{t["date"].month}/{t["date"].strftime("%y")}',
                    desc, f'{t["amount"]:.2f}'])
    # Encoded CP1252, so a UTF-8-only reader corrupts the dash silently.
    out.write_bytes(buf.getvalue().encode("cp1252", errors="replace"))
    return {
        "shape": "anz-shaped",
        "encoding": "cp1252",
        "line_ending": "lf",
        "date_format": "D/M/YY",
        "amount_style": "single_signed",
        "difficulties": [
            "CP1252 encoding, not UTF-8 — a UTF-8-only reader corrupts the en dash silently",
            "D/M/YY without zero padding, and a two-digit year",
            "Processor prefixes and card suffixes in the description",
            "No balance column, so reconciliation must come from the declared balances",
        ],
        "opening_balance": opening,
        "closing_balance": closing,
        "reconciles": True,
    }


def write_ragged(txns, out: pathlib.Path) -> dict:
    """A trailing-comma row and a short row, as real exports contain."""
    lines = ["Date,Description,Amount,Balance"]
    for i, t in enumerate(txns[:40]):
        row = f'{t["date"].isoformat()},{t["merchant"]},{t["amount"]:.2f},{t["balance"]:.2f}'
        if i == 10:
            row += ","                     # trailing comma: one extra empty field
        if i == 20:
            row = f'{t["date"].isoformat()},{t["merchant"]}'   # short row
        lines.append(row)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {
        "shape": "ragged",
        "encoding": "utf-8",
        "difficulties": [
            "Row 11 has a trailing comma, producing one extra empty field",
            "Row 21 is short, missing amount and balance",
        ],
        "reconciles": False,
        "expected_behaviour": "Import must report both rows rather than silently padding them",
    }


def write_nonreconciling(txns, opening, out: pathlib.Path) -> dict:
    """Declared closing balance deliberately wrong, so the check can be shown to fire."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["Date", "Description", "Amount"])
    for t in txns[:30]:
        w.writerow([t["date"].isoformat(), t["merchant"], f'{t["amount"]:.2f}'])
    out.write_text(buf.getvalue(), encoding="utf-8")
    true_closing = round(opening + sum(t["amount"] for t in txns[:30]), 2)
    return {
        "shape": "non-reconciling",
        "encoding": "utf-8",
        "difficulties": [
            "The declared closing balance does not match the sum of the transactions",
        ],
        "opening_balance": opening,
        "declared_closing_balance": round(true_closing + 137.42, 2),
        "true_closing_balance": true_closing,
        "reconciles": False,
        "expected_behaviour": (
            "MK21.5's reconciliation check must fail prominently rather than "
            "proceeding. A statement that does not reconcile means extraction "
            "dropped or misread a transaction, and continuing produces a wrong "
            "budget presented with total confidence."
        ),
    }


INSTITUTION = "SAMPLE MUTUAL (FICTITIOUS)"
HOLDER = "A N EXAMPLE"
ADDRESS = "1 FIXTURE LANE TESTVILLE"
ACCOUNT = "EVERYDAY ACCESS  BSB 000-000  ACCOUNT ENDING 0000"


def rebalance(txns, opening):
    """Recompute running balances after an insertion; returns the closing balance."""
    bal = opening
    for t in txns:
        bal = round(bal + t["amount"], 2)
        t["balance"] = bal
    return bal


def gt_rows(txns):
    return [{"date": t["date"].isoformat(), "merchant": t["merchant"],
             "amount": t["amount"], "category": t["category"]} for t in txns]


# ── XLSX ──────────────────────────────────────────────────────────────────────

def excel_serial(d: date) -> int:
    """1900 date system, for dates after 1900-03-01 (every date here)."""
    return (d - date(1899, 12, 30)).days


def write_xlsx(txns, opening, closing, out: pathlib.Path) -> dict:
    sst = render.SharedStrings()
    rows: dict[int, list[str]] = {}
    rows[1] = [render.cell_s("A1", sst.add_rich(["SAMPLE MUTUAL", " (FICTITIOUS) - TRANSACTIONS"],
                                                 phonetic="サンプル"))]
    rows[2] = [render.cell_s("A2", sst.add(f"Account: {ACCOUNT}"))]
    rows[3] = [render.cell_s("A3", sst.add("Opening balance")),
               render.cell_n("B3", f"{opening:.2f}", render.STYLE_MONEY),
               render.cell_s("D3", sst.add("Closing balance")),
               render.cell_n("E3", f"{closing:.2f}", render.STYLE_MONEY)]
    # Row 4 is absent: rows are sparse too.
    rows[5] = [render.cell_s(f"{c}5", sst.add(h)) for c, h in
               zip("ABCDE", ("Date", "Description", "Reference", "Amount", "Balance"))]
    text_date_row = None
    for i, t in enumerate(txns):
        r = 6 + i
        d = t["date"]
        if text_date_row is None and 2 <= d.day <= 12 and d.day != d.month:
            # Typed in as text by whoever keyed the adjustment: DD/MM/YYYY, and ambiguous.
            text_date_row = r
            date_cell = render.cell_s(f"A{r}", sst.add(d.strftime("%d/%m/%Y")))
        else:
            date_cell = render.cell_n(f"A{r}", str(excel_serial(d)), render.STYLE_DATE)
        cells = [date_cell, render.cell_s(f"B{r}", sst.add(t["merchant"]))]
        if t.get("reference"):
            cells.append(render.cell_s(f"C{r}", sst.add(t["reference"])))
        cells.append(render.cell_n(f"D{r}", f"{t['amount']:.2f}", render.STYLE_MONEY))
        prev = "B3" if i == 0 else f"E{r - 1}"
        cells.append(render.cell_f(f"E{r}", f"{prev}+D{r}", f"{t['balance']:.2f}", render.STYLE_MONEY))
        rows[r] = cells
    out.write_bytes(render.xlsx(render.sheet_xml(rows), sst))
    return {
        "shape": "spreadsheet-export",
        "format": "xlsx",
        "sheet": "Transactions",
        "header_row": 5,
        "first_transaction_row": 6,
        "date_format": "Excel 1900 serial with number format 14; one date is TEXT DD/MM/YYYY",
        "amount_style": "single_signed",
        "text_date_row": text_date_row,
        "difficulties": [
            "Text cells are shared-string indices (as Excel writes them), not inline text",
            "The title in A1 is one shared string stored as two rich-text runs plus a phonetic "
            "run that is not part of its text",
            "Three title rows, then row 4 absent: the header is row 5, and rows are sparse",
            "Dates are serial numbers whose type is only in styles.xml (numFmt 14)",
            f"Row {text_date_row}'s date is a text cell, DD/MM/YYYY, ambiguous with MM/DD/YYYY",
            "The Reference column is empty on most rows and those cells are omitted, so "
            "columns cannot be inferred from cell order",
            "Balance is a formula; only its cached value is a number",
            "Two transactions are genuinely identical (same day, merchant and amount): both "
            "are real and neither may be removed as a duplicate",
        ],
        "opening_balance": opening,
        "closing_balance": closing,
        "reconciles": True,
    }


# ── Text PDF and its scan ─────────────────────────────────────────────────────

ROWS_PER_PAGE = 26


def statement_pages(txns, opening, closing, start: date, end: date):
    """Lay the statement out as pages of rows, shared by the PDF and the scan.

    Each row is a dict: kind ('txn', 'wrap', 'carried', 'brought'), date text, description,
    debit, credit and balance text. The balance lines at the page break are not transactions.
    """
    body = []
    for i, t in enumerate(txns):
        body.append({"kind": "txn", "date": t["date"].strftime("%d/%m/%y"),
                     "desc": t["merchant"],
                     "debit": f"{-t['amount']:,.2f}" if t["amount"] < 0 else "",
                     "credit": f"{t['amount']:,.2f}" if t["amount"] > 0 else "",
                     "balance": f"{t['balance']:,.2f}", "index": i})
        if t.get("reference"):
            body.append({"kind": "wrap", "date": "", "desc": t["reference"], "debit": "",
                         "credit": "", "balance": "", "index": i})
    pages, cur = [], []
    for row in body:
        if len(cur) == ROWS_PER_PAGE:
            bal = next(r["balance"] for r in reversed(cur) if r["kind"] == "txn")
            cur.append({"kind": "carried", "date": "", "desc": "BALANCE CARRIED FORWARD",
                        "debit": "", "credit": "", "balance": bal})
            pages.append(cur)
            cur = [{"kind": "brought", "date": "", "desc": "BALANCE BROUGHT FORWARD",
                    "debit": "", "credit": "", "balance": bal}]
        cur.append(row)
    pages.append(cur)
    header = [
        INSTITUTION,
        "TRANSACTION STATEMENT",
        f"ACCOUNT HOLDER: {HOLDER}",
        ADDRESS,
        ACCOUNT,
        f"STATEMENT PERIOD: {start.strftime('%d/%m/%y')} TO {end.strftime('%d/%m/%y')}",
        f"OPENING BALANCE: ${opening:,.2f}   CLOSING BALANCE: ${closing:,.2f}",
    ]
    return header, pages


PDF_COLS = {"date": 50, "desc": 105, "debit": 400, "credit": 470, "balance": 545}   # right edges for amounts
SPLIT_ROW = 5          # this row's description is drawn as two separate text objects


def write_text_pdf(header, pages, out: pathlib.Path) -> dict:
    size, lead = 9, 16
    pdf_pages = []
    for pno, rows in enumerate(pages, 1):
        draws = []
        y = 790
        for j, line in enumerate(header):
            draws.append((50, y, 13 if j == 0 else 9, line))
            y -= 18 if j == 0 else 13
        draws.append((460, 790, 9, f"PAGE {pno} OF {len(pages)}"))
        y -= 10
        for name, label in (("date", "DATE"), ("desc", "DESCRIPTION")):
            draws.append((PDF_COLS[name], y, size, label))
        for name, label in (("debit", "DEBIT"), ("credit", "CREDIT"), ("balance", "BALANCE")):
            draws.append((PDF_COLS[name] - render.helv_width(label, size), y, size, label))
        top = y - lead
        # Column-major: every date on the page, then every description, then each amount
        # column. Stream order is therefore not reading order.
        for j, r in enumerate(rows):
            if r["date"]:
                draws.append((PDF_COLS["date"], top - j * lead, size, r["date"]))
        for j, r in enumerate(rows):
            d = r["desc"]
            if r["kind"] == "txn" and r.get("index") == SPLIT_ROW and len(d) > 6:
                w = render.helv_width(d[:6], size)
                draws.append((PDF_COLS["desc"], top - j * lead, size, d[:6]))
                draws.append((PDF_COLS["desc"] + w, top - j * lead, size, d[6:]))
            else:
                draws.append((PDF_COLS["desc"] + (12 if r["kind"] == "wrap" else 0),
                              top - j * lead, size, d))
        for name in ("debit", "credit", "balance"):
            for j, r in enumerate(rows):
                if r[name]:
                    draws.append((PDF_COLS[name] - render.helv_width(r[name], size),
                                  top - j * lead, size, r[name]))
        pdf_pages.append(draws)
    out.write_bytes(render.pdf(pdf_pages))
    return {
        "shape": "text-pdf",
        "format": "pdf",
        "pages": len(pages),
        "date_format": "DD/MM/YY",
        "amount_style": "separate_debit_credit",
        "difficulties": [
            "The content stream draws column by column (every date, then every description, "
            "then each amount column), so extraction in stream order does not give rows; rows "
            "come from each string's position",
            f"Transaction {SPLIT_ROW + 1}'s description is two text objects side by side, so it "
            "must be joined by position, not taken as two fields",
            "DD/MM/YY with a two-digit year, ambiguous with MM/DD/YY for days 1-12",
            "Amounts carry thousands separators (2,163.35)",
            "Two pages: BALANCE CARRIED FORWARD ends page 1 and BALANCE BROUGHT FORWARD opens "
            "page 2 with the same figure; neither is a transaction",
            "Some descriptions wrap onto a second line with no date or amount",
        ],
        "reconciles": True,
    }


SCAN_W, SCAN_H = 1000, 1300
SCAN_SCALE = 2
# sin and cos of 1.75 degrees in 16-bit fixed point: round(65536*sin), round(65536*cos).
SCAN_SIN_Q, SCAN_COS_Q = 2001, 65505
SCAN_SHIFT = (17, -11)


def scan_lines(header, rows):
    """Page 1 as monospaced text lines: (x, y, text) in page pixels."""
    cw = 6 * SCAN_SCALE
    x0, y = 50, 50
    out = []
    for j, line in enumerate(header):
        out.append((x0, y, line))
        y += 30 if j == 0 else 22
    y += 14

    def cols(date_s, desc, debit, credit, bal):
        line = [" "] * 74
        def put(col, s):
            for k, c in enumerate(s):
                if col + k < len(line):
                    line[col + k] = c
        put(0, date_s)
        put(10, desc[:30])
        put(52 - len(debit), debit)
        put(62 - len(credit), credit)
        put(74 - len(bal), bal)
        return "".join(line).rstrip()

    out.append((x0, y, cols("DATE", "DESCRIPTION", "DEBIT", "CREDIT", "BALANCE")))
    y += 26
    for r in rows:
        desc = ("  " + r["desc"]) if r["kind"] == "wrap" else r["desc"]
        out.append((x0, y, cols(r["date"], desc, r["debit"], r["credit"], r["balance"])))
        y += 22
    assert y < SCAN_H - 40, "scan page overflows"
    assert all(len(t) * cw + x0 < SCAN_W for _, _, t in out), "scan line too wide"
    return out


def write_scan(header, pages, seed: int, out: pathlib.Path) -> dict:
    lines = scan_lines(header, pages[0])
    px = render.scan(lines, SCAN_W, SCAN_H, seed=seed, scale=SCAN_SCALE,
                     rot_sin_q=SCAN_SIN_Q, rot_cos_q=SCAN_COS_Q,
                     shift_x=SCAN_SHIFT[0], shift_y=SCAN_SHIFT[1])
    out.write_bytes(render.png(SCAN_W, SCAN_H, px))
    return {
        "shape": "scanned-image",
        "format": "png",
        "renders": "page 1 of statement-text.pdf's statement",
        "size_px": [SCAN_W, SCAN_H],
        "date_format": "DD/MM/YY",
        "difficulties": [
            "Misaligned scan: the sheet is rotated 1.75 degrees and shifted, so the lid shows "
            "along two edges, and across the page a row falls about 27 pixels, more than the "
            "22-pixel line pitch: without deskewing, an amount lines up with the row below it",
            "No text layer at all: every character needs recognition",
            "Speckle, a vertical streak across the amount columns and two punch holes in the "
            "left margin",
            "Uneven ink from character to character, and the paper darkens towards the bottom",
            "Page 1 of 2 only: its transactions reconcile to BALANCE CARRIED FORWARD, not to "
            "the statement's closing balance",
            "DD/MM/YY with a two-digit year, and amounts with thousands separators",
        ],
        "reconciles": "to the carried-forward balance only",
    }


def content_digest(name: str, data: bytes) -> str:
    """What must stay identical: the bytes, except a PNG's pixels (its deflate stream is the
    zlib build's choice, not ours)."""
    if name.endswith(".png"):
        w, h, px = render.png_pixels(data)
        return "pixels:" + hashlib.sha256(b"%d,%d," % (w, h) + px).hexdigest()
    return "sha256:" + hashlib.sha256(data).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--out", type=pathlib.Path, default=None)
    ap.add_argument("--verify", action="store_true",
                    help="check reconciliation into a scratch directory, leaving the committed files alone")
    args = ap.parse_args()

    out = args.out or (pathlib.Path(tempfile.mkdtemp(prefix="mk21-verify-")) if args.verify else HERE)
    out.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)

    # Two statements that share June 2026. The second opens with the first's June
    # transactions, the same rows, as a download of an overlapping period does, so
    # importing both double-counts June unless it deduplicates.
    txns_a, close_a = statement(rng, date(2026, 4, 1), 90, 4210.55)
    shared = [dict(t) for t in txns_a if t["date"] >= date(2026, 6, 1)]
    open_b = round(shared[0]["balance"] - shared[0]["amount"], 2)
    rest_b, close_b = statement(rng, date(2026, 6, 30), 61, close_a)
    txns_b = shared + rest_b

    # A January statement for the workbook, with two genuinely identical coffees.
    rng_x = random.Random(args.seed + 1)
    txns_x, _ = statement(rng_x, date(2026, 1, 1), 31, 1520.40)
    twin = {"date": date(2026, 1, 14), "merchant": "SQ *THE LOCAL CAFE", "category": "eating out",
            "amount": -4.80, "balance": 0.0}
    at = next(i for i, t in enumerate(txns_x) if t["date"] > twin["date"])
    txns_x[at:at] = [dict(twin), dict(twin)]
    for t in txns_x:
        if t["merchant"] == "ORIGIN ENERGY BPAY":
            t["reference"] = "BPAY REF 00417"
    close_x = rebalance(txns_x, 1520.40)

    # A February statement for the text PDF and its scan.
    rng_p = random.Random(args.seed + 2)
    txns_p, close_p = statement(rng_p, date(2026, 2, 1), 28, 2890.15)
    for t in txns_p:
        if t["merchant"] == "TRANSFER TO SAVINGS":
            t["reference"] = "REF 00123 SAVINGS GOAL"
    header, pages = statement_pages(txns_p, 2890.15, close_p, date(2026, 2, 1), date(2026, 2, 28))
    page1 = [txns_p[r["index"]] for r in pages[0] if r["kind"] == "txn"]
    carried = next(r["balance"] for r in pages[0] if r["kind"] == "carried")

    meta = {
        "_note": (
            "Synthetic bank statements for story MK21. Every amount, reference and holder "
            "detail is invented. Nothing here corresponds to a real person or account. "
            "Ground truth is included so an import can be scored rather than eyeballed."
        ),
        "seed": args.seed,
        "files": {},
        "ground_truth": {},
        "overlap": {
            "files": ["westpac-shaped.csv", "anz-shaped.csv"],
            "shared_transactions": len(shared),
            "description": (
                "anz-shaped.csv opens with the same June 2026 transactions that close "
                "westpac-shaped.csv, so importing both must deduplicate on date, merchant and "
                "amount rather than double-counting. This is the common real-world case when "
                "somebody imports several months that share a boundary."
            ),
        },
    }

    files = {
        "westpac-shaped.csv": write_westpac_shaped(txns_a, 4210.55, close_a, out / "westpac-shaped.csv"),
        "anz-shaped.csv": write_anz_shaped(txns_b, open_b, close_b, out / "anz-shaped.csv"),
        "ragged.csv": write_ragged(txns_a, out / "ragged.csv"),
        "non-reconciling.csv": write_nonreconciling(txns_a, 4210.55, out / "non-reconciling.csv"),
        "spreadsheet-export.xlsx": write_xlsx(txns_x, 1520.40, close_x, out / "spreadsheet-export.xlsx"),
        "statement-text.pdf": write_text_pdf(header, pages, out / "statement-text.pdf"),
        "statement-scan.png": write_scan(header, pages, args.seed + 3, out / "statement-scan.png"),
    }
    files["statement-text.pdf"].update(opening_balance=2890.15, closing_balance=close_p)
    files["statement-scan.png"].update(opening_balance=2890.15, carried_forward_balance=float(carried.replace(",", "")))
    meta["files"] = files
    meta["ground_truth"]["westpac-shaped.csv"] = gt_rows(txns_a)
    meta["ground_truth"]["anz-shaped.csv"] = gt_rows(txns_b)
    meta["ground_truth"]["spreadsheet-export.xlsx"] = gt_rows(txns_x)
    meta["ground_truth"]["statement-text.pdf"] = gt_rows(txns_p)
    meta["ground_truth"]["statement-scan.png"] = gt_rows(page1)

    # Verify the reconciling fixtures actually reconcile, or the fixture lies.
    failures = 0
    for name, txns, opening, closing in (
        ("westpac-shaped.csv", txns_a, 4210.55, close_a),
        ("anz-shaped.csv", txns_b, open_b, close_b),
        ("spreadsheet-export.xlsx", txns_x, 1520.40, close_x),
        ("statement-text.pdf", txns_p, 2890.15, close_p),
        ("statement-scan.png", page1, 2890.15, files["statement-scan.png"]["carried_forward_balance"]),
    ):
        computed = round(opening + sum(t["amount"] for t in txns), 2)
        if abs(computed - closing) > 0.01:
            print(f"FAIL {name}: transactions sum to {computed}, declared closing {closing}",
                  file=sys.stderr)
            failures += 1
        else:
            print(f"ok   {name}: {len(txns)} txns reconcile {opening} -> {closing}")

    # The overlap is real: the shared rows are identical in both files' ground truth.
    a_rows = {json.dumps(r, sort_keys=True) for r in gt_rows(txns_a)}
    if not shared or any(json.dumps(r, sort_keys=True) not in a_rows for r in gt_rows(shared)):
        print("FAIL the two CSV statements share no transactions, so there is nothing to deduplicate",
              file=sys.stderr)
        failures += 1
    else:
        print(f"ok   {len(shared)} June transactions appear in both CSV statements")

    nr = files["non-reconciling.csv"]
    if nr["declared_closing_balance"] == nr["true_closing_balance"]:
        print("FAIL non-reconciling.csv actually reconciles, so it tests nothing", file=sys.stderr)
        failures += 1
    else:
        print(f"ok   non-reconciling.csv: declared {nr['declared_closing_balance']} "
              f"vs true {nr['true_closing_balance']} — the check has something to catch")

    # Confirm the encodings are genuinely what they claim.
    anz = (out / "anz-shaped.csv").read_bytes()
    try:
        anz.decode("utf-8")
        print("FAIL anz-shaped.csv decodes as UTF-8, so it does not test encoding handling",
              file=sys.stderr)
        failures += 1
    except UnicodeDecodeError:
        print("ok   anz-shaped.csv is genuinely not UTF-8 decodable")

    if failures:
        return 1
    if not args.verify:
        (out / "ground-truth.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
        manifest = {
            "_note": ("What each fixture is, what it contains and which difficulties it carries. "
                      "Regenerate with generate.py; test_fixtures.py fails if any digest moves."),
            "seed": args.seed,
            "files": {
                name: {
                    "digest": content_digest(name, (out / name).read_bytes()),
                    "bytes": (out / name).stat().st_size,
                    "transactions": len(meta["ground_truth"].get(name, [])) or None,
                    **{k: v for k, v in info.items() if k in (
                        "shape", "format", "encoding", "date_format", "amount_style", "pages",
                        "renders", "difficulties", "reconciles")},
                }
                for name, info in files.items()
            },
        }
        manifest["files"]["ground-truth.json"] = {
            "digest": content_digest("ground-truth.json", (out / "ground-truth.json").read_bytes()),
            "difficulties": [],
            "contains": "every file's expected transactions, balances and difficulties",
        }
        (out / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwritten: {len(files)} fixtures + ground-truth.json + manifest.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
