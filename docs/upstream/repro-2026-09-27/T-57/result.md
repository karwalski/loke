# T-57 result

Defect: `http.get(client;path)` registers a GET route (sends nothing); returns read as $err, then $ok after the 256-entry table fills

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | one-arg control arm=ok two-arg calls=300 ok_arm=44 first_ok_call=257 / recorder: 1 GET /control, |
| HEAD 4a50b87 | REPRODUCES | one-arg control arm=ok two-arg calls=300 ok_arm=44 first_ok_call=257 / recorder: 1 GET /control, |

Notes: Recorder on 127.0.0.1:11445 logged only the one-argument control `GET /control`; zero `/health` requests from 300 two-argument calls. First `$ok` at call 257 (256 registrations), ok on the remaining 44, identical on both.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
