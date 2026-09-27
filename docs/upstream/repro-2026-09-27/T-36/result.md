# T-36 result

Defect: str.tki gen:abi block declares members as untyped i64, so wrong arguments type-check

Reproducer(s): repro.tk, repro_b.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | str.len(array): compiles / strlen(array3)=-1 compare(a,b)=1 compare(b,a)=1 compare(a,a)=0 padleft(7,3,"0")=[7] |
| HEAD 4a50b87 | CHANGED | str.len(array): rejected: error[E4031] / strlen(array3)=-1 compare(a,b)=1 compare(b,a)=1 compare(a,a)=0 padleft(7,3,"0")=[7] |

Notes: HEAD now rejects `str.len(<array>)` (E4031, 'argument 1 of std.str.len is read by the runtime as a C string'). Still defective on HEAD: `str.compare` never negative (a,b=1; b,a=1), `str.padleft("7";3;"0")` pads with non-printable bytes (pad is a char code), `str.tof32(12345)` compiles and segfaults (rc 139). str.tki: 77 abi members on both; members declared `-> i64`: 77 (PIN) vs 55 (HEAD).

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
