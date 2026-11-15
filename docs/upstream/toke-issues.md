# toke — issues found building loke

> **Current state: see [`handoff-2026-09-27.md`](handoff-2026-09-27.md).** Every entry below was
> re-verified there against toke `0b0bc4e` and `4a50b87`, several are stale, and T-47 names two
> different defects (T-47a/T-47b there). This file is the detailed history.
>
> **Second batch, 2026-11-09: see [`handoff-2026-11-09.md`](handoff-2026-11-09.md)** (drafted, not
> sent), with reproducers in [`repro-2026-11-09/`](repro-2026-11-09/) run at toke v3.1.0
> (`86c432da`). It covers T-60 to T-64 below and ooke O-4/O-5.
>
> **Status of every item at toke v3.2.0, 2026-11-15: [`status-2026-11-15.md`](status-2026-11-15.md)**,
> measured with [`repro-2026-11-15/`](repro-2026-11-15/). Three new items, T-65 to T-67, are at the end. The third
> handoff, for what is still open, is drafted (not sent) as [`handoff-2026-11-15.md`](handoff-2026-11-15.md).
>
> **Answered 2026-11-15** by toke v3.2.0 (`ea7ddf22`) and ooke v3.0.0 (`7ac2472`): see
> [`toke-reply-2026-11-15.md`](toke-reply-2026-11-15.md), loke's record of the answer, measured with the same reproducers
> ([`results-v3.2.0-ea7ddf22.txt`](repro-2026-11-09/results-v3.2.0-ea7ddf22.txt)).

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

| | Severity | What | Reported as | At toke v3.2.0, 2026-11-15 |
|---|---|---|---|---|
| **T-1** | Blocks | `$ok(<bool>)` in a `bool!$err` function emits invalid IR | clang: `'%t' defined with type 'i1' but expected 'i64'` | fixed |
| **T-2** | Blocks | A `mt` of 3+ arms whose subject type is not known emits duplicate basic-block labels | clang: `Terminator found in the middle of a basic block!` | fixed (residue: T-66) |
| **T-3** | Blocks | An `i32` used as an array index is widened with `zext i1` | clang: `'%t' defined with type 'i32' but expected 'i1'` | fixed |
| **T-4** | Blocks, silent | A bare **type name** in expression position gets no diagnostic | clang: `use of undefined value '%store'` | fixed |
| **T-5** | Blocks | `void!$err` lowers to LLVM `void`, so binding the result emits `alloca void` | clang: `void type only allowed for function results` | fixed |
| **T-6** | Blocks | **Any** `let` shadowing an enclosing `let` emits invalid IR | clang: `Instruction does not dominate all uses!` | fixed |
| **T-7** | Blocks, silent | An unknown **method** call is not checked; it becomes an undefined external symbol | ld: `Undefined symbols` | fixed |
| **T-8** | Hazard | `--lint --fix` deletes imports that are needed | none — it reports success | fixed |
| **T-9** | Hazard, silent | The regex engine ignores unsupported syntax instead of rejecting it | none | rejected at check (E4075) |
| **T-10** | Hazard | `http.post` is declared twice in `http.tki`, so the function form is unreachable | misleading arity error | rejected at check |
| **T-11** | Correctness | `std.tls`, `std.mdns`, `std.infer`, `std.mlx` are stubs that return 0 or a sentinel string | none | fixed |
| **T-12** | Docs | Four stdlib `.tki` files disagree with the compiler's own builtin table | none | fixed |
| **T-13** | Blocks, silent | A bare sum variant in a value position crashes when matched | none | rejected at check (E4033) |
| **T-14** | Correctness, silent | `==` on two sums compares the handle, not the variant | none | rejected at check (E4031) |
| **T-15** | Correctness, silent | `http.get` on a closed port returns `$ok` with a NIL response | none | rejected at check |
| **T-16** | Testability | No way to construct an http request or read a response body from source | n/a | fixed |
| **T-17** | Blocks, silent | `json.parse` binds to an unrelated runtime function | none | rejected at check (E4031) |
| **T-18** | **Correctness, silent** | **`mt` on an `X!$userErr` takes the FIRST arm whatever the value is** | none | fixed |
| **T-19** | Blocks, silent | E4071 misses a trailing bare `mt` when the function returns a sum or struct | none | fixed |
| **T-20** | **Correctness, silent** | **An `f64` returned across a module boundary is corrupted** | none | fixed |
| **T-21** | Correctness, silent | A string returned by `std.homedir()` is truncated when interpolated | none | fixed |
| **T-22** | Blocks, silent | `row.f64` is declared as a result but returns a bare `i64` | none | fixed |
| **T-23** | **Correctness, silent** | **Arguments of different declared types but the same ABI are accepted reversed** (`str.join`) | none — segfault | fixed |
| **T-24** | **Correctness, silent** | **`@(array; element)` nests instead of appending** | none — intermittent segfault | rejected at check (E4031) |
| **T-25** | Blocks | `max_funcs` counts imported signatures; E9010 names neither the limit, the cause, nor that it is configurable | E9010, no line number | fixed |
| **T-26** | **Blocks, and the fix advice creates a silent bug** | **No assignment to a struct field or array element, and E2002 recommends `==`, which compiles to a no-op** | E2002, with wrong advice | fixed |
| **T-27** | **Silent code deletion** | **Comments nest, so `(*` inside a comment (e.g. `COUNT(*)`) swallows the rest of the file** | none at all | fixed as E1007; nesting declined |
| **T-28** | Silent segfault | **`str.isdigit` crashes on a `str.charat` result** — the only producer of a character cannot feed the only classifier of one | none — SIGSEGV | rejected at check (E4031) |
| **T-29** | Minor | Control-flow keywords (`sc`, `mt`, `lp`, `el`, `br`, `if`) are reserved as import aliases and the diagnostic does not name the reserved word | E2002, unhelpful | fixed |
| **T-30** | **Correctness, silent** | **`std.db` has ONE global connection; `db.open`'s returned handle selects nothing, so a two-database program silently queries whichever opened last** | none | fixed |

**Status of every item at toke v3.2.0 (`ea7ddf22`), measured by loke on 2026-11-15:
[`status-2026-11-15.md`](status-2026-11-15.md).** The later items, which this table never listed:

| | What | At toke v3.2.0, 2026-11-15 | Story |
|---|---|---|---|
| T-31 | `mt` binds result arms by position | fixed | 138.2 |
| T-32 | no nested JSON read | rejected at check; `json.at` reads | 138.12 |
| T-33 | falsy JSON values read as errors | fixed | before 3.0.0 |
| T-34 | three-segment std member lowered to a bare global | fixed | before 3.0.0 |
| T-35 | emitted IR silently truncated | fixed | 138.14 |
| T-36 | `str.tki` untyped `abi` block | fixed | 138.11 |
| T-37, T-38, T-39 | `@f64` conversion; function-wide retyping; unused-import lint | fixed | before 3.0.0 |
| T-40 | `db.exec` runs one statement | fixed | 138.6 |
| T-41 | `std.str` results interpolate as addresses | fixed | 138.11 |
| T-42 | literal of an undeclared struct type | fixed | 138.9 |
| T-43 | no bind address | fixed (`http.serveon`); port-only `serve` on `*` declined | 138.1 |
| T-44, T-47a | `json.str` unescape | fixed | 138.12 |
| T-45 | `json.enc` leaves control characters raw | fixed | 127.229 |
| T-46 | annotated binding spread in an array literal | fixed | before 3.0.0 |
| T-47b | `str.nowunix()` a string declared i64 | fixed | 138.11 |
| T-48 | `postheaders` sends nothing in loke's shape | rejected at check; typed call arrives | 138.8, 138.26 |
| T-49 | `net.listen(port)` segfaults | rejected at check | 138.13 |
| T-50 | `mt` on `process.wait` inverts success | rejected at check | before 3.0.0 |
| T-51 | `json.dec` accepts `{not json` | fixed | 138.2 |
| T-52 | `@$self` field crashes the compiler | fixed | 138.13 |
| T-53, T-54 | field cap; 65th struct type | fixed | 127.190; 138.15, 127.250 |
| T-55 | `str.charat` quadratic | fixed (linear, measured) | 127.170 |
| T-56 | 32-import cap | fixed as a diagnostic; default 32 kept | 138.15 |
| T-57 | `http.get(client;path)` registers a route | rejected at check | 138.3 |
| T-58 | https client verifies nothing | fixed; Host port fixed; **header-carrying GET open** | 135.25; 138.28; **138.27** |
| T-59 | capability grants cannot be scoped | **open** (owner) | **138.19** |
| T-60 | `==` on arrays; spawn-failure idiom | `==` **open** (owner); spawn idiom rejected at check (residue T-67) | **138.20**; 138.21 |
| T-61 | u32 field plus untyped local | rejected at check (never reproduced) | 127.356 |
| T-62 | inline `@@str` row as a call argument | fixed | 127.274 |
| T-63 | client connect-to-address, resolver, body cap, deadline | **open** (owner) | **138.24, 138.25** |
| T-64 | cut response answered `$ok` | fixed (every client call measured) | 138.23, 138.31 |
| **T-65** | a parameter named `t<digits>` collides with IR temporaries | **new**, build break after a clean `--check` | — |
| **T-66** | `mt` with variant arms on an i64 passes `--check` | **new**, E9005 at build | — |
| **T-67** | an integer accepted where the runtime reads a pointer (`process.wait(5)`, `str.toupper(42)`) | **new**, silent crash | — |

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

**2026-11-15: fixed** (before toke 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): the reproducer builds and exits 10 ([`repro-2026-09-27/results-v3.2.0-ea7ddf22.txt`](repro-2026-09-27/results-v3.2.0-ea7ddf22.txt)).

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): the declared-field subject builds and exits 33. The i64-subject program no longer reaches clang: it passes `--check` and the build stops with a located E9005 ("the sum type of the matched value is not established"), filed as **T-66**.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): exit 2.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): E4033 "'thing' is a type name, not a value" at `--check`.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): `$ok(0)` in a `void!$err` function builds and exits 0; the filed `$ok(void)` is E4033.

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

**2026-11-15: fixed** (before 3.0.0), with the W3013 shadowing warning. Measured at toke v3.2.0 (`ea7ddf22`): exit 57, W3013 emitted.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): E4036 "no receiver method" at `--check`.

---

## T-8 — `toke --lint --fix` deletes imports that are needed

**Severity:** hazard. Reported before; repeating it here so the set is in one place.

The `unused-import` rule looks only at **alias** usage (`t.foo`) and ignores **type**
references, so it removes `i=t:shared.types;` from a file whose only use of that module
is `$lokeerr`. Applied across loke it deleted **197 imports in 119 files** and produced
265 `identifier 'lokeerr' is not declared` errors, and `--fix` reported success.

A `--fix` that breaks a correct file is worse than no `--fix`. Suggested fix: count
`$type` references as uses; failing that, exclude `unused-import` from `--fix`.

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): `--lint --fix` keeps the import and `--check` afterwards is rc 0.

---

## T-9 — the regex engine ignores unsupported syntax

**Severity:** hazard, silent.

`\s`, `\S`, non-greedy `*?` and the inline flag `(?i)` all return **no match** rather
than raising. So a pattern using them compiles, runs, and quietly does nothing. This is
how loke's `privacy/content.tk` script-stripping sanitiser passed review for months: it
was a privacy control that matched nothing.

Either support them or reject them at compile time. Silence is the worst of the three.

**2026-11-15: rejected at check** (toke 137.9, one regex engine). Measured at toke v3.2.0 (`ea7ddf22`): the lazy `<.*?>` is E4075 at `--check`, suggesting `<[^>]*>`; without that line `\s`, `\S` and `(?i)` match (`s: a_b S: _ _ ci: Z`, [`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p09.tk`).

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

**2026-11-15: rejected at check** (138.3, 137.10). Measured at toke v3.2.0 (`ea7ddf22`): the four-argument call is E4026 naming route registration; `http.post(url;body)` is E4031 naming `http.clientpost`; `clientpost`, `clientput` and `clientdelete` arrive at a loopback recorder ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p10.tk`).

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

**2026-11-15: fixed** (137.11, 121.53). Measured at toke v3.2.0 (`ea7ddf22`): the `.tki`-arity calls take their `$err` arms (`mlx.isavailable=false`, `load`/`generate` errors), and the implementation-arity call is E4026. No stub reports success.

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

**2026-11-15: fixed** (138.11). Measured at toke v3.2.0 (`ea7ddf22`): the four names are in their `.tki`; `str.padright` with a pad pads `[ab***]`; `json.getregulations` has length 1.

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

**2026-11-15: all nine are done at toke v3.2.0 (`ea7ddf22`)**, each measured (status lines under
each item). Item 9 included: an E9003 now reads "while compiling f=judge at repro.tk:14" with a
`-->` location (seen on T-65, the one new build break of this kind).

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

**2026-11-15: loke's error, not toke's;** not re-measured. The neighbouring E4074 (a comparison
standing as a statement, 138.10) is the warning asked for in its statement form.

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

**2026-11-15: fixed** (138.2). Verified by loke at 3.1.0 (F10.39; the tripwire tests now assert the fix) and measured at toke v3.2.0 (`ea7ddf22`): exit 77.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): E4071 for the sum and for the struct.

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

**2026-11-15: fixed** (138.5). Verified by loke at 3.1.0 (F10.39) and measured at toke v3.2.0 (`ea7ddf22`): exit 55, `declare fastcc double @lib_f64abs(double)`.

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

**2026-11-15: fixed** (138.11). Measured at toke v3.2.0 (`ea7ddf22`): every form of the interpolation has the length of `$HOME` plus 2, and `std.homedir` links without `std.process`.

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

**2026-11-15: fixed** (138.6). Measured at toke v3.2.0 (`ea7ddf22`): `x: ok 25 | zero: ok 0 | nosuch: err`.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): the reversed `str.join` is E4031 "argument 1 of 'str.join' is declared 'str' (str.tki), got '@(str)'".

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

**2026-11-15: rejected at check** (138.9). Measured at toke v3.2.0 (`ea7ddf22`): E4031 "array literal elements must share one type"; an append is written `x=x+@(v)`.

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

**2026-11-15: fixed** (138.15, 127.250). Verified by loke at 3.1.0 (`max_funcs` removed from `tkc.toml`) and measured at toke v3.2.0 (`ea7ddf22`): 130 imported signatures build with no flag (the default is 1024); over a cap, `--check` names the count, the limit and the flag.

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

**2026-11-15: fixed** (138.10). Measured at toke v3.2.0 (`ea7ddf22`): `x.a=9` is E2002 showing the rebuild (`x=$type{a:9;b:x.b}`), and the applied old advice `x.a==9;` is E4074 "a comparison stands as a statement".

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

**2026-11-15: fixed as a diagnostic** (138.10); **nesting itself declined** (spec §8.10). Measured at toke v3.2.0 (`ea7ddf22`): E1007 "the '(*' at 7:1 is never closed ... the '(*' at 7:15 inside it opened a nested comment". loke's runner still prints DEFECT because it counts the IR; with an error there is none. Comments still nest, so loke's rule against `(*` and `*)` inside comments stays.

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

**2026-11-15: rejected at check** (138.13). Measured at toke v3.2.0 (`ea7ddf22`): E4031 "argument 1 of 'str.isdigit' is declared 'str'".

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

**2026-11-15: fixed** (138.10). Measured at toke v3.2.0 (`ea7ddf22`): one E2002 "'sc' is a reserved keyword and cannot be an import alias".

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

**2026-11-15: fixed** (138.6). Measured at toke v3.2.0 (`ea7ddf22`): `ha=1 hb=2 ta-before-b=ok ta-after-b=ok`; with `db.execon` each database gets its own tables (A.db `ta ta2`, B.db `tb`, [`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`pr8.tk`).

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

**2026-11-15: fixed** (138.2). Verified by loke at 3.1.0 (F10.39) and measured at toke v3.2.0 (`ea7ddf22`): `valid,okfirst=ok valid,errfirst=ok invalid,okfirst=err invalid,errfirst=err` (the runner's REPRODUCES is its substring match).

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

**2026-11-15: rejected at check** (138.12). Measured at toke v3.2.0 (`ea7ddf22`): a `json.getval` string passed to `json.i64` is E4031 ("declared 'jsonval', got 'str'"), so the crash cannot be written; `json.at(j;"usage")` then `json.i64` reads 150 ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p32.tk`).

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`) (the reproducer's `$json` spelled `$jsonval`, 3.2.0's rename): 0, 0.0, false and "" are each `$ok`; a missing key is `$err`.

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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): both programs build and run.

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

**2026-11-15: fixed** (138.14). Measured at toke v3.2.0 (`ea7ddf22`): 670 constants and a 300k-character string, toke rc 0 and clang rc 0.

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

**It is not only `std.str`.** `std.db` declares its row accessors (`db.rowstr`, `db.rowi64`)
and `std.json` most of its helpers (`json.parsearray`, `json.getval`, `json.getstr`, ...) the
same way. So a JSON value handed to a row accessor type-checks: `core.memory.export.importjson`
read every element of an imported file with `db.rowstr(item;...)`, got nothing back for any
field, and crashed (LS1.1k). It is the mirror of LS1.1i, a row read through a JSON accessor.
Every call-site check is defeated by the signature, which is the root cause T-23 and T-24
share with this one.

**A correction to an assumption we carried for a while, in case it saves someone the same
trip.** `arr.len()` is **not** a defect: `arr.len()` and `arr.len` emit the identical
`getelementptr i64, i64* %p, i32 -1`, and the compiler labels it `; .len()`. Only
`str.len(<array>)` is wrong.

**2026-11-15: fixed for the filed cases** (138.11); **the class remains for integers (T-67)**. Measured at toke v3.2.0 (`ea7ddf22`): `compare(a,b)=-1 compare(b,a)=1 compare(a,a)=0 padleft=[007] tof32=12345` ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p36.tk`); `str.len(array)` and `str.tof32(12345)` are E4031. But 56 of `str.tki`'s 105 members are still `gen:"abi"` (the same 56 as at 3.1.0), and an integer in one of their string slots checks clean and segfaults (`str.toupper(42)`): filed with T-67.

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

**There is no workaround that keeps an f64 vector.** Four were measured and all four fail:
returning it; putting it in a struct field; routing every assignment through a helper (the error
moves *into* the helper, which also returns `@f64`); and wrapping the column in a one-row
`@(@f64)` matrix so only the correct container type is declared — that last one fails because the
inner accumulator is still an `@f64` local, which is the actual problem.

**What does work is changing the element type.** `moke/src/profiler.tk` and `moke/src/hooks.tk`
both assembled the moment their accumulators became `@i64` of scaled micro-units, with
`shared.types.i64min`/`i64max`/`i64mean` replacing `math.min`/`max`/`mean`. That is a real fix
rather than a workaround — integer summation is also more accurate for a mean than accumulating
over f64 — but it is only cheap when the consumers are simple statistics. `moke/src/compute.tk`
is blocked on it because it uses `math.percentile` and `math.linreg`, which have no integer
equivalent and would have to be reimplemented. The options are to carry a fixed-point `@i64` — hundredths or basis points, which is
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

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): `2 1.5` and `2 2.5`.

## T-38 — a name's type is resolved function-wide, so a later `let` retypes an earlier binder and the diagnostic points at the wrong line

**Severity: diagnostic quality, and the suggested fix is actively wrong.**

Two bindings of the same name in one function, in disjoint scopes, are resolved as one name. The
LATER annotated `let` decides the type, and the error is reported against the EARLIER use:

```toke
m=repro.one;
i=str:std.str;
t=$a{p:i64};
t=$b{q:i64};
t=$e{ $bad:str };
f=mk():$a!$e{ <$ok($a{p:7}) };
f=main():i64{
  let v:$a=mt mk() { $ok:s s; $err:e $a{p:0} };   (* E4031 reported HERE *)
  let xs=@($b{q:1});
  lp(let i=0;i<xs.len;i=i+1){
    let s:$b=xs.get(i);                           (* the actual cause *)
    str.fromint(s.q)
  };
  <v.p
};
```

→ `E4031 type mismatch: expected 'a', got 'b'`, attributed to the `mt` line, with
`fix: cast RHS to a using 'as'`. **Following that advice would be wrong**: the `mt` arm binder
`s` is correctly an `$a`, and the `$b` comes from a `let s` inside a loop eleven lines away. Rename
either `s` and the module compiles.

This is adjacent to **T-6** (a shadowed `let` reusing a name across sibling scopes) but the symptom
is different and arguably worse: T-6 produces invalid IR, which fails loudly at the right file.
This produces a type error attributed to a line that is correct, with a fix that would break it.
A reader has no way to connect the two sites, and it cost us a build cycle to find.

**Ask.** Scope a `let` to its block for type resolution. Failing that, when two bindings of one
name disagree, name **both** locations in the diagnostic — the way E4034 does for a field declared
at two offsets, which is the same class of problem and is reported far better.

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): exit 7.

## T-39 — the `unused-import` lint rule is unsound, and `--lint --fix` breaks the build

**Severity: the auto-fix produces code that does not compile.**

An import is reported unused when its ALIAS never appears. But a TYPE from an imported module is
referred to **without** the alias — `$agentdef`, not `at.$agentdef` — so an import that exists
solely to bring types into scope is always reported unused, and `--fix` deletes it.

Measured on `packages/core/src/agents/executor.tk`:

```
$ toke --lint --fix executor.tk        # removes i=str:std.str, i=t:shared.types, i=at:core.agents.types
$ toke --check executor.tk
E3011 identifier 'sensitivitylevel' is not declared
E3011 identifier 'agentdef' is not declared          ... 6 errors
```

`sensitivitylevel` comes from `shared.types` and `agentdef` from `core.agents.types`. Both are
used; neither alias is.

**Across `packages/core`: 189 `unused-import` diagnostics, of which 91 are type-only** — so
`--lint --fix` would break the build in 91 places. A repo-wide `--fix` is not a cleanup, it is an
outage.

**There is a second, subtler case that a caller cannot screen for.** We tried to remove only the
imports whose module declares no type appearing as `$name` in the file. 96 passed that test, and
**5 still broke the build** — with `E4034 no struct in scope declares a field 'content'`. Those
imports were needed for FIELD RESOLUTION on a value whose type is inferred, so the type name never
appears in the source at all. There is no source-level test for that short of compiling. The
survivors (89 removals across 68 files) were established by building, not by analysis.

**Ask.** Count a type reference as a use of the import that supplies it. Until then the rule
should be a hint with no fix span, because an auto-fix that breaks the build in half its
applications is worse than no rule: it teaches people to distrust `--fix` generally, including for
the rules where it is correct.

**A related observation on the same output.** `single-use-let` ("binding is used once, inline it",
47 sites here) is emitted as a `hint` with no fix span, which is the right treatment — and it is
worth noting that several of this codebase's `let` bindings exist precisely to give a value a
DECLARED TYPE, because E4034 reports field-offset ambiguity at the read rather than at the binding
and annotating the intermediate is the documented remedy. Inlining those would reintroduce the
ambiguity. The hint is fine; a fix for it would not be.

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): no `unused-import` on the type-only import; `--lint --fix` keeps it; `--check` afterwards is clean. LS1.3 and LS1.4 noted it the same day.

## T-40 — `db.exec` applies only the FIRST statement of a multi-statement string, and reports success for all of them

**Severity: a migration silently does not apply, and reports that it did.**

`std.db.exec` is `sqlite3_prepare_v2` followed by step. `prepare_v2` compiles the first
statement of the string it is given and writes a pointer to the remainder through its `pzTail`
out-parameter; the binding discards that pointer. So statement one runs, statements two onward
are never seen, and the result is `$ok`.

Found while adding the append-only triggers to loke's audit table. The migration read, in
effect:

    CREATE TABLE x (...); CREATE INDEX ix_x ON x(...);

The table was created. The index was not. `exec` returned `$ok`, the migration was recorded in
`schema_migrations` as applied, and nothing anywhere reported a problem — the next run saw the
version row and skipped it, so the index could never be created afterwards either.

What makes this worth filing rather than documenting locally: the interface cannot express what
the function does. `exec(sql:str;params:@str):i64!$dberr` accepts any string SQLite's parser
accepts, and SQLite's parser accepts a statement list. A caller reading that signature has no
way to know only a prefix of its argument will run, and the success return actively tells it
otherwise. That is the same family as T-23 and T-36: a declared shape that the implementation
does not honour, with nothing for the compiler to say.

Three ways out, in our order of preference:

1. **Loop on the tail pointer** until it reaches the end of the string, stepping each statement.
   This is what `sqlite3_exec` does, and it makes the signature honest.
2. **Reject a multi-statement string** with an error naming the trailing text. Less useful, but
   it cannot mislead.
3. **Document it and rename**, e.g. `execone`. The worst of the three, because every existing
   call site keeps its current behaviour and the name is the only warning.

Either of the first two is a strict improvement; the current behaviour has no reading under
which it is correct.

**Worked around in loke** by one statement per migration (`storage/migrations.tk`), and guarded
by `scripts/find_multistatement_exec.py`, which resolves literals, `str.concat` nests, local
`let` bindings, same-file helpers, pass-through wrappers and `sql:` field initialisers. The
guard exists because the work-around lives in one file and the hazard does not.

**2026-11-15: fixed** (138.6). Measured at toke v3.2.0 (`ea7ddf22`): `sqlite_master` lists `x,ix_x`.

## T-41 — interpolating a `std.str` result prints the string's ADDRESS for fifteen functions

**Severity: wrong output, silently. This one reached the privacy pipeline's own summary line.**

Measured 2026-09-24 against `fedd48d`, the commit loke's figures are labelled with. I re-ran
it on main `444a55c` and got the same result:

    io.println("[\(str.fromi64(5))]")      -> [4349761984]
    io.println("[\(str.randhex(4))]")      -> [4335262192]
    io.println("[\(str.tolower("A"))]")    -> [a]

Interpolation formats a value by its declared type. `std.str` declares its functions in a
`gen:"abi"` block, many of them with return type `i64` (T-36). The functions that really
return a string are therefore formatted as integers, and the integer is the pointer. A
binding inherits the declared type, so `let s=str.fromi64(5); "\(s)"` fails the same way.
`let s:str=str.fromi64(5)` retypes the binding and prints `5`. `str.concat` takes its
arguments as strings and is also correct.
**But see T-46:** the annotated binding is then dropped from any array literal it is
written into, so it is not a safe workaround. Use `str.fromint` or `str.concat`.

The affected set cannot be read off the interface. `tolower`, `toupper` and `substr` sit in
the same block with the same declared return, and interpolate correctly. I probed each
string-producing name one call at a time. These fifteen print an address: `fromi64`,
`fromint64`, `fromi32`, `fromu32`, `fromu16`, `frombool`, `randhex`, `nowiso8601`, `padleft`,
`padright`, `sha256prefix`, `trimws`, `strip`, `reverse`, `replaceall`.

This is the T-21 family. T-21 was one function, `std.homedir()`, whose interpolated result is
truncated. The ask is the same as T-36: declare these functions with the type they return. Any
interpolation of an `i64` that is really a handle would then be reported rather than formatted.

**What it cost in loke.** `core.privacy.pipeline.summariserun`, the one line that tells a
person what the pipeline did, printed "4378090592 entities detected (4378090624 RESTRICTED,
...)". Its test asserted only that the words were present, so it passed. moke's project
ids were `p-` followed by an address. **Worked around** by annotating the binding or using
`str.concat`. **Guarded** by `scripts/find_interp_abi_str.py`, in the quality gate. The guard
flags direct interpolation and unannotated bindings for the fifteen measured names.

**2026-11-15: fixed** (138.11). Measured at toke v3.2.0 (`ea7ddf22`): 0 of 14 print an address.

## T-43 — no toke API can choose the address a server binds, so every server listens on all interfaces

**Severity: a local-first product cannot keep its API off the network.**

`std.http` exposes `serve(port)`, `serveworkers(port; workers)`, `servetls(...)` and
`listen(addr; handler)`. None of them takes a bind address. `tk_web_glue.c` calls
`http_serve_workers(NULL, NULL, port, workers)`. In `http.c`, `bind_listen` treats a NULL
host as `INADDR_ANY`, even though it already supports a real host through `inet_pton`.
`listen("localhost:8080"; …)` parses the port and discards the host.

Measured 2026-09-24 with `lsof`: loke's server listens on `*:11430`, and its `ooke.toml`
says `host = "127.0.0.1"`. The capability exists one layer down, in `http_serve_workers`'s
`host` argument. It is simply not reachable from toke source.

**The ask:** `http.serveworkershost(host:str; port:u64; workers:u64)`, or a `host` argument
on `serveworkers`, passed through to `bind_listen`. ooke's `serverun` would then take the
`host` it already parses from `ooke.toml`. Until then loke refuses requests per request
(a foreign Origin, GA2.6; a non-loopback Host, GA2.7). That stops a browser and does not
stop a client on the same network.

**2026-11-15: fixed** (138.1); **the port-only form declined**. Measured at toke v3.2.0 (`ea7ddf22`): `http.serveon("127.0.0.1";P)` and `http.listen("127.0.0.1:P";…)` listen on `127.0.0.1` only ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p43.tk`), while `http.serve(P)` still listens on `*`: toke's owner kept it, because moving it to loopback would take deployed servers off the network with no diagnostic (`docs/stdlib/http.md`). loke calls the `…on` forms through ooke's `[server] host`.

## T-42 — a struct literal naming an UNDECLARED type is accepted, and read positionally

**Severity: correctness, silent.** Same family as T-4 and T-7: a name that resolves to
nothing is not checked.

Measured 2026-09-24 against `fedd48d`. `--check` exits 0, the build succeeds, the binary runs:

```toke
m=t42;
i=io:std.io;
t=$real{label:str;value:str};
t=$box{items:@$real};
f=main():i64{
  let xs=@($ghost{name:"a";value:"b";extra:"c"});   (* $ghost is declared nowhere *)
  let b=$box{items:xs};
  let r=b.items.get(0);
  io.println(r.label);                              (* prints "a" *)
  <0
};
```

`$ghost` does not exist, its field names do not match `$real`'s, it has a field `$real` does
not, and the array is assigned to a field typed `@$real`. None of that is reported. The read of
`r.label` returns whatever sits at `label`'s offset, which is the literal's first field.

**What it cost in loke (GA5.13).** `core.governance.dashboard.buildscorecard` built its five
metric rows as `$dashboardmetric{name;value;status;detail}` literals and stored them in an
`@$scorecardmetric{label;value;status}` field. It rendered correctly only because the first
three fields happened to line up. `tests/unit/governance/test_dashboard.tk` demonstrates the
hazard: with one literal's fields written in a different order, the loke build still succeeds
with no diagnostic, and the row's label, value and detail come back as each other.

**Suggested fix:** report an undeclared type name in a struct literal (E3011 or E4033), and
check a literal's field names against the declared type it is assigned to.

**2026-11-15: fixed** (138.9). Measured at toke v3.2.0 (`ea7ddf22`): E3011 "identifier 'ghost' is not declared".

## T-46 — an annotated `let s:str=` binding of a T-41 function, used as an array element, is compiled as a spread

**Severity: a value silently disappears from an array; for some functions, SIGBUS.**

Measured 2026-09-24 at `fedd48d` (LS1.1s), against a scratch `(k TEXT, v TEXT)` table:

    let g:str=str.fromi64(12345);
    db.exec("INSERT INTO kv VALUES (?,?)";@("g";g))       -> k='g', v=NULL
    db.exec("INSERT INTO kv VALUES (?,?)";@(g;"first"))   -> k='first', v=NULL
    let u=str.fromi64(12345);   @("u";u)                  -> v='12345'
    @("d";str.fromi64(12345))                             -> v='12345'
    let h:str=str.fromint(12345);   @("h";h)              -> v='12345'
    let r:str=str.randhex(4);   @("r";r)                  -> SIGBUS

The IR shows why. For `@("g";g)` toke emits its **spread-array** path with `g` as the base:
it loads a length from the word before `g`'s data, allocates `len + 1`, copies `len` words
from `g` and stores `"g"` after them. For a `fromi64` string that length reads 0, so the
element vanishes and the literal has one element. For `randhex` it reads garbage. Position
does not matter, and `str.len(g)`, `str.concat` and interpolation of `g` are all correct.
Seen: `trimws` (dropped), `randhex` (crash), `fromi64` (dropped); `tolower` and `concat` are
not affected, which is the T-41 split again. A plain rebinding, `let e2=g`, inherits it.

The annotation is **T-41's recommended workaround**, which is what makes this worth an
entry: fixing the interpolation moves the defect into the next array literal. In loke it
made `memory_scores`' INSERT bind NULL into a NOT NULL column and fail (M1.7a, where it was
first misread as position-dependent). The form that is correct in both places is a function
declared to return `str`: `str.fromint`, or `str.concat("";...)`.

**Guarded** by the array-element check in `scripts/find_interp_abi_str.py`. The ask is T-36's:
declare these functions with the type they return.

**2026-11-15: fixed** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): `len(@("g";g))=2`.

## T-47 — `json.str` unescapes by dropping the backslash, so `\n` reads back as the letter `n`

**The same defect as T-44**, which a parallel branch filed the same day. Kept, because the measurements below go further than T-44's. Treat the two as one upstream ask.

**Severity: data corruption on a round trip, silently.**

Measured 2026-09-24 at `fedd48d` (LS1.1k). `json_str` in `src/stdlib/json.c` copies a string
value with a "basic unescape":

```c
if (*p == '\\') { p++; *w++ = *p++; }
```

so `\"` and `\\` come back right, and `\n`, `\t`, `\r`, `\b`, `\f` and `\uXXXX` come back
as the letter after the backslash. `{"c":"he said \"hi\"\nthen"}` reads as
`he said "hi"nthen`. `json.getstr`, `json.getstring` and `json.get` all route to it, and
`json_keys` has the same loop. The streaming parser in the same file has a correct unescape
(`case 'n': *wp++ = '\n'`) that this path does not use.

In loke it meant a memory export, which escapes newlines correctly, could not be imported
without every multi-line memory collapsing onto one line. **Worked around** in
`shared.jsonobj.strvalue`, which takes the raw value with `json.getval` and decodes it.
**Ask:** use the streaming parser's unescape in `json_str`.

**2026-11-15 (T-47a): fixed** (138.12). Measured at toke v3.2.0 (`ea7ddf22`): bytes `97 10 98 9 99 13 100 34 101 92 102 65`.

## T-48 — `http.postheaders` sends nothing, in the shape loke's cloud providers call it

**Severity: an outbound request fails silently. Measured over http. https is unverified.**

Measured 2026-09-25 against a local server that logs every request. `http.posturl(url;
body)` arrives every time. `http.postheaders(http.client(url);"";bytes;headersjson)` never
arrives, and the match takes its `$err` arm. That is the exact shape of
`browser.pages.api.pipeline.toanthropic`. `http.client(base)` with a separate path fails the
same way, with headers as a JSON string or as an array of `$httpheader`. The glue,
`tk_http_postheaders_w(url, body, headers, extra)`, takes a URL first and ignores its fourth
argument, while the interface declares `(i64, i64, i64, i64)` with no names. So the
compiler's binding and the glue's parameter order cannot be checked against each other.
loke could not measure https without spending a real provider key, so what this means for
the Anthropic and OpenAI paths is recorded as F5.11 and not asserted here.

**Measured 2026-09-27 at `0b0bc4e` (VM1.6f): the call works when it is called the way the glue
reads it.** `let raw:str=http.postheaders("http://127.0.0.1:P/probe";"{\"a\":1}";
"{\"x-probe\":\"yes\",\"authorization\":\"Bearer not-a-real-key\"}";0)` arrived at a local
server that logs every header, with both custom headers, and answered the response body. The
same call to `https://127.0.0.1:P/probe`, against a local TLS server holding a SELF-SIGNED
certificate for `CN=probe.invalid`, also arrived with both headers and answered: see T-58. So
T-48 is loke's calling convention (a client handle where the glue reads a URL string; toke at a
later commit type-rejects exactly that, E4031 "argument 1 ... read by the runtime as a C
string", as reported to loke and not re-measured here), not an inability of the runtime. Also
read from the glue: the request always carries `Content-Type: application/json` whatever the
headers say, a header value cannot contain a `"`, and the Host header omits the port. loke's
local callers post through `shared.reachability.localpost`; the hosted ones stay where they
are until T-58 is resolved (VM1.6g).

**Re-measured 2026-10-08 at toke v3.1.0 (`86c432da`), loke VM1.6g, locally against a TLS recorder
with a throwaway CA.** The four-argument client-first call is E4026 and the two-argument
`http.get(url;@(http.header(...)))` is E4031 (`http.header` wants a `req`, and `http.get` is
route registration). **But the THREE-argument client-first call,
`http.postheaders(http.client(url);body;@(@(name;value)))`, still compiles** (the `httpclient`
is accepted where the declared parameter is `str`) and sends nothing: no TLS handshake reaches
the server, trusted certificate or not, and the call answers `$err`. No loke source uses it
(checked by grep, 2026-10-08); putting it back in `core.providers.transport.post` is VM1.6g's
mutant and fails `tests/integration/test_hosted_tls.tk` by name. The URL-first typed call
arrives: a caller's `content-type` REPLACES the default (one Content-Type line arrives), and the
Host header still omits the port. **The ask (new):** reject an `httpclient` where a `str` URL is
declared, as the four-argument form already is.

**2026-11-15: rejected at check** (138.8; the client-first three-argument shape by 138.26). Measured at toke v3.2.0 (`ea7ddf22`): the typed `http.postheaders(url;body;@(@(name;value)))` arrives at a loopback recorder with `x-api-key=k1` and one `content-type` ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p48.tk`); both four-argument shapes are E4026 and the three-argument client-first one E4031 (W117). Certificate verification is T-58.

## T-49 — `net.listen(port)` segfaults

Measured 2026-09-25: `let fd=net.listen(59433);` in a test binary crashes (SIGSEGV).
`std.net` declares it as `gen:"abi"` `(i64) -> i64`, so the compiler cannot check what it
is given. loke's test opens a listener with `nc -l` instead.

**2026-11-15: rejected at check** (138.13). Measured at toke v3.2.0 (`ea7ddf22`): `net.listen(port)` is E4031; `net.listen("127.0.0.1:P")` returns a descriptor ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p49.tk`).

## T-50 — `process.wait` is a plain `i32`, and every `mt` on it inverts success

`std.process` declares `process.wait(Handle) -> i32`, not a result. A `mt process.wait(h)
{ $ok:c ...; $err:e ... }` therefore falls to T-33's "a zero word is the error" reading, so
**exit code 0 takes the error arm**. loke had 17 such sites. The installer reported failure
on every successful step, `uname` answered an "unknown" platform, and the CLI's `runcmd`
reported 127 for commands that had succeeded. The ask is the same as T-33's: declare the
error side, or reject a match on a non-result.

**2026-11-15: rejected at check** (before 3.0.0). Measured at toke v3.2.0 (`ea7ddf22`): E4031 "expected an error union 'T!E', got 'i32'".

## T-51 — `json.dec` accepts `{not json`, and reading the result crashes

Measured 2026-09-25: `mt json.dec("{not json") { $ok:o ...; $jsonerr:e ... }` takes the `$ok`
arm, and `json.str(o;"method")` on that value then segfaults. So the decoder's own verdict
cannot guard a server's input. The mcp-toke server was taken down by one malformed line from
any client. loke now pre-checks structure (a single `{...}` with balanced braces outside
strings) before decoding. The ask: `json.dec` should reject input that is not JSON.

**2026-11-15: fixed** (138.2). Measured at toke v3.2.0 (`ea7ddf22`): with either arm first, `dec arm=jsonerr read=dec-err`.

## T-52 — a struct holding an array of its own type crashes the compiler

Measured 2026-09-26 at `fedd48d`: this whole program makes `toke --emit-interface` exit
with SIGSEGV.

    m=rb;
    t=$n{v:i32;c:@$n};
    f=mk():$n{
      <$n{v:1 as i32;c:@()}
    };

A struct field of type `@$self` is how a tree is written (loke's navigation items carry their
`children`). The same struct without the self-referential field compiles. loke has no working
use of the shape; `packages/browser/src/nav.tk` is the file that hit it, and it has no
importer.

**2026-11-15: fixed** (138.13). Measured at toke v3.2.0 (`ea7ddf22`): `--emit-interface --check` exits 0.

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

**2026-11-15: rejected at check** (138.13). Measured at toke v3.2.0 (`ea7ddf22`): both forms are E4033 "'$internal' is a type, not a value".

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

**2026-11-15: rejected at check** (138.9). Measured at toke v3.2.0 (`ea7ddf22`): E4031 "'==' does not compare struct or sum values ... match on the variant or compare a field". (loke's 2026-09-27 runner still prints DEFECT, because it accepts only exit 11.)

## T-15 — `http.get` against a closed port returns `$ok` with a nil response

The `$err` arm never runs, and reading `.status` on the nil response is a dereference a
toke program cannot guard — `if(r==0)` is a type error against `$httpresp`. So a
program cannot distinguish "the service replied" from "nothing is listening".

Both of loke's sidecar health checks returned **available** for a dead port because of
this, which is how the privacy pipeline came to call layers that were not running and
crash. We now probe with `net.portavailable`, which answers honestly for a local
service because it tries to bind.

**2026-11-15: rejected at check** (138.3). Measured at toke v3.2.0 (`ea7ddf22`): the one-argument `http.get(url)` is E4026; against a closed port `http.clientget` answers `$err` ("TCP connect failed") and `http.geturl` `$err` ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p15.tk`).

## T-16 — no way to construct an http request or read a response body from source

`http.res(status, body)` builds a response; nothing reads one back. Nothing constructs a
request. So a page handler with the signature `get(req:i64):i64` cannot be unit-tested
at all. Ten test files in loke had been written against `str.mockhttpreq` and
`str.httpbody` — helpers that exist in no module — and had never compiled.

`http.mockreq(method, path, body)` and `http.resbody(res)` would make handler tests
possible. We worked around it by splitting each handler's body-building into a function
that takes no request, which is better structure anyway, but the plumbing itself remains
untestable.

**2026-11-15: fixed** (138.16). Measured at toke v3.2.0 (`ea7ddf22`): a handler called with `http.mockreq("POST";"/x";headers;"hello";@())` answers `status=200 body=[got POST /x body=hello]` ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p16.tk`).

## T-17 — `json.parse` binds to an unrelated function

`json.parse` mangles to `tk_json_parse_w`, which does not exist. The linker resolves it
to `tk_json_parse` — a runtime helper in `tk_runtime.c` that parses an int array, a
boolean or a number and returns an `int64`, not a `Json*`. So every `json.parse` in a
toke program returns something that `json.getopt` and `json.str` then read as a
document. It links silently.

loke had 14 call sites: config parsing, the Ollama response parsers, the dashboard
preferences and the ephemeral placeholder map. `json.decode` is correct and is what we
now use. Either alias `parse` to `dec` or remove the name.

**2026-11-15: rejected at check** (138.9, `12c71a58`). Measured at toke v3.2.0 (`ea7ddf22`): the filed program is E4031 at `--check` ("argument 1 of 'json.getstr' is a JSON document ... but this value comes from json.parse, which returns a str, number, bool or array"). toke kept `json.parse` as a scalar and array parser rather than aliasing it to `json.dec`; loke has no `json.parse` call.


## T-44 — `json.str` unescapes `\n` to a bare `n`

**Severity: wrong value, silently.**

Read from the source at `fedd48d` (`src/stdlib/json.c`, `json_str`) and confirmed by a
failing assertion 2026-09-24: the unescape loop is `if (*p == '\\') { p++; *w++ = *p++; }`,
which copies the character after a backslash verbatim. `\"` and `\\` come out right by
accident; `\n`, `\t`, `\r`, `\b`, `\f` become the letters `n`, `t`, `r`, `b`, `f`, and
`\uXXXX` becomes `uXXXX`. With `str.trim` and an equality match, the reply
`{"content":"summarisation\n"}` was not recognised
(`tests/unit/router/test_intent.tk`, "a reply with a trailing newline is still read").

**What it cost in loke.** Any model reply read through `json.str` that ends in a newline
comes back with a trailing `n`, so an exact comparison fails. `core.router.intent` now
matches the task name by prefix (F5.9). Any other exact comparison on a `json.str` result
from an LLM is exposed to this in the same way. The ask: decode the JSON escapes as the
spec defines them.

**2026-11-15: fixed** (138.12). Verified by loke at 3.1.0 (the brief: `json.str` unescape) and measured at toke v3.2.0 (`ea7ddf22`): `len=14 lastbyte=10`.

## T-45 — `json.enc` escapes only `"` and `\`

**Severity: malformed output, silently.**

`json_enc` in `src/stdlib/json.c` at `fedd48d` escapes the quote and the backslash and copies
every other byte through. A newline, tab or carriage return in the input is therefore a raw
control character inside a JSON string, which RFC 8259 forbids. std.json's own reader accepts it,
so a round trip inside toke looks fine; Go's `encoding/json`, which is what Ollama uses, rejects
it. Found 2026-09-24: `core.router.intent.classifybody` (F5.10) sent every multi-line prompt to
Ollama as invalid JSON. **Worked around** with `shared.jsonobj.escape`, which escapes newline,
CR and tab as well. Other control characters below 0x20 are still not escaped by either.
The ask: escape all control characters, as the spec requires.

**2026-11-15: fixed** (127.229). Measured at toke v3.2.0 (`ea7ddf22`): `json.enc` writes `\n`, `\t` and `\r` as escapes (`34 97 92 110 98 92 116 …`). loke's `shared.jsonobj.escape` workaround is harmless and stays.

## T-53 — a struct is capped at sixteen fields, `--max-params` does not raise it, and the error names neither

**Severity: blocks, with a misleading diagnostic.**

Measured 2026-09-24 at `fedd48d`. `src/llvm.c` sizes `StructInfo.field_names` as
`[TKC_MAX_PARAMS]`, and `src/tkc_limits.h` defines `TKC_MAX_PARAMS` as 16 at compile time.
`core.governance.trace`'s `$decisiontrace` had exactly sixteen fields. Adding four more
compiled the declaration without complaint, and then every read of a field past the sixteenth
failed with `struct 'decisiontrace' has no field 'outcome'`. `--max-params=24` on the command
line and `max_params = 24` in the config file were both accepted, and neither changed the
result: the runtime limit they set is not the array bound codegen uses.

**What it cost in loke.** GA5.5 carries the four assessor fields as a separate
`$assessorfields` record passed to `persist`, not on the trace. **The ask:** reject a
declaration with too many fields at the declaration and name the limit, or size the table from
the configured limit.

**The same limit on a call, which is worse (measured 2026-09-27 at `0b0bc4e`, DA1.9).** A
function declared with seventeen parameters compiles, and its `define` in the IR is correct. A
CALL passing seventeen arguments is not: the first argument is emitted as `%t1`, a value never
defined in the caller, and the seventeenth `i8*` is passed through `ptrtoint` as an `i64`. clang
rejects the module with `use of undefined value '%t1'`, which at least stops the build, but
names neither the call nor the limit. `core.audit.disclosure.reserve` reached seventeen when
DA1.9 added the model version. **What it cost in loke:** `reserveaudited` takes the audit event
and reads the correlation id, provider and model from it, so no call passes more than sixteen.
**The ask:** reject a call or a declaration with more than `TKC_MAX_PARAMS` parameters, naming
the limit.

**2026-11-15: fixed** (before 3.0.0, 127.190). Measured at toke v3.2.0 (`ea7ddf22`): the filed program prints `16 17 20`.

## T-54 — a 65th struct type in scope silently displaces another, and the error blames a field name

**Severity: blocks, with a misleading diagnostic.**

Measured 2026-09-26 at `0b0bc4e`. `src/tkc_limits.h` caps the struct types a compilation unit
sees at 64 (`TKC_MAX_STRUCT_TYPES`). `page.api.pipeline` already saw 64 through its imports.
Importing `core.audit.disclosure`, which declared one more record type, did not report the
cap. Instead, `std.http`'s `$httpresp` stopped being a known type, and the parameter
`r:$httpresp` failed at its first field read with `E4034: field 'body' is declared at different
offsets by more than one struct, and the type of this value is not established`. Nothing in
the file had changed near that line, and renaming a local called `body` elsewhere did not help.

**What it cost in loke.** DA1.7's `reserve` takes its fourteen facts as parameters rather
than a record, so importing it adds no struct type. **The ask:** reject the 65th type where it
is declared or imported and name the limit, or grow the table.

**2026-11-15: fixed** (138.15, 127.250). Measured at toke v3.2.0 (`ea7ddf22`): 58 library types plus std.http build with no flag (`one=1`).

## T-55 — `str.charat` measures the whole string on every call, so a byte loop is quadratic

**Severity: performance, silently. It turns a linear scan into a quadratic one.**

Measured 2026-09-27 at `0b0bc4e`. `tk_str_charat_w` in `src/stdlib/str_glue.c` calls
`strlen(p)` to bounds-check the index before reading `p[i]`, so reading one byte costs the length
of the string. A loop that reads every byte of an n-byte string is O(n²). In loke's regex span
search, an in-place byte comparison written with `str.charat` took **192 s** on 1 MB, where the
copying version it replaced took 1.4 s. `str.substr`, `str.slice` and `str.indexof` measure the
string too, but once per call rather than once per byte.

**What it cost in loke.** F3.1b searches a growing window with `str.indexof` over `str.substr`
instead. **The ask:** bounds-check against a stored length, or add `str.byteat` without the check.

**2026-11-15: fixed** (127.170, a length-carrying string heap). Measured at toke v3.2.0 (`ea7ddf22`), at a larger size because the filed one runs in about a millisecond: 1.6 M and 3.2 M bytes scanned in 3 and 7 ms, ratio x10 = 17, linear ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p55.tk`). The filed program at 3.1.0, measured the same day: 195 and 774 ms for 100 k and 200 k, ratio x10 = 39.

## T-56 — a module may import at most 32 others, which caps an ooke application's routes

**Severity: blocks.**

Measured 2026-09-27 at `0b0bc4e`. `TKC_MAX_IMPORTS` in `src/tkc_limits.h` is 32, and a module that
imports more fails with `compiler limit exceeded: too many imports`. ooke's `gen_handlers.sh`
writes one generated `_handlers.tk` that imports every page module, one import per route, so an
application can have at most about thirty routes before its handler registry stops compiling.
moke reached 28. Giving seven more handlers their own page files, which is the convention
`gen_handlers.sh` documents, took it to 35 and the build failed.

**What it cost in loke.** MK6.5: seven moke API handlers (the MCP panel's five and the agents'
scan, schema and diary) stay unrouted. **The ask:** raise the limit, or have `gen_handlers.sh`
split the registry across modules.

**Worked around 2026-09-27 (MK6.5).** The limit is configurable after all: `--max-imports=N`, or
`max_imports` in `tkc.toml` (docs/upstream/repro-2026-09-27/T-56/). loke's `tkc.toml` sets
`max_imports = 40` and moke's registry, at 35 imports, compiles; with the line removed the same
file fails with E9010 on its 33rd import. What remains upstream is that the diagnostic does not
name the setting, and that ooke does not set it (O-2).

**2026-11-15: fixed as a diagnostic** (138.15); **the default declined**. Measured at toke v3.2.0 (`ea7ddf22`): E9010 at `--check`, "this module has 36 imports and the limit is 32 (max_imports)", with the flag named; `--max-imports=64` builds. The default stays 32 by toke's choice; loke sets `max_imports = 40` in `tkc.toml`. (loke's runner calls any E9010 a reproduction.)

## T-47 — `str.nowunix()` returns the time as a STRING and is declared `i64`

**Severity: wrong value, silently. It reached a budget, a kill switch and an audit trail.**

Measured 2026-09-24 at `fedd48d`. `tk_str_nowunix_w` in `src/stdlib/str_glue.c` returns
`tk_str_fromi64_w(secs)`, a string handle. `str.tki` declares it `(i64) -> i64` in the
`gen:"abi"` block. The name reads as "the unix time", and the declared type is a number, so
every arithmetic use compiles clean and computes on a heap address. Two consecutive calls
printed `30647791264` and `30647791296`, 32 bytes apart, while `time.now()/1000` printed
`1790252367`.

**What it cost in loke.** `page.api.pipeline` used it for request timing, so every audited
duration was the distance between two allocations. Its budget day number was an address
divided by 86400, which changes from allocation to allocation, so the daily budget did not
accumulate across requests. `metrics_raw.timestamp` held a pointer, and a test asserting
`timestamp > 1700000000` passed on it. `core.governance.killswitch` still uses it for
`engaged_at` and auto-release (GA5.28). **Worked around** with `shared.types.nowi64()` and
`nowms()`, which read `std.time`. **The ask** is the T-36 one: declare it `str`, or make it
return the number its name promises.

**2026-11-15 (T-47b): fixed** (138.11). Measured at toke v3.2.0 (`ea7ddf22`): `str.nowunix()` interpolates as the number of seconds, and `a/86400` is E4031 "'/' requires numeric operands: the left side is 'str'".

## T-57 — `http.get(client;path)` registers a server route; nothing says so, and its return value reads as success after 256 calls

**Severity: an outbound request is silently never sent, and a health check built on it answers
"down" for a live service, then "up" for anything. It reached loke's privacy pipeline.**

Measured 2026-09-27 at `0b0bc4e`. `src/llvm.c` resolves `http.get` to `tk_http_get_handler` and
then "disambiguates by argument count": ONE argument becomes the client GET `tk_http_get_w`,
TWO arguments stay route registration. So the natural client form

    let hc=http.client("http://127.0.0.1:5002");
    let r=mt http.get(hc;"/health") { $ok:b true; $err:e false };

compiles clean and calls `tk_http_get_handler(path=hc, handler="/health")`: it registers a GET
route whose path is the client struct read as a string and whose handler is the path string's
address. No request is made. `nm -u` on loke's objects found the symbol in nine modules that
meant a client call. Against a recorder that logs every request, the six such calls driven from
a test (Presidio, NER and LLMLingua health, and `loke doctor`'s three checks) sent nothing; the
recorder's log was never created.

Then the return value. Registration returns 0, which `mt` reads as `$err` (T-33), so every
check built this way answered "down" for a service that was answering: `loke doctor` said Ollama
was not running while it answered on the configured URL. `g_get_handler_routes` holds 256
entries (`TK_MAX_GET_HANDLERS`); once it is full, registration returns **-1**, which `mt` reads
as **`$ok`**. In a test process the Presidio health check flipped from false to TRUE on its
249th call (after seven earlier registrations) with the recorder's log still empty. A long-running
process that health-checks a sidecar per request therefore reports it healthy, forever, after
a few hundred requests, whether or not it is running.

**What it cost in loke.** The Presidio and NER detection layers were skipped as unreachable on
every request, so the pipeline ran regex only while both sidecars answered. After the flip the
pipeline called them; their scans used `http.postheaders`, which also sends nothing (T-48), and
their `X!$lokeerr` results hit T-18: a Presidio that was never reached was counted as a
COMPLETED detection layer (2 completed, 0 degraded, 0 entities), and with NER on, the run grew to
1.9 GB before the OS killed it. `loke doctor`, `GET /api/models`, the LLMLingua check and the
installer's three probes were all dead the same way. Two update checkers still call
`http.get(url;@(headers))` (VM1.6f).

**Worked around** (VM1.6e) with `shared.reachability.localget`, which uses the one-argument form
after a TCP reachability probe, and by returning plain structs, not results, from the scans.

**The ask:** do not overload a client verb on arity with a server verb. At minimum, reject a
two-argument `http.get` whose first argument is an `httpclient` (the type is known), and make
`tk_http_get_handler` return a value `mt` cannot read as success when the table is full.

**2026-11-15: rejected at check** (138.3). Measured at toke v3.2.0 (`ea7ddf22`): `http.get(client;path)` is E4031 naming `http.clientget`; 300 `http.clientget` calls put 300 `GET /health` at a loopback recorder and take the ok arm 300 times ([`repro-2026-11-15/rewrites/`](repro-2026-11-15/rewrites/)`p57.tk`).

## T-58 — `http.postheaders` over https does not verify the server's certificate

**Severity: security. Any API key sent through it is exposed to anyone who can intercept the
connection. Not reached by loke today (no loke caller uses the working shape).**

Measured 2026-09-27 at `0b0bc4e`, locally, with no provider involved. A Python server wrapping
its socket in TLS with a freshly generated self-signed certificate for `CN=probe.invalid`
listened on 127.0.0.1. `http.postheaders("https://127.0.0.1:P/probe";body;headersjson;0)`
completed the handshake, sent the request with an `authorization` header, and answered the
server's body. A client that verified certificates would have refused on two counts: the
certificate chains to no trusted root, and its name is not the host connected to.

Read from `src/stdlib/tk_web_glue.c`: `tk_http_postheaders_w` makes a fresh
`SSL_CTX_new(TLS_client_method())` and calls `SSL_set_tlsext_host_name`, but never
`SSL_CTX_set_verify`, `SSL_CTX_set_default_verify_paths` or `SSL_set1_host`, and never reads
`SSL_get_verify_result`. OpenSSL's default for a client context is `SSL_VERIFY_NONE`.
`std.tls` (`tls.c`) does set verification, so the gap is in this one call.

**What it means for loke.** T-48's addendum shows this is the only header-carrying POST that
arrives at this pin. Moving the Anthropic, OpenAI, OAuth or GitHub callers onto it would make
them send for the first time, and send a bearer token to whoever answers. They are left where
they are (VM1.6g, F5.11).

**The ask:** verify the peer by default (`SSL_VERIFY_PEER`, the system trust store, and
`SSL_set1_host` for the name), fail closed when verification fails, and let a caller opt out
only explicitly.

**Lifted at toke v3.1.0 (B0), measured by loke 2026-10-01 (F5.11) and, per call site, 2026-10-08
(VM1.6g).** `http.postheaders`, `http.geturl` and `http.clientget` each refused a self-signed
certificate (`TLSV1_ALERT_UNKNOWN_CA`) and a trusted certificate for another name
(`SSLV3_ALERT_BAD_CERTIFICATE`), with no request line reaching the server, and sent only once
the test CA was trusted through `SSL_CERT_FILE`. `tests/integration/test_https_verify.tk` and
`test_hosted_tls.tk`. Still open, and not a verification gap: there is no header-carrying GET
(`http.geturl` and `http.clientget` send only `Host` and `Connection`), so a GET that needs a
`User-Agent` or an `Authorization` (GitHub's API needs the first) cannot be written.

**2026-11-15 at toke v3.2.0 (`ea7ddf22`).** Certificate verification: fixed (135.25), as verified by loke at 3.1.0 above; not re-run for this entry (F10.53 runs `test_https_verify.tk` and `test_hosted_tls.tk` on 3.2.0). 3.2.0 also makes `std.tls` clients verify by default (121.64; read from the CHANGELOG). The Host header names a non-default port: fixed (138.28; W117 measured `Host: 127.0.0.1:47979`). **The header-carrying GET is still open as toke 138.27**: a new function and a spec amendment, waiting on toke's owner (register item 2.3 recommends `http.getheaders(url:str;headers:[[str]]):httpresp!httperr`, "accept as proposed"); `http.tki` at 3.2.0 has no such call. VM1.6g waits on it.

## T-59 — a capability grant cannot be scoped, and anyone who launches the binary can widen it

**Severity: a manifest cannot state the property a local-first program needs: network on
loopback only, files under its own directory only. Not a defect in what the broker does; a
gap in what it can express.**

Measured 2026-09-28 at `0b0bc4e`, with a probe program that makes one gated call per class
(`file.read`, `file.write`, `net.portavailable`, `process.spawn`, `env.set`), built with
`--config=` pointing at each manifest below. The probe and its runner are recorded in F10.9
in loke's `docs/epics-and-stories.md`.

1. **A scope is accepted and ignored.** `src/config.c` treats any non-empty quoted string
   as `true` for the whole class ("coarsened to the whole class for now (124.4c refines
   it)"). A binary built with `fs_read = "/nonexistent-dir-only"` read `/etc/hosts`; one
   built with `net = "10.255.255.1:9"` bound a loopback port. Nothing warns. The runtime
   flags behave the same way: `flag_to_caps` matches a prefix, so `--allow-read=/srv/www`
   grants all reads.
2. **`net` is one class for listening and connecting, to any host.** `bind_listen` and
   `client_tcp_connect` both gate on `TK_CAP_NET`. With T-43 (no bind address reachable
   from source) a server granted `net` listens on every interface and can connect anywhere.
3. **`process_spawn` covers every executable.**
4. **The launcher can add any class.** `tk_cap_init` unions every `--allow-*` token in
   `argv`, at any position, and `--allow-all` switches the process to `ALLOW_ALL`. A binary
   built with loke's manifest (no `env_write`) ran `env.set` when started with
   `--allow-env`. The manifest bounds what the code can do without a visible diff; it does
   not bound what the person starting the process can grant, and there is no way to say it
   should.
5. **`env` is the short spelling of `env_write`.** loke's manifest carried `env = true`
   from 2026-09-22 to 2026-09-28, commented as "provider API keys come from the
   environment" — a READ, which toke does not gate. It granted environment WRITE, the one
   class loke never uses. The parser accepted it silently.
6. **`enforce = false` does not opt out**, contrary to `docs/reference/capabilities.md`.
   `tk_cap_init` never reads `__tk_cap_baked_enforce`; a binary built with only
   `enforce = false` trapped CAP001 on all five classes. The behaviour is the safe one; the
   documentation is wrong.

**The ask.**
- Enforce the scope a string already carries: path prefixes for `fs_read`/`fs_write`
  (checked on the resolved path at open), `host:port` patterns for `net`, split into
  `net_listen` and `net_connect`, and an executable allow-list for `process_spawn`. Until
  that lands, **reject** a quoted string with a diagnostic that says scoping is not
  enforced, rather than silently widening it to the class.
- A manifest key (for example `sealed = true`) that makes runtime `--allow-*` flags an
  error, so a shipped binary's grants are exactly its manifest.
- Drop the `env` alias, or warn on it: it reads as "environment access" and grants write.
- Correct the `enforce` documentation, or make the key do what it says.

**What loke does.** `tkc.toml` grants `fs_read`, `fs_write`, `net` and `process_spawn` as
bare `true`, so no line reads as a limit that is not enforced, and states the intended
scope of each in a comment. `env_write` is not granted. Keeping network traffic on the
machine rests on `core.providers.transport` refusing every non-loopback send, a check in
loke's code, not on this manifest.

**2026-11-15: still open at toke v3.2.0 (`ea7ddf22`), as toke 138.19**, which toke's tracker marks **blocked on its owner**: a design note (`docs/decisions/138.19-scoped-capability-grants.md`, commit `b33e7a62` on branch `feature/z136-design-notes`, not on main) proposes per-class scope lists, direction-prefixed `net` scopes, runtime flags that narrow a baked set, a CAP002 code and a warning release before quoted strings change meaning; decisions D1–D5 are register item 3.4. Measured at 3.2.0 with loke's probe ([`repro-2026-11-15/T-59/`](repro-2026-11-15/T-59/)): points 1, 4, 5 and 6 are unchanged (a scoped `fs_read` reads `/etc/hosts`, a scoped `net` grants the class, `--allow-env` adds env_write to loke's manifest, `env = true` grants env_write with no warning, `enforce = false` still traps CAP001). Points 2 and 3 are read, not measured.

---

## T-60 — `==` on an array compares addresses, so `x == @()` is never true

**Severity: correctness, silent. It hid every failed `process.spawn` in this repository.**

Measured 2026-10-01 at toke v3.1.0 (`86c432da`), with a probe built by the pinned compiler
and read in its LLVM IR (loke F10.44).

1. **`==` on two typed arrays is a pointer compare.** `let a:@str=@(); a==@()` lowers to
   `icmp eq i8* %a, %t` against a fresh `malloc(24)` block, so it is `false`. `@()` allocates
   on every evaluation, so a comparison with the literal can never be true, whatever `a`
   holds, including an empty array produced the line before.
2. **Two UNTYPED empty arrays compare as strings.** `let x=@(); let y=@(); x==y` lowers to
   `tk_str_cmp` and answers `true`, while `x==@()` is still an address compare and answers
   `false`. The same operator means three different things depending on inference.
3. **The idiom it broke.** `let h=mt process.spawn(argv) { $ok:h h; $err:e @() }; if(h == @())`
   — spawning `/nonexistent/no-such-tool` takes the `$err` arm and then `h == @()` is
   `false`, so the program goes on to `process.stdout(h)` / `process.wait(h)` with the empty
   array's address as the handle. `process_glue.c` casts it to `ProcessHandle*` and reads a
   pid and an fd out of the array header; a pid of 0 or -1 makes `waitpid` wait for any child,
   and one probe blocked in `wait4` for good. Any other non-NULL error value (`""`, a struct)
   does the same.

What does work, measured: `$err:e 0`. The runtime's own bad handle is NULL
(`tk_process_badhandle_w`), and on it `process.stdout` takes its `$err` arm, `process.wait`
answers -1 and `process.kill` false, and `h==0` is true. loke now uses that everywhere and
`scripts/find_empty_array_sentinel.py` keeps it so.

**The ask.** Either make `==` on arrays an element-wise comparison (as the untyped case
already half does) or reject it with a diagnostic pointing at `.len`; and give
`process.spawn` a failure value that cannot be mistaken for a handle, or have
`process.wait` refuse an address that is not one it handed out.

**Reproduced 2026-11-09 at `86c432da`, with one correction**
([`repro-2026-11-09/T-60/`](repro-2026-11-09/T-60/)). The string compare in point 2 is not
limited to untyped empties: `==` between two NAMED typed arrays lowers to `tk_str_cmp` on the
array blocks, so it compares element bytes as a C string and stops at the first zero byte.
Measured: `@(1;2)==@(1;2;3)` is true, `@(256)==@(512)` is true, `@(1;2)==@(7;8)` is false (all
`@i64`). Comparing with the literal `@()` is still the address compare.

**2026-11-15: half fixed in toke v3.2.0 (`ea7ddf22`), half open.** The spawn idiom is fixed by
**138.21** (`daab5644`): the filed `$err:e @()` arm beside `$ok:h h` is now E4011 at `--check`
("match arms have inconsistent types: 'handle' vs '@(?)'"), `process.wait("abc")` is E4031, and
`$err:e 0` (loke's idiom) still checks clean. `==` on arrays is **still open as 138.20** (refuse
or element-wise is with toke's owner): measured unchanged, exits 2 and 3. loke keeps
`scripts/find_empty_array_sentinel.py` and the `$err:e 0` arms. See [`toke-reply-2026-11-15.md`](toke-reply-2026-11-15.md).

**2026-11-15 (W118), what 138.21 leaves.** An integer is still accepted where `handle` is declared: `process.wait(5)` checks clean and dies with SIGSEGV at 3.1.0 and 3.2.0, and so does the same call through a helper whose parameter loke must spell `h:i64`, because `handle` cannot be named (138.32). The NULL filler `0` is safe (`process.wait(0)` answers -1). Filed as **T-67**; the second half of this entry's ask ("have `process.wait` refuse an address that is not one it handed out") is not done.

## T-61 — adding an untyped integer local to a u32 struct field emits invalid IR

**Severity: build break (the compiler rejects its own output); not silent.**

Reported 2026-10-01 at toke v3.1.0 (`86c432da`) by loke F3.9b; seen by one worker, not yet
reduced to a standalone reproducer. In `core.privacy.systemprompt`, an expression of the shape
`unplaced:r.unplaced+stray` (where `r.unplaced:u32` and `stray` is a local counted with
integer literals) failed at the LLVM step with
`'%t212' defined with type 'i64' but expected 'i32'`: the sum is typed u32 for the field
but one operand is emitted as i64 without a truncation.

Workaround in use (`packages/core/src/privacy/system_prompt.tk:82`): do the arithmetic in i64
and narrow once, `((r.unplaced as i64)+stray) as u32`.

**The ask.** Either widen or narrow the operands consistently when an untyped integer meets a
u32, or reject the mixed expression with a type error naming both operands.

**Not reproduced, 2026-11-09, at toke v3.1.0 (`86c432da`).** A standalone reproducer,
[`repro-2026-11-09/T-61/`](repro-2026-11-09/T-61/) (the sum as a `let`, in a struct literal,
in a returned struct declared in another module, with the local counted in a loop or returned
by a function), compiles and exits 5 as expected. The filed site itself, with line 82 put back
to `unplaced:r.unplaced+stray;` and compiled against a full loke build's interfaces, gives IR
that clang accepts (the add is i64 throughout). The failing source was never committed, so the
shape that failed is unknown. The handoff makes no ask; the workaround stays. Details in
`repro-2026-11-09/T-61/result.md`.

**2026-11-15: rejected at compile time in toke v3.2.0 (`ea7ddf22`).** Story 127.356 (`7d8d1e76`,
`37efd5d0`) type-checks every struct-literal field: `u:q.u+stray` is now E4031 "expected 'u32',
got 'i64'" at `--check` (`repro.tk:18:20`), so the shape can no longer narrow silently. loke's site
already writes `((r.unplaced as i64)+stray) as u32`, which is the form 3.2.0 requires.

## T-62 — an `@@str` row subscripted inline as a call argument emits invalid IR (loke F10.42)

**Severity: build break; `--check` passes and the error is clang's.**

Found 2026-10-01 by loke F10.39; reproduced 2026-11-09 at toke v3.1.0 (`86c432da`),
[`repro-2026-11-09/F10.42/`](repro-2026-11-09/F10.42/). With `let rows:@@str=@(...)`,
`str.eq(rows.get(i).get(0);"x")` passes `--check` and fails at clang with
`'%t65' defined with type 'ptr' but expected 'i64'` (E9003): the element is loaded as `i8*`
and passed where the callee takes `i64`. A user function taking a `str` fails the same way
(`inttoptr i64 %t61`), so it is not specific to std. Binding the row first
(`let row:@str=rows.get(i);`) compiles and runs.

Workaround in loke: bind the row with its declared type before subscripting it
(`tests/unit/nocustody/test_artifact.tk`, `packages/moke/tests/test_upload_csv.tk`).

**The ask.** Load the inner element with the outer array's element type, or refuse the shape
in the checker until it does.

**2026-11-15: fixed in toke v3.2.0 (`ea7ddf22`)**, story 127.274 (`75209d81`). Measured: the std
and user-function arguments build and exit 1 and 7. Removing loke's bind-the-row-first workaround
is follow-up under F10.42.

## T-63 — the https client cannot be told where to connect, has no body cap and no whole-request deadline (loke MK19.11)

**Severity: feature ask with a security reason (SSRF defences for a user-supplied URL).**

Read from toke 3.1.0 `src/stdlib/http.c` `client_do_request` (loke MK19.9, 2026-10-01): the
client resolves the host inside connect and takes no address, and std exports no general
resolver, so a program cannot pin the address it checked (DNS rebinding). Measured 2026-11-09 at
`86c432da` over plain http on loopback ([`repro-2026-11-09/MK19.11/`](repro-2026-11-09/MK19.11/)):
a server sending one body byte every 5 s held `http.geturl` for 40,041 ms and the call answered
`$ok` (the only clock is the 30 s `SO_RCVTIMEO`, which restarts on every byte); a 64 MiB body was
read whole and answered `$ok`, length 67,108,864.

Workaround in loke: `moke.proxy.fetch` runs the system curl (no shell, absolute path) with
`--resolve`, `--max-filesize`, `--max-time`, `--proto =https`, `--max-redirs 0`, `--noproxy '*'`.

**The ask.** A client option to connect to a given address while verifying the certificate
against the URL's name; a resolver returning every address; a body-size limit enforced while
reading; a deadline for the whole request.

**2026-11-15: still open at toke v3.2.0 (`ea7ddf22`).** The deadline and body cap are **138.24**,
connect-to-address with name verification and a resolver are **138.25**; both are new stdlib API
needing a spec amendment and an owner decision, no date. Measured at 3.2.0: drip `$ok` at about
40 s, 64 MiB read whole. loke keeps curl in `moke.proxy.fetch` (MK19.11 stays open).

## T-64 — a per-read timeout ends a response as `$ok` with a short body

**Severity: silent wrong result.**

Measured 2026-11-09 at toke v3.1.0 (`86c432da`), loopback, plain http
([`repro-2026-11-09/MK19.11/`](repro-2026-11-09/MK19.11/), `stall` case): a server answering
`Content-Length: 8` that sends three body bytes and then nothing for 45 s makes `http.geturl`
answer **`$ok` with a 3-byte body** after 30,001 ms. The per-read timer's expiry is read as the
end of the body. `http.clientget` and `http.postheaders` were not measured.

Workaround in loke: none in the client; loke's fetch of untrusted servers uses curl (T-63).

**The ask.** A body shorter than its `Content-Length` (or a chunked body without its last
chunk) is a transport error.

**2026-11-15: fixed in toke v3.2.0 (`ea7ddf22`)**, story **138.23** (`60c319af`), with close-delimited
bodies in **138.31** (`1046f364`). Measured: the `stall` case now answers `$err` after about 30 s.
toke states one reader serves `geturl`, `clientget`/`post`/`put`/`delete` and `postheaders`; loke
measured `geturl` only. F10.52's caller audit is overtaken once loke builds on 3.2.0 (F10.53).

**2026-11-15 (W118): toke's wider claim measured.** With [`repro-2026-11-15/T-64/`](repro-2026-11-15/T-64/) at 3.2.0: `http.clientget` and `http.postheaders` answer `$err` for the stall (about 30 s), and `clientget`, `clientpost`, `postheaders` and `geturl` answer `$err` for a chunked body cut before its last chunk and for a close-delimited body ended by a reset, while a clean close answers `$ok` with the 3 bytes. Nothing toke claimed for 138.23 and 138.31 failed.

---

## T-65 — a function parameter named `t<digits>` collides with toke's IR temporaries

**Severity: build break after a clean `--check`. Not silent; not reached by loke.**

Found 2026-11-15 (W118) while writing a reproducer for T-64, and reduced
([`repro-2026-11-15/T-65/`](repro-2026-11-15/T-65/)). Measured at toke v3.1.0 (`86c432da`) and
v3.2.0 (`ea7ddf22`):

```toke
m=t65;
f=g(t0:i64):i64{
  <t0+1
};
f=main():i64{
  <g(4)
};
```

`toke --check` is rc 0. The build stops at clang: `multiple definition of local value named 't0'`
(E9003, "while compiling f=g"). The emitted IR names the parameter's stack slot `%t0` and the
first temporary `%t0` as well (`%t0 = alloca i64` … `%t0 = load i64, i64* %t0`). A parameter `t5`
collides the same way when the function has a fifth temporary. A **local** `let t0=4;` is fine
(`control.tk` exits 5), so only parameters are affected.

**What it cost loke:** nothing yet; no loke function has a parameter named so (grep, 2026-11-15).
It cost the T-64 reproducer one rename.

**The ask.** Give parameter slots a name that cannot collide with a temporary (a suffix or a
different prefix, as the `.arg` value already has), or refuse the name at `--check`.

## T-66 — a `mt` with variant arms on an i64 passes `--check` and fails at build

**Severity: a check-only target cannot see it. Not silent at build: the error is located.**

Found 2026-11-15 re-running T-2's reproducer at v3.2.0
([`repro-2026-11-15/T-66/`](repro-2026-11-15/T-66/)). A three-arm `mt` whose labels are
`FileErr` variants (`$notfound`, `$permission`, `$io`) on a parameter declared `i64` passes
`toke --check` (rc 0). The build stops with `error[E9005]: match has 3 arms, but the sum type of
the matched value is not established`, located at the `mt`. Same at v3.1.0.

This is the class toke closed elsewhere in 3.2.0: an unrecognised arm label is E3011 at
`--check` (127.292) and `mt` with variant arms on a record value is E4080 (127.367), each of
which "failed at build" before. An i64 subject is the case left.

**What it cost loke:** nothing measured. loke builds three linked trees and keeps check-only
trees (legacy `src/`, `packages/browser/src`) where such a match would pass.

**The ask.** Refuse variant arms on a subject that is not a sum or a result at `--check`, as
E4080 does for a record.

## T-67 — an integer is accepted where the runtime reads a pointer: `process.wait(5)` and `str.toupper(42)` segfault

**Severity: silent until it crashes. The remaining half of T-60's spawn ask.**

Found 2026-11-15 (W118) checking toke 138.21 for this ledger
([`repro-2026-11-15/T-67/`](repro-2026-11-15/T-67/)). Measured at v3.1.0 and v3.2.0:

- `process.wait(5)` checks clean, builds, and the program dies with SIGSEGV (exit 139).
  `process.wait(4096)` and `process.stdout(7)` do the same.
- `process.wait(0)`, the NULL handle that a `$err:e 0` arm yields, answers -1 (`zero.tk`).
  loke's idiom is safe.
- **The shape loke writes** (`laundered.tk`): `handle` cannot be named in type position
  (`let h:handle` is E2005; toke 138.32), so a helper that takes a process handle declares
  `h:i64` (`packages/core/src/installer/detect.tk`, `ollamacli.tk`, `install.tk`). The real
  handle passes through it correctly (`real=0`), and so does any other integer: `waitfor(5)`
  checks clean and segfaults.

toke 3.2.0's breaking change 6 (138.21) judges a str, float, array, map or record where a
`handle` is declared, which is what T-60 measured (`process.wait("abc")` is E4031). An integer is
deliberately left legal, because `0` is the failure filler. T-60's ask had a second half, "or
have `process.wait` refuse an address it did not hand out", which is not done.

- **The same class through `std.str`** (`abistr.tk`): 56 of `str.tki`'s 105 members are still
  `gen:"abi"`, 41 of them with every parameter and the result declared `i64` (T-36's residue;
  the same 56 as at 3.1.0). 3.2.0 refuses an array there when the runtime reads a C string
  (`str.toupper(@("x"))` is E4031, "read by the runtime as a C string"), but not an integer:
  `str.toupper(42)` and `str.reverse(12345)` check clean and segfault, at 3.1.0 and 3.2.0.

**What it cost loke:** no live defect known: loke passes only real handles and the `0` filler,
and strings to `std.str`.
But the 138.21 check never reaches loke's own handle passing, since every helper parameter is an
`i64`.

**The ask, either of:** (1) let a program name `handle` as a parameter type (138.32, option (b)),
so the checker judges loke's helpers as it now judges std's slots; or (2) have the process
runtime refuse a handle it did not create (a registry of live handles, or a tagged header),
answering -1 / `$err` as for NULL rather than dereferencing it. (2) also covers a forged handle
that reaches the runtime some other way. For `std.str`: type the remaining `gen:"abi"` members
(T-36's original ask), or extend the C-string check to integer arguments.
