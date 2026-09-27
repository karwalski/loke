# T-2 - 3+-arm `mt` on a subject of unknown sum type emits duplicate labels

Files: repro.tk, field.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-2`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | i64 subject: compile rc=2: error[E9005]: match has 3 arms, but the sum type of the matched value is not established // field subject: compile rc=2: error[E9005]: match has 3 arms, but the sum type of the matched value is not established (expected exit 33) |
| HEAD 4a50b87 | FIXED | i64 subject: compile rc=2: error[E9005]: match has 3 arms, but the sum type of the matched value is not established // field subject: exit=33 (expected exit 33) |

No invalid IR on either. i64 subject: both give E9005 (a front-end diagnostic, the ask). Struct-field / untyped-local subject (field.tk): PIN refuses with E9005 (field is declared `$s`, so this is a false refusal, not the defect); HEAD compiles and returns the right answer (33).
