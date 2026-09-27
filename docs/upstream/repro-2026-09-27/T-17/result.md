# T-17 - `json.parse` binds to an unrelated runtime function

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-17`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=0 out: decode a=[xyz] parse a=[] |
| HEAD 4a50b87 | REPRODUCES | exit=0 out: decode a=[xyz] parse a=[] |

decode a=[xyz], parse a=[] on both. IR now calls `@tk_json_parse` directly (not via an unresolved _w name) on both.
