# T-50 result

Defect: `mt` on `process.wait` (plain i32) sends exit 0 to the $err arm

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | mt: true->err false->ok:1 / plain wait(true) as i64=0 |
| HEAD 4a50b87 | FIXED(rejected) | error[E4031]: type mismatch: expected an error union 'T!E', got 'i32' |

Notes: HEAD rejects the match at compile time: E4031 "expected an error union 'T!E', got 'i32' - a '$ok'/'$err' match tests the value against 0". `process.wait(h) as i64` returns 0 correctly on PIN.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
