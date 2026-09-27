# T-18 - `mt` on X!$userErr always takes the first arm

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-18`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=57 (expected 77; 57 = first arm always) |
| HEAD 4a50b87 | REPRODUCES | exit=57 (expected 77; 57 = first arm always) |

exit 57: ok-first match of an $err value yields 5 ($ok arm), err-first yields 7 - first arm both times.
