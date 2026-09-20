#!/usr/bin/env bash
# quality-gate.sh — run the real checks, in order, and stop at the first failure.
#
# This script previously reported "Gate passed" with all four steps green, in
# about one second, on a tree where 294 of 532 files did not type-check and the
# build refused to link. Every step tested `command -v ooke` and fell through to
# a no-op branch, because the binary is named ooke-toke, not ooke. The build
# fallback additionally checked for directories in the legacy src/ tree, so it
# would have kept passing if every real module were deleted.
#
# A gate that cannot fail is worse than no gate, because it gets cited. This one
# calls the actual scripts and has no fallbacks: if a tool is missing, that is a
# failure, not a reason to skip the step.
#
# Usage:
#   ./scripts/quality-gate.sh              # run every step
#   ./scripts/quality-gate.sh --step build # run one step
#   ./scripts/quality-gate.sh --from test  # run from a step onwards
#   ./scripts/quality-gate.sh --list       # show the steps
#
# Exit codes:
#   0  every step run passed
#   1  a step failed
#   2  usage error

set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[0;33m'; DIM=$'\033[2m'; NC=$'\033[0m'

STEPS=(toolchain checks build test)
STEP_FILTER=""
FROM_STEP=""

usage() { sed -n '2,25p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --step) STEP_FILTER="${2:-}"; shift 2 ;;
    --from) FROM_STEP="${2:-}"; shift 2 ;;
    --list) printf '%s\n' "${STEPS[@]}"; exit 0 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

for named in "$STEP_FILTER" "$FROM_STEP"; do
  [[ -z "$named" ]] && continue
  found=0
  for s in "${STEPS[@]}"; do [[ "$s" == "$named" ]] && found=1; done
  if [[ "$found" -eq 0 ]]; then
    echo "unknown step: $named (known: ${STEPS[*]})" >&2
    exit 2
  fi
done

should_run() {
  local step="$1"
  if [[ -n "$STEP_FILTER" ]]; then
    [[ "$step" == "$STEP_FILTER" ]]
    return
  fi
  if [[ -n "$FROM_STEP" ]]; then
    local reached=0
    for s in "${STEPS[@]}"; do
      [[ "$s" == "$FROM_STEP" ]] && reached=1
      [[ "$s" == "$step" ]] && { [[ "$reached" -eq 1 ]]; return; }
    done
  fi
  return 0
}

RAN=0
run_step() {
  local step="$1" label="$2"; shift 2
  should_run "$step" || return 0
  RAN=1
  printf '%s\n' "${DIM}── ${label}${NC}"
  local start=$SECONDS
  if "$@"; then
    printf '%s[ok]%s   %-22s %ss\n\n' "$GREEN" "$NC" "$label" "$((SECONDS - start))"
    return 0
  fi
  printf '%s[FAIL]%s %-22s %ss\n' "$RED" "$NC" "$label" "$((SECONDS - start))"
  printf '%sGate failed at: %s%s\n' "$RED" "$label" "$NC"
  exit 1
}

# --- Steps ---------------------------------------------------------------

step_toolchain() {
  [[ -x ./scripts/check_toolchain.sh ]] || { echo "scripts/check_toolchain.sh missing or not executable" >&2; return 1; }
  ./scripts/check_toolchain.sh
}

# Cheap checks that do not need the compiler. Each must fail loudly.
step_checks() {
  local failed=0

  if [[ -f benchmarks/lib/result.py ]]; then
    echo "  measurement result sink self-test"
    python3 -m benchmarks.lib.result >/dev/null || { echo "  result sink self-test failed" >&2; failed=1; }
  fi

  if [[ -x ./scripts/check_claims.py ]] || [[ -f ./scripts/check_claims.py ]]; then
    echo "  claims register"
    python3 ./scripts/check_claims.py --check || failed=1
  fi

  if [[ -f tests/fixtures/pii-corpus/generate.py ]]; then
    echo "  PII corpus spans verify"
    python3 tests/fixtures/pii-corpus/generate.py --verify >/dev/null \
      || { echo "  corpus span verification failed — every recall figure computed" \
                "from it would be wrong" >&2; failed=1; }
  fi

  if [[ -f packages/moke/static/js/tests/test-moke-provenance.js ]] && command -v node >/dev/null; then
    echo "  card provenance vocabulary"
    node packages/moke/static/js/tests/test-moke-provenance.js >/dev/null \
      || { echo "  provenance tests failed — a card could claim a number it did not compute" >&2; failed=1; }
  fi

  if [[ -f packages/moke/static/js/tests/test-moke-flow.js ]] && command -v node >/dev/null; then
    echo "  demo flow interpreter"
    node packages/moke/static/js/tests/test-moke-flow.js >/dev/null \
      || { echo "  flow tests failed — a walkthrough step could show the wrong instruction" >&2; failed=1; }
  fi

  if [[ -f packages/moke/static/js/tests/test-moke-relationships.js ]] && command -v node >/dev/null; then
    echo "  cross-dataset joins hold against real columns"
    node packages/moke/static/js/tests/test-moke-relationships.js >/dev/null \
      || { echo "  a declared join names a column the data does not have" >&2; failed=1; }
  fi

  # Two checks for the defect class MK20.4 fixed: presentation mode rendered
  # Math.random() figures under a "computed locally" caption, because the NC1.5
  # rule lived in one template and it had no access to it.
  echo "  presentation mode invents no figures"
  if grep -n 'Math\.random' packages/moke/templates/presentation.tkt 2>/dev/null | grep .; then
    echo "  presentation.tkt must not generate figures. It has no legitimate use for" >&2
    echo "  Math.random: no ids, no jitter, no shuffling. Slides come from the DDL." >&2
    failed=1
  fi

  echo "  provenance rule has one definition"
  dupes=$(grep -l 'function cardState\|function setProvenance\|function stripUnverifiedValues' \
          packages/moke/templates/*.tkt 2>/dev/null | head -3)
  if [[ -n "$dupes" ]]; then
    printf '%s\n' "$dupes"
    echo "  the templates above define provenance helpers locally. There must be one" >&2
    echo "  definition, in static/js/moke-provenance.js, or they drift and a page" >&2
    echo "  without the rule renders numbers nobody computed." >&2
    failed=1
  fi

  if [[ -f benchmarks/toon/run.py ]]; then
    # Print the harness's own summary rather than swallowing it: the self-test
    # passes both when the token guards ran and when they were skipped for want of a
    # tokeniser, and those are different facts about this run.
    echo "  serialisation baseline harness"
    if toon_out=$(python3 benchmarks/toon/run.py --self-test 2>&1); then
      echo "    ${toon_out##*$'\n'}"
    else
      printf '%s\n' "$toon_out" >&2
      echo "  the token harness no longer measures correctly, so every ratio it" >&2
      echo "  produced is suspect" >&2
      failed=1
    fi
  fi

  if [[ -f tests/fixtures/adversarial/score.py ]]; then
    echo "  adversarial corpus scorer discriminates"
    python3 tests/fixtures/adversarial/score.py --self-test >/dev/null \
      || { echo "  adversarial scorer self-test failed — the instrument no longer" \
                "discriminates, so any figure it produced would be meaningless" >&2; failed=1; }
  fi

  if [[ -f tests/fixtures/bank-statements/generate.py ]]; then
    echo "  bank statement fixtures reconcile"
    python3 tests/fixtures/bank-statements/generate.py --verify >/dev/null \
      || { echo "  statement fixtures do not reconcile — an import scored against" \
                "them would be scored against a lie" >&2; failed=1; }
  fi

  if [[ -f packages/moke/static/js/tests/test-moke-data.js ]] && command -v node >/dev/null; then
    echo "  dataset data layer"
    node packages/moke/static/js/tests/test-moke-data.js >/dev/null \
      || { echo "  data layer tests failed — includes the assertion that a schema" \
                "profile leaks no cell value" >&2; failed=1; }
  fi

  if [[ -f scripts/fetch_opendata.py ]]; then
    echo "  pre-baked dashboards reference real columns"
    python3 ./scripts/fetch_opendata.py --validate-dashboards >/dev/null 2>&1 \
      || { echo "  a dashboard references a column or operation that does not exist;" \
                "it would render a blank card with no error" >&2; failed=1; }
  fi

  # Only tracked files matter: the question is whether a fresh clone builds,
  # not what happens to be sitting in the working directory.
  # Known defects are listed explicitly in scripts/known-defects.txt, each with
  # the story that removes it, so tolerated debt stays visible and reviewable
  # rather than being silently excluded here.
  echo "  no hardcoded home directories in tracked files"
  local hits
  hits=$(git ls-files -z 'scripts/*' 'packages/*' 'tests/*' '*.toml' '*.sh' 2>/dev/null \
           | xargs -0 grep -In '/Users/[a-z.]*/' 2>/dev/null \
           | grep -vFf <(grep -v '^#' scripts/known-defects.txt | awk 'NF{print $1}') || true)
  if [[ -n "$hits" ]]; then
    printf '%s\n' "$hits" | sed -n '1,5p'
    echo "  hardcoded home directories found above — a fresh clone must build" >&2
    echo "  (known exceptions are listed in scripts/known-defects.txt)" >&2
    failed=1
  fi

  # The two-line Apache licence header is REQUIRED, not a comment to be removed.
  # It is written in toke's own comment syntax, (* ... *). It used to be written as
  # C-style "//", which the compiler flags W1020 on every line because toke has no
  # C-style comment — 1040 warnings across 521 files, now none.
  # 520 of 692 committed .tk files carry it, and a destructive migration script
  # once stripped it from all of them (F10.6), so this check guards both
  # directions: no stray C-style comments, and no missing licence header.
  #
  # Note also that toke gained (* ... *) block comments on 2026-04-27, so
  # comment-freedom in this repository is a project choice for token density, not
  # a language constraint. Documentation still belongs in .tkc.md companions.
  if [[ -f scripts/verify_held_changes.py ]]; then
    echo "  held toke changes are an equality-only sweep"
    python3 scripts/verify_held_changes.py --quiet \
      || { echo "  the uncommitted toke work is not what F10.13 claims it is" >&2; failed=1; }
  fi

  echo "  toke source carries its licence header and no C-style comments"
  stray=$(git ls-files -z '*.tk' 2>/dev/null \
          | xargs -0 grep -ln '^//' 2>/dev/null \
          | while read -r f; do
              grep '^//' "$f" \
                | grep -qv -e 'Copyright 2026 loke contributors' \
                           -e 'SPDX-License-Identifier' && echo "$f"
            done)
  stray=$(printf '%s\n' "$stray" | sed -n '1,5p')
  if [[ -n "$stray" ]]; then
    printf '%s\n' "$stray"
    echo "  C-style comments other than the licence header found above;" >&2
    echo "  documentation belongs in .tkc.md companions" >&2
    failed=1
  fi

  # _archived-tests/ never carried the header, so requiring it there would be a
  # rule invented by this check rather than an invariant of the repository.
  missing=$(git ls-files -z '*.tk' 2>/dev/null \
            | tr '\0' '\n' | grep -v '^_archived-tests/' | tr '\n' '\0' \
            | xargs -0 grep -L 'Copyright 2026 loke contributors' 2>/dev/null \
            | grep -vFf <(grep -v '^#' scripts/known-defects.txt | awk 'NF{print $1}') || true)
  missing=$(printf '%s\n' "$missing" | sed -n '1,5p')
  if [[ -n "$missing" ]]; then
    printf '%s\n' "$missing"
    echo "  toke source above is missing its Apache 2.0 licence header." >&2
    echo "  A migration script deleted it from 520 files once (F10.6); do not" >&2
    echo "  commit that removal. Restore it with: git checkout -- <file>" >&2
    failed=1
  fi

  return "$failed"
}

step_build() {
  [[ -x ./scripts/build_loke.sh ]] || { echo "scripts/build_loke.sh missing or not executable" >&2; return 1; }
  ./scripts/build_loke.sh
}

step_test() {
  [[ -x ./scripts/run_tests.sh ]] || { echo "scripts/run_tests.sh missing or not executable" >&2; return 1; }
  ./scripts/run_tests.sh .
}

# --- Run -----------------------------------------------------------------

printf '\n%sloke quality gate%s\n\n' "$YELLOW" "$NC"

run_step toolchain "Toolchain"      step_toolchain
run_step checks    "Static checks"  step_checks
run_step build     "Build"          step_build
run_step test      "Tests"          step_test

if [[ "$RAN" -eq 0 ]]; then
  echo "no steps matched the given filters" >&2
  exit 2
fi

printf '%sGate passed%s\n\n' "$GREEN" "$NC"
