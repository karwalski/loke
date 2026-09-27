# T-8 - `--lint --fix` deletes a needed import (type-only use)

Files: repro.tk, ty.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-8`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | lint --fix: repro.tk:6:1: warning: [unused-import] imported module 't' is never used [auto-fixed]; import removed=yes; --check after fix rc=1 error[E3011]: identifier 'lokeerr' is not declared |
| HEAD 4a50b87 | FIXED | lint --fix: tkc: no lint warnings; import removed=no; --check after fix rc=0 |

PIN removes `i=t:ty;`, reports "fixed 1 violation", file then fails E3011 lokeerr not declared. HEAD: no lint warning, file unchanged.
