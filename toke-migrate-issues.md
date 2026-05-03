# toke --migrate Issues — Top 20 Error Patterns

**Status:** 13/559 files compile clean after migration + manual fixes
**Date:** 2026-05-03

## Error Pattern Analysis

Each entry shows: count, error message, actual code at error location, required fix.

---

### #1 — 81 files: `expected ':' got '{'`
```
BEFORE: mt someexpr {Ok:v result){
AFTER:  mt someexpr {Ok:v v;Err:e ""}
```
**Cause:** `--migrate` mangled `|{` → `mt` conversion, lost expression boundaries. Match arms incomplete.
**Fix in --migrate:** Ensure both `Ok` and `Err` arms are emitted when converting `|{` match syntax.

### #2 — 55 files: `expected '(' got 'str'`
```
BEFORE: if str.eq(got;want)
AFTER:  if(str.eq(got;want))
```
**Cause:** `--migrate` didn't wrap `if` conditions in parens. v3 requires `if(cond){`.
**Fix in --migrate:** Detect `if <non-paren>` and wrap condition in `()`.

### #3 — 21 files: `unexpected token` at module declaration
```
BEFORE: m=loke.platform.ui.tokens
AFTER:  m=loke.platform.ui.tokens;
```
**Cause:** Missing semicolon after module declaration, or module path too long for parser.
**Fix in --migrate:** Ensure `m=` lines end with `;`.

### #4 — 15 files: `unexpected token in type position` (http.$req)
```
BEFORE: f=get(req:http.$req):http.$res{
AFTER:  f=get(req:i64):i64{
```
**Cause:** Qualified cross-module types not valid in standalone compilation. Handler signatures need `i64`.
**Fix in --migrate:** Convert `http.$req`, `http.$res`, `db.$store`, `db.$conn` to `i64` in function signatures.

### #5 — 13 files: `expected ':' in map type, got ')'`
```
BEFORE: headers:@(str);
AFTER:  headers:@str;
```
**Cause:** `@(str)` with parens is map type syntax (expects `@(key:val)`). Array type is `@str` without parens.
**Fix in --migrate:** Convert `@(str)` → `@str`, `@($type)` → `@$type` in type positions.

### #6 — 7 files: `expected ':' in map type, got ')'`
```
BEFORE: items:@(str)
AFTER:  items:@str
```
Same as #5 but in different context (no semicolon). Same fix.

### #7 — 5 files: `missing semicolon` after shared.log import
```
BEFORE: i=log:shared.log\n\n
AFTER:  i=log:shared.log;\n
```
**Cause:** Import line missing trailing `;`, or blank line confuses parser.
**Fix in --migrate:** Ensure all `i=` lines end with `;`.

### #8 — 5 files: `missing semicolon` after cross-module return type
```
BEFORE: f=preset():$s.policy{
AFTER:  f=preset():$s.policy{  (valid — the ; error is elsewhere)
```
**Cause:** Cross-module type `$s.policy` works but preceding declarations may be unterminated.
**Fix:** Check preceding lines for missing `;`.

### #9 — 5 files: `module 'ooke.template' not found`
```
BEFORE: i=tpl:ooke.template;
AFTER:  (keep — resolves at link time during ooke compile)
```
**Not a migration issue** — this is a link-time dependency. Only fails in standalone `--emit-llvm` check.

### #10 — 5 files: `unexpected token` in src/core/inference
```
BEFORE: m=loke.core.inference.ner.local
AFTER:  m=loke.core.inference.ner.local;
```
Same as #3 — missing semicolon on module declaration.

### #11 — 4 files: `expected ':' in map type, got ')'`
```
BEFORE: args:@(str)):i32{
AFTER:  args:@str):i32{
```
Same as #5 — `@(str)` in function param type position.

### #12 — 4 files: `expected ':' got '+'`
```
BEFORE: i=i+1        (inside a type block due to bad indentation)
AFTER:  i=i+1;       (move outside type block, or fix indentation)
```
**Cause:** Code statement accidentally inside a `t=$type{...}` block. The `--migrate` tool or original code has structural issues.
**Fix:** These files have structural problems — type blocks not properly closed.

### #13 — 4 files: `expected ')' got '{'`
```
BEFORE: let results=@$str{
AFTER:  let results=@($str);
```
**Cause:** `@$str{` parsed as array type followed by block. Should be `@($str)` array literal or `@str` type.
**Fix in --migrate:** Distinguish array type annotations from array literal construction.

### #14 — 4 files: `unexpected token ')' after }el{`
```
BEFORE: }el{()};
AFTER:  }el{};
```
**Cause:** Empty parens `()` in else block — not valid v3 expression.
**Fix in --migrate:** Strip `()` in empty else blocks.

### #15 — 4 files: `expected binding name, got '$'`
```
BEFORE: Ok:$v v;
AFTER:  Ok:v v;
```
**Cause:** `$` prefix on match binding variable. v3 bindings are bare identifiers.
**Fix in --migrate:** Strip `$` from binding names in match arms.

### #16 — 4 files: `unexpected token` in moke API pages
```
BEFORE: m=page.moke.api.datasets
AFTER:  m=page.moke.api.datasets;
```
Same as #3 — missing semicolon.

### #17 — 3 files: `expected ':' got 'e'`
```
BEFORE: perr e;
AFTER:  Err:e "";
```
**Cause:** `--migrate` mangled `$err:e` into `perr e` (lost the `$` and `:`).
**Fix in --migrate:** Ensure error match arms preserve `Err:binding` format.

### #18 — 3 files: `unexpected token in type position` (db.$store)
```
BEFORE: store:db.$store
AFTER:  store:i64
```
Same as #4 — qualified cross-module type needs `i64` replacement.

### #19 — 3 files: `expected '(' after '@', got '$'`
```
BEFORE: let paths=mut.@$str;
AFTER:  let paths=mut.@($str);
```
**Cause:** Mutable array literal needs `@()` parens, not bare `@$type`.
**Fix in --migrate:** Use `@($type)` for array literals/constructors, `@$type` only for type annotations.

### #20 — 3 files: `expected ')' got '.'`
```
BEFORE: (req:$http.req):$http.res{
AFTER:  (req:i64):i64{
```
Same as #4 — qualified HTTP types.

---

## Summary for --migrate tool

| Priority | Fix | Files affected |
|----------|-----|----------------|
| P0 | Fix `|{` → `mt` expression boundary detection | 81 |
| P0 | Add `if()` parens around conditions | 55 |
| P1 | Ensure `m=` and `i=` lines end with `;` | 26 |
| P1 | Convert qualified types (http.$req, db.$store) to i64 | 18 |
| P1 | Fix `@(type)` → `@type` in type positions | 25 |
| P2 | Strip `$` from match binding names | 4 |
| P2 | Fix mangled error arms (perr → Err:e) | 3 |
| P2 | Distinguish `@$type` (type) vs `@($type)` (literal) | 7 |
| — | Module not found (link-time, not migration) | 5 |

## Files that compile clean (13)
```
packages/core/src/pipeline/types.tk
packages/core/src/policy/schema.tk
packages/core/src/policy/conflict.tk
packages/core/src/policy/merge.tk
packages/browser/src/components/modal.tk
src/platform/a11y/roving-tabindex.tk
src/platform/a11y/aria-patterns.tk
src/platform/a11y/announcements.tk
src/platform/a11y/skip-link.tk
src/platform/a11y/focus-trap.tk
(+ 3 more)
```
