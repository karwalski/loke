# T-47b result

Defect: `str.nowunix()` returns a string handle, declared i64

Reproducer(s): repro.tk, repro_str.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | interpolation=address [nowunix=4315225104 time.now/1000=1790509268] / arithmetic=on-handle [nowunix a=35748055584 b=35748055616 b-a=32 day=413750 time.now/1000=1790509265] |
| HEAD 4a50b87 | CHANGED | interpolation=ok [nowunix=1790509455 time.now/1000=1790509455] / arithmetic=on-handle [nowunix a=1790509452 b=1790509452 b-a=32 day=50228 time.now/1000=1790509452] |

Notes: HEAD declares `str.nowunix (  ) -> str`; interpolation now prints the seconds, but `a/86400` and `b-a` on the str still compile silently and compute on the heap handle (b-a=32 while a and b print the same second).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
