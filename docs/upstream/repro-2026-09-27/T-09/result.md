# T-9 - regex: `\s` `\S` `*?` `(?i)` silently match nothing

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-9`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | exit=0 out: pattern text: \s s: a b S: a b lazy: <x>y<z> ci: ABC ctl: a_b ctl2: [x]y[x] |
| HEAD 4a50b87 | REPRODUCES | exit=0 out: pattern text: \s s: a b S: a b lazy: <x>y<z> ci: ABC ctl: a_b ctl2: [x]y[x] |

str.replacere returns input unchanged for all four; controls `[ ]` and `<[^>]*>` work.
