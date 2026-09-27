# T-37 result

Defect: a declared `@f64` array handle gets the scalar f64 conversion (fptosi/bitcast double), IR invalid

Reproducer(s): repro.tk, repro_field.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | return: error: '%t4' defined with type 'i64' but expected 'double' / field: error: '%t9' defined with type 'i64' but expected 'double' |
| HEAD 4a50b87 | FIXED | return: 2 1.5 / field: 2 2.5 |

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
