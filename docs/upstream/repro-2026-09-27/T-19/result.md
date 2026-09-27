# T-19 - E4071 misses trailing bare `mt` returning sum/struct

Files: repro.tk, struct.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-19`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | sum: compile rc=1: error[E4071]: function body ends in a value expression with no '<': the value is computed and discarded, and the function returns 0 // struct: compile rc=1: error[E4071]: function body ends in a value expression with no '<': the value is computed and discarded, and the function returns 0 |
| HEAD 4a50b87 | FIXED | sum: compile rc=1: error[E4071]: function body ends in a value expression of type 'd' with no '<': the value is computed and discarded, and the function returns 0 // struct: compile rc=1: error[E4071]: function body ends in a value expression of type 'p' with no '<': the value is computed and discarded, and the function returns 0 |

E4071 for both sum and struct returns.
