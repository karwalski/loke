# T-4 - bare type name as a value gets no diagnostic

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-4`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | compile rc=1: error[E4033]: 'thing' is a type name, not a value |
| HEAD 4a50b87 | FIXED | compile rc=1: error[E4033]: 'thing' is a type name, not a value |

E4033 on both.
