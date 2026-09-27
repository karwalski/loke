# T-27 - `(*` inside a comment nests and swallows the file

Files: repro.tk (EXPECTED vs DEFECT in each header comment).
Rerun: `TOKE_DIR=<toke checkout> ../run.sh T-27`

| compiler | status | observed (run.sh line) |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | compile rc=1: error[E9020]: no main function defined — every executable toke program needs an entry point // --emit-llvm rc=0, survived defined in IR: 0 // control without the paren-star: exit=1 |
| HEAD 4a50b87 | REPRODUCES | compile rc=1: error[E9023]: no main function defined — every executable toke program needs an entry point, e.g. `f=main():i64{...};`; to type-check a library module without one use --check // --emit-llvm rc=0, survived defined in IR: 0 // control without the paren-star: exit=1 |

Executable build: only "no main function defined" (E9020 PIN / E9023 HEAD). --emit-llvm rc 0 with `survived` absent from IR. Control with the paren-star removed exits 1.
