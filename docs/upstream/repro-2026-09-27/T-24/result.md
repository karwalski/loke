# T-24 - `@(array;element)` nests instead of appending

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-24`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=2 (expected 3 or a type error) |
| HEAD 4a50b87 | REPRODUCES | exit=2 (expected 3 or a type error) |

exit 2 (expected 3), no diagnostic, on both.
