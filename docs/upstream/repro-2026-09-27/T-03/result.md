# T-3 - i32 array index widened with `zext i1`

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-3`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | exit=2 |
| HEAD 4a50b87 | FIXED | exit=2 |


