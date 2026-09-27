# T-46 result

Defect: annotated `let g:str=str.fromi64(...)` used as an array element is compiled as a spread (element vanishes / garbage / crash)

Reproducer(s): repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | fromi64: len(@("g";g))=1 len(@(g;"first"))=1 / fromint control: len(@("h";h))=2 rc=139  |
| HEAD 4a50b87 | FIXED | fromi64: len(@("g";g))=2 len(@(g;"first"))=2 / fromint control: len(@("h";h))=2 randhex: len=2 a[0]=g a[last]=12345 rc=0  |

Notes: PIN: randhex case gave len=3 on one run and SIGSEGV (rc 139) on another; nondeterministic garbage length as filed.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
