# T-14 - `==` on sums compares handles

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-14`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=1 (expected 11; 1 = returned sum != identical local) |
| HEAD 4a50b87 | REPRODUCES | exit=1 (expected 11; 1 = returned sum != identical local) |

exit 1: local==local true, returned==local false.
