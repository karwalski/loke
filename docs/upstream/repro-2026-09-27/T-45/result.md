# T-45 result

Defect: json.enc escapes only quote and backslash; raw control bytes in output

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | enc_bytes=34 97 10 98 9 99 13 100 92 34 101 34  |
| HEAD 4a50b87 | REPRODUCES | enc_bytes=34 97 10 98 9 99 13 100 92 34 101 34  |

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
