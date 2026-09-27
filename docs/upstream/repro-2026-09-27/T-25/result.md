# T-25 - max_funcs counts imports; E9010 names nothing

Files: repro.tk, big.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-25`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | --check rc=0; --emit-llvm rc=2: error[E9010]: compiler limit exceeded: too many functions (x2); with --max-funcs=200 rc=0 |
| HEAD 4a50b87 | REPRODUCES | --check rc=0; --emit-llvm rc=2: error[E9010]: compiler limit exceeded: too many functions (x2); with --max-funcs=200 rc=0 |

10-fn module importing a 120-fn module: `--check` rc 0, `--emit-llvm` rc 2 "E9010 compiler limit exceeded: too many functions" (no count/limit/key, line 0), x2 on both; passes with --max-funcs=200.
