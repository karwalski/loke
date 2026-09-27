# T-22 - `row.f64` declared a result but returns a bare i64

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-22`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | CHANGED | exit=0 out: x: ok 25 / zero: err / nosuch: err |
| HEAD 4a50b87 | CHANGED | exit=0 out: x: ok 25 / zero: err / nosuch: err |

No crash on either. 2.5 -> $ok 25 correct, missing column -> $err, but a stored 0.0 -> $err: with no tag the value 0 is the error signal. Entry said it crashed; observed is zero/err conflation.
