"""Serialisation formats for the token-optimisation benchmark (story VM1.7).

Scope, and why it stops where it does
-------------------------------------
`docs/research/toon-benchmark-methodology.md` §3.1 defines seven formats. This
module implements the three the story names as baselines, and no more:

    B1  raw JSON, 2-space indent — the primary baseline, and what most
        applications actually send today
    B2  minified JSON — tests how much of any saving is just whitespace
    B3  YAML — tests whether a less verbose markup gets there on its own

**TOON itself is deliberately absent.** The methodology says the TOON serialiser
is the one "specified in the toon-format/toon repository", and no faithful
implementation is available to this harness: there is no Python or JavaScript TOON
package installed, and loke's own encoder is
`packages/core/src/optimiser/toon.tk`, which needs the compiler. Writing a
plausible TOON encoder from the format's description would produce a number about
a format of my own invention, attributed to TOON. That is worse than having no
number, so the harness measures the three baselines it can measure faithfully and
reports TOON as unimplemented.

What B2 vs B1 is actually for
-----------------------------
It is the control that stops a whitespace saving being reported as a compression
technique. If a format beats B1 by roughly what B2 beats B1 by, it has not done
anything interesting, and the methodology asks for exactly this comparison.
"""

from __future__ import annotations

import json
from typing import Any

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover - reported by validate.py
    _yaml = None


FORMATS = ("b1_json", "b2_json_min", "b3_yaml")

FORMAT_LABELS = {
    "b1_json": "Raw JSON (2-space indent)",
    "b2_json_min": "Minified JSON",
    "b3_yaml": "YAML",
}

# Formats the methodology defines and this harness does not implement, with the
# reason each is absent. Reported alongside every result so the omission is part
# of the record rather than a silence.
UNIMPLEMENTED = {
    "f4_toon": (
        "No faithful TOON encoder is available here. The methodology specifies the "
        "toon-format/toon implementation; no Python or JS package is installed, and "
        "loke's own encoder is toke (packages/core/src/optimiser/toon.tk) and needs "
        "the compiler. An encoder written from the description would measure a "
        "format of this harness's invention under TOON's name."
    ),
    "f5_llmlingua": (
        "Requires the LLMLingua-2 sidecar and its XLM-RoBERTa weights, which this "
        "repository does not bundle (claims.md C2)."
    ),
    "f6_toon_llmlingua": "Composition of two formats neither of which is available.",
    "f7_toke": "Needs the toke compiler; the build is red pending ooke 3.0.0.",
}


def b1_json(data: Any) -> str:
    """Raw JSON, 2-space indent. The primary baseline.

    sort_keys is on so the bytes are deterministic across runs: a benchmark whose
    baseline changes with dict ordering cannot be compared to itself.
    """
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False)


def b2_json_min(data: Any) -> str:
    """Minified JSON: no whitespace at all."""
    return json.dumps(data, separators=(",", ":"), sort_keys=True, ensure_ascii=False)


def b3_yaml(data: Any) -> str:
    """YAML, per §3.1: default flow style for short sequences."""
    if _yaml is None:
        raise RuntimeError("PyYAML is not installed; run validate.py")
    return _yaml.dump(data, default_flow_style=None, sort_keys=True,
                      allow_unicode=True, width=10000)


SERIALISERS = {
    "b1_json": b1_json,
    "b2_json_min": b2_json_min,
    "b3_yaml": b3_yaml,
}


def serialise(fmt: str, data: Any) -> str:
    if fmt not in SERIALISERS:
        raise KeyError(
            f"unknown format {fmt!r}. Implemented: {', '.join(FORMATS)}. "
            f"Unimplemented: {', '.join(UNIMPLEMENTED)}")
    return SERIALISERS[fmt](data)


def roundtrips(fmt: str, data: Any) -> bool:
    """Does this format preserve the data?

    A format that loses information is not a compression of it, and a token saving
    from a lossy format is not a saving. Checked for every payload rather than
    assumed, because YAML in particular has type-coercion edge cases (an unquoted
    `no` becoming False, a version-like string becoming a float) that would quietly
    change what the model is shown.
    """
    text = serialise(fmt, data)
    try:
        if fmt == "b3_yaml":
            if _yaml is None:
                return False
            back = _yaml.safe_load(text)
        else:
            back = json.loads(text)
    except Exception:
        return False
    return back == data
