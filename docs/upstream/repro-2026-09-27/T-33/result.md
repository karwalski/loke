# T-33 result

Defect: numeric/bool std.json accessors report `$jsonerr` for 0 / 0.0 / false

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | i64(0)=err u64(0)=err f64(0.0)=err bool(false)=err str(empty)=ok: i64(5)=ok:5 bool(true)=ok:1 i64(missing)=err |
| HEAD 4a50b87 | FIXED | i64(0)=ok:0 u64(0)=ok:0 f64(0.0)=ok:0 bool(false)=ok:0 str(empty)=ok: i64(5)=ok:5 bool(true)=ok:1 i64(missing)=err |

Notes: Side observation (R8 probe, both compilers): `row.i64(w;"n")` on a COUNT of 0 took the `$err` arm too (std.db analogue).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
