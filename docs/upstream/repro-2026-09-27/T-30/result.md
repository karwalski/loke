# T-30 - std.db has one global connection

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-30`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=0 out: ha=1 hb=1 ta-before-b=ok ta-after-b=err setup=00 |
| HEAD 4a50b87 | REPRODUCES | exit=0 out: ha=1 hb=1 ta-before-b=ok ta-after-b=err setup=00 |

ha=1 hb=1 (identical handles); table ta readable before opening the 2nd db, $err after, on both.
