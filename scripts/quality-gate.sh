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

  # The register's own arithmetic. check_claims.py verifies that a verified claim carries an
  # evidence pointer and that every figure traces to metrics-baseline.md; it does not add the
  # verdicts up. On 2026-09-23 the hand-written Summary read verified 33 / total 95 while the
  # rows said 34 / 97, and two of its five numbers had been wrong before that session's edits.
  # In a document whose purpose is to stop the project overstating itself, the table a reader
  # is most likely to quote was the one with nothing checking it. Same conclusion as RV1.7
  # reached for the backlog: derive it.
  if [[ -f ./scripts/gen_claims_summary.py ]]; then
    echo "  the claims register's Summary is derived from its rows"
    python3 ./scripts/gen_claims_summary.py --check || failed=1
  fi

  # GA5.1 — a SQL time function stored as TEXT. Eleven sites in seven modules, by three
  # separate mechanisms: bound as a parameter (`@(..., "now()")`), quoted inside the statement
  # (`VALUES (?,?,'now()')`), and assigned straight to a struct field. A bound parameter is a
  # value and is never evaluated; a quoted string in SQL is a string.
  #
  # packages/moke joined the roots when it compiled (F10.23h fixed its ten sites; MK21.13).
  #
  # Two of these did real damage rather than storing a useless column:
  # governance/monitoring filtered `created_at >= datetime('now','-N days')` against a column
  # of literal `now()`, so every trend window returned nothing for every model, always; and
  # memory/storage stamped every drawer and closet identically, which is why memory decay had
  # nothing to age.
  if [[ -f ./scripts/find_sql_literal_now.py ]]; then
    echo "  no SQL time function is stored as text"
    python3 ./scripts/find_sql_literal_now.py --check \
      packages/core packages/shared packages/browser packages/moke >/dev/null \
      || { python3 ./scripts/find_sql_literal_now.py \
             packages/core packages/shared packages/browser packages/moke >&2
           failed=1; }
  fi

  # `~` is not expanded by toke's path layer. Measured: file.exists("~/.loke/x") is false for a
  # file that exists, and file.appendline to a `~/` path writes nothing at all — neither to
  # $HOME nor to a literal `~` directory.
  #
  # 29 literals in this repo began with `~/`. The two that mattered: shared/log.tk appended
  # every log line to "~/.loke/loke.log", so LOKE HAS NEVER WRITTEN A LOG FILE at any level;
  # and three call sites loaded "~/.loke/config.toml", so a user's configuration was never
  # read — compounded by T-18, which meant the fallback to defaults could not run either.
  #
  # Gated on the built trees plus cli/mcp-broker/mcp-toke. moke has one more and legacy src/
  # has three; both are filed rather than gated, because neither tree is in a state where a
  # gate failure would tell anyone anything new.
  # T-26 — `x.field == v` as a STATEMENT. toke has no assignment to a struct field, and
  # E2002's advice for the parse error is to "use ==", which turns it into a legal expression
  # whose value is discarded. 21 sites in 6 modules, every one silent: the gateway kill switch
  # logged "activated" and left the flag false; the decision trace recorded nothing;
  # agents/registry's enable and disable returned $ok(0) for work they had not done.
  #
  # No existing check covered this. find_field_matches.py sounds like it would and does not —
  # that one is a `mt` over a struct field with 3+ arms (T-2).
  # A table named in SQL that nothing creates. Every read against one fails, and the row
  # accessors map a failed read to 0 or "" (LS1.1i), so the data is silently always empty.
  # Found five on 2026-09-24: memory_graph_entities, memory_graph_relations, memory_settings
  # (M1.7's remaining three), metrics_raw (DA1.2 — so no metric event was ever stored) and
  # compliance_events (so a policy-violation rate was always 0%, the most flattering possible
  # number). scripts/known-tables.txt carries the two deliberate exceptions with their reasons.
  # `toke --lint` has rules for real defects and NOTHING in this repo ran it. Measured
  # 2026-09-24: 3,287 diagnostics over 454 files, including 61 sites of
  # "result discarded — write x=x.push(...)" — the T-24 class this session had been finding by
  # hand, one module at a time, from failing tests. Ten were in the built trees, and every one
  # was a silently empty collection: a model download that reported no progress or outcome, L3
  # deep memory contributing nothing to any context, and a `ps` parse that never read a pid or a
  # CPU figure for any process.
  #
  # Only the defect-class rules fail. The 1,619 style diagnostics (concat nesting, unused
  # imports) are counted and printed — they are LS1.2/LS1.3/LS1.4's work, and failing on them
  # today would mean the gate is switched off. moke and legacy src/ are out of scope for the
  # same reason as the other sweeps: MK21.16 and the F10.12 decision.
  if [[ -f ./scripts/check_lint_rules.py ]]; then
    echo "  no defect-class lint rule fires"
    python3 ./scripts/check_lint_rules.py --check \
      packages/core packages/shared packages/browser >/dev/null \
      || { python3 ./scripts/check_lint_rules.py \
             packages/core packages/shared packages/browser >&2
           failed=1; }
    # The style count also ratchets: it may fall, it must not rise. Floor in baselines/lint.json,
    # which is committed — unlike build/, so it survives a clone and can therefore actually fail.
  fi

  # T-27 — comments NEST, so one stray open-paren-star inside a comment swallows the rest of the
  # file. The module still TYPE-CHECKS; what is lost is every declaration after the comment, and
  # it surfaces somewhere else as "module X has no exported member Y".
  #
  # Documented as T-27 for weeks with nothing detecting it, and on 2026-09-24 it cost two build
  # cycles in ten minutes: a comment in core/storage/db.tk containing a SQL aggregate written with
  # a star broke fourteen call sites across six modules, and then the paragraph written to explain
  # that contained the sequence twice while describing it.
  #
  # The check reports a file that ENDS at comment depth > 0. Balanced nesting is legal and is not
  # flagged — several comments here quote defective code that itself contains a comment.
  if [[ -f ./scripts/find_nested_comment_open.py ]]; then
    echo "  every comment closes"
    python3 ./scripts/find_nested_comment_open.py --check packages src >/dev/null \
      || { python3 ./scripts/find_nested_comment_open.py packages src >&2
           failed=1; }
  fi

  if [[ -f ./scripts/find_uncreated_tables.py ]]; then
    echo "  every table referenced in SQL is created somewhere"
    python3 ./scripts/find_uncreated_tables.py --check \
      packages/core packages/shared packages/browser >/dev/null \
      || { python3 ./scripts/find_uncreated_tables.py \
             packages/core packages/shared packages/browser >&2
           failed=1; }
  fi

  # GA5.18. std.db.exec discards prepare_v2's tail pointer, so a two-statement string applies
  # statement one and reports success for both. Found when a migration created its table and
  # silently skipped its index.
  if [[ -f ./scripts/find_multistatement_exec.py ]]; then
    echo "  every db.exec applies exactly one statement"
    python3 ./scripts/find_multistatement_exec.py --check packages tests >/dev/null \
      || { python3 ./scripts/find_multistatement_exec.py packages tests >&2
           failed=1; }
  fi

  if [[ -f ./scripts/find_discarded_field_compare.py ]]; then
    echo "  no struct-field comparison used as a statement"
    python3 ./scripts/find_discarded_field_compare.py --check \
      packages/core packages/shared packages/browser packages/cli \
      packages/mcp-broker packages/mcp-toke packages/moke >/dev/null \
      || { python3 ./scripts/find_discarded_field_compare.py \
             packages/core packages/shared packages/browser packages/cli \
             packages/mcp-broker packages/mcp-toke packages/moke >&2
           failed=1; }
  fi

  # F10.15a — one prefix for page modules, derived from the path, so the generated
  # _handlers.tk cannot import two spellings of the same kind of module.
  if [[ -f ./scripts/check_page_module_names.py ]]; then
    echo "  every page module is named after its path"
    python3 ./scripts/check_page_module_names.py --check >/dev/null \
      || { python3 ./scripts/check_page_module_names.py >&2; failed=1; }
  fi

  if [[ -f ./scripts/find_tilde_path.py ]]; then
    echo "  no unexpanded \`~/\` path literal"
    python3 ./scripts/find_tilde_path.py --check \
      packages/core packages/shared packages/browser packages/cli \
      packages/mcp-broker packages/mcp-toke packages/moke >/dev/null \
      || { python3 ./scripts/find_tilde_path.py \
             packages/core packages/shared packages/browser packages/cli \
             packages/mcp-broker packages/mcp-toke packages/moke >&2
           failed=1; }
  fi

  if [[ -f ./scripts/find_nowunix_as_int.py ]]; then
    echo "  no str.nowunix() used as a number"
    python3 ./scripts/find_nowunix_as_int.py --check packages tests >/dev/null \
      || { python3 ./scripts/find_nowunix_as_int.py packages tests >&2; failed=1; }
  fi

  if [[ -f ./scripts/find_wait_before_read.py ]]; then
    echo "  no child process is waited for before its output is read"
    python3 ./scripts/find_wait_before_read.py --check packages >/dev/null \
      || { python3 ./scripts/find_wait_before_read.py packages >&2; failed=1; }
  fi

  if [[ -f ./scripts/find_interp_abi_str.py ]]; then
    echo "  no std.str result interpolated as an address"
    python3 ./scripts/find_interp_abi_str.py --check packages tests >/dev/null \
      || { python3 ./scripts/find_interp_abi_str.py packages tests >&2; failed=1; }
  fi

  if [[ -x ./scripts/check_backlog.py ]] || [[ -f ./scripts/check_backlog.py ]]; then
    echo "  backlog schema and generated SUMMARY"
    python3 ./scripts/check_backlog.py --check || failed=1
  fi

  # The hook must be INSTALLED, not merely present in the tree. X4.2 was marked Done
  # claiming a pre-push hook was in place while .git/hooks held only .sample files, and
  # nothing could have revealed that from the repository. So the gate asserts the
  # configuration, not the file.
  echo "  git hooks are installed"
  if [[ "$(git config --get core.hooksPath 2>/dev/null || true)" != "githooks" ]]; then
    echo "    core.hooksPath is not set to githooks — run scripts/install-hooks.sh" >&2
    echo "    A hook that is not installed is documentation. X4.2 shipped as exactly that." >&2
    failed=1
  fi

  # Unexplained deletions in the commits not yet pushed. 09b0a67 cut a 240-line request
  # handler to 79 inside a mechanical sweep, removing response restoration, policy
  # evaluation and audit logging, and never mentioned the file — three stories were
  # recorded as "never implemented" for a day as a result.
  if [[ -f ./scripts/check_sweep_commit.py ]]; then
    echo "  every large deletion is named in its commit message"
    if _sweep_base=$(git rev-parse --abbrev-ref '@{u}' 2>/dev/null); then
      python3 ./scripts/check_sweep_commit.py --range "$_sweep_base..HEAD" || failed=1
    else
      echo "    no upstream branch; nothing to compare against."
    fi
  fi

  # X7.3 — a test that re-declares its subject is a gate failure, PER DIRECTORY.
  #
  # Turning this on repo-wide only after X7.2 finishes would leave it unenforced for
  # exactly the period in which the stub count could grow back. The script carries an
  # ENFORCED list; a directory joins it the moment it reaches zero and never leaves.
  # scripts/known-defects.txt is the shrinking allowlist, story ID required.
  if [[ -f ./scripts/check_test_stubs.py ]]; then
    echo "  enforced test directories exercise production code"
    python3 ./scripts/check_test_stubs.py --check || failed=1
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
  # Four sweeps for toke defects that compile cleanly and fail at LINK time, in
  # LLVM's words, naming no toke file. Each is documented in
  # docs/upstream/toke-issues.md with a minimal reproduction; until they are fixed
  # upstream these keep them from coming back. Three of the four also catch a silent
  # logic bug of their own — a shadowing `let` is how a broken accumulator looks, and
  # a type name used as a value is how a missing parameter looks.
  #
  # find_err_arm_first is the newest and the only one of these that catches an INVERSION
  # rather than a dead path: `mt` binds a result's arms by position, so an `$ok` arm written
  # second runs on failure and the error arm runs on success (T-31). 53 sites, and the pair
  # that shows why it is gated rather than remembered is `privacy/presidio.isavailable`
  # against `optimiser/llmlingua.isavailable` — the identical mistake, fail-closed in one
  # module and fail-OPEN in the other.
  for sweep in find_shadowed_lets find_typename_values find_field_matches \
               find_missing_return_semi find_offbyone_loops find_discarded_tail_expr \
               find_err_arm_first find_discarded_tail_match; do
    if [[ -f "scripts/$sweep.py" ]]; then
      echo "  toke codegen hazard: $sweep"
      python3 "scripts/$sweep.py" --check packages >/dev/null \
        || { python3 "scripts/$sweep.py" packages >&2
             echo "  see docs/upstream/toke-issues.md for why each of these breaks the link" >&2
             failed=1; }
    fi
  done

  # The same class, checked in the emitted IR rather than the source, because the
  # source-side heuristic cannot see every shape toke miscompiles.
  if [[ -f scripts/check_match_labels.py ]] \
     && [[ -d packages/browser/build/ooke ]]; then
    echo "  emitted IR has no duplicate match labels"
    python3 scripts/check_match_labels.py --check >/dev/null \
      || { python3 scripts/check_match_labels.py >&2; failed=1; }
  fi

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
  ./scripts/build_loke.sh || return 1

  # F10.23g — loke-cli enters the gate.
  #
  # The tree has built clean and linked for a while (0 compile errors, 0 undefined symbols, a
  # 2 MB binary), and none of that was checked by anything: the gate built only `loke`, so cli,
  # mcp-broker and mcp-toke could regress to any depth without failing a run. That is the state
  # every other tree was in before it was onboarded, and it is how 247 files came to have never
  # been compiled once.
  #
  # `moke` is deliberately NOT here. It has 0 compile errors and 252 of 252 interfaces but six
  # objects still fail IR assembly (MK21.16: T-35 truncation in four data modules, T-37 in
  # compute and ml/engine), so adding it would fail every gate run on a known, filed condition —
  # which trains people to ignore the gate. It joins when it links.
  if [[ -x ./scripts/build_trees.sh ]]; then
    ./scripts/build_trees.sh loke-cli || return 1
    # MK21.16: moke links as of 2026-09-24. Its demo datasets moved out of source literals
    # (T-35) and its @f64 accumulators were restructured (T-37), so it joins here as the
    # comment above said it would.
    ./scripts/build_trees.sh moke || return 1
  fi
}

step_test() {
  [[ -x ./scripts/run_tests.sh ]] || { echo "scripts/run_tests.sh missing or not executable" >&2; return 1; }
  ./scripts/run_tests.sh . || return 1
  # F10.36: one real HTTP request per route. Handler tests never enter ooke's accept
  # loop, and that is where a server that crashed on every API request was hiding.
  if [[ -x ./scripts/smoke_serve.sh ]]; then
    ./scripts/smoke_serve.sh || return 1
  fi
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
