# T-48 result

Defect: `http.postheaders(client;"";body;headers)` (loke's provider shape) sends nothing, takes $err

Reproducer(s): repro.tk, repro_urlfirst.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | loke shape: posturl returned loke-shape postheaders arm=err url-first postheaders returned nonzero=1  recorder=[POST /control,POST /v1/messages-direct,] / url-first variant recorder=[POST /control,POST /v1/messages-direct,] / https unmeasured |
| HEAD 4a50b87 | CHANGED | loke shape: loke shape rejected: error[E4031]: type mismatch: expected 'str', got 'httpclient' recorder=[] / url-first variant recorder=[POST /control,POST /v1/messages-direct,] / https unmeasured |

Notes: Measured over http against a local recorder on 127.0.0.1:11443 only; https to any real provider was NOT attempted: **https unmeasured**. The C glue is `tk_http_postheaders_w(url, body, headers, extra)` (extra ignored) on both; the URL-first call `http.postheaders(url;body;headersjson;"")` arrived with x-api-key and content-type headers on both (content-type appears twice: the glue's own plus the custom one).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
