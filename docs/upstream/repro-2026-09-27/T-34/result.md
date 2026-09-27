# T-34 result

Defect: `http.res.err` lowers to a call of libc `err(3)` (exits the process); `http.res.json` to undefined `_json`

Reproducer(s): repro.tk, repro_json.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | res.err: rc=96 out=[r: (rno\001: Operation not permitted] / res.json: Undefined symbols |
| HEAD 4a50b87 | FIXED | res.err: rc=0 out=[built] / res.json: out=built |

Notes: HEAD IR: `call i64 @tk_http_res_err(...)`; PIN IR: `call i64 @err(...)`. PIN exit status here is 96 (the low byte of the string pointer passed as err's eval), not 144 as in the filed text, because the one-argument form passes a pointer.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
