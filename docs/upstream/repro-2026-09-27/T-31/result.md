# T-31 result

Defect: `mt` binds a stdlib result's arms by position, not label

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | valid,okfirst=ok valid,errfirst=err invalid,okfirst=err invalid,errfirst=ok |
| HEAD 4a50b87 | REPRODUCES | valid,okfirst=ok valid,errfirst=err invalid,okfirst=err invalid,errfirst=ok |

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
