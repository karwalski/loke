# Ratchet baselines

These files are the floors that `scripts/build_census.py` and `scripts/check_lint_rules.py`
compare against. A count may fall; it may not rise.

**They live here, and not under `build/`, because `build/` is gitignored** (`.gitignore:7`). Until
2026-09-24 the census baselines were written to `build/trees/<tree>/census-baseline.json`, so they
were never committed — which meant that on a fresh clone, and therefore in CI, there was no
baseline at all and the ratchet had nothing to compare against. It could not fail. That is the
fifth check in this repository found inert for a reason of that kind, and it was found while
adding the lint ratchet, which would have inherited the same defect.

| file | floor | recorded by |
|---|---|---|
| `census-<tree>.json` | compile errors and undefined symbols per build tree | `build_census.py --tree <name> --baseline` |
| `lint.json` | `toke --lint` STYLE diagnostics over the built trees | `check_lint_rules.py --baseline` |

`lint.json` deliberately counts only the style rules. The defect-class rules (today
`result discarded`) fail the gate outright rather than ratcheting — a defect is not something to
hold at its current level.

**Re-record a baseline only downwards.** If a number has risen, the change that raised it is the
thing to look at; moving the floor up to make a run green is the one use of these files that
defeats their purpose.
