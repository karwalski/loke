# T-43 result

Defect: no API chooses a server's bind address; servers listen on all interfaces

Reproducer(s): repro.tk, repro_listen.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | listen addresses (lsof): repro:*:11441 repro_listen:*:11442 |
| HEAD 4a50b87 | REPRODUCES | listen addresses (lsof): repro:*:11441 repro_listen:*:11442 |

Notes: `tk_web_glue.c` calls `http_serve_workers(NULL, NULL, port, workers)` on both. `http.listen("127.0.0.1:11442";...)` also bound `*:11442`. Servers were run with `--allow-net` (without it: CAP001).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
