# T-32 result

Defect: std.json cannot read a nested value; the untyped json.getval handle passed to json.i64 segfaults

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | str(usage)=err i64(usage.input_tokens)=err getval returned  rc=139 (rc 139 = getval handle fed to json.i64 segfaults) |
| HEAD 4a50b87 | REPRODUCES | str(usage)=err i64(usage.input_tokens)=err getval returned  rc=139 (rc 139 = getval handle fed to json.i64 segfaults) |

Notes: HEAD's json.tki has no typed `json.obj(Json,str)`; the only `json.obj` is `json.obj ( i64 ) -> i64 [abi]` on both.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
