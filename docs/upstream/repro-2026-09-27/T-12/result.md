# T-12 - stdlib .tki files disagree with the builtin table

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-12`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | CHANGED | missing from .tki: none; exit=0 out: padright str-arg=[ab???] code-arg=[ab***] getregulations len=0 control json.getarr len=1 |
| HEAD 4a50b87 | CHANGED | missing from .tki: none; exit=0 out: padright str-arg=[ab |

All four named gaps are now in the .tki on both (json.getarr, str.padright, process.spawndetached, file.listglob). Still wrong on both: json.getregulations returns len 0 for a document with one regulation (control json.getarr len 1); str.padright is `(i64,i64,i64)` gen:abi so a str pad char compiles and pads with a byte of its pointer (only a char code works); infer/mlx .tki arity disagrees with the implementation (T-11).
