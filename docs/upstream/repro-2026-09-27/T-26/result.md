# T-26 - no field assignment; E2002 advises `==`

Files: repro.tk, applied_advice.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-26`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | x.a=9: compile rc=1: error[E2002]: `=` is assignment; use `==` for equality // advice applied x.a==9: exit=1 |
| HEAD 4a50b87 | REPRODUCES | x.a=9: compile rc=1: error[E2002]: `=` is assignment; use `==` for equality // advice applied x.a==9: exit=1 |

E2002 "`=` is assignment; use `==` for equality"; applying it compiles clean, exits 1 (no-op), no warning; --lint only says mut never mutated.
