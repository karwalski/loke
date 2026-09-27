# T-41 result

Defect: interpolating a std.str result prints the string's address

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | 14 of 14 print an address: fromi64 fromint64 fromi32 fromu32 fromu16 frombool randhex nowiso8601 padleft padright trimws strip reverse replaceall  |
| HEAD 4a50b87 | CHANGED | 2 of 14 print an address: frombool replaceall  |

Notes: `sha256prefix` was dropped from the repro: HEAD rejects a str argument to it (E4031, it takes an array). HEAD still declares `str.frombool ( i64 ) -> i64` and `str.replaceall ( i64, i64, i64 ) -> i64`, the two that still print an address.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
