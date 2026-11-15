# ooke upstream issues

> **Current state: see [`handoff-2026-09-27.md`](handoff-2026-09-27.md)** (O-1 re-verified; O-2 and O-3 added).
> O-4 and O-5 re-verified at rc.2 (`3cc4998`) on 2026-11-09, with reproducers, in
> [`handoff-2026-11-09.md`](handoff-2026-11-09.md) (drafted, not sent).
> **Status of every item at ooke v3.0.0, 2026-11-15:** [`status-2026-11-15.md`](status-2026-11-15.md). O-1 to O-5 are all
> fixed; no new ooke item was found. ooke calls the modules loke imports internal (F10.54); the third handoff,
> [`handoff-2026-11-15.md`](handoff-2026-11-15.md) (drafted, not sent), lists the calls without making a request.
>
> **Answered 2026-11-15** by ooke v3.0.0 (`7ac2472`, requires toke 3.2.0): see [`toke-reply-2026-11-15.md`](toke-reply-2026-11-15.md).

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

**2026-11-15: fixed** in rc.2 (toke-tracked story 138.7, ooke `94607ac`); rc.1 was replaced, not
repaired. Verified by loke at 3.1.0 (F10.39: rc.2 builds) and measured at toke v3.2.0: ooke
3.0.0's `src/store.tk` passes `toke --check` (two W1001 lossy-cast warnings), while rc.1's copy in
`repro-2026-09-27/O-1/` still fails E4071 at 174:3 and 183:3, as expected.

## O-2 — the generated handler registry imports every page, so ~30 routes hit the 32-import cap

Filed in [`handoff-2026-09-27.md`](handoff-2026-09-27.md) §4. **2026-11-15: fixed** (138.7, ooke
`5d53dae`). Read, not measured: ooke 3.0.0's `scripts/gen_app_makefile.sh` passes
`--max-imports=N` when the page count passes 32. loke generates its own registry and sets
`max_imports = 40` in `tkc.toml` (MK6.5).

## O-3 — `[server] host`: ooke needs a bind address too

Filed in [`handoff-2026-09-27.md`](handoff-2026-09-27.md) §4. **2026-11-15: fixed** (138.7, ooke
`076db84`, `be126df`). Verified by loke at 3.1.0 (loke's generated server mains pass
`[server] host` to `serve.serverun`); the `127.0.0.1` default is read from ooke 3.0.0's
`src/config.tk` (`toml.str(server;"host")`, `$err` arm `"127.0.0.1"`).

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

**Reproduced 2026-11-09 at rc.2 (`3cc4998`)** with rc.2's own `template.tk`:
[`repro-2026-11-09/O-4/`](repro-2026-11-09/O-4/). An unknown directive renders `AB` from
`A{! frobnicate("x") !}B`; a body block closed with `endblock`, or never closed, renders the
layout with an empty `<main>`; all three answer `$ok`.

**2026-11-15: fixed in ooke v3.0.0 (`7ac2472`)**, toke-tracked story **138.29** (ooke `26c8c16`).
Measured with the same reproducer: `unknown.tkt`, `endblock.tkt` and `unclosed.tkt` each answer
`$tplerr` and log it ("template: unknown directive …", "block \"body\" is never closed"); exit 0;
`control.tkt` still renders BODY. ooke states `ooke.template` is internal (no stability promise),
which is F10.54. loke keeps `scripts/check_ooke_surface.py`, which catches the same templates at
the gate rather than as a 500 at runtime.

## O-5 — the 3.0.0 changelog names a raw syntax the engine does not have

**Severity: documentation; misleads a consumer migrating from 2.0.0.**

`CHANGELOG.md` (3.0.0-rc.2, "Breaking, relative to 2.0.0") says a template that relied on raw
interpolation should "Use `{{raw ...}}`". The rc.2 lexer recognises `{= =}`, `{! !}` and
`{# #}` only; `{{` is literal text. Raw output is the `raw` filter, `{= key | raw =}`
(`tplapplyfilter`). Combined with O-4, following the changelog produces literal braces in the
page rather than an error.

**The ask:** correct the changelog entry to `{= key | raw =}`.

**Reproduced 2026-11-09 at rc.2 (`3cc4998`)**, [`repro-2026-11-09/O-5/`](repro-2026-11-09/O-5/):
`A{{raw x}}B|{= x | raw =}|{= x =}` with `x = "<b>"` renders `A{{raw x}}B|<b>|&lt;b&gt;`.

**2026-11-15: fixed in ooke v3.0.0 (`7ac2472`)**, story **138.30** (`d4c9bcb`): the CHANGELOG no
longer names `{{raw`, and names `{= key | raw =}`; `docs/public-api.md` and `docs/versioning.md`
are corrected too (checked 2026-11-15: no `{{raw`, one `| raw =}` each). `{{raw x}}` still renders literally, as
it never was syntax. Nothing to change in loke.
