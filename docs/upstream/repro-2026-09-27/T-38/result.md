# T-38 result

Defect: a later `let` retypes an earlier same-named binder; E4031 attributed to the wrong line with a wrong fix hint

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | error[E4031]: type mismatch: expected 'a', got 'b' |
| HEAD 4a50b87 | FIXED | rc=7 |

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
