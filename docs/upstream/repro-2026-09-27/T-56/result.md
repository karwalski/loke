# T-56 result

Defect: a module may import at most 32 others (E9010), capping an ooke handler registry

Reproducer(s): gen.py, p01.tk, p02.tk, p03.tk, p04.tk, p05.tk, p06.tk, p07.tk, p08.tk, p09.tk, p10.tk, p11.tk, p12.tk, p13.tk, p14.tk, p15.tk, p16.tk, p17.tk, p18.tk, p19.tk, p20.tk, p21.tk, p22.tk, p23.tk, p24.tk, p25.tk, p26.tk, p27.tk, p28.tk, p29.tk, p30.tk, p31.tk, p32.tk, p33.tk, p34.tk, p35.tk, repro.tk (see header comment for EXPECTED vs DEFECT). Driven by `../run2.sh TOKE_DIR`.

| compiler | status | observed |
|---|---|---|
| PIN 0b0bc4e | REPRODUCES | 36 imports (35 pages + std.io) / default: error[E9010]: compiler limit exceeded: too many imports / --max-imports=64: sum=630 |
| HEAD 4a50b87 | REPRODUCES | 36 imports (35 pages + std.io) / default: error[E9010]: compiler limit exceeded: too many imports / --max-imports=64: sum=630 |

Notes: 31 page imports + std.io compiles, 32 + std.io fails, on both. `--max-imports=64` compiles, links and runs a 35-page registry on both (sum=630). The diagnostic does not name the flag.

Build note: both compilers truncate their stdlib source list at 8192 bytes (`char sources[8192]` in llvm.c/stdlib_deps.h) when the checkout path is long, so std.http programs fail to link from this path; builds here go through ../w2tools/tkbuild.sh, whose clang shim re-supplies the same selective source list (recomputed from src/stdlib_deps.c) without the cut.
