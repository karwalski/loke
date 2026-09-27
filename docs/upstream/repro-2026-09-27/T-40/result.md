# T-40 result

Defect: `db.exec` runs only the first statement of a multi-statement string and returns ok

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | program: open-ok exec-ok / sqlite_master (sqlite3 CLI): x, |
| HEAD 4a50b87 | REPRODUCES | program: open-ok exec-ok / sqlite_master (sqlite3 CLI): x, |

Notes: Verified with the sqlite3 CLI on the file the program wrote. Side observation: on PIN the program's own interpolation of the nested-mt row.str result printed an address (the sqlite3 CLI result is the evidence used).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
