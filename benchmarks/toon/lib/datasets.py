"""Benchmark payloads, with licence and integrity checks (story VM1.7).

Two rules, both from §6.1 of the methodology and both enforced here rather than
documented and hoped for.

**A payload is either licensed for redistribution or it is generated.** A snapshot
committed to this repository is redistribution. `scripts/fetch_opendata.py` already
aborts on a licence mismatch for the demo datasets; the same rule applies to
benchmark inputs, so every entry declares its licence and the loader refuses one it
cannot account for.

**Every payload is checksummed.** A token count is a measurement of a specific
sequence of bytes. If the bytes change and the checksum does not travel with the
figure, the figure describes something that no longer exists. `checksums.sha256` is
written on first generation and verified on every run.

Why these payloads are synthetic
--------------------------------
The data shapes in §1.2 — uniform tabular, nested, mixed, wide, sparse — are
properties of *structure*, and structure is what a serialisation format responds
to. Real content adds licence obligations and nothing to the measurement, so the
shapes are generated deterministically from a fixed seed. The one real dataset
available here (BITRE road fatalities, CC BY) is included as a cross-check that the
synthetic shapes are not flattering: if the ratios on real data differ materially
from the uniform-tabular shape, the synthetic shapes are misleading and that is a
finding.
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import random

HERE = pathlib.Path(__file__).resolve().parent.parent
DATA_DIR = HERE / "datasets"
CHECKSUMS = DATA_DIR / "checksums.sha256"

SEED = 20260920

# Real snapshot already in the repository, fetched with a verified licence.
BITRE_CSV = (HERE.parent.parent / "packages" / "moke" / "static" / "data"
             / "snapshots" / "bitre.road_fatalities.csv")


class LicenceError(RuntimeError):
    pass


class PayloadSpec:
    def __init__(self, name: str, shape: str, licence: str, source: str,
                 builder, rows: int, note: str = ""):
        self.name = name
        self.shape = shape
        self.licence = licence
        self.source = source
        self.builder = builder
        self.rows = rows
        self.note = note


def _rng() -> random.Random:
    return random.Random(SEED)


def _uniform_tabular(n: int) -> list[dict]:
    r = _rng()
    states = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "NT", "ACT"]
    return [{
        "id": i + 1,
        "state": r.choice(states),
        "count": r.randint(0, 500),
        "rate": round(r.uniform(0, 100), 2),
        "active": r.random() > 0.5,
    } for i in range(n)]


def _nested(n: int) -> list[dict]:
    r = _rng()
    return [{
        "id": i + 1,
        "meta": {"created": f"2026-0{r.randint(1, 9)}-1{r.randint(0, 9)}",
                 "tags": [f"t{r.randint(1, 20)}" for _ in range(r.randint(1, 4))]},
        "metrics": {"cpu": round(r.uniform(0, 100), 1),
                    "ram": round(r.uniform(0, 100), 1),
                    "history": [round(r.uniform(0, 100), 1) for _ in range(5)]},
    } for i in range(n)]


def _mixed(n: int) -> list[dict]:
    r = _rng()
    return [{
        "id": i + 1,
        "label": "row " + str(i + 1),
        "note": " ".join(r.choice(["alpha", "beta", "gamma", "delta", "epsilon"])
                         for _ in range(r.randint(4, 12))),
        "value": round(r.uniform(-1000, 1000), 3),
        "flags": {"ok": r.random() > 0.3, "checked": r.random() > 0.6},
    } for i in range(n)]


def _wide(n: int) -> list[dict]:
    r = _rng()
    cols = [f"col_{j:02d}" for j in range(40)]
    return [{**{"id": i + 1}, **{c: round(r.uniform(0, 1), 4) for c in cols}}
            for i in range(n)]


def _sparse(n: int) -> list[dict]:
    """Many nulls — the shape where formats diverge most, so it is not omitted."""
    r = _rng()
    out = []
    for i in range(n):
        row = {"id": i + 1}
        for j in range(12):
            row[f"f{j:02d}"] = None if r.random() < 0.7 else r.randint(0, 99)
        out.append(row)
    return out


def _bitre_real(n: int) -> list[dict]:
    """The one real dataset available, as a cross-check on the synthetic shapes."""
    if not BITRE_CSV.exists():
        raise FileNotFoundError(
            f"{BITRE_CSV} is missing. Run scripts/fetch_opendata.py to retrieve the "
            "snapshot; it verifies the CC BY licence before writing.")
    with BITRE_CSV.open(newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    return rows[:n]


SPECS = [
    PayloadSpec("uniform_tabular_100", "uniform_tabular", "generated",
                "benchmarks/toon/lib/datasets.py", _uniform_tabular, 100),
    PayloadSpec("uniform_tabular_1000", "uniform_tabular", "generated",
                "benchmarks/toon/lib/datasets.py", _uniform_tabular, 1000),
    PayloadSpec("nested_100", "nested", "generated",
                "benchmarks/toon/lib/datasets.py", _nested, 100),
    PayloadSpec("mixed_100", "mixed", "generated",
                "benchmarks/toon/lib/datasets.py", _mixed, 100),
    PayloadSpec("wide_100", "wide", "generated",
                "benchmarks/toon/lib/datasets.py", _wide, 100),
    PayloadSpec("sparse_100", "sparse", "generated",
                "benchmarks/toon/lib/datasets.py", _sparse, 100),
    PayloadSpec("bitre_road_fatalities_500", "real_tabular", "cc-by",
                "https://data.gov.au — BITRE Australian Road Deaths Database",
                _bitre_real, 500,
                note="Real data, CC BY, attributed. Included so the synthetic shapes "
                     "can be checked against something nobody designed for this "
                     "benchmark."),
]

ALLOWED_LICENCES = {"generated", "cc-by", "cc-by-4.0", "cc0", "public-domain"}


def check_licence(spec: PayloadSpec) -> None:
    if spec.licence not in ALLOWED_LICENCES:
        raise LicenceError(
            f"payload {spec.name!r} declares licence {spec.licence!r}, which is not "
            f"in the allowed set {sorted(ALLOWED_LICENCES)}. A benchmark input "
            "committed to this repository is redistributed, so its licence has to "
            "permit that.")


def build(spec: PayloadSpec):
    check_licence(spec)
    return spec.builder(spec.rows)


def digest(payload) -> str:
    """Checksum the canonical JSON, not a serialised format.

    The point of the checksum is that the *data* is the same, independent of which
    format is being measured.
    """
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def write_checksums(digests: dict[str, str]) -> pathlib.Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"{d}  {name}" for name, d in sorted(digests.items())]
    CHECKSUMS.write_text("\n".join(lines) + "\n")
    return CHECKSUMS


def verify_checksums(digests: dict[str, str]) -> list[str]:
    """Returns a list of problems; empty means every payload is byte-identical."""
    if not CHECKSUMS.exists():
        return []  # first run; write_checksums will record them
    recorded = {}
    for line in CHECKSUMS.read_text().splitlines():
        if not line.strip():
            continue
        d, _, name = line.partition("  ")
        recorded[name.strip()] = d.strip()
    problems = []
    for name, d in digests.items():
        if name not in recorded:
            problems.append(f"{name}: no recorded checksum")
        elif recorded[name] != d:
            problems.append(
                f"{name}: payload changed (recorded {recorded[name][:12]}, "
                f"now {d[:12]}). Any figure measured against the old bytes no longer "
                "describes this payload.")
    return problems
