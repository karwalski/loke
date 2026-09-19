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
`packages/core/src/privacy/patterns.tk` defines ten patterns. Several Australian
identifiers that loke's own demo data and regulatory presets centre on have **no
detector at all** — Medicare number, BSB, ACN, driver licence, passport. Those
appear in the corpus marked `expected_detected: false` so that a recall figure
computed from it reflects reality rather than only the cases loke already covers.

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


def medicare_valid(rng: random.Random) -> str:
    """Medicare number with a correct check digit. loke has no detector for this."""
    weights = [1, 3, 7, 9, 1, 3, 7, 9]
    while True:
        first = rng.randint(2, 6)
        rest = [rng.randint(0, 9) for _ in range(7)]
        digits = [first] + rest
        check = sum(w * d for w, d in zip(weights, digits)) % 10
        issue = rng.randint(1, 9)
        return f"{''.join(map(str, digits))}{check}{issue}"


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

    # --- Entities loke has no detector for -------------------------------
    # Included so a recall figure reflects a realistic Australian corpus rather
    # than only the types already covered.
    for _ in range(6):
        add("positive",
            "Claim lodged against Medicare number {mc} for the patient named {name}.",
            {"mc": ("AU_MEDICARE", medicare_valid(rng), False,
                    "no detector exists in patterns.tk — flagship demo datasets "
                    "are built around this identifier"),
             "name": ("PERSON", rng.choice(["Ruth Alkinbaya", "Jorge Silveira",
                                            "Mei Lin Choo"]), True, None)})

    for _ in range(4):
        add("positive",
            "Refund to BSB {bsb} account {acct}; entity ACN {acn}.",
            {"bsb": ("AU_BSB", bsb(rng), False, "no detector exists"),
             "acct": ("BANK_ACCOUNT", str(rng.randint(10000000, 99999999)), False,
                      "no detector exists; also indistinguishable from any 8-digit number"),
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
        t = tfn_valid(rng)
        add("adversarial",
            "TFN supplied as {spaced} on the form and {dashed} in the attachment.",
            {"spaced": ("AU_TFN", f"{t[:3]} {t[3:6]} {t[6:]}", True, "space-separated"),
             "dashed": ("AU_TFN", f"{t[:3]}-{t[3:6]}-{t[6:]}"[:-1] + str((int(t[-1]) + 1) % 10), True,
                        "dash-separated, different value to keep the case unambiguous")})

    for _ in range(4):
        add("adversarial",
            'Payload was {json} and the callback hit {url}.',
            {"json": ("EMAIL", f'contact{rng.randint(10,99)}@example-corp.com.au', True,
                      "entity embedded in a JSON-ish fragment"),
             "url": ("URL", f"https://api.example-corp.com.au/v1/u?e=user{rng.randint(10,99)}"
                            f"%40example-corp.com.au", True,
                     "an email is percent-encoded inside this URL; the url pattern "
                     "will match the URL but the embedded address is not separately reported")})

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
