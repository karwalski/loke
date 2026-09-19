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
    printf '%s\n' "$hits" | head -5
    echo "  hardcoded home directories found above — a fresh clone must build" >&2
    echo "  (known exceptions are listed in scripts/known-defects.txt)" >&2
    failed=1
  fi

  echo "  no C-style comments in tracked toke source"
  if git ls-files -z '*.tk' 2>/dev/null | xargs -0 grep -ln '^//' 2>/dev/null | head -5 | grep .; then
    echo "  toke source must stay comment-free; documentation belongs in .tkc.md" >&2
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
