# T-5 - `void!$err` lowers to LLVM void (`alloca void`)

Files: repro.tk, ok0.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-5`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | FIXED | filed $ok(void): exit=0 // $ok(0): exit=0 |
| HEAD 4a50b87 | FIXED | filed $ok(void): compile rc=1: error[E4033]: 'void' is a built-in type name, not a value // $ok(0): exit=0 |

PIN compiles the filed program (with W1020 warnings) and exits 0. HEAD refuses the filed spelling `$ok(void)` with E4033 (`void` is a type name; commit 49eb193); with `$ok(0)` (ok0.tk) HEAD compiles and exits 0, so the lowering defect is gone on both. Side finding: `<$ok()` gives clang "use of undefined value '@ok'" (E9003) on both.
