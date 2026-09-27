# O-1 - ooke v3.0.0-rc.1 store.tk fails E4071 on toke >= 060e11b

Files: , store.tk, min.tk, tkc.toml (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh O-1`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | COMPILES (defect absent, as the entry says) | ooke v3.0.0-rc.1 src/store.tk --emit-llvm rc=0 |
| HEAD 4a50b87 | REPRODUCES | ooke v3.0.0-rc.1 src/store.tk --emit-llvm rc=1 error[E4071]: function body ends in an error propagation with no '<': on the success path nothing is returned, and the function returns 0 --> store.tk:174:3 error[E4071]: function body ends in an error propagation with no '<': on the success path nothing is returned, and the function returns 0 --> s |

PIN: store.tk --check and --emit-llvm rc 0. HEAD: E4071 at store.tk:174:3 and :183:3. 060e11b is an ancestor of HEAD and not of PIN. Corrections: the first function is `storeslug`, not `storeget`; `c07c503` is the TAG OBJECT, the tagged commit is d4acc03.
