# ooke upstream issues

> **Current state: see [`handoff-2026-09-27.md`](handoff-2026-09-27.md)** (O-1 re-verified; O-2 and O-3 added).

Defects in ooke found while building loke. The toke ones are in `toke-issues.md`.

## O-1 — ooke 3.0.0-rc.1 does not compile with toke after `060e11b`

**Severity: blocks the build, as soon as the local toke is rebuilt past the pin.**

Measured 2026-09-26. `src/store.tk` in ooke `v3.0.0-rc.1` (`c07c503`, the `TOOLCHAIN.lock`
pin) ends `storeget` and `storefind` with `(file.listall("")!$storeerr)`, at lines 174 and 183.
Each function's body ends in an error propagation with no `<`. toke `060e11b` (2026-09-24,
toke story 127.127) made that `E4071`, where before it silently returned null on the success
path. The pinned toke, `0b0bc4e`, predates `060e11b` and still builds it.

**What it cost in loke.** The local `~/tk/toke` checkout is ahead of the pin. When its binary
was rebuilt on 2026-09-26, `scripts/build_loke.sh` failed at `ooke module store does not
compile`, while nothing in loke had changed. Building toke at the pinned `0b0bc4e` and passing
it as `TOKE_DIR` builds loke, moke and the CLI, and every test passes.
`scripts/check_toolchain.sh` warns about a checkout ahead of the pin, but warns only.

**The ask:** end both functions with an explicit `<`, so a later ooke rc builds on current
toke. Until then, loke builds only against a toke at or before the pin.
