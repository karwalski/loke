# T-47a result

Defect: json.str unescape drops the backslash (\n \t \r \u0041 read back as letters)

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | bytes=97 110 98 116 99 114 100 34 101 92 102 117 48 48 52 49  |
| HEAD 4a50b87 | REPRODUCES | bytes=97 110 98 116 99 114 100 34 101 92 102 117 48 48 52 49  |

Notes: Same defect as T-44.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
