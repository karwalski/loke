# toke — issues found building loke

**Reported by:** the loke project (`github.com/karwalski/loke`)
**Toolchain under test:** toke `445f519` (mechanisms re-verified against `c4e4704`) (on `feat/type-flow-bytes-redesign`, `toke_min_commit = 6cc9061`), ooke `v3.0.0-rc.1`
**Date:** 2026-09-20
**Context:** migrating 217 toke modules from a four-month-old API to the current one, and getting them to link for the first time

Every item below is reproduced with a minimal program that was actually compiled, or
— where a minimal case did not reproduce — with the exact loke function and the
emitted IR. Each carries the workaround loke is now using, so nothing here blocks us.

**Please read T-1 through T-7 as one family first.** Five of the seven are the same
shape of problem: **toke accepts the program and the failure appears at link time, in
LLVM's words, naming no toke source file, function or line.** That is the most
expensive property of the set, more than any individual bug. A red link that says

```
error: invalid LLVM IR input: Terminator found in the middle of a basic block!
label %rm_err11
```

gives a user nothing to search for. Finding the cause of each of these meant reading
emitted IR and bisecting by hand. Three of the four sweeps loke now runs
(`scripts/check_match_labels.py`, `scripts/find_shadowed_lets.py`,
`scripts/find_typename_values.py`) exist only to recover information the compiler
already had and discarded.

---

## Summary

| | Severity | What | Reported as |
|---|---|---|---|
| **T-1** | Blocks | `$ok(<bool>)` in a `bool!$err` function emits invalid IR | clang: `'%t' defined with type 'i1' but expected 'i64'` |
| **T-2** | Blocks | A `mt` of 3+ arms whose subject type is not known emits duplicate basic-block labels | clang: `Terminator found in the middle of a basic block!` |
| **T-3** | Blocks | An `i32` used as an array index is widened with `zext i1` | clang: `'%t' defined with type 'i32' but expected 'i1'` |
| **T-4** | Blocks, silent | A bare **type name** in expression position gets no diagnostic | clang: `use of undefined value '%store'` |
| **T-5** | Blocks | `void!$err` lowers to LLVM `void`, so binding the result emits `alloca void` | clang: `void type only allowed for function results` |
| **T-6** | Blocks | **Any** `let` shadowing an enclosing `let` emits invalid IR | clang: `Instruction does not dominate all uses!` |
| **T-7** | Blocks, silent | An unknown **method** call is not checked; it becomes an undefined external symbol | ld: `Undefined symbols` |
| **T-8** | Hazard | `--lint --fix` deletes imports that are needed | none — it reports success |
| **T-9** | Hazard, silent | The regex engine ignores unsupported syntax instead of rejecting it | none |
| **T-10** | Hazard | `http.post` is declared twice in `http.tki`, so the function form is unreachable | misleading arity error |
| **T-11** | Correctness | `std.tls`, `std.mdns`, `std.infer`, `std.mlx` are stubs that return 0 or a sentinel string | none |
| **T-12** | Docs | Four stdlib `.tki` files disagree with the compiler's own builtin table | none |
| **T-13** | Blocks, silent | A bare sum variant in a value position crashes when matched | none |
| **T-14** | Correctness, silent | `==` on two sums compares the handle, not the variant | none |
| **T-15** | Correctness, silent | `http.get` on a closed port returns `$ok` with a NIL response | none |
| **T-16** | Testability | No way to construct an http request or read a response body from source | n/a |
| **T-17** | Blocks, silent | `json.parse` binds to an unrelated runtime function | none |
| **T-18** | **Correctness, silent** | **`mt` on an `X!$userErr` takes the FIRST arm whatever the value is** | none |
| **T-19** | Blocks, silent | E4071 misses a trailing bare `mt` when the function returns a sum or struct | none |
| **T-20** | **Correctness, silent** | **An `f64` returned across a module boundary is corrupted** | none |
| **T-21** | Correctness, silent | A string returned by `std.homedir()` is truncated when interpolated | none |
| **T-22** | Blocks, silent | `row.f64` is declared as a result but returns a bare `i64` | none |
| **T-23** | **Correctness, silent** | **Arguments of different declared types but the same ABI are accepted reversed** (`str.join`) | none — segfault |
| **T-24** | **Correctness, silent** | **`@(array; element)` nests instead of appending** | none — intermittent segfault |
| **T-25** | Blocks | `max_funcs` counts imported signatures; E9010 names neither the limit, the cause, nor that it is configurable | E9010, no line number |
| **T-26** | **Blocks, and the fix advice creates a silent bug** | **No assignment to a struct field or array element, and E2002 recommends `==`, which compiles to a no-op** | E2002, with wrong advice |
| **T-27** | **Silent code deletion** | **Comments nest, so `(*` inside a comment (e.g. `COUNT(*)`) swallows the rest of the file** | none at all |
| **T-28** | Silent segfault | **`str.isdigit` crashes on a `str.charat` result** — the only producer of a character cannot feed the only classifier of one | none — SIGSEGV |
| **T-29** | Minor | Control-flow keywords (`sc`, `mt`, `lp`, `el`, `br`, `if`) are reserved as import aliases and the diagnostic does not name the reserved word | E2002, unhelpful |
| **T-30** | **Correctness, silent** | **`std.db` has ONE global connection; `db.open`'s returned handle selects nothing, so a two-database program silently queries whichever opened last** | none |

T-1 to T-7 are build-breaking. T-8 to T-12 are hazards that let a wrong program look
right. **T-13 to T-24 were found later, getting loke's test suite to run against real
modules rather than stubs, and four of them are worse than anything above: T-18, T-20,
T-23 and T-24 are silent, they affect every module in the codebase, and nothing in the
language or the tooling reports them.**

T-23 and T-24 share a shape worth naming on its own. Both are cases where the **declared
type is right there** — `str.join(str, [str])` in the `.tki`, `@$entry` on the field —
and the call site is simply not checked against it, because at the ABI everything is an
`i64` handle. The failure mode is the worst available: it compiles clean, it runs clean
until that exact line executes, and then it segfaults. T-24 in particular crashed one of
our tests in 19 runs out of 20, which means a green CI run was not evidence of
anything. Between them they account for **99 defective call sites across 53 files**
in this repository — 70 `str.join` calls in 40 files and 29 nesting appends in 14 —
every one of which read as obviously correct.

**Verified fixed in 445f519 (thank you): T-1, T-3, T-4, T-5 and T-6.** T-6 also gained
`W3013`, the shadowing warning this document asked for, which is exactly right. T-2 and
T-7 remain. `std.tls` is now a real TLS 1.3 implementation with `tls.mutualconfig`,
which closed the gap that had forced us to reopen two stories — that is the single most
useful change for this project in the release.

---

## T-1 — `$ok(<bool>)` in a `bool!$err` function emits invalid IR

**Severity:** blocks. `bool!$errtype` is unusable.

```toke
m=b1;
t=$e1{ $bad:str };
f=inner(x:i64):bool{
  <x>0
};
f=outer(x:i64):bool!$e1{
  <$ok(inner(x))
};
f=main():i64{
  mt outer(1) { $ok:v 0; $err:e 1 }
};
```

```
/tmp/tkc_qCZ727.ll:32:19: error: '%t4' defined with type 'i1' but expected 'i64'
E9003 clang invocation failed with exit code 1
```

toke emits `inttoptr i64 %t4` on an `i1` without widening it first. Tested in loke's
own `core/mcp/client.tk`, the emitted IR reads:

```llvm
%t173 = call fastcc i1 @core_mcp_client_checkinitobj( i64 %t170, i8* %t171, i8* %t172)
%t174 = inttoptr i64 %t173 to i8*
```

**What does not work as a workaround:** binding the bool to a local first; using a
bool literal (`<$ok(true)`); branching so each arm returns `$ok(true)` / `$ok(false)`.
All three fail identically.

**What loke does:** declares the function `i64!$errtype` and returns `$ok(1)` / `$ok(0)`.

**Suggested fix:** `zext i1 … to i64` before the `inttoptr`, wherever a success value
is boxed into the result representation.

---

## T-2 — a multi-arm `mt` whose subject type is not known emits duplicate labels

**Severity:** blocks. This was the single most expensive item in the migration: **17
sites** across loke, each found by reading IR.

```toke
m=bi;
t=$r{ ok:bool; msg:str };
f=h(e:i64):$r{
  mt e {
    $notfound:v $r{ok:false;msg:"nf"};
    $permission:v $r{ok:false;msg:"pd"};
    $io:v $r{ok:false;msg:"io"}
  }
};
f=main():i64{ <0 };
```

```
error: invalid LLVM IR input: Terminator found in the middle of a basic block!
label %rm_err1
```

The emitted IR defines `rm_err<n>` **once per arm past the first**:

```llvm
rm_err2:
  %v.1 = alloca i64
  …
  br label %rm_end2
rm_err2:            ; <- same label again
  %v.2 = alloca i64
```

So the label scheme looks like it assumes one `rm_ok` / `rm_err` pair per match —
which is exactly right for two arms and wrong for three or more.

### Measured behaviour

| Shape | Result |
|---|---|
| `mt x { 2 arms }` — any subject | links (this is why every `$ok`/`$err` match in the codebase is fine) |
| `mt x { 3+ arms }` where `x` is a parameter **declared as the sum type** | links |
| `mt mk() { 3+ arms }` — a direct call result | links |
| `mt x { 3+ arms }` where `x:i64` carries a sum | **fails** |
| `mt w.tier { 3+ arms }` — a struct field | **fails** |
| `let t=w.tier; mt t { 3+ arms }` — untyped local | **fails** |
| `let t:$s=w.tier; mt t { 3+ arms }` — **annotated** local | links |
| a 3+-arm `mt` nested inside another match's arm | **fails** |

The pattern across all eight rows: it works when toke can see the subject's sum type
at the match, and produces invalid IR when it cannot.

**What loke does:** annotates the subject (`let status:$ollamastatus=ollama.healthcheck(client);`),
or lifts the match into a function taking the sum as a typed parameter. Where the sum
is one of toke's own and is not nameable from user code — `ProcessErr`; see T-12 — loke
declares a local sum with the same variant names and uses that as the parameter type.

**Suggested fix:** the label counter should be per arm, not per match. Separately, a
match on a value whose sum type is not known is worth an error in its own right — that
is the condition that makes this reachable.

---

## T-3 — an `i32` array index is widened with `zext i1`

**Severity:** blocks.

```toke
m=bc;
f=at(a:@i64;i:i32):i64{
  <a.get(i)
};
f=main():i64{
  <at(@(1;2;3);1 as i32)
};
```

```
error: '%t189' defined with type 'i32' but expected 'i1'
```

The emitted IR loads the index as `i32` and then widens it as if it were a bool:

```llvm
%t189 = load i32, i32* %i
%t190 = zext i1 %t189 to i64
```

**What loke does:** declares index parameters `i64`. Casting at the call site
(`a.get(i as i64)`) also works.

**Suggested fix:** `sext i32 … to i64` for a signed index. The `zext i1` looks like a
default branch being taken for any non-`i64` integer.

---

## T-4 — a bare type name in expression position gets no diagnostic

**Severity:** blocks, and silent. The diagnostic that does exist, E4033, does not fire
here.

```toke
m=bg;
t=$thing{ n:i64 };
f=take(x:$thing):i64{ <x.n };
f=run():i64{
  <take(thing)          (* `thing` is the TYPE; no local of that name exists *)
};
f=main():i64{ <run() };
```

```
error: use of undefined value '%thing'
E9003 clang invocation failed with exit code 1
```

No E3011, no E4033, no warning. For comparison, toke **does** report an undefined
identifier correctly when it is not also a type name:

```toke
f=run():str{ <take(neverdeclared) };     (* -> E3011, as it should be *)
```

and it **does** report a type name used with a field access:

```
E4033 'drawer' is a type name, not a value: 'drawer.id' has no meaning
```

So the gap is narrow and the message already exists — a bare type name as a call
argument just isn't checked. In loke this hid a genuinely missing parameter in
`core/policy/export.tk:exportcompliance` and in `core/policy/feedback.tk`, where three
functions referenced a `store` that was declared nowhere. The sibling function
`exportaudit` took `store:$store` correctly, so the two sat side by side for months.

**What loke does:** `scripts/find_typename_values.py` sweeps for it.

**Suggested fix:** extend E4033 to a bare type name in any value position.

---

## T-5 — `void!$err` lowers to LLVM `void`

**Severity:** blocks. Same family as T-1: only an i64-width success type survives the
`!$err` lowering.

```toke
m=bh;
t=$e{ $bad:str };
f=inner(x:i64):void!$e{
  if(x>0){ <$ok(void) }el{ <$err($bad("no")) }
};
f=outer(x:i64):void!$e{
  mt inner(x) { $ok:v $ok(void); $err:e $err($bad("up")) }
};
f=main():i64{ mt outer(1) { $ok:v 0; $err:e 1 } };
```

```
error: void type only allowed for function results
```

The call site allocates space for the result and the result type is `void`:

```llvm
%t286 = alloca void
```

loke had **17** such declarations across 8 files.

**What loke does:** declares them `i64!$errtype` and returns `$ok(0)`.

**Suggested fix:** represent a `void` success as a zero-width or i64 placeholder in the
result lowering, as `$ok(void)` already implies.

---

## T-6 — any `let` shadowing an enclosing `let` emits invalid IR

**Severity:** blocks. This is the one to fix first if only one gets fixed, because the
same source defect is also a silent logic bug — see the note below.

```toke
m=bk;
f=pick(x:i64):i64{
  let p=x;
  if(p==0){
    let p=8739;
    <p              (* the inner value is used only inside the branch *)
  }el{
    <p
  }
};
f=main():i64{ <pick(0) };
```

```
error: invalid LLVM IR input: Instruction does not dominate all uses!
  %p.1 = alloca i64, align 8
  %t4 = load ptr, ptr %p.1, align 8
```

toke emits the `alloca` inside the branch and the load after it. This fails **whether
or not the inner binding's value escapes the branch**, so in practice toke has no
lexical shadowing at all: every occurrence is a build break.

### Why this one matters most

Shadowing is also how an ordinary mistake looks. In toke, `let x=…` inside an `if`
does not assign to an outer `x` — so this, which reads like an assignment:

```toke
let blocked=false;
lp(let i=0;i<topics.len;i=i+1){
  if(str.contains(lower;topics.get(i))){
    let blocked=true            (* declares a second, branch-local `blocked` *)
  }
};
if(blocked){ <false }el{ <true }
```

always returns `true`. That is real code from loke's
`core/memory/privacy.tk:shouldstore`, and it meant a user's opt-out topics were never
honoured. We found **52 shadowed bindings across 18 files** this way, including four
job-queue state transitions that were infinite loops (`let i=i+1` never advanced the
counter, `let lv=1` never broke), a model registry that could never find a model, an
Ollama model list that was always empty, and a shorthand expander that returned its
input unchanged. All of them compiled.

So a diagnostic here would catch a class of silent logic bug at the same time as it
fixes the codegen. Even a warning — *"this `let` shadows a binding in an enclosing
scope; did you mean an assignment to a `mut`?"* — would have saved most of the effort
in this migration.

**What loke does:** `scripts/find_shadowed_lets.py`, scope-aware, in the quality gate.

**Suggested fix:** hoist every `alloca` to the function entry block. Independently,
reject or warn on a shadowing `let`.

---

## T-7 — an unknown method call is not checked

**Severity:** blocks, and silent.

```toke
m=bn;
f=run():i64{
  let a=@(1;2;3);
  <a.nosuchmethod(2).len
};
f=main():i64{ <run() };
```

```
Undefined symbols for architecture arm64:
  "_nosuchmethod", referenced from: …
E9003 clang invocation failed with exit code 1
```

No E4027, no E3011. A plain undefined *function* call is reported properly (E3011), so
the check exists for one call form and not the other.

In loke this hid two whole non-functional code paths. `shared/config.tk` called
`file.parsetoml(raw)` and then `parsed.getstr("project.data_dir")` — a fluent TOML API
that does not exist anywhere in toke — so **loke has never read its own config file**,
and nothing said so. `core/memory/search.tk` called `.take(limit)` on an array, which
is not a toke array method.

**Suggested fix:** resolve method calls against the receiver's type and report E4027
(`module 'x' has no member 'y'`) or its method equivalent when there is no match.

---

## T-8 — `toke --lint --fix` deletes imports that are needed

**Severity:** hazard. Reported before; repeating it here so the set is in one place.

The `unused-import` rule looks only at **alias** usage (`t.foo`) and ignores **type**
references, so it removes `i=t:shared.types;` from a file whose only use of that module
is `$lokeerr`. Applied across loke it deleted **197 imports in 119 files** and produced
265 `identifier 'lokeerr' is not declared` errors, and `--fix` reported success.

A `--fix` that breaks a correct file is worse than no `--fix`. Suggested fix: count
`$type` references as uses; failing that, exclude `unused-import` from `--fix`.

---

## T-9 — the regex engine ignores unsupported syntax

**Severity:** hazard, silent.

`\s`, `\S`, non-greedy `*?` and the inline flag `(?i)` all return **no match** rather
than raising. So a pattern using them compiles, runs, and quietly does nothing. This is
how loke's `privacy/content.tk` script-stripping sanitiser passed review for months: it
was a privacy control that matched nothing.

Either support them or reject them at compile time. Silence is the worst of the three.

---

## T-10 — `http.post` is declared twice in `http.tki`

**Severity:** hazard; the arity error it produces is misleading.

```json
{"kind": "route", "name": "http.post", "params": ["str", "funcdecl"]},
{"kind": "func",  "name": "http.post", "params": ["httpclient", "str", "[byte]", "str"], "return": "httpresp!httperr"},
```

toke resolves the route, so **the function form is unreachable from user code** — no
argument list satisfies it — and the diagnostic reads `takes 2 arguments` for a
four-parameter function, which sends the reader to the wrong place. Confirmed by
migrating call sites to the correct four-parameter form and getting the same error.

`http.postheaders` and `http.postjson` are the workarounds and are what loke now uses
at all eight former `http.post` sites.

---

## T-11 — four stdlib modules are stubs, and nothing says so at the call site

**Severity:** correctness, and a claims hazard for anyone building on them.

`std.tls`, `std.mdns`, `std.infer` and `std.mlx` are present, callable, and
type-checked — and every function in them is a stub. From toke's own source:

| Module | Behaviour |
|---|---|
| `std.tls` | `tlsconfig`, `connecttls`, `listentls`, `genselfsigned` all `(void)` their arguments and `return 0`. There is no TLS |
| `std.mdns` | `advertise` returns 0 — its own comment reads *"no handle (not available)"*; `browse` returns an empty array |
| `std.infer` | `load` returns 0; `generate` returns the literal string `"[infer: not available]"` |
| `std.mlx` | `isavailable` returns 0 unconditionally, including on Apple Silicon, where the comment says availability depends on a framework that is not linked; `generate` returns `"[mlx: not available]"` |

This matters more than a missing feature would, for two reasons.

**A stub that returns a plausible value is worse than one that fails.**
`infer.generate` returning `"[infer: not available]"` as a *successful* result means a
caller treating that string as model output gets no error. In loke that path is a
privacy detector: a local NER model returning the sentinel would have read as "no
entities found" — a fail-open. loke now checks for the zero handle and reports the
layer as unavailable instead.

**`std.tls`'s signature change is not just an arity change.** `tlsconfig` now takes
`(cert, key)`. loke previously passed the peer certificate and a verify-peer flag as
well — that is the mutual-authentication half — and there is nowhere to put them in the
current signature. So "TLS 1.3 mutual auth" is not merely untested through this API; it
cannot be expressed. loke has reopened the four stories that claimed it.

A stub is a reasonable thing to ship. Suggested fix: make it visible — a
`capability`/`available()` predicate per module, a compile-time warning when a stub
function is called, or a distinguishable error result rather than `0` and a sentinel
string. Documenting the stub status in the `.md` beside each `.tki` would also help.

*Correction to our own earlier report:* loke previously told this project that these
four modules were **unreachable** because their `.tki` files declare identifiers
containing underscores, which toke rejects. That was wrong. The compiler has these
functions in its builtin table and resolves them regardless of the `.tki`; they are
reachable and they are stubs. We had concluded a hard ceiling of 209 of 217 modules on
that basis. The real figure is 217 of 217, which is what now builds.

---

## T-12 — four stdlib `.tki` files disagree with the compiler's builtin table

**Severity:** documentation, but it cost real time.

The `.tki` files under `stdlib/` are not the source of truth — the compiler's own
builtin registry is — and they disagree. Reading the `.tki` to find a signature gives
the wrong answer, and there is nothing in the file to say so.

| `.tki` says | The compiler actually has |
|---|---|
| `json.tki` lists 13 functions | 30+, including `getarr`, `getval`, `getobj`, `entries`, `parsearray`, `try*`, and the aliases `decode`/`encode`/`getstr`/`geti64` |
| `str.tki` has no `padright` | `str.padright(s, width, padchar)` exists |
| `process.tki` says `spawn(["str"])` | correct — but `spawndetached(cmd)` takes a single shell **command string**, a different shape, and is not in the `.tki` at all |
| `file.tki` has no `listglob` | `file.listglob(pattern)` exists, taking the whole pattern |

Two of these cost a wrong migration on our side before we read the C. Worse, several
names invite the wrong direction: `json.strarr` and `json.strarray` *encode* a string
array as JSON text — they are not getters — and loke had used them as getters at three
sites. A name like `json.encodestrarray` would not have been misread.

There is also a loke-specific stub in toke's own stdlib:
`json.getregulations(obj)`, documented in `json_glue.c` as *"loke-specific, stub
returning empty array"*. loke's `policy/loader.tk` builds every `$policyset` with
`regulations:json.getregulations(data;"regulations")` — so **every policy set loads with
zero regulations and the policy engine can never produce a violation.** We will remove
the dependency on our side; we mention it because a stub named after one consumer, in
another project's stdlib, is a trap for that consumer.

Suggested fix: generate the `.tki` files from the builtin table, or state in each that
the table wins.

---

## What we would ask for, in order

This list was written against T-1 to T-12 and is now reordered: five of those are fixed
in 445f519, and the fifteen found since include four that are more damaging than anything that remains.

1. **T-26** — change E2002's advice, and warn on a discarded comparison in statement
   position. This is first because it is the only item on the list whose *diagnostic* has
   created defects: 32 silent no-ops in this codebase are the compiler's own recommended
   fix, applied faithfully. Both halves are small and neither needs new analysis.
2. **T-18** — `mt` on an `X!$userErr` takes the first arm whatever the value is. Every
   error path in this codebase is dead code, 182 functions' worth, and we have had to
   write around it by returning sentinels instead of results. Nothing else on this list
   distorts a program's control flow.
3. **T-20** — an `f64` returned across a module boundary is corrupted. **We have found the
   mechanism and it looks like a one-line fix**: `llvm.c:1641` registers a literal `"i64"`
   return for every imported function, discarding the correct `"double"` that line 1629
   just computed, while the definition side emits a real `double` — and the bitcast the
   comment at 1639 promises is performed by neither side. Either half fixes it. Until it
   lands, no figure this project computes across a module boundary can be published.
4. **T-23 and T-24** — call sites not checked against a declared type where the ABI
   representation coincides. 99 latent segfaults here, and T-24's crash is
   *intermittent*, so a green test run is not evidence.
5. **T-2**, the label counter. 17 sites in one project, each needing IR archaeology.
6. **T-7** — the remaining silent one from the original set. The diagnostic already
   exists and simply is not reached.
7. **T-12 and T-22** — generate the stdlib `.tki` files from the builtin table, or check
   them against it in CI. Four disagreements found so far, each one a crash.
8. **T-11** — make stub status visible at the call site.
9. **A source location on codegen failures.** Even a "while compiling `f=x` at
   `file.tk:120`" prefix on E9003 would change these from a day of bisection into a
   minute of reading. This remains the single highest-leverage item in the document:
   T-23 took a day to find and five minutes to fix.

## Reproducing

Every program above is complete and was compiled with:

```
toke --out /tmp/probe /tmp/probe.tk
```

against toke `1bc4a44`. The loke-side sweeps that find each class in a real codebase
are in [`scripts/`](../../scripts/): `check_match_labels.py` (T-2),
`find_shadowed_lets.py` (T-6), `find_typename_values.py` (T-4),
`find_field_matches.py` (T-2, source-side), `find_missing_return_semi.py` (a loke bug
class, noted below).

## One that turned out to be ours

For completeness, since it looked like a toke bug and is not: `<` is both the return
operator and less-than, so

```toke
(log.info("…";"c";""))
<$ok(1)
```

with no semicolon parses as one comparison expression, and the function returns the
comparison rather than `$ok(1)`. toke is behaving as specified. It is only *reported*
when the left operand is a void call, and then it arrives as
`void type only allowed for function results` from clang. A warning on a discarded
comparison would catch it — the `discarded-value-result` rule already covers the
neighbouring case.

---

## T-18 — `mt` on a result with a user-declared error type always takes the first arm

*See **T-31** first: arms bind by position for every result type, and T-18 is the case
where the discriminant is not read at all.*

**Severity: correctness, silent, and it affects every error path in this codebase.**
If one item here gets attention, this is the one.

```toke
m=g;
t=$e{ $bad:str };
f=check():i64!$e{ <$err($bad("no")) };
f=main():i64{ <mt check() { $ok:v 5; $err:e 7 } };
```

Returns **5**. Swap the arms and it returns 7 — for the same `$err` value. The match
runs the first arm regardless of the tag, and binds the arm's payload from whatever is
there, so `$ok:v v` on an errored call yields garbage (we measured 96 for a function
that never returns a success).

**Correction, 2026-09-23: the line that used to sit here said "stdlib results are
unaffected". That is false, and see T-31.** A stdlib result does read its discriminant, but
it then uses it as an *index into the arm list*, so `ok` runs arm 0 and `err` runs arm 1
whatever the arms are labelled. Our original probe wrote `$ok` first, which is the single
arrangement where positional binding and label binding give the same answer — so the probe
could not distinguish them, and we generalised from it. Write the error arm first and a
stdlib match is inverted rather than merely half-dead.

What is specific to a **user-declared** error side is that the discriminant is not consulted
at all: arm 0 always runs. A two-variant error sum returning its second variant still takes
arm 0, so it is not the inner variant index being read either.

loke has **182 functions returning `X!$lokeerr`**. Every one of them has a dead error
path, and because `$ok` is written first by convention, every error was being read as a
success. It would have defeated the fail-closed privacy gate we were building at the
time: the refusal was returned as `$err` and both call sites matched `$ok` first, so
unscanned text would have been forwarded. We converted that gate to a plain bool.

There is no arm order that works, so the workaround is to avoid result types for
anything that matters and return an explicit struct or bool instead.

---

## T-19 — E4071 misses a trailing bare `mt` when the function returns a sum or a struct

```toke
f=pick(x:$s):i64{
  mt x { $a:v 7; $b:v 9 }        (* -> E4071, correctly refused *)
};

f=pick(x:$s):$d{
  mt x { $a:v $yes("y"); $b:v $no("n") }    (* -> compiles, returns garbage *)
};
```

The scalar case is caught. The sum or struct case compiles and the function returns
whatever was in the return slot, so the caller receives a value that is not of the
declared type and crashes when it matches on it.

**104 functions in loke were in that hole**, including `db.exec`, `db.query`,
`db.queryone`, every `sync_queue` operation, `dispatcher.dispatch` and
`governance.policy.evaluate`. Each computed the correct answer and discarded it. The
diagnostic already exists and is good — it just needs to fire for the other return
kinds.

---

## T-20 — an `f64` returned across a module boundary is corrupted

**Severity: correctness, silent, and it invalidates every published figure.**

```toke
(* shared/types.tk *)
f=f64abs(n:f64):f64{ if(n<0.0){ <0.0-n }el{ <n } };

(* another module *)
<t.f64abs(0.0-50.0) as i64      (* -> 1, not 50 *)
```

A second, independent case: a savings function computing `50.0` inside its own module
is received as `5` by a caller in another module. Within a single module the same
expression is correct, and f64 **parameters** cross intact — only returns are affected.

In loke this reaches **23 functions**, and the list is the worst possible one:
`computeprecision`, `computerecall`, `computef1` (the detection-recall figures),
`calccost` for both hosted providers (the cost figures), both `measuresavings`
implementations (the compression figures), and the three confidence mappers. So every
headline number this project could publish is wrong the moment it crosses a module
boundary, and nothing reports it.

### The mechanism, found 2026-09-23 against `c4e4704`

This is a one-line disagreement between two halves of the same ABI, and we think it is
cheap to fix.

The **definition** side maps `f64` correctly. `resolve_llvm_type` (`llvm.c:680`) returns
`"double"`, so `shared/src/types.tk` emits:

```llvm
define dso_local fastcc double @shared_types_f64abs(double %n.arg)
```

The **cross-module declaration** side does not. `llvm.c:1629` computes the correct
`"double"` via `tki_type_to_llvm`, and then `llvm.c:1641` **discards it** and registers
the signature with a literal `"i64"`:

```c
/* Cross-module ABI: all non-void returns use i64 (pointers via
 * ptrtoint, bools via zext, floats via bitcast). Only void stays void. */
FnSig *sig = register_fn(c, mangled_fn,
                          !strcmp(ret_type, "void") ? "void" : "i64");
```

so every importer emits:

```llvm
declare fastcc i64 @shared_types_f64abs(double)
```

The comment states the intent — a uniform i64 cross-module ABI with **floats via
bitcast** — and that design would be fine. But neither side performs the bitcast. The
callee returns a `double` in `xmm0`; the caller reads an `i64` from `rax`. The
**parameter** is `double` on both sides, which is exactly why f64 parameters cross intact
and only returns are affected.

Either half alone fixes it: emit the bitcast the comment promises, or use the `"double"`
that line 1629 already computed.

Two corrections to what we reported above, both from asserting this rather than eyeballing
it:

- **The corrupted value is not `1`, and is not consistent.** `f64abs(-50.0)` arrives as the
  bit pattern 1 (4.94e-324, which is why it prints as `4.940`); `f64abs(50.0)` and
  `f64abs(-1.5)` both arrive as `0`. It is whatever was in the integer return register,
  so "arrives as 1" was one observation of undefined behaviour.
- **Stdlib builtins are exempt, and correctly so.** A `tk_*_w` wrapper really does return
  the f64 bit pattern in an `i64` and really is bitcast back — both halves of *that* ABI
  agree, by way of `tki_type_to_llvm_abi` (`llvm.c:1115`). So `json.getfloat` and friends
  are fine. Only toke-to-toke module calls are affected. We had wrongly suspected 15
  `json.getfloat` sites; they are exonerated.

This narrowed the blast radius a long way. Across loke's built tree there turned out to be
exactly **one** live corrupting call site rather than 23 — `shared.types.f64abs` from
`eval/compare.tk:56`, which was reporting a score delta and a cost delta that were neither
of them the measured value. The other 22 f64-returning functions are called only within
their own module, or have no caller at all because their consumers are unwired; they become
live the moment those consumers land.

We are converting the affected functions to return scaled integers — hundredths of a
percent — because an integer crosses correctly and is exact, and that workaround is now
asserted too (`f64hundredths`, arm D). Where a caller only wants the value for display we
return a `str` instead, which crosses safely — `f64absfixed` does the abs and the
formatting in one call so the f64 never leaves its own module.

**A boundary the defect does NOT cross, measured 2026-09-23.** An `f64` **field of a
struct** returned across a module boundary is **intact**. We checked because
`core.metrics.collector.summarise` returns a struct with four f64 fields that a user-facing
command prints, and nobody had established whether those were corrupted too. They are not,
and the reason fits the diagnosis exactly: a struct crosses as a **pointer**, so the field
is loaded from memory on the far side rather than read out of a return register. The bug is
specific to the register, which is why the parameter direction is also unaffected. So the
blast radius is bare `f64` returns only — worth knowing before anyone migrates a struct that
did not need it.

**The assertion, if you want it as a regression test.** `tests/unit/shared/test_f64_boundary.tk`
in loke, four arms: a module-local control, the loke-boundary case, the stdlib-builtin case,
and the integer workaround. Arm B is written as a tripwire that asserts the defect is still
present, so it fails on the day you fix this.

---

## T-21 — a string returned by `std.homedir()` is truncated when interpolated

**Severity: correctness, silent, and it only affects one stdlib call's return value.**

```toke
i=std:std;
i=str:std.str;
f=main():i64{
  let a=str.len("\(std.homedir())/x");        (* -> 12 *)
  let b=str.len(str.concat(std.homedir();"/x"));  (* -> 21, correct *)
  <a
};
```

Interpolating a local or a parameter is fine; it is specifically the value this call
returns. Every path built the interpolated way pointed at a directory that does not
exist, so `db.open` failed on it — which is how four of our tests came to open a
database in a directory that was never there. We now use `str.concat` for this one call
and interpolation everywhere else, which is an unsatisfying rule to have to remember.

---

## T-22 — `row.f64` is declared as a result but does not return one

**Severity: correctness, crashes. Same family as T-12.**

`stdlib/db.tki` declares `row.f64` as returning `f64!DbErr`. `tk_row_f64_w` returns a
plain `i64` carrying the f64 bit pattern, and `0` on error — with no tag. So matching
the "result" reads a tag that was never written, and it crashed for us.

This is the fourth `.tki`-disagrees-with-implementation case we have hit (T-12 covers
the other three), which is why the ask in T-12 — generate the `.tki` files from the
builtin table, or check them against it in CI — matters more than any individual fix.

We work around it by reading the column as TEXT and parsing it, which also sidesteps
T-20.

---

## T-23 — arguments of different declared types but the same ABI are accepted reversed

**Severity: correctness, silent, segfaults at run time. This one cost us a whole day.**

`str.join` is declared `(str, [str]) -> str`. Passing them the other way round compiles
with no diagnostic and segfaults when the call is reached:

```toke
i=str:std.str;
f=main():i64{
  let a=@("x";"yy";"zzz");
  <str.len(str.join(a;"|"))      (* SIGSEGV; str.join("|";a) -> 8 *)
};
```

`str` and `[str]` are both an i64 handle at the ABI, so nothing in the type checker
separates them at the call site. Every one of the **70 `str.join` call sites in loke,
across 40 files**, was written the wrong way round, and each was a latent segfault that
only fired when that line was actually executed. We found it by bisecting a crashing
audit-log write, not by any diagnostic.

The reason all 70 were wrong is worth saying too: **the stdlib is not consistent with
itself.** `fmt.strs([str], str)` and `fmt.arr([i64], str)` take the array first;
`str.join(str, [str])` takes it second. A reader has no way to guess, and the compiler
does not correct the guess.

Two asks, either of which would have prevented this:

1. Check declared types at the call site even where the ABI representation coincides —
   `str` is not `[str]`, and the `.tki` already says so.
2. Make the stdlib's own argument order consistent, or at least make `str.join` agree
   with `fmt.strs`.

### The general form, which is worth fixing once rather than per-function

T-23 and T-24 are two symptoms of one thing, and we have since hit a third. Any `.tki`
signature typed in terms of `i64` — whether written that way or marked `"gen": "abi"` —
**disables call-site checking for every argument**, because at the ABI a string, an array,
a struct handle, a row handle and a JSON handle are all an `i64`.

Three defects in loke, all of which compiled clean:

| what was passed | to a parameter declared | result |
|---|---|---|
| `[str]` and `str`, reversed | `str.join(str, [str])` | segfault (T-23) |
| an array plus an element | `@(…)` literal | heterogeneous array, intermittent segfault (T-24) |
| a database row | `json.enc(str)` | garbage JSON in a subject-access export |
| a parsed JSON object | `db.rowstr(i64, i64)` — `gen:"abi"` | every field read back empty |

The last two are mirror images of each other and neither is detectable from the source,
because both sides of the confusion are `i64`. We found **78 sites** in one sweep where a
`$row` was read with a `json.*` accessor and silently returned empty strings and zeros —
including one that made every float setting in the project read as `0.0`.

So the ask is narrower than "check more things": **`gen: "abi"` should describe the
lowering, not erase the type.** Keep the declared toke types in the `.tki` for checking and
apply the uniform `i64` ABI only when emitting the call. `std.db`'s `row.str` already
declares `(Row, str) -> str!DbErr` correctly in one place and `(i64, i64) -> i64` in
another; the correct one exists and is not the one the call site is checked against.

This is the same class as T-4, T-7 and T-22: something the interface file already
knows,
which the call site is not checked against.

---

## T-24 — `@(array; element)` nests silently where an append was meant

**Severity: correctness, silent, intermittent segfault.**

```toke
t=$entry{ scope:str; target:str };
t=$state{ items:@$entry };

f=add(st:$state;e:$entry):$state{
  <$state{ items:@(st.items;e) }    (* [[...], e] — length 2, whatever st.items held *)
};
```

`@(a;b)` is a two-element array literal, so where `a` is itself an array the result is a
**heterogeneous** array holding an array and an element. Reading element 0 back as the
element type dereferences an array handle as a struct. In our case
`tests/unit/governance/test_kill_switch.tk` crashed in **19 runs out of 20** — the
surviving run is what makes this so unpleasant, because a green CI proves nothing.

`@$entry` is a declared element type, and `@(st.items;e)` mixes `@$entry` with `$entry`.
A homogeneity check on array literals whose element type is known would catch this
outright.

We found **29 live sites** in loke this way, including the privacy filter registry, the
enabled-privacy-layer list, the local NER entity list, the provider registry, the
pipeline hook registry and the OpenAI system-prompt prepend. Each silently held at most
one element or nested on the first append. `.push()` is the correct append and now
appears at all 29.

---

## T-25 — `max_funcs` counts imported signatures, and E9010 does not say it is a setting

**Severity: blocks the build, and reads as a compiler bug rather than as configuration.**

A module compiled fine one hour and not the next, with:

```
E9010 compiler limit exceeded: too many functions
```

No line number, no file position beyond the first line, no statement of what the limit is,
and no hint that it is configurable. We went looking in the compiler source, which is not
where a project should have to look for this.

Three things would each have saved the trip:

1. **Say the number and the key.** `"compiler limit exceeded: 129 functions, max_funcs is
   128 — raise it in tkc.toml or with --max-funcs"`. Everything in that sentence is already
   in scope at `register_fn` (`llvm.c:699`), except the count, which is `c->fn_count`.
2. **Say that it counts imports.** The signature table holds every function the module can
   *see*, not the ones it declares. The module that hit it,
   `packages/core/memory/mcp_server.tk`, declares 25 functions and has eleven imports —
   while `shared/src/types.tk` declares 35 and compiles. From the message alone the natural
   conclusion is "this file is too big", which is wrong and leads to a pointless refactor.
3. **Name the section.** `max_funcs` is a top-level key: `src/config.c` treats the
   section-less part of `tkc.toml` as the limits block, so a limit written under
   `[capabilities]` is rejected as *"capability 'max_funcs' wants true/false or a quoted
   path"*. That diagnostic is good — it just arrives after you have guessed wrong, and
   nothing says where limits go.

The default is 128 (`TKC_MAX_FUNCS`, `src/tkc_limits.h:83`). loke crossed it by exactly one
function, bisected with `--max-funcs`, and the fix was one line of `tkc.toml`. That is a
perfectly reasonable design — we are not asking for a bigger default. We are asking for the
diagnostic to be the thing that tells us, because this is the same shape as the ask at the
bottom of this document: **the compiler knew the answer and printed something else.**

---

## T-26 — there is no assignment to a struct field or array element, and the diagnostic for it recommends the bug

**Severity: blocks, and its `fix` field actively creates a silent defect. This is the single
most expensive item we have reported.**

```toke
t=$r{a:i64;b:i64};
f=main():i64{
  let x=mut.$r{a:1;b:2};
  x.a=9;          (* E2002: "`=` is assignment; use `==` for equality" *)
  <x.a
};
```

There is no form of `x.a = v` in the language — not through a parameter, not on a local
`mut` struct, not on an array element. That is a defensible design for a value-semantics
language and we are not asking for it to change.

**What we are asking for is the diagnostic.** `E2002` says *"`=` is assignment; use `==` for
equality"*, and following that advice turns a parse error into a **discarded comparison
that compiles clean and does nothing**. `x.a==9;` in statement position is legal, has no
effect, and emits no warning.

That is not hypothetical. It is the origin of the worst defect class in this codebase:

- **13 accumulations that silently did nothing** (our story LS1.1a), each of them an
  `x.field==value;` where an assignment was meant. Two examples that survived months of
  review: a k-means centroid update, and a governance trace that recorded nothing while
  reporting success.
- **19 more sites found this week** in a tree being migrated, all the same shape. We only
  did not convert them because we had already learned the lesson — a sweep that trusted
  the compiler's advice would have converted 19 parse errors into 19 silent no-ops. Eleven
  of them are functions whose entire body is field assignments, so they are no-ops today
  and would have stayed no-ops, quietly, forever.

Three asks, in order of value:

1. **Change the advice.** When the left-hand side of `=` is a field access or an index, the
   message should say that the language has no such assignment and name the alternative —
   reconstruct the struct, or return the new value — rather than suggesting `==`.
2. **Warn on a discarded comparison in statement position.** `x==y;` as a statement has no
   effect and is a bug in every case we have seen. The linter has
   `discarded-value-result` for calls; this is the same rule for operators. It would have
   caught all 32 sites above with no new analysis.
3. Consider allowing field assignment on a local `mut` struct, which is what people
   reach for and is sound under value semantics.

---

## T-27 — comments nest, so `(*` inside a comment silently deletes the rest of the file

**Severity: silent code deletion, no diagnostic of any kind.**

```toke
m=q;
(* reads COUNT(*) from the table *)
f=survived():i64{ <1 };
```

The `(*` inside `COUNT(*)` opens a **nested** comment. The single `*)` closes the inner one,
the outer stays open, and `f=survived` is consumed as comment text. The compiler exits 0,
emits IR, and the function is simply **not in it**. We verified it by checking the emitted
`.ll` rather than the exit status, which is the only way to see it:

| comment | function in the IR? |
|---|---|
| `(* plain *)` | yes |
| `(* reads COUNT(*) from the table *)` | **no** |
| `(* outer (* inner *)` | **no** |
| `(* outer (* inner *) *)` | yes |

Two things make this worse than an ordinary lexer quirk. First, there is no diagnostic —
not a warning, not an unclosed-delimiter error at EOF — so the only symptom is a function
that has vanished, which surfaces much later as an undefined symbol at link time, or not at
all if nothing calls it. Second, `COUNT(*)` is not an exotic thing to write in a comment in
a database-backed project; it is the single most common SQL fragment there is, and our house
style asks for comments explaining what a query does.

We scanned our tree and nothing is currently swallowed, so we were lucky rather than
careful. One of our own workers hit it this week while writing a new comment.

Either treatment would be fine, and we have no preference:

- Do not nest — first `*)` closes, which is what OCaml-style syntax leads people to expect
  least but is simplest; or
- Keep nesting and **emit an error at EOF** when depth is greater than zero. `E2004
  unclosed delimiter` already exists and would be exactly right here.

The current combination — nesting plus silence — is the one that loses code.

---

## T-28 — `str.isdigit` segfaults on a character code, which is the only thing you have to give it

**Severity: silent segfault. A fourth instance of T-23's root cause, and this one is a
closed loop inside one module's own API.**

```toke
i=str:std.str;
f=main():i64{
  let c=str.charat("a5b";1);        (* -> 53, the byte value of '5' *)
  if(str.isdigit(c)){ <1 }el{ <0 }  (* SIGSEGV *)
};
```

`str.isdigit("5")` works and returns 1. Passing a character code crashes. The two
declarations explain why, and they are in the same `.tki`:

```json
{"name": "str.charat",  "params": ["str", "i64"], "return": "i64", "note": "byte value at index i"}
{"name": "str.isdigit", "params": ["i64"],        "return": "i64", "gen": "abi"}
```

`charat` returns a byte value as `i64`. `isdigit` declares its parameter `i64` because
`gen: "abi"` erases it — the real expectation is a `str` handle. So the ONE function that
produces a character and the ONE function that classifies one cannot be composed, the type
checker cannot see it because both sides are `i64`, and the failure is a segfault rather
than a diagnostic.

We worked around it by comparing against 48 and 57 directly, which is fine but means the
predicate has no callable form for the case it exists to serve.

This is the same mechanism as T-23, T-24 and the `json.enc(row)` / `db.rowstr(json)` pair —
**four defects from one property** — and it is the clearest argument for the ask in T-23:
`gen: "abi"` should describe the lowering and keep the declared toke type for checking. Here
the correct type is knowable, is not written down, and its absence turns a two-function
composition into a crash.

If `isdigit` is genuinely meant to take a character code, the fix is smaller still: declare
it `(u8) -> bool` or document the unit. Either way the current pair cannot both be right.

---

## T-29 — control-flow keywords are reserved as import aliases, and the diagnostic does not say so

**Severity: minor, but it costs a confusing five minutes every time.**

```toke
i=sc:std.str;      (* E2002: "expected import alias, got 'sc'" *)
```

Measured by probing: **`sc`, `mt`, `lp`, `el`, `br` and `if` are all rejected** as import
aliases. That is entirely reasonable — they are keywords — but the message says only
*"expected import alias"*, so the first reading is that the alias syntax is wrong rather than
that this particular word is taken. We spent a few minutes checking the module path and the
`i=` form before trying a different letter.

`sc` is the one that actually bites, because it is the natural two-letter abbreviation for a
great many module names (`scorecard`, `schema`, `scanner`, `scope`) and is not obviously a
keyword to a reader — it appears to be the structured-concurrency marker, judging by
`sc_scope` in `llvm.c`.

The ask is one word in the message: *"'sc' is a reserved keyword; choose another alias"*. The
compiler already knows which token it rejected.

Same family as T-25 and T-26: the information needed to act is in the compiler's hand at the
moment it emits the diagnostic, and is not in the diagnostic.

---

## T-30 — `std.db` has exactly one global connection, so a program cannot use two databases

**Severity: correctness, silent, and it makes a two-database program impossible to write
without knowing this.**

`src/stdlib/db.c`:

```c
static sqlite3 *g_db = NULL;                      /* :10 */
...
if (sqlite3_open(dsn, &g_db) != SQLITE_OK) { ... } /* :20 — overwrites, does not close */
...
static sqlite3 *conn_db(int conn_id)               /* :199 */
{
    if (conn_id == 0) return g_db;
    return NULL;
}
```

`db.open` returns a `u64!DbErr`, which reads like a handle — but `conn_db` resolves **only
conn_id 0**, to the single global. So the returned value cannot select a connection, every
subsequent `db.one`/`db.many`/`db.exec` goes to whichever database was opened **last**, and
opening a second one silently replaces the first without closing it.

This is not hypothetical for us. loke opens two files in one process:

- `core.storage.db.openstore(datadir)` → `datadir/loke.db` (audit trail, settings, sessions)
- `core.memory.palace.openpalace(datadir)` → `datadir/memory.db` (drawers, closets, index)

Whichever ran last receives every query from both subsystems. `audit_log` does not exist in
`memory.db` and `memory_drawers` does not exist in `loke.db`, so the loser's queries fail —
**silently**, because a failed read is mapped to `0` or `""` by the row accessors (see the
related defect below). We found it only because a test that had never imported the real module
was de-stubbed and started asserting that the memory tables exist.

Three asks, in descending order of value:

1. **Make `conn_db` honour the handle**, so `db.open`'s return value means what its type says.
   A small table of open connections indexed by the returned id would do it, and the signature
   already accommodates it.
2. **If one connection is the intended design, say so in the type.** `db.open` returning
   `u64` invites exactly this mistake; `void!DbErr` plus a `db.use(path)` would not. The
   current signature documents a capability that does not exist.
3. **Close the previous connection on re-open**, or refuse the second open. Overwriting the
   pointer leaks the handle and its file lock.

**Related, and worth fixing together: a stdlib result cannot carry a legitimate zero.** We hit
this on `db.one("PRAGMA secure_delete")`, which returns 0 when the pragma is off — and `mt
row.i64` takes that to `$err`. loke's own `rowi64`/`rowi32` wrappers then map the error side
back to `0`, so **every integer column read in this codebase conflates "the value is 0" with
"the read failed"**, including `tokens_in`, `tokens_out` and `duration_ms` in the audit trail.
The same shape as T-22: a result whose error side is indistinguishable from a valid value.

---

## T-31 — `mt` binds a result's arms by POSITION, not by label

**Severity: correctness, silent, and it inverts every outcome of an affected match.**
This is the general form of T-18, and it is worse than T-18 because the failure is not
"the error path is dead" but "success and failure are swapped".

One `mt` construct behaves three different ways depending on what it is matching. Measured
at `0b0bc4e`, each row a separate program, the exit status being the arm body that ran:

```toke
(* 1. A PLAIN SUM — correct. Reordering the arms changes nothing. *)
t=$s{ $a:i64; $b:i64; $c:i64 };
f=pick():$s{ <$c(0) };
mt pick() { $a:v 1; $b:v 2; $c:v 3 }     (* -> 3, correct *)
mt pick() { $c:v 3; $b:v 2; $a:v 1 }     (* -> 3, correct: by LABEL *)

(* 2. A STDLIB RESULT — the discriminant is read, then used as an INDEX. *)
mt json.dec("{\"a\":1}") { $ok:o 1; $jsonerr:e 2 }   (* -> 1  ok  *)
mt json.dec("{\"a\":1}") { $jsonerr:e 2; $ok:o 1 }   (* -> 2  THE ERROR BODY, on valid input *)
mt json.dec("{{{nope")   { $ok:o 1; $jsonerr:e 2 }   (* -> 2  err *)
mt json.dec("{{{nope")   { $jsonerr:e 2; $ok:o 1 }   (* -> 1  THE OK BODY, on invalid input *)

(* 3. A RESULT WITH A USER-DECLARED ERROR TYPE — the discriminant is not read at all. *)
t=$e{ $one:str; $two:str };
f=check():i64!$e{ <$err($two("no")) };
mt check() { $ok:v 1; $err:e 2 }         (* -> 1, arm[0], see T-18 *)
```

So for a stdlib result, `ok` selects arm **0** and `err` selects arm **1** by position, and
the arm's own label is never checked against the tag it is bound to. Write the error arm
first — which reads naturally, and which a guard-clause style encourages — and **every
outcome of the match is exactly backwards**: valid input runs the error handler, invalid
input runs the success handler and binds the error payload as if it were the parsed value.

Case 3 is the same bug with the discriminant missing entirely, so `arm[0]` always wins. We
had filed that separately as T-18, whose text says *"Stdlib results are unaffected"* — that
sentence is wrong, and it was wrong because our probe happened to write `$ok` first, which
is the one arrangement under which positional binding and label binding agree.

**What it cost us.** 53 sites in 20 modules. The ones that had visible consequences:

| module | effect |
|---|---|
| `mcp-toke/src/tools.tk`, `core/mcp/client.tk` | 16 sites. Every well-formed MCP request answered "Parse error"; `start()` logged "failed to listen" without accepting a connection. **The whole MCP server was unreachable**, with no diagnostic anywhere |
| `core/privacy/presidio.tk` | `isavailable` matched `$err` first, so a *healthy* Presidio reported unavailable — the PII detection layer never ran |
| `core/optimiser/llmlingua.tk` | the mirror image: `isavailable` returned TRUE for an **absent** sidecar. A fail-open on a privacy-adjacent layer, and no prompt had ever been compressed |
| `core/mcp/discovery.tk` | server name and tool count silently defaulted for every server that answered |

The `presidio` and `llmlingua` pair is the reason this is not merely a bug report. The same
misuse of the same construct produced a fail-closed in one module and a **fail-open** in the
other, and neither module's tests could see it, because the arms type-check either way.

**Ask.** Bind arms by label and reject an arm whose label is not a variant of the matched
type. If positional binding is deliberate, E-code an arm list whose labels are not in
declaration order, because there is no way to read the current behaviour off the source.

**Our workaround**, which we would rather not keep: `scripts/find_err_arm_first.py` in the
gate, failing any `mt` over a result whose `$ok` arm is not written first, and
`scripts/fix_err_arm_first.py` to reorder them. It is a lint rule standing in for a type
rule, and it cannot see a match built by a macro or spread across a helper.

## T-32 — `std.json` cannot read a nested value

**Severity: capability gap, and every workaround for it fails differently.**

`std.json`'s typed API is eight functions — `enc`, `dec`, `str`, `u64`, `i64`, `f64`, `bool`,
`arr` — and every accessor among them takes a `Json` plus a **flat** key. There is no
`json.obj(Json, str) -> Json!JsonErr`, so a value one level down is unreachable. Measured at
`0b0bc4e` against `{"model":"abc","usage":{"input_tokens":150}}`:

```toke
json.str(o;"usage")                    (* -> $jsonerr: usage is an object, not a str *)
json.i64(o;"usage.input_tokens")       (* -> $jsonerr: dotted paths are not supported *)
json.getval(o;"usage")  then json.i64  (* -> SIGSEGV *)
str.matchbracket(rest)                 (* -> $bracketerr *)
```

The third one is the one to look at. `json.getval` is one of roughly fifty names in
`std.json`'s interface declared `(i64, i64) -> i64` — `getobj`, `getstr`, `getint`, `has`,
`keys`, `entries`, `values`, `tryint`, and so on. They operate on a different representation,
reached through `json.parse`, which is **T-17**: a name that links to an unrelated runtime
symbol. Handing one of them the typed `Json` compiles and links, because a one-field struct
and a handle share an ABI (**T-23**), and then dereferences whatever the struct's first word
happens to be. So the API surface a user reads offers about sixty functions of which eight
are usable, and picking a wrong one is a segfault rather than a diagnostic.

**What it cost us.** Both hosted providers. `core.providers.anthropic` and
`core.providers.openai` read token usage as `json.str(obj;"usage")` followed by `json.dec` on
the result — so the decode always errored and both counts fell to their `0` default. Every
audit row for a hosted request carried `tokens_in = 0`, `tokens_out = 0` and `cost_usd = 0`,
and `audit_log` is append-only and hash-chained over exactly those columns, so the zeros are
permanent once written and the chain attests to them. OpenAI additionally returned **empty
content for every completion**, because `choices[0].message.content` is one level deeper than
Anthropic's `content[0].text` and `message` is an object.

**Our workaround**, in `packages/shared/src/jsonobj.tk`, rests on two things that do work:
`Json` is declared `{ raw:str }` and `o.raw` holds the whole document; and `$json{raw:"…"}`
can be constructed in user code and read correctly by the typed accessors. So we find
`"key":` in the raw text, brace-match the object that follows — tracking string state and
backslash escapes, because `{"note":"a } brace"}` is real data — and re-wrap the substring.
`json.arr` is typed and genuinely works, so array elements come back as real `Json` values and
that part needs no trick.

It is a text scan standing in for an object model. It cannot handle duplicate keys at
different depths, and it is O(n) per lookup over the whole document.

**Ask.** `json.obj(Json, str) -> Json!JsonErr`. One function closes this. Failing that,
support a dotted path in the existing accessors. And separately: either fix or remove the
fifty untyped `(i64, i64) -> i64` names, because at present the interface advertises them
alongside the eight that work.

---

## T-33 — every numeric and boolean `std.json` accessor reports an error for a falsy value

**Severity: correctness, silent, and it makes "zero" and "absent" the same answer.**

Measured at `0b0bc4e`, each accessor against a document where the field is present:

| expression | result |
|---|---|
| `json.i64(o;"n")` where `n` is `0` | **`$jsonerr`** |
| `json.u64(o;"n")` where `n` is `0` | **`$jsonerr`** |
| `json.f64(o;"f")` where `f` is `0.0` | **`$jsonerr`** |
| `json.bool(o;"b")` where `b` is `false` | **`$jsonerr`** |
| `json.str(o;"s")` where `s` is `""` | `$ok ""` |
| `json.i64(o;"n")` where `n` is `5` | `$ok 5` |
| `json.f64(o;"f")` where `f` is `1.5` | `$ok 1.5` |
| `json.bool(o;"b")` where `b` is `true` | `$ok true` |

`json.str` is the only survivor, and it survives because an empty string is still a non-null
pointer. So a JSON `0` cannot be distinguished from a missing key, a `false` cannot be
distinguished from a missing key, and every `$err`/`$jsonerr` arm in a program is doing double
duty as "the value was falsy".

**This is almost certainly the same defect as T-31, seen from the other side.** The
measurements are consistent with `X!E` being a **single machine word carrying the value, with
zero standing for the error and no tag at all**. That one sentence predicts everything we have
filed separately:

- a falsy payload reads as an error — this issue;
- `ok` selects arm 0 and `err` selects arm 1 **by position**, because the only test available
  is "is the word zero" — **T-31**;
- a result whose error side is a user-declared sum always takes arm 0, because the success
  payload is a non-null pointer and so is the error payload — **T-18**;
- `json.dec` on malformed input correctly takes the error arm, because it returns NULL;
- bare `json.str(o;"model")` used directly as a `str`, with no match at all, *works* — which
  should be impossible if a result had a tag, and which a great deal of code in the wild is
  presumably relying on without knowing it.

We have not read the compiler, so that mechanism is inference from eleven measurements rather
than a claim about the implementation. But if it is right, T-18, T-31 and T-33 are one fix,
and it is the most valuable fix available in the language.

**Our workaround** is to ask the document text whether the field is present and falsy:
`shared.jsonobj.fieldiszero` locates `"field":` and checks whether the value's first character
is `0` — exact rather than heuristic, because JSON forbids leading zeros in numbers, so a value
beginning with `0` can only be `0`, `0.0` or the like. A field that is present, not falsy, and
still errored is treated as a genuine type mismatch and gets the caller's fallback.

That works for numbers. There is no equivalent trick for `false`, which is why nothing in this
codebase now reads a boolean out of JSON.

## T-34 — a three-segment stdlib member is lowered as a call to a bare unqualified global

**Severity: correctness AND availability, silent, and one case terminates the process.**

`http.res.json`, `http.res.ok`, `http.res.bad` and `http.res.err` type-check, and none of them
reaches `std.http`. The dotted name is lowered as a call to a global named by the LAST segment
only:

```toke
m=t; i=http:std.http; i=io:std.io;
f=main():i64{ let b=http.res.json(200;"{}"); io.println("built"); <0 };
```

→ `Undefined symbols: "_json", referenced from: _tk_main`. `http.res.ok` wants `_ok`,
`http.res.bad` wants `_bad`. Those three fail at link, which is at least loud.

**`http.res.err` links — to libc's `err(3)`.** So it type-checks, links, runs, and then:

```
$ ./t13
t13: nope: Operation not permitted
$ echo $?
144
```

`err(3)` prints to stderr and **exits the process**. 144 is `400 & 0xff` — the status code we
passed as `err`'s exit code. Every 4xx response built this way would have terminated the server
process, and nothing in the toolchain says so at any stage.

This is the same lowering defect T-7 records the *outcome* of. The mechanism is worth stating
because it is shared with the receiver-dropping bug below: **a `.member()` call emits a
declaration and call for the trailing identifier and discards everything to its left.**
`a.pushcopy("y")` emits `declare i64 @pushcopy(i64)` and passes the ARGUMENT but not the
receiver; `let b=a.clone();` emits `declare i64 @clone()` with no arguments at all. When libc
happens to export the name, it is called with the wrong arguments. When it does not, the link
fails.

`http.res(status;body)` — two segments — links and runs correctly, and is what the migrated
`packages/browser` tree uses throughout. It is declared nowhere in `http.tki`.

**Ask.** Reject a member path that resolves to no declared export, rather than emitting a call
to its last segment. A diagnostic naming `http.res.json` would have cost us nothing; the
silent one cost a demo application's entire API surface.

---

## T-35 — emitted IR is silently truncated, and toke reports success

**Severity: availability, silent, and the toolchain's own exit status says the build worked.**

A module whose string constants exceed a limit emits IR that is cut off mid-token. `toke` exits
**0**; only `clang` notices, and it reports a type mismatch or a parse error rather than a
truncation, so the error points somewhere misleading.

Two boundaries, both measured at `fedd48d`. They do not look like the same limit.

**1. A ~64 KiB cap on emitted string-constant data.**

| input | IR emitted | result |
|---|---|---|
| ONE string of 4,000 chars | 4,779 bytes | assembles |
| ONE string of 300,000 chars | **66,257 bytes** | truncated |
| 200 strings of 2,006 chars | 107,643 bytes, **32 of 200 declarations**, 64,480 declared string bytes | truncated |

32 declarations totalling 64,480 bytes, and a 300,000-character string surviving as ~64 KiB of
IR, both land just under **65,536**. That looks like a fixed 64 KiB buffer.

**2. Separately, 670 short string constants truncate the LAST declaration; 669 do not.**

```
669 strings of 38 chars -> 203,997 bytes of IR, assembles
670 strings of 38 chars -> 204,289 bytes of IR, TRUNCATED
```

The cut is in the final declaration, and clang reports the declared length no longer matching
the content:

```
@.str.g_669 = private unnamed_addr constant [38 x i8] c"value-00669-padding-to-make
  error: constant expression type mismatch: got type '[56 x i8]' but expected '[38 x i8]'
```

Total string data there is only ~25 KB, so this is not the 64 KiB boundary. Reproduction:

```toke
m=g; i=str:std.str;
f=blob():@str{ <@("value-00000-padding-to-make-it-longer"; ... 670 of them ...) };
```

**What it cost us.** Four `packages/moke/data/*.tk` modules — 737 to 757 string constants each,
because they hold demo datasets as literal arrays — emit IR that cannot be assembled. The cut
point varies with the module (`priv`, `private unnamed_ad`, `private unnamed_addr consta`), which
is consistent with a buffer whose remaining capacity differs. All four compile without a single
diagnostic and all four fail at `clang -c -x ir`. Five more modules fail the same step for the
unrelated type reasons listed under T-3.

We only found it because `scripts/lib/build_tree.sh` assembles IR to objects as an explicit step
and counts the failures. A build that goes straight from toke to a link would see "Undefined
symbols" for every function in the affected module and no indication why.

**Ask.** Whatever the buffer is, grow it or stream it — and **fail non-zero when the emitted IR
is incomplete**. The silence is worse than the limit: a compiler that reports success having
written a truncated artefact cannot be trusted by any build system.

## T-36 — `str.tki`'s `gen:"abi"` block declares ~90 members as `(i64,…) -> i64`, disabling argument type checking for all of them

**Severity: correctness, silent, and it is the reason most of the other defects here were
invisible.**

`stdlib/str.tki` declares 116 functions. **39 are typed.** The rest sit in a `gen:"abi"` block as
`(i64, …) -> i64`, and because `i64` accepts a `str`, an array, a struct handle and a character
code indifferently, every call to one of them type-checks whatever is passed.

This is not T-12, which is the `.tki` disagreeing with the builtin table. Here the `.tki` itself
defeats the checker.

Measured: of **17 bogus `std.str` calls** in one module (`packages/moke/src/compute.tk`), only
**5** names raised `E4027`. The other 12 type-checked in silence. What those silences were:

| call | what it actually is |
|---|---|
| `str.len(<array>)` | `strlen()` on a `char *`. Over an array of heap pointers it stops at the first zero byte and returns about **3**. It was every loop bound in five modules |
| `str.compare(a;b)` | `tk_str_eq_w(a,b) ? 0 : 1` (`str_glue.c:524`) — declared like a three-way comparator, implemented as INEQUALITY, **never negative**. So `str.compare(x;y) > 0` is true whenever the strings merely differ. It was a sort key |
| `str.padleft(s;width;pad)` | `char ch = (char)(pad ? pad : ' ')` — the pad is a character CODE, and every call site passed a string, so the pad character was the low byte of a heap address |
| `str.tof32(x)` | an alias for `tk_str_tofloat_w`: it PARSES A STRING, and was handed an `i64` row count to dereference |
| `str.fromf32(x)` | an alias for `tk_str_fromfloat_w`: reads its argument as f64 bits, and was handed an f32 |

The `str.len`-on-an-array case is the one to fix first. It is a one-character difference from
correct code (`arr.len` versus `str.len(arr)`), it returns a plausible small number rather than
crashing, and it silently truncates every loop written against it.

**Ask.** Type the `gen:"abi"` block, or mark those names as unchecked so a diagnostic can say
so. A stdlib of 116 functions where 77 accept anything, and where six of those are aliases for
a differently-typed function, cannot be used safely from source.

**A correction to an assumption we carried for a while, in case it saves someone the same
trip.** `arr.len()` is **not** a defect: `arr.len()` and `arr.len` emit the identical
`getelementptr i64, i64* %p, i32 -1`, and the compiler labels it `; .len()`. Only
`str.len(<array>)` is wrong.

## T-37 — a declared `@f64` gets the SCALAR f64 conversion applied to its array handle

**Severity: availability, and it emits IR that cannot be assembled.** Nine `packages/moke`
modules fail `clang -c -x ir`; five of them fail for this.

Wherever a value's declared type is `@f64`, toke converts it as though it were `f64`. Minimal
reproduction, three functions of identical shape:

```toke
m=g;
f=retf64arr(a:@f64;v:f64):@f64{ <a.push(v) };   (* BROKEN *)
f=retstrarr(a:@str;v:str):@str{ <a.push(v) };   (* fine   *)
f=reti64arr(a:@i64;v:i64):@i64{ <a.push(v) };   (* fine   *)
```

The `@f64` one emits:

```llvm
%t4 = call i64 @tk_array_append_w(i64 %t1, i64 %t3)
%t5 = fptosi double %t4 to i64        ; <- the ARRAY HANDLE, converted as a double
ret i64 %t5
```

→ `error: '%t4' defined with type 'i64' but expected 'double'`.

`@str` and `@i64` emit `ptrtoint` and are correct. It is specific to `@f64`.

**It is not only the return position.** A struct FIELD declared `@f64` does the same:

```toke
t=$f64vec{ v:@f64 };
f=wrapped(a:$f64vec;x:f64):$f64vec{ <$f64vec{ v:a.v.push(x) } };
```

→ `%t10 = bitcast double %t9 to i64` where `%t9` is the array handle. So wrapping the array in a
struct is **not** a workaround.

`@(@f64)` — an array of f64 arrays — IS correct, which is the shape that makes the bug look
intermittent: in `moke/src/ml/engine.tk` the k-means matrix (`@(@f64)`) is fine while every
single-vector helper (`zerovector`, `centroidfor`, `extractnumericcol`, all `:@f64`) is not.

**Where it bites, and how it presents.** Two adjacent pushes in one function lowered
differently — `moke/src/compute.tk`, accumulating a timeseries:

```llvm
%t1197 = call i64 @tk_array_append_w(i64 %t1195, i64 %t1196)   ; a str element
%t1198 = inttoptr i64 %t1197 to i8*                            ; conversion present
store i8* %t1198, i8** %datekeys

%t1202 = bitcast double %t1201 to i64                          ; an f64 element
%t1203 = call i64 @tk_array_append_w(i64 %t1200, i64 %t1202)
store i8* %t1203, i8** %datesums                               ; inttoptr MISSING
```

The simple shape — `let a=mut.@(); a=a.push(1.5);` alone in a function — takes
`tk_array_append_inplace_w` and is correct, so a small probe does not reproduce it. It needs the
non-in-place path, which is selected when the same variable is also assigned from a function
call elsewhere in the function.

**There is no workaround that keeps an f64 vector.** Returning it fails, putting it in a struct
field fails, and routing every assignment through a helper only moves the error into the helper
(measured). The options are to carry a fixed-point `@i64` — hundredths or basis points, which is
what we already do for T-20 — or to use `@(@f64)` and index into a single row. Both change the
type of every producer and consumer, which for a k-means implementation means rewriting the
arithmetic.

**A discriminator, in case it narrows the search.** `core.optimiser.cache.tof64` is declared
`(v:@f32):@f64` and assembles cleanly in all three of our trees. Its accumulator is only ever
written as `out=out.push(...)` — a self-update — so it takes `tk_array_append_inplace_w`, where
the conversion is emitted correctly. The defect appears when the same variable is ALSO assigned
from a function call somewhere in the function, which selects the non-in-place path. So the two
paths disagree, and only one of them is wrong.

**Ask.** Use the array conversion for any `@T`, including `@f64`. The element type should not
select the conversion for the container.

## T-13 — a bare sum variant in a value position produces a value that crashes

```toke
t=$lvl{ $public:i64; $internal:i64 };
f=name(s:$lvl):i64{ <mt s { $public:v 0; $internal:v 1 } };
f=main():i64{ let l=mut.$public; <name(l) };     (* SIGTRAP *)
```

`$public` in a value position — `mut.$public`, `<$public`, `x==$public`,
`field:$public` inside a struct literal — has to be constructed as `$lvl{$public:0}`.
The bare form compiles with no diagnostic and produces a value that crashes when
matched. loke had **280 of them**, including every pattern definition in the privacy
detector, which is why that detector crashed on the first text that matched.

## T-14 — `==` on two sums compares the handle, not the variant

Two locally constructed values compare correctly. A value returned from a function does
**not** compare equal to an identically constructed local:

```toke
f=mk():$lvl{ <$lvl{$restricted:0} };
let x=mk();
x==$lvl{$restricted:0}        (* false *)
```

Every `sensitivity==$restricted` in loke's privacy and governance decisions was
therefore false. We replaced them with a ranking function that matches once and
compares integers.

## T-15 — `http.get` against a closed port returns `$ok` with a nil response

The `$err` arm never runs, and reading `.status` on the nil response is a dereference a
toke program cannot guard — `if(r==0)` is a type error against `$httpresp`. So a
program cannot distinguish "the service replied" from "nothing is listening".

Both of loke's sidecar health checks returned **available** for a dead port because of
this, which is how the privacy pipeline came to call layers that were not running and
crash. We now probe with `net.portavailable`, which answers honestly for a local
service because it tries to bind.

## T-16 — no way to construct an http request or read a response body from source

`http.res(status, body)` builds a response; nothing reads one back. Nothing constructs a
request. So a page handler with the signature `get(req:i64):i64` cannot be unit-tested
at all. Ten test files in loke had been written against `str.mockhttpreq` and
`str.httpbody` — helpers that exist in no module — and had never compiled.

`http.mockreq(method, path, body)` and `http.resbody(res)` would make handler tests
possible. We worked around it by splitting each handler's body-building into a function
that takes no request, which is better structure anyway, but the plumbing itself remains
untestable.

## T-17 — `json.parse` binds to an unrelated function

`json.parse` mangles to `tk_json_parse_w`, which does not exist. The linker resolves it
to `tk_json_parse` — a runtime helper in `tk_runtime.c` that parses an int array, a
boolean or a number and returns an `int64`, not a `Json*`. So every `json.parse` in a
toke program returns something that `json.getopt` and `json.str` then read as a
document. It links silently.

loke had 14 call sites: config parsing, the Ollama response parsers, the dashboard
preferences and the ephemeral placeholder map. `json.decode` is correct and is what we
now use. Either alias `parse` to `dec` or remove the name.

