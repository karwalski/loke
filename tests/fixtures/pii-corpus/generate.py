#!/usr/bin/env python3
"""Generate a span-labelled synthetic PII corpus (story AD1.1).

Why generated rather than hand-written
--------------------------------------
Character spans have to be exact or every recall number computed against the
corpus is wrong. Building each example from a template with known insertion
points makes the spans correct by construction, rather than correct if somebody
counted carefully.

What is in it
-------------
Three kinds of example, because a corpus of positives alone measures nothing
useful:

* **positive**  — contains entities that MUST be detected. Drives recall, which
  is the metric that matters: a missed entity leaks, whereas a spurious one only
  costs utility.
* **negative**  — contains near-miss strings that must NOT be reported. Drives
  precision, and these are where loke's current patterns are weakest.
* **adversarial** — formatting that a naive pattern misses: case variation,
  separators, entities inside URLs or JSON, digits split across lines.

Every value is synthetic. Where a real identifier format carries a checksum, the
generator can emit both checksum-valid and checksum-invalid variants, so a
detector that validates checksums can be distinguished from one that only
pattern-matches. Nothing here corresponds to a real person, account or number.

Known gaps in what loke detects, encoded deliberately
----------------------------------------------------
`packages/core/src/privacy/patterns.tk` defines the regex layer's patterns. Some
Australian identifiers that loke's own demo data and regulatory presets centre on
have **no detector at all** — ACN. Those appear in the corpus marked
`expected_detected: false` so that a recall figure computed from it reflects
reality rather than only the cases loke already covers. Medicare, BSB and bank
account numbers were in that list until RG1.7 gave them detectors; their cases are
now scored, and RG1.7 added their formats and near misses at the end. RG1.7a did
the same for Centrelink CRN, passport, driver licence and super member numbers,
each detected only after the words that name it.

Usage
-----
    python3 tests/fixtures/pii-corpus/generate.py --out corpus.jsonl
    python3 tests/fixtures/pii-corpus/generate.py --verify   # check spans
"""

from __future__ import annotations

import argparse
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_OUT = HERE / "corpus.jsonl"

# --- Synthetic identifier construction -----------------------------------
# Format-valid, checksum-correct where the format defines one, and not real.


def tfn_valid(rng: random.Random) -> str:
    """Australian Tax File Number with a correct weighted-modulus check digit."""
    weights = [1, 4, 3, 7, 5, 8, 6, 9, 10]
    while True:
        digits = [rng.randint(0, 9) for _ in range(8)]
        for last in range(10):
            candidate = digits + [last]
            if sum(w * d for w, d in zip(weights, candidate)) % 11 == 0:
                return "".join(map(str, candidate))


def tfn_invalid(rng: random.Random) -> str:
    """Nine digits that match the TFN pattern but fail its checksum."""
    weights = [1, 4, 3, 7, 5, 8, 6, 9, 10]
    while True:
        d = [rng.randint(0, 9) for _ in range(9)]
        if sum(w * x for w, x in zip(weights, d)) % 11 != 0:
            return "".join(map(str, d))


def abn_valid(rng: random.Random) -> str:
    """Australian Business Number with a correct modulus-89 check."""
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    while True:
        rest = [rng.randint(0, 9) for _ in range(10)]
        for first in range(1, 10):
            digits = [first] + rest
            adjusted = [digits[0] - 1] + digits[1:]
            if sum(w * d for w, d in zip(weights, adjusted)) % 89 == 0:
                return "".join(map(str, digits))


MEDICARE_WEIGHTS = [1, 3, 7, 9, 1, 3, 7, 9]


def medicare_valid(rng: random.Random) -> str:
    """Medicare card number (ten digits) with a correct check digit: first digit 2-6,
    ninth digit = weighted sum of the first eight mod 10, tenth the issue number."""
    while True:
        first = rng.randint(2, 6)
        rest = [rng.randint(0, 9) for _ in range(7)]
        digits = [first] + rest
        check = sum(w * d for w, d in zip(MEDICARE_WEIGHTS, digits)) % 10
        issue = rng.randint(1, 9)
        return f"{''.join(map(str, digits))}{check}{issue}"


def medicare_invalid(rng: random.Random) -> str:
    """Ten digits in Medicare's shape (first digit 2-6) whose check digit is wrong."""
    good = medicare_valid(rng)
    wrong = (int(good[8]) + rng.randint(1, 9)) % 10
    return good[:8] + str(wrong) + good[9]


def medicare_bad_first(rng: random.Random) -> str:
    """Ten digits whose check digit is right but whose first digit (7-9) no card has."""
    digits = [rng.randint(7, 9)] + [rng.randint(0, 9) for _ in range(7)]
    check = sum(w * d for w, d in zip(MEDICARE_WEIGHTS, digits)) % 10
    return f"{''.join(map(str, digits))}{check}{rng.randint(1, 9)}"


def tfn_invalid_dashed(rng: random.Random) -> str:
    v = tfn_invalid(rng)
    return f"{v[:3]}-{v[3:6]}-{v[6:]}"


def bsb_nonzero(rng: random.Random) -> str:
    return f"{rng.randint(10, 99)}{rng.randint(0, 9)}{rng.randint(100, 999)}"


NHS_WEIGHTS = [10, 9, 8, 7, 6, 5, 4, 3, 2]


def _nhs_check(nine: list[int]) -> int:
    """NHS Data Dictionary, NHS NUMBER: 11 minus (weighted sum mod 11); 11 -> 0; 10 means
    the number is invalid and never issued (returned as 10)."""
    c = 11 - sum(w * d for w, d in zip(NHS_WEIGHTS, nine)) % 11
    return 0 if c == 11 else c


def nhs_valid(rng: random.Random) -> str:
    """Ten digits with a correct NHS modulus 11 check digit. The first digit is 7, so
    no Australian phone (0...) or Medicare (2-6) pattern can also claim the run."""
    while True:
        nine = [7] + [rng.randint(0, 9) for _ in range(8)]
        c = _nhs_check(nine)
        if c != 10:
            return "".join(map(str, nine)) + str(c)


def nhs_invalid(rng: random.Random) -> str:
    """An NHS-shaped ten digits whose check digit is wrong."""
    v = nhs_valid(rng)
    return v[:9] + str((int(v[9]) + rng.randint(1, 9)) % 10)


def nhs_check_ten(rng: random.Random) -> str:
    """Nine digits whose check computes to 10, with any tenth digit: never issued."""
    while True:
        nine = [7] + [rng.randint(0, 9) for _ in range(8)]
        if _nhs_check(nine) == 10:
            return "".join(map(str, nine)) + str(rng.randint(0, 9))


NINO_FIRST = "ABCEGHJKLMNOPRSTWXYZ"   # HMRC NIM39110: never D F I Q U V
NINO_SECOND = "ABCEGHJKLMNPRSTWXYZ"   # nor O as the second letter
NINO_UNUSED = {"BG", "GB", "KN", "NK", "NT", "TN", "ZZ"}


def nino_parts(rng: random.Random) -> tuple[str, str, str]:
    """A NINO's prefix, six digits and suffix, following HMRC NIM39110's rules."""
    while True:
        p = rng.choice(NINO_FIRST) + rng.choice(NINO_SECOND)
        if p not in NINO_UNUSED:
            return p, "".join(str(rng.randint(0, 9)) for _ in range(6)), rng.choice("ABCD")


def sort_code_nonzero(rng: random.Random) -> str:
    return f"{rng.randint(10, 99)}{rng.randint(10, 99)}{rng.randint(10, 99)}"


def uk_driver_number(rng: random.Random, surname: str, female: bool) -> str:
    """DVLA leaflet INS57P's sixteen characters: surname (padded with 9), decade, month
    (+50 for a woman), day, year, two initials (9 for none), three check characters."""
    year = rng.randint(1950, 2005)
    month = rng.randint(1, 12) + (50 if female else 0)
    initials = rng.choice("ABCDEJKLMPRST") + rng.choice(["9", "A", "M", "R"])
    checks = "".join(rng.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(2))
    return (f"{(surname.upper() + '99999')[:5]}{(year // 10) % 10}{month:02d}"
            f"{rng.randint(1, 28):02d}{year % 10}{initials}9{checks}")


def nric_like(rng: random.Random, series: str) -> str:
    """A series letter, seven digits and a check letter. The letter is computed with the
    algorithm in circulation (Ngiam 2003), which the ICA has not published, so loke does
    not validate it; it is here only so the examples look like real numbers."""
    d = [rng.randint(0, 9) for _ in range(7)]
    total = sum(w * x for w, x in zip([2, 7, 6, 5, 4, 3, 2], d)) + (4 if series in "TG" else 0)
    table = "JZIHGFEDCBA" if series in "ST" else "XWUTRQPNMLK"
    return f"{series}{''.join(map(str, d))}{table[total % 11]}"


def luhn_valid(rng: random.Random, prefix: str, length: int) -> str:
    """Card-shaped number passing the Luhn check."""
    body = prefix + "".join(str(rng.randint(0, 9)) for _ in range(length - len(prefix) - 1))
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return body + str((10 - total % 10) % 10)


def luhn_invalid(rng: random.Random, prefix: str, length: int) -> str:
    n = luhn_valid(rng, prefix, length)
    last = (int(n[-1]) + 1) % 10
    return n[:-1] + str(last)


def bsb(rng: random.Random) -> str:
    return f"{rng.randint(10, 99)}{rng.randint(0, 9)}-{rng.randint(100, 999)}"


def acn(rng: random.Random) -> str:
    return f"{rng.randint(100, 999)} {rng.randint(100, 999)} {rng.randint(100, 999)}"


# --- Case construction ----------------------------------------------------

Entity = dict  # {type, value, start, end, expected_detected, note?}


def build(template: str, slots: dict[str, tuple[str, str, bool, str | None]]) -> tuple[str, list[Entity]]:
    """Fill a template and return the text plus exact spans.

    `slots` maps a `{name}` placeholder to (entity_type, value,
    expected_detected, note). Spans are computed from the assembled string, so
    they cannot drift from the text.
    """
    text = template
    entities: list[Entity] = []
    for name, (etype, value, expected, note) in slots.items():
        marker = "{" + name + "}"
        idx = text.index(marker)
        text = text[:idx] + value + text[idx + len(marker):]
    # Second pass: locate each value in the final text. Values are generated to
    # be distinctive, so a single occurrence is expected; if a value appears
    # more than once the case is rejected rather than guessed at.
    for name, (etype, value, expected, note) in slots.items():
        occurrences = [i for i in range(len(text)) if text.startswith(value, i)]
        if len(occurrences) != 1:
            raise ValueError(
                f"value {value!r} for slot {name} occurs {len(occurrences)} times; "
                "a corpus case must be unambiguous"
            )
        start = occurrences[0]
        e: Entity = {
            "type": etype,
            "value": value,
            "start": start,
            "end": start + len(value),
            "expected_detected": expected,
        }
        if note:
            e["note"] = note
        entities.append(e)
    entities.sort(key=lambda e: e["start"])
    return text, entities


def cases(rng: random.Random) -> list[dict]:
    out: list[dict] = []

    def add(kind: str, template: str, slots: dict, locale: str = "en-AU", note: str | None = None):
        text, ents = build(template, slots)
        case = {
            "id": f"{kind}-{len(out) + 1:04d}",
            "kind": kind,
            "locale": locale,
            "text": text,
            "entities": ents,
        }
        if note:
            case["note"] = note
        out.append(case)

    # --- Positives: must be detected -------------------------------------
    for _ in range(12):
        add("positive",
            "Please update the record for {name} — contact {email} or {phone}.",
            {"name": ("PERSON", rng.choice(["Priya Raghavan", "Tom Okafor", "Wei Zhang",
                                            "Aroha Ngata", "Sam Beauchamp"]), True, None),
             "email": ("EMAIL", f"{rng.choice(['p.raghavan','t.okafor','w.zhang'])}"
                                f"{rng.randint(10,99)}@example-corp.com.au", True, None),
             "phone": ("PHONE_AU", f"04{rng.randint(10000000, 99999999)}", True, None)})

    for _ in range(8):
        add("positive",
            "Tax file number {tfn} was supplied with ABN {abn} on the application.",
            {"tfn": ("AU_TFN", tfn_valid(rng), True, "checksum-valid"),
             "abn": ("AU_ABN", abn_valid(rng), True, "checksum-valid")})

    for _ in range(6):
        add("positive",
            "Card ending in the number {card} was declined; retry from {ip}.",
            {"card": ("CREDIT_CARD", luhn_valid(rng, "4", 16), True, "luhn-valid"),
             "ip": ("IP_V4", f"{rng.randint(11,223)}.{rng.randint(0,255)}."
                             f"{rng.randint(0,255)}.{rng.randint(1,254)}", True, None)})

    for _ in range(4):
        add("positive",
            "Deployment token {key} leaked in the build log at {url}.",
            {"key": ("API_KEY", "sk-" + "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789")
                                                for _ in range(28)), True, None),
             "url": ("URL", f"https://ci.example-corp.com.au/builds/{rng.randint(1000,9999)}", True, None)})

    # --- Australian identifiers added to the regex layer by RG1.7 ---------
    # These were expected_detected=False until RG1.7 gave Medicare, BSB and
    # bank account numbers detectors; they now count toward recall. AU_ACN still
    # has no detector and stays unscored.
    for _ in range(6):
        add("positive",
            "Claim lodged against Medicare number {mc} for the patient named {name}.",
            {"mc": ("AU_MEDICARE", medicare_valid(rng), True,
                    "checksum-valid; unspaced ten digits"),
             "name": ("PERSON", rng.choice(["Ruth Alkinbaya", "Jorge Silveira",
                                            "Mei Lin Choo"]), True, None)})

    for _ in range(4):
        add("positive",
            "Refund to BSB {bsb} account {acct}; entity ACN {acn}.",
            {"bsb": ("AU_BSB", bsb(rng), True, "after the word BSB"),
             "acct": ("BANK_ACCOUNT", str(rng.randint(10000000, 99999999)), True,
                      "after the word account; without it, indistinguishable from any 8-digit number"),
             "acn": ("AU_ACN", acn(rng), False, "no detector exists")})

    # --- Negatives: must NOT be reported ---------------------------------
    # These probe the specific weaknesses of the current patterns. au_tfn is
    # `\d{3}[\s-]?\d{3}[\s-]?\d{3}` with no checksum, so it matches any nine
    # digits; ssn_us has the same shape and collides with it.
    for _ in range(10):
        add("negative",
            "Invoice {inv} was raised against purchase order {po} in period {period}.",
            {"inv": ("NOT_PII", f"{rng.randint(100,999)} {rng.randint(100,999)} {rng.randint(100,999)}",
                     False, "nine digits — matches the au_tfn pattern, is not a TFN"),
             "po": ("NOT_PII", f"PO-{rng.randint(100000,999999)}", False, None),
             "period": ("NOT_PII", f"FY{rng.randint(20,29)}", False, None)})

    for _ in range(6):
        add("negative",
            "Reading {measure} recorded at sequence {seq}; version {ver}.",
            {"measure": ("NOT_PII", f"{rng.randint(100,999)}-{rng.randint(10,99)}-{rng.randint(1000,9999)}",
                         False, "matches the ssn_us pattern; is a measurement code"),
             "seq": ("NOT_PII", str(rng.randint(100000000, 999999999)), False,
                     "nine consecutive digits — matches au_tfn"),
             "ver": ("NOT_PII", f"{rng.randint(1,9)}.{rng.randint(0,20)}.{rng.randint(0,99)}", False, None)})

    for _ in range(4):
        add("negative",
            "Build {sem} published; latency budget {ms} ms; card-shaped test value {fake}.",
            {"sem": ("NOT_PII", f"2.{rng.randint(10,99)}.{rng.randint(100,999)}", False, None),
             "ms": ("NOT_PII", str(rng.randint(100, 999)), False, None),
             "fake": ("NOT_PII", luhn_invalid(rng, "4", 16), False,
                      "16 digits with a Visa prefix that fails Luhn; the credit_card "
                      "pattern has no Luhn check so it will be reported")})

    # --- Adversarial: correct entities, awkward presentation -------------
    for _ in range(6):
        local = rng.choice(["John.Smith", "A.MacLeod", "Sarah.OBrien"])
        add("adversarial",
            "Escalation raised by {email}; mirror of {email2}.",
            {"email": ("EMAIL", f"{local}@Example-Corp.COM.AU", True,
                       "mixed and upper case — the email pattern is lowercase-only "
                       "([a-z0-9._%+-]+@...), so this may be missed entirely"),
             "email2": ("EMAIL", f"{local.lower()}+tag{rng.randint(1,99)}@example-corp.com.au", True,
                        "plus-addressing")})

    for _ in range(4):
        # Two INDEPENDENT checksum-valid TFNs, not one value with its last digit
        # bumped. The bump was there only to keep the two spans unambiguous, and it
        # silently produced a checksum-INVALID number still labelled AU_TFN with
        # expected_detected=True — so the corpus asserted that a nine-digit run which
        # is not a TFN must be detected as one. That is 4 of the 16 AU_TFN positives,
        # and it is exactly the assertion that would have blocked gating au_tfn on its
        # checksum. A real TFN has a valid check digit; a fixture claiming otherwise is
        # measuring the wrong thing. Two draws are unambiguous and both valid.
        spaced = tfn_valid(rng)
        dashed = tfn_valid(rng)
        while dashed == spaced:
            dashed = tfn_valid(rng)
        add("adversarial",
            "TFN supplied as {spaced} on the form and {dashed} in the attachment.",
            {"spaced": ("AU_TFN", f"{spaced[:3]} {spaced[3:6]} {spaced[6:]}", True, "space-separated, checksum-valid"),
             "dashed": ("AU_TFN", f"{dashed[:3]}-{dashed[3:6]}-{dashed[6:]}", True, "dash-separated, checksum-valid")})

    for _ in range(4):
        add("adversarial",
            'Payload was {json} and the callback hit {url}.',
            {"json": ("EMAIL", f'contact{rng.randint(10,99)}@example-corp.com.au', True,
                      "entity embedded in a JSON-ish fragment"),
             "url": ("URL", f"https://api.example-corp.com.au/v1/u?e=user{rng.randint(10,99)}"
                            f"%40example-corp.com.au", True,
                     "an email is percent-encoded inside this URL; the url pattern "
                     "will match the URL but the embedded address is not separately reported")})

    # --- RG1.7: Australian identifier formats and their near misses ------
    # Appended after every earlier case so the cases above keep the values the
    # earlier measurements were taken on (the generator is seeded and sequential).
    for _ in range(4):
        v = medicare_valid(rng)
        add("adversarial",
            "Patient's Medicare card is {mc}, valid to 09/2027.",
            {"mc": ("AU_MEDICARE", f"{v[:4]} {v[4:9]} {v[9]}", True,
                    "4-5-1, spaced as printed on the card")})

    for sep in ("/", "-", "/"):
        v = medicare_valid(rng)
        add("adversarial",
            "Medicare {mc} covers the second child on the card.",
            {"mc": ("AU_MEDICARE", f"{v[:4]} {v[4:9]} {v[9]}{sep}{rng.randint(1, 9)}", True,
                    "with the individual reference number after a separator")})

    for _ in range(2):
        add("adversarial",
            "Medicare no. {mc} was quoted on the referral.",
            {"mc": ("AU_MEDICARE", medicare_valid(rng) + str(rng.randint(1, 9)), True,
                    "eleven digits: card number with the IRN run straight on")})

    for _ in range(4):
        add("negative",
            "Batch {batch} closed with {count} records.",
            {"batch": ("NOT_PII", medicare_invalid(rng), False,
                       "Medicare-shaped ten digits with a wrong check digit"),
             "count": ("NOT_PII", rng.choice(["forty", "sixty-two", "ninety"]), False, None)})

    for _ in range(2):
        add("negative",
            "Consignment {ref} left the depot.",
            {"ref": ("NOT_PII", medicare_bad_first(rng), False,
                     "Medicare check digit right but first digit 7-9, which no card has")})

    for _ in range(3):
        add("negative",
            "Ticket {ticket} was reopened by the service desk.",
            {"ticket": ("NOT_PII", tfn_invalid_dashed(rng), False,
                        "dash-separated nine digits failing the TFN checksum")})

    bsb_forms = [
        ("BSB: {bsb}, acct {acct}.", lambda b: f"{b[:3]} {b[3:]}", "space-separated after 'BSB:'",
         "after 'acct'"),
        ("Pay to bsb {bsb} account number: {acct} today.", lambda b: b, "unseparated after lower-case 'bsb'",
         "after 'account number:'"),
        ("BSB number {bsb} a/c {acct} for the refund.", lambda b: f"{b[:3]}-{b[3:]}", "after 'BSB number'",
         "after 'a/c'"),
        ("ACCOUNT NO. {acct} at BSB {bsb}.", lambda b: f"{b[:3]}-{b[3:]}", "upper-case context",
         "after 'ACCOUNT NO.'"),
    ]
    for template, fmt, bnote, anote in bsb_forms:
        add("adversarial", template,
            {"bsb": ("AU_BSB", fmt(bsb_nonzero(rng)), True, bnote),
             "acct": ("BANK_ACCOUNT", str(rng.randint(100000, 9999999999)), True, anote)})

    for _ in range(3):
        lo = rng.randint(100, 499)
        add("negative",
            "Pages {range} of the {doc} manual were revised.",
            {"range": ("NOT_PII", f"{lo}-{lo + rng.randint(100, 499)}", False,
                       "3-3 hyphenated digits with no BSB context: a page range"),
             "doc": ("NOT_PII", f"v{rng.randint(2, 9)}", False, None)})

    for _ in range(3):
        add("negative",
            "Order {order} shipped in {n} boxes.",
            {"order": ("NOT_PII", str(rng.randint(10000000, 99999999)), False,
                       "eight digits with no account context"),
             "n": ("NOT_PII", rng.choice(["two", "three", "five"]), False, None)})

    add("negative",
        "The form had BSB {bsb} entered as a placeholder.",
        {"bsb": ("NOT_PII", "000-000", False, "the all-zero BSB placeholder")})

    # --- RG1.7a: CRN, passport, driver licence, super member number -------
    # Appended after RG1.7's cases for the same reason. None of these has a check
    # loke can apply (the CRN check letter's algorithm is not published), so each
    # detector is gated on its words; the positives carry the words and the
    # negatives carry the same shapes without them, or the words without the shape.
    def nine_and_letter() -> tuple[str, str]:
        d = "".join(str(rng.randint(0, 9)) for _ in range(9))
        return d, rng.choice("ABCDEFGHJKLMNPRSTVWXYZ")

    crn_forms = [
        ("Centrelink CRN {crn} is on the claim.", lambda d, c: f"{d[:3]} {d[3:6]} {d[6:]}{c}",
         "after 'CRN', spaced 3-3-3 and the check letter"),
        ("Customer Reference Number: {crn} (Centrelink).", lambda d, c: f"{d}{c}",
         "after 'Customer Reference Number:', unspaced"),
        ("crn no. {crn} for the family payment.", lambda d, c: f"{d[:3]}-{d[3:6]}-{d[6:]}{c.lower()}",
         "lower case, hyphenated, lower-case letter"),
    ]
    for template, fmt, note in crn_forms:
        d, c = nine_and_letter()
        add("adversarial", template, {"crn": ("AU_CRN", fmt(d, c), True, note)})

    pp_forms = [
        ("Passport number: {pp}, expires 2031.", lambda: f"N{rng.randint(1000000, 9999999)}",
         "Australian: one letter and seven digits"),
        ("Her passport no. {pp} was sighted.", lambda: f"PA{rng.randint(1000000, 9999999)}",
         "Australian: two letters and seven digits"),
        ("UK PASSPORT {pp} on the booking.", lambda: str(rng.randint(100000000, 999999999)),
         "UK: nine digits, upper-case context"),
    ]
    for template, gen, note in pp_forms:
        add("adversarial", template, {"pp": ("PASSPORT", gen(), True, note)})

    dl_forms = [
        ("Driver's licence {dl} (NSW).", lambda: str(rng.randint(10000000, 99999999)),
         "NSW: eight digits after \"driver's licence\""),
        ("drivers license number: {dl} (VIC).", lambda: str(rng.randint(1000000000, 9999999999)),
         "VIC: ten digits, US spelling, no apostrophe"),
        ("Driver Licence No. {dl} (SA).", lambda: f"S{rng.randint(10000, 99999)}",
         "SA: a letter and five digits"),
        ("Driving licence {dl} (WA).", lambda: str(rng.randint(1000000, 9999999)),
         "WA: seven digits after 'driving licence'"),
    ]
    for template, gen, note in dl_forms:
        add("adversarial", template, {"dl": ("DRIVER_LICENCE", gen(), True, note)})

    sm_forms = [
        ("Superannuation fund member number {sm} for the rollover.",
         "after 'superannuation fund member number'"),
        ("Super member no. {sm} please.", "after 'super member no.'"),
    ]
    for template, note in sm_forms:
        add("adversarial", template,
            {"sm": ("AU_SUPER_MEMBER", str(rng.randint(100000000, 999999999)), True, note)})

    for _ in range(2):
        d, c = nine_and_letter()
        add("negative",
            "Part {part} ships on Tuesday.",
            {"part": ("NOT_PII", f"{d}{c}", False,
                      "nine digits and a letter with no CRN context: a part number")})

    add("negative",
        "BPAY biller 23796, CRN {ref} for the invoice.",
        {"ref": ("NOT_PII", f"1{rng.randint(100000000, 999999999)}", False,
                 "a BPAY customer reference number: digits only, no check letter")})

    add("negative",
        "Passport office ticket {t} was called.",
        {"t": ("NOT_PII", str(rng.randint(10000000, 99999999)), False,
               "the word passport, but not followed by a number")})

    add("negative",
        "Software licence number {n} was renewed.",
        {"n": ("NOT_PII", str(rng.randint(10000000, 99999999)), False,
               "a licence number that is not a driver licence")})

    add("negative",
        "Gym member number {n} checked in.",
        {"n": ("NOT_PII", str(rng.randint(100000000, 999999999)), False,
               "a member number with no superannuation context")})

    add("negative",
        "Driver's licence {y} renewal is due.",
        {"y": ("NOT_PII", str(rng.randint(2020, 2030)), False,
               "four digits after the words: a year, too short for a licence")})

    # --- RG1.7b and the UK/SG identifiers --------------------------------
    # Appended after RG1.7a's cases, so every earlier case keeps its values. NHS
    # numbers carry the NHS Data Dictionary's modulus 11 check and are gated on the
    # word NHS; NINOs follow HMRC NIM39110's prefix rules; driver numbers follow DVLA
    # leaflet INS57P's structure; sort codes and NRIC/FIN numbers are gated on their
    # words (no published check). The near misses break exactly one rule each.
    for template, fmt, note in [
        ("NHS number {nhs} is on the referral.", lambda v: f"{v[:3]} {v[3:6]} {v[6:]}",
         "3-3-4 as printed, after 'NHS number'"),
        ("NHS No: {nhs} (GP practice copy).", lambda v: v, "unspaced, after 'NHS No:'"),
        ("Patient nhs no. {nhs} was re-registered.", lambda v: f"{v[:3]}-{v[3:6]}-{v[6:]}",
         "hyphenated, lower-case context"),
    ]:
        add("adversarial", template, {"nhs": ("UK_NHS_NUMBER", fmt(nhs_valid(rng)), True, note)})

    for template, fmt, note in [
        ("National Insurance number {ni} on the P45.", lambda p, d, s: f"{p}{d}{s}", "unspaced"),
        ("Her NI number is {ni}, per the payslip.", lambda p, d, s: f"{p} {d[:2]} {d[2:4]} {d[4:]} {s}",
         "spaced in pairs, as HMRC prints it"),
        ("ni: {ni}", lambda p, d, s: f"{p}{d}{s}".lower(), "lower case"),
    ]:
        p, d, s = nino_parts(rng)
        add("adversarial", template, {"ni": ("UK_NINO", fmt(p, d, s), True, note)})

    for template, fmt, note in [
        ("Sort code {sc} for the transfer.", lambda v: f"{v[:2]}-{v[2:4]}-{v[4:]}", "nn-nn-nn after 'sort code'"),
        ("sort-code: {sc}", lambda v: v, "unseparated after 'sort-code:'"),
    ]:
        add("adversarial", template, {"sc": ("UK_SORT_CODE", fmt(sort_code_nonzero(rng)), True, note)})

    for surname, female, spaced, note in [
        ("MORGAN", False, False, "male, five surname letters"),
        ("LEE", True, False, "female (month + 50), surname padded with 9"),
        ("OKAFOR", False, True, "spaced in its four groups"),
    ]:
        v = uk_driver_number(rng, surname, female)
        if spaced:
            v = f"{v[:5]} {v[5:11]} {v[11:13]} {v[13:]}"
        add("adversarial", "Driving licence {dl} was checked online.",
            {"dl": ("UK_DRIVING_LICENCE", v, True, note)})

    for template, series, note in [
        ("NRIC {ic} was verified at the counter.", "S", "S series after 'NRIC'"),
        ("FIN: {ic} on the work pass.", "G", "G series after 'FIN:'"),
        ("NRIC/FIN no. {ic} for the booking.", "T", "T series after 'NRIC/FIN no.'"),
    ]:
        add("adversarial", template, {"ic": ("SG_NRIC", nric_like(rng, series), True, note)})

    v = nhs_valid(rng)
    add("negative", "Reference {r} was logged.",
        {"r": ("NOT_PII", v, False,
               "checksum-valid ten digits with no NHS context: not reported")})
    add("negative", "NHS number {n} was mistyped.",
        {"n": ("NOT_PII", nhs_invalid(rng), False, "after 'NHS number' but failing modulus 11")})
    add("negative", "The NHS {n} entry is a placeholder.",
        {"n": ("NOT_PII", nhs_check_ten(rng), False,
               "modulus 11 gives 10: the Data Dictionary says no such number is issued")})
    add("negative", "The manual's example {n} is not issued.",
        {"n": ("NOT_PII", "QQ123456C", False, "prefix QQ: Q is never a NINO prefix letter")})
    add("negative", "Code {n} refers to the country.",
        {"n": ("NOT_PII", f"GB{rng.randint(100000, 999999)}A", False, "prefix GB is not allocated")})
    add("negative", "Item {n} is in stock.",
        {"n": ("NOT_PII", f"Z{nino_parts(rng)[0]}{rng.randint(100000, 999999)}C", False,
               "a NINO-shaped run inside a longer token")})
    add("negative", "Order dated {d} was shipped.",
        {"d": ("NOT_PII", f"{rng.randint(10, 28)}-0{rng.randint(1, 9)}-2{rng.randint(0, 9)}", False,
               "nn-nn-nn with no sort-code context: a date")})
    add("negative", "The form had sort code {n} as a placeholder.",
        {"n": ("NOT_PII", "00-00-00", False, "the all-zero sort code placeholder")})
    add("negative", "Batch {n} passed inspection.",
        {"n": ("NOT_PII", f"ABCDE{rng.randint(1, 9)}{rng.randint(13, 49)}{rng.randint(10, 28)}{rng.randint(0, 9)}XY9AB",
               False, "driver-number shape with month 13-49, which DVLA never issues")})
    add("negative", "Order {n} shipped from the depot.",
        {"n": ("NOT_PII", nric_like(rng, "S"), False, "an NRIC-shaped run with no NRIC or FIN context")})

    return out


def verify(corpus: list[dict]) -> int:
    """Every span must slice exactly the value it claims. Returns failure count."""
    failures = 0
    for case in corpus:
        text = case["text"]
        for e in case["entities"]:
            sliced = text[e["start"]:e["end"]]
            if sliced != e["value"]:
                print(f"FAIL {case['id']}: span [{e['start']}:{e['end']}] slices "
                      f"{sliced!r}, expected {e['value']!r}", file=sys.stderr)
                failures += 1
            if not (0 <= e["start"] < e["end"] <= len(text)):
                print(f"FAIL {case['id']}: span out of bounds", file=sys.stderr)
                failures += 1
        for a, b in zip(case["entities"], case["entities"][1:]):
            if a["end"] > b["start"]:
                print(f"FAIL {case['id']}: overlapping spans", file=sys.stderr)
                failures += 1
    return failures


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    ap.add_argument("--seed", type=int, default=20260919,
                    help="fixed so the corpus is reproducible")
    ap.add_argument("--verify", action="store_true", help="verify spans and exit")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    corpus = cases(rng)

    failures = verify(corpus)
    if failures:
        print(f"\n{failures} span error(s) — corpus not written", file=sys.stderr)
        return 1

    counts: dict[str, int] = {}
    undetectable = 0
    for c in corpus:
        counts[c["kind"]] = counts.get(c["kind"], 0) + 1
        undetectable += sum(1 for e in c["entities"] if not e["expected_detected"]
                            and e["type"] != "NOT_PII")

    print(f"{len(corpus)} cases, spans verified: " +
          ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    print(f"{undetectable} entities of types loke has no detector for")

    if args.verify:
        return 0

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for c in corpus:
            fh.write(json.dumps(c, sort_keys=True) + "\n")
    print(f"written: {args.out.relative_to(pathlib.Path.cwd()) if args.out.is_relative_to(pathlib.Path.cwd()) else args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
