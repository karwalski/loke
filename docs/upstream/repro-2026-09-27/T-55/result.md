# T-55 result

Defect: str.charat does strlen per call; byte loop is quadratic

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | n=100000 sum=9700000 ms=264 n=200000 sum=19400000 ms=1015 ratio_x10=38 (2x the bytes: x10 ratio of time; 20=linear, 40=quadratic) |
| HEAD 4a50b87 | REPRODUCES | n=100000 sum=9700000 ms=208 n=200000 sum=19400000 ms=856 ratio_x10=40 (2x the bytes: x10 ratio of time; 20=linear, 40=quadratic) |

Notes: `tk_str_charat_w` still calls `strlen(p)` on HEAD (str_glue.c:206-211). HEAD adds `str.indexfrom ( str, str, i64 ) -> i64`, not a byteat.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
