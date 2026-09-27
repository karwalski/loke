# T-6 - `let` shadowing an enclosing `let` emits invalid IR

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-6`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | exit=57 [W3013 shadow warning emitted] |
| HEAD 4a50b87 | FIXED | exit=57 [W3013 shadow warning emitted] |

Both exit 57 and emit W3013.
