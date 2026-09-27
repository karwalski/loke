# T-21 - `std.homedir()` interpolated is "truncated"

Files: repro.tk, nolink.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-21`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | expected every length 21: exit=0 out: interp text=[4320140176/x] interp=12 concat=21 process-interp=12 bound-then-interp=21 // std.homedir without importing std.process: compile rc=2: Undefined symbols for architecture arm64: |
| HEAD 4a50b87 | REPRODUCES | expected every length 21: exit=0 out: interp text=[4335688416/x] interp=12 concat=21 process-interp=21 bound-then-interp=21 // std.homedir without importing std.process: compile rc=2: Undefined symbols for architecture arm64: |

Interpolation prints the string's ADDRESS (e.g. "4382923344/x", len 12), not a truncated path - same mechanism as T-41. concat and bind-then-interpolate are correct (21). HEAD fixed `process.homedir()` interpolation (21) but not `std.homedir()` (12). Also: `std.homedir` does not link at all unless std.process is imported (tk_std_homedir_w lives in process_glue.c) - PIN ld error, HEAD E4027 (nolink.tk).
