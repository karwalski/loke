# T-1 - `$ok(<bool>)` in a `bool!$err` fn emits invalid IR

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-1`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | exit=10 |
| HEAD 4a50b87 | FIXED | exit=10 |

Filed program as written (bare trailing `mt` in main) is now refused by E4071 on both; repro adds `<`.
