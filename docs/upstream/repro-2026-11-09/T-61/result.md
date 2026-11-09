# T-61 result — does not reproduce

Filed 2026-10-01 (loke F3.9b) from `core.privacy.systemprompt`, where
`unplaced:r.unplaced+stray` (`r.unplaced:u32`, `stray` an untyped integer local) failed at
the LLVM step with `'%t212' defined with type 'i64' but expected 'i32'`. It was seen by one
worker and never reduced.

Checked 2026-11-09 at toke v3.1.0 (`86c432da`):

| what | observed |
|---|---|
| `repro.tk` + `t61lib.tk`: the u32 field plus an untyped local, as a `let`, in a struct literal, in a return of a struct declared in another module, with the local counted by `+1` in a loop or returned by a function | compiles and runs; exit 5, `x=5 y=5 out.u=5 z=6 w=7` |
| the filed site itself: `packages/core/src/privacy/system_prompt.tk` with line 82 put back to `unplaced:r.unplaced+stray;`, compiled with loke's `tkc.toml` against the interfaces of a full `scripts/build_loke.sh` build | `--emit-llvm` rc 0, and `clang -c -x ir` accepts the IR: the field is loaded and added as i64 (`llvm.sadd.with.overflow.i64`) |
| the same, with `stray` counted inline in `run` instead of returned by `unlocated` | rc 0, clang accepts |

So T-61 is **not reproduced** on the pinned compiler, standalone or at the site where it was
reported. The original failing source was never committed (the module's first commit already
carries the workaround), so the exact shape that failed is not known. loke keeps the
workaround, which is harmless, and makes no ask; the entry stays so the next occurrence can be
captured with its source.
