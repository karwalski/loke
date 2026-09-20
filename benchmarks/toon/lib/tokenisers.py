"""Per-provider token counting (story VM1.7).

Why this file is the point of the story
--------------------------------------
`packages/core/src/optimiser/toon.tk:285` computes savings like this:

    let origlen = str.len(originaljson) as f64;
    let toonlen = str.len(toonstr) as f64;

That is a ratio of **character counts**. It is not a token saving, and a token
saving is the only kind that changes what a provider charges or what fits in a
context window. The two can disagree in either direction: a format that shortens
text by splitting words into unusual fragments can cost more tokens while
occupying fewer characters.

So every number this harness produces is counted with a real tokeniser, and is
labelled with which one. A figure without its tokeniser named is not admissible —
`benchmarks/lib/result.py` refuses it, which is why that refusal exists.

Which tokenisers, and the honest gaps
-------------------------------------
§2.3 of the methodology names six. Availability here:

    OpenAI      cl100k_base, o200k_base   tiktoken, offline, exact
    Llama/Qwen/Mistral                    HuggingFace tokenizers, if the weights
                                          are cached locally; skipped otherwise
    Anthropic   Claude tokeniser          NOT available. Counting requires an API
                                          call to .count_tokens(), so it cannot be
                                          done offline and is not approximated
    Google      Gemini tokeniser          same

Anthropic's and Google's counts are **absent rather than estimated**. Substituting
cl100k_base for a Claude count and calling it a Claude count would be a fabricated
measurement of the provider this project sends most of its traffic to.

Cross-tokeniser comparison uses the geometric mean, per §2.3, so no single
tokenisation scheme dominates the headline.
"""

from __future__ import annotations

import math
from typing import Callable

# name -> (loader, provider, note)
_CANDIDATES: list[tuple[str, str, str]] = [
    ("cl100k_base", "openai", "GPT-4 / GPT-3.5 family"),
    ("o200k_base", "openai", "GPT-4o family"),
]

_HF_CANDIDATES: list[tuple[str, str, str]] = [
    # Loaded only if already cached locally: the harness must not reach the network
    # to take a measurement, or the measurement is not reproducible offline.
    ("meta-llama/Llama-3.1-8B", "meta", "Llama 3.1"),
    ("Qwen/Qwen2.5-7B", "alibaba", "Qwen 2.5"),
    ("mistralai/Mistral-7B-v0.3", "mistral", "Mistral"),
]

UNAVAILABLE = {
    "anthropic": (
        "The Claude tokeniser is not public. Counting requires an API call to "
        "client.messages.count_tokens(), so it cannot be done offline. Not "
        "approximated with cl100k_base: that would be a fabricated Claude figure."
    ),
    "google": (
        "The Gemini tokeniser requires the google-generativeai SDK and a call. Not "
        "approximated."
    ),
}


class Tokeniser:
    def __init__(self, name: str, provider: str, note: str, count: Callable[[str], int]):
        self.name = name
        self.provider = provider
        self.note = note
        self._count = count

    def count(self, text: str) -> int:
        return self._count(text)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Tokeniser {self.name} ({self.provider})>"


def available() -> list[Tokeniser]:
    """Every tokeniser that can count offline, right now, on this machine."""
    out: list[Tokeniser] = []

    try:
        import tiktoken
    except ImportError:
        tiktoken = None

    if tiktoken is not None:
        for name, provider, note in _CANDIDATES:
            try:
                enc = tiktoken.get_encoding(name)
            except Exception:
                continue
            out.append(Tokeniser(name, provider, note,
                                 lambda t, _e=enc: len(_e.encode(t))))

    try:
        from transformers import AutoTokenizer
    except ImportError:
        AutoTokenizer = None

    if AutoTokenizer is not None:
        for repo, provider, note in _HF_CANDIDATES:
            try:
                # local_files_only: a benchmark that downloads weights mid-run is
                # not a reproducible offline measurement.
                tok = AutoTokenizer.from_pretrained(repo, local_files_only=True)
            except Exception:
                continue
            out.append(Tokeniser(repo, provider, note,
                                 lambda t, _t=tok: len(_t.encode(t))))

    return out


def geometric_mean(values: list[float]) -> float:
    """Per §2.3, for combining counts across tokenisers.

    Rejects a zero or negative count rather than returning 0.0: a token count of
    zero for non-empty text means the tokeniser is broken, and a silent 0.0 would
    make every ratio built on it look spectacular.
    """
    if not values:
        raise ValueError("geometric mean of nothing")
    for v in values:
        if v <= 0:
            raise ValueError(f"non-positive token count {v}; a tokeniser is broken")
    return math.exp(sum(math.log(v) for v in values) / len(values))


def compression_ratio(baseline_tokens: int, candidate_tokens: int) -> float:
    """tokens(JSON) / tokens(format), per §4.1.1. Above 1.0 means a saving.

    Reported as a ratio, never as a percentage saved, because the two get confused:
    a ratio of 2.0 is a 50% reduction, and "2x" has been read as "200% saved" often
    enough that the units are worth being strict about.
    """
    if candidate_tokens <= 0:
        raise ValueError("candidate token count must be positive")
    return baseline_tokens / candidate_tokens
