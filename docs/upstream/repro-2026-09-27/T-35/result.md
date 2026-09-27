# T-35 result

Defect: emitted IR silently truncated (670 x 38-char constants; one 300,000-char constant), toke exits 0

Reproducer(s): repro.tk, repro_669.tk, repro_big.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES |  repro:toke=0,clang=1 repro_669:toke=0,clang=0 repro_big:toke=0,clang=1 (669 is the control) |
| HEAD 4a50b87 | REPRODUCES |  repro:toke=0,clang=1 repro_669:toke=0,clang=0 repro_big:toke=0,clang=1 (669 is the control) |

Notes: `--emit-llvm` sizes identical on both: 204,289 bytes (670) vs 203,997 (669 control); 66,258 bytes for the 300k string. clang: `constant expression type mismatch: got type '[56 x i8]' but expected '[38 x i8]'` / `'[65506 x i8]' but expected '[300001 x i8]'`.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
