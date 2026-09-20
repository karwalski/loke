# toke — issues found building loke

**Reported by:** the loke project (`github.com/karwalski/loke`)
**Toolchain under test:** toke `1bc4a44` (on `feat/type-flow-bytes-redesign`, `toke_min_commit = 6cc9061`), ooke `v3.0.0-rc.1`
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

T-1 to T-7 are build-breaking. T-8 to T-12 are hazards that let a wrong program look
right.

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

1. **T-6**, and a warning on shadowing `let`. One fix, two classes of bug caught.
2. **T-2**, the label counter. 17 sites in one project, each needing IR archaeology.
3. **T-4 and T-7** — the two silent ones. Both have a diagnostic that already exists
   and simply is not reached.
4. **T-1, T-3, T-5** — three narrow lowering bugs with clear fixes.
5. **T-11** — make stub status visible at the call site.
6. **A source location on codegen failures.** Even a "while compiling `f=x` at
   `file.tk:120`" prefix on E9003 would change these from a day of bisection into a
   minute of reading.

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
