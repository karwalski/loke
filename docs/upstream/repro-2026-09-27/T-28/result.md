# T-28 - `str.isdigit(str.charat(..))` segfaults

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-28`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=139 (signal 11) |
| HEAD 4a50b87 | REPRODUCES | exit=139 (signal 11) |

compiles, SIGSEGV (exit 139) on both.
