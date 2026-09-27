# T-23 - `str.join` args reversed accepted (same ABI)

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-23`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=139 (signal 11) |
| HEAD 4a50b87 | FIXED | compile rc=1: error[E4031]: type mismatch: expected 'str', got '@(str)' — argument 1 of 'std.str.join' is read by the runtime as a C string, so a handle of another kind is read as text |

PIN: compiles, SIGSEGV (exit 139). HEAD: E4031 on both arguments.
