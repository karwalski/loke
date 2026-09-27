# T-16 - no API to build an http request / read a response body

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-16`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | compile rc=1: error[E4027]: module 'std.http' has no member 'mockreq': neither the interface nor the runtime declares it (the call would link against 'tk_http_mockreq_w') |
| HEAD 4a50b87 | REPRODUCES | compile rc=1: error[E4027]: module 'std.http' has no member 'mockreq': neither the interface nor the runtime declares it (the call would link against 'tk_http_mockreq_w') |

E4027 no member mockreq / resbody on both (feature still absent).
