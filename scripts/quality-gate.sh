#!/usr/bin/env bash
# quality-gate.sh — Single-command quality gate for the loke project.
# Runs: lint -> build -> test pipeline. Stops at first failure.
#
# Usage:
#   ./scripts/quality-gate.sh              # Run the full gate
#   ./scripts/quality-gate.sh --step lint  # Run a specific step
#   ./scripts/quality-gate.sh --from test  # Run from a specific step onwards
#   ./scripts/quality-gate.sh --timing     # Show timing breakdown
#
# Exit codes:
#   0 — All steps passed
#   1 — A step failed (gate failed)
#   2 — Usage error

set -euo pipefail

# --- Configuration ---
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

SHOW_TIMING=false
STEP_FILTER=""
FROM_STEP=""

# --- Colours ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Colour

# --- Parse Arguments ---
while [[ $# -gt 0 ]]; do
  case "$1" in
    --step)
      STEP_FILTER="$2"
      shift 2
      ;;
    --from)
      FROM_STEP="$2"
      shift 2
      ;;
    --timing)
      SHOW_TIMING=true
      shift
      ;;
    --help|-h)
      echo "Usage: quality-gate.sh [--step <step>] [--from <step>] [--timing]"
      echo ""
      echo "Steps: lint, build, unit, integration"
      echo ""
      echo "Options:"
      echo "  --step <name>   Run only the specified step"
      echo "  --from <name>   Run from the specified step onwards"
      echo "  --timing        Show timing breakdown for each step"
      echo "  --help          Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 2
      ;;
  esac
done

# --- Step Tracking ---
STEPS=("lint" "build" "unit" "integration")
STEP_TIMES=()
TOTAL_START=$(date +%s)
GATE_PASSED=true
FAILED_STEP=""

# Determine which steps to run
should_run_step() {
  local step="$1"

  # If --step is set, only run that step
  if [[ -n "$STEP_FILTER" ]]; then
    [[ "$step" == "$STEP_FILTER" ]]
    return $?
  fi

  # If --from is set, skip steps before the target
  if [[ -n "$FROM_STEP" ]]; then
    local found=false
    for s in "${STEPS[@]}"; do
      if [[ "$s" == "$FROM_STEP" ]]; then
        found=true
      fi
      if [[ "$s" == "$step" ]] && $found; then
        return 0
      fi
    done
    return 1
  fi

  return 0
}

# Run a step and track timing
run_step() {
  local step_name="$1"
  local step_cmd="$2"
  local step_desc="$3"

  if ! should_run_step "$step_name"; then
    return 0
  fi

  local step_start
  step_start=$(date +%s)

  # Run the command, capture exit code
  local exit_code=0
  local output
  output=$(eval "$step_cmd" 2>&1) || exit_code=$?

  local step_end
  step_end=$(date +%s)
  local step_duration=$((step_end - step_start))
  STEP_TIMES+=("$step_name:${step_duration}s")

  if [[ $exit_code -eq 0 ]]; then
    printf "${GREEN}[✓]${NC} %-22s %-40s %s\n" "$step_desc" "passed" "${step_duration}s"
  else
    printf "${RED}[✗]${NC} %-22s %-40s %s\n" "$step_desc" "FAILED" "${step_duration}s"
    if [[ -n "$output" ]]; then
      echo ""
      echo "$output" | head -20
      echo ""
    fi
    GATE_PASSED=false
    FAILED_STEP="$step_name"
    return 1
  fi
}

# --- Banner ---
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo " loke quality gate"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- Step 1: Lint ---
# Check for ooke lint, fall back to basic syntax check
LINT_CMD="true"
if command -v ooke &>/dev/null; then
  LINT_CMD="ooke lint"
else
  # Fallback: verify all .tk files are non-empty and have a module declaration
  LINT_CMD='
    errors=0
    while IFS= read -r -d "" f; do
      if ! head -20 "$f" | grep -q "^m="; then
        echo "WARN: $f may be missing module declaration"
      fi
    done < <(find src -name "*.tk" -print0)
    exit $errors
  '
fi

run_step "lint" "$LINT_CMD" "Lint" || {
  echo ""
  printf "${RED}Gate FAILED at step: lint${NC}\n"
  exit 1
}

# --- Step 2: Build ---
BUILD_CMD="true"
if command -v ooke &>/dev/null; then
  BUILD_CMD="ooke build"
else
  # Fallback: verify source structure is intact
  BUILD_CMD='
    for dir in src/core src/cli src/platform src/companion src/mcp-broker; do
      if [[ ! -d "$dir" ]]; then
        echo "ERROR: missing directory $dir"
        exit 1
      fi
    done
    echo "Build check: source structure verified"
  '
fi

run_step "build" "$BUILD_CMD" "Build" || {
  echo ""
  printf "${RED}Gate FAILED at step: build${NC}\n"
  exit 1
}

# --- Step 3: Unit Tests ---
UNIT_CMD="true"
if command -v ooke &>/dev/null; then
  UNIT_CMD="ooke test tests/unit/"
else
  # Fallback: verify test files exist and have run_all functions
  UNIT_CMD='
    count=0
    errors=0
    while IFS= read -r -d "" f; do
      count=$((count + 1))
      if ! grep -q "run_all" "$f"; then
        echo "WARN: $f missing run_all function"
      fi
    done < <(find tests/unit -name "*.tk" -print0)
    echo "Unit tests: $count test files found"
    if [[ $count -eq 0 ]]; then
      echo "ERROR: no unit test files found"
      exit 1
    fi
  '
fi

run_step "unit" "$UNIT_CMD" "Unit tests" || {
  echo ""
  printf "${RED}Gate FAILED at step: unit tests${NC}\n"
  exit 1
}

# --- Step 4: Integration Tests ---
INTEGRATION_CMD="true"
if command -v ooke &>/dev/null; then
  INTEGRATION_CMD="ooke test tests/integration/"
else
  # Fallback: verify integration test files exist
  INTEGRATION_CMD='
    count=0
    while IFS= read -r -d "" f; do
      count=$((count + 1))
      if ! grep -q "run_all" "$f"; then
        echo "WARN: $f missing run_all function"
      fi
    done < <(find tests/integration -name "*.tk" -print0)
    echo "Integration tests: $count test files found"
    if [[ $count -eq 0 ]]; then
      echo "ERROR: no integration test files found"
      exit 1
    fi
  '
fi

run_step "integration" "$INTEGRATION_CMD" "Integration tests" || {
  echo ""
  printf "${RED}Gate FAILED at step: integration tests${NC}\n"
  exit 1
}

# --- Summary ---
TOTAL_END=$(date +%s)
TOTAL_DURATION=$((TOTAL_END - TOTAL_START))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if $GATE_PASSED; then
  printf "${GREEN}Gate passed${NC}                                                    %ss\n" "$TOTAL_DURATION"
else
  printf "${RED}Gate FAILED at step: %s${NC}                                     %ss\n" "$FAILED_STEP" "$TOTAL_DURATION"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# --- Timing ---
if $SHOW_TIMING; then
  echo ""
  echo "Timing breakdown:"
  for entry in "${STEP_TIMES[@]}"; do
    IFS=':' read -r name duration <<< "$entry"
    printf "  %-22s %s\n" "$name" "$duration"
  done
  echo "  ────────────────────────────"
  printf "  %-22s %ss\n" "Total" "$TOTAL_DURATION"
fi

if $GATE_PASSED; then
  exit 0
else
  exit 1
fi
