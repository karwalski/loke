# toke and ooke answer the 2026-11-15 handoff — loke's record

**From:** toke and ooke (one maintainer for both), recorded by the loke project
**Re:** [`handoff-2026-11-15.md`](handoff-2026-11-15.md) and its reproducers in
[`repro-2026-11-15/`](repro-2026-11-15/)
**Recorded:** 2026-11-24
**Answered by:** toke `main` (measured at `eca5062f`, 2026-11-24) and ooke `main` (`4d3bf65`,
VERSION 3.0.1). **Nothing is tagged.** The fixes ship in **toke 3.3.0**, after **ooke 3.0.1**
(toke owner answer R1, 2026-11-15); toke's reply repeats "targeted early December" for 3.3.0.
loke's pins stay at toke v3.2.0 / ooke v3.0.0 until both tags exist (`TOOLCHAIN.lock`).

**Source, and how far to trust it.** As in [`toke-reply-2026-11-15.md`](toke-reply-2026-11-15.md),
this is loke's record, not a document toke sent:

1. toke's reply exists as a draft in the toke maintainer's working tree, for its owner to send
   (toke story 138.43, status `review`; drafted 2026-11-23 against `main` `a4636b56`), and in
   toke's `docs/progress.md` rows 138.19–138.44 and 127.319. These are toke's **claims**.
2. loke's own measurements on 2026-11-24, with its runners unchanged, against private builds of
   toke `main` `eca5062f` and ooke `main` `4d3bf65`
   (`/Users/…/loke/toolchain/toke-main`, `ooke-main`; never `~/tk`, which another session edits):
   [`repro-2026-11-15/results-main-eca5062f.txt`](repro-2026-11-15/results-main-eca5062f.txt),
   [`repro-2026-11-15/results-main-eca5062f-T39.txt`](repro-2026-11-15/results-main-eca5062f-T39.txt),
   [`repro-2026-11-09/results-main-eca5062f.txt`](repro-2026-11-09/results-main-eca5062f.txt).

**Every verdict loke measured agrees with toke's draft.** Where an item says "measured", loke ran it.

---

## The answer in one table

| ID | At v3.2.0 (`ea7ddf22`) | At toke `main` `eca5062f` (loke's run) | toke story | Ships in |
|---|---|---|---|---|
| T-67 (integer read as a handle or C string) | DEFECT (SIGSEGV ×3) | **OK (now rejected at --check)** | 138.35 checker, 138.36 runtime | 3.3.0 |
| 138.32 (`handle` in type position) | OPEN (E2005) | OPEN by design: the probe spells bare `h:handle`; `h:$handle` works on 3.2.0 already | 138.32 | — |
| T-60 `==` on arrays | DEFECT | refused at `--check` (E4031, fix `x.len==0`); our runner still prints DEFECT because it judges exit codes | 138.20 | 3.3.0 |
| T-60 spawn idiom, T-61, F10.42 | OK | OK | — | — |
| T-63 / MK19.11 controls | DEFECT | DEFECT on `http.geturl` **by design**: the controls are opt-in (`withdeadline`, `withmaxbody`, `withconnectaddr`, `net.resolve`), not measured by loke yet | 138.24, 138.25 | 3.3.0 |
| T-58 addendum, GET with headers | — | `http.getheaders` exists; not measured by loke yet | 138.27 | 3.3.0 |
| T-59 / B9 scoped grants | OPEN | OPEN on the runner's quoted-string probes (3.3.0 warns, W9012; the switch to refusing is 3.4.0, toke 138.52); point 4 now CAP001 | 138.19 (D1–D4), 138.44 (D5, OS enforcement) | 3.3.0 |
| 127.319 (std `T!E` read as a value) | OPEN | **OK** (E4031 at `--check`) | 127.319, 127.323 | 3.3.0 |
| T-66 | DEFECT | **OK** | 138.37 | 3.3.0 |
| T-65 | DEFECT | **OK** (exit 5) | 138.38 | 3.3.0 |
| T-39 reopened (`typeonly`, `fieldres`) | DEFECT (both) | **OK** (both) | 138.39, 138.40 | 3.3.0 |
| T-64 | OK | OK | — | — |
| O-4, O-5 | OK | OK (ooke `4d3bf65`) | — | — |
| N-7 (lint rules in the changelog) | — | toke says done (docs and a gate) | 138.41 | 3.3.0 |
| N-8 (which stdlib C to link) | — | toke says: link what `tkc --emit-deps` names | 138.42 | 3.3.0 |
| §5 `$ookecfg` comment | — | toke says: corrected on ooke `main`, no field added | ooke 134.50 | next ooke release |

## What loke must change, and when

toke lists seven items. loke's own census on 2026-11-24 (`--check` of all 673 files under
`packages/` and `tests/` against toke `main`, with loke's 3.2.0 interfaces) is the authority for
loke's scope; toke's list was read-only and partial (it says so). Stories in
`docs/epics-and-stories.md`:

| toke item | Valid on 3.2.0? | loke story |
|---|---|---|
| 1. handles held in `i64` → `$handle` (and `$tomlval` for toml documents) | yes | F10.56 |
| 2. std records held in `i64` → their type (`$tlsconn`, `$securebuf`, vecstore handles, `req:$req`) | yes | F10.56 |
| 3. std `T!E` results matched before use (127.319) | yes | F10.55 |
| 4. array `==` → `.len` | yes; loke's gate already holds it | — |
| 5. capability flags narrow only; scoped flag values; `runtime = "union"` | **no**: 3.2.0 refuses the new manifest forms | F10.58 |
| 6. runner updates (T-60eq verdict, 138.32 probe spelling) | yes | F10.58 |
| 7. diagnostic `fix` changes (E4026, CAP001) | — | F10.58 (check any tooling that reads `fix`) |

New capabilities loke can adopt only once 3.3.0 is tagged: the http client controls (MK19.11
moves `moke.proxy.fetch` off curl) and `http.getheaders` (VM1.6g's update check). F10.58.

## One item toke filed against loke

**toke 138.71** (blocked on loke, filed 2026-11-24): toke's CI checks loke out as a sibling and its
claims sweep fails on `docs/research/research-proposal.md:15` — "token savings of 60-80%" without
metric type, tokenizer, baseline or N. toke has made it a warning until loke acts. The line is on
loke's **default branch `main`** (last commit 2026-05-21), not on `foundation/reset`, where that
sentence is gone; but `foundation/reset` still has an anticipated "combined savings of 60-80%" in
the same document's "Expected findings" (line 390), which the same sweep may flag once `main`
moves. Resolving it means either fast-forwarding `main` /
changing the default branch, or qualifying the claim on `main`: a user decision (F10.59).
