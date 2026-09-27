# T-13 - bare sum variant in value position crashes when matched

Files: repro.tk, field.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-13`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | mut.$internal: exit=133 (signal 5) // struct field l:$internal: exit=133 (signal 5) |
| HEAD 4a50b87 | CHANGED | mut.$internal: compile rc=1: error[E4033]: '$internal' is a type, not a value // struct field l:$internal: exit=133 (signal 5) |

PIN: `mut.$internal` and struct field `l:$internal` both SIGTRAP (exit 133). HEAD: `mut.$internal` is now E4033, but the struct-literal field form (field.tk) still compiles clean and SIGTRAPs.
