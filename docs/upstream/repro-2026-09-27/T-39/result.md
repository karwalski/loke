# T-39 result

Defect: unused-import lint ignores type-only use; `--lint --fix` deletes the import and breaks the build

Reproducer(s): repro.tk, t39lib.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | lint: unused-import] imported module 'tl' is never used / imports after --fix: 0 / check after fix: error[E3011]: identifier 'thing' is not declared |
| HEAD 4a50b87 | FIXED | lint: none / imports after --fix: 1 / check after fix: ok |

Notes: Only the type-only case was tested; the field-resolution-only case from the filed text was not reproduced standalone.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
