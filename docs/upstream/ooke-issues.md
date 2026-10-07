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

## O-4 — the template engine renders an unknown directive, and an unclosed block, as nothing

**Severity: silent loss of a page's content. Found by loke F10.8 (2026-10-07), ooke `v3.0.0-rc.2` (`3cc4998`).**

`tplrender` in `src/template.tk` acts on seven directive names (`layout`, `block`, `end`,
`var`, `yield`, `partial`, `island`) and drops any other `{! .. !}` token without a word. A
`block` that is never closed by `end` is never appended to the collected blocks, so the
layout's `yield` for it, and for any block opened before it, renders empty. Neither case
returns a `$tplerr` or logs.

**What it cost in loke.** `templates/tabs.tkt` closed its blocks with `{! endblock !}` and
`templates/privacy.tkt` with `{! /block !}`. Under rc.2, `GET /tabs` and `GET /privacy`
answered 200 with the base layout alone (2,536 bytes, an empty `<title>`), and every status
probe passed. `templates/installer.tkt`'s `{! raw("hardware_json") !}` rendered as nothing, so
the page parsed an empty string and showed no hardware. Fixed in loke by using `end` and an
escaped `{= .. =}` in a data attribute; `scripts/check_ooke_surface.py` now reads the directive
and filter names out of the pinned `template.tk` and fails a template that uses any other, or
whose `block`/`end` counts differ.

**The ask:** return a `$tplerr` (and log it, per 134.24) for an unknown directive name and for
a block still open at the end of the template.

## O-5 — the 3.0.0 changelog names a raw syntax the engine does not have

**Severity: documentation; misleads a consumer migrating from 2.0.0.**

`CHANGELOG.md` (3.0.0-rc.2, "Breaking, relative to 2.0.0") says a template that relied on raw
interpolation should "Use `{{raw ...}}`". The rc.2 lexer recognises `{= =}`, `{! !}` and
`{# #}` only; `{{` is literal text. Raw output is the `raw` filter, `{= key | raw =}`
(`tplapplyfilter`). Combined with O-4, following the changelog produces literal braces in the
page rather than an error.

**The ask:** correct the changelog entry to `{= key | raw =}`.
