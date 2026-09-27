# T-29 - keyword import alias; E2002 does not say reserved

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-29`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | compile rc=1: error[E2002]: expected import alias, got 'sc' |
| HEAD 4a50b87 | REPRODUCES | compile rc=1: error[E2002]: expected import alias, got 'sc' |

E2002 "expected import alias, got 'sc'" plus a cascade of follow-on errors on both.
