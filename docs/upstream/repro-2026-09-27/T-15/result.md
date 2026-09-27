# T-15 - http.get on a closed port returns $ok with nil response

Files: repro.tk, onearg.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-15`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | CHANGED | closed port, mt http.get(client;path): exit=2 / same against a live server: exit=2, requests received=0 / http.get(url) closed port: len=0 text=[] |
| HEAD 4a50b87 | CHANGED | closed port, mt http.get(client;path): exit=2 / same against a live server: exit=2, requests received=0 / http.get(url) closed port: len=0 text=[] |

The filed shape `mt http.get(http.client(url);path)` compiles on both but is ROUTE REGISTRATION: it takes the `$err` arm (exit 2) for a closed port AND for a live local server that received 0 requests. The client form that works, `http.get(url)` -> str, returns "" (len 0) for a closed port and "ok" for a live one: no error channel, empty body indistinguishable from unreachable. Not the defect as filed (no nil deref), still wrong.
