# T-7 - unknown method call not checked; link error

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-7`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | compile rc=2: Undefined symbols for architecture arm64: |
| HEAD 4a50b87 | FIXED | compile rc=1: error[E4036]: no receiver method 'nosuchmethod': no built-in receiver type answers 'nosuchmethod' |

PIN: ld "Undefined symbols _nosuchmethod", E9003. HEAD: E4036 no receiver method 'nosuchmethod'.
