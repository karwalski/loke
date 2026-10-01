#!/usr/bin/env bash
# Copyright 2026 loke contributors
# SPDX-License-Identifier: Apache-2.0
#
# check_moke_estimates.sh — moke must not invent token counts or savings (GA1.5c).
#
# moke's savings ledger counted tokens as a text's length divided by four and priced them at
# a hard-coded $0.015 per 1K tokens, "the most expensive model", and showed the result as
# tokens and dollars saved. None of it was measured. What loke measures is reported in each
# /api/pipeline reply's `optimisation` object, and static/js/moke-savings.js records only that.
# This check fails if either invention comes back anywhere in moke's templates, scripts,
# pages or sources:
#
#   * a length divided by four: `.length / 4`, `str.len(...) / 4`, or `len / 4`;
#   * the 0.015 rate, or the `expensiveRate` name, in the templates, pages or browser scripts;
#   * a price written as a literal approximation ("~$0." and a number), as the privacy review's
#     fixed "~$0.003" for any cloud request was.
#     (src/cost_comparison.tk keeps a per-model list-price table, which is not a saving, and
#     is exempt from the price patterns only.)
#
#   scripts/check_moke_estimates.sh [moke-root]    # default packages/moke; exit 1 on a hit

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
MOKE="${1:-$ROOT/packages/moke}"
[ -d "$MOKE" ] || { echo "check_moke_estimates: $MOKE is not a directory" >&2; exit 2; }

hits=0
report() { printf '%s\n' "$1"; hits=1; }

# Vendored, minified libraries are not moke's code.
files() {
  find "$MOKE/templates" "$MOKE/static" "$MOKE/pages" "$MOKE/src" -type f \
    \( -name '*.tkt' -o -name '*.js' -o -name '*.tk' -o -name '*.html' \) \
    ! -name '*.min.js' ! -path '*/static/js/tests/*' 2>/dev/null
}

LEN4='(\.length|str\.len\([^)]*\)|\blen)[[:space:]]*/[[:space:]]*4([^0-9.]|$)'
while IFS= read -r f; do
  out=$(grep -nE "$LEN4" "$f") && report "$(printf '%s\n' "$out" | sed "s|^|${f#$ROOT/}:|")"
done < <(files)

while IFS= read -r f; do
  case "$f" in */src/*) continue ;; esac
  out=$(grep -nE '0\.015([^0-9]|$)|expensiveRate|~\$0\.[0-9]' "$f") && report "$(printf '%s\n' "$out" | sed "s|^|${f#$ROOT/}:|")"
done < <(files)

if [ "$hits" -ne 0 ]; then
  echo "check_moke_estimates: moke computes a token count from text length, or prices tokens" >&2
  echo "at the invented rate, above. Record what loke measured (the reply's optimisation" >&2
  echo "object, via static/js/moke-savings.js) or show 'not measured' (GA1.5c)." >&2
  exit 1
fi
echo "check_moke_estimates: OK, no length/4 token count and no invented rate in moke"
