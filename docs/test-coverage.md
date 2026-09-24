# Test Coverage Map

Generated: 2026-05-20 (updated after T15 epic completion) · **Corrected: 2026-09-19 (story X6.4)** ·
**Re-measured and restated: 2026-09-23 (stories X7.1 and X7.4)**

Stories: T15.1–T15.10, X6.4, X7.1, X7.3, X7.4

> **Read this before quoting any figure below. There are two coverage figures and they measure
> different things.** "Has a test file" measures *intent* — somebody decided this module deserved a
> test. "Actually exercised" measures *protection* — this module cannot silently break. Only the
> second is a coverage figure in the sense the word is normally used, and for most of this
> repository's life only the first has been quoted.
>
> The 2026-09-19 correction put the exercised figure at **about 5%**, against 35.5% for files. Its
> denominators are now stale — it counted 86 test files against 408 modules — and both moved. What
> follows is re-measured from the tree.
>
> **There is now a third figure, and it is the smallest.** A module can be exercised by a test and
> still be unreachable in the product: nothing imports it, so nothing it does can affect a user.
> Measured — 80 modules are exercised, and **31 of those have no importer anywhere in
> `packages/**` or `src/**`**, so only **49** are both exercised and on a live path. The 2026-09-19
> version of this page mentioned the problem in passing; it is measured here because de-stubbing
> made it quantifiable, and because the difference changes what a green test means. Two examples
> worth naming: `core.privacy.placeholderstore`, which holds the X8.2 field-level sealing of the
> placeholder mapping — the highest-value data in the system — is imported by nothing and appears
> only in `core.storage.db`'s comments; and `core.storage.ephemeral`, whose own test says it covers
> "the property the privacy pipeline depends on", likewise has no importer.
>
> So: **35.5% have a test file, 20% are exercised, 12% are exercised and reachable.** Quote the
> third one.

## Summary

<!-- MEASURED:BEGIN — regenerate with the census in the X7.1 inventory below; do not hand-edit -->

| Metric | Before T15 | After T15 | Corrected 2026-09-19 | **Re-measured 2026-09-23** |
|--------|-----------|-----------|----------------------|----------------------------|
| Total source modules | 313 | 408 | 408 | **408** |
| Test files discovered by `run_tests.sh` | 56 | 120 | 86 | **135** — 86 was `tests/` only and missed moke's 33 |
| Modules with a matching test file | 47 | 145 | 145 | **145** |
| Test files that import production code | — | — | 12 | **100** |
| Distinct production modules exercised | — | — | 22 | **80** |
| …of those, with **no importer** in `packages/**` or `src/**` | — | — | — | **31** |
| Test files with an explicit stub marker | — | — | 54 | **see the census** |
| Assertions the suite runs | — | — | not counted | **2423** |
| Test files that make no assertion at all | — | — | not counted | **28** |
| **"Has a test file" coverage** | **15.0%** | **35.5%** | **35.5%** | **35.5%** |
| **Modules actually exercised** | — | — | **~5%** | **20% (80 of 408)** |
| **Modules exercised AND reachable in the product** | — | — | — | **12% (49 of 408)** |
| JS utility test assertions | 0 | 70+ | unchanged | unchanged; separate harness |

<!-- MEASURED:END -->

The exercised figure moved from 22 modules to 80 in one day, and that is not a measurement artefact:
it is epic **X7.2**, which replaced the test files that declared their subject with test files that
import it. The "has a test file" figure did not move at all, which is the point of reporting both —
the number most often quoted is the one that says least.

### What a stubbed test is, and the sharpest example

`tests/unit/privacy/test_regex_detector.tk`, as it stood on the morning of 2026-09-23, imported
`std.test` and `std.str` and nothing else. Every one of its fourteen assertions was a `str.len` or
`str.contains` over a **literal**:

```
if(t.assert((str.len("123456789") as i64) == 9;"tfn: 9 digits")){pass=pass+1}el{fail=fail+1};
if(t.assert(str.contains("john@example.com";"@");"email: has @")){pass=pass+1}el{fail=fail+1};
```

It asserted that the string `"123456789"` is nine characters long, under the name
`test_regex_detector`. Meanwhile the module it is named for carried an unanchored `patautfn` that
matched the trailing nine digits of every Australian mobile number, so **every AU mobile was also
reported as a Tax File Number** — and because the pipeline takes the maximum sensitivity and
`au_tfn` is RESTRICTED against `phone_au`'s CONFIDENTIAL, every prompt containing a phone number was
escalated to the sensitivity that decides which providers it may reach. That defect (PL1.10) lived
and was fixed with this file green throughout.

That is the whole argument for X7. A test that re-declares its subject verifies that the assertion
library works and that the author's mental model is self-consistent. It cannot fail when production
code changes, which is the only thing a regression test is for.

**The linker excuse is dead.** The stub pattern was justified by a note that cross-module imports
would not link — `tests/unit/privacy/test_placeholder.tk:9` still carried
`(* i=ph:core.privacy.placeholder; -- linker issue, stubbed below *)` this morning. The gap closed
upstream (`UPSTREAM.md:77`), the build is green, and 100 test files now import production code.

---

## X7.1 — the inventory

Every discovered test file, triaged into one of three verdicts. The criterion is mechanical and is
checked by [`scripts/check_test_stubs.py`](../scripts/check_test_stubs.py): a file **exercises
production code** if it has at least one live `i=<alias>:<module>;` whose module is not `std.*`.

- **de-stub** — a real module exists, compiles and can be imported. This is the verdict for almost
  everything, because almost every module in the tree now builds.
- **delete** — the file tests nothing and something else covers the module.
- **keep with a reason** — it legitimately tests pure logic with no production dependency, or the
  module it names cannot be reached today and the reason is named.

### Four traps, all real

1. **`tests/unit/privacy/test_patterns.tk` is a genuinely good test** whose assertions are wrapped in
   `matches`/`rejects` helpers, so a raw `assert(` count reports 2 where it makes 28 checks against
   `core.privacy.patterns`. Count imports and what the assertions *reach*, not `assert(` occurrences.
2. **A file can import a production module and still assert nothing about it.** Several imported
   `shared.types` only for a struct definition. The inventory counts a module as reached when the
   test references its alias, not when the import line is present.

   The sharp instance of this is worth its own paragraph, because it is a test that was on the
   2026-09-19 list of twelve "files that import production code" and is nonetheless vacuous.
   `tests/integration/test_toon_roundtrip.tk:108` asserts `savings > 0.0` against
   `core.optimiser.toon.measuresavings`, which returns a bare `f64` across a module boundary and is
   therefore corrupted (T-20). Measured: where 37.5, 0, −300 and 0 were expected, the returned values
   are denormals whose **bit patterns are 10, 8, 8 and 4 — exactly `str.len` of the second argument.**
   A positive denormal is greater than 0.0, so the assertion passes on garbage, in both directions,
   for ever. Importing the real module is necessary and is not sufficient; the assertion has to be
   capable of distinguishing the right answer from the wrong one.

The third and fourth turned up while working it. A test can be **incapable of failing for a reason that has
nothing to do with stubs**. `tests/unit/storage/test_settings.tk` had eleven assertions written as
bare statements — `t.asserteq(v1;"loke";"...")` — with the returned bool discarded, followed by an
unconditional `pass=pass+1`; `fail` was declared, never incremented, and returned. That is a
stronger failure than the stub pattern, because a stub at least reports a mismatch against its own
copy. And a test can be **incapable of failing because the language silently corrupts the value it
asserts on** — the `measuresavings` case above, and the reason several de-stubbed tests now assert an
integer-of-hundredths form rather than the `f64` the module would prefer to return.

### The census, by directory

Measured 2026-09-23 by `find . -name 'test_*.tk'` with the same two exclusions `scripts/run_tests.sh` applies — `_archived-tests/` and the one product module `packages/core/src/privacy/test_harness.tk`, which declares no `main`.

| Directory | Files | Exercise production code | Do not |
|---|--:|--:|--:|
| `packages/moke/tests/` | 33 | **0** | 33 |
| `tests/unit/privacy/` | 25 | **25** | 0 |
| `tests/unit/governance/` | 14 | **14** | 0 |
| `tests/integration/` | 11 | **11** | 0 |
| `tests/unit/browser/` | 10 | **10** | 0 |
| `tests/unit/router/` | 8 | **8** | 0 |
| `tests/unit/storage/` | 7 | **7** | 0 |
| `tests/unit/optimiser/` | 6 | **6** | 0 |
| `tests/unit/memory/` | 5 | **5** | 0 |
| `tests/unit/providers/` | 4 | **4** | 0 |
| `tests/unit/models/` | 3 | **3** | 0 |
| `tests/unit/agents/` | 2 | **2** | 0 |
| `tests/unit/cli/` | 2 | **0** | 2 |
| `tests/unit/shared/` | 2 | **2** | 0 |
| `tests/` | 1 | **1** | 0 |
| `tests/unit/mcp/` | 1 | **1** | 0 |
| `tests/unit/policy/` | 1 | **1** | 0 |
| **Total** | **135** | **100** | **35** |

Total assertions across the suite: **2423** `t.assert`/`t.asserteq` calls. **28** files make none — they use a bare `if` and count a failure without describing it, and all but a handful of those are moke's.

### The production modules actually exercised

**80** of them.

A module is listed when a test file imports it **and** references its alias, so an import present only for a struct definition does not count.

- **`browser.pages.*`** — `health`, `models`, `pipeline`, `settings`
- **`core.agents.*`** — `scheduler`, `types`
- **`core.governance.*`** — `alert`, `approval`, `compliance`, `consent`, `forecast`, `gateway`, `incidents`, `killswitch`, `monitoring`, `policy`, `reportengine`, `rulesengine`, `scorecard`, `types`, `usecases`
- **`core.mcp.*`** — `protocol`
- **`core.memory.*`** — `aaak`, `decay`, `export`, `search`
- **`core.models.*`** — `infer`, `queue`, `registry`, `tiers`
- **`core.optimiser.*`** — `budget`, `cache`, `llmlingua`, `profiler`, `toon`
- **`core.policy.*`** — `loader`, `registry`
- **`core.privacy.*`** — `consensus`, `content`, `entityrouting`, `evaluation`, `filtermetrics`, `filterregistry`, `guardian`, `layerconfig`, `layerhealth`, `logsanitiser`, `orgpolicy`, `patterns`, `pipeline`, `placeholder`, `placeholderstore`, `regex`, `sidecarclient`, `template`, `testharness`
- **`core.providers.*`** — `anthropic`, `dispatcher`, `ollamaprovider`, `openai`, `types`
- **`core.router.*`** — `examples`, `intent`, `latencyrouter`, `router`, `selector`, `sensitivity`, `strategy`
- **`core.storage.*`** — `audit`, `backup`, `db`, `ephemeral`, `keychain`, `settings`
- **`ooke.*`** — `handlers`
- **`page.api.*`** — `approve`, `privacy`, `savings`, `tabs`
- **`shared.*`** — `types`

Imported but never referenced, so not counted as exercised: `core.memory.types`, `core.models.queuetypes`, `core.optimiser.budgettypes`, `core.optimiser.toontypes`, `core.policy.schema`, `core.policy.types`.

### Exercised, but not reachable in the product

Of the 80 modules above, **31 have no importer anywhere** in `packages/**` or `src/**`, so nothing they do can affect a user. A green test on one of these says the module behaves as written; it says nothing about the product. Only **49** are both exercised and on a live path.

- `core.governance.alert`
- `core.governance.approval`
- `core.governance.compliance`
- `core.governance.consent`
- `core.governance.forecast`
- `core.governance.incidents`
- `core.governance.monitoring`
- `core.governance.rulesengine`
- `core.governance.scorecard`
- `core.memory.decay`
- `core.memory.export`
- `core.models.queue`
- `core.models.tiers`
- `core.optimiser.llmlingua`
- `core.privacy.consensus`
- `core.privacy.content`
- `core.privacy.entityrouting`
- `core.privacy.evaluation`
- `core.privacy.filtermetrics`
- `core.privacy.filterregistry`
- `core.privacy.layerconfig`
- `core.privacy.layerhealth`
- `core.privacy.orgpolicy`
- `core.privacy.placeholderstore`
- `core.privacy.sidecarclient`
- `core.privacy.template`
- `core.privacy.testharness`
- `core.router.examples`
- `core.router.latencyrouter`
- `core.storage.backup`
- `core.storage.ephemeral`

Two of those deserve naming. `core.privacy.placeholderstore` holds the X8.2 field-level sealing of the placeholder mapping — the data `docs/threat-model.md` rates Maximum — and appears in `core.storage.db` only inside comments. `core.storage.ephemeral`'s own test says it covers "the property the privacy pipeline depends on", and it too has no importer. Neither is a test problem; both are recorded here because de-stubbing is what made them visible.

### Files that still exercise no production code

| Directory | Files | Detail |
|---|--:|---|
| `packages/moke/tests/` | 33 | all 33 of them |
| `tests/unit/cli/` | 2 | `test_commands.tk`, `test_session.tk` |

### What is not reachable today, and why

Two whole trees are invisible to the test runner, and the reasons are different. Both were measured
rather than inferred.

**`packages/moke/` — 33 test files, 0 exercise production code, and they cannot.**
`build/trees/moke/break-report.txt` records **52 `COMPILE_FAIL` lines over 42 distinct source
files**. Every module moke's tests are named after is in that list: `src/ddl.tk`, `src/profiler.tk`,
`src/agents/status.tk`, `src/cost_comparison.tk`, `src/governance.tk`, `src/routing_explainer.tk`,
`src/streaming.tk`, `src/tier_visualiser.tk`, and all eleven `pages/api/*` handlers. So the 33 are
not stubs written out of laziness: the target of each one does not exist as a linkable module. The
nineteen `pages/*.tk` page handlers **do** compile, but each exports only `get(i64):i64` — it takes an
ooke request handle, and toke offers no way to construct one from source, so there is nothing a unit
test can call.

Worse than stubbed: **21 of the 33 make no assertion at all.** They declare a struct of literal
strings describing the handler and then compare each field to the same literal —

```
f=describechathandler():$handlerinfo{
  <$handlerinfo{modulename:"page.moke.chat";templatepath:"templates/chat.tkt";hasget:true;...}
};
...
if(str.eq(info.modulename;"page.moke.chat")){pass=pass+1}el{fail=fail+1};
```

— with no `t.assert` anywhere. Twenty-eight of the 33 use bare `if` rather than the assertion
library, so a failure would be counted but never described.

The two claims in that struct that *are* falsifiable were checked against the tree: **all twelve
templates named by a `templatepath` exist on disk, and every `modulename` is declared by a real
`m=` line.** So the pattern is tautological rather than wrong, which is exactly why nothing caught
it — the assertions have been green and will stay green whatever the handlers do. A test that would
actually protect these nineteen page handlers is one that walks the page list and asserts each
template file exists and each route is registered; that is a real regression class (a renamed
template is a 500 at runtime) and it is worth one file rather than twenty-one.

Verdict for all 33: **untestable today**, blocked on the moke tree compiling. They belong to the moke
onboarding wave, not after X7.2 — a test that compiles against nothing tells you nothing about
whether moke built.

**`tests/unit/cli/` — 2 test files, blocked by the runner, not by the code.** The CLI tree builds
**clean**: `build/trees/loke-cli/break-report.txt` has **zero** `COMPILE_FAIL` lines and
`build/trees/loke-cli/interfaces/` holds `cli.commands.tki`, `cli.ask.tki` and twenty more.
`scripts/run_tests.sh` passes a single `-I "$IFACE_DIR"` pointing at `build/interfaces`, and links
`packages/browser/build/ooke` only, so nothing under `cli.*` is importable from a test however green
it is. Verified reachable by hand: compiling a probe with
`-I build/trees/loke-cli/interfaces` and linking `build/trees/loke-cli/obj/*.o` produces a working
binary that calls `cli.commands.parse` and `cli.commands.usage`.

So this is a one-line runner change, not a code problem — but it is a change to a shared script that
several stories touch, and it is recorded here rather than made under X7. The same applies to moke's
`build/trees/moke/interfaces`, with the difference that its modules must compile first.

### The gate — X7.3, live and per directory

[`scripts/check_test_stubs.py`](../scripts/check_test_stubs.py), wired into
[`scripts/quality-gate.sh`](../scripts/quality-gate.sh)'s static-checks step. Three things fail a file
in an enforced directory:

1. no live production import — every `i=` is `std.*`;
2. a commented-out import, e.g. `(* i=ph:core.privacy.placeholder; -- linker issue, stubbed below *)`,
   which is the stub pattern's own signature;
3. a stub **declaration** marker — `(* --- stub … *)`, `(* Stub: … *)`, `stubbed below`,
   `mirrors core.…`.

(3) matches declaration forms only, never the word in prose: a de-stubbed test that explains in a
comment what its stubs used to be — which most of them now do, because the history is the point —
must not be flagged for saying so.

**It is enforced per directory, and that is deliberate.** Switching it on repo-wide only after X7.2
finishes would leave it unenforced for exactly the period in which the count could grow back. A
directory joins the `ENFORCED` list in the script the moment it reaches zero, and never leaves.
`tests/unit/storage/` was first, and **fifteen of the seventeen directories that hold test files are
enforced as of 2026-09-23** — every one except `packages/moke/tests/` and `tests/unit/cli/`, for the
reasons above. The list lives in the script and is checked by the gate on every run, so it cannot
drift from this page. Two guards keep it honest: a directory named in `ENFORCED` that
holds **no** test files is a failure rather than a vacuous pass — zero violations over zero files is a
stale entry, not a clean directory — and the one product module whose name begins with `test_`,
`packages/core/src/privacy/test_harness.tk`, is excluded by full path exactly as `run_tests.sh`
excludes it.

`scripts/known-defects.txt` is the shrinking allowlist and a story ID is required per line; **it
carries no entries for this check, which is the intended state** — every enforced directory reached
zero before enforcement began, so nothing had to be tolerated.

The marker rule is judged at comment nesting **depth 1** only, and the declaration forms are matched
only in a comment's opening. toke comments nest (T-27), so a de-stubbed test that quotes the stub it
removed —

```
(* X7.2 — this file used to say
     (* i=ph:core.privacy.placeholder; -- linker issue, stubbed below *)
     (* --- stub placeholder map --- *)
   and assert against the copy. *)
```

— sits at depth 2 and is prose about a stub rather than a stub. Reading the raw text flagged four
de-stubbed files for quoting the thing they had just removed, which would have punished exactly the
behaviour the epic wants.

Proven able to fail: pointed at `tests/unit/governance/` before X7.2 ran there, it reported 12 of 14
files with the reason for each.

### The one thing de-stubbing established in the product's favour

**A RESTRICTED request cannot reach a cloud provider through `core.router.selector` or
`core.router.router`, and that is now asserted at both layers rather than assumed.** Measured, under a
deliberately hostile configuration — `newconfigfull(url;false;0.05;bestquality())`, the setting that
would otherwise prefer claude-3-5-sonnet at quality score 0.95:

- `sensitivity.canusecloud` is false for `$restricted` and true for the other three, asserted per tag
  rather than in aggregate, because `$restricted` is the *first* arm of that match and would invert if
  `mt` dispatched positionally on a plain user sum. It does not — plain sums discriminate; it is
  results that do not.
- `selector.selectmodel` on a RESTRICTED chat request with `preferlocal:false` selects `qwen2.5:72b`,
  `islocal` true, provider `"ollama"`, with a reason carrying `local-only`.
- `router.routerequest` yields a non-cloud decision by three independent routes: explicitly RESTRICTED;
  RESTRICTED by text alone with zero PII entities; and escalated to RESTRICTED by four CONFIDENTIAL
  entities. A PUBLIC control under the same hostile configuration *is* cloud-routed, so this is a rule
  being applied and not a constant refusal.

This is the project's central invariant and until today nothing in the suite exercised it: the test
named `test_sensitivity.tk` re-declared the module and asserted against the copy. Whatever else is
listed below, this part holds.

### Defects that de-stubbing exposed

The point of the epic. **37**, each found by importing a module whose test had been asserting a
copy of it, and each **reported, not fixed** — the modules belong to other stories. Every figure below
was measured by running a test, not inferred from reading; where a crash is claimed it was isolated by
bisection and re-verified against a freshly rebuilt archive, because a concurrent rebuild of the shared
`/tmp/loke-tests/libloke.a` can fake one.

**Four were fixed by other workers during the same session**, and all four are kept here because they
are the clearest demonstration of what the epic is for — in each case a de-stubbed test measured the
behaviour, the measurement was reported, and the module was repaired with a comment citing it:

| Module | What the de-stubbed test measured | Repair |
|---|---|---|
| `core.governance.scorecard:99` | `countquery` returns `rows.len`, so `SELECT COUNT(id)` is always 1 — breaking `requests`, `avgcostperreq` and a "P99" that came out below the mean | reads the aggregate through `db.one` + `rowi64` |
| `core.optimiser.llmlingua` | all four matches error-arm-first: `isavailable` returned TRUE for an absent sidecar, and no prompt had ever been compressed | `$ok` written first throughout |
| `core.optimiser.profiler.findmin`/`findmax` | `std.str.compare` returns 1 for *both* orderings, so `findmin` returned the first element and `findmax` the last | a real byte-by-byte `strlt` helper |
| `core.router.intent:319-333` | classification always answered `chat` / `method:"llm"` / 0.72 whatever the prompt | `$ok` first, and the request body rebuilt with `str.concat` |

The `str.compare` repair carries the measurement verbatim in its comment, including the two inputs and
the two answers. That is the shape this epic was meant to produce: a number somebody can check, sitting
next to the code it describes.

#### The toolchain hazard behind several of the others

**`mt` binds match arms BY POSITION, not by tag.** This is T-18 stated more sharply, and it is worse
than "the error arm is dead". Minimal reproduction, two functions differing only in arm order, over
`json.dec` — a **stdlib** result, so both arms should be live:

```
f=okfirst(raw:str):str{  <mt json.dec(raw) { $ok:o "DECODED"; $jsonerr:e "FAILED" } };
f=errfirst(raw:str):str{ <mt json.dec(raw) { $jsonerr:e "FAILED"; $ok:o "DECODED" } };
```

| | valid input | invalid input |
|---|---|---|
| `okfirst` | DECODED ✓ | FAILED ✓ |
| `errfirst` | **FAILED** ✗ | **DECODED** ✗ |

Both branches swap. So writing the error arm first does not merely lose the error case — it inverts
the function, and the success arm then receives the **error payload** bound as if it were the value.

A comment-aware sweep of `packages/**` and `src/**` counts **33 error-arm-first matches on a stdlib
result, across 12 modules** (inverted today), and **26 on a user-declared error side, across 17
modules** (where T-18 means the error arm runs on every call). Those 59 sites are a list to audit
rather than 59 confirmed defects — and one counter-example is on record: `http.get`'s result was
probed against a live server at `privacy/presidio.tk:48` and `privacy/ner.tk:38` and returned
**correctly**, so the inversion is not universal across stdlib results and each site needs measuring.
This is the class the existing `scripts/find_*.py` sweeps exist for, and by the end of the session it
had one: `scripts/find_err_arm_first.py`, written by another worker acting on the measurement, with a
repair in flight across the modules listed above.

The reproduction was made independently three times today, in three directories, by three different
routes, which is why it is stated first: it is the single defect class behind the largest number of
the rows below. `core.providers.openai.tk:44` carries a comment asserting that its matches "DO
discriminate correctly" — it describes a property the code does not have.

The worst instance found is a **fail-open**: `core.optimiser.llmlingua` had all four of its matches
error-arm-first, so `isavailable` returned TRUE for an absent sidecar, `parsecompressresponse`
rejected valid bodies, and `compress`/`compressauto` reported failure on every success — **no prompt
had ever been compressed**, and the module reported a compression sidecar it could not reach as
present. All four were fixed in source by another worker during this session and the de-stubbed
assertions were re-run green afterwards, so `tests/unit/optimiser/test_llmlingua.tk` is now a proven
regression test rather than a claim.

Two further consequences traced to source, each with its own row below: the provider token counts, and
`privacy/pipeline.tk:523`, where `let presidiosuccess=mt presidioresult { $lokeerr:e false; $ok:… true }`
makes the Presidio layer's success test a constant.

#### Live, with a caller

1. **`core.providers.anthropic:90` and `core.providers.openai:66` send a request that names no model
   and carries no prompt.** Both build the body as

   ```
   let body=json.enc($jsonobj{
     model:req.modelid; maxtokens:req.maxtokens; system:req.systemprompt; messages:req.messages
   });
   ```

   `$jsonobj` is **declared in no module in this repository**, and `json.enc` takes a `str`. It compiles
   because a struct literal of an undeclared type in an argument position compiles and passes garbage
   (see the non-defects below). Measured on the identical expression in `core.router.intent` before
   another worker repaired it there: the resulting string contains **neither the model id, nor
   `"messages"`, nor the user's text**. The field names are wrong independently — the Anthropic API
   expects `max_tokens`, not `maxtokens`.

   It is on the live path: `core.providers.dispatcher:57-66` calls `ant.completeplain` and
   `oai.completeplain`, and `page.api.pipeline.dispatch` calls the dispatcher. So this
   supersedes the token-count row below in severity — the counts are zero because the response is
   empty, and the response is empty because the request never carried the prompt. `intent.tk` has been
   fixed with `str.concat`; these two are reported and not fixed here, because they are not this
   story's modules.
2. **`core.providers.anthropic:49` and `core.providers.openai:119` — every hosted request records zero
   tokens and zero cost.** Both read the nested usage object with `json.str(obj;"usage")`, and
   `json.str` extracts a *string* where `usage` is an *object*; the following `json.dec` fails and the
   error arm returns 0. Measured against a real `/v1/messages` body carrying
   `"usage":{"input_tokens":150,"output_tokens":42}`: `content` and `model` parse correctly,
   `inputtokens` and `outputtokens` are both **0**. `calccost(model;0;0)` is then 0, and
   `browser/pages/api/pipeline.tk:405` reads both straight into `recordevent` — so **every audit row
   for an Anthropic or OpenAI request carries `tokens_in = 0`, `tokens_out = 0` and `cost_usd = 0`**,
   permanently, inside an append-only trail whose hash chain covers exactly those columns. Every
   figure derived from them is zero while reading as a measurement. Invisible from inside the program,
   because `providerfailed()` legitimately writes `0;0`: a successful call and a failed one are
   indistinguishable in the trail. **This is the second spelling of the defect** — the first,
   `page.api.pipeline.usagetokens`, read `json.i64` off the top-level object and was deleted
   by the dispatcher rewrite the same day, which reproduced the fault one module down. A test is what
   stops the third spelling.
3. **`core.providers.openai:114` — every OpenAI completion returns empty text**, same class,
   error-arm-first on the message object.
4. **`core.optimiser.profiler.findmin` and `findmax` do not find.** `std.str.compare` returns **1 for
   both orderings** and 0 for equality — measured — so it is an inequality predicate, not a three-way
   comparison. `findmin`'s `if(cmp<0)` is dead code and it returns the **first** element; `findmax`'s
   `if(cmp>0)` fires on every unequal pair and it returns the **last**. Measured:
   `findmin(cherry,banana,apple)` is `"cherry"`, `findmax(apple,cherry,banana)` is `"banana"`.
   `profilecol` sets `$colprofile.minval`/`.maxval` from these and `totoonschema` renders them into
   the schema description **sent to the model** on the no-custody path, so a column's stated range is
   two arbitrary cells presented as its minimum and maximum. Only three call sites exist in product
   source (`profiler.tk:218`, `profiler.tk:234`, `moke/src/compute.tk:582`).
5. **`core.governance.scorecard:99` — one line broke three figures. FIXED during this session**, by
   another worker, whose comment on the repaired line restates the finding exactly; the de-stubbed test
   is green against the new source. Recorded because it is the clearest demonstration of what the epic
   is for.** It passes an aggregate to
   `core.storage.db.countquery`, which returns `rows.len` rather than the aggregate's value, so
   `SELECT COUNT(id)` returns one row and therefore **1**. Measured on three Anthropic requests:
   the `COUNT(id)` form gives 1, the `SELECT id` form gives 3. `n` is reused, so `requests` reads 1
   against 3, `avgcostperreq` 100 against 33, and `p99latencyms` 100 against 900 — the offset derived
   from `n` becomes 0 and the query is `ORDER BY … ASC`, so the reported "P99" is the sample
   **minimum**. Self-evidently wrong from inside the data: the reported P99 is below the reported
   mean. `avglatencyms` and `totalcosthundredths` do not go through `n` and are correct, which
   localises it. The repair reads the aggregate through `db.one` plus `rowi64` instead.
6. **`core.governance.monitoring:63` — a quality-trend window that is always true.** `created_at` is
   written as the literal `'now()'` and `computetrend` filters
   `created_at >= datetime('now','-N days')`. `'n'` sorts after `'2'`, so the comparison holds for
   every row forever: a 1-day trend and a 3650-day trend are identical, which the test asserts. GA5.1
   and GA5.11 in two lines.
7. **`core.governance.forecast:19-37` reads neither of its inputs.** Three hardcoded constants;
   `store` and `historydays` are never read, and `historydays` selects only the *confidence label* —
   so it reports "high" confidence for history it did not look at.
8. **`core.governance.approval:45-50` — a suppression rule ignores its own scope.** Matching is on
   `tasktype` alone; `$dontaskrule.providerid` and `maxsensitivity` are never read, so a rule scoped
   to ollama/internal suppresses a restricted-to-anthropic approval and overrides mode `always`.
9. **`core.memory.export` `rowtojson` escapes JSON with CSV rules.** `csvescape` doubles interior
   quotes, so a memory containing `"` exports as `"content":"he said ""hi"""` and the file will not
   parse. The same helper is correct in `rowtocsv2`, which the test asserts as the contrast.
10. **`core.mcp.protocol:39-48` — no MCP tool can receive an argument.** `paramsraw` is set with
   `json.enc(json.getval(...))`, passing a Json handle where `str` is declared; the measured value is
   `"51887746848"`, a rendered pointer. `mcp-toke/src/tools.tk` decodes that field for tool arguments.
   `protocol.tk:52` compounds it: `parserequest` is error-arm-first, so it reports `$err` for every
   valid request and runs `buildrequestfromobj` over the error payload for an invalid one.
11. **`core.mcp.protocol.errorresponse` does not escape its message**, and `tools.tk:312` builds one
    from a client-supplied tool name.
12. **`core.memory.schema` segfaults, so no `memory_*` table is ever created.** All five statements
    are `db.exec(conn; sql)` while `std.db.exec` is `(str,[str])` — the arity-compatible defect
    `core/storage/db.tk` documents fixing in five of its own calls; these five were missed. Measured
    after a real `openstore` ran the migrations: **`memory_drawers`, `memory_closets`, `memory_index`
    and `memory_scores` are all absent**, with controls in the same run confirming the store opened
    and that `tableexists` discriminates. It is the only `CREATE TABLE` for a `memory_*` table in the
    tree, it covers three of the four, and **`memory_scores` has no creator anywhere** although
    `decay.tk`, `export.tk` and `privacy.tk` all read and write it. This is the empirical answer to
    **M1.7**.
13. **`core.storage.settings` — all four setters — and `core.storage.dashboard:97` bind `"now()"` as a
    parameter.** SQL functions are not evaluated inside a bound parameter, so `settings.updated_at`
    stores the seven characters `n-o-w-(-)`. The GA5.1 defect, fixed in `audit_log.created_at` and
    again in `schema_migrations.applied_at`, still live here. Latent only because nothing reads the
    column yet.
14. **`core.governance.approval:81`** — `!(i>maxlen)` runs `maxlen+1` times and appends a blank line
    to every generated diff.

15. **`core.router.intent:319-333` — intent classification always answers "chat", with a false
    provenance claim.** All three stdlib-result matches are error-arm-first, so `raw` is bound to
    `fast` (an `$intentresult`) and `json.dec` is handed a struct pointer; the keyword fallback is
    never returned, it is fed to the parser, and the function ends at its unconditional
    `<$intentresult{task:task;confidence:0.72;method:"llm"}`. Measured with nothing listening on the
    classifier port:

    | prompt | `classifyfast` | `classify` |
    |---|---|---|
    | "implement a sorting algorithm" | code_generation / keyword / 0.80 | **chat / llm / 0.72** |
    | "load this csv and find trends" | data_analysis / keyword / 0.78 | **chat / llm / 0.72** |

    The threshold is `> 0.80` and 41 of the module's 56 keyword outcomes are 0.60, 0.70, 0.78 or 0.80,
    so most classifications take this path. `router.tk:308` calls `classify` on every request and feeds
    `.task` into `$selectioncriteria.task`, so **a request asking for code is not offered a code
    model**. Two further consequences: the confidence *rises* above the keyword result it discarded,
    and `method` reads `"llm"` when no LLM was reached — a false provenance claim, in a project whose
    NC1.5 rule is that a figure must name where it came from. Masked by `taskfromstr` defaulting to
    `chat` rather than erroring.
16. **`core.router.selector.senstostr` and `core.router.sensitivity.leveltostr` render `"RESTRICTED"`
    while `shared.types.senslabel` renders `"restricted"`.** `governance/dashboard.tk:82-86` already
    records this making a privacy-coverage query read 0 of N on every row the request path has written.
    Not left red, because the uppercase form reaches only logs and the reason string and the stored
    column goes through `senslabel` — but it is one rename away from doing damage again.

#### Crashes — a valid call kills the process

Each was isolated by bisection and re-verified against a freshly rebuilt archive, because a
concurrent rebuild of `/tmp/loke-tests/libloke.a` can fake a crash.

17. **`core.models.registry.meetstier($background(0);…)` SEGFAULTS.** `$interactive` and `$considered`
    return; the third arm faults at any speed, and so does
    `bestfortask(r;$chat(0);false;$background(0))`. **Model selection at the background tier crashes
    the process**, which is the whole overnight and agent path. T-2 family — a three-arm match.
18. **`core.providers.ollamaprovider.isavailable` SEGFAULTS on a machine with no Ollama**, which is
    the normal state. `$ollamaprovider` declares `client:i64`, `new` stores an `$ollamaclient` struct
    in it, and `isavailable` passes that back where the struct is expected. `core.models.ollama.healthcheck`
    itself is fine. `completeplain` has the same shape.
19. **`core.models.queue` — all four transitions SEGFAULT on the field they exist to change.** They
    pass a bare `$running` where `$jobstatus{$running:0}` is required; `.id` and `.startedat` read
    back fine and `statuslabel(j.status)` faults. `enqueue` also never adds the job, and all four
    transitions drop `maxconcurrent`.
20. **`core.privacy.template` SEGFAULTS on a parameterless render.** Reproduced in isolated files:
    `renderuser(t;"{}")`, `renderuser(t;"")` and `render(t;"")` all fault, while `renderuser` with at
    least one key and `render` with `"{}"` are correct. Cause is the arm-order defect: both open with
    `mt json.dec(paramsjson) { $ok:obj obj; … }`, so a failed decode binds the **error payload** and it
    is then used as a JSON object. `""` and `"{}"` are exactly what a caller sends for an all-optional
    template and what a UI submits before the user types, so **in a server this is a denial of service
    reachable from a parameterless render.** No red assertion was left for it: a SIGSEGV aborts the
    binary and would destroy the other forty assertions in that file.

#### Fail-open, or a control that does not control

21. **`core.privacy.sidecarclient` cannot report failure.** `detect` returns the raw transport string
    with no result type and no status check, so a sidecar that is down is byte-identical to "this text
    is clean". That is fail-open on a detection layer, against the invariant in `CLAUDE.md`.
    `isavailable` only asks whether `/health` *contains* `"ok"`.
22. **`core.privacy.layerhealth.checkhealth` probes nothing.** `if(str.eq(id;"presidio")){isavail=false}`
    and every other id is "operational" — so NER reports healthy with no Ollama running, and a
    nonexistent layer id reports available. `degraded` is `available<total`, so an **empty** layer list
    formats as "HEALTHY: all 0 layers available" while `issystemhealthy` on the same report says false.
23. **`core.privacy.orgpolicy` — four defects in an enforcement module.** `minimum_layers` is never
    parsed, so any value becomes the literal `2` and a five-layer policy validates at two — fail-open;
    `enforced` is `str.contains(content;"enforced")`, so `{"enforced": false}` loads as **true**;
    `max_confidence_threshold` is never read; and `validate` ignores both `requiredlayers` and
    `bannedlayers`, so a configuration running a banned layer reports no violation.
24. **`core.privacy.consensus.resolveoverlaps` ignores its strategy argument and resolves nothing.**
    `unanimous`, `majority`, `most-restrictive` and a nonexistent strategy are identical
    pass-throughs, and a single-layer detection survives `unanimous`.
25. **`core.privacy.pipeline:727,731,735` — `applypreset`, `setentityenabled` and `setlayerenabled`
    are complete no-ops**, returning their config argument and ignoring the rest. A privacy-settings
    screen wired to them reports success and changes nothing.
26. **`core.privacy.layerconfig.getlayer` returns the FIRST layer for an unknown id** — the
    accumulator is seeded with `layers.get(0)` — so asking whether an unknown layer is enabled answers
    yes, with the regex layer's threshold attached.
27. **`core.privacy.filtermetrics.recorddetection` — `avgconfidence` is not an average.** It overwrites
    with the latest value (0.95, 0.80, 0.0 reads back as 0.0), and `entitycounts` is never written at
    all: it stays `"{}"` for ever.

#### Latent — no live caller, characterised rather than left red

28. **`core.governance.gateway.submit`/`submitinner` SIGSEGV on a valid request.**
    `submitinnerwithuc`'s third parameter is declared `i64`, so `founduc.risklevel` (an i64) reaches
    `pol.classifyrisk`, which declares `$risktier`. Minimised: every component works standalone and
    `submitinner` dies. `submitinnerunknownuc` is dead code under T-18.
29. **`core.governance.gateway:148-158` — `activatekillswitch` and `deactivatekillswitch` are `==`
    comparisons, not assignments.** T-26's advice was followed literally. Neither can work with `=`
    either: the parameter is by value and the return is `:void`. `submit`'s deny branch is therefore
    unreachable, and **T4.5's acceptance criterion cannot hold through this module.** Gateway is
    imported by `cli/ask.tk:12` and `browser/extensions/core.tk:11`, and neither calls `submit`.
30. **`core.memory.decay.apply` returns garbage across the module boundary** — `2` for a fresh memory
    and `-inf` at every age, while `$decayconfig`'s struct fields read back perfectly: T-20 for `f32`.
    Latent because nothing imports the module, but `sweeprows` deletes when the value is below
    `prunebelow` and `-inf` is below everything, so **`apply` must be fixed before the memory tables
    are created, or the first sweep wipes the palace.** Both memory tests cross-reference that
    ordering.
31. **`core.storage.keychain.getkey` returns a NULL string on a miss**, not `""`. Measured:
    `str.len(NULL)` is 0, but `str.eq(NULL;"")` is **false** and `str.contains(NULL;…)` is false. Every
    current caller guards with `str.len(k)>0`, so nothing is broken — including
    `browser/pages/api/settings.tk:73`, which would otherwise have masked and rendered `(null)` as
    though a key were configured. A trap for the next caller who reaches for the other spelling.
32. **`core.agents.scheduler.checkdue` never reads `currenttimeepoch`** — asserted directly with two
    timestamps twenty-five years apart producing the same verdict, so a scheduled agent is due on
    every tick. Self-declared in the module's own reason string, so it is recorded as debt and the
    test goes red when a real parser lands.
33. **`core.memory.search.indexdrawer`** declares `drawer:i64` and then reads `drawer.content` and
    `drawer.id` (a segfault), and returns from inside its keyword loop, so it would index one keyword
    per drawer. Not called; rows are inserted with SQL instead.
34. **`core.memory.palace.status`** — the interface says `return: i64` and the body returns
    `$ok($palacestatus{…})`. Not called.

35. **`core.router.latencyrouter:62` logs a control that did not run.** `filterbylatency` logs
    "restricted to local models" and returns `t.filtermodels(candidates;true)`, but
    `shared.types.filtermodels` is `{ <models }` — an identity stub — and is additionally called with
    `@i64` where `i64` is declared and `bool` where `str` is. Nothing is restricted, and the log line
    asserts otherwise.
36. **`core.router.examples` never persists anything.** `std.vecstore` writes
    `<datadir>/<collection>.vecs`, but `collection_save` runs only from `vecstore_close` and nothing in
    the repository calls `vecstore.close` — the module exposes `open` and `collection` with no
    counterpart. Measured: after two `addexample` calls and two successful searches, the file does not
    exist. Routing examples live in memory and die with the process.
37. **`core.router.selector.tolerancefromstr` returns a `$modeltier` from a function declared
    `$latencytolerance`.** Both sums carry `$background` at index 2, so it behaves correctly by
    coincidence.

#### Two further T-20 measurements, and the accessor that makes one untestable

- **`core.providers.anthropic.calccost` and `core.providers.openai.calccost`** return a bare `f64`
  across a module boundary and yield garbage — the same shape as `toon.measuresavings`. So even with
  correct token counts the cost figure would not survive the return.
- **Reading an element out of an `@f32` array is broken**: `@(1.5 as f32).get(0) as f64` gives
  `4.60943e+18`, the f64 bit pattern of 1.5. A scalar `f32` and an `@f64` array are both fine.
  `core.optimiser.cache.tof64` uses that accessor, so whether the conversion added to fix the f32/f64
  width mismatch is itself converting garbage cannot be settled without a loaded `nomic-embed-text`
  model; only `tof64`'s length is asserted.

#### Three non-defects, recorded because each cost time and reads like one

- **`$budgetmanager.usage` is an array** of per-period counters, so `m.usage.tokensused` reads an array
  header as a struct and yields a pointer value — 4387275664 where 1234 was expected.
  `core.optimiser.budget.rowtokens(m;idx)` is the accessor. The module is fine; the spelling was.
- **A sum-variant literal in an ARGUMENT position compiles with its declaring module unimported** and
  passes garbage, where the same type in a `let` **annotation** correctly raises E3011. That made 19
  policy assertions fail in a way indistinguishable from LS1.1a never having been fixed.
- **`sc` is a reserved token and cannot be an import alias.** It is reported as E2002 "unexpected
  token" at the alias, with no hint that the name is the cause. Two workers lost time to it
  independently.
- **A context-dependent miscompilation in large functions.** In `tests/unit/privacy/test_template.tk`
  a `$prompttemplate` literal placed after the 35th assertion in `main()` segfaulted at its
  *construction*, while identical code in a smaller function was fine; splitting the block into its
  own function fixed it. Repeated `mt tpl.render(...)` blocks in one function also segfaulted at the
  third. Binding a result once, through a helper that returns a plain struct, is the safe shape. One
  assertion is left unwritten because of this and the file says so.

---

## Coverage by Package

| Package | Modules | Tested | Untested | Coverage |
|---------|---------|--------|----------|----------|
| packages/core | 169 | 76 | 93 | 44% |
| packages/moke | 62 | 32 | 30 | 51% |
| packages/browser | 34 | 16 | 18 | 47% |
| packages/cli | 26 | 4 | 22 | 15% |
| packages/mcp-broker | 6 | 1 | 5 | 16% |
| packages/mcp-toke | 4 | 0 | 4 | 0% |
| packages/shared | 5 | 2 | 3 | 40% |
| src/ (foundation) | 102 | 14 | 88 | 13% |
| **Total** | **408** | **145** | **263** | **35.5%** |

Note: the per-package totals include some modules mapped to tests via indirect
coverage (e.g. `test_commands.tk` covers both `cli/ask.tk` and `cli/proxy.tk`),
so the sum may differ slightly from the summary table which counts unique modules.

**These per-package percentages count FILES, not exercised modules, and are the "has a test file"
figure throughout.** They are kept because they are the only per-package breakdown this document has
and because the map from module to test-file name is still useful; they are not a coverage figure in
the normal sense. For what is actually exercised, read [the census](#the-census-by-directory) and
[the module list](#the-production-modules-actually-exercised) above — those are measured from the
import graph, this table is not. The list of packages with import-level coverage in the 2026-09-19
version of this paragraph is now wrong in the good direction, and was deleted rather than corrected
because it will be wrong again tomorrow: the census is generated, a prose list is not.

---

## Tested Modules (Full List)

> "Tested" in the tables below means **a test file exists and is mapped to this module**. It does not
> mean the module is imported or executed. Rows where the test imports production code are the twelve
> files listed under [Test files that import production code](#test-files-that-import-production-code).

### packages/core/src/privacy/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| placeholder.tk | tests/unit/privacy/test_placeholder.tk | Tested |
| placeholder_store.tk | tests/unit/privacy/test_placeholder_store.tk | Tested |
| org_policy.tk | tests/unit/privacy/test_org_policy.tk | Tested |
| regex.tk | tests/unit/privacy/test_regex_detector.tk | Tested |
| template.tk | tests/unit/privacy/test_template.tk | Tested |
| guardian.tk | tests/unit/privacy/test_guardian.tk | Tested |
| content.tk | tests/unit/privacy/test_content.tk | Tested |
| pipeline.tk | tests/unit/privacy/test_pipeline_orchestrator.tk | Tested |

### packages/core/src/memory/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| search.tk | tests/unit/memory/test_search.tk | Tested |
| export.tk | tests/unit/memory/test_export.tk | Tested |
| aaak.tk | tests/unit/memory/test_aaak.tk | Tested |
| decay.tk | tests/unit/memory/test_decay.tk | Tested |
| palace.tk | tests/unit/memory/test_palace_drawers.tk | Tested |

### packages/core/src/providers/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| anthropic.tk | tests/unit/providers/test_anthropic.tk | Tested |
| openai.tk | tests/unit/providers/test_openai.tk | Tested |
| ollama_provider.tk | tests/unit/providers/test_ollama.tk | Tested |
| dispatcher.tk | tests/unit/providers/test_dispatcher.tk | Tested |

### packages/core/src/agents/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| scheduler.tk | tests/unit/agents/test_scheduler.tk | Tested |
| types.tk | tests/unit/agents/test_types.tk | Tested |

### packages/core/src/mcp/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| protocol.tk | tests/unit/mcp/test_protocol.tk | Tested |

### packages/core/src/models/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| tiers.tk | tests/unit/models/test_tiers.tk | Tested |
| registry.tk | tests/unit/models/test_registry.tk | Tested |
| queue.tk | tests/unit/models/test_queue.tk | Tested |

### packages/core/src/router/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| router.tk | tests/unit/router/test_router.tk | Tested |
| sensitivity.tk | tests/unit/router/test_sensitivity.tk | Tested |

### packages/core/src/optimiser/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| budget.tk | tests/unit/optimiser/test_budget.tk | Tested |
| toon.tk | tests/unit/optimiser/test_toon.tk | Tested |

### packages/core/src/storage/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| audit.tk | tests/unit/storage/test_audit.tk | Tested |
| ephemeral.tk | tests/unit/storage/test_ephemeral.tk | Tested |
| keychain.tk | tests/unit/storage/test_keychain.tk | Tested |
| settings.tk | tests/unit/storage/test_settings.tk | Tested |

### packages/core/src/governance/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| consent.tk | tests/unit/governance/test_consent.tk | Tested |
| gateway.tk | tests/unit/governance/test_gateway.tk | Tested |
| incidents.tk | tests/unit/governance/test_incidents.tk | Tested |
| kill_switch.tk | tests/unit/governance/test_kill_switch.tk | Tested |
| rules_engine.tk | tests/unit/governance/test_rules_engine.tk | Tested |
| scorecard.tk | tests/unit/governance/test_scorecard.tk | Tested |

### packages/cli/src/

| Source Module | Test File | Status |
|---------------|-----------|--------|
| ask.tk / proxy.tk | tests/unit/cli/test_commands.tk | Tested |
| session.tk | tests/unit/cli/test_session.tk | Tested |

### Integration Tests

| Target Subsystem | Test File | Status |
|------------------|-----------|--------|
| Health API | tests/integration/test_health_api.tk | Tested |
| Pipeline API | tests/integration/test_pipeline_api.tk | Tested |
| Pipeline (full) | tests/integration/test_pipeline_integration.tk | Tested |

### Standalone Tests

| Target | Test File | Status |
|--------|-----------|--------|
| storage/keychain + settings | tests/test_keychain_settings.tk | Tested |
| storage/db (encryption) | tests/test_db_encryption.tk | Tested |
| privacy (log sanitiser) | tests/unit/privacy/test_log_sanitiser.tk | Tested |
| governance/policy (ownership) | tests/unit/governance/test_ownership.tk | Tested |

### packages/moke/ (moke tests)

| Source Module | Test File | Status |
|---------------|-----------|--------|
| src/agents/status.tk | packages/moke/tests/test_agents_status.tk | Tested |
| src/cost_comparison.tk | packages/moke/tests/test_cost_comparison.tk | Tested |
| src/ddl.tk | packages/moke/tests/test_ddl.tk | Tested |
| src/governance.tk | packages/moke/tests/test_governance.tk | Tested |
| src/profiler.tk | packages/moke/tests/test_profiler.tk | Tested |
| src/routing_explainer.tk | packages/moke/tests/test_routing_explainer.tk | Tested |
| src/streaming.tk | packages/moke/tests/test_streaming.tk | Tested |
| src/tier_visualiser.tk | packages/moke/tests/test_tier_visualiser.tk | Tested |
| pages/* (pipeline panel) | packages/moke/tests/test_pipeline_panel.tk | Tested |
| pages/* (pipeline stages) | packages/moke/tests/test_pipeline_stages.tk | Tested |

---

## Untested Modules (Full List)

### packages/core/src/privacy/ (13 untested of 21)

- consensus.tk
- entity_routing.tk
- evaluation.tk
- filter_metrics.tk
- filter_registry.tk
- layer_config.tk
- layer_health.tk
- ner.tk
- patterns.tk
- pipeline_types.tk
- presidio.tk
- sidecar_client.tk
- web_meta.tk

### packages/core/src/memory/ (9 untested of 14)

- context.tk
- graph.tk
- mcp_server.tk
- mining.tk
- privacy.tk
- schema.tk
- shorthand.tk
- storage.tk
- types.tk

### packages/core/src/pipeline/ (3 untested of 3)

- emitter.tk
- history.tk
- types.tk

### packages/core/src/auth/ (4 untested of 4)

- oauth.tk
- pkce.tk
- refresh.tk
- token_store.tk

### packages/core/src/providers/ (1 untested of 5)

- types.tk

### packages/core/src/agents/ (8 untested of 10)

- executor.tk
- latency.tk
- observability.tk
- overnight.tk
- pipeline.tk
- registry.tk
- sandbox.tk
- templates.tk

### packages/core/src/mcp/ (2 untested of 3)

- client.tk
- discovery.tk

### packages/core/src/models/ (6 untested of 9)

- hardware.tk
- infer.tk
- mlx.tk
- ollama.tk
- queue_types.tk
- streaming.tk

### packages/core/src/router/ (6 untested of 8)

- escalation.tk
- examples.tk
- intent.tk
- latency_router.tk
- routellm.tk
- selector.tk

### packages/core/src/optimiser/ (5 untested of 7)

- budget_types.tk
- cache.tk
- llmlingua.tk
- profiler.tk
- toon_types.tk

### packages/core/src/storage/ (4 untested of 8)

- backup.tk
- dashboard.tk
- db.tk
- migrations.tk
- sync_queue.tk

### packages/core/src/governance/ (21 untested of 27)

- ai_gov.tk
- alert.tk
- approval.tk
- compliance.tk
- dashboard.tk
- dsar.tk
- external.tk
- forecast.tk
- monitoring.tk
- policy.tk
- quota.tk
- report.tk
- report-engine.tk
- report-export.tk
- response-scanner.tk
- suppression.tk
- trace.tk
- types.tk
- use_cases.tk
- value.tk
- violation-types.tk

### packages/core/src/feedback/ (7 untested of 7)

- draft.tk
- learning.tk
- pipeline.tk
- report.tk
- reporter.tk
- store.tk
- types.tk

### packages/core/src/extensions/ (3 untested of 3)

- gateway_hooks.tk
- pipeline_hooks.tk
- provider_registry.tk

### packages/core/src/companion/ (5 untested of 5)

- channel.tk
- discovery.tk
- exo.tk
- executor.tk
- types.tk

### packages/core/src/eval/ (3 untested of 3)

- advisor.tk
- bench.tk
- compare.tk

### packages/core/src/installer/ (9 untested of 9)

- autostart.tk
- detect.tk
- install.tk
- models.tk
- pull.tk
- start.tk
- uninstall.tk
- updater.tk
- verify.tk

### packages/core/src/policy/ (10 untested of 10)

- conflict.tk
- export.tk
- feedback.tk
- loader.tk
- merge.tk
- regulations.tk
- schema.tk
- types.tk
- validate.tk
- watcher.tk

### packages/core/src/ (other -- 4 untested of 4)

- audit/metrics.tk
- metrics/collector.tk
- monitoring/sysmon.tk
- setup/wizard.tk
- update/checker.tk

### packages/moke/ (39 untested of 49)

#### src/ (untested)
- _handlers.tk
- approval.tk
- companion_simulator.tk
- compute.tk
- console_log.tk
- dashboard_flow.tk
- hooks.tk
- main.tk
- provider.tk
- sensitivity.tk
- token_optimisation.tk
- upload.tk
- workspace.tk
- agents/quality_scanner.tk
- agents/schema_detector.tk
- feedback/feedback.tk
- mcp/broker_status.tk
- mcp/memory_demo.tk
- mcp/tool_panel.tk
- memory/memory.tk
- ml/engine.tk
- ml/proposal.tk

#### pages/ (untested)
- agents.tk
- chat.tk
- confirm.tk
- connections.tk
- dashboard.tk
- governance.tk
- index.tk
- insight.tk
- lokehealth.tk
- mcp.tk
- memory.tk
- presentation.tk
- settings.tk
- sysmon.tk
- upload.tk
- api/ (agents, datasets, feedback, health, memory, ml, mcp, pipeline, routing, stream, upload)

#### data/ (untested)
- au_datasets.tk
- customer_intel.tk
- it_hardware.tk
- it_platform.tk
- registry.tk

#### extensions/ (untested)
- core.tk

### packages/browser/ (33 untested of 33)

- _handlers.tk
- _serve_main.tk
- extensions/core.tk
- pages/: approve.tk, chat.tk, index.tk, installer.tk, pipeline.tk, privacy.tk, savings.tk, setup.tk, sysmon.tk, tabs.tk
- pages/api/: approve.tk, health.tk, models.tk, pipeline.tk, privacy.tk, savings.tk, settings.tk, tabs.tk
- src/: _handlers.tk, main.tk, nav.tk, notifications.tk, server.tk, shell.tk, tabs.tk
- src/components/: button.tk, card.tk, form.tk, input.tk, modal.tk, table.tk

### packages/cli/src/ (24 untested of 26)

- bundle.tk
- code_profile.tk
- commands.tk
- doctor.tk
- feedback.tk
- health.tk
- init.tk
- installer.tk
- integrations.tk
- locale.tk
- main.tk
- model-mgmt.tk
- output.tk
- policy.tk
- port.tk
- portable.tk
- proxy.tk (partially covered via test_commands.tk)
- proxy_config.tk
- report.tk
- sign.tk
- startup.tk
- stats.tk
- updater.tk
- verbose.tk

### packages/mcp-toke/src/ (4 untested of 4)

- main.tk
- server.tk
- tools.tk
- transport.tk

### packages/mcp-broker/src/ (6 untested of 6)

- aggregator.tk
- main.tk
- permissions.tk
- proxy.tk
- registry.tk
- server.tk

### packages/shared/src/ (5 untested of 5)

- config.tk
- errors.tk
- log.tk
- result.tk
- types.tk

### src/ (foundation layer -- 37 untested of 37)

#### src/core/
- audit/trail.tk
- cache/semantic.tk
- config/keychain.tk, schema.tk
- discovery/mdns.tk
- hardware/profile.tk, recommender.tk
- health/api.tk, checker.tk
- inference/mlx/backend.tk, native/engine.tk, native/selector.tk, ner/local.tk, sidecar.tk, streaming/disk.tk
- storage/ephemeral.tk, vector.tk

#### src/mcp-broker/
- broker.tk, cli.tk, config.tk, registry.tk, transport.tk

#### src/memory/
- agent_diary.tk, enrichment.tk, knowledge_graph.tk, mining.tk

#### src/dist/
- cli_binary.tk, package.tk, port.tk, proxy_config.tk, signing.tk, updater.tk

#### src/platform/
- a11y/ (11 modules): announcements.tk, aria-patterns.tk, colour.tk, focus.tk, focus-trap.tk, keyboard.tk, live_regions.tk, roving-tabindex.tk, semantic.tk, skip-link.tk, testing.tk
- error/ (3 modules): api_client.tk, client.tk, server.tk
- http/ (5 modules): middleware.tk, response.tk, router.tk, security.tk, server.tk
- i18n/ (3 modules): layout.tk, locales.tk, translator.tk
- integration/ (4 modules): adapter.tk, http_client.tk, oauth.tk, sanitise.tk
- plugin/ (5 modules): anonymisation.tk, config.tk, contracts.tk, lifecycle.tk, registry.tk
- testing/ (5 modules): debug.tk, quality_gate.tk, scaffold.tk, utilities.tk, watch.tk
- ui/ (9 modules): components.tk, navigation.tk, notifications.tk, reset.tk, router.tk, settings_ui.tk, shell.tk, theme.tk, tokens.tk

#### src/browser/
- shell.tk, window_manager.tk
- workspace/: chat_panel.tk, dashboard_persist.tk, extractor.tk, privacy_metadata.tk, tabs.tk

#### src/cli/
- ask.tk, code_preprocess.tk, env.tk, proxy.tk, sessions.tk

#### src/companion/
- channel.tk, discovery.tk, exo.tk, remote_exec.tk

#### src/governance/
- disclosure.tk, dsar.tk, explainability.tk, incidents.tk, justification.tk, kill_switch.tk, ownership.tk, tier_dashboard.tk, trace.tk

---

## All Test Files

**This table is deleted rather than updated.** It listed 57 files against a suite of 134 and mapped
each to a target module by name, which is precisely the measurement that made 35.5% quotable. Any
hand-maintained list of test files in a tree this active is stale the day it is written — this one
had been wrong since before the 2026-09-19 correction and nothing caught it.

What replaces it is measured from the tree, in [the census](#the-census-by-directory) and
[the module list](#the-production-modules-actually-exercised). To regenerate either, count live
`i=<alias>:<module>;` lines whose module is not `std.*` across
`find . -name 'test_*.tk' -not -path '*/_archived-tests/*'`, which is what
[`scripts/check_test_stubs.py`](../scripts/check_test_stubs.py) does. Each test file's own
`.tkc.md` companion states what it covers and what it depends on, and those are kept current
because they sit beside the file.

---

## Priority Gaps for T15.2-T15.8

| Epic Story | Gap Area | Untested Modules |
|------------|----------|------------------|
| T15.2 | Privacy pipeline | consensus, entity_routing, evaluation, filter_registry, ner, patterns, layer_health, filter_metrics, layer_config, pipeline_types, presidio, sidecar_client, web_meta |
| T15.3 | Router + optimiser | selector, intent, latency_router, escalation, routellm, cache, profiler, llmlingua |
| T15.4 | Governance + storage | policy, compliance, monitoring, quota, suppression, trace, response-scanner, db, migrations, sync_queue |
| T15.5 | Browser handlers | All 33 browser modules (pages/api/, src/, components/) |
| T15.6 | Moke page handlers | All 15 moke pages + 11 API handlers |
| T15.7 | Integration tests | Full pipeline flow (partially started with test_pipeline_integration.tk) |
| T15.8 | JS utility tests | static/js/*.js (not .tk -- separate harness needed) |

---

## Test files that import production code

The twelve-file table that stood here was correct on 2026-09-19 and is now three times wrong. It is
replaced by the generated census above: see [the census by directory](#the-census-by-directory) for
the count and [the module list](#the-production-modules-actually-exercised) for what they reach.

One thing the old table got right and is worth keeping: it distinguished a module *imported* from a
module *exercised*, noting that three of its twenty-two were types-only declarations. The census
applies that rule mechanically — a module counts as reached only when the test references its alias,
so an import present solely for a struct definition does not inflate the figure.

---

## Known exclusions

`scripts/run_tests.sh` excludes exactly two things from discovery, and the difference between them
matters:

1. `packages/core/src/privacy/test_harness.tk` — a product module whose name begins with `test_`. It
   declares no `main` and must not be discovered as a test. The exclusion used to be the glob
   `*/test_harness*`, which also swallowed `tests/unit/privacy/test_harness_runner.tk`, the driver
   that actually executes the harness; naming the file rather than a prefix keeps the module out and
   lets the runner in. That was **AD1.8**, and the runner now exists and imports
   `core.privacy.testharness`.
2. `_archived-tests/` — **514 archived test files**, excluded wholesale. This is the quiet one. The
   RV1.1 reconciliation found that **37 of the 65 `T1`–`T14` story rows cite a test file that lives
   in this directory**, so 37 Done markers rest on evidence the discovery glob removes before
   compilation. Nothing in the repository made that visible: the rows name a path under `tests/`, and
   the file at that path is simply absent. See **RV1.1 worked** in
   [epics-and-stories.md](epics-and-stories.md).

Two further exclusions are not in the runner's glob but have the same effect, and are measured under
[what is not reachable today](#what-is-not-reachable-today-and-why): the runner passes a single
`-I build/interfaces` and links `packages/browser/build/ooke` alone, so `build/trees/loke-cli/` (which
builds clean) and `build/trees/moke/` (which does not) are both unreachable from a test.

CI reports pass and fail counts only. `std.test` exposes three string-comparison assertions and cannot
record a numeric value, so no test can publish a measurement even when it takes one. That is the first
blocker in [metrics-baseline.md](metrics-baseline.md), tracked as **VM1.1** and **VM1.5**.
