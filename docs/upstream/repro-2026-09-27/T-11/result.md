# T-11 - std.infer/std.mlx stubs return plausible values

Files: repro.tk, tki_arity.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-11`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | CHANGED | impl-arity calls: exit=0 out: mlx.isavailable=0 mlx.load(/nonexistent) arm=err mlx.load(/nonexistent) arm, err arm written first=ok mlx.generate arm=load-err infer.generate arm=load-err // .tki-arity calls: compile rc=1: error[E4026]: wrong number of arguments for 'std.infer.load': the implementation takes 1 argument, the call passes 2 |
| HEAD 4a50b87 | CHANGED | impl-arity calls: exit=0 out: mlx.isavailable=false mlx.load(/nonexistent) arm=err mlx.load(/nonexistent) arm, err arm written first=ok mlx.generate arm=load-err infer.generate arm=load-err // .tki-arity calls: compile rc=1: error[E4026]: wrong number of arguments for 'std.mlx.generate': the implementation takes 2 arguments, the call passes 3 |

Stub C unchanged (infer_glue.c/mlx_glue.c still return 0 and "[infer: not available]"/"[mlx: not available]"). Observed from source: `load` of a nonexistent path takes the `$err` arm (ok-first) so generate is never reached; with the err arm written first the SAME call takes `$ok` (T-31 positional binding), so the result is not trustworthy either way. mlx.isavailable prints 0 (PIN) / false (HEAD). No compile-time warning on either. The entry's std.tls/std.mdns rows are stale (tls is real; mdns has an implementation). New: calling infer.load/infer.generate/mlx.generate with the arity their .tki declares is refused with E4026 on both (tki_arity.tk).
