# T-20 - f64 returned across a module boundary is corrupted

Files: repro.tk, lib.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-20`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | build rc=0 exit=5 (expected 55; tens digit = cross-module value/10) decl: declare fastcc i64 @lib_f64abs(double) |
| HEAD 4a50b87 | REPRODUCES | build rc=0 exit=5 (expected 55; tens digit = cross-module value/10) decl: declare fastcc i64 @lib_f64abs(double) |

exit 5 (expected 55): cross-module f64abs(-50.0) as i64 = 1; same fn in-module = 50. IR on both: `declare fastcc i64 @lib_f64abs(double)`. Side finding: PIN cannot build two sources in one `toke --out b a.tk b.tk` invocation (clang gets "m0.ll m1.ll" as ONE path); HEAD can. run.sh links manually for both.
