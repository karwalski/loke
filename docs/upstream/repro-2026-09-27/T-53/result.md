# T-53 result

Defect: struct capped at 16 fields; --max-params does not raise it; error names neither

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | default: error[E4025]: struct 'big' has no field 'f17' / --max-params=24: error[E4025]: struct 'big' has no field 'f17' |
| HEAD 4a50b87 | FIXED | default: 16 17 20 / --max-params=24: 16 17 20 |

Notes: R3 probe (w2probes/fieldsN.tk): HEAD compiles and runs structs of 40, 64, 65, 70 fields correctly; PIN fails at f17 (and at f65 for 65/70 fields).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
