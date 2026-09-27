# T-51 result

Defect: json.dec accepts `{not json` and reading the value crashes

Reproducer(s): repro.tk, repro_errfirst.tk, repro_more.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | NO-STANDALONE-REPRO | ok-first: dec arm=jsonerr read=dec-err / err-first (T-31 order): errfirst dec arm=ok read=str-err  |
| HEAD 4a50b87 | NO-STANDALONE-REPRO | ok-first: dec arm=jsonerr read=dec-err / err-first (T-31 order): errfirst dec arm=ok read=str-err  |

Notes: With the `$ok` arm first, `{not json` takes `$jsonerr` on both compilers, as do `{not`, `{a:1}`, `{"a":}`, `{"a":1`, `garbage`, and empty (repro_more.tk). `{"a":1}x` (trailing garbage) is accepted on both. With the `$jsonerr` arm written first (repro_errfirst.tk) the `$ok` arm runs — that is T-31, and json.str on the value then took its err arm, no crash. The loke site is packages/mcp-toke/src/server.tk (the `wellformed` pre-check comment citing T-51); the standalone decoder does not reproduce the filed behaviour.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
