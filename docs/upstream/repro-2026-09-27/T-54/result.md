# T-54 result

Defect: past 64 struct types in scope, a type (here std.http's $httpresp) is displaced; the error blames a field

Reproducer(s): gen.py, repro.tk, repro_import.tk, t54lib.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | 58 lib types + std.http / default: error[E4034]: field 'body' is declared at different offsets by more than one struct / --max-structs=256: one=1 |
| HEAD 4a50b87 | REPRODUCES | 58 lib types + std.http / default: error[E4034]: field 'body' is declared at different offsets by more than one struct / --max-structs=256: one=1 |

Notes: Bisected with gen.py: via imports, K=57 lib types already fails on HEAD, K=58 on PIN (K=56 ok on both). Declaring 70 types directly in one file gives a loud E9010 on both. `--max-structs=256` makes K=58 compile, link and run on both (the displacement is silent only at the default).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
