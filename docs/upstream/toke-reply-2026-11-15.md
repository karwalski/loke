# toke and ooke answer the 2026-11-09 handoff — loke's record

**From:** toke and ooke (one maintainer for both), recorded by the loke project
**Re:** [`handoff-2026-11-09.md`](handoff-2026-11-09.md) and its reproducers in
[`repro-2026-11-09/`](repro-2026-11-09/)
**Recorded:** 2026-11-15
**Answered by:** toke **v3.2.0** (`ea7ddf22`) and ooke **v3.0.0** (`7ac2472`). Both tags are
public (checked with `git ls-remote` over https on 2026-11-15). **ooke 3.0.0 requires toke 3.2.0
or later** (`mintoke = "3.2.0"`, ooke `CHANGELOG.md` "Requirements"), so the two pins move together
(loke F10.53).

**Source, and how far to trust it.** This is not a reply document from toke. It is loke's record
built from two things:

1. toke's own reply, which exists only as a draft in the toke maintainer's working tree, marked
   **"DRAFT for the owner to review. Not sent."** (last updated 2026-11-15, after the tags were
   cut), and the "Fixed for loke" / "Still open for loke" lists in toke 3.2.0's `CHANGELOG.md` and
   the 3.0.0 entry of ooke's `CHANGELOG.md`. These are toke's **claims**.
2. loke's own measurements on 2026-11-15: `repro-2026-11-09/run.sh`, unchanged apart from the
   verdict fixes described below, run against the two tagged checkouts
   ([`results-v3.2.0-ea7ddf22.txt`](repro-2026-11-09/results-v3.2.0-ea7ddf22.txt)), plus a few
   small probes named per item. Where an item says "measured", loke ran it; where it says "toke
   says", loke did not.

(loke's handoff itself was also marked "drafted, not sent"; toke answered it all the same.)

---

## The answer in one table

The first column is the run at loke's old pin (toke `86c432da` / ooke `3cc4998`,
[`results-pin-86c432da.txt`](repro-2026-11-09/results-pin-86c432da.txt)); the second is loke's
run at the release tags.

| ID | At the old pin | At toke 3.2.0 / ooke 3.0.0 (loke's run) | toke's answer | loke now |
|---|---|---|---|---|
| T-60 `==` on arrays | DEFECT | **DEFECT** (exits 2 and 3, unchanged) | open, **138.20** | keeps `find_empty_array_sentinel.py` and `.len` |
| T-60 spawn idiom | DEFECT | **OK (now rejected at --check)**: E4011 | fixed, **138.21** | keeps `$err:e 0` (still legal) |
| T-61 | OK (not reproduced) | **OK (now rejected at --check)**: E4031 | refused by 127.356 | keeps the explicit cast, which 3.2.0 requires |
| T-62 (F10.42) | DEFECT | **OK** (exits 1 and 7) | fixed, 127.274 | workaround removal is F10.42 |
| T-64 (MK19.11 `stall`) | DEFECT | **OK**: `stall: err ms=30002` (the MK19.11 line stays DEFECT for drip and big) | fixed, **138.23** (+138.31) | F10.52's audit overtaken on 3.2.0 |
| T-63 (MK19.11 `drip`, `big`) | DEFECT | **DEFECT**: `drip: ok len=8 ms=40383`, `big: ok len=67108864` | open, **138.24**, **138.25** | keeps curl; MK19.11 stays open |
| O-4 | DEFECT | **OK**: all three bad templates `$tplerr`, logged | fixed, **138.29** | keeps `check_ooke_surface.py` |
| O-5 | DEFECT | **OK (docs fixed)** | fixed, **138.30** | nothing to do |
| T-48 addendum | — | E4031 at `--check` (probe) | fixed, **138.26** | nothing to do (no loke source used it) |
| T-58 addendum, Host port | — | `Host: 127.0.0.1:47979` sent (probe) | fixed, **138.28** | nothing to do |
| T-58 addendum, GET with headers | — | not measured (no such call) | open, **138.27** | VM1.6g stays Partial |

**Nothing toke claims fixed failed loke's check.** Every "fixed" above that loke could measure
reproduced as toke described; the open items are open in both accounts. The disagreements are
about what loke imports from ooke (below, "ooke modules").

### Changes to loke's runner

`run.sh` printed three stale verdicts against the release, and was corrected on 2026-11-15
(the header comment now lists the verdicts):

- **O-5** said DEFECT because it judged the rendering. The filed defect was the CHANGELOG naming
  `{{raw ...}}`, which never was syntax; `{{raw x}}` still renders literally and should. O-5 is now
  judged on the CHANGELOG: `OK (docs fixed)` when it no longer names `{{raw` and names
  `| raw =}`, with the rendering kept in the line for reference.
- **T-60** is two lines: `T-60eq` (`==` on arrays; DEFECT) and `T-60sp` (the spawn idiom), which
  now reads `OK (now rejected at --check)` when `spawn.tk` is refused at `--check` with E4011.
- **T-61** said `note` because the program no longer compiles. The fix toke chose is to refuse the
  silent narrowing at `--check` (E4031), so that is now `OK (now rejected at --check)`.

Checked both ways: the corrected runner still gives DEFECT for T-60eq, T-60sp and O-5 and OK for
T-61 at the old pin (`86c432da` / `3cc4998`).

---

## Per item

### T-60 — `==` on arrays, and the spawn-failure value

**toke says.** The spawn half is fixed (**138.21**, `daab5644`): std's opaque records (`handle`
and the others) are judged in argument slots, so `process.wait("abc")` is E4031, and a `$err` arm
of `@()` or a string beside `$ok:h h` is E4011. `$err:e 0` stays legal; the failure value to use is
`process.badhandle()` (NULL, on which `process.wait` answers -1, `process.stdout` `$err` and
`process.kill` false). Whether `handle` may be named as a type is **138.32**, with toke's owner.
The `==` half is **still open as 138.20**: refuse it with a diagnostic pointing at `.len`, or make
it element-wise, is with toke's owner. No date.

**loke measured.** `T-60eq` DEFECT, unchanged from the pin: `a==@()` false with `a.len` 0 (exit
2), `@(1;2)==@(1;2;3)` and `@(256)==@(512)` true (exit 3). `T-60sp`: the filed program is refused
at `--check` with `error[E4011]: match arms have inconsistent types: 'handle' vs '@(?)'`.
Probes: `process.wait("abc")` is E4031 ("argument 1 of 'process.wait' is declared 'handle'");
a spawn with `$err:e 0` checks clean; with `$err:e process.badhandle()` it builds and
`process.wait` answers -1 after a failed spawn.

**loke now.** Keeps every `$err:e 0` spawn arm and `scripts/find_empty_array_sentinel.py`: the
`== @()` half of that gate is still needed because 138.20 is open, and `0` is still legal. Moving
the arms to `process.badhandle()` is optional and not filed.

### T-61 — u32 field plus an untyped integer local

**toke says.** Story 127.356 (`7d8d1e76`, `37efd5d0`, in 3.2.0) type-checks every struct-literal
field against its declaration: the T-61 shape is now E4031, "expected 'u32', got 'i64'". Before,
it compiled and narrowed silently.

**loke measured.** `T-61/repro.tk` is refused at `--check`, `repro.tk:18:20`
(`u:q.u+stray`), E4031 as quoted. At the old pin it compiled and exited 5; the filed invalid IR
never reproduced. So the shape is now a located error rather than a silent narrowing, which is the
better of the two outcomes the original ask offered.

**loke now.** `packages/core/src/privacy/system_prompt.tk:82` already writes
`((r.unplaced as i64)+stray) as u32`, which is the form 3.2.0 demands. Nothing to remove.

### T-62 (loke F10.42) — inline `@@str` row as a call argument

**toke says.** Fixed in `75209d81` (127.274), in 3.2.0.

**loke measured.** OK: `str.eq(rows.get(i).get(0);"x")` builds and exits 1; the user-function
variant exits 7; the bound control exits 1.

**loke now.** The bind-the-row-first workaround (`tests/unit/nocustody/test_artifact.tk`,
`packages/moke/tests/test_upload_csv.tk`) is harmless and stays until F10.42 is closed on the
3.2.0 build; that row is the follow-up.

### T-64 — a cut response answered `$ok`

**toke says.** Fixed (**138.23**, `60c319af`). One reader serves `http.geturl`,
`clientget`/`post`/`put`/`delete` and `postheaders`; a response cut short (incomplete headers, a
body short of its `Content-Length`, a chunked body without its last chunk, whether by close or by
read timeout) is `$err` (`$httperr`, code 0). Chunked bodies are read chunk by chunk. A
close-delimited body that ends in a timeout or reset is `$err` too (**138.31**, `1046f364`).

**loke measured.** OK: the `stall` case (`Content-Length: 8`, three bytes, then silence) answers
`stall: err ms=30002` (MK19.11 line of the results file, whose verdict stays DEFECT because of
`drip` and `big`). Only `http.geturl` was measured;
the other client calls and the chunked and close-delimited cases are toke's statement.

**loke now.** Nothing in loke worked around T-64. F10.52 (measure what each caller does with a
short body) is overtaken once loke builds on 3.2.0 (F10.53); closing it is follow-up for F10.52.

### T-63 (loke MK19.11) — connect-to-address, resolver, body cap, deadline

**toke says.** Still open. The deadline and body cap are **138.24**; connect-to-address with name
verification, and a resolver, are **138.25**. Both are new stdlib API needing a spec amendment and
an owner decision. **No date.** "Keep curl until then."

**loke measured.** DEFECT, as at the pin: `drip` answers `$ok` with all 8 bytes after 40,383 ms
(one byte every 5 s; the per-read clock restarts), and `big` reads a 64 MiB body whole and answers
`$ok`.

**loke now.** `moke.proxy.fetch` keeps the system curl (`--resolve`, `--max-filesize`,
`--max-time`); MK19.11 stays open.

### O-4 — unknown directive and unclosed block rendered as nothing

**toke says.** Fixed in ooke (**138.29**, ooke `26c8c16`): an unknown directive, a bare
`{! endblock !}`, a stray `{! end !}` and a block open at the end of the template are each
`$tplerr` and logged. A template with any of these, which used to render, now fails (behaviour
change). This is `ooke.template`, which ooke calls internal (below).

**loke measured.** OK, exit 0 (the results line is cut at 220 characters; the per-template
lines below are from the same run's output): `unknown.tkt`, `endblock.tkt` and `unclosed.tkt`
each answer `err`, with error log lines `template: unknown directive "frobnicate" (known: layout, block, end,
var, yield, partial, island)`, the same for `"endblock"`, and `template: block "body" is never
closed with {! end !}`. `control.tkt` still renders `<title>T1</title><main>BODY</main>`.

**loke now.** Keeps `scripts/check_ooke_surface.py`: it fails such a template at the gate, where
ooke 3.0.0 would only fail it at render time (loke's pages answer 500 "template render failed").
No row; the check costs nothing.

### O-5 — the changelog's `{{raw ...}}`

**toke says.** Fixed (**138.30**, ooke `d4c9bcb`): `CHANGELOG.md` now says `{= key | raw =}`, and
the same wrong syntax was corrected in `docs/public-api.md` and `docs/versioning.md`.

**loke measured.** OK (docs fixed): ooke 3.0.0's `CHANGELOG.md` contains no `{{raw` and names
`` `{= key | raw =}` ``; `docs/public-api.md` and `docs/versioning.md` contain no `{{raw` and one
`| raw =}` each. `A{{raw x}}B|{= x | raw =}|{= x =}` still renders `A{{raw x}}B|<b>|&lt;b&gt;`,
which is correct: `{{raw x}}` never was syntax.

**loke now.** Nothing; loke's templates use the filter.

### T-48 addendum — an `httpclient` where a `str` URL is declared

**toke says.** Fixed (**138.26**, `aa6f65e7`): `http.postheaders(http.client(url);…)` and
`http.geturl(http.client(url))` are E4031.

**loke measured.** Both probes are refused at `--check`: "argument 1 of 'http.postheaders' is
declared 'str' (http.tki), got 'httpclient'", and the same for `http.geturl`.

**loke now.** Nothing; no loke source used the shape.

### T-58 addendum — a header-carrying GET, and the Host port

**toke says.** The header-carrying GET is **138.27**, still open (new function, spec amendment).
The Host header that dropped the port is fixed (**138.28**, `a37cd26e`): `host:port` unless the
port is the scheme default.

**loke measured.** Host: an `http.geturl("http://127.0.0.1:47979/x")` probe against a loopback
listener sent `Host: 127.0.0.1:47979`. The GET with headers does not exist at 3.2.0, so there is
nothing to measure.

**loke now.** VM1.6g (update checks need a `User-Agent` on a GET) stays Partial, waiting on 138.27.

---

## Section 5 questions

| Item | toke says | loke measured | loke now |
|---|---|---|---|
| **T-17** `json.parse` | Nothing to do; `json.parse` refuses object handles (138.9). | Not measured; loke has no `json.parse` call. | Nothing. |
| **T-55** `str.charat` | The length-carrying string heap (127.170) ships in 3.2.0; a `.len` + `str.charat` scan is linear (~0.5 s wall at 100 k to 1.6 MB). `str.bytes(str) -> [byte]` exists for a byte view. | Not measured by loke. | Nothing filed; any hot-loop work would measure first. |
| **T-59 / B9** scoped grants | Story **138.19**, P2, planned; needs a spec amendment for grant syntax. | — | The story number answers loke's question; loke's capability comments can cite 138.19 when next edited. |
| **127.244 / 127.319** matched `m.get` / std results | The map half ships in 3.2.0: `m.get(k)+1` is E4031 (`i64!$err`). The std half (`str.toint`, `str.slice`, `json.*`) is **127.319**: a typed migration of ~1,370 files, not signed off by toke's owner; loke's acceptance is recorded. No date. | Probe: `m.get("a")+1` is refused at `--check`, "'+' requires numeric operands: the left side is 'i64!$err'". | The map half is part of F10.53's migration (`m.getor` or `mt`). The std half waits on toke. |
| RSA over 2048 bits | Nothing to do. | — | Nothing. |

toke also notes that ten E4031 sites no longer carry a prose `fix` field (127.436, 127.438); loke's
tooling does not apply `fix` automatically.

## New checks in 3.2.0 that loke's migration meets

toke lists checks that "may flag code which used to check clean": 138.22 (expression-`if`
branches of different types, E4011), 138.33 (the `$ok` payload of a std `record!err` is typed;
`$err:e "oops"` beside `$ok:x x` is E4011), 127.356 (struct-literal field types, E4031), 127.365 /
127.366 (a missing or repeated struct-literal field, E4077 / E4078). These are F10.53's business
(the build migration) and are not re-measured here.

---

## ooke modules loke imports, and ooke's statement that they are internal

**toke says.** loke imports five ooke modules, `template`, `handlers`, `serve`, `context` and
`config`, "at 30 sites". They are **internal to ooke** with no stability commitment: ooke may
rename, reshape or remove anything in them in any release, without a deprecation period or a
CHANGELOG entry addressed to loke. 138.29 is the example (it changed what `ooke.template` returns
for a malformed template). If loke needs something these modules provide, it should send a
**bindings request with the calls it uses**; ooke will then publish it as supported API or point to
the supported equivalent (story 136.9). ooke's `docs/public-api.md` §2 says the same ("pin an exact
ooke commit and expect to follow it. Making them supportable is not scheduled").

toke also asked **what loke's `ooke.context` import resolves to**, since ooke has no such module.

**loke measured** (grep over the repository, excluding `.claude/`, on 2026-11-15):

- **`ooke.context` resolves to nothing.** Its only occurrence is inside a generated string
  literal in `src/platform/testing/scaffold.tk:44`, a scaffold that writes
  `i=ctx:ooke.context;` into a new routes file. `src/` is the legacy tree; it is not built and
  nothing in `packages/` or `scripts/` imports `ooke.context`. It is dead text from the ooke
  2.0.0-era API, not a dependency.
- **Live import sites** (`i=…:ooke.…` in `packages/` and `scripts/`): **34**.

  | ooke module | sites | where | calls and types used |
  |---|---|---|---|
  | `ooke.template` | 24 | 9 `packages/browser/pages/*.tk`, 15 `packages/moke/pages/*.tk` | `tplrenderfile(path; vars; root)` and its `$ok`/`$err` (24 calls) |
  | `ooke.config` | 4 | `packages/browser/_serve_main.tk`, `packages/moke/pages/api/proxy.tk`, the generated mains in `scripts/build_loke.sh` and `scripts/build_trees.sh` | `configload(path)` and the `$ookecfg` record, built field by field in `lokedefaultcfg` (all 16 fields) |
  | `ooke.serve` | 3 | `packages/browser/_serve_main.tk`, `scripts/build_loke.sh`, `scripts/build_trees.sh` | `serverun` |
  | `ooke.handlers` | 3 | the same three | `registerall`; the module itself is loke's own generated `_handlers.tk` (`m=ooke.handlers;`), named so `serve` finds it |

- **The two counts disagree in loke's direction.** toke's "30 sites" and five modules include
  `context`, which loke does not import; ooke's `docs/public-api.md` names `ooke.router`, which
  loke does not import either (no `ooke.router` import in `packages/` or `scripts/`). loke does not
  import an `ooke.toml` or `ooke.tls` module (ooke 3.0.0 ships neither); `ooke.toml` in loke is the
  configuration file `configload` reads, and TLS reaches ooke only as the `tlscert`/`tlskey` fields
  of `$ookecfg`.

**loke now.** This is a dependency on surface ooke has said it will not keep stable, and 3.2.0's
struct-literal checks make one of the calls brittle (a field added to `$ookecfg` makes loke's
literal E4077). Whether to send a bindings request listing the calls above, or to vendor or
replace them, is **the user's decision**, filed as **F10.54**. Nothing has been sent.

---

## What loke still does, and where the follow-up lives

| Workaround or gap | Kept / removed | Row |
|---|---|---|
| `$err:e 0` spawn arms; `find_empty_array_sentinel.py` | kept (138.20 open) | — |
| `.len` instead of `==` on arrays | kept (138.20 open) | — |
| explicit `as u32` at `system_prompt.tk:82` | kept (now required) | — |
| bind an `@@str` row before subscripting it | kept until verified on the 3.2.0 build | F10.42 |
| short-body caller audit | overtaken by 138.23 once loke is on 3.2.0 | F10.52 |
| system curl in `moke.proxy.fetch` | kept (138.24, 138.25 open) | MK19.11 |
| `check_ooke_surface.py` template gate | kept | — |
| update checks without a `User-Agent` GET | still blocked (138.27) | VM1.6g |
| imports of internal ooke modules | decision needed | F10.54 |
| the build itself on toke 3.2.0 / ooke 3.0.0 | in progress | F10.53 |

## Reproducing

```sh
cd docs/upstream/repro-2026-11-09
TOKE_DIR=/path/to/toke-v3.2.0 OOKE_DIR=/path/to/ooke-v3.0.0 ./run.sh
```

The run behind this record is
[`results-v3.2.0-ea7ddf22.txt`](repro-2026-11-09/results-v3.2.0-ea7ddf22.txt). The probes quoted
for T-48, T-58, T-60 and 127.244 were single-file programs checked or built with the same toke and
are not kept in the tree.
