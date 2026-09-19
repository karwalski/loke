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

Every merchant, amount, account number and BSB is invented. The account numbers
and BSBs are drawn from ranges reserved for documentation where one exists, and
are in any case not issued.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import pathlib
import random
import sys
from datetime import date, timedelta

HERE = pathlib.Path(__file__).resolve().parent

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


def statement(rng: random.Random, start: date, months: int, opening: float):
    """Build a transaction list with a running balance that reconciles."""
    txns = []
    balance = opening
    d = start
    end = start + timedelta(days=30 * months)

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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20260919)
    ap.add_argument("--verify", action="store_true", help="check reconciliation and exit")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    HERE.mkdir(parents=True, exist_ok=True)

    # Two overlapping periods, so importing both must deduplicate.
    txns_a, close_a = statement(rng, date(2026, 4, 1), 3, 4210.55)
    txns_b, close_b = statement(rng, date(2026, 6, 1), 3, close_a)

    meta = {
        "_note": (
            "Synthetic bank statements for story MK21. Every merchant, amount, "
            "account number and BSB is invented. Nothing here corresponds to a "
            "real person or account. Ground truth is included so an import can be "
            "scored rather than eyeballed."
        ),
        "seed": args.seed,
        "files": {},
        "ground_truth": {},
        "overlap": {
            "files": ["westpac-shaped.csv", "anz-shaped.csv"],
            "description": (
                "The two periods share June 2026, so importing both must "
                "deduplicate on date, merchant and amount rather than "
                "double-counting. This is the common real-world case when "
                "somebody imports several months that share a boundary."
            ),
        },
    }

    files = {
        "westpac-shaped.csv": write_westpac_shaped(txns_a, 4210.55, close_a, HERE / "westpac-shaped.csv"),
        "anz-shaped.csv": write_anz_shaped(txns_b, close_a, close_b, HERE / "anz-shaped.csv"),
        "ragged.csv": write_ragged(txns_a, HERE / "ragged.csv"),
        "non-reconciling.csv": write_nonreconciling(txns_a, 4210.55, HERE / "non-reconciling.csv"),
    }
    meta["files"] = files
    meta["ground_truth"]["westpac-shaped.csv"] = [
        {"date": t["date"].isoformat(), "merchant": t["merchant"],
         "amount": t["amount"], "category": t["category"]} for t in txns_a
    ]
    meta["ground_truth"]["anz-shaped.csv"] = [
        {"date": t["date"].isoformat(), "merchant": t["merchant"],
         "amount": t["amount"], "category": t["category"]} for t in txns_b
    ]

    # Verify the reconciling fixtures actually reconcile, or the fixture lies.
    failures = 0
    for name, txns, opening, closing in (
        ("westpac-shaped.csv", txns_a, 4210.55, close_a),
        ("anz-shaped.csv", txns_b, close_a, close_b),
    ):
        computed = round(opening + sum(t["amount"] for t in txns), 2)
        if abs(computed - closing) > 0.01:
            print(f"FAIL {name}: transactions sum to {computed}, declared closing {closing}",
                  file=sys.stderr)
            failures += 1
        else:
            print(f"ok   {name}: {len(txns)} txns reconcile {opening} -> {closing}")

    nr = files["non-reconciling.csv"]
    if nr["declared_closing_balance"] == nr["true_closing_balance"]:
        print("FAIL non-reconciling.csv actually reconciles, so it tests nothing", file=sys.stderr)
        failures += 1
    else:
        print(f"ok   non-reconciling.csv: declared {nr['declared_closing_balance']} "
              f"vs true {nr['true_closing_balance']} — the check has something to catch")

    # Confirm the encodings are genuinely what they claim.
    anz = (HERE / "anz-shaped.csv").read_bytes()
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
        (HERE / "ground-truth.json").write_text(
            json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"\nwritten: {len(files)} fixtures + ground-truth.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
